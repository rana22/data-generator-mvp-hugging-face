from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from config import get_disease_generation_config
from render.inter_analysis_view import (
    compute_cross_node_analysis,
    create_cross_node_data,
    generate_cross_node_data,
    run_cross_analysis_for_mode,
)

ICDC_CONFIG = get_disease_generation_config("ICDC")
assert ICDC_CONFIG is not None
DISEASE_SPECIFIC_MODE = ICDC_CONFIG.disease_specific_mode


class CrossNodeScopeTests(unittest.TestCase):
    @patch("render.inter_analysis_view.run_cross_analysis")
    def test_cross_analysis_is_declined_outside_all_loaded_mode(self, run_analysis):
        output = run_cross_analysis_for_mode(
            {}, [], {}, [], [], DISEASE_SPECIFIC_MODE
        )

        run_analysis.assert_not_called()
        self.assertEqual(len(output), 6)
        self.assertIn("all loaded source data only", output[2])

    @patch("render.inter_analysis_view.CrossNodeDataGenerator")
    def test_cross_edge_generation_is_declined_before_generator_construction(self, generator):
        output = generate_cross_node_data(
            {}, pd.DataFrame(), [], DISEASE_SPECIFIC_MODE
        )

        generator.assert_not_called()
        self.assertEqual(len(output), 4)
        self.assertIn("all loaded source data only", output[3])

    @patch("render.inter_analysis_view.PairwiseRelationshipEvaluator")
    def test_combined_analysis_is_declined_before_evaluator_construction(self, evaluator):
        output = compute_cross_node_analysis(
            {}, [], [], {}, pd.DataFrame(), pd.DataFrame(), DISEASE_SPECIFIC_MODE
        )

        evaluator.assert_not_called()
        self.assertEqual(len(output), 4)
        self.assertIn("all loaded source data only", output[3])

    @patch("render.inter_analysis_view.SyntheticDataGenerator")
    def test_combined_generation_is_declined_before_generator_construction(self, generator):
        output = create_cross_node_data(
            [], {}, {}, [], pd.DataFrame(), DISEASE_SPECIFIC_MODE
        )

        generator.assert_not_called()
        self.assertEqual(len(output), 3)
        self.assertIn("all loaded source data only", output[2])


if __name__ == "__main__":
    unittest.main()
