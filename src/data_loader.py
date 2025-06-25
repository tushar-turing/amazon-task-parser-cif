import json

instruction_json = r'instruction.json'
conflicting_instructions_json = r'conflicting_instructions.json'

with open(instruction_json, 'r') as tfile:
    template_json = json.load(tfile)

with open(conflicting_instructions_json, 'r') as file:
    conflict_dict = json.load(file)
