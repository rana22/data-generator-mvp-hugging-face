import gradio as gr
import pandas as pd

def display_selected_node(node, grouped_data):
    if not node or node not in grouped_data:
        return pd.DataFrame()
    return grouped_data[node]

def update_node_selector(node_list):
    return gr.update(choices=node_list)

def view_load_data(error_box):
    with gr.Row():
        data_upload = gr.File(
            label="Upload data",
            file_types=[".json", ".xlsx"],
            type="filepath",
            file_count="multiple",
        )

    with gr.Row():
        selected_node_table = gr.Dropdown(
            label="Select node",
            choices=[],
            interactive=True
        )

    selected_node_dataframe = gr.Dataframe(label="Selected Node", interactive=False)
    full_node_data_state = gr.State({})

    selected_node_table.change(
        fn=display_selected_node,
        inputs=[selected_node_table, full_node_data_state],
        outputs=[selected_node_dataframe],
    )

    return (
        data_upload,
        selected_node_table,
        selected_node_dataframe,
        full_node_data_state,
        error_box
    )
    
    
