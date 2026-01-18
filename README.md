# P-RHO Matrix Processor

A PyQt5 GUI application for processing P-value and RHO correlation matrices from neuroimaging data. The tool filters significant correlations based on a customizable p-value threshold and exports results in formats compatible with brain connectivity visualization tools.

## Features

- Load paired P-value and RHO correlation matrix files (tab-separated .txt)
- Auto-detect matching RHO file when P-file is selected
- Adjustable p-value threshold (0.001 to 0.300)
- Optional RHO value inversion (multiply by -1)
- View significant pairs in an interactive table
- Export results as:
  - `.edge` file (matrix format for BrainNet Viewer)
  - `.xlsx` Excel file (long format with Region1, Region2, P-Value, RHO-Value)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/P-RHO-Processor.git
cd P-RHO-Processor
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python p_rho_processor.py
```

### Workflow

1. **Select Files**: Click "Browse P-file" to select your P-value matrix file. The application will automatically look for a matching RHO file (e.g., if you select `data-p-.txt`, it will search for `data-RHO-.txt`).

2. **Adjust Settings**:
   - Set the p-value threshold using the slider
   - Check/uncheck "Invert RHO values" as needed

3. **Process**: Click "Process Files" to filter significant correlations

4. **Export**: Enter an output name and click "Export .edge + .xlsx" to save results

## Input File Format

The application expects tab-separated text files with:
- Header row with region names
- Square correlation matrix

Example P-value file structure:
```
Group X corr_area X  Corrected Alpha Level: 0.3
	L.CAC	R.CAC	L.CMF	...
L.CAC	0	0.645	0.843	...
R.CAC	0.645	0	0.8208	...
...
```

## Sample Data

Sample P-value and RHO files are included in the `sample_data/` directory for testing.

## Brain Regions

The application includes 28 predefined brain region labels (bilateral):
- CAC (Caudal Anterior Cingulate)
- CMF (Caudal Middle Frontal)
- IP (Inferior Parietal)
- INS (Insula)
- IST (Isthmus Cingulate)
- MOF (Medial Orbitofrontal)
- MT (Middle Temporal)
- PHIP (Parahippocampal)
- PCG (Posterior Cingulate)
- PREC (Precuneus)
- RAC (Rostral Anterior Cingulate)
- RMF (Rostral Middle Frontal)
- SF (Superior Frontal)
- SP (Superior Parietal)

## Output

### Edge File (.edge)
A space-separated matrix file compatible with BrainNet Viewer. Non-significant connections are set to 0.

### Excel File (.xlsx)
A spreadsheet with columns:
- Region1
- Region2
- P_Values
- RHO_Values

## Requirements

- Python 3.7+
- numpy
- pandas
- PyQt5
- openpyxl (for Excel export)

## License

MIT License
