# Unsupported Disease Generation Strategy and Implementation Plan

Date: 2026-06-15

## Purpose

This document defines the strategy and implementation plan for handling requests to generate example ICDC data for cancer types or disease areas that do not yet exist in the ICDC validated data vocabulary.

The core issue from the March 18 design review is valid: the generator can learn values and value combinations only from known ICDC data. If a submitter requests example files for a cancer type with no existing validated ICDC source rows, the system must not invent disease-specific values or imply that generic values are disease-specific.

## Recommendation

Use Option B as the default behavior:

- Decline disease-specific generation when the requested disease is not present in the supported ICDC vocabulary.
- Return a clear, informative message with the supported disease list and next steps.
- Do not silently fall back to a generic dataset.

Add Option C as an explicit alternate mode:

- Manual synthetic mode may generate examples from submitter-provided value lists.
- Manual mode output must be clearly labeled as user-provided synthetic data, not ICDC-derived disease-specific examples.

Do not use Option A as the default:

- A generic/default example dataset is risky because users may treat it as disease-specific.
- If Option A is ever added, it should be an explicit user choice with a strong disclaimer and should not be labeled as supported for the requested disease.

## Investigation Summary

### Current generation flow

The current app is a Gradio demo with node-level synthetic generation.

Relevant files:

- `app.py` wires the main Gradio UI.
- `render/intra_analysis_view.py` defines the node-level generation controls.
- `generate/intra_node.py` performs generation for the selected node.
- `generator.py` samples values from learned marginal and conditional distributions.
- `analyze/intra_node.py` learns pairwise property relationships from real rows.
- `loaders.py` loads uploaded JSON/XLSX files and splits records by `type` or `type_`.
- `neo4j_loader.py` can fetch node rows from Neo4j, currently scoped by `study_id`, not by disease.

The critical runtime path is:

1. Load schema.
2. Upload or load source data.
3. Select a node.
4. Run pairwise relationship analysis on the selected node dataframe.
5. Generate synthetic rows from the learned relationships.
6. Validate generated rows against learned relationships.

Current limitation:

- `generate_node_data()` requires real rows for the selected node.
- It does not accept a requested disease.
- It does not check whether the disease exists in ICDC.
- It does not disease-scope the source rows before learning relationships.
- If data is missing, it fails with a generic missing-data or no-relationships message.

Conclusion:

- For production behavior, the supported disease list must be derived dynamically from validated ICDC data, preferably Neo4j or a validated export.
- For local uploaded-file mode, the supported disease list can be derived from uploaded `diagnosis` rows, but only for data that parses cleanly?

## Definition of Supported Disease

A disease term is supported for ICDC-derived generation only when all of the following are true:

- The term exists in validated ICDC source data as `diagnosis.disease_term`.
- The value is not blank and not a missing-value sentinel such as `Unknown`, `Not Reported`, `Not Applicable`, or an empty string.
- The selected generation mode can retrieve real source rows associated with that disease.
- For the selected node, enough disease-scoped rows exist to learn relationships safely.

Support is node-specific:

- A disease can be supported for `diagnosis` while not yet supported for `sample`, `file`, or another node if there are no reachable rows for that node.
- The UI and API should distinguish "unsupported disease" from "supported disease, but no data for selected node."

Recommended MVP threshold:

- Use `min_diagnosis_rows = 1` for the first implementation so known diseases are discoverable.
- Use `min_node_rows = 5` before generation for a selected node unless product owners choose a different threshold.
- If row count is below the threshold, decline generation with an "insufficient source data" message instead of generating weak examples.

Healthy controls:

- `Healthy Control` appears in the local data as a `diagnosis.disease_term`.
- Display it separately as a control/cohort term unless product owners confirm it should appear in the same "supported cancer types" list.

## Fallback Behavior

### Default unsupported disease response

When a user requests a disease that is not supported:

1. Do not run relationship analysis.
2. Do not call `SyntheticDataGenerator`.
3. Do not fall back to all-disease or generic data.
4. Return a clear message.
5. Include currently supported terms.
6. Offer next steps:
   - submit the study first so ICDC can validate and learn the vocabulary;
   - choose an existing supported disease;
   - use manual synthetic mode with user-provided value lists, if enabled.

Recommended message:

```text
ICDC does not currently have validated source data for "<requested_disease>", so this tool cannot generate disease-specific example files for that disease.

Supported ICDC-derived disease terms are: <supported_terms>.

To proceed, choose a supported disease term, submit the study data first so the ICDC vocabulary can be updated, or use manual synthetic mode with approved value lists. Manual synthetic output is not ICDC-derived disease-specific data.
```

