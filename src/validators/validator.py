import re
import string
import json
from typing import Dict, List, Tuple, Any

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

CONTRADICTING_PAIRS = {
    "change_case:all_caps": [
        "change_case:lowercase",
        "change_case:alternating",
        "change_case:first_letter_cap",
        "change_case:all_caps_target"
    ],
    "change_case:lowercase": [
        "change_case:all_caps",
        "change_case:alternating",
        "change_case:first_letter_cap",
        "change_case:lowercase_target"
    ],
    "change_case:alternating": [
        "change_case:all_caps",
        "change_case:lowercase",
        "change_case:first_letter_cap",
        "change_case:alternating_target"
    ],
    "change_case:first_letter_cap": [
        "change_case:all_caps",
        "change_case:lowercase",
        "change_case:alternating",
        "change_case:first_letter_cap_target"
    ],
    "change_case:all_caps_target": ["change_case:all_caps"],
    "change_case:lowercase_target": ["change_case:lowercase"],
    "change_case:alternating_target": ["change_case:alternating"],
    "change_case:first_letter_cap_target": ["change_case:first_letter_cap"],
    "detectable_format:json_format": [
        "detectable_format:multiple_sections",
        "detectable_format:numbered_list",
        "detectable_format:number_bullet_lists",
        "detectable_format:title",
        "startend:quotation",
        "startend:wrap_checker",
        "startend:start_checker",
        "startend:end_checker"
    ],
    "detectable_format:multiple_sections": ["detectable_format:json_format"],
    "detectable_format:numbered_list": ["detectable_format:json_format"],
    "detectable_format:number_bullet_lists": ["detectable_format:json_format"],
    "detectable_format:title": [
        "detectable_format:json_format",
        "startend:quotation",
        "startend:wrap_checker",
        "startend:start_checker"
    ],
    "startend:quotation": [
        "startend:wrap_checker",
        "startend:start_checker",
        "startend:end_checker",
        "detectable_format:json_format",
        "detectable_format:title"
    ],
    "startend:wrap_checker": [
        "startend:quotation",
        "startend:start_checker",
        "startend:end_checker",
        "detectable_format:json_format",
        "detectable_format:title"
    ],
    "startend:start_checker": [
        "startend:quotation",
        "startend:wrap_checker",
        "detectable_format:title",
        "detectable_format:json_format"
    ],
    "startend:end_checker": [
        "startend:quotation",
        "startend:wrap_checker",
        "detectable_format:json_format"
    ]
}

def is_strict_alternating(word: str) -> bool:
    """Check if a word has strictly alternating case."""
    letters = [c for c in word if c.isalpha()]
    return all(letters[i].isupper() != letters[i + 1].isupper() for i in range(len(letters) - 1))

def char_frequency(response: str, char: str) -> int:
    """Count frequency of a character in response."""
    return response.count(char)

def count_numbered_items(response: str) -> int:
    """Count number of numbered items in response."""
    return len(re.findall(r'^\s*\d+\.', response, re.MULTILINE))

def count_bullet_points(response: str) -> int:
    """Count number of bullet points in response."""
    return len(re.findall(r'^[*-•]\s', response, re.MULTILINE))

def count_placeholders(response: str) -> int:
    """Count number of placeholders in response."""
    return len(re.findall(r'\[.*?\]', response))

def count_all_caps_words(response: str) -> int:
    """Count number of all-caps words in response."""
    return sum(1 for w in response.split() if w.isupper())

def count_lowercase_words(response: str) -> int:
    """Count number of lowercase words in response."""
    return sum(1 for w in response.split() if w.islower())

def word_frequency(response: str, word: str) -> int:
    """Count frequency of a word in response."""
    words = re.findall(r'[^\s]+', response.lower())
    return words.count(word.lower())

def keyword_frequency(response: str, keyword: str) -> int:
    """Count frequency of a keyword in response, ensuring it's a full word or phrase."""
    pattern = r'\b' + re.escape(keyword.strip()) + r'\b'
    return len(re.findall(pattern, response, flags=re.IGNORECASE))

