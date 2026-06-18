import unittest
import json
from pathlib import Path
from unittest.mock import patch

from app.world_loader import (
    load_world,
    load_world_and_species,
    _resolve_config_path,
    _coerce_float,
    _coerce_bool,
    _positive_int,
    _positive_float
)

class TestWorldLoader(unittest.TestCase):
    def test_coerce_float(self):
        self.assertEqual(_coerce_float(5), 5.0)
        self.assertEqual(_coerce_float("3.14"), 3.14)
        self.assertIsNone(_coerce_float("abc"))
        self.assertIsNone(_coerce_float(None))

    def test_coerce_bool(self):
        self.assertTrue(_coerce_bool(True))
        self.assertTrue(_coerce_bool("yes"))
        self.assertTrue(_coerce_bool("1"))
        self.assertFalse(_coerce_bool("0"))
        self.assertFalse(_coerce_bool("false"))
        self.assertIsNone(_coerce_bool("maybe"))

    def test_positive_int(self):
        self.assertEqual(_positive_int(5), 5)
        self.assertEqual(_positive_int("10"), 10)
        self.assertIsNone(_positive_int(-5))
        self.assertIsNone(_positive_int("abc"))

    def test_positive_float(self):
        self.assertEqual(_positive_float(5.5), 5.5)
        self.assertIsNone(_positive_float(-2.0))
        self.assertIsNone(_positive_float("foo"))

    @patch('app.world_loader.load_config')
    def test_load_world_fallback_on_error(self, mock_load_config):
        mock_load_config.side_effect = FileNotFoundError("Not found")
        world = load_world(fallback_food=50, fallback_water=20)
        
        self.assertTrue(len(world.food_sources) > 0)
        self.assertTrue(len(world.water_sources) > 0)

    @patch('app.world_loader.load_config')
    def test_load_world_and_species_fallback(self, mock_load_config):
        mock_load_config.side_effect = json.JSONDecodeError("Error", "", 0)
        world, species = load_world_and_species(fallback_food=10, fallback_water=5)
        
        self.assertTrue(len(world.food_sources) > 0)
        self.assertTrue(len(world.water_sources) > 0)
        self.assertGreater(len(species), 0)
        self.assertEqual(species[0].species_type, "Chasseron")

    def test_resolve_config_path_absolute(self):
        abs_path = Path("/tmp/some_config.json").resolve()
        resolved = _resolve_config_path(str(abs_path))
        self.assertEqual(resolved, abs_path)

if __name__ == '__main__':
    unittest.main()
