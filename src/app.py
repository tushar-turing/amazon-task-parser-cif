import streamlit as st
import os
import json
from pathlib import Path
import tempfile
from main import run_validation, run_batch_processing

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
    page = st.sidebar.radio("Choose a page", ["Notebook Processing and Validation"])

    if page == "Notebook Processing and Validation":
        show_batch_processing()

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
if __name__ == "__main__":
    main() 