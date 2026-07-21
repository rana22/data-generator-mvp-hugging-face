---
title: Data Generator MVP
emoji: 🔥
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.11.0
app_file: app.py
pinned: false
license: unknown
short_description: 'predict property relation and generate valid data '
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

## Project-configured disease-specific generation

For the full operator and developer guide, see
[`docs/disease-specific-generation-guide.md`](docs/disease-specific-generation-guide.md).

The app supports two explicit generation modes:

- **Project-derived disease-specific** appears only when the selected project has a validated disease-generation profile. It generates only from rows that can be reliably scoped using that profile.
- **All loaded source data** preserves the existing whole-dataset behavior and labels its output as not disease-specific.

ICDC is currently configured with `diagnosis.disease_term` as its vocabulary source. CDS, CTDC, and GC remain all-loaded-only until their vocabulary and scoping mappings are validated and added. An unconfigured project never inherits another project's disease semantics.

Supported terms are derived dynamically from the configured vocabulary field. Blank values and configured missing-value terms are excluded. Matching ignores case and repeated whitespace, but does not use fuzzy matching or aliases.

Disease-specific generation is declined when:

- the requested disease is not in the selected project's loaded vocabulary;
- fewer than the configured minimum number of verified node rows are available; or
- the selected node cannot be reliably associated with the disease.

The ICDC minimum verified row count defaults to `5` and can be changed with:

```bash
MIN_DISEASE_NODE_ROWS=10 python app.py
```

Uploaded records are currently separated into independent node tables without graph relationships. A project profile can declare a direct disease-scope property for each node, or a `"*"` fallback property shared by all nodes. A node is declined when its configured property is absent. Cross-node operations remain available only in explicit all-loaded mode and are not disease-specific.

### Adding another project profile

Add one entry to `DISEASE_GENERATION_CONFIGS` in `config.py` after validating the project's model and uploaded data:

```python
"CDS": DiseaseGenerationConfig(
    project_key="CDS",
    source_label="CDS",
    vocabulary_node="diagnosis",
    vocabulary_property="disease_type",
    direct_scope_properties={
        "diagnosis": "disease_type",
        "sample": "diagnosis_disease_type",
    },
    minimum_node_rows=5,
    missing_terms=frozenset({"", "unknown", "not reported"}),
    request_label="Disease type",
),
```

The profile controls the UI mode label, vocabulary source, per-node scope fields, missing terms, request label, fallback source name, and row threshold. Do not add a node mapping unless that field reliably associates each row with the requested disease.

Run the fallback and scoping tests with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
