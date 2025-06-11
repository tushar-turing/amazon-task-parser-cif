# Source Code Directory

This directory contains the main source code for the Turing Amazon Task Parser VIF project.

## Directory Structure

- `main.py`: The main entry point of the application that handles batch processing of notebooks and validation
- `app.py`: Streamlit web interface for the application
- `requirements.txt`: Python package dependencies
- `validators/`: Contains validation logic for instructions and responses
  - `validator.py`: Core validation functions and schema definitions
- `notebook_processing/`: Contains notebook processing and conversion logic
  - `processor.py`: Functions for processing Jupyter notebooks and converting them to the required format

## Main Components

### Main Script (`main.py`)

- Handles batch processing of Jupyter notebooks
- Converts notebooks to JSON format
- Runs validation on the converted output
- Generates validation reports

### Streamlit Interface (`app.py`)

- Provides a user-friendly web interface
- Supports batch processing of multiple notebooks
- Allows single file validation
- Displays results in an interactive format
- Features:
  - File upload interface
  - Progress indicators
  - JSON result viewer
  - Error handling and reporting

### Validators

The validation system checks:

- Instruction compliance
- Response format and content
- Schema validation
- Custom validation rules

### Notebook Processing

The notebook processing system:

- Reads Jupyter notebook files
- Extracts dialogue and instruction data
- Converts to a standardized JSON format
- Handles metadata and structure preservation

## Usage

### Command Line

The main script can be run from the command line:

```bash
python main.py <input_directory>
```

Where `<input_directory>` should contain the Jupyter notebook files to be processed.

### Web Interface

To run the Streamlit interface:

```bash
streamlit run app.py
```

This will start a local web server and open the interface in your default browser. You can then:

1. Upload Jupyter notebooks for batch processing
2. Upload individual JSON files for validation
3. View results in an interactive format
