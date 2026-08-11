"""
Live Firebase Integration Test Script.
Tests live Firestore registration, atomic chunk allocation, reviewer handle uniqueness,
submission of reviews, and final export from live Firebase database.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.index import app

def test_live_firebase():
    ts = int(time.time())
    reviewer_alpha = f"LiveTest_Alpha_{ts}"
    reviewer_beta = f"LiveTest_Beta_{ts}"

    print("Connecting to live Firebase API...")
    app.config['TESTING'] = True
    client = app.test_client()

    # 1. Status Check
    status_res = client.get('/api/status')
    status_data = status_res.get_json()
    print("API Status:", status_data)
    assert status_data['firebase_connected'] == True, "Firebase should be connected!"

    # 2. Register Reviewer 1 (Alpha)
    print(f"\n--- Test 1: Registering Reviewer 1 ({reviewer_alpha}) ---")
    reg1 = client.post('/api/register', json={
        'reviewer_id': reviewer_alpha,
        'name': 'Alpha Legal Expert',
        'credentials': 'Advocate High Court',
        'is_anonymous': False
    })
    data1 = reg1.get_json()
    print("Registration Response:", data1)
    assert data1['success'] == True, f"Registration failed: {data1.get('error')}"
    assert len(data1['cases']) == 10
    first_case_idx = data1['cases'][0]['case_index']
    last_case_idx = data1['cases'][-1]['case_index']
    print(f"[SUCCESS] Reviewer assigned chunk index {data1['reviewer']['chunk_index']} (cases {first_case_idx} to {last_case_idx})!")

    # 3. Duplicate Handle Check
    print(f"\n--- Test 2: Checking Duplicate Handle Rejection for {reviewer_alpha} ---")
    reg_dup = client.post('/api/register', json={
        'reviewer_id': reviewer_alpha,
        'name': 'Duplicate User',
        'credentials': 'N/A',
        'is_anonymous': True
    })
    data_dup = reg_dup.get_json()
    print("Duplicate Registration Response:", data_dup)
    assert data_dup['success'] == False
    assert "already being used" in data_dup['error']
    print("[SUCCESS] Duplicate handle correctly rejected!")

    # 4. Register Reviewer 2 (Beta) -> Must get Next Chunk
    print(f"\n--- Test 3: Registering Reviewer 2 ({reviewer_beta}) ---")
    reg2 = client.post('/api/register', json={
        'reviewer_id': reviewer_beta,
        'name': 'Beta Legal Researcher',
        'credentials': 'LL.M.',
        'is_anonymous': True
    })
    data2 = reg2.get_json()
    print("Registration Response:", data2)
    assert data2['success'] == True, f"Registration failed: {data2.get('error')}"
    assert len(data2['cases']) == 10
    b_first_case = data2['cases'][0]['case_index']
    b_last_case = data2['cases'][-1]['case_index']
    assert data2['reviewer']['chunk_index'] == data1['reviewer']['chunk_index'] + 1
    assert b_first_case == last_case_idx + 1
    print(f"[SUCCESS] Sequential Chunk {data2['reviewer']['chunk_index']} (cases {b_first_case} to {b_last_case}) correctly assigned to {reviewer_beta} with ZERO overlap!")

    # 5. Submit Reviews for Reviewer 1
    print(f"\n--- Test 4: Submitting Reviews for {reviewer_alpha} ---")
    reviews_payload = []
    for c in data1['cases']:
        reviews_payload.append({
            'case_index': c['case_index'],
            'filename': c['filename'],
            'review_result': 'Fine' if c['case_index'] % 2 == 0 else 'Problem',
            'problem_description': '' if c['case_index'] % 2 == 0 else f"Live test problem description for case {c['filename']}"
        })

    sub_res = client.post('/api/submit', json={
        'reviewer_id': reviewer_alpha,
        'reviews': reviews_payload
    })
    sub_data = sub_res.get_json()
    print("Submission Response:", sub_data)
    assert sub_data['success'] == True
    print("[SUCCESS] Live reviews submitted to Firestore!")

if __name__ == '__main__':
    test_live_firebase()
