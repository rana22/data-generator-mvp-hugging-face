from tkinter.constants import FALSE
import gradio as gr

README_TEXT = """
1. PROVIDE NODE_MODEL_URL and PROP_MODEL_URL in Environment variables input text.
2. Upload a JSON or Excel file of the data specific to study and node. 

## Data Format Requirements
(Make sure the file has `type` or `type_`, for target node)

### Supported file types
- JSON (`.json`)
- Excel (`.xlsx`, `.xls`)

---

## Required structure

Each row must represent a single entity and include a node type.

### Required field
- `type` **or** `type_` → defines the node (e.g., sample, file, study)

---

## JSON format (recommended)

### Option 1: Array of objects
```json
[
  {
    "type": "file",
    "file_name": "example.bam",
    "file_type": "bam",
    "file_size": 1048576
  },
  {
    "type": "file",
    "file_name": "example2.bai",
    "file_type": "bai",
    "file_size": 2048
  }
]
"""

def view_read_me_content():
    with gr.Accordion("Before you start", open=FALSE):
        gr.Markdown(README_TEXT)
