# Step-by-Step Guide: Firebase Setup & Vercel Deployment

This document provides complete, beginner-friendly instructions on setting up **Firebase Firestore**, seeding the 500 legal cases dataset, running the application locally, deploying to **Vercel**, and exporting the final validated dataset.

---

## 1. Firebase Setup (Free Tier)

### Step 1: Create a Free Firebase Project
1. Open your browser and go to [Firebase Console](https://console.firebase.google.com/).
2. Click **Add project** (or **Create a project**).
3. Enter a project name, e.g., `legal-human-validation`.
4. (Optional) Disable Google Analytics for this project, then click **Create project**.

### Step 2: Enable Firestore Database
1. In your Firebase project dashboard, click **Build** in the left sidebar and select **Firestore Database**.
2. Click **Create database**.
3. Select a location near you (e.g., `us-central` or `asia-south1`).
4. Select **Start in test mode** (or production mode), then click **Create**.

### Step 3: Download Firebase Service Account Key
1. In the left sidebar, click the **Gear Icon ⚙️** next to *Project Overview* and select **Project settings**.
2. Select the **Service accounts** tab.
3. Click the **Generate new private key** button at the bottom.
4. A `.json` file will download to your computer (e.g. `legal-human-validation-firebase-adminsdk-xxx.json`).

### Step 4: Add the Key to Your Local Project
1. Rename the downloaded `.json` file to `serviceAccountKey.json`.
2. Move `serviceAccountKey.json` into the root folder of this project (`Human validation for legal/serviceAccountKey.json`).

---

## 2. Seed Firebase with 500 Legal Cases

Once `serviceAccountKey.json` is placed in the project root:

1. Open your terminal in the project directory:
   ```bash
   cd "Human validation for legal"
   ```
2. Run the seeding script to upload all 500 cases:
   ```bash
   python scripts/seed_firebase.py
   ```
3. You will see:
   ```
   Loading dataset from: Data/qwen_pilot_500_human_validation.xlsx ...
   Loaded 500 cases. Splitting into 50 chunks of 10 cases each.
   Committed batch of 450 cases.
   Committed final batch of 50 cases.

   [SUCCESS] Firestore Seeding Complete!
   Seeded 500 cases into 'cases' collection.
   Initialized 'system/chunk_assignment' with next_chunk_index = 0.
   ```

---

## 3. Test & Run Locally

### Option A: Run Locally in Mock Mode (Without Firebase Keys)
If you want to test right now before setting up Firebase:
```bash
python api/index.py
```
Open `http://localhost:5000` in your browser. The app will automatically use **In-Memory Mock Database** mode!

### Option B: Run Locally with Live Firebase Firestore
Once `serviceAccountKey.json` is present:
```bash
python api/index.py
```
Open `http://localhost:5000` in your browser. The app will connect directly to your live Firestore database!

---

## 4. Deploying to Vercel

Vercel allows you to host the web application online for free so reviewers can access it from anywhere.

### Option A: Deploy via GitHub (Recommended)
1. Push your repository code to **GitHub**.
2. Go to [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. Under **Environment Variables**, add:
   * **Name**: `FIREBASE_SERVICE_ACCOUNT_JSON`
   * **Value**: Copy and paste the entire JSON text from your `serviceAccountKey.json` file.
5. Click **Deploy**. Vercel will build and launch your website!

### Option B: Deploy via Vercel CLI
1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```
2. In your project directory, run:
   ```bash
   vercel
   ```
3. Follow the prompts. In Vercel Project Settings, add the `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable.

---

## 5. Export Final Validated Dataset (CSV / Excel)

After your reviewers have completed their 10-case validations:

1. Run the export script:
   ```bash
   python scripts/export_final_data.py
   ```
2. The script will download all 500 cases and merge human validation responses.
3. The output files will be created in `Data/`:
   * `Data/final_500_cases_validated.csv`
   * `Data/final_500_cases_validated.xlsx`
4. Both output files maintain the **exact 500 rows** with original case details plus appended human validation fields (`reviewer_id`, `reviewer_name`, `review_result`, `problem_description`, `review_timestamp`).

---

## 6. Automated Unit Tests

To verify reviewer handle uniqueness, sequential chunk shifting (0..49), zero overlap, and capacity enforcement at any time, run:
```bash
python scripts/test_assignment.py
```