### Supported disease but unsupported selected node

When the disease exists, but there are not enough rows for the selected node:

```text
"<requested_disease>" exists in the ICDC disease vocabulary, but there are not enough validated "<node>" rows associated with that disease to generate reliable examples.

Available node support for this disease: <node_counts>.
```

### No disease requested

For backwards compatibility, the app may keep the current behavior when no disease is requested:

- Generate from the loaded dataset as a whole.
- Label the result as "all loaded source data" rather than disease-specific.
- Do not imply support for a disease that was not selected.

### Manual synthetic mode

Manual mode is allowed only when the user explicitly selects it and provides value lists.

Manual mode must:

- Validate property names against the loaded schema.
- Validate values against schema enums where enums exist.
- Reject unknown fields by default.
- Produce clear disclaimers.
- Avoid claiming that relationships are learned from ICDC disease-specific source data.

Recommended manual mode label:

```text
Generated from user-provided value lists. This output is synthetic and is not derived from ICDC validated source data for "<requested_disease>".
```

## Proposed Architecture

Add a small disease-vocabulary layer between data loading and generation.

### New module

Create `disease_vocabulary.py`.

Responsibilities:

- Normalize requested disease names.
- Extract supported diseases from loaded data.
- Query supported diseases from Neo4j.
- Resolve aliases to canonical disease terms.
- Validate generation requests.
- Build user-facing fallback messages.

Suggested data structures:

```python
@dataclass(frozen=True)
class DiseaseTerm:
    canonical_term: str
    normalized_term: str
    aliases: tuple[str, ...]
    primary_sites: tuple[str, ...]
    study_ids: tuple[str, ...]
    diagnosis_row_count: int
    node_row_counts: dict[str, int]
    source: str
    refreshed_at: str

@dataclass(frozen=True)
class DiseaseRequestResult:
    status: str
    requested_term: str
    canonical_term: str | None
    message: str
    supported_terms: tuple[str, ...]
    node_row_counts: dict[str, int]
```

Suggested status values:

- `supported`
- `unsupported_disease`
- `supported_disease_no_node_data`
- `ambiguous_disease`
- `manual_mode_required`
- `manual_mode_invalid`
- `no_disease_requested`

### Normalization rules

Use conservative normalization:

- Trim whitespace.
- Collapse repeated whitespace.
- Compare case-insensitively.
- Preserve the canonical display term from source data.
- Do not use fuzzy matching silently.

Alias behavior:

- Exact normalized alias matches can resolve to a canonical term.
- Ambiguous alias matches must ask the user to choose.
- Human relevance terms can seed aliases only if product owners approve that mapping.

Examples:

- `glioma` -> `Glioma`
- `  Mammary   Cancer  ` -> `Mammary Cancer`
- `breast cancer` should not automatically map to `Mammary Cancer` unless an approved alias table contains that mapping.

## Data Source Strategy

### Preferred production source: Neo4j

Neo4j should be the authoritative vocabulary source because it represents validated ICDC graph data.

Add a vocabulary query similar to:

```cypher
MATCH (d:diagnosis)
WHERE d.disease_term IS NOT NULL
  AND trim(d.disease_term) <> ""
RETURN
  d.disease_term AS disease_term,
  collect(DISTINCT d.primary_disease_site) AS primary_disease_sites,
  count(d) AS diagnosis_count
ORDER BY disease_term
```

If study metadata is needed:

```cypher
MATCH (d:diagnosis)
MATCH path = (d)-[*1..3]-(s:study)
WHERE d.disease_term IS NOT NULL
  AND trim(d.disease_term) <> ""
RETURN
  d.disease_term AS disease_term,
  collect(DISTINCT d.primary_disease_site) AS primary_disease_sites,
  collect(DISTINCT s.clinical_study_designation) AS study_ids,
  count(DISTINCT d) AS diagnosis_count
ORDER BY disease_term
```

Exact traversal depth and direction must be validated against the real ICDC graph model before implementation.

### Disease-scoped Neo4j row fetching

Extend `neo4j_loader.py` with disease-aware fetching.

Current code can fetch by `study_id`. Add:

- `fetch_supported_diseases_from_neo4j()`
- `fetch_rows_from_neo4j(..., disease_term=None)`
- `build_neo4j_query(..., disease_term=None)`

For `diagnosis`:

