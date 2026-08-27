# 🏛️ Opportunity Inbox Copilot — System Architecture & Data Flow

**SOFTEC 2026 AI Hackathon Competition**  
*Email Parsing, Noise Rejection & Personalized Opportunity Ranking System*

---

## 🎯 1. End-to-End System Pipeline & Data Flow Diagram

```mermaid
flowchart TD
    %% STAGE 1: INPUTS
    subgraph S1 ["📥 STAGE 1: INBOX & PROFILE INPUTS"]
        direction TB
        RAW_EMAILS["📬 Raw University Emails<br/>(Paragraphs, Announcements, Deadlines)"]
        PROFILE["👤 Structured Student Profile (CV)<br/>• Degree / Major: BS CS / BBA<br/>• Semester: 1-8 | CGPA: 0.0-4.0<br/>• Skills & Career Interests<br/>• Financial Need: True/False"]
    end

    %% STAGE 2: AI PARSING
    subgraph S2 ["🤖 STAGE 2: AI PARSING & NOISE FILTERING (email_parser.py)"]
        direction TB
        PARSER["Gemini 2.0 Flash / Heuristic Parser<br/>(Strict JSON Mode & Regex Fallback)"]
        IS_OPP{"Is Genuine<br/>Opportunity?"}
        SPAM_STORE["🗑️ Filtered Spam / Noise Bin<br/>(Lost & Found, Parking Permits,<br/>Facility Announcements)"]
        PARSED_JSON["📄 Clean ParsedOpportunity Objects<br/>• Title & Organization<br/>• Opportunity Type (Scholarship/Internship/Hackathon)<br/>• ISO Deadline & Days Remaining<br/>• Eligibility: Min CGPA, Target Majors<br/>• Required Documents List<br/>• Benefits & Application Link"]
    end

    %% STAGE 3: DETERMINISTIC SCORING
    subgraph S3 ["⚖️ STAGE 3: DETERMINISTIC SCORING ENGINE (scoring_engine.py)"]
        direction TB
        FIT["🎯 1. Profile Fit Score (40% Weight)<br/>• CGPA Match: +25 pts<br/>• Major Match: +25 pts<br/>• Skills Overlap: +25 pts<br/>• Type Preference: +25 pts"]
        URG["🚨 2. Urgency Score (35% Weight)<br/>• 0-2 Days Left: 100 pts (Critical)<br/>• 3-7 Days Left: 80 pts (High)<br/>• 8-14 Days Left: 55 pts (Medium)<br/>• Expired: -1000 pts (Penalty)"]
        COMP["📋 3. Completeness Score (25% Weight)<br/>• Portal URL: +40 pts<br/>• Explicit Perks / Stipend: +30 pts<br/>• Enumerated Documents: +30 pts"]
        
        PENALTY{"Ineligibility Check<br/>(CGPA < Min OR<br/>Major Mismatch?)"}
        PEN_APPLY["Apply Penalty: -45 pts<br/>Flag 'is_eligible = False'"]
        
        FORMULA["🧮 Weighted Formula Calculation<br/>Final Score = (0.40 × Fit) + (0.35 × Urgency) + (0.25 × Completeness) - Penalty"]
        SORT["🔢 Deterministic Ranking<br/>Sort Descending by Final Score (#1, #2, #3...)"]
    end

    %% STAGE 4: ACTION & CHECKLIST GENERATION
    subgraph S4 ["✅ STAGE 4: ACTION & EVIDENCE GENERATOR (checklist_service.py)"]
        direction TB
        EVID_TAG["💡 Evidence Rationale Tag<br/>('🔥 Top Match: Closes in 2d + 100% Major Fit')"]
        TASKS["📝 Personalized Action Checklist<br/>• [Document] Request Transcript (CGPA: 3.85)<br/>• [Document] Tailor Resume for Python/PyTorch<br/>• [Application] Submit to Official Portal<br/>• [Calendar] Set Reminder for Deadline"]
    end

    %% STAGE 5: UI PRESENTATION
    subgraph S5 ["🖥️ STAGE 5: STREAMLIT COPILOT DASHBOARD (app.py)"]
        direction TB
        FEED["🏆 Tab 1: Priority Opportunity Feed<br/>• Gold / Silver / Bronze Rank Badges<br/>• Real-time Urgency Badges<br/>• Evidence Rationale Box<br/>• Interactive Action Checklist with Checkboxes<br/>• 1-Click Direct Apply Link Button"]
        MATRIX["📊 Tab 2: Deterministic Scoring Matrix<br/>• Transparent Table for Judges<br/>• Inspectable Fit, Urgency, Completeness & Penalties"]
        SPAM_TAB["🗑️ Tab 3: Filtered Spam Bin<br/>• View Ignored Emails & AI Rejection Rationale"]
        INGEST_TAB["📥 Tab 4: Ingest Custom Email<br/>• Live Form to Parse & Insert New Emails"]
    end

    %% ==========================================
    %% DATA FLOW CONNECTIONS
    %% ==========================================
    RAW_EMAILS -->|Raw Text Batch| PARSER
    PARSER --> IS_OPP
    
    IS_OPP -->|❌ Non-Opportunity| SPAM_STORE
    IS_OPP -->|✅ Valid Opportunity| PARSED_JSON
    
    PARSED_JSON --> FIT & URG & COMP
    PROFILE -->|Student Criteria| FIT & PENALTY
    
    FIT & URG & COMP --> FORMULA
    PENALTY -->|Violation Detected| PEN_APPLY --> FORMULA
    
    FORMULA --> SORT
    SORT --> EVID_TAG & TASKS
    
    SORT & EVID_TAG & TASKS --> FEED
    SORT --> MATRIX
    SPAM_STORE --> SPAM_TAB
```

