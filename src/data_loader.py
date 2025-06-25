import json
from pathlib import Path

# Define file paths using pathlib for cross-platform compatibility
instruction_json_path = Path('instruction.json')
conflicting_instructions_json_path = Path('conflicting_instructions.json')

try:
    # Read instruction.json
    with instruction_json_path.open('r') as tfile:
        template_json = json.load(tfile)

    # Read conflicting_instructions.json
    with conflicting_instructions_json_path.open('r') as file:
        conflict_dict = json.load(file)

    print("Files loaded successfully.")
    # You can now use `template_json` and `conflict_dict` as needed

except FileNotFoundError as e:
    print(f"File not found: {e.filename}")
except json.JSONDecodeError as e:
    print(f"Invalid JSON in file: {e.msg} at line {e.lineno}, column {e.colno}")
except Exception as e:
    print(f"Unexpected error: {e}")
