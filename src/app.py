import streamlit as st
import os
import json
from pathlib import Path
import tempfile
from main import run_validation, run_batch_processing
from validators.validator import validate_instruction, check_contradicting_instructions, CONTRADICTING_PAIRS
import requests

st.set_page_config(
    page_title="Turing Amazon Task Parser VIF",
    page_icon="📊",
    layout="wide"
)

def call_nova_api(user_content, system_content="You are a chatbot", temperature=0.7, seed=42, top_p=1, top_k=40, max_tokens=1000):
    url = "https://kong.turing.com/api/llm-gateway"
    headers = {
        "x-api-key": "sk_key_snow_b8b48aff-ddc4-4ea2-a5f5-28311f0be068",
        "x-api-gw-key": "0c015800-dcba-448d-94bb-d01a56b0d22c",
        "Authorization": "Basic YWRtaW46VHVyaW5nQDEyMw==",
        "Content-Type": "application/json"
    }
    payload = {
        "modelName": "us.amazon.nova-premier-v1:0",
        "provider": "Amazon",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ],
        "params": {
            "temperature": temperature,
            "seed": seed,
            "top_p": top_p,
            "top_k": top_k,
            "max_tokens": max_tokens
        },
        "images": []
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        # Nova returns: {"choices": [{"message": {"content": ...}}]}
        return data["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"

def main():
    st.title("Turing Amazon Task Parser VIF")
    st.markdown("Process and validate Jupyter notebooks containing Turing Amazon task data.")
    # Tabs
    tab2, tab1, tab3, tab4 = st.tabs([
        "Validation (Single Turn)",
        "Validation (Batch/Notebook)",
        "Nova (Single Turn)",
        "Nova (Notebook/Batch)"
    ])
    with tab1:
        show_batch_processing()
    with tab2:
        show_single_cell_validation()
    with tab3:
        st.subheader("Nova Model: Single Turn Test & Validation")
        st.markdown("Test a prompt against the Nova model and validate the result.")
        show_nova_single_turn()
    with tab4:
        st.subheader("Nova Model: Batch Test & Validation")
        st.markdown("Upload a Jupyter notebook, run each turn through Nova, and validate the results.")
        show_nova_batch()

def show_batch_processing():
    st.header("Notebook Processing and Validation")
    st.markdown("Process and validate a single or multiple Jupyter notebooks.")

    uploaded_files = st.file_uploader(
        "Upload Jupyter notebooks",
        type=['ipynb'],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Process Notebooks"):
            with st.spinner("Processing notebooks..."):
                # Create a temporary directory for processing
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save uploaded files
                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                    # Process the notebooks
                    run_batch_processing(temp_dir, temp_dir)

                    # Display results
                    st.success("Processing complete!")
                    
                    # Show results for each file
                    for uploaded_file in uploaded_files:
                        base_name = Path(uploaded_file.name).stem
                        result_dir = os.path.join(temp_dir, base_name)
                        
                        if os.path.exists(result_dir):
                            st.subheader(f"Validation Report for {uploaded_file.name}")
                            
                            # Display validation report
                            validation_path = os.path.join(result_dir, "validation_report.json")
                            if os.path.exists(validation_path):
                                with open(validation_path, 'r', encoding='utf-8') as f:
                                    validation_data = json.load(f)
                                st.json(validation_data)
                            # Display metadata change report
                            metadata_report_path = os.path.join(result_dir, "metadata_change_report.json")
                            if os.path.exists(metadata_report_path):
                                st.markdown("#### Metadata Change Report")
                                with open(metadata_report_path, 'r', encoding='utf-8') as f:
                                    metadata_report = json.load(f)
                                st.json(metadata_report)

def show_single_cell_validation():
    st.header("Single Cell Validation")
    st.markdown("""
    Validate a single cell's assistant response and instructions.
    
    The instructions should follow this JSON schema:
    ```json
    {
      "metadata": ["add"],
      "instructions": [
        {
          "instruction_id": "",
          "kwarg1_name": "kwarg1_value",
          "kwarg2_name": "kwarg2_value"
        }
      ]
    }
    ```
    """)

    # Input for Assistant Response
    assistant_response = st.text_area(
        "Assistant Response",
        height=200,
        help="Paste the assistant's response text here",
        key="1"
    )

    # Input for Instructions JSON
    instructions_json = st.text_area(
        "Instructions JSON",
        height=200,
        help="Paste the instructions JSON following the schema above",
        key="2"
    )

    if st.button("Validate Cell", type="primary"):
        if not assistant_response or not instructions_json:
            st.error("Please provide both Assistant Response and Instructions JSON")
            return

        with st.spinner("Validating cell..."):
            try:
                # Parse instructions JSON
                instructions = json.loads(instructions_json)
                
                # Validate schema
                if not isinstance(instructions, dict):
                    st.error("Instructions must be a JSON object")
                    return
                    
                if "metadata" not in instructions or "instructions" not in instructions:
                    st.error("Instructions must contain 'metadata' and 'instructions' fields")
                    return
                    
                if not isinstance(instructions["metadata"], list):
                    st.error("'metadata' must be a list")
                    return
                    
                if not isinstance(instructions["instructions"], list):
                    st.error("'instructions' must be a list")
                    return
                    
                for instruction in instructions["instructions"]:
                    if not isinstance(instruction, dict):
                        st.error("Each instruction must be an object")
                        return
                    if "instruction_id" not in instruction:
                        st.error("Each instruction must have an 'instruction_id' field")
                        return
                    
                contradiction_errors = check_contradicting_instructions(instructions["instructions"])
                if contradiction_errors:
                    st.error("Contradicting instructions found: " + str(contradiction_errors))
                    return

                # Validate each instruction
                results = []
                for instruction in instructions["instructions"]:
                    inst_id = instruction["instruction_id"]
                    # Remove instruction_id from kwargs
                    kwargs = {k: v for k, v in instruction.items() if k != "instruction_id"}
                    valid, message = validate_instruction(assistant_response, inst_id, kwargs, instructions)
                    results.append({
                        "instruction": inst_id,
                        "status": "Passed" if valid else "Failed",
                        "message": message
                    })

                # Display results
                st.success("Validation complete!")
                st.json({
                    "response": assistant_response[:100] + "..." if len(assistant_response) > 100 else assistant_response,
                    "results": results
                })

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {str(e)}")
            except Exception as e:
                st.error(f"Error during validation: {str(e)}")

    # Add button to show contradicting pairs
    if st.button("Show Contradicting Instruction Pairs"):
        pairs = []
        for pair in CONTRADICTING_PAIRS:
            pair_list = list(pair)
            if len(pair_list) == 2:
                pairs.append({"Instruction 1": pair_list[0], "Instruction 2": pair_list[1]})
            elif len(pair_list) == 1:
                pairs.append({"Instruction 1": pair_list[0], "Instruction 2": ""})
        st.markdown("#### Contradicting Instruction Pairs")
        st.table(pairs)

def show_nova_single_turn():
    st.header("Nova Model: Single Turn Test & Validation")
    st.markdown("Test a prompt against the Nova model and validate the result.")
    user_prompt = st.text_area("User Prompt", height=100)
    instructions_json = st.text_area("Instructions JSON", height=200, help="Paste the instructions JSON following the schema above")
    # Disable button and add tooltip
    st.button("Run Nova & Validate", key="nova_single", disabled=True, help="Coming soon")
    # if st.button("Run Nova & Validate", key="nova_single"):
    #     if not user_prompt or not instructions_json:
    #         st.error("Please provide both User Prompt and Instructions JSON")
    #         return
    #     try:
    #         instructions = json.loads(instructions_json)
    #     except Exception as e:
    #         st.error(f"Invalid JSON: {e}")
    #         return
    #     with st.spinner("Calling Nova model..."):
    #         nova_response = call_nova_api(user_prompt)
    #     st.subheader("Nova Model Response")
    #     st.write(nova_response)
    #     # Validate
    #     try:
    #         # Schema checks (reuse from single cell validation)
    #         if not isinstance(instructions, dict):
    #             st.error("Instructions must be a JSON object")
    #             return
    #         if "metadata" not in instructions or "instructions" not in instructions:
    #             st.error("Instructions must contain 'metadata' and 'instructions' fields")
    #             return
    #         if not isinstance(instructions["metadata"], list):
    #             st.error("'metadata' must be a list")
    #             return
    #         if not isinstance(instructions["instructions"], list):
    #             st.error("'instructions' must be a list")
    #             return
    #         for instruction in instructions["instructions"]:
    #             if not isinstance(instruction, dict):
    #                 st.error("Each instruction must be an object")
    #                 return
    #             if "instruction_id" not in instruction:
    #                 st.error("Each instruction must have an 'instruction_id' field")
    #                 return
    #         results = []
    #         for instruction in instructions["instructions"]:
    #             inst_id = instruction["instruction_id"]
    #             kwargs = {k: v for k, v in instruction.items() if k != "instruction_id"}
    #             valid, message = validate_instruction(nova_response, inst_id, kwargs, instructions)
    #             results.append({
    #                 "instruction": inst_id,
    #                 "status": "Passed" if valid else "Failed",
    #                 "message": message
    #             })
    #         st.success("Validation complete!")
    #         st.json({
    #             "response": nova_response[:100] + "..." if len(nova_response) > 100 else nova_response,
    #             "results": results
    #         })
    #     except Exception as e:
    #         st.error(f"Validation error: {e}")

def show_nova_batch():
    st.header("Nova Model: Batch Test & Validation")
    st.markdown("Upload a Jupyter notebook, run each turn through Nova, and validate the results.")
    uploaded_file = st.file_uploader("Upload Jupyter notebook", type=["ipynb"], key="nova_batch")
    # Disable button and add tooltip
    st.button("Run Nova Batch", key="nova_batch_btn", disabled=True, help="Coming soon")
    # if uploaded_file and st.button("Run Nova Batch", key="nova_batch_btn"):
    #     with st.spinner("Processing notebook and calling Nova model for each turn..."):
    #         # Save to temp file
    #         with tempfile.NamedTemporaryFile(delete=False, suffix=".ipynb") as tmp:
    #             tmp.write(uploaded_file.getbuffer())
    #             tmp_path = tmp.name
    #         from notebook_processing.processor import process_notebook
    #         notebook_data = process_notebook(tmp_path)
    #         results = []
    #         for turn in notebook_data["turns"]:
    #             prompt = turn.get("prompt", "")
    #             instructions = turn.get("instructions", {})
    #             if not prompt or not instructions:
    #                 continue
    #             try:
    #                 nova_response = call_nova_api(prompt)
    #             except Exception as e:
    #                 nova_response = f"Nova error: {e}"
    #             turn_result = {"prompt": prompt, "instructions": instructions, "nova_response": nova_response, "validation": []}
    #             # Validate
    #             try:
    #                 if not isinstance(instructions, dict):
    #                     turn_result["validation"].append({"error": "Instructions must be a JSON object"})
    #                 elif "metadata" not in instructions or "instructions" not in instructions:
    #                     turn_result["validation"].append({"error": "Instructions must contain 'metadata' and 'instructions' fields"})
    #                 elif not isinstance(instructions["metadata"], list):
    #                     turn_result["validation"].append({"error": "'metadata' must be a list"})
    #                 elif not isinstance(instructions["instructions"], list):
    #                     turn_result["validation"].append({"error": "'instructions' must be a list"})
    #                 else:
    #                     for instruction in instructions["instructions"]:
    #                         if not isinstance(instruction, dict) or "instruction_id" not in instruction:
    #                             turn_result["validation"].append({"error": "Each instruction must be an object with 'instruction_id'"})
    #                             continue
    #                         inst_id = instruction["instruction_id"]
    #                         kwargs = {k: v for k, v in instruction.items() if k != "instruction_id"}
    #                         valid, message = validate_instruction(nova_response, inst_id, kwargs, instructions)
    #                         turn_result["validation"].append({
    #                             "instruction": inst_id,
    #                             "status": "Passed" if valid else "Failed",
    #                             "message": message
    #                         })
    #             except Exception as e:
    #                 turn_result["validation"].append({"error": f"Validation error: {e}"})
    #             results.append(turn_result)
    #         st.success("Batch Nova validation complete!")
    #         for i, res in enumerate(results):
    #             st.markdown(f"#### Turn {i+1}")
    #             st.markdown(f"**Prompt:** {res['prompt']}")
    #             st.markdown(f"**Nova Response:** {res['nova_response']}")
    #             st.json(res["validation"])

if __name__ == "__main__":
    main() 