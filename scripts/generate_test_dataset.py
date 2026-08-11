"""
Generate Synthetic Test Dataset Excel file for Legal Human Validation.
Creates 'Data/test_sample_50_cases.xlsx' with exact matching structure as the production dataset.
"""

import os
import pandas as pd

def generate_test_dataset(num_cases=50, output_path="Data/test_sample_50_cases.xlsx"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    data = []
    court_types = ["Supreme_Court", "Madras_HC", "Delhi_HC", "Bombay_HC", "Kolkata_HC"]
    
    for i in range(1, num_cases + 1):
        court = court_types[(i - 1) % len(court_types)]
        year = 2015 + (i % 10)
        filename = f"TEST_{court}_{year}_{i:03d}"
        
        case_text = (
            f"IN THE HIGH COURT / SUPREME COURT OF INDIA ({court}, {year})\n"
            f"Case Identifier: {filename}\n\n"
            f"FACTS OF THE CASE:\n"
            f"The appellant filed an appeal under Section {100 + i} challenging the decision of the lower tribunal. "
            f"The central dispute revolves around legal interpretation of contractual clause {i%12 + 1} "
            f"and compliance with statutory notice period under Section {20 + i%5}.\n\n"
            f"ARGUMENTS:\n"
            f"1. Petitioner contends that due process was not followed during arbitration.\n"
            f"2. Respondent argues that limitation period of 3 years has expired.\n\n"
            f"JUDGMENT:\n"
            f"The Court observed that equity favors the vigilant. Appeal is hereby disposed of with direction to "
            f"remand the matter back to the appellate authority."
        )
        
        model_response = (
            f"SUMMARY & LEGAL ENTITY EXTRACTION:\n"
            f"- Court: {court.replace('_', ' ')}\n"
            f"- Year: {year}\n"
            f"- Key Section: Section {100 + i}\n"
            f"- Outcome: Disposed / Remanded\n"
            f"- Confidence Score: {0.85 + (i % 15) * 0.01:.2f}\n"
            f"- Model Notes: Standard legal summary inference generated for case {i}."
        )
        
        data.append({
            "filename": filename,
            "text(main info of case)": case_text,
            "raw_model_response": model_response,
            "Fine /Problem": "",
            "Please tell the problem ": "",
            "Please provide your name and credentials; if you prefer to remain anonymous, please provide your credentials only.": ""
        })
        
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    print(f"Successfully generated test dataset with {num_cases} cases at: {output_path}")

if __name__ == "__main__":
    generate_test_dataset(50, "Data/test_sample_50_cases.xlsx")
