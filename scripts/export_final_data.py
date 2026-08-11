"""
Export Final Dataset Script.
Downloads all 500 cases from Firestore along with human review responses,
and merges them into a clean final CSV and Excel file (500 rows).
"""

import os
import sys
import json
import argparse
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def get_firestore_client():
    import firebase_admin
    from firebase_admin import credentials, firestore
    
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
                "Please set FIREBASE_SERVICE_ACCOUNT_JSON or place serviceAccountKey.json in the project root."
            )
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

def export_data(output_dir="Data"):
    os.makedirs(output_dir, exist_ok=True)
    db = get_firestore_client()

    print("Fetching all cases from Firestore 'cases' collection...")
    cases_docs = db.collection("cases").get()
    cases = []
    for doc in cases_docs:
        d = doc.to_dict()
        cases.append(d)

    # Sort cases by case_index
    cases.sort(key=lambda x: x.get("case_index", 0))
    print(f"Retrieved {len(cases)} cases.")

    print("Fetching all reviews from Firestore 'reviews' collection...")
    reviews_docs = db.collection("reviews").get()
    reviews_map = {}
    for doc in reviews_docs:
        r = doc.to_dict()
        case_id = r.get("case_id")
        if case_id:
            reviews_map[case_id] = r
    print(f"Retrieved {len(reviews_map)} submitted reviews.")

    print("Fetching reviewer information from 'reviewers' collection...")
    reviewer_docs = db.collection("reviewers").get()
    reviewers_map = {}
    for doc in reviewer_docs:
        rev = doc.to_dict()
        r_id = rev.get("reviewer_id")
        if r_id:
            reviewers_map[r_id] = rev

    merged_data = []
    for c in cases:
        case_id = f"case_{c.get('case_index', 0):03d}"
        review = reviews_map.get(case_id, {})
        
        reviewer_id = review.get("reviewer_id", "")
        reviewer_info = reviewers_map.get(reviewer_id, {})
        reviewer_name = reviewer_info.get("name", "") or reviewer_id

        ts_val = review.get("submitted_at", "")
        if ts_val and hasattr(ts_val, "isoformat"):
            ts_val = ts_val.isoformat()
        elif ts_val:
            ts_val = str(ts_val)

        row = {
            "filename": c.get("filename", ""),
            "text(main info of case)": c.get("text_main_info", ""),
            "raw_model_response": c.get("raw_model_response", ""),
            "Fine /Problem": c.get("original_fine_problem", ""),
            "Please tell the problem ": c.get("original_problem_desc", ""),
            "Please provide your name and credentials; if you prefer to remain anonymous, please provide your credentials only.": c.get("original_reviewer_info", ""),
            # Human Validation Appended Fields
            "reviewer_id": reviewer_id,
            "reviewer_name": reviewer_name,
            "reviewer_credentials": reviewer_info.get("credentials", ""),
            "is_anonymous": reviewer_info.get("is_anonymous", False),
            "review_result": review.get("review_result", ""),
            "problem_description": review.get("problem_description", ""),
            "review_timestamp": ts_val
        }
        merged_data.append(row)

    df_final = pd.DataFrame(merged_data)

    csv_path = os.path.join(output_dir, "final_500_cases_validated.csv")
    excel_path = os.path.join(output_dir, "final_500_cases_validated.xlsx")

    df_final.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df_final.to_excel(excel_path, index=False)

    print("\n[SUCCESS] Export Successful!")
    print(f"Total Rows: {len(df_final)}")
    print(f"Saved CSV output to:   {csv_path}")
    print(f"Saved Excel output to: {excel_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export final human validated dataset from Firestore.")
    parser.add_argument("--output-dir", default="Data", help="Directory to save export files")
    args = parser.parse_args()
    export_data(args.output_dir)
