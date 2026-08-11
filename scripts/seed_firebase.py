"""
Seed Firebase Firestore database with Legal Cases dataset.
Supports production Excel file ('Data/qwen_pilot_500_human_validation.xlsx') or test datasets.
"""

import os
import sys
import json
import datetime
import argparse
import pandas as pd
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

def get_firestore_client():
    if not firebase_admin._apps:
        cert_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        cert_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
        
        if cert_json_str:
            cred_dict = json.loads(cert_json_str)
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists(cert_path):
            cred = credentials.Certificate(cert_path)
        else:
            raise ValueError(
                "Firebase Service Account Credentials not found!\n"
                "Please provide FIREBASE_SERVICE_ACCOUNT_JSON or place serviceAccountKey.json in the project root."
            )
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

def seed_cases(excel_path, chunk_size=10, dry_run=False):
    if not os.path.exists(excel_path):
        print(f"Error: Dataset file not found at {excel_path}")
        sys.exit(1)

    print(f"Loading dataset from: {excel_path} ...")
    df = pd.read_excel(excel_path)
    # Fill NaN values with empty strings
    df = df.fillna("")
    
    total_cases = len(df)
    total_chunks = (total_cases + chunk_size - 1) // chunk_size
    print(f"Loaded {total_cases} cases. Splitting into {total_chunks} chunks of {chunk_size} cases each.")

    if dry_run:
        print("\n--- DRY RUN SUMMARY ---")
        print(f"Total cases to seed: {total_cases}")
        print(f"Columns present: {df.columns.tolist()}")
        print(f"First case filename: {df.iloc[0]['filename']}")
        print(f"Last case filename: {df.iloc[-1]['filename']}")
        print("Dry run completed successfully. No data was written to Firebase.")
        return

    db = get_firestore_client()
    cases_ref = db.collection("cases")
    
    print("Writing cases to Firestore collection 'cases'...")
    batch = db.batch()
    batch_count = 0

    for idx, row in df.iterrows():
        case_id = f"case_{idx:03d}"
        doc_ref = cases_ref.document(case_id)
        
        case_data = {
            "case_index": int(idx),
            "filename": str(row.get("filename", "")).strip(),
            "text_main_info": str(row.get("text(main info of case)", "")).strip(),
            "raw_model_response": str(row.get("raw_model_response", "")).strip(),
            "original_fine_problem": str(row.get("Fine /Problem", "")).strip(),
            "original_problem_desc": str(row.get("Please tell the problem ", "")).strip(),
            "original_reviewer_info": str(row.get("Please provide your name and credentials; if you prefer to remain anonymous, please provide your credentials only.", "")).strip()
        }
        
        batch.set(doc_ref, case_data)
        batch_count += 1

        if batch_count >= 450:  # Firestore batch limit is 500
            batch.commit()
            print(f"Committed batch of {batch_count} cases.")
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()
        print(f"Committed final batch of {batch_count} cases.")

    # Initialize system metadata counter for chunk assignment
    system_ref = db.collection("system").document("chunk_assignment")
    system_ref.set({
        "next_chunk_index": 0,
        "total_cases": total_cases,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "updated_at": firestore.SERVER_TIMESTAMP
    })

    print("\n[SUCCESS] Firestore Seeding Complete!")
    print(f"Seeded {total_cases} cases into 'cases' collection.")
    print(f"Initialized 'system/chunk_assignment' with next_chunk_index = 0.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Firebase Firestore with legal cases dataset.")
    parser.add_argument("--excel", default="Data/qwen_pilot_500_human_validation.xlsx", help="Path to Excel dataset file")
    parser.add_argument("--chunk-size", type=int, default=10, help="Number of cases per reviewer chunk (default: 10)")
    parser.add_argument("--dry-run", action="store_true", help="Validate file without writing to Firestore")
    
    args = parser.parse_args()
    seed_cases(args.excel, args.chunk_size, args.dry_run)
