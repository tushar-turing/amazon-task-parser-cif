# Amazon File Processor Script

This script is designed to process Jupyter Notebook (`.ipynb`) files and format them into JSON. It can be run from the command line with a specified directory containing Jupyter Notebooks as input. The script will take the `.ipynb` files from the provided directory and output their formatted JSON versions.

## Requirements

* Python 3.x
* `nbformat` library (for handling Jupyter notebook files)

## Installation

1. Clone or download the repository.
2. Install the required dependencies:

   ```bash
   pip install nbformat
   ```

## Usage

### Command to Run the Script

To use the script, run the following command in the terminal:

```bash
python process_samples.py <path-to-files>
```

### Parameters:

* `<path-to-files>`: The directory containing the Jupyter Notebook files (`.ipynb`) you want to process. Replace this with the path to the folder where your `.ipynb` files are located.

### Output:

* The script will process all the `.ipynb` files in the specified directory and output them as JSON objects.

## How It Works

* The script reads each Jupyter Notebook file from the specified directory.
* It formats the contents of each notebook into a clean, structured JSON format.
* The processed JSON output can be used for further analysis, storage, or conversion.

## Example

Given the following structure:

```
./samples/
    sample1.ipynb
    sample2.ipynb
```

Running the command:

```bash
python process_samples.py ./samples
```

Will output the formatted JSON for each notebook, typically with the `.json` extension, in the same directory or a specified output location.

## Error Handling

If the script encounters any invalid `.ipynb` files or files that are not valid Jupyter Notebooks, it will display an error message and skip those files.
