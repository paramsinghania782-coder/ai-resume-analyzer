from django.shortcuts import render, redirect, get_object_or_404
import pdfplumber
import google.generativeai as genai
from .models import ResumeHistory
import os
import json
import re

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

def extract_json_from_text(text):
    """
    Ek helper function jo AI ke raw text me se sirf valid JSON nikalta hai.
    """
    text = text.strip()
    # Find everything between the first { and the last }
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        clean_json = match.group(0)
        # Handle escape characters that might break JSON
        clean_json = clean_json.replace('\n', ' ').replace('\r', '')
        return clean_json
    return text

def home(request):
    recent_history = ResumeHistory.objects.all().order_by('-created_at')[:5]

    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        resume_file = request.FILES.get('resume_file')
        job_description = request.POST.get('job_description', '')

        extracted_text = ""

        if resume_file:
            file_name = resume_file.name
            with pdfplumber.open(resume_file) as pdf:
                for page in pdf.pages:
                    extracted_text += page.extract_text() + "\n"
            
            # Using JSON response format feature (if supported by the specific model version)
            # or just strict prompting.
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = ""
            if action_type == 'analyze_mistakes':
                prompt = f"""Act as an expert Resume Reviewer. Review this resume and provide feedback strictly as a valid, parsable JSON object.
                CRITICAL: Return ONLY JSON. Do not return markdown, do not use 
```json, do not add introductory text.
                Ensure all string values are enclosed in double quotes. Avoid using unescaped double quotes inside the text.
                Required JSON Structure:
                {{
                    "overall_impression": "A single string summarizing the resume.",
                    "key_mistakes": ["mistake 1", "mistake 2"],
                    "improvements": ["suggestion 1", "suggestion 2"]
                }}
                Resume text: {extracted_text}"""
            
            elif action_type == 'ats_score':
                prompt = f"""Act as an ATS Expert. Calculate an estimated ATS score for this resume strictly as a valid JSON object.
                CRITICAL: Return ONLY JSON. Do not return markdown, do not use 
```json.
                Required JSON Structure:
                {{
                    "score": integer between 0 and 100,
                    "readability": "String describing machine readability status.",
                    "good_points": ["point 1", "point 2"],
                    "missing_sections": ["missing 1", "missing 2"],
                    "recommendations": ["rec 1", "rec 2"]
                }}
                Resume text: {extracted_text}"""
            
            elif action_type == 'jd_match':
                prompt = f"""Act as a Technical HR Recruiter. Compare this resume with the Job Description. Output strictly as a valid JSON object.
                CRITICAL: Return ONLY JSON. Do not return markdown, do not use 
```json.
                Required JSON Structure:
                {{
                    "match_percentage": integer between 0 and 100,
                    "matched_skills": ["skill 1", "skill 2"],
                    "missing_skills": ["skill 1", "skill 2"],
                    "verdict": "Final verdict string (e.g., 'Strong Fit', 'Not Fit')"
                }}
                Job Description: {job_description}
                Resume Text: {extracted_text}"""

            response = model.generate_content(prompt)
            raw_ai_text = response.text
            
            # Use the new cleaner function
            cleaned_json_string = extract_json_from_text(raw_ai_text)

            try:
                # Try to parse the cleaned text
                parsed_data = json.loads(cleaned_json_string)
            except json.JSONDecodeError as e:
                # If it still fails, fallback gracefully
                parsed_data = {
                    "error": "Failed to parse AI output. AI returned incorrectly formatted data.", 
                    "raw_text": raw_ai_text,
                    "parse_error": str(e)
                }

            ResumeHistory.objects.create(
                action_type=action_type,
                file_name=file_name,
                ai_result=json.dumps(parsed_data) 
            )

            recent_history = ResumeHistory.objects.all().order_by('-created_at')[:5]
            
            return render(request, 'index.html', {
                'ai_data': parsed_data, 
                'action_type': action_type,
                'message': 'Analysis Complete!', 
                'history': recent_history
            })

    return render(request, 'index.html', {'history': recent_history})


def delete_history(request, item_id):
    item = get_object_or_404(ResumeHistory, id=item_id)
    item.delete()
    return redirect('home')


def view_history_result(request, item_id):
    history_item = get_object_or_404(ResumeHistory, id=item_id)
    recent_history = ResumeHistory.objects.all().order_by('-created_at')[:5]
    
    try:
        parsed_data = json.loads(history_item.ai_result)
    except:
        parsed_data = {"error": "Old text format", "raw_text": history_item.ai_result}
    
    return render(request, 'index.html', {
        'ai_data': parsed_data,
        'action_type': history_item.action_type, 
        'history': recent_history
    })
