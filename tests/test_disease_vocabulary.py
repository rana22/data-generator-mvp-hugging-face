from __future__ import annotations

import unittest

import pandas as pd

from config import DiseaseGenerationConfig, get_disease_generation_config
from disease_vocabulary import (
    ALL_LOADED_MODE,
    DiseaseRequestStatus,
    extract_supported_diseases as _extract_supported_diseases,
    normalize_disease_term as _normalize_disease_term,
    prepare_generation_rows as _prepare_generation_rows,
)

ICDC_CONFIG = get_disease_generation_config("ICDC")
assert ICDC_CONFIG is not None
DISEASE_SPECIFIC_MODE = ICDC_CONFIG.disease_specific_mode


def normalize_disease_term(value):
    return _normalize_disease_term(value, ICDC_CONFIG)


def extract_supported_diseases(data_state):
    return _extract_supported_diseases(data_state, ICDC_CONFIG)


def prepare_generation_rows(*args, **kwargs):
    kwargs.setdefault("scope_config", ICDC_CONFIG)
    kwargs.setdefault("project_name", "ICDC")
    return _prepare_generation_rows(*args, **kwargs)


class DiseaseVocabularyTests(unittest.TestCase):
    def test_normalization_is_conservative(self):
        self.assertEqual(normalize_disease_term("  Mammary   Cancer  "), "mammary cancer")
        self.assertEqual(normalize_disease_term("GLIOMA"), "glioma")
        self.assertEqual(normalize_disease_term("Gliomaa"), "gliomaa")

    def test_missing_disease_terms_are_excluded(self):
        values = [
            "",
            "Unknown",
            "Not Reported",
            "Not Applicable",
            "NA",
            "N/A",
            "None",
            "Null",
            "NaN",
            None,
            pd.NA,
            float("nan"),
        ]
        data_state = {"diagnosis": pd.DataFrame({"disease_term": values})}

        self.assertEqual(extract_supported_diseases(data_state), ())

    def test_extraction_preserves_deterministic_canonical_spelling(self):
        data_state = {
            "diagnosis": pd.DataFrame(
                {
                    "disease_term": [
                        "glioma",
                        "Glioma",
                        "Glioma",
                        " Mammary   Cancer ",
                        "Unknown",
                    ]
                }
            )
        }

        self.assertEqual(
            extract_supported_diseases(data_state),
            ("Glioma", "Mammary Cancer"),
        )

    def test_missing_diagnosis_data_produces_empty_vocabulary(self):
        self.assertEqual(extract_supported_diseases({}), ())
        self.assertEqual(
            extract_supported_diseases({"diagnosis": pd.DataFrame({"stage": ["I"]})}),
            (),
        )


