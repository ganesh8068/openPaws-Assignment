# OpenPAWS: USDA APHIS Animal Welfare Database

This repository contains a prototype tool suite for scraping, parsing, and querying USDA APHIS Animal Welfare Act inspection reports. It transforms unstructured government PDFs into a normalized SQLite database and provides a simple CLI to interrogate the data.

## Product & User Considerations

**Who is this for?**
This tool is designed for animal advocacy organizations, investigative journalists, researchers, and policymakers.

**How does it serve them?**
Currently, extracting actionable insights from APHIS inspection reports requires reading through hundreds of unstructured PDFs. This tool liberates that data, allowing advocates to track repeat offenders, cross-reference violations by species or severity, and quickly identify systemic issues. By turning documents into queried data, it empowers organizations to build data-driven campaigns, target policy interventions, and optimize their advocacy efforts.

**How would it work in the real world?**
While this prototype is a CLI tool and local database, in a production environment, this parsing engine would run as an automated, scheduled pipeline (e.g., via Airflow or Cron). It would continuously monitor the USDA portal for new reports, process the PDFs, and update a centralized, cloud-hosted database (like PostgreSQL). This database would then power a public-facing web dashboard or API—allowing non-technical users to set up email alerts, generate graphs, and perform complex searches without needing to run Python scripts.

## Technical Thinking and Approach

The core technical challenge of this project is extracting structured data from minimally structured PDF reports. My approach is divided into 4 primary steps:

1. **Data Acquisition (`scraper.py`)**: 
   Since the USDA APHIS portal relies on dynamic, complex Salesforce endpoints, directly scraping their search portal is unstable. Instead, this project uses the Data Liberation Project's combined CSV index to reliably resolve the direct PDF URLs and download 200+ raw records.
2. **Schema Design (`models.py`)**: 
   A normalized SQLite database built using SQLAlchemy ensures fast and structured queries. The schema separates `Facilities`, `Inspections`, `Violations`, and `Species` to enable complex relational queries (e.g., finding the intersection of a species and a specific violation severity across all facilities).
3. **Data Parsing & Seeding (`parser.py`)**:
   Instead of using heavy LLMs that can hallucinate data or require extensive API keys for processing hundreds of PDFs, this parser uses `pdfplumber` for robust text extraction. Regular expressions paired with a state-machine logic block help identify headers and iterate through violations and species count tables accurately.
4. **Querying (`cli.py`)**:
   A visually appealing Command Line Interface built with `typer` and `rich`, providing clear tables for the requested criteria.

## Requirements

- Python 3.9+ 
- Dependencies listed in `requirements.txt`

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd openPaws

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Download Seed Data
To populate the `data/raw_pdfs/` directory with 200+ reports:
```bash
python scraper.py
```

### 2. Parse & Seed the Database
This analyzes the PDFs and populates the SQLite database (`data/aphis.db`):
```bash
python parser.py
```

### 3. Query the Database (CLI)
Use the included CLI to query the data.

**Get all critical violations for a company in a state over 2 years:**
```bash
python cli.py critical-violations "UNIVERSITY" "TX" --years 2
```

**Find facilities with repeat violations:**
```bash
python cli.py repeat-violators
```

**Find violations by species and severity:**
```bash
python cli.py species-violations "MACAQUE" --severity "Critical"
```
*(Leave the `--severity` flag out to see all severities for a species)*
