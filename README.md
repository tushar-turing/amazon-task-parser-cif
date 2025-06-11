# Turing Amazon Task Parser VIF

A Python-based tool for processing and validating Jupyter notebooks containing Turing Amazon task data. This tool helps in converting notebook-based task data into a standardized format and validating the content against predefined schemas and rules.

## Features

- Batch processing of Jupyter notebooks
- Conversion of notebook content to standardized JSON format
- Comprehensive validation of instructions and responses
- Detailed validation reports
- Support for multiple dialogue formats
- Schema-based validation

## Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/turing-amazon-task-parser-cif.git
cd turing-amazon-task-parser-cif/src
```

2. Install the required dependencies:

```bash
pip install -r src/requirements.txt
```

## Usage

1. Place your Jupyter notebook files in a directory
2. Run the parser:

```bash
python src/main.py <input_directory>
```

The tool will:

- Process all `.ipynb` files in the input directory
- Convert them to JSON format
- Run validation checks
- Generate validation reports

## Output

For each processed notebook, the tool creates a directory with:

- `converted_output.json`: The converted notebook content
- `validation_report.json`: Detailed validation results

## Project Structure

```
turing-amazon-task-parser-cif/
├── src/
│   ├── main.py
│   ├── requirements.txt
│   ├── validators/
│   └── notebook_processing/
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
