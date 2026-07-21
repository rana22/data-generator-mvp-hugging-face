import gradio as gr
from loaders import (
    parse_env_text,
    load_env_to_text,
    get_excel_or_json_data
)
from config import (
    DEFAULT_PROJECT_KEY,
    projects_config
)

def get_env_from_project(project, current_env_text=""):
    cfg = projects_config.get(project, {})
    if not cfg:
        return current_env_text

    # keep any other env lines, replace only these two keys
    lines = []
    if current_env_text:
        lines = [
            line for line in current_env_text.splitlines()
            if not line.startswith("NODE_MODEL_URL=")
            and not line.startswith("PROP_MODEL_URL=")
        ]

    lines.extend([
        f"NODE_MODEL_URL={cfg['NODE_MODEL_URL']}",
        f"PROP_MODEL_URL={cfg['PROP_MODEL_URL']}",
    ])

    return "\n".join(lines).strip()

def view_configuration():
    projects = projects_config.keys()
    select_project = gr.Dropdown(
        label="Select project",
        choices=projects,
        value=DEFAULT_PROJECT_KEY,
        interactive=True
    )
    
    with gr.Row():
        env_text = gr.Textbox(
            label="Environment variables (.env text)",
            value=get_env_from_project(DEFAULT_PROJECT_KEY),
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

    select_project.change(
        get_env_from_project,
        inputs=[select_project, env_text],
        outputs=[env_text]
    )

    return env_text, select_project
