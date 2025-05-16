import json
import re
import nbformat
import os
import sys
import glob

def extract_turns_from_markdown(markdown_text):
    turns = []
    # Split by user block (each turn starts with **[user]**)
    blocks = re.split(r'\*\*\[user\]\*\*', markdown_text)

    for block in blocks[1:]:  # skip any preamble before first user block
        try:
            prompt_match = re.search(r'\n+(.*?)\n+\*\*\[assistant\]\*\*', block, re.DOTALL)
            response_match = re.search(r'\*\*\[assistant\]\*\*\n+(.*?)\n+\*\*\[turn_metadata\]\*\*', block, re.DOTALL)
            metadata_match = re.search(r'\*\*\[turn_metadata\]\*\*\n+```(?:json)?\n(.+?)```', block, re.DOTALL)

            prompt = prompt_match.group(1).strip() if prompt_match else ""
            response = response_match.group(1).strip() if response_match else ""
            instruction_block = metadata_match.group(1).strip() if metadata_match else "{}"
            instruction_data = json.loads(instruction_block)

            turn = {
                "prompt": prompt,
                "response": response,
                "instructions": [
                    {
                        "instruction_id_list": instruction_data.get("instruction_id_list", []),
                        "kwargs": instruction_data.get("kwargs", [])
                    }
                ]
            }

            turns.append(turn)
        except Exception as e:
            print("Skipping block due to error:", e)
            continue

    return turns


def process_notebook(ipynb_path, dialogue_id=None):
    with open(ipynb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Combine all markdown cells into one big string
    full_markdown = ""
    for cell in nb['cells']:
        if cell['cell_type'] == 'markdown':
            full_markdown += ''.join(cell['source']) + "\n\n"

    turns = extract_turns_from_markdown(full_markdown)
    result = {
        "turns": turns,
        "dialogue_metadata": {
            "id": dialogue_id or os.path.basename(ipynb_path),
            "length": len(turns)
        }
    }
    return result


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