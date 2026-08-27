# 📁 Phase 6 Specification: Testing, Verification & Judge Demo Playbook
**Phase:** 6 of 6  
**Focus:** Automated Verification Scripts, Edge-Case Validation & 2-Minute Winning Demo Strategy

---

## 🎯 1. Phase Objective
Verify all components of the system end-to-end through automated Python scripts and establish a scripted 2-minute demo walkthrough for the competition presentation to maximize judging criteria scores.

---

## 📂 2. Files to Implement in this Phase

| File Path | Purpose |
| :--- | :--- |
| [`codebase/test_pipeline.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/test_pipeline.py) | Standalone verification script testing models, parsing, scoring formulas, and ranking assertions. |
| [`plan/phase-6-testing-and-judge-demo-playbook.md`](file:///home/dev/Personalized%20Opportunity%20Ranking/plan/phase-6-testing-and-judge-demo-playbook.md) | (This document) Step-by-step test matrix & pitch presentation playbook. |

---

## 🧪 3. Automated Verification Matrix (`test_pipeline.py`)

The verification script must test the following 5 core assertions:

```python
# 1. Verification of Data Loading
assert len(sample_emails) >= 10, "Must have at least 10 sample emails"
assert len(preset_profiles) >= 4, "Must have at least 4 student personas"

# 2. Verification of Spam Noise Filtering
parsed_results = EmailParserService.parse_email_batch(sample_emails)
spam_items = [p for p in parsed_results if not p.is_opportunity]
assert len(spam_items) >= 2, "Must filter out at least 2 non-opportunity spam emails"

# 3. Verification of High-CGPA Persona Ranking
cs_star_profile = StudentProfile(**preset_profiles[0]) # CGPA 3.85
ranked_cs = ScoringEngine.rank_opportunities(cs_star_profile, parsed_results)
assert ranked_cs[0].opportunity.opportunity_type in ["Scholarship", "Internship", "Research / Fellowship"]

# 4. Verification of Persona Re-Ranking (Business Persona)
bba_profile = StudentProfile(**preset_profiles[2]) # BBA Finance
ranked_bba = ScoringEngine.rank_opportunities(bba_profile, parsed_results)
assert "McKinsey" in ranked_bba[0].opportunity.title or "Business" in ranked_bba[0].opportunity.title

# 5. Verification of Ineligibility Penalty
low_cgpa_profile = StudentProfile(degree="BS CS", semester=6, cgpa=2.5)
ranked_low = ScoringEngine.rank_opportunities(low_cgpa_profile, parsed_results)
csail_item = next(r for r in ranked_low if "MIT" in r.opportunity.title or "CSAIL" in r.opportunity.title)
assert csail_item.scoring.is_eligible == False, "Student with 2.5 CGPA must be flagged ineligible for CSAIL"
assert csail_item.scoring.ineligible_penalty > 0, "Ineligibility penalty must be applied"
```

---

## 🎤 4. Winning 2-Minute Judge Demo Script

### ⏱️ Act 1: The Problem & Cluttered Inbox (0:00 – 0:30)
1. **Hook**: *"Judges, university students receive dozens of emails every week about scholarships, internships, hackathons, and research grants. Because deadlines are buried in natural language paragraphs, high-value opportunities are ignored or missed."*
2. **Show the UI**: Point to the **10 Scanned Emails** and the **Noise Bin (2 filtered spam emails)** to demonstrate clean noise rejection.

### ⏱️ Act 2: Deep Extraction & Actionable Checklist (0:30 – 1:00)
1. Show **Rank #1 Card**:
   - Highlight the **Urgency Badge** (*"Closes in 48 hours"*).
   - Point to the **Evidence Rationale Pill** (*"Ranked #1 because: 100% Major match, CGPA 3.85 >= 3.0, and high deadline urgency"*).
2. Show the **Action Checklist**:
   - Point out that it doesn't just summarize — it tells the student *what documents to pull* (Transcript, Guardian Salary Slip, Tailored CV) with a one-click apply portal.

### ⏱️ Act 3: Live Personalization & Determinism Proof (1:00 – 1:45)
1. **Live Persona Switch**:
   - Change the sidebar persona from **Hamza (CS Senior)** to **Bilal (BBA Finance Student)**.
   - **Watch the feed re-order live**: McKinsey Business Analyst instantly shoots to Rank #1, while CS-only internships drop down!
2. **Open the "Deterministic Scoring Matrix" Tab**:
   - Show the mathematical formula: $\text{Score} = 0.40(S_{\text{fit}}) + 0.35(S_{\text{urgency}}) + 0.25(S_{\text{completeness}}) - \text{Penalty}$.
   - Prove that every ranking is 100% mathematically transparent, not random LLM hallucination.

### ⏱️ Act 4: Live Custom Email Ingestion & Q&A (1:45 – 2:00)
1. Switch to **Tab 4 (Ingest)**:
   - Click *"Add to Active Inbox"* with a custom email snippet.
   - Show it immediately parsed, scored, and placed into the priority hierarchy.
2. **Closing**: *"Opportunity Inbox Copilot turns cluttered inboxes into a prioritized, actionable career launchpad."*
