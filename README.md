# Human Validation Web App — 500 Legal Cases

A streamlined, robust human validation web platform for 500 legal cases built with **Python (Flask)**, **Firebase Firestore**, and **Vercel** serverless hosting.

## Features

- **500 Legal Cases Benchmark**: Preserves original legal case structure (`filename`, `text(main info of case)`, `raw_model_response`).
- **Atomic Sequential Assignment**: Divides 500 cases into 50 chunks of 10 cases (Cases 1–10, 11–20, ..., 491–500). Uses Firestore Transactions to guarantee 0 duplicate assignments under heavy concurrent access.
- **Unique Reviewer Identification**: Enforces unique reviewer handles (e.g. `BlueTiger27`) with optional anonymity settings.
- **Clean Reviewer UI**: Single-page flow with side-by-side legal case text & AI model inference, radio validation controls (**Fine** vs **Problem**), problem description input, progress bar, and local draft auto-saving.
- **Python Data Tools**:
  - `scripts/seed_firebase.py`: Populates Firestore from Excel dataset.
  - `scripts/export_final_data.py`: Downloads and outputs final 500-row CSV/Excel dataset.
  - `scripts/generate_test_dataset.py`: Generates sample test data.
  - `scripts/test_assignment.py`: Automated unit test suite verifying uniqueness, sequential chunk shifting, and capacity limits.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python scripts/test_assignment.py
```

### 3. Start Local Server
```bash
python api/index.py
```
Open `http://localhost:5000` in your web browser.

---

## Documentation

For full step-by-step instructions on obtaining Firebase keys, seeding your dataset, deploying to Vercel, and exporting results, refer to [FIREBASE_SETUP_GUIDE.md](FIREBASE_SETUP_GUIDE.md).