---

## 🔍 2. Step-by-Step Data Flow Narrative

| Stage | Process Description | Input Data | Output Data |
| :---: | :--- | :--- | :--- |
| **Stage 1** | **Input Ingestion** | Raw messy emails (`sample_emails.json`) + Student form inputs (`StudentProfile`). | Plain text strings & profile object. |
| **Stage 2** | **AI Parsing & Noise Filter** | Email parser runs Gemini LLM (JSON Mode) or heuristic fallback to separate spam from real opportunities. | `ParsedOpportunity` objects + filtered spam list. |
| **Stage 3** | **Deterministic Scoring** | Pure Python engine calculates Fit ($40\%$), Urgency ($35\%$), and Completeness ($25\%$), then applies ineligibility penalties. | Auditable `ScoringBreakdown` and final ranks (`#1..#N`). |
| **Stage 4** | **Checklist Generation** | Maps parsed documents and URLs to tailored student action items and calendar reminders. | `List[ActionItem]` and evidence tags. |
| **Stage 5** | **Copilot Presentation** | Streamlit UI renders ranked cards, live persona switching, scoring matrices, and interactive checklists. | Interactive Web Dashboard on `localhost:8501`. |

---

## 📐 3. Mathematical Formula Specification

$$\text{Final Score} = (\underbrace{0.40 \times S_{\text{fit}}}_{\text{40% Profile Fit}}) + (\underbrace{0.35 \times S_{\text{urgency}}}_{\text{35% Deadline Urgency}}) + (\underbrace{0.25 \times S_{\text{completeness}}}_{\text{25% Actionability \& Perks}}) - \text{Penalty}_{\text{ineligible}}$$

### 🔹 Sub-Score Calculation Rules:
* **$S_{\text{fit}}$ (0 to 100 pts)**:
  * $\text{CGPA Match}$: $+25\text{ pts}$ if $\text{Student CGPA} \ge \text{Min CGPA}$
  * $\text{Major Match}$: $+25\text{ pts}$ if degree matches target fields
  * $\text{Skills Overlap}$: $+25\text{ pts}$ for keyword overlap
  * $\text{Preferred Type}$: $+25\text{ pts}$ for prioritized category
  * $\text{Financial Need}$: $+10\text{ pts}$ bonus if need-based
* **$S_{\text{urgency}}$ (0 to 100 pts)**:
  * $0 \le \text{days} \le 2$: $100\text{ pts}$ (🚨 Critical Urgency)
  * $3 \le \text{days} \le 7$: $80\text{ pts}$ (⚡ High Urgency)
  * $8 \le \text{days} \le 14$: $55\text{ pts}$ (⏳ Medium Urgency)
  * $\text{days} \ge 15$: $30\text{ pts}$ (📅 Low Urgency)
  * $\text{days} < 0$: $-1000\text{ pts}$ (❌ Expired)
* **$S_{\text{completeness}}$ (0 to 100 pts)**:
  * Verified Portal URL: $+40\text{ pts}$
  * Explicit Perks / Stipend: $+30\text{ pts}$
  * Required Documents List: $+30\text{ pts}$
* **Ineligibility Penalty**:
  * Deducts $-45\text{ pts}$ if the student fails strict criteria (e.g. CGPA below minimum).