```cypher
MATCH (n:diagnosis)
WHERE toLower(n.disease_term) = toLower($disease_term)
RETURN n { <projection> } AS row
```

For `study`:

```cypher
MATCH (d:diagnosis)-[*1..3]-(s:study)
WHERE toLower(d.disease_term) = toLower($disease_term)
RETURN DISTINCT s { <projection> } AS row
```

For other nodes:

```cypher
MATCH (d:diagnosis)-[*1..3]-(n:<node_label>)
WHERE toLower(d.disease_term) = toLower($disease_term)
RETURN DISTINCT n { <projection> } AS row
```

This query shape must be tested against real graph paths to avoid accidental cross-study or cross-case contamination.

### Uploaded-file mode

Uploaded-file mode can derive disease support only from rows present in the uploaded files.

Rules:

- If `diagnosis` rows are present, extract disease terms from `diagnosis.disease_term`.
- If the selected node is `diagnosis`, disease filtering is direct.
- If the selected node is another node, disease filtering is allowed only when the uploaded data includes relationship keys that can connect that node to disease-scoped diagnosis rows.
- If no reliable join path exists in uploaded files, show an informative message instead of generating from all rows.

This matters because the current local node files do not consistently include relationship keys such as `case_id`, `sample_id`, or study linkage columns.

## UI and Chatbot Behavior

### Gradio UI

Add controls near the existing generation controls in `render/intra_analysis_view.py`:

- `Disease or disease area` text input or searchable dropdown.
- `Generation mode` selector:
  - `ICDC-derived disease-specific`
  - `All loaded source data`
  - `Manual synthetic value lists`
- Supported disease summary panel.
- Manual value-list upload/input, visible only in manual mode.
- Fallback/status message area.

Recommended UI behavior:

- If a supported disease dropdown can be populated, prefer dropdown plus optional search.
- If the user enters a term not in the list, show the unsupported disease message before generation.
- Disable or short-circuit generation when validation fails.
- Always label generated output with its source mode.

### Chatbot/API-ready behavior

Keep validation and message construction outside Gradio so future chatbot/API surfaces can reuse it.

Suggested function:

```python
validate_generation_request(
    requested_disease: str | None,
    selected_node: str,
    mode: str,
    vocabulary: DiseaseVocabulary,
    data_state: dict[str, pd.DataFrame],
) -> DiseaseRequestResult
```

The caller should receive:

- machine-readable status;
- user-facing message;
- canonical disease term, if resolved;
- supported terms;
- node support counts.

## Implementation Plan

### Phase 1: Vocabulary and request validation

Files to add or change:

- Add `disease_vocabulary.py`.
- Add tests under a new `tests/` directory if the project test framework is available.

Tasks:

- Implement `normalize_disease_term()`.
- Implement missing-value filtering.
- Implement extraction from `data_state["diagnosis"]`.
- Implement `DiseaseTerm` and `DiseaseRequestResult`.
- Implement request validation statuses.
- Implement user-facing unsupported and insufficient-data messages.
- Add unit tests for normalization, extraction, unsupported response, and ambiguous aliases.

Acceptance value:

- The system can define and expose a supported disease list from loaded data.
- Unsupported disease behavior is deterministic and reusable.

### Phase 2: Neo4j vocabulary support

Files to change:

- `neo4j_loader.py`
- Possibly `loaders.py` or a new service module if data source selection is centralized.

Tasks:

- Add `fetch_supported_diseases_from_neo4j()`.
- Add disease-aware query building.
- Add disease-scoped row fetching for `diagnosis`.
- Validate traversal for `study`, `case`, `sample`, and `file`.
- Return row counts by node for the selected disease.
- Ensure queries deduplicate rows by `uuid` when present.

Acceptance value:

- The app can grow the supported vocabulary automatically as validated Neo4j data grows.

### Phase 3: Guard generation

Files to change:

- `generate/intra_node.py`
- `render/table/component.py` if a richer status panel is needed.

Tasks:

- Add optional `requested_disease` and `generation_mode` arguments to `generate_node_data()`.
- Validate disease request before relationship analysis.
- If unsupported, return the fallback message and empty result tables.
- If supported, filter or fetch disease-scoped rows before analysis.
- If supported but selected node has insufficient rows, return the insufficient-data message.
- Preserve current behavior when no disease is requested and mode is `All loaded source data`.

Critical safety requirement:

- Unsupported disease requests must not call `PairwiseRelationshipEvaluator` or `SyntheticDataGenerator`.

