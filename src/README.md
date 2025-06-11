# Source Code Directory

This directory contains the main source code for the Turing Amazon Task Parser VIF project.

## Directory Structure

- `main.py`: The main entry point of the application that handles batch processing of notebooks and validation
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

The main script can be run from the command line:

```bash
python main.py <input_directory>
```

Where `<input_directory>` should contain the Jupyter notebook files to be processed.
