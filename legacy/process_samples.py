import nbformat
import json
import re
import string
import os
import sys
from collections import defaultdict

def get_cell_text(cell):
    return ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']

def detect_tag(cell_text):
    match = re.match(r"\*\*\[(.*?)\]\*\*", cell_text.strip())
    if not match:
        return None, None
    tag = match.group(1)
    if tag == "user": return "user", None
    if tag == "turn_metadata": return "metadata", None
    if tag == "assistant": return "assistant", None
    if tag.startswith("assistant_"): return "assistant_model", tag.split("_", 1)[1]
    return None, None

def extract_json_from_metadata_cell(source_text):
    try:
        match = re.search(r"```(?:json)?\n(.*?)```", source_text, re.DOTALL)
        if not match: return {}
        json_str = match.group(1).strip()
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON error: {e}")
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
                "instruction_id_list": instruction_data.get("instruction_id_list", []),
                "kwargs": instruction_data.get("kwargs", [])
            }
        elif tag_type == "assistant":
            current_turn["response"] = content
        elif tag_type == "assistant_model":
            assistant_models[model_tag] = content

    if current_turn:
        for k, v in assistant_models.items():
            current_turn[f"{k}_response"] = v
        turns.append(current_turn)

    # Map of expected kwargs for each instruction ID
    EXPECTED_ARGUMENTS = {
        "change_case:all_caps": [],
        "change_case:lowercase": [],
        "change_case:alternating": [],
        "change_case:first_letter_cap": [],
        "change_case:capital_word_frequency": ["capital_relation", "capital_frequency"],
        "change_case:lowercase_word_frequency": ["lowercase_relation", "lowercase_frequency"],
        "change_case:all_caps_target": ["target_string"],
        "change_case:lowercase_target": ["target_string"],
        "change_case:alternating_target": ["target_string"],
        "change_case:first_letter_cap_target": ["target_string"],
        "detectable_content:number_placeholders": ["relation", "num_placeholders"],
        "detectable_content:postscript": ["postscript_marker"],
        "detectable_format:json_format": [],
        "detectable_format:multiple_sections": ["section_splitter", "relation", "num_sections"],
        "detectable_format:numbered_list": ["relation", "num_numbered_items"],
        "detectable_format:number_bullet_lists": ["relation", "num_bullets"],
        "detectable_format:title": [],
        "keywords:existence": ["keywords"],
        "keywords:frequency": ["keyword", "relation", "frequency"],
        "keywords:forbidden_words": ["forbidden_words"],
        "keywords:letter_frequency": ["letter", "let_relation", "let_frequency"],
        "punctuation:no_comma": [],
        "length_constraints:number_characters": ["relation", "num_chars"],
        "length_constraints:number_words": ["relation", "num_words"],
        "length:max_word_count": ["max_words"],
        "startend:start_checker": ["start_phrase"],
        "startend:end_checker": ["end_phrase"],
        "startend:wrap_checker": ["wrap_phrase"],
        "startend:quotation": []
    }

    def validate_instruction_schema(instructions):
        mismatches = []
        ids = instructions.get("instruction_id_list", [])
        kwargs_list = instructions.get("kwargs", [])

        for i, inst in enumerate(ids):
            expected_args = set(EXPECTED_ARGUMENTS.get(inst, []))
            actual_args = set(kwargs_list[i].keys()) if i < len(kwargs_list) else set()

            if expected_args != actual_args:
                mismatches.append({
                    "instruction": inst,
                    "expected_args": sorted(expected_args),
                    "actual_args": sorted(actual_args)
                })

        return mismatches

    # === Instruction schema check ===
    all_mismatches = []

    for turn_index, turn in enumerate(turns):
        if "instructions" in turn:
            mismatches = validate_instruction_schema(turn["instructions"])
            if mismatches:
                all_mismatches.append({
                    "turn_index": turn_index + 1,
                    "prompt": turn['prompt'][:10],
                    "mismatches": mismatches
                })

    if all_mismatches:
        print(f"\n❌ Instruction schema mismatches found in the notebook:")
        for entry in all_mismatches:
            print(f"\n📌 Turn {entry['turn_index']}: {entry['prompt']}...")
            for m in entry['mismatches']:
                print(f"- Instruction: {m['instruction']}")
                print(f"  Expected: {m['expected_args']}")
                print(f"  Found:    {m['actual_args']}")
    else:
        print("✅ Instruction IDs and kwargs are valid for all turns.")

    return {
        "turns": turns,
        "dialogue_metadata": {
            "dialogue_id": dialogue_id or os.path.basename(file_path),
            "dialogue_length": len(turns)
        }
    }

# === Validators (simplified core logic) ===
def is_strict_alternating(word):
    letters = [c for c in word if c.isalpha()]
    return all(letters[i].isupper() != letters[i + 1].isupper() for i in range(len(letters) - 1))

def char_frequency(response, char):
    return response.count(char)

def count_numbered_items(response):
    return len(re.findall(r'^\s*\d+\.', response, re.MULTILINE))

def count_bullet_points(response):
    # Only count bullet points at top-level (start of line, not indented)
    return len(re.findall(r'^[*-•]\s', response, re.MULTILINE))