class DiseaseRequestTests(unittest.TestCase):
    @staticmethod
    def diagnosis_state(row_count: int = 5) -> dict[str, pd.DataFrame]:
        return {
            "diagnosis": pd.DataFrame(
                {
                    "disease_term": ["Glioma"] * row_count,
                    "stage": [f"stage-{index}" for index in range(row_count)],
                }
            )
        }

    def test_mode_is_required(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(), "diagnosis", None, "Glioma"
        )

        self.assertEqual(result.status, DiseaseRequestStatus.INVALID_REQUEST)
        self.assertFalse(result.can_generate)
        self.assertIsNone(rows)

    def test_disease_is_required_in_disease_specific_mode(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(), "diagnosis", DISEASE_SPECIFIC_MODE, ""
        )

        self.assertEqual(result.status, DiseaseRequestStatus.INVALID_REQUEST)
        self.assertIsNone(rows)

    def test_unsupported_disease_returns_supported_terms(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(), "diagnosis", DISEASE_SPECIFIC_MODE, "Sarcoma"
        )

        self.assertEqual(result.status, DiseaseRequestStatus.UNSUPPORTED_DISEASE)
        self.assertEqual(result.supported_terms, ("Glioma",))
        self.assertIn("Sarcoma", result.message)
        self.assertIn("Glioma", result.message)
        self.assertIsNone(rows)

    def test_unsupported_disease_is_resolved_before_selected_node_availability(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(), "sample", DISEASE_SPECIFIC_MODE, "Sarcoma"
        )

        self.assertEqual(result.status, DiseaseRequestStatus.UNSUPPORTED_DISEASE)
        self.assertIsNone(rows)

    def test_supported_disease_with_missing_selected_node_has_zero_verified_rows(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(), "sample", DISEASE_SPECIFIC_MODE, "Glioma"
        )

        self.assertEqual(result.status, DiseaseRequestStatus.INSUFFICIENT_NODE_DATA)
        self.assertEqual(result.canonical_disease, "Glioma")
        self.assertEqual(result.selected_node_row_count, 0)
        self.assertEqual(result.node_row_counts["sample"], 0)
        self.assertIsNone(rows)

    def test_missing_sentinel_request_is_unsupported_not_blank(self):
        result, _ = prepare_generation_rows(
            self.diagnosis_state(), "diagnosis", DISEASE_SPECIFIC_MODE, "Unknown"
        )

        self.assertEqual(result.status, DiseaseRequestStatus.UNSUPPORTED_DISEASE)

    def test_supported_diagnosis_request_returns_only_scoped_rows(self):
        data_state = {
            "diagnosis": pd.DataFrame(
                {
                    "disease_term": ["Glioma"] * 5 + ["Mammary Cancer"] * 5,
                    "stage": list(range(10)),
                }
            )
        }

        result, rows = prepare_generation_rows(
            data_state,
            "diagnosis",
            DISEASE_SPECIFIC_MODE,
            "  glioma ",
            min_node_rows=5,
        )

        self.assertEqual(result.status, DiseaseRequestStatus.SUPPORTED)
        self.assertEqual(result.canonical_disease, "Glioma")
        self.assertEqual(result.selected_node_row_count, 5)
        self.assertTrue(result.can_generate)
        self.assertEqual(len(rows), 5)
        self.assertEqual(set(rows["disease_term"]), {"Glioma"})

    def test_exact_minimum_row_count_is_supported(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(5),
            "diagnosis",
            DISEASE_SPECIFIC_MODE,
            "Glioma",
            min_node_rows=5,
        )

        self.assertEqual(result.status, DiseaseRequestStatus.SUPPORTED)
        self.assertEqual(len(rows), 5)

    def test_below_minimum_row_count_is_declined(self):
        result, rows = prepare_generation_rows(
            self.diagnosis_state(4),
            "diagnosis",
            DISEASE_SPECIFIC_MODE,
            "Glioma",
            min_node_rows=5,
        )

        self.assertEqual(result.status, DiseaseRequestStatus.INSUFFICIENT_NODE_DATA)
        self.assertEqual(result.selected_node_row_count, 4)
        self.assertIsNone(rows)

    def test_non_diagnosis_node_with_direct_disease_term_can_be_scoped(self):
        data_state = self.diagnosis_state(5)
        data_state["sample"] = pd.DataFrame(
            {
                "disease_term": ["Glioma"] * 5 + ["Mammary Cancer"],
                "sample_site": ["Brain"] * 5 + ["Mammary Gland"],
            }
        )

        result, rows = prepare_generation_rows(
            data_state,
            "sample",
            DISEASE_SPECIFIC_MODE,
            "Glioma",
            min_node_rows=5,
        )

        self.assertEqual(result.status, DiseaseRequestStatus.SUPPORTED)
        self.assertEqual(result.node_row_counts["sample"], 5)
        self.assertEqual(len(rows), 5)

    def test_non_diagnosis_node_without_linkage_is_unscopable(self):
        data_state = self.diagnosis_state(5)
        data_state["sample"] = pd.DataFrame({"sample_site": ["Brain"] * 10})

        result, rows = prepare_generation_rows(
            data_state,
            "sample",
            DISEASE_SPECIFIC_MODE,
            "Glioma",
        )

        self.assertEqual(result.status, DiseaseRequestStatus.UNSCOPABLE_NODE)
        self.assertIsNone(result.selected_node_row_count)
        self.assertIsNone(result.node_row_counts["sample"])
        self.assertIn("cannot be reliably associated", result.message)
        self.assertIsNone(rows)

    def test_all_loaded_mode_is_explicit_and_not_disease_specific(self):
        data_state = self.diagnosis_state(6)

        result, rows = prepare_generation_rows(
            data_state,
            "diagnosis",
            ALL_LOADED_MODE,
            requested_disease="Glioma",
        )

        self.assertEqual(result.status, DiseaseRequestStatus.ALL_LOADED)
        self.assertIsNone(result.requested_disease)
        self.assertFalse(result.is_disease_specific)
        self.assertEqual(len(rows), 6)
        self.assertIn("should not be treated as disease-specific", result.message)


