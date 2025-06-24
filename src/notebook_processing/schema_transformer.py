import uuid
from datetime import datetime
import os
import copy

def generate_file_metadata() -> dict:
    """Return the hardcoded fileMetadata block. Some fields can be derived from the filename if needed."""
    return {
        "simId": "CPM-15031",
        "channel": "turing",
        "vendor": "3P",
        "batchFileId": "4ff35133d737f13ed6eba8d561d51c71",
        "serviceOrderId": "SO-64051",
        "workType": "NA",
        "workflowName": "Verifiable Instruction Following - dialogue generation - 3P",
        "sensitiveContentExposure": "NA",
        "locale": "en_US",
        "customerInputFileName": "dca394b2-da28-4218-b827-aade70011b23",
        "annotationType": "NA",
        "conventionLink": "NA",
        "inputDataType": "NA",
        "outputDataType": "NA",
        "customerID": "1107",
        "ingestionDate": "2025-06-09",
        "workstream": "NA",
        "workitemsCount": 1000
    }

def notebook_to_workitem(parsed_notebook: dict, notebook_filename: str) -> dict:
    """Transform the parsed notebook dict into a workitem as per the new schema."""
    # Generate a unique workItemId and taskId for demo
    work_item_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    workflow = "Verifiable Instruction Following - dialogue generation - 3P"
    locale = "en_US"
    dialogue_length = str(parsed_notebook.get("dialogue_metadata", {}).get("dialogue_length", ""))
    # Compose turnInputData and turnLevelOutput
    turn_level_output = []
    turns = parsed_notebook.get("turns", [])
    for turn in turns:
        # Compose responses array
        responses = []
        for k, v in turn.items():
            if k.endswith("_response") or k == "response":
                model_id = k.replace("_response", "").replace("response", "Nova Premier/None").strip("_") or "Nova Premier/None"
                responded_by_role = "Bot" if "assistant" in k or k == "response" else "User"
                responses.append({
                    "modelId": model_id,
                    "responseText": v,
                    "respondedByRole": responded_by_role,
                    "errorMessage": ""
                })
        # Compose instructions as string
        instructions = turn.get("instructions", {}).get("instructions", [])
        instructions_str = str(instructions)
        instruction_change = turn.get("instructions", {}).get("instruction_change", [])
        turn_level_output.append({
            "prompt-turn": {
                "prompt": turn.get("prompt", ""),
                "promptedByRole": "User",
                "selectedResponseIndex": 1,
                "responses": responses
            },
            "instructions": instructions_str,
            "instruction_change": instruction_change
        })
    # Compose taskAnswers
    task_answers = [{
        "turnLevelOutput": turn_level_output,
        "language": locale,
        "dialogue_length": dialogue_length,
        "task_type": "overall task type for the dialogue",
        "task_difficulty": "medium"
    }]
    # Compose the inner dict with a random UUID key (as in your schema example)
    uuid_key = str(uuid.uuid4())
    workitem_inner = {
        uuid_key: [{
            "data": {
                "taskAnswers": task_answers
            },
            "metadata": {
                "taskId": task_id,
                "operationType": "LABELLING",
                "labelledTimestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.0Z"),
                "obfuscatedDaAlias": "author ID"
            }
        }]
    }
    # Compose the workitem
    workitem = {
        "workItemId": work_item_id,
        "workflow": workflow,
        "locale": locale,
        "inputData": {
            "turnInputData": []
        },
        "metadata": {
            "field": "whatever additional metadata"
        }
    }
    workitem.update(workitem_inner)
    return workitem

def convert_to_final_schema(parsed_notebook: dict, notebook_filename: str) -> dict:
    """Return the final output JSON as per the required schema."""
    return {
        "fileMetadata": generate_file_metadata(notebook_filename),
        "workitems": [notebook_to_workitem(parsed_notebook, notebook_filename)]
    } 