def count_placeholders(response):
    return len(re.findall(r'\[.*?\]', response))

def count_all_caps_words(response):
    return sum(1 for w in response.split() if w.isupper())

def count_lowercase_words(response):
    return sum(1 for w in response.split() if w.islower())

def word_frequency(response, word):
    words = re.findall(r'\b\w+\b', response.lower())
    return words.count(word.lower())

def validate_instruction(response, inst_type, kwargs, all_instructions=None):
    try:
        if inst_type == "change_case:all_caps":
            return (response.isupper(), "No error" if response.isupper() else "Response is not all uppercase.")

        if inst_type == "change_case:lowercase":
            return (response.islower(), "No error" if response.islower() else "Response is not all lowercase.")

        if inst_type == "change_case:alternating":
            valid = all(is_strict_alternating(w) for w in response.split() if w.isalpha())
            return (valid, "No error" if valid else "Response is not strictly alternating caps.")

        if inst_type == "change_case:first_letter_cap":
            valid = all(w.istitle() for w in response.split() if w.isalpha())
            return (valid, "No error" if valid else "Not all words are first-letter capitalized.")

        if inst_type == "change_case:capital_word_frequency":
            count = count_all_caps_words(response)
            rel, val = kwargs['capital_relation'], kwargs['capital_frequency']
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} all-cap words, found {count}.")

        if inst_type == "change_case:lowercase_word_frequency":
            count = count_lowercase_words(response)
            rel, val = kwargs['lowercase_relation'], kwargs['lowercase_frequency']
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} lowercase words, found {count}.")

        if "_target" in inst_type:
            target = kwargs["target_string"].strip().lower()
            target_escaped = re.escape(target)

            # Handle multi-word phrases with optional quotes
            pattern = rf'(["\']?{target_escaped}["\']?)'
            matches = re.findall(pattern, response, re.IGNORECASE)

            if not matches:
                return (False, f"Target '{target}' not found in response.")

            for match in matches:
                raw_text = match.strip('"').strip("'")

                if inst_type == "change_case:all_caps_target" and not raw_text.isupper():
                    return (False, f"'{raw_text}' should be ALL CAPS.")
                elif inst_type == "change_case:lowercase_target" and not raw_text.islower():
                    return (False, f"'{raw_text}' should be all lowercase.")
                elif inst_type == "change_case:alternating_target" and not is_strict_alternating(raw_text):
                    return (False, f"'{raw_text}' is not in alternating caps.")
                elif inst_type == "change_case:first_letter_cap_target" and not raw_text.istitle():
                    return (False, f"'{raw_text}' is not first-letter capitalized.")

            return (True, "No error")

        if inst_type == "detectable_content:number_placeholders":
            count = count_placeholders(response)
            rel, val = kwargs["relation"], kwargs["num_placeholders"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} placeholders, found {count}.")

        if inst_type == "detectable_content:postscript":
            marker = kwargs.get("postscript_marker", "PS:").strip()
            lines = response.strip().splitlines()
            for line in reversed(lines):
                if line.strip():
                    last_line = line.strip()
                    break
            else:
                last_line = ""

            has_postscript = last_line.startswith(marker) and len(last_line) > len(marker)
            return (
                has_postscript,
                "No error" if has_postscript else f"Postscript must start with '{marker}' and contain content. Found: '{last_line}'"
            )

        if inst_type == "detectable_format:json_format":
            try:
                json_part = response[response.find("{"):response.rfind("}")+1]
                json.loads(json_part)
                return (True, "No error")
            except:
                return (False, "Response is not valid JSON format.")

        if inst_type == "detectable_format:multiple_sections":
            splitter = kwargs.get("section_splitter", "").strip()
            rel = kwargs.get("relation")
            val = kwargs.get("num_sections")

            # Match lines that contain the splitter + a number, possibly with Markdown prefix like ### or whitespace
            pattern = rf"^\s*[#>*\-]*\s*{re.escape(splitter)}\s+\d+\b"
            sections = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)

            valid = eval(f"{len(sections)} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} sections, found {len(sections)}.")

        if inst_type == "detectable_format:numbered_list":
            count = count_numbered_items(response)
            rel, val = kwargs["relation"], kwargs["num_numbered_items"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} numbered items, found {count}.")

        if inst_type == "detectable_format:number_bullet_lists":
            count = count_bullet_points(response)
            rel, val = kwargs["relation"], kwargs["num_bullets"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} bullet points, found {count}.")

        if inst_type == "detectable_format:title":
            lines = response.strip().splitlines()
            found_title = any(line.strip().startswith("<<") and line.strip().endswith(">>") for line in lines)

            return (
                found_title,
                "No error" if found_title else "Title not wrapped in << >> on any line."
            )

        if inst_type == "keywords:existence":
            missing = [kw for kw in kwargs["keywords"] if kw.lower() not in response.lower()]
            return (not missing, "No error" if not missing else f"Missing keyword(s): {missing}")

        if inst_type == "keywords:frequency":
            keyword = kwargs["keyword"].strip().lower()
            matches = re.findall(rf'\b{re.escape(keyword)}\b', response, flags=re.IGNORECASE)
            count = len(matches)

            rel = kwargs["relation"]
            val = kwargs["frequency"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            
            return (
                valid,
                "No error" if valid else f"Expected {rel} {val} of '{keyword}', found {count}."
            )

        if inst_type == "keywords:forbidden_words":
            present = [w for w in kwargs["forbidden_words"] if w.lower() in response.lower()]
            return (not present, "No error" if not present else f"Forbidden words found: {present}")

        # letters are not case-sensitive
        if inst_type == "keywords:letter_frequency":
            letter = kwargs["letter"].lower()
            count = response.lower().count(letter)
            rel, val = kwargs["let_relation"], kwargs["let_frequency"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (
                valid,
                "No error" if valid else f"Expected {rel} {val} '{letter}' (case-insensitive), found {count}."
            )

        if inst_type == "punctuation:no_comma":
            return (',' not in response, "No error" if ',' not in response else "Commas found in response.")

        if inst_type == "length_constraints:number_characters":
            count = len(response)
            rel, val = kwargs["relation"], kwargs["num_chars"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} characters, found {count}.")

        if inst_type == "length_constraints:number_words":
            count = len(re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9_-]*\b', response))
            rel, val = kwargs["relation"], kwargs["num_words"]
            # print(f"    ↪ Word count (strict): {count}")  # Debug output
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} words, found {count}.")

        if inst_type == "startend:start_checker":
            starts_correctly = response.lstrip(string.punctuation + " ").startswith(kwargs.get("start_phrase", ""))
            return (
                starts_correctly,
                "No error" if starts_correctly else "Response does not start with required phrase."
            )

        if inst_type == "startend:end_checker":
            required = kwargs["end_phrase"].strip()

            # Get the last few words from the response, based on required length
            actual_words = response.strip().split()[-len(required.split()):]
            actual_phrase = " ".join(actual_words).strip().strip('"')

            # Compare full phrase (with punctuation)
            if actual_phrase != required:
                return (
                    False,
                    f"End phrase mismatch: expected '{required}', but found '{actual_phrase}'"
                )

            return (True, "No error")

        if inst_type == "startend:wrap_checker":
            wrap = kwargs["wrap_phrase"]
            return (response.strip().startswith(wrap) and response.strip().endswith(wrap),
                    "No error" if response.strip().startswith(wrap) else f"Not wrapped with: {wrap}")

        if inst_type == "startend:quotation":
            return (response.strip().startswith('"') and response.strip().endswith('"'),
                    "No error" if response.strip().startswith('"') else "Response not wrapped in double quotes.")

    except Exception as e:
        return (False, f"Validation error: {str(e)}")

    return (True, "No error")

# === Main Validation Function ===
def run_validation(input_json_path, output_log_path):
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dialogues = [data] if isinstance(data, dict) else data
    results = []

    for d_index, dialogue in enumerate(dialogues):
        dialogue_id = dialogue.get("dialogue_metadata", {}).get("dialogue_id", f"dialogue_{d_index}")
        for t_index, turn in enumerate(dialogue["turns"]):
            instructions = turn.get("instructions", {})
            ids = instructions.get("instruction_id_list", [])
            kwargs_list = instructions.get("kwargs", [])
            all_responses = {k: v for k, v in turn.items() if k.endswith("_response") or k == "response"}

            for label, response in all_responses.items():
                turn_results = []
                for i, inst_id in enumerate(ids):
                    kwargs = kwargs_list[i]
                    valid, message = validate_instruction(response, inst_id, kwargs, instructions)
                    turn_results.append({
                        "instruction": inst_id,
                        "status": "Passed" if valid else "Failed",
                        "message": message
                    })

                results.append({
                    "dialogue_id": dialogue_id,
                    "turn_index": t_index + 1,
                    "response_type": label,
                    "prompt": turn["prompt"][:100],
                    "results": turn_results
                })

    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ Validation complete. Log saved to: {output_log_path}")

# === Driver ===
def run_batch_processing(input_dir, output_base_dir):
    ipynb_files = [f for f in os.listdir(input_dir) if f.endswith(".ipynb")]
    if not ipynb_files:
        print("No .ipynb files found in input folder.")
        return

    for ipynb_file in ipynb_files:
        base_name = os.path.splitext(ipynb_file)[0]
        input_path = os.path.join(input_dir, ipynb_file)
        output_dir = os.path.join(output_base_dir, base_name)
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Convert notebook
        print(f"\n📘 Processing notebook: {ipynb_file}")
        converted = process_notebook(input_path, dialogue_id=base_name)
        converted_path = os.path.join(output_dir, "converted_output.json")
        with open(converted_path, "w", encoding="utf-8") as f:
            json.dump(converted, f, indent=2, ensure_ascii=False)
        print(f"✅ Converted JSON saved to: {converted_path}")

        # Step 2: Validate and write .json
        validation_txt_path = os.path.join(output_dir, "validation_report.json")
        run_validation(converted_path, validation_txt_path)

if __name__ == "__main__":
    input_dir = sys.argv[1]
    run_batch_processing(input_dir, input_dir)
