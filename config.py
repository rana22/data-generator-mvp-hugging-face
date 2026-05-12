from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TABLE_JS = (BASE_DIR / "static" / "table.js").read_text(encoding="utf-8")
CUSTOM_CSS = (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8")

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
