import nbformat
import json
import re
import os
from typing import Dict, List, Tuple, Optional
import copy

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

def validate_and_fix_consecutive_metadata_items(prev_instr: List[Dict], curr_instr: List[Dict]):
    """
    Compare consecutive metadata items and return the updated metadata and details for reporting.
    prev_instr: List[Dict] - List of previous instructions
    curr_instr: List[Dict] - List of current instructions
    return: Tuple[List[str], List[Dict]] - (List of metadata changes, List of change details)
    """
    def to_dict(instructions):
        return {instr['instruction_id']: instr for instr in instructions}

    prev_instr_dict = to_dict(prev_instr)
    curr_instr_dict = to_dict(curr_instr)

    metadata = set()
    change_details = []

    # Check for additions and modifications
    for instr_id, instr in curr_instr_dict.items():
        if instr_id not in prev_instr_dict:
            metadata.add("add")
            change_details.append({"change": "add", "instruction_id": instr_id})
        elif instr != prev_instr_dict[instr_id]:
            metadata.add("modify")
            change_details.append({"change": "modify", "instruction_id": instr_id})

    # Check for removals
    for instr_id in prev_instr_dict:
        if instr_id not in curr_instr_dict:
            metadata.add("remove")
            change_details.append({"change": "remove", "instruction_id": instr_id})

    return list(metadata), change_details

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
    instruction_list = []
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
            curr_instr = instruction_data.get("instructions", [])
            # if the first metadata cell, check if it has only "add", else, pass both previous and current metadata
            if len(turns) == 0:
                updated_metadata = ["add"]
            else:
                updated_metadata, _ = validate_and_fix_consecutive_metadata_items(instruction_list[-1], curr_instr)
            instruction_list.append(curr_instr)
            current_turn["instructions"] = {
                "instruction_change": updated_metadata,
                "instructions": curr_instr
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

def process_notebook_with_metadata_report(file_path: str, dialogue_id: Optional[str] = None) -> Tuple[Dict, List[Dict]]:
    """
    Process a Jupyter notebook and return both the structured format and a metadata change report.
    The report is a list of dicts: {turn_index, changes: [ {change, instruction_id}, ... ]}
    """
    with open(file_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    turns = []
    current_turn = {}
    assistant_models = {}
    instruction_list = []
    metadata_report = []
    turn_idx = 0
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
                turn_idx += 1
            current_turn["prompt"] = content
        elif tag_type == "metadata":
            instruction_data = extract_json_from_metadata_cell(cell_text)
            curr_instr = instruction_data.get("instructions", [])
            if len(turns) == 0:
                updated_metadata = ["add"]
                change_details = [{"change": "add", "instruction_id": instr.get("instruction_id", "")}
                                 for instr in curr_instr]
            else:
                updated_metadata, change_details = validate_and_fix_consecutive_metadata_items(
                    instruction_list[-1], curr_instr)
            instruction_list.append(curr_instr)
            current_turn["instructions"] = {
                "instruction_change": updated_metadata,
                "instructions": curr_instr
            }
            metadata_report.append({
                "turn_index": turn_idx + 1,
                "changes": change_details
            })
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
    }, metadata_report 