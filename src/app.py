import streamlit as st
import os
import json
from pathlib import Path
import tempfile
from main import run_validation, run_batch_processing
from validators.validator import validate_instruction

st.set_page_config(
    page_title="Turing Amazon Task Parser VIF",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("Turing Amazon Task Parser VIF")
    st.markdown("Process and validate Jupyter notebooks containing Turing Amazon task data.")

    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Choose a page", ["Notebook Processing and Validation", "Single Cell Validation"])

    if page == "Notebook Processing and Validation":
        show_batch_processing()
    else:
        show_single_cell_validation()

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
        help="Paste the assistant's response text here"
    )

    # Input for Instructions JSON
    instructions_json = st.text_area(
        "Instructions JSON",
        height=200,
        help="Paste the instructions JSON following the schema above"
    )

    if st.button("Validate Cell"):
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

if __name__ == "__main__":
    main() 