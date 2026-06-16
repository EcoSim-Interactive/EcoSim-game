"""Serveur WebSocket qui expose le moteur de simulation au client Godot."""
from __future__ import annotations

import asyncio
import errno
import json
import logging
from math import ceil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import websockets

from app.config import DEFAULT_SETTINGS
from app.species_catalog import SpeciesCatalogStore
from app.world_loader import build_species_from_config, build_world_from_config, load_config
from domain import World
from simulation import Simulation

# Etat global du serveur pour la session courante --------------------------------

logger = logging.getLogger(__name__)

sim: Optional[Simulation] = None
world: Optional[World] = None
runner_task: Optional[asyncio.Task] = None
compute_task: Optional[asyncio.Task] = None
pause_event = asyncio.Event()
stop_event = asyncio.Event()
tick_ms = DEFAULT_SETTINGS.tick_ms

precomputed_steps: List[Dict[str, Any]] = []
summary_cache: Optional[Dict[str, Any]] = None
steps_file: Optional[str] = None
summary_file: Optional[str] = None
step_cursor: int = 0
generation_duration: Optional[float] = None
species_catalog_cache: Optional[Dict[str, Any]] = None
species_selection_cache: Optional[List[Dict[str, Any]]] = None
species_store = SpeciesCatalogStore(
    legacy_selection_file=(Path(__file__).resolve().parents[2] / "app" / "species_selection.json")
)


def _reset_runtime_state(*, clear_events: bool = True) -> None:
    """Reinitialise les donnees derives de la simulation courante."""
    global precomputed_steps, summary_cache, steps_file, summary_file, step_cursor, compute_task
    precomputed_steps = []
    summary_cache = None
    steps_file = None
    summary_file = None
    step_cursor = 0
    if clear_events:
        pause_event.clear()
        stop_event.clear()
    if compute_task and not compute_task.done():
        compute_task.cancel()
    compute_task = None


async def _cancel_runner_task() -> None:
    """Stop and clear the current streaming task if it exists."""
    global runner_task
    if runner_task and not runner_task.done():
        runner_task.cancel()
        try:
            await runner_task
        except asyncio.CancelledError:
            pass
    runner_task = None


def _coerce_positive_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _load_catalog_with_selection() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    global species_catalog_cache, species_selection_cache

    if species_catalog_cache is None:
        species_catalog_cache = species_store.load_catalog()

    if species_selection_cache is None:
        species_selection_cache = species_store.build_selection_from_catalog(species_catalog_cache)

    return species_catalog_cache, species_selection_cache


def _build_config_with_species_selection(base_config: Dict[str, Any]) -> Dict[str, Any]:
    catalog, selection = _load_catalog_with_selection()
    _ = catalog  # garde la reference explicite pour lisibilite
    config = dict(base_config)
    config["species"] = species_store.selection_to_species_config(selection)
    return config


async def _send_species_catalog(websocket: websockets.WebSocketServerProtocol) -> None:
    catalog, _ = _load_catalog_with_selection()
    config, _ = load_config(DEFAULT_SETTINGS.world_config_path)
    world_section = config.get("world", {}) if isinstance(config, dict) else {}
    world_width = int(world_section.get("width", 1000)) if isinstance(world_section, dict) else 1000
    world_height = int(world_section.get("height", 1000)) if isinstance(world_section, dict) else 1000
    await websocket.send(
        json.dumps(
            {
                "type": "species_catalog",
                "data": {
                    "templates": catalog.get("templates", []),
                    "selection": catalog.get("default_selection", []),
                    "world_width": world_width,
                    "world_height": world_height,
                },
            }
        )
    )