Acceptance value:

- Users receive a clear response when requesting unsupported disease generation.
- The generator no longer silently uses unrelated rows for unsupported disease requests.

### Phase 4: UI integration

Files to change:

- `render/intra_analysis_view.py`
- Potentially `render/data_view.py`
- Potentially `app.py` if shared state is introduced.

Tasks:

- Add disease input/dropdown.
- Add generation mode selector.
- Add supported disease display.
- Add fallback message display.
- Pass disease and mode into `generate_node_data()`.
- Ensure output labels identify the generation source.

Acceptance value:

- Future UI behavior is clear and user-facing.
- Unsupported disease handling is visible before or during generation.

### Phase 5: Manual synthetic mode

Files to add or change:

- Add `manual_synthetic.py` or add a contained class/function in `disease_vocabulary.py` if small.
- Update `generate/intra_node.py`.
- Update `render/intra_analysis_view.py`.

Suggested manual input format:

```json
{
  "diagnosis": {
    "disease_term": ["Example Sarcoma"],
    "primary_disease_site": ["Soft Tissue"],
    "stage_of_disease": ["Unknown", "Not Reported"]
  },
  "sample": {
    "sample_site": ["Soft Tissue"],
    "physical_sample_type": ["Tissue"]
  }
}
```

Tasks:

- Validate node names against loaded schema.
- Validate property names against node schema.
- Validate enum values when schema enums exist.
- Reject empty value lists.
- Generate independent combinations first.
- Add relationship constraints only if the user supplies them explicitly.
- Label output as manual synthetic.

Acceptance value:

- Submitters have a controlled path for unsupported diseases without misleading ICDC-derived claims.

### Phase 6: Documentation

Files to change:

- `README.md`
- This plan file, if final decisions change.
- Optional user-facing docs page if the app grows a docs section.

Tasks:

- Document supported disease behavior.
- Document unsupported fallback.
- Document manual mode and disclaimers.
- Document vocabulary growth and refresh behavior.
- Document how to refresh vocabulary from Neo4j.

Acceptance value:

- The fallback behavior is documented and supportable.

## Bulletproof Validation Checklist

Before considering the ticket complete, verify all checks below.

### Vocabulary correctness

- Supported terms come from `diagnosis.disease_term`, not from free text.
- Blank, missing, and sentinel values are excluded.
- `human_relevance.relevant_human_cancer` is not treated as generation support by itself.
- Aliases are explicit and auditable.
- Ambiguous aliases do not auto-resolve.
- Supported terms preserve source capitalization for display.

### Generation safety

- Unsupported disease requests do not run generation.
- Unsupported disease requests do not fall back to all rows.
- Supported disease requests use disease-scoped rows.
- If disease-scoped row counts are too low, generation is declined.
- Output clearly states whether it is disease-specific, all-data, or manual synthetic.
- Generated examples never claim validation for an unsupported disease.

### Node-specific support

- Disease support is checked for the selected node, not only globally.
- `diagnosis` support is direct.
- Non-diagnosis node support requires a proven graph path or join path.
- Uploaded files without relationship keys do not pretend to support node-level disease filtering.
- Node row counts are included in diagnostics or logs.

### UI behavior

- Supported diseases are visible or discoverable.
- Unsupported messages are shown in the normal UI flow.
- Manual mode disclaimer is visible before and after generation.
- Users are not forced into manual mode silently.
- Error messages are user-facing and not stack traces.

### Data and parsing

- Invalid JSON exports are rejected with actionable messages.
- UTF-8 BOM files continue to parse where valid.
- Large vocabularies are handled without making the UI unusable.
- Vocabulary refresh failure does not corrupt the last known valid vocabulary.

### Tests

- Unit tests cover normalization.
- Unit tests cover supported disease extraction.
- Unit tests cover unsupported disease messaging.
- Unit tests cover supported disease with insufficient selected-node rows.
- Unit tests cover manual value-list validation.
- Integration tests cover one supported disease path.
- Integration tests cover one unsupported disease path.
- UI smoke test confirms fallback text appears.

### Observability

- Log requested disease, resolved canonical term, selected node, mode, and validation status.
- Do not log sensitive submitted values beyond what is needed for debugging.
- Track unsupported requests to inform future vocabulary or alias additions.

## Acceptance Criteria Mapping

### Fallback behavior is defined, documented, and implemented

Defined here:

- Default behavior is Option B.
- Option C is explicit manual synthetic mode.
- Option A is not default.

