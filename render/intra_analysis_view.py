import gradio as gr
import pandas as pd
import html as html_lib
import json
from analyze.intra_node import (
    run_intra_node_analysis,
    PairwiseRelationshipEvaluator
)
from render.table.component import (
    build_sortable_table
)
from generate.intra_node import (
    generate_node_data
)
from config import (
    DEFAULT_PROJECT_KEY,
    DISPLAY_COLUMNS,
    get_disease_generation_config,
)
from disease_vocabulary import (
    ALL_LOADED_MODE,
    extract_supported_diseases,
    format_supported_diseases,
)


EMPTY_ANALYSIS_HTML = "<p>No analysis data</p>"
EMPTY_GENERATED_HTML = "<p>No generated data</p>"
EMPTY_INVALID_HTML = "<p>No invalid rows</p>"


def _scope_status(generation_mode, selected_project, *, selection_changed=False):
    scope_config = get_disease_generation_config(selected_project)
    if scope_config is not None and generation_mode == scope_config.disease_specific_mode:
        if selection_changed:
            return "Disease or node selection changed. Run scoped analysis or generation again."
        return "Select or enter a supported disease term."
    if generation_mode == ALL_LOADED_MODE:
        return (
            "All-loaded mode selected. Generated output will not be treated as disease-specific."
        )
    if scope_config is None:
        return (
            f'Disease-specific generation is not configured for "{selected_project}". '
            "All-loaded mode remains available."
        )
    return "Choose a generation mode before running analysis or generation."


def _supported_summary(supported_terms, selected_project):
    scope_config = get_disease_generation_config(selected_project)
    if scope_config is None:
        return (
            f'**Disease-specific generation:** Not configured for "{selected_project}". '
            "Add a project scope profile before enabling it."
        )
    return (
        f"**Supported {scope_config.source_label}-derived disease terms "
        f"from `{scope_config.vocabulary_path}`:** "
        f"{format_supported_diseases(supported_terms)}"
    )


def refresh_project_scope_controls(selected_project, data_state):
    scope_config = get_disease_generation_config(selected_project)
    choices = [ALL_LOADED_MODE]
    supported_terms = ()
    disease_label = "Disease or disease area"
    if scope_config is not None:
        choices.insert(0, scope_config.disease_specific_mode)
        supported_terms = extract_supported_diseases(data_state, scope_config)
        disease_label = scope_config.request_label

    return (
        gr.update(choices=choices, value=None),
        gr.update(
            choices=list(supported_terms),
            value=None,
            visible=False,
            label=disease_label,
        ),
        _supported_summary(supported_terms, selected_project),
        _scope_status(None, selected_project),
        EMPTY_ANALYSIS_HTML,
        EMPTY_GENERATED_HTML,
        EMPTY_INVALID_HTML,
    )


def refresh_disease_controls(data_state, selected_project, generation_mode):
    scope_config = get_disease_generation_config(selected_project)
    supported_terms = extract_supported_diseases(data_state, scope_config)
    summary = (
        _supported_summary(supported_terms, selected_project)
    )
    status = _scope_status(generation_mode, selected_project)
    if scope_config is not None and generation_mode == scope_config.disease_specific_mode:
        status = "Loaded data changed. Select or enter a supported disease term."
    return (
        gr.update(choices=list(supported_terms), value=None),
        summary,
        status,
        EMPTY_ANALYSIS_HTML,
        EMPTY_GENERATED_HTML,
        EMPTY_INVALID_HTML,
    )


def update_generation_mode_controls(generation_mode, selected_project):
    scope_config = get_disease_generation_config(selected_project)
    if scope_config is not None and generation_mode == scope_config.disease_specific_mode:
        disease_update = gr.update(
            visible=True,
            interactive=True,
            value=None,
            label=scope_config.request_label,
        )
    else:
        disease_update = gr.update(visible=False, value=None)

    return (
        disease_update,
        _scope_status(generation_mode, selected_project),
        EMPTY_ANALYSIS_HTML,
        EMPTY_GENERATED_HTML,
        EMPTY_INVALID_HTML,
    )


def clear_generation_results(generation_mode, selected_project):
    status = _scope_status(
        generation_mode,
        selected_project,
        selection_changed=True,
    )
    return status, EMPTY_ANALYSIS_HTML, EMPTY_GENERATED_HTML, EMPTY_INVALID_HTML

def format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    def truncate_cell(x):
        if isinstance(x, (list, dict)):
            x = json.dumps(x, default=str)
        x = "" if x is None else str(x)
        return html_lib.escape(x, quote=False)

    if "evidence" in out.columns:
        out["evidence"] = out["evidence"].apply(
            lambda x: json.dumps(x, indent=2, default=str) if isinstance(x, (list, dict)) else x
        ).apply(truncate_cell)

    if "a_to_b_mapping" in out.columns and not out["a_to_b_mapping"].astype(str).eq("").all():
        out["a_to_b_mapping"] = out["a_to_b_mapping"].astype(str).apply(truncate_cell)
    return out

