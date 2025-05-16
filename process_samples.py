import json
import nbformat
import os
import sys
import glob
import re
from collections import defaultdict

def get_cell_text(cell):
    """Safely join multiline or string cell contents."""
    return ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

def detect_tag(cell_text):
    """Detect tag and return tag type and optional model tag."""
    match = re.match(r"\*\*\[(.*?)\]\*\*", cell_text.strip())
    if not match:
        return None, None

    tag = match.group(1)
    if tag == "user":
        return "user", None
    elif tag == "turn_metadata":
        return "metadata", None
    elif tag == "assistant":
        return "assistant", None
    elif tag.startswith("assistant_"):
        return "assistant_model", tag.split("_", 1)[1]
    else:
        return None, None

def extract_json_from_metadata_cell(source_text):
    try:
        match = re.search(r"```(?:json)?\n(.*?)```", source_text, re.DOTALL)
        if not match:
            return {}
        json_str = match.group(1).strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("JSON decode error:")
        print(f"Parse error on line {e.lineno}:")
        print(e.doc.splitlines()[e.lineno-1])
        print(" " * e.colno + "^")
        print(f"Expecting {e.msg}")
        return {}

def process_notebook(file_path, dialogue_id=None):
    with open(file_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    turns = []
    current_turn = {}
    assistant_models = {}

    for cell in nb['cells']:
        if cell['cell_type'] != 'markdown':
            continue

        cell_text = get_cell_text(cell)
        tag_type, model_tag = detect_tag(cell_text)

        if not tag_type:
            continue

        content = re.sub(r"\*\*\[.*?\]\*\*", "", cell_text).strip()

        if tag_type == "user":
            # If we already have a turn in progress, save it
            if current_turn:
                # Append any previously collected assistant_model responses
                for k, v in assistant_models.items():
                    current_turn[f"{k}_response"] = v
                turns.append(current_turn)
                current_turn = {}
                assistant_models = {}

            current_turn["prompt"] = content

        elif tag_type == "metadata":
            instruction_data = extract_json_from_metadata_cell(cell_text)
            current_turn["instructions"] = [{
                "instruction_id_list": instruction_data.get("instruction_id_list", []),
                "kwargs": instruction_data.get("kwargs", [])
            }]

        elif tag_type == "assistant":
            current_turn["response"] = content

        elif tag_type == "assistant_model":
            assistant_models[model_tag] = content

    # Save last turn
    if current_turn:
        for k, v in assistant_models.items():
            current_turn[f"{k}_response"] = v
        turns.append(current_turn)

    return {
        "turns": turns,
        "dialogue_metadata": {
            "id": dialogue_id or os.path.basename(file_path),
            "length": len(turns)
        }
    }




if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_samples.py <input_directory>")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    ipynb_files = glob.glob(os.path.join(input_dir, "*.ipynb"))
    if not ipynb_files:
        print(f"No .ipynb files found in {input_dir}")
        sys.exit(1)

    all_dialogues = []
    total_files = len(ipynb_files)
    processed_files = 0

    for ipynb_path in ipynb_files:
        dialogue_id = os.path.splitext(os.path.basename(ipynb_path))[0]
        
        try:
            dialogue = process_notebook(ipynb_path, dialogue_id=dialogue_id)
            all_dialogues.append(dialogue)
            
            processed_files += 1
            print(f"Processed {dialogue['dialogue_metadata']['length']} turns from {dialogue_id}")
        except Exception as e:
            print(f"Error processing {ipynb_path}: {str(e)}")
            continue

    # Save all dialogues to a single output file
    output_path = os.path.join(input_dir, "all_dialogues.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_dialogues, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete:")
    print(f"- Processed {processed_files} out of {total_files} files")
    print(f"- Total dialogues collected: {len(all_dialogues)}")
    print(f"- Output saved to {output_path}")