Implementation tasks:

- Add request validation.
- Guard generation.
- Add UI messaging.
- Add tests.

### Users receive a clear, informative response when requesting an unsupported disease type

Defined here:

- Unsupported message template.
- Insufficient selected-node data message template.

Implementation tasks:

- Centralize message construction.
- Return message to Gradio and future chatbot/API callers.

### The solution is extensible as ICDC's disease vocabulary grows

Defined here:

- Vocabulary is derived from validated data.
- Neo4j is the preferred authoritative source.
- No hardcoded disease list is required.

Implementation tasks:

- Add Neo4j vocabulary query.
- Add refreshable vocabulary object.
- Add row counts and source metadata.

## Risks and Mitigations

### Risk: Users misunderstand manual mode as ICDC-derived

Mitigation:

- Require explicit mode selection.
- Display disclaimer before and after generation.
- Include source mode in exported files if exports are added later.

### Risk: Human relevance terms overstate support

Mitigation:

- Use `diagnosis.disease_term` as the only support signal.
- Use human relevance only as display metadata or approved aliases.

### Risk: Disease-scoped traversal pulls unrelated rows

Mitigation:

- Validate Neo4j relationship paths against the ICDC model.
- Prefer model-defined relationships over arbitrary graph traversal where possible.
- Deduplicate by stable identifiers.
- Add integration tests with known studies.

### Risk: Too few rows produce poor synthetic examples

Mitigation:

- Add `min_node_rows`.
- Return an insufficient-data response below threshold.
- Log row counts.

### Risk: Vocabulary changes unexpectedly

Mitigation:

- Include `source`, `refreshed_at`, and row counts.
- Keep refresh behavior explicit.
- Optionally cache the last successful vocabulary snapshot.

### Risk: Current upload flow does not expose enough relationship context

Mitigation:

- Support direct disease filtering for `diagnosis`.
- Require relationship keys for other uploaded nodes.
- Prefer Neo4j for full disease-scoped generation.

## Open Questions

1. What is the authoritative production vocabulary source: Neo4j, a curated export, uploaded files, or a combination?

2. Should `Healthy Control` appear in the same supported list as cancer/disease terms, or in a separate control/cohort list?

3. What minimum row threshold is acceptable for disease-specific generation by node?

4. Are disease areas allowed to resolve to multiple `diagnosis.disease_term` values, or must users choose exact terms?

5. Who owns the approved alias table, for example whether `Breast Cancer` can map to `Mammary Cancer`?

6. Should Option A ever be available as an explicit "generic schema example" mode, or should it be excluded entirely?

7. Is manual synthetic mode required for the first release of this ticket, or can it be a follow-up after Option B is implemented?

8. What exact file format should manual value lists use: JSON only, XLSX only, or both?

9. Should manual mode allow user-provided relationship constraints, or only independent property value lists in the first version?

10. Which graph path should define disease association for `case`, `sample`, `file`, and other downstream nodes?

11. Should restricted or embargoed studies contribute to the supported vocabulary shown in the UI?

12. Should the supported disease list be global, user-permission scoped, environment scoped, or upload scoped?

13. Should exported generated files include a metadata sheet or sidecar file with disease support status and source mode?

14. How should the system behave when the requested disease is supported globally but only through studies that the current user cannot access?

15. Should chatbot responses include the full supported disease list, or summarize with top terms and a link/dropdown when the list is long?

16. Should unsupported requests be tracked as product analytics to prioritize vocabulary growth?

17. Should malformed source exports like the current `GLIOMA01-records.json` be rejected, repaired during loading, or regenerated upstream?

18. What is the desired behavior when a disease term exists in `human_relevance` but not in `diagnosis.disease_term`?

19. Should the vocabulary refresh happen on app startup, on demand, on schedule, or after each new study submission?

20. What acceptance test dataset should be used to prove the supported and unsupported paths?

## Proposed Definition of Done

The ticket is done when:

- The app can list supported ICDC-derived disease terms from the configured source.
- The app rejects unsupported disease-specific generation with the approved message.
- Unsupported requests do not call the generator.
- Supported disease requests use disease-scoped rows.
- Supported disease requests with insufficient selected-node rows are declined clearly.
- Manual synthetic mode is either implemented with disclaimers or explicitly deferred.
- UI and future chatbot/API responses use the same validation result object.
- Tests cover supported, unsupported, insufficient-data, and manual-mode validation paths.
- README or user docs explain the behavior and vocabulary growth strategy.
