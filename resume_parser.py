# resume_parser.py
import fitz  # PyMuPDF
import json
import os
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def parse_resume_to_json(pdf_path="resume.pdf"):
    # 1. Read the PDF Text
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found!")
        return None

    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    
    print("✅ Resume text extracted. Asking AI to structure it...")

    # 2. Ask Groq to structure it
    prompt = f"""
    Extract the following details from this resume text and return ONLY a JSON object:
    - full_name
    - email
    - phone
    - linkedin_url
    - github_url
    - education (list of objects with degree, college, year, gpa)
    - skills (list of strings)
    - experience (list of objects with role, company, duration, description)
    - projects (list of objects with name, tech_stack, description)

    RESUME TEXT:
    {text}
    """

    completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a data extraction assistant. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"}
    )

    # 3. Save to profile.json
    profile_data = json.loads(completion.choices[0].message.content)
    
    with open("profile.json", "w") as f:
        json.dump(profile_data, f, indent=4)
        
    print("✅ profile.json created successfully!")
    return profile_data

if __name__ == "__main__":
    parse_resume_to_json()