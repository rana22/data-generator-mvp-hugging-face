from __future__ import annotations

import os, json
import gradio as gr
import copy
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
from render.feature_weight_view import (
    view_feature_weights
)
from feature.weights import (
    node_features_2_weight
)
# from feature.model_wrapper import relation_model_wrapper
# from feature.textual import TextualFeatureAnalyzer
from config import (
    CUSTOM_CSS,
    AG_GRID_HEAD,
)

# def log_full_node_data_shapes(full_node_data_state):
#     if not isinstance(full_node_data_state, dict) or not full_node_data_state:
#         print("full_node_data_state is empty or not a dict")
#         return

#     for node, df in full_node_data_state.items():
#         if df is None:
#             print(f"{node}: None")
#         else:
#             try:
#                 print(f"{node}: {df.shape}")
#             except Exception as e:
#                 print(f"{node}: could not read shape ({type(df)}), error={e}")

with gr.Blocks(
    title="Synthetic Data Demo"
) as demo:
    gr.Markdown("# Synthetic Data Demo\nAnalyze learned property relationships, visualize them, and generate synthetic rows.")
    
    error_box = gr.HTML(value="")
    view_read_me_content()

    env_text, selected_project = view_configuration()

    node_list_state = gr.State([])

    data_upload, selected_node_table, selected_node_dataframe, \
    full_node_data_state, error_box = view_load_data(error_box)
    # log_full_node_data_shapes(full_node_data_state)

    node_list_state, schema_state, graph_state, paths_out, \
    edges, edges_out, error_box = view_model(env_text, error_box)

    normalized_weights_state = gr.State({})
    weights_state = gr.State(copy.deepcopy(node_features_2_weight))
    weights_state, normalized_weights_state = view_feature_weights(node_list_state, weights_state, normalized_weights_state)
    
    error_box, generation_mode = view_intra_node_analysis(
        weights_state,
        schema_state, 
        full_node_data_state,
        selected_node_table,
        error_box,
        selected_project,
    )
    # log_full_node_data_shapes(full_node_data_state)

    error_box = view_inter_nodes_analysis(
        weights_state,
        data_upload,
        selected_node_table,
        selected_node_dataframe,
        schema_state,
        node_list_state,
        full_node_data_state,
        edges,
        edges_out,
        error_box,
        generation_mode,
    )

def main() -> None:
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        head=AG_GRID_HEAD + f"<style>{CUSTOM_CSS}</style>",
    )
if __name__ == "__main__":
    main()