def validate_instruction(response: str, inst_type: str, kwargs: Dict[str, Any], all_instructions: Dict = None) -> Tuple[bool, str]:
    """Validate a response against a specific instruction type and its kwargs."""
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
            pattern = rf'\b{target_escaped}\b'
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
            missing = [kw for kw in kwargs["keywords"] if keyword_frequency(response, kw) == 0]
            return (not missing, "No error" if not missing else f"Missing keyword(s): {missing}")

        if inst_type == "keywords:frequency":
            keyword = kwargs["keyword"].strip().lower()
            count = keyword_frequency(response, keyword)
            rel = kwargs["relation"]
            val = kwargs["frequency"]
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (
                valid,
                "No error" if valid else f"Expected {rel} {val} of '{keyword}', found {count}."
            )

        if inst_type == "keywords:forbidden_words":
            present = [w for w in kwargs["forbidden_words"] if keyword_frequency(response, w)]
            return (not present, "No error" if not present else f"Forbidden words found: {present}")

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
            valid = eval(f"{count} {'>=' if rel == 'at least' else '==' if rel == 'equal to' else '<'} {val}")
            return (valid, "No error" if valid else f"Expected {rel} {val} words, found {count}.")

        if inst_type == "startend:start_checker":
            starts_correctly = response.lstrip(string.punctuation + " ").lower().startswith(kwargs.get("start_phrase", "").lower())
            return (
                starts_correctly,
                "No error" if starts_correctly else "Response does not start with required phrase."
            )

        if inst_type == "startend:end_checker":
            required = kwargs["end_phrase"].strip()
            # Check if required phrase ends with punctuation
            ends_with_punctuation = required[-1] in string.punctuation if required else False
            
            # Get the actual end of the response
            actual_words = response.lstrip(string.punctuation).strip().split()
            if not actual_words:
                return (False, "Empty response")
                
            # If required phrase ends with punctuation, we need exact match
            if ends_with_punctuation:
                actual_phrase = " ".join(actual_words[-len(required.split()):])
                if actual_phrase.lower() != required.lower():
                    return (
                        False,
                        f"End phrase mismatch: expected '{required}', but found '{actual_phrase}'"
                    )
            else:
                # If no punctuation, strip trailing punctuation and whitespace
                actual_phrase = " ".join(actual_words).rstrip(string.punctuation + " ")[-len(required):]
                if actual_phrase.lower() != required.lower():
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

def check_contradicting_instructions(instructions_list: List[Dict]) -> List[Dict]:
    """Check for contradicting instruction IDs in the list (order-insensitive)."""
    errors, seen_pairs = set(), set()
    # Collect all instruction IDs
    ids = {inst["instruction_id"] for inst in instructions_list if isinstance(inst, dict) and "instruction_id" in inst}

    # Check each instruction for conflicts
    for instr_id in ids:
        for conflicting_id in CONTRADICTING_PAIRS.get(instr_id, []):
            pair = frozenset([instr_id, conflicting_id])
            if conflicting_id in ids and pair not in seen_pairs:
                errors.add(f"{instr_id} and {conflicting_id} are contradicting")
                seen_pairs.add(pair)

    return list(errors)

def validate_instruction_schema(instructions: Dict) -> List[Dict]:
    """Validate the schema of instructions against expected arguments and check for contradicting instructions."""
    mismatches = []
    
    # Validate metadata field
    metadata = instructions.get("metadata", [])
    if not isinstance(metadata, list):
        mismatches.append({
            "field": "metadata",
            "expected": "list",
            "actual": type(metadata).__name__
        })
    
    # Validate instructions array
    instructions_list = instructions.get("instructions", [])
    if not isinstance(instructions_list, list):
        mismatches.append({
            "field": "instructions",
            "expected": "list",
            "actual": type(instructions_list).__name__
        })
        return mismatches

    # Check for contradicting instructions
    contradiction_errors = check_contradicting_instructions(instructions_list)
    mismatches.extend(contradiction_errors)


    # Validate each instruction object
    for i, inst in enumerate(instructions_list):
        if not isinstance(inst, dict):
            mismatches.append({
                "instruction_index": i,
                "expected": "dict",
                "actual": type(inst).__name__
            })
            continue

        # Check for required instruction_id field
        if "instruction_id" not in inst:
            mismatches.append({
                "instruction_index": i,
                "missing_field": "instruction_id"
            })
            continue

        # Validate kwargs against expected arguments
        expected_args = set(EXPECTED_ARGUMENTS.get(inst["instruction_id"], []))
        actual_args = set(k for k in inst.keys() if k != "instruction_id")

        if expected_args != actual_args:
            mismatches.append({
                "instruction": inst["instruction_id"],
                "expected_args": sorted(expected_args),
                "actual_args": sorted(actual_args)
            })

    return mismatches 