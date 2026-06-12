from django.shortcuts import render
import pdfplumber
import google.generativeai as genai
from .models import ResumeHistory  # 
from django.shortcuts import render, redirect, get_object_or_404
import os

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
            
            prompt = ""
            if action_type == 'analyze_mistakes':
                prompt = f"Act as an expert Resume Reviewer. Review this resume and provide feedback in structured Markdown. Use Emojis, short bullet points, and bold text for important keywords. Break it down into: 1. 🎯 Overall Impression, 2. 🚨 Key Mistakes, 3. ✨ Recommended Improvements.\n\nResume text:\n{extracted_text}"
            
            elif action_type == 'ats_score':
                prompt = f"Act as an ATS Expert. Calculate an estimated ATS score (out of 100) for this resume. Use structured Markdown with Emojis. Clearly output the score in a large heading. Then provide: 1. 🤖 Machine Readability Status, 2. ✅ What's Good, 3. ❌ Missing Sections/Keywords, 4. 🚀 3 Strict Recommendations.\n\nResume text:\n{extracted_text}"
            
            elif action_type == 'jd_match':
                prompt = f"Act as a Technical HR Recruiter. Compare this resume with the given Job Description. Use structured Markdown with Emojis. Provide: 1. 📊 Match Percentage (in bold heading), 2. 🟢 Matching Skills Found, 3. 🔴 Critical Skills Missing, 4. 💡 Final Verdict (Fit or Not Fit).\n\nJob Description:\n{job_description}\n\nResume Text:\n{extracted_text}"

            response = model.generate_content(prompt)
            ai_result = response.text

            ResumeHistory.objects.create(
                action_type=action_type,
                file_name=file_name,
                ai_result=ai_result
            )

            recent_history = ResumeHistory.objects.all().order_by('-created_at')[:5]
            return render(request, 'index.html', {'ai_result': ai_result, 'message': 'Analysis Complete!', 'history': recent_history})

    return render(request, 'index.html', {'history': recent_history})
def delete_history(request, item_id):
    item = get_object_or_404(ResumeHistory, id=item_id)
    item.delete()
    return redirect('home')

def view_history_result(request, item_id):
    history_item = get_object_or_404(ResumeHistory, id=item_id)
    recent_history = ResumeHistory.objects.all().order_by('-created_at')
    
    return render(request, 'index.html', {
        'ai_result': history_item.ai_result, 
        'history': recent_history
    })