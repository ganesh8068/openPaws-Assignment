import os
import re
import glob
from datetime import datetime
import pdfplumber
from models import init_db, get_session, Facility, Inspection, Violation, Species

RAW_DIR = "data/raw_pdfs"

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%d-%b-%Y").date()
    except:
        return None

def parse_pdf(pdf_path):
    print(f"Parsing {pdf_path}...")
    data = {"violations": [], "species": []}
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
                
        text = "\n".join(full_text)
        
        # Regex heuristics for header
        customer_match = re.search(r"Customer ID:\s*(\d+)", text)
        data["customer_id"] = customer_match.group(1) if customer_match else "UNKNOWN"
        
        cert_match = re.search(r"Certificate:\s*([\w\-]+)", text)
        data["license_type"] = cert_match.group(1) if cert_match else "UNKNOWN"
        
        # Facility name often comes after Certificate or Customer ID. This is a naive extraction.
        # Actually, let's use a simpler heuristic for facility name
        facility_match = re.search(r"Facility:(.*?)(?:\n|$)", text, re.IGNORECASE)
        data["facility_name"] = facility_match.group(1).strip() if facility_match else f"Facility_{data['customer_id']}"
        
        date_match = re.search(r"Date[:\s]+(\d{1,2}-[A-Za-z]{3}-\d{4})", text)
        data["date"] = parse_date(date_match.group(1)) if date_match else None
        
        # State and zip - simplified regex
        state_zip_match = re.search(r"\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b", text)
        if state_zip_match:
            data["state"] = state_zip_match.group(1)
            data["zip_code"] = state_zip_match.group(2)
        else:
            data["state"] = "UNKNOWN"
            data["zip_code"] = "UNKNOWN"
            
        data["report_id"] = os.path.basename(pdf_path).replace(".pdf", "")
        
        # Violations parsing
        # Looks for things like "3.1(a) Critical" or "2.126(a)(1) Direct"
        lines = text.split("\n")
        current_violation = None
        
        in_species_table = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Stop violation parsing if we hit Species table
            if "Species Inspected" in line or "Count Scientific Name" in line:
                in_species_table = True
                continue
                
            if in_species_table:
                # species line e.g., "000010 Canis lupus familiaris DOG ADULT"
                species_match = re.search(r"^(\d+)\s+([A-Z][a-z]+(?:\s[a-z]+)*)\s+([A-Z0-9\s]+)$", line)
                if species_match:
                    count = int(species_match.group(1))
                    sci_name = species_match.group(2).strip()
                    common_name = species_match.group(3).strip()
                    if common_name.lower() != "total":
                        data["species"].append({
                            "count": count,
                            "scientific_name": sci_name,
                            "common_name": common_name
                        })
                continue

            # Detect violation start
            violation_match = re.search(r"^(\d+\.\d+(?:[a-zA-Z0-9\(\)]+)?)\s+(Critical|Direct|Teachable Moment)?", line, re.IGNORECASE)
            if violation_match and not "Item" in line:
                if current_violation:
                    data["violations"].append(current_violation)
                
                v_code = violation_match.group(1)
                severity = violation_match.group(2) or "Non-Critical"
                current_violation = {
                    "code": v_code,
                    "severity": severity.title(),
                    "notes": []
                }
            elif current_violation:
                if not re.search(r"^Date[:\s]", line): # skip date lines in notes
                    current_violation["notes"].append(line)
                    
        if current_violation:
            data["violations"].append(current_violation)
            
        for v in data["violations"]:
            v["notes"] = "\n".join(v["notes"])
            
    return data

def seed_database():
    session = get_session()
    
    pdf_files = glob.glob(os.path.join(RAW_DIR, "*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {RAW_DIR}. Run scraper first.")
        return
        
    for pdf_path in pdf_files:
        data = parse_pdf(pdf_path)
        
        # Insert Facility
        facility = session.query(Facility).filter_by(customer_id=data["customer_id"]).first()
        if not facility:
            facility = Facility(
                customer_id=data["customer_id"],
                name=data["facility_name"],
                state=data["state"],
                zip_code=data["zip_code"],
                license_type=data["license_type"]
            )
            session.add(facility)
            session.commit()
            
        # Insert Inspection
        inspection = session.query(Inspection).filter_by(report_id=data["report_id"]).first()
        if not inspection:
            inspection = Inspection(
                facility_id=facility.id,
                report_id=data["report_id"],
                date=data["date"]
            )
            session.add(inspection)
            session.commit()
            
            # Insert Violations
            for v_data in data["violations"]:
                violation = Violation(
                    inspection_id=inspection.id,
                    violation_type=v_data["code"],
                    severity=v_data["severity"],
                    notes=v_data["notes"],
                    enforcement_action="Not specified"
                )
                session.add(violation)
                
            # Insert Species
            for s_data in data["species"]:
                species = Species(
                    inspection_id=inspection.id,
                    count=s_data["count"],
                    scientific_name=s_data["scientific_name"],
                    common_name=s_data["common_name"]
                )
                session.add(species)
                
            session.commit()
            
    print(f"Successfully seeded database with {len(pdf_files)} reports.")

if __name__ == "__main__":
    init_db()
    seed_database()
