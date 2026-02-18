"""
AI Agent for intelligent form field detection and mapping.
Uses Groq AI to analyze form structure and decide how to fill it.
"""

import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def analyze_form_with_ai(form_fields, user_profile):
    """
    AI Agent: Analyzes form fields and intelligently maps user data to them.
    
    Args:
        form_fields: List of dicts with field info (id, name, placeholder, type)
        user_profile: User's structured data from resume
    
    Returns:
        Dict mapping field selectors to values to fill
    """
    
    # Prepare form field information for AI
    fields_info = "\n".join([
        f"- Field {i+1}: {f.get('id', 'no-id')} | name='{f.get('name', '')}' | placeholder='{f.get('placeholder', '')}' | type='{f.get('type', 'text')}'"
        for i, f in enumerate(form_fields)
    ])
    
    # Prepare user data
    user_data = json.dumps(user_profile, indent=2)
    
    prompt = f"""You are an AI agent that fills web forms. Analyze the form fields and user data, then create a mapping.

FORM FIELDS:
{fields_info}

USER DATA:
{user_data}

TASK: For each form field, determine:
1. Which user data field should fill it (if any)
2. The exact value to use
3. The best CSS selector to target it

Return ONLY a valid JSON object (no markdown, no explanation) in this format:
{{
  "selector1": "value1",
  "selector2": "value2"
}}

Use these selector strategies (in order of preference):
1. If field has id: use "#id"
2. If field has name: use "[name='name']"  
3. If field has placeholder: use "[placeholder='text']"
4. If field has type: use "[type='type']"

IMPORTANT:
- Only include fields you can confidently fill
- Use exact values from USER DATA
- For names: use first_name/last_name separately if fields exist
- For dropdowns: match the expected format
- Skip fields you're unsure about

JSON OUTPUT:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert AI agent that analyzes web forms and maps data intelligently. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up markdown code blocks if AI included them
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        # Parse the JSON mapping
        field_mapping = json.loads(result)
        return field_mapping
        
    except Exception as e:
        print(f"AI Agent Error: {e}")
        return {}


def extract_form_fields(page):
    """
    Extract all form fields from the page for AI analysis.
    
    Returns:
        List of dicts with field information
    """
    try:
        fields_data = page.evaluate("""() => {
            const fields = [];
            
            // Get all input fields
            document.querySelectorAll('input, textarea, select').forEach(el => {
                if (el.type !== 'hidden' && el.type !== 'submit' && el.type !== 'button') {
                    fields.push({
                        tagName: el.tagName.toLowerCase(),
                        type: el.type || 'text',
                        id: el.id || '',
                        name: el.name || '',
                        placeholder: el.placeholder || '',
                        value: el.value || ''
                    });
                }
            });
            
            return fields;
        }""")
        
        return fields_data
    except Exception as e:
        print(f"Error extracting form fields: {e}")
        return []