async def _configure_species_selection(
    websocket: websockets.WebSocketServerProtocol,
    obj: Dict[str, Any],
) -> None:
    global sim, world, species_selection_cache

    payload = obj.get("value") if isinstance(obj.get("value"), dict) else obj.get("data")
    if not isinstance(payload, dict):
        await websocket.send(json.dumps({"type": "error", "message": "configure_species : payload manquant"}))
        return

    raw_selection = payload.get("selection")
    if not isinstance(raw_selection, list):
        await websocket.send(json.dumps({"type": "error", "message": "configure_species : selection invalide"}))
        return

    catalog, _ = _load_catalog_with_selection()
    sanitized = species_store.sanitize_selection(raw_selection, catalog)

    species_selection_cache = sanitized

    await _cancel_runner_task()
    _reset_runtime_state(clear_events=True)
    sim = None
    world = None

    await websocket.send(
        json.dumps(
            {
                "type": "species_configuration_saved",
                "data": {
                    "ok": True,
                    "species_count": len(sanitized),
                },
            }
        )
    )
    logger.info("Configuration especes enregistree (%s templates actifs).", len(sanitized))


async def _send_world_config(websocket: websockets.WebSocketServerProtocol) -> None:
    from app.world_loader import _resolve_config_path

    config_path = _resolve_config_path(DEFAULT_SETTINGS.world_config_path)
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        await websocket.send(
            json.dumps(
                {
                    "type": "world_config",
                    "data": data,
                }
            )
        )
    except Exception as exc:
        await websocket.send(json.dumps({"type": "error", "message": f"Erreur lecture config: {exc}"}))


async def _configure_world(
    websocket: websockets.WebSocketServerProtocol,
    obj: Dict[str, Any],
) -> None:
    global sim, world
    from app.world_loader import _resolve_config_path

    payload = obj.get("value") if isinstance(obj.get("value"), dict) else obj.get("data")
    if not isinstance(payload, dict):
        await websocket.send(json.dumps({"type": "error", "message": "configure_world : payload manquant"}))
        return

    config_path = _resolve_config_path(DEFAULT_SETTINGS.world_config_path)

    try:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        await _cancel_runner_task()
        _reset_runtime_state(clear_events=True)
        sim = None
        world = None

        await websocket.send(
            json.dumps(
                {
                    "type": "world_configuration_saved",
                    "data": {
                        "ok": True,
                    },
                }
            )
        )
        logger.info("Configuration du monde enregistree avec succes.")
    except Exception as exc:
        logger.exception("Erreur ecriture config")
        await websocket.send(json.dumps({"type": "error", "message": f"Erreur ecriture config: {exc}"}))


async def get_world(websocket: websockets.WebSocketServerProtocol) -> None:
    """Initialise le monde et envoie ses donnees au client."""
    global sim, world
    logger.info("Initialisation du monde...")
    config, base_dir = load_config(DEFAULT_SETTINGS.world_config_path)
    config_with_species = _build_config_with_species_selection(config)

    world = build_world_from_config(config_with_species, base_dir=base_dir)
    species_list = build_species_from_config(config_with_species, world, base_dir=base_dir)
    world.generate_terrain() # TODO: to move

    sim = Simulation(
        world,
        species_list,
        steps=DEFAULT_SETTINGS.steps,
        verbose=False,  # Désactivé en mode serveur
        write_logs=True,
        logs_dir=DEFAULT_SETTINGS.logs_dir,
    )
    _reset_runtime_state()

    CHUNK_SIZE = 50
    total_chunks = ceil(len(world.terrain) / CHUNK_SIZE)

    await websocket.send(
        json.dumps(
            {
                "type": "world_meta",
                "data": {
                    "width": world.width,
                    "height": world.height,
                    "total_chunks": total_chunks,
                    "food_sources": world.food_sources,
                    "water_sources": world.water_sources,
                    "minutes_per_step": world.minutes_per_step,
                },
            }
        )
    )
    logger.info("Métadonnées du monde envoyées, envoi des chunks terrain...")

    for i in range(total_chunks):
        start = i * CHUNK_SIZE
        end = start + CHUNK_SIZE
        chunk_rows = world.terrain[start:end]

        await websocket.send(json.dumps({
            "type": "terrain_chunk",
            "data": {
                "chunk_index": i,
                "y_start": start,
                "rows": chunk_rows,
            }
        }))
        # optionnel : une petite pause pour ne pas saturer le client
        await asyncio.sleep(0.01)

    await websocket.send(json.dumps({"type": "terrain_complete"}))
    logger.info("Tous les chunks envoyés avec succès")




