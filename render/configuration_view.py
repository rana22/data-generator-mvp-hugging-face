import gradio as gr
from loaders import (
    parse_env_text,
    load_env_to_text,
    get_excel_or_json_data
)

def view_configuration():
    select_project = gr.Dropdown(label="Select node", choices=[
        "ICDC", "CRDC"
    ], interactive=True)
    
    with gr.Row():
        env_text = gr.Textbox(
            label="Environment variables (.env text)",
            lines=8,
            placeholder="NODE_MODEL_URL=...\nPROP_MODEL_URL=...\nNEO4J_URI=...\nNEO4J_USER=...\nNEO4J_PASSWORD=...",
        )
        
        env_upload = gr.File(
            label="Upload .txt file",
            file_types=[".env", ".txt"],
            type="filepath",
        )
    env_upload.change(
        load_env_to_text,
        inputs=[env_upload],
        outputs=[env_text]
    )
    return env_text