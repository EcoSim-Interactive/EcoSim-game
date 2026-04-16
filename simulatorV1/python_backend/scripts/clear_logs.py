"""Script utilitaire pour nettoyer les journaux generes dans le workspace."""
from __future__ import annotations

import logging
import os
import shutil
from typing import Iterable


logger = logging.getLogger(__name__)


def delete_logs_dirs(base_path: str = ".") -> int:
    """Supprime recursivement tous les dossiers `logs` sous le chemin donne."""

    deleted = 0
    for root, dirs, _ in os.walk(base_path):
        for directory in dirs:
            if directory == "logs":
                full_path = os.path.join(root, directory)
                logger.info("Suppression de : %s", full_path)
                shutil.rmtree(full_path, ignore_errors=True)
                deleted += 1
    if deleted == 0:
        logger.info("Aucun dossier 'logs' trouve.")
    else:
        logger.info("%s dossier(s) 'logs' supprime(s).", deleted)
    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, force=True)
    delete_logs_dirs()