def format_step_summary(step_data: Dict[str, Any]) -> str:
    species_states = []
    for status in step_data.get("species", []):
        after = status.get("after") or {}
        before = status.get("before") or {}
        x = after.get("x", before.get("x", 0.0))
        y = after.get("y", before.get("y", 0.0))
        vitality = after.get("vitality", before.get("vitality", 0))
        calories = after.get("calories", before.get("calories"))
        hunger = after.get("hunger", before.get("hunger", 0))
        thirst = after.get("thirst", before.get("thirst", 0))
        fatigue = after.get("fatigue", before.get("fatigue", 0))
        calories_fragment = f" calories={calories:.0f}" if isinstance(calories, (int, float)) else ""
        species_states.append(
            f"{status.get('name', 'Inconnu')} pos=({x:.2f}, {y:.2f}) vitalite={vitality:.0f} faim={hunger:.0f} soif={thirst:.0f} fatigue={fatigue:.0f}{calories_fragment}"
        )

    return " | ".join(species_states) if species_states else "aucune espece"


async def _compute_steps() -> None:
    global precomputed_steps, summary_cache, steps_file, summary_file, step_cursor, generation_duration
    if sim is None:
        raise RuntimeError("Simulation non initialise.")

    logger.info("Pre-calcul des steps en cours...")

    def _generate() -> Tuple[List[Dict[str, Any]], Dict[str, Any], Optional[str], Optional[str], Optional[float]]:
        assert sim is not None  # pour mypy
        steps = sim.generate_all_steps()
        summary = sim.save_summary()
        return (
            list(steps),
            dict(summary),
            sim.steps_file,
            sim.summary_file,
            getattr(sim, "last_generation_duration", None),
        )

    steps, summary, bundle_path, summary_path, duration = await asyncio.to_thread(_generate)
    precomputed_steps = steps
    summary_cache = summary
    steps_file = bundle_path
    summary_file = summary_path
    step_cursor = 0
    generation_duration = duration
    stop_event.clear()
    pause_event.clear()

    bundle_info = steps_file or "<memoire>"
    summary_info = summary_file or "<memoire>"
    logger.info(
        "Pre-calcul termine : %s steps stockes (simulation=%s, resume=%s, duree=%.3fs).",
        len(precomputed_steps),
        bundle_info,
        summary_info,
        (generation_duration or 0.0),
    )


async def ensure_precomputed(
    websocket: websockets.WebSocketServerProtocol,
    *,
    notify: bool = False,
) -> None:
    """Garantit que les steps sont pre-calcules avant le streaming."""
    global compute_task

    if sim is None:
        await get_world(websocket)

    if precomputed_steps:
        if notify:
            await websocket.send(
                json.dumps(
                    {
                        "type": "status",
                        "data": {
                            "state": "computed",
                            "steps": len(precomputed_steps),
                            "simulation_file": steps_file,
                            "summary_file": summary_file,
                            "duration_sec": generation_duration,
                        },
                    }
                )
            )
        return

    if compute_task is None or compute_task.done():
        if notify:
            await websocket.send(json.dumps({"type": "status", "data": "computing"}))
        compute_task = asyncio.create_task(_compute_steps())
    elif notify:
        await websocket.send(json.dumps({"type": "status", "data": "computing"}))

    try:
        await compute_task
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - diagnostic
        compute_task = None
        message = f"Pre-calcul echoue: {exc}"
        logger.exception(message)
        await websocket.send(json.dumps({"type": "error", "message": message}))
        raise
    else:
        if notify:
            payload = {
                "type": "status",
                "data": {
                    "state": "computed",
                    "steps": len(precomputed_steps),
                    "simulation_file": steps_file,
                    "summary_file": summary_file,
                    "duration_sec": generation_duration,
                },
            }
            await websocket.send(json.dumps(payload))
    finally:
        if compute_task and compute_task.done():
            compute_task = None


