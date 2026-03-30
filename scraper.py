import os
import csv
import io
import requests
import time

CSV_URL = "https://raw.githubusercontent.com/data-liberation-project/aphis-inspection-reports/main/data/combined/inspections.csv"
DOWNLOAD_DIR = "data/raw_pdfs"
TARGET_COUNT = 210

def download_csv():
    print(f"Downloading CSV from {CSV_URL}...")
    response = requests.get(CSV_URL)
    response.raise_for_status()
    return response.text

def parse_and_download_pdfs(csv_text):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    reader = csv.DictReader(io.StringIO(csv_text))
    count = 0
    
    for row in reader:
        pdf_url = row.get("web_reportLink")
        if not pdf_url:
            continue
            
        hash_id = row.get("hash_id")
        if not hash_id:
            hash_id = pdf_url.split("/")[-1]
            
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{hash_id}.pdf")
        
        if os.path.exists(pdf_path):
            count += 1
            if count >= TARGET_COUNT:
                break
            continue
            
        print(f"[{count+1}/{TARGET_COUNT}] Downloading PDF: {pdf_url}")
        try:
            pdf_resp = requests.get(pdf_url, timeout=10)
            if pdf_resp.status_code == 200:
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_resp.content)
                count += 1
            else:
                print(f"Failed to download {pdf_url} (HTTP {pdf_resp.status_code})")
        except Exception as e:
            print(f"Error downloading {pdf_url}: {e}")
            
        time.sleep(0.5)  # Be nice to the server
        
        if count >= TARGET_COUNT:
            break
            
    print(f"Successfully ensured {count} PDFs in {DOWNLOAD_DIR}")

if __name__ == "__main__":
    try:
        csv_text = download_csv()
        parse_and_download_pdfs(csv_text)
    except Exception as e:
        print(f"Error: {e}")
