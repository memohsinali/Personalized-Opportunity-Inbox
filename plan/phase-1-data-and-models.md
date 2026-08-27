# 📁 Phase 1 Specification: Data Models, Config & Test Datasets
**Phase:** 1 of 6  
**Focus:** Core Data Structures, Validation Schemas, Benchmark Dataset, and Environment Setup

---

## 🎯 1. Phase Objective
Establish the foundational data layer and test infrastructure for the Opportunity Inbox Copilot. This includes defining strongly typed Pydantic models for student profiles, extracted email opportunities, scoring breakdowns, and curated realistic sample emails for hackathon judging.

---

## 📂 2. Files to Implement in this Phase

| File Path | Purpose |
| :--- | :--- |
| [`codebase/config.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/config.py) | Environment variables, scoring weights ($40/35/25$), and directory paths. |
| [`codebase/requirements.txt`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/requirements.txt) | Dependency manifest (`streamlit`, `pydantic`, `google-genai`, `pandas`, `python-dotenv`). |
| [`codebase/.env.example`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/.env.example) | Template for API keys (`GEMINI_API_KEY`). |
| [`codebase/models/profile.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/models/profile.py) | `StudentProfile` Pydantic model representing the structured student CV/form. |
| [`codebase/models/opportunity.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/models/opportunity.py) | `EligibilityCriteria`, `ParsedOpportunity`, `ScoringBreakdown`, `ActionItem`, and `RankedOpportunity` models. |
| [`codebase/models/__init__.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/models/__init__.py) | Export module for clean imports. |
| [`codebase/data/sample_emails.json`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/data/sample_emails.json) | 10–12 realistic, diverse university emails covering scholarships, ML internships, hackathons, fellowships, and spam. |
| [`codebase/data/preset_profiles.json`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/data/preset_profiles.json) | 4 student personas for 1-click live demo switching (CS Star, Need-Based, BBA, Freshman). |

---

## 🧱 3. Detailed Specifications

### A. Configuration (`config.py`)
- Define directory anchors: `BASE_DIR`, `DATA_DIR`, `ASSETS_DIR`.
- Define mathematical weights:
  - `WEIGHT_PROFILE_FIT = 0.40`
  - `WEIGHT_URGENCY = 0.35`
  - `WEIGHT_COMPLETENESS = 0.25`
- Read `GEMINI_API_KEY` from `.env` with fallback.

### B. Student Profile Model (`models/profile.py`)
Must contain all fields required by the competition paper:
```python
class StudentProfile(BaseModel):
    student_id: str
    name: str
    degree: str                  # e.g., "BS Computer Science"
    semester: int                # 1 to 8
    cgpa: float                  # 0.0 to 4.0
    skills: List[str]            # e.g., ["Python", "Machine Learning", "FastAPI"]
    interests: List[str]         # e.g., ["AI Research", "Software Engineering"]
    preferred_types: List[str]   # ["Internship", "Scholarship", "Hackathon"]
    financial_need: bool         # True / False
    location_preference: str     # "Remote", "Lahore", "Any"
    past_experience: Optional[str]
```

### C. Opportunity Models (`models/opportunity.py`)
1. **`EligibilityCriteria`**: `min_cgpa` (float), `eligible_majors` (list), `eligible_semesters` (list), `financial_need_required` (bool).
2. **`ParsedOpportunity`**: `email_id`, `is_opportunity` (bool), `rejection_reason`, `title`, `organization`, `opportunity_type`, `deadline` (ISO string), `days_until_deadline`, `eligibility`, `required_documents`, `benefits`, `application_link`, `contact_email`, `summary`.
3. **`ScoringBreakdown`**: `fit_score`, `fit_reasons`, `urgency_score`, `urgency_reason`, `completeness_score`, `completeness_reasons`, `ineligible_penalty`, `is_eligible`, `ineligibility_reasons`, `final_score`.
4. **`ActionItem`**: `task`, `category` (Document / Application / Calendar), `is_completed` (bool).
5. **`RankedOpportunity`**: `rank` (int), `opportunity` (ParsedOpportunity), `scoring` (ScoringBreakdown), `evidence_tag` (str), `action_checklist` (List[ActionItem]).

### D. Sample Datasets
1. **`sample_emails.json`**:
   - `email_01`: Urgent Need-based Scholarship (Closes in 2 days, CGPA 3.0+ required).
   - `email_02`: Google Summer of Code (Global open-source internship, CS/SE, deadline in 14 days).
   - `email_03`: MIT-Harvard CSAIL Fellowship (Strict CGPA 3.75+, Semesters 5-8, Deep Learning).
   - `email_04`: SOFTEC 2026 AI Hackathon (Open to all degrees, cash prize, team registration).
   - `email_05`: McKinsey Business Analyst Internship (BBA/Finance only, CGPA 3.3+).
   - `email_06`: Spam / Noise — Lost water bottle in CS Lab.
   - `email_07`: Spam / Noise — Campus parking permit renewal notice.
   - `email_08`: Local ML Engineer Summer Internship (Paid stipend, Python/Docker, deadline in 4 days).
   - `email_09`: Expired Event — Fall robotic competition from last year.
   - `email_10`: Goldman Sachs Virtual Insights Series (Open to all, FinTech/quant).

---

## ✅ 4. Verification & Acceptance Criteria
- [ ] Running `python3 -c "from models import StudentProfile, ParsedOpportunity"` executes with zero errors.
- [ ] `sample_emails.json` contains valid JSON with 10 test emails.
- [ ] `preset_profiles.json` contains 4 distinct student personas.