async def simulation_runner(websocket: websockets.WebSocketServerProtocol) -> None:
    """Task asynchrone qui envoie un step pre-calcule a la fois."""
    global step_cursor
    logger.info("Simulation pre-calculee en lecture.")
    try:
        while not stop_event.is_set():
            await pause_event.wait()
            if stop_event.is_set():
                break

            if step_cursor >= len(precomputed_steps):
                logger.info("Simulation terminee (tous les steps envoyes).")
                break

            step_data = precomputed_steps[step_cursor]
            step_cursor += 1

            step_num = step_data.get("step")
            logger.info("Step %s : %s", step_num, format_step_summary(step_data))
            await websocket.send(json.dumps({"type": "step", "data": step_data}))

            if tick_ms > 0:
                await asyncio.sleep(tick_ms / 1000.0)

        completed = step_cursor >= len(precomputed_steps)
        if completed and summary_cache is not None:
            summary_payload = dict(summary_cache)
            if generation_duration is not None:
                summary_payload = dict(summary_payload)
                summary_payload["generation_duration_sec"] = generation_duration
            await websocket.send(json.dumps({"type": "summary", "data": summary_payload}))
            logger.info("Resume envoye.")
    except websockets.ConnectionClosed:
        logger.info("Client deconnecte, arret de la simulation.")
    except Exception as exc:
        logger.exception("Erreur dans simulation_runner")
        await websocket.send(json.dumps({"type": "error", "message": str(exc)}))


