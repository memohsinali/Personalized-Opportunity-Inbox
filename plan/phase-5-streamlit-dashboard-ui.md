# 📁 Phase 5 Specification: Interactive Streamlit Copilot Dashboard
**Phase:** 5 of 6  
**Focus:** Frontend Architecture, Responsive Components, Custom CSS Glassmorphism & State Management

---

## 🎯 1. Phase Objective
Build an intuitive, visually stunning, and responsive Streamlit dashboard (`app.py`) backed by custom CSS (`styles.css`). The dashboard must enable judges to view ranked opportunity cards, inspect transparent deterministic scoring breakdowns, filter spam/noise into a separate bin, paste custom emails, and interactively toggle student personas to see live re-ranking in real time.

---

## 📂 2. Files to Implement in this Phase

| File Path | Purpose |
| :--- | :--- |
| [`codebase/app.py`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/app.py) | Main Streamlit application entrypoint with interactive tabs, sidebar profile, and cards. |
| [`codebase/assets/styles.css`](file:///home/dev/Personalized%20Opportunity%20Ranking/codebase/assets/styles.css) | Custom modern CSS for glassmorphic cards, gradient rank badges, and urgency pills. |

---

## 🎨 3. UI Layout & Component Architecture

```text
+-----------------------------------------------------------------------------------+
| 🎓 OPPORTUNITY INBOX COPILOT                                                      |
| Top Metrics: [ 📬 10 Scanned ] [ ✨ 8 Opportunities ] [ 🚨 3 Urgent ] [ 🗑️ 2 Spam ] |
+----------------------+------------------------------------------------------------+
| SIDEBAR              | MAIN CONTENT TABS                                          |
| 👤 Student Profile   | [ 🏆 Priority Feed ] [ 📊 Scoring Matrix ] [ 🗑️ Spam ] [ 📥 Ingest ] |
| - Preset Persona     +------------------------------------------------------------+
|   Selector (1-Click) | 🥇 RANK #1 TOP MATCH   [ 🚨 Closes in 2 Days ]              |
| - Degree / Major     | FAST-NU Alumni Need-Based Scholarship 2026                 |
| - Semester & CGPA    | 💡 Evidence: Top Match (100% Fit + 48h Deadline)           |
| - Skills multiselect | ---------------------------------------------------------- |
| - Financial Need     | 🔍 [ Expand Score Breakdown ]   | 📋 [ Action Checklist ]  |
| 🔑 API Config        | - CGPA Fit: +25 pts             | [ ] Salary Slip          |
| [ 🔄 Re-Parse AI ]   | - Major Fit: +25 pts            | [ ] Transcript (3.6)     |
|                      | - Urgency: 100/100              | [ 🚀 Apply Portal Link ] |
+----------------------+------------------------------------------------------------+
```

---

## 🧱 4. Detailed Component Specifications

### A. Sidebar: Form-Based Student Profile Form
- **Persona Quick-Switcher**: Dropdown with 4 presets:
  1. *Hamza Tariq (High-Achieving CS Senior — CGPA 3.85)*
  2. *Ayesha Khan (Need-Based Sophomore — CGPA 3.40)*
  3. *Bilal Ahmed (BBA Finance Student — CGPA 3.65)*
  4. *Zainab Malik (Curious Freshman — CGPA 3.10)*
- **Interactive Form Inputs**:
  - `st.selectbox` for Degree
  - `st.number_input` for Semester and CGPA
  - `st.multiselect` for Skills and Preferred Opportunity Types
  - `st.checkbox` for Financial Need Status
- **API Configuration Section**:
  - Password text input for optional Gemini API key.
  - Button to re-parse raw emails with Gemini LLM on demand.

### B. Header & Metric Counter Cards
- Render 4 top-level key metrics:
  - Total Scanned Emails (`st.metric`)
  - Genuine Opportunities Found (`st.metric`)
  - Urgent Deadlines (<7 days) (`st.metric`)
  - Filtered Noise / Spam Count (`st.metric`)

### C. Tab 1: Priority Opportunity Feed (The Core Copilot View)
- Displays opportunities sorted in descending rank order.
- **Card Styling**:
  - Gold (`#FFD700`), Silver (`#E0E0E0`), and Bronze (`#CD7F32`) gradient rank badges for Top 3.
  - Dynamic urgency badges (🚨 Critical for $\le 2\text{d}$, ⚡ High for $\le 7\text{d}$, ⏳ Medium for $\le 14\text{d}$).
  - Evidence-backed rationale pill.
  - Two-column expanders for Score Breakdown ($S_{\text{fit}}, S_{\text{urgency}}, S_{\text{completeness}}$) and Action Checklist.
  - Direct Action button (`st.link_button`) linked to the verified application URL.

### D. Tab 2: Deterministic Scoring Matrix (Judge Auditing Table)
- Renders an interactive Pandas DataFrame displaying all mathematical columns:
  - Rank, Title, Type, Profile Fit ($40\%$), Urgency ($35\%$), Completeness ($25\%$), Penalty, Ineligibility Status, Final Composite Score.
- Displays the mathematical LaTeX formula.

### E. Tab 3: Filtered Spam / Noise Bin
- Inspects rejected non-opportunity emails (Lost & Found, Parking announcements) with exact reason why the AI filtered them out.

### F. Tab 4: Ingest / Custom Email Batch
- Text inputs and text area to paste new emails live during the demo and instantly parse them into the active inbox.

---

## 🧪 5. Verification & Acceptance Criteria
- [ ] Running `streamlit run codebase/app.py` launches the UI on `http://localhost:8501`.
- [ ] Switching between student personas in the sidebar immediately updates the ranking cards without requiring page reloads.
- [ ] Checkboxes inside action checklists persist state during user interaction.
- [ ] Custom CSS loads cleanly with dark-mode aesthetic, glowing badges, and readable typography.
