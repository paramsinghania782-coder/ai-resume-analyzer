from django.shortcuts import render, redirect, get_object_or_404
import pdfplumber
import google.generativeai as genai
from .models import ResumeHistory
import os
import json

genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))

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
            
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # --- 1. Prompts for JSON Output ---
            prompt = ""
            if action_type == 'analyze_mistakes':
                prompt = f"""Act as an expert Resume Reviewer. Review this resume and provide feedback strictly as a JSON object.
                Required keys:
                - "overall_impression": A string summarizing the resume.
                - "key_mistakes": A list of strings detailing major mistakes.
                - "improvements": A list of actionable suggestions.
                Do not include markdown blocks like ```json.
                Resume text: {extracted_text}"""
            
            elif action_type == 'ats_score':
                prompt = f"""Act as an ATS Expert. Calculate an estimated ATS score for this resume strictly as a JSON object.
                Required keys:
                - "score": Integer between 0 and 100.
                - "readability": String describing machine readability status.
                - "good_points": List of strings for what's good.
                - "missing_sections": List of missing keywords/sections.
                - "recommendations": List of 3 strict recommendations.
                Do not include markdown blocks like ```json.
                Resume text: {extracted_text}"""
            
            elif action_type == 'jd_match':
                prompt = f"""Act as a Technical HR Recruiter. Compare this resume with the Job Description. Output strictly as a JSON object.
                Required keys:
                - "match_percentage": Integer between 0 and 100.
                - "matched_skills": List of strings for matching skills.
                - "missing_skills": List of strings for missing skills.
                - "verdict": Final verdict string (e.g., 'Strong Fit', 'Not Fit').
                Do not include markdown blocks like 
```json.
                Job Description: {job_description}
                Resume Text: {extracted_text}"""

            # --- 2. Getting Response & Cleaning it ---
            response = model.generate_content(prompt)
            raw_ai_text = response.text.strip()
            
            # Cleaning markdown if AI adds it
            if raw_ai_text.startswith("```json"):
                raw_ai_text = raw_ai_text[7:]
            if raw_ai_text.endswith("```"):
                raw_ai_text = raw_ai_text[:-3]
            raw_ai_text = raw_ai_text.strip()

            # --- 3. Parsing JSON ---
            try:
                parsed_data = json.loads(raw_ai_text)
            except json.JSONDecodeError:
                # Fallback if AI fails to give proper JSON
                parsed_data = {"error": "Failed to parse AI output. Try again.", "raw_text": response.text}

            # Save the JSON string in Database
            ResumeHistory.objects.create(
                action_type=action_type,
                file_name=file_name,
                ai_result=json.dumps(parsed_data) 
            )

            recent_history = ResumeHistory.objects.all().order_by('-created_at')[:5]
            
            # Passing parsed_data (dictionary) and action_type to template
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
    
    # Try to parse the saved string back into JSON dictionary
    try:
        parsed_data = json.loads(history_item.ai_result)
    except:
        # For older records that were saved as plain text
        parsed_data = {"error": "Old text format", "raw_text": history_item.ai_result}
    
    return render(request, 'index.html', {
        'ai_data': parsed_data,
        'action_type': history_item.action_type, 
        'history': recent_history
    })