def get_display_df(df: pd.DataFrame, feature_type: str) -> pd.DataFrame:
    cols = DISPLAY_COLUMNS.get(feature_type, DISPLAY_COLUMNS["default"])
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()

def view_intra_node_analysis(
    weights_state,
    schema_state, 
    full_node_data_state,
    selected_node_table,
    error_box,
    selected_project,
):
    initial_scope_config = get_disease_generation_config(DEFAULT_PROJECT_KEY)
    initial_mode_choices = [ALL_LOADED_MODE]
    if initial_scope_config is not None:
        initial_mode_choices.insert(0, initial_scope_config.disease_specific_mode)

    gr.Markdown("## Generation Scope")
    generation_mode = gr.Radio(
        label="Generation mode",
        choices=initial_mode_choices,
        value=None,
        info="All-loaded generation must be selected explicitly.",
    )
    requested_disease = gr.Dropdown(
        label=(
            initial_scope_config.request_label
            if initial_scope_config is not None
            else "Disease or disease area"
        ),
        choices=[],
        value=None,
        allow_custom_value=True,
        filterable=True,
        interactive=True,
        visible=False,
    )
    supported_disease_summary = gr.Markdown(
        "Upload project vocabulary data to populate the supported disease list."
    )
    generation_status = gr.Markdown(
        "Choose a generation mode before running analysis or generation."
    )

    # NodeSchema
    with gr.Row():
        run_intra_node_analysis_btn = gr.Button("Run Scoped Property Analysis")
        textual_analyze_btn = gr.Button("Textual Analyze")
    # run_analysis_btn = gr.Button("Run Property analysis")

    analysis_state = gr.State({})
    relationship_state = gr.State({})
    analysis_summary = gr.Markdown()
    analysis_dfs = gr.State({})
    feature_tables_html = gr.HTML()

    def render_tables(dfs):
        if not isinstance(dfs, dict) or not dfs:
            return "<p>No grouped tables to display.</p>"

        html_parts = []
        for i, (feature_type, df) in enumerate(dfs.items(), start=1):
            display_df = format_display_df(get_display_df(df, feature_type))
            table_id = f"feature_table_{i}"
            html_parts.append(build_sortable_table(display_df, table_id, str(feature_type)))

        return "".join(html_parts)

    run_intra_node_analysis_btn.click(
        run_intra_node_analysis,
        inputs=[
            weights_state,
            schema_state, 
            full_node_data_state, 
            selected_node_table,
            generation_mode,
            requested_disease,
            selected_project,
        ],
        outputs=[
            analysis_state, 
            relationship_state, 
            analysis_summary, 
            analysis_dfs
        ]
    ).then(
        render_tables,
        inputs=analysis_dfs,
        outputs=feature_tables_html
    )

    # textual analysis summary
    textual_analysis_summary = gr.Markdown()
    textual_analysis_table = gr.HTML()
    textual_analysis_state = gr.State(pd.DataFrame())

    # generate data
    num_rows_input = gr.Number(
        label="Number of rows to generate",
        value=60,
        precision=0
    )
    generate_btn = gr.Button("Analyze and Generate Synthetic Data")
    # generated_table = gr.Dataframe(label="Generated Data")
    # invalid_data_table = gr.Dataframe(label="Invalid Data")
    analysis_table = gr.HTML()
    generated_table = gr.HTML()
    invalid_data_table = gr.HTML()

    full_node_data_state.change(
        fn=refresh_disease_controls,
        inputs=[full_node_data_state, selected_project, generation_mode],
        outputs=[
            requested_disease,
            supported_disease_summary,
            generation_status,
            analysis_table,
            generated_table,
            invalid_data_table,
        ],
    )

    generation_mode.change(
        fn=update_generation_mode_controls,
        inputs=[generation_mode, selected_project],
        outputs=[
            requested_disease,
            generation_status,
            analysis_table,
            generated_table,
            invalid_data_table,
        ],
    )

    requested_disease.change(
        fn=clear_generation_results,
        inputs=[generation_mode, selected_project],
        outputs=[
            generation_status,
            analysis_table,
            generated_table,
            invalid_data_table,
        ],
    )

    selected_node_table.change(
        fn=clear_generation_results,
        inputs=[generation_mode, selected_project],
        outputs=[
            generation_status,
            analysis_table,
            generated_table,
            invalid_data_table,
        ],
    )

    generate_btn.click(
        fn=generate_node_data,
        inputs=[
            weights_state,
            schema_state,
            full_node_data_state,
            selected_node_table,
            num_rows_input,
            generation_mode,
            requested_disease,
            selected_project,
        ],
        outputs=[
            analysis_table,
            generated_table,
            invalid_data_table,
            generation_status,
            error_box
        ],
    )

    selected_project.change(
        fn=refresh_project_scope_controls,
        inputs=[selected_project, full_node_data_state],
        outputs=[
            generation_mode,
            requested_disease,
            supported_disease_summary,
            generation_status,
            analysis_table,
            generated_table,
            invalid_data_table,
        ],
    )

    return (
        error_box,
        generation_mode,
    )
