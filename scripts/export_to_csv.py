"""
Export Firestore reviews to a local CSV file.

Usage:
    python scripts/export_to_csv.py

This script reads all reviews from the Firestore 'reviews' collection
and saves them to Data/collected_human_validations.csv on your laptop.
"""

import os
import sys
import csv
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

def main():
    import firebase_admin
    from firebase_admin import credentials, firestore

    # Initialize Firebase
    cert_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    cert_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
    if not os.path.isabs(cert_path):
        cert_path = os.path.join(os.path.dirname(__file__), '..', cert_path)

    if not firebase_admin._apps:
        if cert_json_str:
            cred = credentials.Certificate(json.loads(cert_json_str))
        elif os.path.exists(cert_path):
            cred = credentials.Certificate(cert_path)
        else:
            print("[ERROR] No Firebase credentials found. Set FIREBASE_SERVICE_ACCOUNT_JSON or place serviceAccountKey.json in project root.")
            sys.exit(1)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Fetch all reviews
    print("Fetching reviews from Firestore...")
    reviews_docs = list(db.collection('reviews').stream())
    print(f"Found {len(reviews_docs)} review documents.")

    if not reviews_docs:
        print("No reviews found. Nothing to export.")
        return

    # Output path
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'Data')
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, 'collected_human_validations.csv')

    fieldnames = [
        'reviewer_id', 'reviewer_name', 'reviewer_credentials', 'is_anonymous',
        'case_id', 'case_index', 'filename', 'review_result',
        'problem_description', 'submitted_at'
    ]

    rows_written = 0
    with open(output_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for doc in reviews_docs:
            rev = doc.to_dict()

            # Convert Firestore timestamp to ISO string
            submitted_at = rev.get('submitted_at')
            if hasattr(submitted_at, 'isoformat'):
                submitted_at = submitted_at.isoformat()
            elif submitted_at is None:
                submitted_at = ''
            else:
                submitted_at = str(submitted_at)

            writer.writerow({
                'reviewer_id':          rev.get('reviewer_id', ''),
                'reviewer_name':        rev.get('reviewer_name', ''),
                'reviewer_credentials': rev.get('reviewer_credentials', ''),
                'is_anonymous':         rev.get('is_anonymous', False),
                'case_id':              rev.get('case_id', ''),
                'case_index':           rev.get('case_index', ''),
                'filename':             rev.get('filename', ''),
                'review_result':        rev.get('review_result', ''),
                'problem_description':  rev.get('problem_description', ''),
                'submitted_at':         submitted_at
            })
            rows_written += 1

    print(f"\n[SUCCESS] Exported {rows_written} reviews to:\n  {os.path.abspath(output_path)}")


if __name__ == '__main__':
    main()
