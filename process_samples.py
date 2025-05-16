import json
import nbformat
import os
import sys
import glob

def get_cell_text(cell):
    """Safely join multiline or string cell contents."""
    return ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

def is_user_cell(cell):
    """Check if the cell is a user cell."""
    return cell['cell_type'] == 'markdown' and '**[user]**' in get_cell_text(cell)

def is_assistant_cell(cell):
    """Check if the cell is an assistant cell."""
    return cell['cell_type'] == 'markdown' and '**[assistant]**' in get_cell_text(cell)

def is_metadata_cell(cell):
    """Check if the cell is a metadata cell."""
    return cell['cell_type'] == 'markdown' and '**[turn_metadata]**' in get_cell_text(cell)

def extract_json_from_metadata_cell(source_text):
    try:
        start = source_text.find("```")
        end = source_text.rfind("```")
        if start == -1 or end == -1 or start == end:
            return {}
        json_str = source_text[start+3:end].strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        return {}

def process_notebook(file_path, dialogue_id=None):
    with open(file_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    turns = []
    cells = nb['cells']
    i = 0

    while i < len(cells) - 2:
        user_cell = cells[i]
        metadata_cell = cells[i + 1]    
        assistant_cell = cells[i + 2]

        if is_user_cell(user_cell) and is_assistant_cell(assistant_cell) and is_metadata_cell(metadata_cell):
            prompt = get_cell_text(user_cell).replace('**[user]**', '').strip()
            response = get_cell_text(assistant_cell).replace('**[assistant]**', '').strip()
            metadata_text = get_cell_text(metadata_cell)
            instruction_data = extract_json_from_metadata_cell(metadata_text)

            turns.append({
                "prompt": prompt,
                "response": response,
                "instructions": [
                    {
                        "instruction_id_list": instruction_data.get("instruction_id_list", []),
                        "kwargs": instruction_data.get("kwargs", [])
                    }
                ]
            })

            i += 3  # Advance to next triplet
        else:
            i += 1  # Skip malformed or extra cells

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