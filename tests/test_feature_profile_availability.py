from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from feature.substring import SubstringFeatureAnalyzer


class FeatureProfileAvailabilityTests(unittest.TestCase):
    def test_substring_analysis_skips_node_without_weight_profile(self):
        analyzer = SubstringFeatureAnalyzer(
            node_schema=SimpleNamespace(name="diagnosis"),
            doc_model=Mock(),
            all_weights={
                "sample": {
                    "support": 0.2,
                    "prefix_match": 0.2,
                    "suffix_match": 0.2,
                    "substring_match": 0.2,
                    "doc_alignment": 0.2,
                }
            },
        )
        rows = pd.DataFrame({"a": ["x"], "b": ["x-value"]})

        self.assertIsNone(analyzer.analyze(rows, "a", "b"))
        analyzer.doc_model.score.assert_not_called()


if __name__ == "__main__":
    unittest.main()
