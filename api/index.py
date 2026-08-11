import os
import sys
import json
import datetime
import threading
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'))
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'legal-human-validation-secret-key-2026')

# Global variables for Firebase / Mock Mode
db = None
use_mock_db = False
mock_db_lock = threading.Lock()
mock_db = {
    'cases': [],
    'reviewers': {},
    'reviews': {},
    'system': {'next_chunk_index': 0, 'chunk_size': 10, 'total_cases': 500, 'total_chunks': 50}
}

def init_firebase():
    global db, use_mock_db
    cert_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    cert_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
    
    # Absolute path check
    if not os.path.isabs(cert_path):
        cert_path = os.path.join(os.path.dirname(__file__), '..', cert_path)

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        if not firebase_admin._apps:
            if cert_json_str:
                cred_dict = json.loads(cert_json_str)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin initialized via FIREBASE_SERVICE_ACCOUNT_JSON env var.")
            elif os.path.exists(cert_path):
                cred = credentials.Certificate(cert_path)
                firebase_admin.initialize_app(cred)
                print(f"Firebase Admin initialized via service key file: {cert_path}")
            else:
                raise FileNotFoundError("No Firebase service account key found.")
        db = firestore.client()
        use_mock_db = False
    except Exception as e:
        print(f"[WARNING] Firebase initialization skipped/failed: {e}")
        print("[INFO] Falling back to In-Memory Mock Database mode for local testing.")
        use_mock_db = True
        init_mock_db()

def init_mock_db(num_cases=500, chunk_size=10):
    global mock_db
    excel_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'qwen_pilot_500_human_validation.xlsx')
    test_excel_path = os.path.join(os.path.dirname(__file__), '..', 'Data', 'test_sample_50_cases.xlsx')
    
    loaded_cases = []
    
    try:
        import pandas as pd
        # Match the Firebase queue order: the 50 test cases are assigned first,
        # followed by the 500 research cases.
        for dataset_path, dataset_name in ((test_excel_path, 'test'), (excel_path, 'research')):
            if not os.path.exists(dataset_path):
                continue
            df = pd.read_excel(dataset_path).fillna("")
            for _, row in df.iterrows():
                loaded_cases.append({
                    "case_index": len(loaded_cases),
                    "filename": str(row.get("filename", "")).strip(),
                    "text_main_info": str(row.get("text(main info of case)", "")).strip(),
                    "raw_model_response": str(row.get("raw_model_response", "")).strip(),
                    "dataset_phase": dataset_name
                })
    except Exception as err:
        print(f"Error loading datasets for mock db: {err}")

    if not loaded_cases:
        # Generate synthetic fallback cases
        for i in range(num_cases):
            loaded_cases.append({
                "case_index": i,
                "filename": f"CASE_{i+1:03d}_Sample_Legal_Record",
                "text_main_info": f"Sample Legal Case #{i+1} text details...",
                "raw_model_response": f"Sample Model Inference Response for Case #{i+1}."
            })

    total_cases = len(loaded_cases)
    total_chunks = (total_cases + chunk_size - 1) // chunk_size

    mock_db['cases'] = loaded_cases
    mock_db['reviewers'] = {}
    mock_db['reviews'] = {}
    mock_db['system'] = {
        'next_chunk_index': 0,
        'chunk_size': chunk_size,
        'total_cases': total_cases,
        'total_chunks': total_chunks
    }

# Initialize database connection on load
init_firebase()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({
        'status': 'online',
        'use_mock_db': use_mock_db,
        'firebase_connected': not use_mock_db
    })

