import nbformat
import json
import re
import os
from typing import Dict, List, Tuple, Optional

def get_cell_text(cell: Dict) -> str:
    """Extract text content from a notebook cell."""
    return ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

def detect_tag(cell_text: str) -> Tuple[Optional[str], Optional[str]]:
    """Detect and return the tag type and model tag from cell text."""
    match = re.match(r"\*\*\[(.*?)\]\*\*", cell_text.strip())
    if not match:
        return None, None
    tag = match.group(1)
    if tag == "user": return "user", None
    if tag == "turn_metadata": return "metadata", None
    if tag == "assistant": return "assistant", None
    if tag.startswith("assistant_"): return "assistant_model", tag.split("_", 1)[1]
    return None, None

def extract_json_from_metadata_cell(source_text: str) -> Dict:
    """Extract JSON data from metadata cell."""
    try:
        match = re.search(r"```(?:json)?\n(.*?)```", source_text, re.DOTALL)
        if not match: return {}
        json_str = match.group(1).strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON error: {e}")
        return {}

def process_notebook(file_path: str, dialogue_id: Optional[str] = None) -> Dict:
    """Process a Jupyter notebook and convert it to a structured format of:
    {
        "turns": [
            {
                "prompt": str,
                "instructions": {
                    "metadata": List[str],
                    "instructions": List[Dict]
                },
                "response": str,
                "response_type": str,
                "results": Dict[str, Any]
            }
        ],
        "dialogue_metadata": {
            "dialogue_id": str,
            "dialogue_length": int
        }
    }
    """
    with open(file_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    turns = []
    current_turn = {}
    assistant_models = {}

    # Skip the first cell
    for cell in nb['cells'][1:]:
        if cell['cell_type'] != 'markdown':
            continue
        cell_text = get_cell_text(cell)
        tag_type, model_tag = detect_tag(cell_text)
        if not tag_type:
            continue
        content = re.sub(r"\*\*\[.*?\]\*\*", "", cell_text).strip()
        
        if tag_type == "user":
            if current_turn:
                for k, v in assistant_models.items():
                    current_turn[f"{k}_response"] = v
                turns.append(current_turn)
                current_turn = {}
                assistant_models = {}
            current_turn["prompt"] = content
        elif tag_type == "metadata":
            instruction_data = extract_json_from_metadata_cell(cell_text)
            current_turn["instructions"] = {
                "metadata": instruction_data.get("metadata", []),
                "instructions": instruction_data.get("instructions", [])
            }
        elif tag_type == "assistant":
            current_turn["response"] = content
        elif tag_type == "assistant_model":
            assistant_models[model_tag] = content

    if current_turn:
        for k, v in assistant_models.items():
            current_turn[f"{k}_response"] = v
        turns.append(current_turn)

    return {
        "turns": turns,
        "dialogue_metadata": {
            "dialogue_id": dialogue_id or os.path.basename(file_path),
            "dialogue_length": len(turns)
        }
    } 