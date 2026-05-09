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
    DISPLAY_COLUMNS
)

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
    schema_state, 
    full_node_data_state,
    selected_node_table,
    error_box
):
    # NodeSchema
    with gr.Row():
        run_intra_node_analysis_btn = gr.Button("Run Property analysis")
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
            schema_state, 
            full_node_data_state, 
            selected_node_table
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

    generate_btn.click(
        fn=generate_node_data,
        inputs=[
            schema_state,
            full_node_data_state,
            selected_node_table,
            num_rows_input
        ],
        outputs=[
            analysis_table,
            generated_table,
            invalid_data_table,
            error_box
        ],
    )

    return (
        error_box
    )
