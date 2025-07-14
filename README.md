# Simplified Roll Planning App

This Streamlit application helps optimize fabric roll usage for garment production by simulating multiple roll planning scenarios. It analyzes cut plans and roll data to predict fabric utilization, wastage, and production shortfalls.

## Features

- **Fabric Requirement Analysis**: Calculates total fabric needed vs uploaded
- **Yield Estimation**: Computes estimated yield per garment
- **Shortfall Prediction**: Warns about potential production shortfalls
- **50-Roll Simulation**: Runs 50 randomized roll usage scenarios
- **Comprehensive Reporting**:
  - Fabric utilization metrics
  - Production shortfall statistics
  - End bit categorization by garment yield
  - Percentage-based wastage analysis

## Requirements

- Python 3.7+
- Streamlit
- Pandas
- Numpy

## Installation

```bash
pip install streamlit pandas numpy
```

## Usage

1. Prepare an Excel file with two sheets:
   - `cutplan`: Contains columns:
     - `Marker_Name`
     - `Marker_Length`
     - `Ply_Height`
     - `Bundles`
   - `rolls_data`: Contains columns:
     - `Roll_Number`
     - `Roll_Length`

2. Run the application:
```bash
streamlit run app.py
```

3. Upload your Excel file through the interface
4. Review the fabric sufficiency warning (if any)
5. Click "Run 50 Random Roll Plans" to generate simulations
6. Analyze the summary statistics

## Output Metrics

### Fabric Utilization
- Excess rolls (unused full rolls)
- Fabric saved in roll form
- Usable end bits (by garment yield groups)
- Unusable fabric scraps

### Production Analysis
- Ply shortfall (incomplete layers)
- Garment production shortfall
- Actual garments produced vs planned

### End Bit Analysis
- Categorizes usable end bits by garment yield potential:
  - 1-2 bundles
  - 2-3 bundles
  - ... up to maximum possible

## Important Notes

- The simulation adds a 2% allowance to fabric requirements
- Residuals smaller than the smallest marker are considered scraps
- 50 randomized iterations provide statistical reliability
- "Yield per garment" is calculated as `Total Fabric Needed / Total Garments`

![App Screenshot](https://via.placeholder.com/800x400?text=Roll+Planning+App+Screenshot)

## License
MIT License
