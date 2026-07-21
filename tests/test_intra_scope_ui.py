from __future__ import annotations

import unittest

import pandas as pd

from config import get_disease_generation_config
from disease_vocabulary import ALL_LOADED_MODE
from render.intra_analysis_view import (
    clear_generation_results,
    refresh_disease_controls,
    refresh_project_scope_controls,
    update_generation_mode_controls,
)

ICDC_CONFIG = get_disease_generation_config("ICDC")
assert ICDC_CONFIG is not None
DISEASE_SPECIFIC_MODE = ICDC_CONFIG.disease_specific_mode


class IntraScopeUiTests(unittest.TestCase):
    def test_data_refresh_rebuilds_choices_and_clears_old_results(self):
        data_state = {
            "diagnosis": pd.DataFrame(
                {"disease_term": ["Glioma", "Unknown", "Mammary Cancer"]}
            )
        }

        output = refresh_disease_controls(
            data_state,
            "ICDC",
            DISEASE_SPECIFIC_MODE,
        )

        self.assertEqual(output[0]["choices"], ["Glioma", "Mammary Cancer"])
        self.assertIsNone(output[0]["value"])
        self.assertIn("Glioma", output[1])
        self.assertIn("Loaded data changed", output[2])
        self.assertIn("No generated data", output[4])

    def test_all_loaded_mode_hides_and_clears_disease_selection(self):
        output = update_generation_mode_controls(ALL_LOADED_MODE, "ICDC")

        self.assertFalse(output[0]["visible"])
        self.assertIsNone(output[0]["value"])
        self.assertIn("not be treated as disease-specific", output[1])

    def test_disease_mode_shows_disease_selection(self):
        output = update_generation_mode_controls(DISEASE_SPECIFIC_MODE, "ICDC")

        self.assertTrue(output[0]["visible"])
        self.assertTrue(output[0]["interactive"])

    def test_scope_changes_clear_previous_generated_output(self):
        output = clear_generation_results(DISEASE_SPECIFIC_MODE, "ICDC")

        self.assertIn("selection changed", output[0])
        self.assertIn("No generated data", output[2])

    def test_unconfigured_project_exposes_only_all_loaded_mode(self):
        output = refresh_project_scope_controls("CDS", {})

        self.assertEqual(output[0]["choices"], [ALL_LOADED_MODE])
        self.assertFalse(output[1]["visible"])
        self.assertIn("Not configured", output[2])


if __name__ == "__main__":
    unittest.main()
