from __future__ import annotations

import os
import gradio as gr
# These imports assume your package is included in the Space repo.
from render.read_me_view import view_read_me_content
from render.data_view import (
    view_load_data
)
from render.configuration_view import (
    view_configuration
)
from render.model_view import (
    view_model
)
from render.intra_analysis_view import (
    view_intra_node_analysis
)
from render.inter_analysis_view import(
    view_inter_nodes_analysis
)
# from feature.model_wrapper import relation_model_wrapper
# from feature.textual import TextualFeatureAnalyzer
from config import (
    CUSTOM_CSS,
    AG_GRID_HEAD,
)

with gr.Blocks(
    title="ICDC Synthetic Data Demo"
) as demo:
    gr.Markdown("# ICDC Synthetic Data Demo\nAnalyze learned property relationships, visualize them, and generate synthetic rows.")
    
    error_box = gr.HTML(value="")
    view_read_me_content()

    env_text = view_configuration()

    node_list_state = gr.State([])

    data_upload, selected_node_table, selected_node_dataframe, \
    full_node_data_state, error_box = view_load_data(error_box)

    node_list_state, schema_state, graph_state, paths_out, \
    edges, edges_out, error_box = view_model(env_text, error_box)
    
    error_box = view_intra_node_analysis(
        schema_state, 
        full_node_data_state,
        selected_node_table,
        error_box
    )

    view_inter_nodes_analysis(
        data_upload,
        selected_node_table,
        selected_node_dataframe,
        schema_state,
        node_list_state,
        full_node_data_state,
        edges,
        edges_out,
        error_box
    )


def main() -> None:
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        head=AG_GRID_HEAD + f"<style>{CUSTOM_CSS}</style>",
    )
if __name__ == "__main__":
    main()
