# Vercel Deployment Guide — Legal AI Human Validation Platform

## Overview

This app is a Flask-based human validation platform deployed on Vercel with Firebase Firestore as the database. All reviewer data and review responses are stored directly in Firestore — no CSV downloads are needed.

---

## Prerequisites

- [Vercel account](https://vercel.com) (free tier is fine)
- Firebase project `htmf-aa23f` already seeded with 550 cases (done via `scripts/seed_firebase.py`)
- Git repo pushed to GitHub / GitLab / Bitbucket

---

## Step 1 — Push to GitHub

```bash
cd "Legal judge/human-validation-for-legal"
git add .
git commit -m "feat: pure human validation platform with Firestore storage"
git push origin main
```

> ⚠️ **Do NOT push `serviceAccountKey.json` or `.env`** — they're in `.gitignore`. Credentials go into Vercel's environment variables (Step 3).

---

## Step 2 — Import Project in Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **"Import Git Repository"**
3. Select your repo
4. Leave all build settings as default — Vercel auto-detects `vercel.json`
5. **Don't deploy yet** — set env vars first (Step 3)

---

## Step 3 — Set Environment Variables in Vercel

Go to your project → **Settings → Environment Variables** and add:

| Variable | Value |
|---|---|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | *(Full JSON content of `serviceAccountKey.json` — paste as one line)* |
| `FLASK_SECRET_KEY` | `legal-human-validation-secret-key-2026` *(or any secure random string)* |

### How to get the `FIREBASE_SERVICE_ACCOUNT_JSON` value

Open `serviceAccountKey.json` and copy the **entire contents** (it's a JSON object). Paste it as a single-line string in the Vercel env var field. Vercel handles multi-line values safely.

You can also convert it to one line using PowerShell:
```powershell
(Get-Content serviceAccountKey.json -Raw) | ConvertFrom-Json | ConvertTo-Json -Compress
```

---

## Step 4 — Deploy

Click **Deploy** in Vercel. The build will:
1. Install Python packages from `requirements.txt`
2. Start the Flask app via `api/index.py`
3. Serve static files from `static/`

Your app will be live at `https://<your-project>.vercel.app`

---

## Step 5 — Verify Firestore is Connected

After deploy, visit `https://<your-project>.vercel.app/api/status`

You should see:
```json
{
  "status": "online",
  "use_mock_db": false,
  "firebase_connected": true
}
```

If `firebase_connected` is `false`, check your `FIREBASE_SERVICE_ACCOUNT_JSON` env var.

---

## Step 6 — Test Across 5 Browsers

1. Open the app in 5 different browsers simultaneously
2. Register a unique Reviewer ID in each browser
3. Each reviewer gets a non-overlapping 10-case chunk (cases 0–9, 10–19, etc.)
4. Complete all 10 reviews and submit

Then verify in **Firebase Console → Firestore → `reviews` collection** that all 50 reviews appear with full fields:

| Field | Description |
|---|---|
| `reviewer_id` | Unique ID entered at registration |
| `reviewer_name` | Full name (or "Anonymous") |
| `reviewer_credentials` | Professional credentials |
| `is_anonymous` | Boolean |
| `case_id` | e.g. `case_000` |
| `case_index` | Integer index (0–549) |
| `filename` | Original case filename |
| `review_result` | `Fine`, `Problem`, or `Unclear/Vague` |
| `problem_description` | Description of problem (if applicable) |
| `submitted_at` | Server-generated Firestore timestamp |

---

## Downloading Data (Firebase Console)

Since there's no CSV download on the site, to get your data:

1. Go to [Firebase Console](https://console.firebase.google.com/project/htmf-aa23f/firestore)
2. Navigate to the `reviews` collection
3. Use **"Export"** from Firebase Console, or run locally:

```powershell
cd "Legal judge/human-validation-for-legal"
python scripts/export_to_csv.py
```

*(This script reads from Firestore and saves `Data/collected_human_validations.csv` to your laptop)*

---

## Architecture

```
Vercel (Flask)
    ├── GET  /                  → Serve index.html
    ├── GET  /api/status        → Health check + Firebase connection status
    ├── POST /api/register      → Register reviewer + atomic chunk assignment
    ├── GET  /api/reviewer/:id  → Reload existing reviewer session
    └── POST /api/submit        → Save all 10 reviews to Firestore

Firestore Collections
    ├── cases/          → 550 seeded legal cases (case_000 to case_549)
    ├── reviewers/      → One doc per reviewer (ID, name, creds, chunk info)
    ├── reviews/        → One doc per review (reviewer_id_case_NNN)
    └── system/         → chunk_assignment doc (atomic counter)
```