@app.route('/api/register', methods=['POST'])
def register_reviewer():
    data = request.get_json() or {}
    reviewer_id = str(data.get('reviewer_id', '')).strip()
    name = str(data.get('name', '')).strip()
    credentials = str(data.get('credentials', '')).strip()
    is_anonymous = bool(data.get('is_anonymous', False))

    if not reviewer_id:
        return jsonify({'success': False, 'error': 'Reviewer ID / Identifier is required.'}), 400

    if not credentials:
        return jsonify({'success': False, 'error': 'Genuine qualifications or professional credentials are required.'}), 400

    if use_mock_db:
        with mock_db_lock:
            # 1. Uniqueness check
            if reviewer_id in mock_db['reviewers']:
                return jsonify({
                    'success': False,
                    'existing_reviewer': True,
                    'error': 'This reviewer ID is already being used. Please choose another unique ID.'
                }), 400
            
            # 2. Atomic Chunk Assignment
            next_chunk = mock_db['system']['next_chunk_index']
            total_chunks = mock_db['system']['total_chunks']
            chunk_size = mock_db['system']['chunk_size']

            if next_chunk >= total_chunks:
                return jsonify({
                    'success': False,
                    'error': 'All review chunks have already been assigned.'
                }), 400

            chunk_index = next_chunk
            mock_db['system']['next_chunk_index'] += 1

            start_idx = chunk_index * chunk_size
            end_idx = min(start_idx + chunk_size, mock_db['system']['total_cases'])
            assigned_cases = mock_db['cases'][start_idx:end_idx]

            reviewer_doc = {
                'reviewer_id': reviewer_id,
                'name': name if not is_anonymous else 'Anonymous',
                'credentials': credentials,
                'is_anonymous': is_anonymous,
                'chunk_index': chunk_index,
                'start_index': start_idx,
                'end_index': end_idx,
                'total_chunks': total_chunks,
                'status': 'in_progress'
            }

            mock_db['reviewers'][reviewer_id] = reviewer_doc

            return jsonify({
                'success': True,
                'reviewer': reviewer_doc,
                'cases': assigned_cases
            })
    else:
        # FIREBASE FIRESTORE ATOMIC TRANSACTION
        from firebase_admin import firestore

        reviewer_ref = db.collection('reviewers').document(reviewer_id)
        sys_ref = db.collection('system').document('chunk_assignment')

        @firestore.transactional
        def run_registration_transaction(transaction):
            # 1. Check if reviewer doc already exists
            reviewer_snapshot = reviewer_ref.get(transaction=transaction)
            if reviewer_snapshot.exists:
                return None, 'This reviewer ID is already being used. Please choose another unique ID.', True

            # 2. Read system chunk counter
            sys_snapshot = sys_ref.get(transaction=transaction)
            if not sys_snapshot.exists:
                return None, 'System configuration doc system/chunk_assignment not initialized. Please run seed script.', False

            sys_data = sys_snapshot.to_dict()
            next_chunk = sys_data.get('next_chunk_index', 0)
            total_chunks = sys_data.get('total_chunks', 50)
            chunk_size = sys_data.get('chunk_size', 10)
            total_cases = sys_data.get('total_cases', 500)

            if next_chunk >= total_chunks:
                return None, 'All review chunks have already been assigned.', False

            chunk_index = next_chunk
            transaction.update(sys_ref, {'next_chunk_index': next_chunk + 1})

            start_idx = chunk_index * chunk_size
            end_idx = min(start_idx + chunk_size, total_cases)

            reviewer_doc = {
                'reviewer_id': reviewer_id,
                'name': name if not is_anonymous else 'Anonymous',
                'credentials': credentials,
                'is_anonymous': is_anonymous,
                'chunk_index': chunk_index,
                'start_index': start_idx,
                'end_index': end_idx,
                'total_chunks': total_chunks,
                'status': 'in_progress',
                'assigned_at': firestore.SERVER_TIMESTAMP
            }

            transaction.set(reviewer_ref, reviewer_doc)
            
            # Create a JSON-serializable copy for response
            response_reviewer = dict(reviewer_doc)
            response_reviewer['assigned_at'] = datetime.datetime.utcnow().isoformat()
            
            return (response_reviewer, start_idx, end_idx), None, False

        transaction = db.transaction()
        result, err_msg, existing_reviewer = run_registration_transaction(transaction)

        if err_msg:
            return jsonify({'success': False, 'error': err_msg, 'existing_reviewer': existing_reviewer}), 400

        reviewer_doc, start_idx, end_idx = result

        # Fetch assigned cases (range start_idx to end_idx)
        cases_ref = db.collection('cases')
        query = cases_ref.where('case_index', '>=', start_idx).where('case_index', '<', end_idx).order_by('case_index')
        case_docs = query.get()

        assigned_cases = []
        for doc in case_docs:
            c = doc.to_dict()
            assigned_cases.append({
                'case_index': c.get('case_index'),
                'filename': c.get('filename'),
                'text_main_info': c.get('text_main_info'),
                'raw_model_response': c.get('raw_model_response')
            })

        return jsonify({
            'success': True,
            'reviewer': reviewer_doc,
            'cases': assigned_cases
        })

