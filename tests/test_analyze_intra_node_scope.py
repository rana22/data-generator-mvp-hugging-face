from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from analyze.intra_node import run_intra_node_analysis as _run_intra_node_analysis
from config import get_disease_generation_config

ICDC_CONFIG = get_disease_generation_config("ICDC")
assert ICDC_CONFIG is not None
DISEASE_SPECIFIC_MODE = ICDC_CONFIG.disease_specific_mode


def run_intra_node_analysis(*args, **kwargs):
    kwargs.setdefault("selected_project", "ICDC")
    return _run_intra_node_analysis(*args, **kwargs)


class AnalyzeIntraNodeScopeTests(unittest.TestCase):
    @patch("analyze.intra_node.PairwiseRelationshipEvaluator")
    def test_unsupported_request_does_not_run_relationship_analysis(self, evaluator):
        data_state = {
            "diagnosis": pd.DataFrame(
                {"disease_term": ["Glioma"] * 5, "stage": list(range(5))}
            )
        }

        output = run_intra_node_analysis(
            {},
            [SimpleNamespace(name="diagnosis")],
            data_state,
            "diagnosis",
            DISEASE_SPECIFIC_MODE,
            "Sarcoma",
        )

        evaluator.assert_not_called()
        self.assertEqual(len(output), 4)
        self.assertIn("Sarcoma", output[2])

    @patch("analyze.intra_node.PairwiseRelationshipEvaluator")
    def test_unscopable_request_does_not_run_relationship_analysis(self, evaluator):
        data_state = {
            "diagnosis": pd.DataFrame({"disease_term": ["Glioma"] * 5}),
            "sample": pd.DataFrame({"sample_site": ["Brain"] * 10}),
        }

        output = run_intra_node_analysis(
            {},
            [SimpleNamespace(name="sample")],
            data_state,
            "sample",
            DISEASE_SPECIFIC_MODE,
            "Glioma",
        )

        evaluator.assert_not_called()
        self.assertIn("cannot be reliably associated", output[2])

    @patch("analyze.intra_node.PairwiseRelationshipEvaluator")
    def test_unconfigured_project_does_not_run_icdc_analysis(self, evaluator):
        data_state = {
            "diagnosis": pd.DataFrame({"disease_term": ["Glioma"] * 5}),
        }

        output = _run_intra_node_analysis(
            {},
            [SimpleNamespace(name="diagnosis")],
            data_state,
            "diagnosis",
            "CDS-derived disease-specific",
            "Glioma",
            selected_project="CDS",
        )

        evaluator.assert_not_called()
        self.assertIn("not configured", output[2])


if __name__ == "__main__":
    unittest.main()
