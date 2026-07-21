from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from config import get_disease_generation_config
from disease_vocabulary import ALL_LOADED_MODE
from generate.intra_node import generate_node_data as _generate_node_data

ICDC_CONFIG = get_disease_generation_config("ICDC")
assert ICDC_CONFIG is not None
DISEASE_SPECIFIC_MODE = ICDC_CONFIG.disease_specific_mode


def generate_node_data(*args, **kwargs):
    kwargs.setdefault("selected_project", "ICDC")
    return _generate_node_data(*args, **kwargs)


class GenerateNodeDataTests(unittest.TestCase):
    schema_state = [SimpleNamespace(name="diagnosis")]

    @staticmethod
    def data_state(glioma_rows: int = 5, other_rows: int = 0):
        return {
            "diagnosis": pd.DataFrame(
                {
                    "disease_term": ["Glioma"] * glioma_rows
                    + ["Mammary Cancer"] * other_rows,
                    "stage": list(range(glioma_rows + other_rows)),
                }
            )
        }

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_unsupported_request_short_circuits_both_engines(self, evaluator, generator):
        output = generate_node_data(
            {},
            self.schema_state,
            self.data_state(),
            "diagnosis",
            10,
            DISEASE_SPECIFIC_MODE,
            "Sarcoma",
        )

        self.assertEqual(len(output), 5)
        self.assertIn("Sarcoma", output[3])
        evaluator.assert_not_called()
        generator.assert_not_called()

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_unconfigured_project_cannot_inherit_icdc_scope(self, evaluator, generator):
        output = _generate_node_data(
            {},
            self.schema_state,
            self.data_state(),
            "diagnosis",
            10,
            "CDS-derived disease-specific",
            "Glioma",
            selected_project="CDS",
        )

        self.assertIn("not configured", output[3])
        evaluator.assert_not_called()
        generator.assert_not_called()

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_insufficient_request_short_circuits_both_engines(self, evaluator, generator):
        output = generate_node_data(
            {},
            self.schema_state,
            self.data_state(glioma_rows=4),
            "diagnosis",
            10,
            DISEASE_SPECIFIC_MODE,
            "Glioma",
        )

        self.assertIn("not enough", output[3])
        evaluator.assert_not_called()
        generator.assert_not_called()

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_unscopable_request_short_circuits_both_engines(self, evaluator, generator):
        data_state = self.data_state()
        data_state["sample"] = pd.DataFrame({"sample_site": ["Brain"] * 10})
        sample_schema = [SimpleNamespace(name="sample")]

        output = generate_node_data(
            {},
            sample_schema,
            data_state,
            "sample",
            10,
            DISEASE_SPECIFIC_MODE,
            "Glioma",
        )

        self.assertIn("cannot be reliably associated", output[3])
        evaluator.assert_not_called()
        generator.assert_not_called()

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_supported_request_passes_only_scoped_rows(self, evaluator_cls, generator_cls):
        relationships = pd.DataFrame(
            [{"A": "disease_term", "B": "stage", "classification": "strong"}]
        )
        evaluator_cls.return_value.evaluate_all_pairs.return_value = relationships
        generated = pd.DataFrame({"disease_term": ["Glioma"], "stage": [1]})
        generator_cls.return_value.generate.return_value = generated
        generator_cls.return_value.validate_rows.return_value = (
            generated,
            pd.DataFrame(),
        )

        output = generate_node_data(
            {},
            self.schema_state,
            self.data_state(glioma_rows=5, other_rows=5),
            "diagnosis",
            1,
            DISEASE_SPECIFIC_MODE,
            "glioma",
        )

        scoped_rows = evaluator_cls.return_value.evaluate_all_pairs.call_args.args[0]
        self.assertEqual(len(scoped_rows), 5)
        self.assertEqual(set(scoped_rows["disease_term"]), {"Glioma"})
        generator_rows = generator_cls.call_args.kwargs["real_rows"]
        self.assertEqual(len(generator_rows), 5)
        self.assertIn("disease-specific", output[3])
        self.assertEqual(output[4], "")

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_all_loaded_mode_passes_every_selected_node_row(self, evaluator_cls, generator_cls):
        relationships = pd.DataFrame(
            [{"A": "disease_term", "B": "stage", "classification": "strong"}]
        )
        evaluator_cls.return_value.evaluate_all_pairs.return_value = relationships
        generated = pd.DataFrame({"disease_term": ["Glioma"], "stage": [1]})
        generator_cls.return_value.generate.return_value = generated
        generator_cls.return_value.validate_rows.return_value = (
            generated,
            pd.DataFrame(),
        )

        output = generate_node_data(
            {},
            self.schema_state,
            self.data_state(glioma_rows=5, other_rows=5),
            "diagnosis",
            1,
            ALL_LOADED_MODE,
            None,
        )

        all_rows = evaluator_cls.return_value.evaluate_all_pairs.call_args.args[0]
        self.assertEqual(len(all_rows), 10)
        self.assertIn("should not be treated as disease-specific", output[3])

    @patch("generate.intra_node.SyntheticDataGenerator")
    @patch("generate.intra_node.PairwiseRelationshipEvaluator")
    def test_no_relationships_does_not_construct_generator(self, evaluator_cls, generator_cls):
        evaluator_cls.return_value.evaluate_all_pairs.return_value = pd.DataFrame()

        output = generate_node_data(
            {},
            self.schema_state,
            self.data_state(),
            "diagnosis",
            1,
            DISEASE_SPECIFIC_MODE,
            "Glioma",
        )

        evaluator_cls.assert_called_once()
        generator_cls.assert_not_called()
        self.assertIn("could not be completed", output[3])


if __name__ == "__main__":
    unittest.main()
