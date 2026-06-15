from __future__ import annotations

import itertools
import random
import unittest
from pathlib import Path

from app.main import parse_args
from app.world_loader import load_world_and_species
from domain import World
from simulation import SimulationEngine
from simulation.action_executor import resolve_consumption
from simulation.actions.grouping import maintain_group_cohesion
from simulation.actions.predation import _nearest_prey, execute_predation_cycle
from simulation.actions.scavenging import seek_carcass_opportunity
from simulation.ai.behavior import handle_thirst
from simulation.ai.decision import process_species
from simulation.ai.relationships import handle_species_relationships
from simulation.animal import Animal
from simulation.step_context import finalize_species_status, initialize_species_status


def _build_hunter(
    name: str,
    position: tuple[float, float],
    *,
    pack_id: str,
    role: str,
    feed_priority: float,
    wait_for_priorities: list[float] | None = None,
) -> Animal:
    """Construit rapidement un carnivore de test avec une configuration de chasse simple."""

    hunt_cfg = {
        "attack_range": 40,
        "chase_range": 200,
        "success_rate": 1.0,
        "pack_bonus": 0.0,
        "feed_priority": feed_priority,
        "targets": ["gazelle"],
    }
    if wait_for_priorities is not None:
        hunt_cfg["wait_for_priorities"] = list(wait_for_priorities)
    animal = Animal(
        name=name,
        position=position,
        speed=12,
        vision=250,
        smell_range=250,
        diet="carnivore",
        species_type="lion",
        pack_id=pack_id,
        group_id=pack_id,
        traits={
            "role": role,
            "feed_priority": feed_priority,
            "hunt": hunt_cfg,
        },
    )
    animal.hunger = 60.0
    return animal


