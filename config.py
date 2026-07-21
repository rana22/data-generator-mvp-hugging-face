import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


def _positive_int_from_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default

BASE_DIR = Path(__file__).resolve().parent
TABLE_JS = (BASE_DIR / "static" / "table.js").read_text(encoding="utf-8")
CUSTOM_CSS = (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")
MIN_DISEASE_NODE_ROWS = _positive_int_from_env("MIN_DISEASE_NODE_ROWS", 5)

DEFAULT_MISSING_DISEASE_TERMS = frozenset({
    "",
    "unknown",
    "not reported",
    "not applicable",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
})


@dataclass(frozen=True)
class DiseaseGenerationConfig:
    """Project-specific mapping for validated disease-scoped generation."""

    project_key: str
    source_label: str
    vocabulary_node: str
    vocabulary_property: str
    direct_scope_properties: Mapping[str, str]
    minimum_node_rows: int = 5
    missing_terms: frozenset[str] = DEFAULT_MISSING_DISEASE_TERMS
    request_label: str = "Disease or disease area"

    def __post_init__(self) -> None:
        text_fields = (
            "project_key",
            "source_label",
            "vocabulary_node",
            "vocabulary_property",
            "request_label",
        )
        for field_name in text_fields:
            cleaned = " ".join(str(getattr(self, field_name)).split())
            if not cleaned:
                raise ValueError(f"{field_name} cannot be empty")
            object.__setattr__(self, field_name, cleaned)

        object.__setattr__(self, "project_key", self.project_key.upper())
        object.__setattr__(self, "minimum_node_rows", max(1, int(self.minimum_node_rows)))
        normalized_scope_properties: dict[str, str] = {}
        for node_name, property_name in self.direct_scope_properties.items():
            normalized_node = " ".join(str(node_name).split()).casefold()
            normalized_property = " ".join(str(property_name).split())
            if not normalized_node or not normalized_property:
                raise ValueError("direct_scope_properties cannot contain blank keys or values")
            normalized_scope_properties[normalized_node] = normalized_property
        object.__setattr__(
            self,
            "direct_scope_properties",
            MappingProxyType(normalized_scope_properties),
        )
        object.__setattr__(
            self,
            "missing_terms",
            frozenset(" ".join(str(term).split()).casefold() for term in self.missing_terms),
        )

    @property
    def disease_specific_mode(self) -> str:
        return f"{self.source_label}-derived disease-specific"

    @property
    def vocabulary_path(self) -> str:
        return f"{self.vocabulary_node}.{self.vocabulary_property}"

    def scope_property_for_node(self, node_name: str) -> str | None:
        normalized_node = " ".join(str(node_name).split()).casefold()
        return self.direct_scope_properties.get(
            normalized_node,
            self.direct_scope_properties.get("*"),
        )

AG_GRID_HEAD = f"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community/styles/ag-grid.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ag-grid-community/styles/ag-theme-quartz.css">
<script src="https://cdn.jsdelivr.net/npm/ag-grid-community/dist/ag-grid-community.min.js"></script>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script>
  {TABLE_JS}
</script>
"""

DISPLAY_COLUMNS = {
    "categorical": [
        "A",
        "B",
        "support",
        "predictive_strength",
        "determinism",
        "stability",
        "doc_alignment",
        "strength",
        "classification",
        "evidence",
        "a_to_b_mapping",
    ],
    "substring": [
        "A",
        "B",
        "support",
        "prefix_match",
        "suffix_match",
        "substring_match",
        "doc_alignment",
        "strength",
        "classification",
        "evidence",
    ],
    "default": [
        "A",
        "B",
        "support",
        "strength",
        "classification",
        "evidence",
    ],
}

projects_config = {
    "ICDC": {
        "NODE_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/develop/model-desc/icdc-model.yml",
        "PROP_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/develop/model-desc/icdc-model-props.yml"
    },
    "CDS": {
        "NODE_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/dev/cache/CDS/7.0.0/cds-model.yml",
        "PROP_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/dev/cache/CDS/7.0.0/cds-model-props.yml"

    },
    "CTDC": {
        "NODE_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/prod/cache/CTDC/1.2.0/ctdc_model_file.yaml",
        "PROP_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/crdc-datahub-models/prod/cache/CTDC/1.2.0/ctdc_model_properties_file.yaml"

    },
    "GC": {
        "NODE_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/develop/model-desc/icdc-model.yml",
        "PROP_MODEL_URL": "https://raw.githubusercontent.com/CBIIT/icdc-model-tool/develop/model-desc/icdc-model-props.yml"
    },
}

DEFAULT_PROJECT_KEY = "ICDC"


# Add a project here only after its vocabulary and row-scoping fields are validated.
DISEASE_GENERATION_CONFIGS: dict[str, DiseaseGenerationConfig] = {
    "ICDC": DiseaseGenerationConfig(
        project_key="ICDC",
        source_label="ICDC",
        vocabulary_node="diagnosis",
        vocabulary_property="disease_term",
        direct_scope_properties={"*": "disease_term"},
        minimum_node_rows=MIN_DISEASE_NODE_ROWS,
    ),
}


def get_disease_generation_config(
    project_key: str | None,
) -> DiseaseGenerationConfig | None:
    if not project_key:
        return None
    return DISEASE_GENERATION_CONFIGS.get(str(project_key).strip().upper())