class ProjectConfigurationTests(unittest.TestCase):
    def test_registry_lookup_is_case_insensitive(self):
        self.assertIs(get_disease_generation_config("icdc"), ICDC_CONFIG)
        self.assertIsNone(get_disease_generation_config("CDS"))

    def test_alternate_project_mapping_controls_vocabulary_and_scope_fields(self):
        example_config = DiseaseGenerationConfig(
            project_key="EXAMPLE",
            source_label="Example Commons",
            vocabulary_node="condition",
            vocabulary_property="condition_name",
            direct_scope_properties={"condition": "condition_name"},
            minimum_node_rows=2,
            missing_terms=frozenset({"", "Missing"}),
            request_label="Condition",
        )
        data_state = {
            "condition": pd.DataFrame(
                {
                    "condition_name": ["Rare Disease", "Rare Disease", "Missing"],
                    "category": ["A", "B", "C"],
                }
            )
        }

        supported = _extract_supported_diseases(data_state, example_config)
        result, rows = _prepare_generation_rows(
            data_state,
            "condition",
            example_config.disease_specific_mode,
            "rare disease",
            scope_config=example_config,
            project_name="EXAMPLE",
        )

        self.assertEqual(supported, ("Rare Disease",))
        self.assertEqual(result.status, DiseaseRequestStatus.SUPPORTED)
        self.assertEqual(result.node_row_counts["condition"], 2)
        self.assertEqual(len(rows), 2)
        self.assertIn("Example Commons-derived", result.message)

    def test_unconfigured_project_rejects_disease_specific_mode(self):
        data_state = {"diagnosis": pd.DataFrame({"disease_term": ["Glioma"] * 5})}

        result, rows = _prepare_generation_rows(
            data_state,
            "diagnosis",
            "CDS-derived disease-specific",
            "Glioma",
            scope_config=None,
            project_name="CDS",
        )

        self.assertEqual(result.status, DiseaseRequestStatus.INVALID_REQUEST)
        self.assertIn("not configured", result.message)
        self.assertIsNone(rows)

    def test_project_can_map_different_scope_properties_by_node(self):
        example_config = DiseaseGenerationConfig(
            project_key="EXAMPLE",
            source_label="Example Commons",
            vocabulary_node="condition",
            vocabulary_property="condition_name",
            direct_scope_properties={
                "condition": "condition_name",
                "sample": "condition_label",
            },
            minimum_node_rows=2,
        )
        data_state = {
            "condition": pd.DataFrame(
                {"condition_name": ["Rare Disease", "Rare Disease"]}
            ),
            "sample": pd.DataFrame(
                {
                    "condition_label": ["Rare Disease", "Rare Disease", "Other"],
                    "sample_site": ["A", "B", "C"],
                }
            ),
        }

        result, rows = _prepare_generation_rows(
            data_state,
            "sample",
            example_config.disease_specific_mode,
            "Rare Disease",
            scope_config=example_config,
            project_name="EXAMPLE",
        )

        self.assertEqual(result.status, DiseaseRequestStatus.SUPPORTED)
        self.assertEqual(len(rows), 2)
        self.assertEqual(set(rows["condition_label"]), {"Rare Disease"})

    def test_unconfigured_project_can_use_explicit_all_loaded_mode(self):
        data_state = {"sample": pd.DataFrame({"sample_id": ["1", "2"]})}

        result, rows = _prepare_generation_rows(
            data_state,
            "sample",
            ALL_LOADED_MODE,
            scope_config=None,
            project_name="CDS",
        )

        self.assertEqual(result.status, DiseaseRequestStatus.ALL_LOADED)
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