@app.route('/api/reviewer/<reviewer_id>', methods=['GET'])
def get_reviewer_session(reviewer_id):
    reviewer_id = str(reviewer_id).strip()
    if use_mock_db:
        with mock_db_lock:
            reviewer = mock_db['reviewers'].get(reviewer_id)
            if not reviewer:
                return jsonify({'success': False, 'error': 'Reviewer not found.'}), 404
            
            start_idx = reviewer['start_index']
            end_idx = reviewer['end_index']
            cases = mock_db['cases'][start_idx:end_idx]

            # Fetch existing reviews
            saved_reviews = []
            for c in cases:
                case_id = f"case_{c['case_index']:03d}"
                r_key = f"{reviewer_id}_{case_id}"
                if r_key in mock_db['reviews']:
                    saved_reviews.append(mock_db['reviews'][r_key])

            return jsonify({
                'success': True,
                'reviewer': reviewer,
                'cases': cases,
                'saved_reviews': saved_reviews
            })
    else:
        from firebase_admin import firestore

        rev_ref = db.collection('reviewers').document(reviewer_id)
        rev_doc = rev_ref.get()
        if not rev_doc.exists:
            return jsonify({'success': False, 'error': 'Reviewer not found.'}), 404

        reviewer = rev_doc.to_dict()
        start_idx = reviewer.get('start_index', 0)
        end_idx = reviewer.get('end_index', 10)

        # Fetch cases
        cases_ref = db.collection('cases')
        query = cases_ref.where('case_index', '>=', start_idx).where('case_index', '<', end_idx).order_by('case_index')
        case_docs = query.get()
        cases = [doc.to_dict() for doc in case_docs]

        # Fetch saved reviews
        reviews_ref = db.collection('reviews').where('reviewer_id', '==', reviewer_id)
        review_docs = reviews_ref.get()
        saved_reviews = [rd.to_dict() for rd in review_docs]

        return jsonify({
            'success': True,
            'reviewer': reviewer,
            'cases': cases,
            'saved_reviews': saved_reviews
        })

@app.route('/api/submit', methods=['POST'])
def submit_reviews():
    data = request.get_json() or {}
    reviewer_id = str(data.get('reviewer_id', '')).strip()
    reviews = data.get('reviews', [])

    if not reviewer_id or not reviews:
        return jsonify({'success': False, 'error': 'Invalid payload.'}), 400

    if use_mock_db:
        with mock_db_lock:
            if reviewer_id not in mock_db['reviewers']:
                return jsonify({'success': False, 'error': 'Reviewer not found.'}), 404

            for item in reviews:
                case_index = item.get('case_index')
                case_id = f"case_{case_index:03d}"
                r_key = f"{reviewer_id}_{case_id}"
                
                mock_db['reviews'][r_key] = {
                    'reviewer_id': reviewer_id,
                    'case_id': case_id,
                    'case_index': case_index,
                    'filename': item.get('filename'),
                    'review_result': item.get('review_result'),
                    'problem_description': item.get('problem_description', ''),
                    'submitted_at': 'MOCK_TIMESTAMP'
                }

            mock_db['reviewers'][reviewer_id]['status'] = 'completed'
            return jsonify({'success': True, 'message': 'All 10 case reviews successfully submitted!'})
    else:
        from firebase_admin import firestore
        
        batch = db.batch()
        for item in reviews:
            case_index = item.get('case_index')
            case_id = f"case_{case_index:03d}"
            r_key = f"{reviewer_id}_{case_id}"
            
            r_ref = db.collection('reviews').document(r_key)
            batch.set(r_ref, {
                'reviewer_id': reviewer_id,
                'case_id': case_id,
                'case_index': case_index,
                'filename': item.get('filename'),
                'review_result': item.get('review_result'),
                'problem_description': item.get('problem_description', ''),
                'submitted_at': firestore.SERVER_TIMESTAMP
            })

        rev_ref = db.collection('reviewers').document(reviewer_id)
        batch.update(rev_ref, {'status': 'completed', 'completed_at': firestore.SERVER_TIMESTAMP})
        batch.commit()

        return jsonify({'success': True, 'message': 'All 10 case reviews successfully submitted!'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