class PackAITestCase(unittest.TestCase):
    """Verifie les scenarios critiques de coordination de meute."""

    def setUp(self) -> None:
        Animal.reset_shared_states()
        Animal._id_sequence = itertools.count(1)

    def test_cli_parses_optional_seed(self) -> None:
        args = parse_args(["--steps", "12", "--seed", "42"])

        self.assertEqual(args.steps, 12)
        self.assertEqual(args.seed, 42)

    def test_target_filter_keeps_requested_species(self) -> None:
        world = World(width=300, height=300)
        hunter = _build_hunter("Lion", (0.0, 0.0), pack_id="pride", role="hunter", feed_priority=30)
        gazelle = Animal("Gazelle", (60.0, 0.0), diet="herbivore", species_type="gazelle")
        elephant = Animal("Elephant", (10.0, 0.0), diet="herbivore", species_type="elephant")

        prey = _nearest_prey(hunter, [gazelle, elephant], {"gazelle"}, world)

        self.assertIs(prey, gazelle)

    def test_same_priority_pack_members_can_all_feed(self) -> None:
        world = World(width=300, height=300)
        prey = Animal("Gazelle", (100.0, 100.0), diet="herbivore", species_type="gazelle", body_nutrition=220.0)
        carcass = world.add_carcass(prey)

        leader = _build_hunter("Leader", (100.0, 100.0), pack_id="pride", role="leader", feed_priority=10)
        hunter_a = _build_hunter(
            "HunterA",
            (100.0, 100.0),
            pack_id="pride",
            role="hunter",
            feed_priority=30,
            wait_for_priorities=[10],
        )
        hunter_b = _build_hunter(
            "HunterB",
            (100.0, 100.0),
            pack_id="pride",
            role="hunter",
            feed_priority=30,
            wait_for_priorities=[10],
        )
        pack_kill = leader.pack_state.setdefault("shared_kill", {})
        pack_kill.update(
            {
                "food_id": carcass["id"],
                "position": (carcass["x"], carcass["y"]),
                "originator": leader.animal_id,
                "fed_animals": set(),
                "fed_priorities": set(),
                "blocked": set(),
                "participants": {},
                "wait_counters": {},
                "stale_steps": 0,
                "feed_log": [],
            }
        )
        animals = [leader, hunter_a, hunter_b]

        for animal in animals:
            acted, _, resolve_food = execute_predation_cycle(animal, animals, world, lambda _msg: None)
            self.assertTrue(acted)
            self.assertTrue(resolve_food)
            result = resolve_consumption(world, animal, lambda _msg: None)
            self.assertIsNotNone(result["food_event"])

        fed_animals = leader.pack_state["shared_kill"]["fed_animals"]
        self.assertSetEqual(fed_animals, {leader.animal_id, hunter_a.animal_id, hunter_b.animal_id})

    def test_pack_members_follow_shared_target(self) -> None:
        world = World(width=400, height=400)
        leader = _build_hunter("Leader", (0.0, 0.0), pack_id="pride", role="leader", feed_priority=10)
        hunter = _build_hunter("Hunter", (0.0, 50.0), pack_id="pride", role="hunter", feed_priority=30)
        gazelle_primary = Animal("GazelleA", (100.0, 0.0), diet="herbivore", species_type="gazelle")
        gazelle_secondary = Animal("GazelleB", (0.0, 120.0), diet="herbivore", species_type="gazelle")
        animals = [leader, hunter, gazelle_primary, gazelle_secondary]

        acted, action, _ = execute_predation_cycle(leader, animals, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertIn(action, {"pack_tracking_prey", "pack_closing_distance"})
        shared_target = leader.pack_state.get("shared_target")
        self.assertIsNotNone(shared_target)
        self.assertEqual(shared_target["prey_id"], gazelle_primary.animal_id)

        acted, action, _ = execute_predation_cycle(hunter, animals, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertIn(action, {"pack_tracking_prey", "pack_closing_distance"})
        self.assertGreater(hunter.x, 0.0)
        self.assertLess(hunter.y, 50.0)

    def test_hunt_creates_shared_kill_and_packmate_eats(self) -> None:
        world = World(width=200, height=200)
        leader = _build_hunter("Leader", (100.0, 100.0), pack_id="pride", role="leader", feed_priority=10)
        hunter = _build_hunter(
            "Hunter",
            (110.0, 100.0),
            pack_id="pride",
            role="hunter",
            feed_priority=30,
            wait_for_priorities=[10],
        )
        prey = Animal("Gazelle", (112.0, 100.0), diet="herbivore", species_type="gazelle", body_nutrition=180.0)
        animals = [leader, hunter, prey]

        acted, action, resolve_food = execute_predation_cycle(leader, animals, world, lambda _msg: None)

        self.assertTrue(acted)
        self.assertEqual(action, "pack_hunt_success")
        self.assertFalse(prey.alive)
        self.assertIn("shared_kill", leader.pack_state)
        if resolve_food:
            result = resolve_consumption(world, leader, lambda _msg: None)
            self.assertIsNotNone(result["food_event"])

        acted, action, resolve_food = execute_predation_cycle(hunter, animals, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertEqual(action, "pack_feed_from_carcass")
        self.assertTrue(resolve_food)
        result = resolve_consumption(world, hunter, lambda _msg: None)
        self.assertIsNotNone(result["food_event"])

    def test_engine_clears_stale_shared_state(self) -> None:
        Animal.pack_state_for("stale_pride")["shared_kill"] = {"food_id": "stale"}
        world = World(width=200, height=200)
        animal = _build_hunter("Leader", (20.0, 20.0), pack_id="stale_pride", role="leader", feed_priority=10)

        engine = SimulationEngine(world, [animal], steps=1, verbose=False)

        self.assertEqual(engine.species_list[0].pack_state, {})

    def test_blocked_thirst_does_not_fake_move_to_water(self) -> None:
        class BlockedWaterWorld:
            width = 100
            height = 100
            minutes_per_step = 60
            water_sources = []

            @staticmethod
            def find_shore_tile(_x, _y, _radius, min_radius=0):
                if min_radius > 0:
                    return None
                return (10.0, 0.0)

            @staticmethod
            def can_entity_enter(_entity, _x, _y):
                return False

        animal = Animal("Gazelle", (0.0, 0.0), speed=10, vision=30, smell_range=30, diet="herbivore")

        acted, action, _ = handle_thirst(animal, BlockedWaterWorld(), lambda _msg: None)

        self.assertFalse(acted)
        self.assertEqual(action, "")
        self.assertEqual((animal.x, animal.y), (0.0, 0.0))

    def test_blocked_group_avoidance_does_not_report_fake_action(self) -> None:
        class TrappedWorld:
            width = 100
            height = 100
            minutes_per_step = 60

            @staticmethod
            def can_entity_enter(_entity, _x, _y):
                return False

        leader = Animal("GazelleA", (10.0, 10.0), speed=8, diet="herbivore")
        follower = Animal("GazelleB", (12.0, 10.0), speed=8, diet="herbivore")

        acted, action = maintain_group_cohesion(leader, [leader, follower], TrappedWorld(), spacing=20.0)

        self.assertFalse(acted)
        self.assertEqual(action, "")
        self.assertEqual((leader.x, leader.y), (10.0, 10.0))

    def test_relationships_prioritize_hunt_before_territory(self) -> None:
        world = World(width=300, height=300)
        hunter = _build_hunter("Leader", (95.0, 100.0), pack_id="pride", role="leader", feed_priority=10)
        hunter.set_trait("territory", {"center": (100.0, 100.0), "radius": 12.0, "margin": 6.0})
        prey = Animal("Gazelle", (120.0, 100.0), diet="herbivore", species_type="gazelle")

        acted, action, motivation, _ = handle_species_relationships(
            hunter,
            [hunter, prey],
            world,
            lambda _msg: None,
        )

        self.assertTrue(acted)
        self.assertIn(action, {"pack_closing_distance", "pack_hunt_success", "pack_tracking_prey"})
        self.assertEqual(motivation, "coordination de chasse")

    def test_relationships_suspend_territory_when_hunger_is_critical(self) -> None:
        world = World(width=300, height=300)
        animal = Animal("Gazelle", (150.0, 100.0), speed=8, diet="herbivore", species_type="gazelle")
        animal.set_trait("territory", {"center": (100.0, 100.0), "radius": 20.0, "margin": 5.0})
        animal.hunger = 90.0

        acted, action, _, _ = handle_species_relationships(
            animal,
            [animal],
            world,
            lambda _msg: None,
        )

        self.assertFalse(acted)
        self.assertEqual(action, "")

    def test_relationships_suspend_territory_while_water_target_is_active(self) -> None:
        world = World(width=300, height=300)
        animal = Animal("Gazelle", (150.0, 100.0), speed=8, diet="herbivore", species_type="gazelle")
        animal.set_trait("territory", {"center": (100.0, 100.0), "radius": 20.0, "margin": 5.0})
        animal.remember_water(40.0, 40.0)
        animal.remember_water_target(45.0, 45.0)

        acted, action, _, _ = handle_species_relationships(
            animal,
            [animal],
            world,
            lambda _msg: None,
        )

        self.assertFalse(acted)
        self.assertEqual(action, "")

    def test_engine_logs_terminal_snapshot_for_prey_killed_mid_step(self) -> None:
        world = World(width=200, height=200)
        hunter = _build_hunter("Leader", (100.0, 100.0), pack_id="pride", role="leader", feed_priority=10)
        hunter.diurnal = False
        prey = Animal("Gazelle", (105.0, 100.0), diet="herbivore", species_type="gazelle", body_nutrition=140.0)

        engine = SimulationEngine(world, [hunter, prey], steps=1, verbose=False)
        step = engine.step_once()

        self.assertIsNotNone(step)
        prey_status = next(item for item in step["species"] if item["animal_id"] == prey.animal_id)
        self.assertEqual(prey_status["action"], "killed_by_predation")
        self.assertFalse(prey_status["after"]["alive"])
        self.assertEqual(prey_status["after"]["vitality"], 0.0)

    def test_thirst_drinks_immediately_when_already_on_shore(self) -> None:
        world = World(width=20, height=20)
        world._register_water_source(5.0, 5.0, water_type="stagnant", capacity=None, max_capacity=None)
        animal = Animal("Gazelle", (4.0, 5.0), speed=4, vision=20, smell_range=20, diet="herbivore")
        animal.thirst = 40.0

        acted, action, motivation = handle_thirst(animal, world, lambda _msg: None)

        self.assertTrue(acted)
        self.assertEqual(action, "drink")
        self.assertIn("rive atteinte", motivation)
        self.assertLess(animal.thirst, 40.0)

    def test_thirst_reuses_memorized_drink_target(self) -> None:
        class StableWaterWorld:
            width = 50
            height = 50
            minutes_per_step = 5

            def __init__(self) -> None:
                self.water = {"id": "water_1", "x": 10.0, "y": 0.0}
                self.water_sources = [self.water]
                self.find_drink_target_calls = 0

            def get_nearest_water(self, _x, _y):
                return self.water

            @staticmethod
            def distance_to_water(x, y, water):
                return ((x - water["x"]) ** 2 + (y - water["y"]) ** 2) ** 0.5

            def find_drink_target(self, _x, _y, _water, *, entity=None, search_radius=40):
                self.find_drink_target_calls += 1
                return (4.0, 0.0) if self.find_drink_target_calls == 1 else (12.0, 0.0)

            @staticmethod
            def can_entity_enter(_entity, _x, _y):
                return True

            @staticmethod
            def water_has_supply(_water):
                return True

            @staticmethod
            def consume_water(_water, amount=10.0):
                return True

        world = StableWaterWorld()
        animal = Animal("Lion", (0.0, 0.0), speed=2, vision=30, smell_range=30, diet="carnivore")
        animal.thirst = 40.0

        acted, action, _ = handle_thirst(animal, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertEqual(action, "move_to_water")
        self.assertEqual(world.find_drink_target_calls, 1)
        self.assertEqual(animal.recall_water_target(), (4.0, 0.0))

        acted, action, motivation = handle_thirst(animal, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertEqual(action, "move_to_known_water")
        self.assertEqual(motivation, "soif (cible memorisee)")
        self.assertEqual(world.find_drink_target_calls, 1)
        self.assertEqual(animal.recall_water_target(), (4.0, 0.0))

    def test_find_drink_target_prefers_same_shore_side(self) -> None:
        world = World(width=30, height=30)
        for wx in range(10, 13):
            for wy in range(10, 13):
                world._register_water_source(float(wx), float(wy), water_type="lake", capacity=None, max_capacity=None)
        animal = Animal("Gazelle", (7.0, 11.0), speed=4, vision=20, smell_range=20, diet="herbivore")

        target = world.find_drink_target(animal.x, animal.y, {"x": 11.0, "y": 11.0}, entity=animal)

        self.assertLessEqual(target[0], 9.0)
        self.assertTrue(world._has_water_neighbor(int(target[0]), int(target[1])))

    def test_find_drink_target_cache_rebuilds_after_new_water_tiles(self) -> None:
        world = World(width=30, height=30)
        world._register_water_source(10.0, 10.0, water_type="lake", capacity=None, max_capacity=None, body_id="body_1")
        initial_target = world.find_drink_target(7.0, 10.0, {"body_id": "body_1", "x": 10.0, "y": 10.0})

        world._register_water_source(10.0, 11.0, water_type="lake", capacity=None, max_capacity=None, body_id="body_1")
        world._register_water_source(11.0, 10.0, water_type="lake", capacity=None, max_capacity=None, body_id="body_1")
        world._register_water_source(11.0, 11.0, water_type="lake", capacity=None, max_capacity=None, body_id="body_1")
        rebuilt_target = world.find_drink_target(7.0, 10.0, {"body_id": "body_1", "x": 10.0, "y": 10.0})

        self.assertTrue(world._has_water_neighbor(int(initial_target[0]), int(initial_target[1])))
        self.assertTrue(world._has_water_neighbor(int(rebuilt_target[0]), int(rebuilt_target[1])))

    def test_thirst_recomputes_when_stale_water_target_is_already_reached(self) -> None:
        class RecomputeWaterWorld:
            width = 50
            height = 50
            minutes_per_step = 5

            def __init__(self) -> None:
                self.water = {"id": "water_1", "x": 10.0, "y": 0.0}
                self.water_sources = [self.water]
                self.find_drink_target_calls = 0

            def get_nearest_water(self, _x, _y):
                return self.water

            @staticmethod
            def distance_to_water(x, y, water):
                return ((x - water["x"]) ** 2 + (y - water["y"]) ** 2) ** 0.5

            def find_drink_target(self, _x, _y, _water, *, entity=None, search_radius=40):
                self.find_drink_target_calls += 1
                return (6.0, 0.0)

            @staticmethod
            def can_entity_enter(_entity, _x, _y):
                return True

            @staticmethod
            def water_has_supply(_water):
                return True

            @staticmethod
            def consume_water(_water, amount=10.0):
                return True

        world = RecomputeWaterWorld()
        animal = Animal("Gazelle", (4.0, 0.0), speed=2, vision=30, smell_range=30, diet="herbivore")
        animal.thirst = 40.0
        animal.remember_water(10.0, 0.0)
        animal.remember_water_target(4.0, 0.0)

        acted, action, motivation = handle_thirst(animal, world, lambda _msg: None)

        self.assertTrue(acted)
        self.assertEqual(action, "drink")
        self.assertEqual(motivation, "soif (vue)")
        self.assertEqual(world.find_drink_target_calls, 1)

    def test_hunger_property_maps_to_calorie_reserve(self) -> None:
        animal = Animal(
            "Gazelle",
            (0.0, 0.0),
            diet="herbivore",
            traits={"metabolism": {"daily_calorie_need": 2000, "reserve_days": 4, "meal_calories": 500}},
        )

        animal.hunger = 25.0

        self.assertAlmostEqual(animal.max_calories, 8000.0)
        self.assertAlmostEqual(animal.calories, 6000.0)
        self.assertAlmostEqual(animal.hunger, 25.0)

    def test_try_eat_restores_calories_without_exceeding_meal_cap(self) -> None:
        world = World(width=100, height=100)
        animal = Animal(
            "Gazelle",
            (10.0, 10.0),
            diet="herbivore",
            traits={"metabolism": {"daily_calorie_need": 2000, "reserve_days": 4, "meal_calories": 500}},
        )
        animal.hunger = 50.0
        before_calories = animal.calories
        world._register_food_source(10.0, 10.0, food_type="herbs", nutrition=1500.0, metadata=None, food_class="plant")

        result = animal.try_eat(world)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["consumed"], 500.0)
        self.assertAlmostEqual(animal.calories, before_calories + 500.0)
        self.assertAlmostEqual(animal.hunger, 43.75)

    def test_step_status_exposes_calories(self) -> None:
        animal = Animal(
            "Lion",
            (5.0, 5.0),
            diet="carnivore",
            traits={"metabolism": {"daily_calorie_need": 3000, "reserve_days": 5, "meal_calories": 700}},
        )
        animal.hunger = 20.0

        status = initialize_species_status(animal)
        finalized = finalize_species_status(animal, status)

        self.assertIn("calories", finalized["before"])
        self.assertIn("calories", finalized["after"])
        self.assertAlmostEqual(finalized["after"]["calories"], animal.calories)

    def test_carcass_keeps_link_to_killed_animal(self) -> None:
        world = World(width=100, height=100)
        prey = Animal(
            "Gazelle",
            (25.0, 40.0),
            diet="herbivore",
            species_type="gazelle",
            traits={
                "sex": "male",
                "age_stage": "adult",
                "metabolism": {
                    "body_mass_kg": 24,
                    "carcass_edible_ratio": 0.58,
                    "carcass_calories_per_kg": 1400,
                    "sex_mass_scale": {"male": 1.15, "female": 1.0},
                    "age_stage_mass_scale": {"adult": 1.0},
                },
            },
        )

        carcass = world.add_carcass(prey)

        self.assertEqual(carcass["source_animal_id"], prey.animal_id)
        self.assertEqual(carcass["source_species_type"], "gazelle")
        self.assertEqual(carcass["source_original_name"], prey.original_name)
        self.assertTrue(str(carcass["id"]).startswith(f"carcass_{prey.animal_id}_"))
        self.assertAlmostEqual(carcass["source_body_mass_kg"], 27.6)
        self.assertAlmostEqual(carcass["calories"], prey.estimate_carcass_calories())
        self.assertEqual(carcass["metadata"]["source_animal_id"], prey.animal_id)

    def test_body_profile_scales_carcass_by_age_stage(self) -> None:
        juvenile = Animal(
            "Gazelle",
            (0.0, 0.0),
            diet="herbivore",
            traits={
                "sex": "female",
                "age_stage": "juvenile",
                "metabolism": {
                    "body_mass_kg": 24,
                    "carcass_edible_ratio": 0.58,
                    "carcass_calories_per_kg": 1400,
                    "age_stage_mass_scale": {"juvenile": 0.45, "adult": 1.0},
                },
            },
        )
        adult = Animal(
            "Gazelle",
            (0.0, 0.0),
            diet="herbivore",
            traits={
                "sex": "female",
                "age_stage": "adult",
                "metabolism": {
                    "body_mass_kg": 24,
                    "carcass_edible_ratio": 0.58,
                    "carcass_calories_per_kg": 1400,
                    "age_stage_mass_scale": {"juvenile": 0.45, "adult": 1.0},
                },
            },
        )

        self.assertLess(juvenile.body_mass_kg, adult.body_mass_kg)
        self.assertLess(juvenile.body_nutrition, adult.body_nutrition)

    def test_active_shared_kill_overrides_cycle_rest(self) -> None:
        class SilentLogger:
            def log(self, _message: str) -> None:
                return

        world = World(width=200, height=200)
        leader = _build_hunter("Leader", (100.0, 100.0), pack_id="pride", role="leader", feed_priority=10)
        hunter = _build_hunter(
            "Hunter",
            (110.0, 100.0),
            pack_id="pride",
            role="hunter",
            feed_priority=30,
            wait_for_priorities=[10],
        )
        prey = Animal("Gazelle", (112.0, 100.0), diet="herbivore", species_type="gazelle", body_nutrition=180.0)
        animals = [leader, hunter, prey]

        acted, action, _ = execute_predation_cycle(leader, animals, world, lambda _msg: None)
        self.assertTrue(acted)
        self.assertEqual(action, "pack_hunt_success")

        status = initialize_species_status(hunter)
        process_species(
            hunter,
            status,
            {"hour": 2, "minute": 0, "is_day": False, "minutes_per_step": 5},
            world,
            [leader, hunter],
            SilentLogger(),
        )

        self.assertNotEqual(status["action"], "resting_cycle")
        self.assertIn(status["action"], {"pack_feed_from_carcass_and_ate", "pack_move_to_carcass", "pack_waiting_move", "pack_waiting_guard", "pack_feed_from_carcass"})

    def test_process_species_prioritizes_critical_hunger_before_moderate_thirst(self) -> None:
        class SilentLogger:
            def log(self, _message: str) -> None:
                return

        world = World(width=120, height=120)
        world._register_food_source(20.0, 10.0, food_type="herbs", nutrition=5000.0, metadata=None, food_class="plant")
        animal = Animal("Gazelle", (10.0, 10.0), speed=6, vision=40, smell_range=40, diet="herbivore", species_type="gazelle")
        animal.hunger = 95.0
        animal.thirst = 30.0

        status = initialize_species_status(animal)
        process_species(
            animal,
            status,
            {"hour": 12, "minute": 0, "is_day": True, "minutes_per_step": 5},
            world,
            [animal],
            SilentLogger(),
        )

        self.assertIn(status["action"], {"move_to_seen_food", "move_to_seen_food_and_ate"})

    def test_scavenger_blocks_shared_carcass_after_repeated_failures(self) -> None:
        world = World(width=200, height=200)
        carcass = world._register_food_source(
            120.0,
            120.0,
            food_id="carcass_test",
            food_type="carcass",
            nutrition=5000.0,
            metadata=None,
            food_class="meat",
        )
        scout = Animal(
            "Hyene",
            (20.0, 20.0),
            speed=10,
            vision=120,
            smell_range=200,
            diet="carnivore",
            species_type="hyene",
            traits={"scavenger": {"follow_packs": ["pride"], "hunger_threshold": 15}},
        )
        scout.hunger = 100.0
        scout.move_towards = lambda _target, _world=None: False
        scout.random_move = lambda _world=None: True
        shared = Animal.pack_state_for("pride").setdefault("shared_kill", {})
        shared.clear()
        shared.update(
            {
                "food_id": carcass["id"],
                "position": (carcass["x"], carcass["y"]),
                "blocked": set(),
                "fed_animals": set(),
                "participants": {scout.animal_id: 30.0},
            }
        )

        for _ in range(3):
            acted, action, resolve = seek_carcass_opportunity(scout, world)
            self.assertTrue(acted)
            self.assertEqual(action, "scavenge_reposition")
            self.assertFalse(resolve)

        acted, action, resolve = seek_carcass_opportunity(scout, world)
        self.assertFalse(acted)
        self.assertEqual(action, "")
        self.assertFalse(resolve)
        self.assertTrue(shared == {} or scout.animal_id in shared.get("blocked", set()))

    def test_same_seed_reproduces_same_summary(self) -> None:
        config_path = Path(__file__).resolve().parents[1] / "app" / "world_config.json"

        def _run_once(seed: int):
            random.seed(seed)
            Animal.reset_shared_states()
            Animal._id_sequence = itertools.count(1)
            world, species = load_world_and_species(str(config_path))
            simulation = SimulationEngine(world, species, steps=20, verbose=False, seed=seed)
            simulation.run()
            return simulation.save_summary()

        summary_a = _run_once(1234)
        summary_b = _run_once(1234)

        self.assertEqual(summary_a, summary_b)
        self.assertEqual(summary_a.get("seed"), 1234)


if __name__ == "__main__":
    unittest.main()
