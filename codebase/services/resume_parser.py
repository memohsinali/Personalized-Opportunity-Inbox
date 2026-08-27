import io
import json
import re
from typing import Dict, Any, Optional, List
import pypdf

from config import GEMINI_API_KEY, GEMINI_MODEL
from models.profile import StudentProfile


class ResumeParserService:
    """
    Service to extract and parse student profile information from a Resume PDF.
    Supports LLM extraction with Gemini and offline rule-based heuristic extraction.
    """

    EXTRACTION_PROMPT = """You are an expert AI Resume Parser for university students.
Extract the student's academic and technical profile from the resume text into a structured JSON format.

Tasks:
1. Extract the full name of the student.
2. Extract the degree/major (e.g. BS Computer Science, BS Software Engineering, BS Data Science, BS Artificial Intelligence, Bachelor of Business Administration (BBA), BS Electrical Engineering).
3. Extract current semester (integer between 1 and 8). If not mentioned, estimate based on graduation year / current year (e.g. Junior/3rd year = 6, Senior/4th year = 8). Default to 6 if unknown.
4. Extract CGPA (float between 0.00 and 4.00) ONLY if explicitly stated in the resume. If not explicitly found, return null.
5. Extract key technical and professional skills as a list of strings (e.g., ["Python", "FastAPI", "Machine Learning", "SQL", "Docker", "Git"]).
6. Extract career domains and technical interests as a list of strings (e.g., ["Artificial Intelligence", "Software Engineering"]).
7. Extract location preference (e.g. "Any", "Remote", "Lahore", "Islamabad", "Global").
8. Provide a brief 1-2 sentence past experience summary.

Return ONLY valid JSON matching this exact structure:
{
  "name": "string",
  "degree": "string",
  "semester": integer,
  "cgpa": float or null,
  "skills": ["string"],
  "interests": ["string"],
  "location_preference": "string",
  "past_experience": "string"
}
"""

    @classmethod
    def extract_text_from_pdf(cls, file_bytes_or_buffer: Any) -> str:
        """Extracts plain text from a PDF file buffer or bytes."""
        try:
            if isinstance(file_bytes_or_buffer, bytes):
                reader = pypdf.PdfReader(io.BytesIO(file_bytes_or_buffer))
            else:
                reader = pypdf.PdfReader(file_bytes_or_buffer)

            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts).strip()
        except Exception as e:
            print(f"[ResumeParserService] Error reading PDF: {e}")
            return ""

    @classmethod
    def parse_with_gemini(cls, resume_text: str, api_key: Optional[str] = None) -> Optional[StudentProfile]:
        """Uses Gemini API to extract a structured StudentProfile from resume text."""
        key = api_key or GEMINI_API_KEY
        if not key:
            return None

        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config={"response_mime_type": "application/json"}
            )

            prompt = f"{cls.EXTRACTION_PROMPT}\n\nRESUME TEXT:\n{resume_text}"
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            # Validate degree
            degree = cls._normalize_degree(data.get("degree", ""))
            data["degree"] = degree
            data["student_id"] = "uploaded_resume_student"
            # Ensure preferred types and financial need are left to manual user selection
            if "preferred_types" not in data or not data["preferred_types"]:
                data["preferred_types"] = ["Internship", "Scholarship", "Hackathon / Competition"]
            if "financial_need" not in data:
                data["financial_need"] = False

            return StudentProfile(**data)
        except Exception as e:
            print(f"[ResumeParserService] Gemini extraction failed: {e}. Falling back to heuristics.")
            return None

    @classmethod
    def parse_with_heuristics(cls, resume_text: str) -> StudentProfile:
        """Rule-based heuristic extractor for offline operation."""
        text_lower = resume_text.lower()

        # 1. Degree Detection
        degree = "BS Computer Science"
        if any(w in text_lower for w in ["software engineering", "bs se", "bsse"]):
            degree = "BS Software Engineering"
        elif any(w in text_lower for w in ["data science", "bs ds", "bsds"]):
            degree = "BS Data Science"
        elif any(w in text_lower for w in ["artificial intelligence", "bs ai", "bsai"]):
            degree = "BS Artificial Intelligence"
        elif any(w in text_lower for w in ["bba", "business administration", "finance", "marketing"]):
            degree = "Bachelor of Business Administration (BBA)"
        elif any(w in text_lower for w in ["electrical engineering", "bs ee", "bsee"]):
            degree = "BS Electrical Engineering"

        # 2. CGPA Detection (None if not explicitly found)
        cgpa = None
        cgpa_matches = re.findall(r'(?:cgpa|gpa|grade point|cumulative gpa)[:\s]*([0-4](?:\.\d{1,2})?)', text_lower)
        if cgpa_matches:
            try:
                cgpa_val = float(cgpa_matches[0])
                if 1.0 <= cgpa_val <= 4.0:
                    cgpa = cgpa_val
            except ValueError:
                pass
        else:
            # Look for general X.XX / 4.00 patterns
            gpa_slash = re.findall(r'([0-3]\.\d{1,2})\s*/\s*4', text_lower)
            if gpa_slash:
                try:
                    cgpa = float(gpa_slash[0])
                except ValueError:
                    pass

        # 3. Semester Detection
        semester = 6
        sem_matches = re.findall(r'(?:semester|sem)[:\s]*([1-8])', text_lower)
        if sem_matches:
            semester = int(sem_matches[0])
        elif "final year" in text_lower or "senior" in text_lower:
            semester = 7
        elif "junior" in text_lower or "3rd year" in text_lower:
            semester = 5
        elif "sophomore" in text_lower or "2nd year" in text_lower:
            semester = 3
        elif "freshman" in text_lower or "1st year" in text_lower:
            semester = 1

        # 4. Skills Extraction
        known_skills = [
            "Python", "Machine Learning", "FastAPI", "PyTorch", "TensorFlow",
            "SQL", "Docker", "JavaScript", "HTML/CSS", "React", "Node.js",
            "C++", "Java", "Data Analysis", "Git", "ROS", "Financial Modeling",
            "Business Strategy", "Deep Learning", "NLP", "Pandas", "Scikit-Learn"
        ]
        found_skills = []
        for s in known_skills:
            pattern = rf'\b{re.escape(s.lower())}\b'
            if re.search(pattern, text_lower):
                found_skills.append(s)

        if not found_skills:
            found_skills = ["Python", "Data Analysis", "Git"]

        # 5. Extract candidate Name (usually in first 2 lines)
        lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
        name = "Uploaded Candidate"
        if lines:
            first_line = lines[0]
            # Simple check that it's a realistic name
            if len(first_line.split()) <= 4 and not any(ch in first_line for ch in ["@", "http", "www", "resume", "curriculum"]):
                name = first_line

        interests = ["Software Engineering", "Artificial Intelligence"]
        if "business" in text_lower or "marketing" in text_lower:
            interests = ["Business Strategy", "Financial Modeling"]

        return StudentProfile(
            student_id="uploaded_resume_student",
            name=name,
            degree=degree,
            semester=semester,
            cgpa=cgpa,
            skills=found_skills,
            interests=interests,
            preferred_types=["Internship", "Scholarship", "Hackathon / Competition"],
            financial_need=False,
            location_preference="Any",
            past_experience=f"Extracted from resume: {degree} student with skills in {', '.join(found_skills[:4])}."
        )


    @classmethod
    def _normalize_degree(cls, degree_str: str) -> str:
        degree_lower = degree_str.lower()
        if "software" in degree_lower:
            return "BS Software Engineering"
        elif "data" in degree_lower:
            return "BS Data Science"
        elif "artificial" in degree_lower or "ai" in degree_lower:
            return "BS Artificial Intelligence"
        elif "business" in degree_lower or "bba" in degree_lower:
            return "Bachelor of Business Administration (BBA)"
        elif "electrical" in degree_lower:
            return "BS Electrical Engineering"
        return "BS Computer Science"

    @classmethod
    def parse_resume(cls, pdf_source: Any, api_key: Optional[str] = None) -> Optional[StudentProfile]:
        """Main entry point to parse a PDF file into a StudentProfile."""
        text = cls.extract_text_from_pdf(pdf_source)
        if not text:
            return None

        profile = None
        if api_key or GEMINI_API_KEY:
            profile = cls.parse_with_gemini(text, api_key=api_key)

        if profile is None:
            profile = cls.parse_with_heuristics(text)

        return profile
