import pdfplumber
import pandas as pd
import re

RESUME_PATH = "Amal-Prasad-Resume.pdf"
CONTACTS_PATH = "Company Wise HR Contacts - HR Contacts (3).pdf"

def analyze_resume():
    print(f"--- Analyzing {RESUME_PATH} ---")
    try:
        with pdfplumber.open(RESUME_PATH) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            print("Resume Text Snippet:")
            print(text[:500])
            return text
    except Exception as e:
        print(f"Error reading resume: {e}")
        return None

def analyze_contacts():
    print(f"\n--- Analyzing {CONTACTS_PATH} ---")
    try:
        with pdfplumber.open(CONTACTS_PATH) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    all_tables.extend(table)
            
            print(f"Found {len(all_tables)} rows in tables.")
            if all_tables:
                df = pd.DataFrame(all_tables[1:], columns=all_tables[0])
                print("Columns found:", df.columns.tolist())
                print("First 5 rows:")
                print(df.head())
            else:
                print("No tables found using default extraction.")
                
    except Exception as e:
        print(f"Error reading contacts: {e}")

if __name__ == "__main__":
    analyze_resume()
    analyze_contacts()