async def _send_world_snapshot(
    websocket: websockets.WebSocketServerProtocol,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Envoie les metadonnees du monde (et eventuellement le terrain) au client."""
    source: Dict[str, Any] = {}
    if isinstance(payload, dict):
        source = payload

    fallback_world = world if world is not None else World()

    width = _coerce_positive_int(source.get("width")) or getattr(fallback_world, "width", 0)
    height = _coerce_positive_int(source.get("height")) or getattr(fallback_world, "height", 0)
    minutes_per_step = (
        _coerce_positive_int(source.get("minutes_per_step"))
        or getattr(fallback_world, "minutes_per_step", 0)
    )
    food_sources = source.get("food_sources")
    if not isinstance(food_sources, list):
        food_sources = []
    water_sources = source.get("water_sources")
    if not isinstance(water_sources, list):
        water_sources = []

    terrain_rows = source.get("terrain")
    if not isinstance(terrain_rows, list):
        terrain_rows = []

    CHUNK_SIZE = 50
    total_chunks = ceil(len(terrain_rows) / CHUNK_SIZE) if terrain_rows else 0

    await websocket.send(
        json.dumps(
            {
                "type": "world_meta",
                "data": {
                    "width": width,
                    "height": height,
                    "total_chunks": total_chunks,
                    "food_sources": food_sources,
                    "water_sources": water_sources,
                    "minutes_per_step": minutes_per_step,
                },
            }
        )
    )

    if terrain_rows:
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            chunk_rows = terrain_rows[start:end]
            await websocket.send(
                json.dumps(
                    {
                        "type": "terrain_chunk",
                        "data": {
                            "chunk_index": i,
                            "y_start": start,
                            "rows": chunk_rows,
                        },
                    }
                )
            )
            await asyncio.sleep(0.01)

    await websocket.send(json.dumps({"type": "terrain_complete"}))


async def _load_simulation_payload(source: Dict[str, Any], label: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[float], str]:
    """Valide et extrait les steps/summary issus d'une requete rerun."""
    steps_data = source.get("steps")
    if not isinstance(steps_data, list) or not steps_data:
        raise ValueError("rerun : le JSON doit contenir une cle 'steps' non vide.")

    normalized_steps: List[Dict[str, Any]] = []
    for entry in steps_data:
        if isinstance(entry, dict):
            normalized_steps.append(entry)
    if not normalized_steps:
        raise ValueError("rerun : aucun step exploitable dans le JSON fourni.")

    summary_data = source.get("summary") if isinstance(source.get("summary"), dict) else None
    duration = None
    for key in ("generation_duration_sec", "duration_sec", "duration"):
        if key in source:
            try:
                duration = float(source[key])
                break
            except (TypeError, ValueError):
                continue

    return normalized_steps, summary_data, duration, label


async def _handle_rerun_command(
    websocket: websockets.WebSocketServerProtocol,
    obj: Dict[str, Any],
) -> None:
    """Recharge un JSON de simulation et le stream immediatement au client."""
    global precomputed_steps, summary_cache, steps_file, summary_file, step_cursor, generation_duration, runner_task

    target_path = obj.get("path") or obj.get("file") or obj.get("filename")
    payload = obj.get("data") or obj.get("value") or {}
    source_label = "<client>"

    if not isinstance(payload, dict) and target_path:
        try:
            resolved = Path(str(target_path)).expanduser()
            def _read() -> Dict[str, Any]:
                with resolved.open("r", encoding="utf-8") as handle:
                    return json.load(handle)

            payload = await asyncio.to_thread(_read)
            source_label = str(resolved)
        except Exception as exc:  # pragma: no cover - I/O failure path
            message = f"Impossible de lire le fichier de simulation : {exc}"
            logger.exception(message)
            await websocket.send(json.dumps({"type": "error", "message": message}))
            return

    if not isinstance(payload, dict):
        await websocket.send(json.dumps({"type": "error", "message": "rerun : données de simulation manquantes."}))
        return

    try:
        steps, summary, duration, source_label = await _load_simulation_payload(payload, source_label)
    except ValueError as exc:
        await websocket.send(json.dumps({"type": "error", "message": str(exc)}))
        return

    await _cancel_runner_task()
    _reset_runtime_state(clear_events=True)

    precomputed_steps = steps
    summary_cache = summary
    steps_file = source_label
    summary_file = None
    step_cursor = 0
    generation_duration = duration
    stop_event.clear()
    pause_event.clear()

    await _send_world_snapshot(websocket, payload.get("world"))
    await websocket.send(
        json.dumps(
            {
                "type": "status",
                "data": {
                    "state": "computed",
                    "steps": len(precomputed_steps),
                    "simulation_file": steps_file,
                    "summary_file": summary_file,
                    "duration_sec": generation_duration,
                },
            }
        )
    )

    pause_event.set()
    runner_task = asyncio.create_task(simulation_runner(websocket))
    await websocket.send(json.dumps({"type": "status", "data": "started"}))
    logger.info("Commande RERUN executee depuis %s (%s steps).", source_label, len(precomputed_steps))


async def handle_command(websocket: websockets.WebSocketServerProtocol, message: str) -> None:
    """Gere chaque message recu depuis le client."""
    global runner_task, tick_ms, step_cursor

    logger.debug("Commande recue : %s", message)
    try:
        obj = json.loads(message)
    except json.JSONDecodeError:
        obj = {"cmd": message}

    cmd = obj.get("cmd", "")

    if cmd == "get_world":
        await get_world(websocket)
        return

    if cmd == "get_species_catalog":
        await _send_species_catalog(websocket)
        return

    if cmd == "configure_species":
        await _configure_species_selection(websocket, obj)
        return

    if cmd == "get_world_config":
        await _send_world_config(websocket)
        return

    if cmd == "configure_world":
        await _configure_world(websocket, obj)
        return

    if cmd in ("compute", "prepare", "precompute"):
        await ensure_precomputed(websocket, notify=True)
        return

    if cmd in ("start", "start_simulation"):
        if sim is None:
            logger.info("Aucune simulation, creation du monde avant start.")
            await get_world(websocket)
        await ensure_precomputed(websocket)
        if step_cursor >= len(precomputed_steps):
            step_cursor = 0
        stop_event.clear()
        pause_event.set()
        if runner_task is None or runner_task.done():
            runner_task = asyncio.create_task(simulation_runner(websocket))
        await websocket.send(json.dumps({"type": "status", "data": "started"}))
        logger.info("Commande START executee.")
        return

    if cmd == "pause":
        pause_event.clear()
        await websocket.send(json.dumps({"type": "status", "data": "paused"}))
        logger.info("Simulation mise en pause.")
        return

    if cmd == "resume":
        pause_event.set()
        await websocket.send(json.dumps({"type": "status", "data": "resumed"}))
        logger.info("Simulation reprise.")
        return

    if cmd == "stop":
        stop_event.set()
        pause_event.set()
        step_cursor = 0
        await websocket.send(json.dumps({"type": "status", "data": "stopped"}))
        logger.info("Simulation arretee.")
        return

    if cmd == "rerun":
        await _handle_rerun_command(websocket, obj)
        return

    if cmd == "speed":
        value = obj.get("value")
        if isinstance(value, (int, float)) and value >= 0:
            tick_ms = int(value)
            await websocket.send(json.dumps({"type": "status", "data": f"speed={tick_ms}ms"}))
            logger.info("Vitesse modifiee : %sms/step", tick_ms)
        else:
            await websocket.send(json.dumps({"type": "error", "message": "invalid speed"}))
            logger.warning("Mauvaise valeur speed recue.")
        return

    await websocket.send(json.dumps({"type": "error", "message": "Unknown command"}))
    logger.warning("Commande inconnue : %s", cmd)


async def handler(websocket: websockets.WebSocketServerProtocol) -> None:
    pause_event.clear()
    stop_event.clear()
    client = websocket.remote_address
    logger.info("Nouveau client connecte : %s", client)
    try:
        async for message in websocket:
            await handle_command(websocket, message)
    except websockets.ConnectionClosed:
        logger.info("Client deconnecte : %s", client)


def _addr_in_use_codes() -> Tuple[int, ...]:
    codes = [errno.EADDRINUSE]
    if hasattr(errno, "WSAEADDRINUSE"):
        codes.append(errno.WSAEADDRINUSE)
    return tuple(codes)


async def _bind_websocket_server() -> Tuple[Any, int]:
    settings = DEFAULT_SETTINGS
    addr_in_use = _addr_in_use_codes()
    last_error: Optional[OSError] = None

    for offset in range(max(1, settings.port_scan_limit)):
        port = settings.port + offset
        try:
            server = await websockets.serve(
                handler,
                settings.host,
                port,
                max_size=1_000_000_000,  # autorise l'import de simulations volumineuses (~1Go)
            )
            if offset > 0:
                logger.info(
                    "Port %s indisponible, utilisation du port %s.",
                    settings.port,
                    port,
                )
            return server, port
        except OSError as exc:
            if exc.errno in addr_in_use:
                logger.info(
                    "Port %s deja utilise (%s/%s).",
                    port,
                    offset + 1,
                    settings.port_scan_limit,
                )
                last_error = exc
                continue
            raise

    raise RuntimeError("Impossible de trouver un port libre pour le serveur WebSocket.") from last_error


async def main() -> None:
    server, bound_port = await _bind_websocket_server()
    async with server:
        logger.info(
            "WebSocket server running on ws://%s:%s",
            DEFAULT_SETTINGS.host,
            bound_port,
        )
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    asyncio.run(main())
