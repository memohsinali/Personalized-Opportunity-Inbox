import json
import os
from pathlib import Path
import streamlit as st
import pandas as pd
import urllib.parse

from config import DATA_DIR, ASSETS_DIR, GEMINI_API_KEY
from models import StudentProfile, ParsedOpportunity, RankedOpportunity
from services import (
    EmailParserService,
    ScoringEngine,
    ChecklistService,
    ResumeParserService,
    ImapSyncService,
    ApplicationService,
    MailboxWatcherService,
)

# ==========================================
# ⚙️ Page Configuration & Styling
# ==========================================
st.set_page_config(
    page_title="Opportunity Inbox Copilot | SOFTEC 2026",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
css_path = ASSETS_DIR / "styles.css"
if css_path.exists():
    with open(css_path, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ==========================================
# 📦 Data Loaders
@st.cache_data
def load_preset_profiles():
    with open(DATA_DIR / "preset_profiles.json", "r") as f:
        return json.load(f)


preset_profiles = load_preset_profiles()


# ==========================================
# 🧠 Session State Initialization (Pure Live Mode)
# ==========================================
if "parsed_opportunities" not in st.session_state:
    # Pure live mode: start with clean empty inbox
    st.session_state.parsed_opportunities = []

if "active_emails" not in st.session_state:
    st.session_state.active_emails = []

if "uploaded_profile" not in st.session_state:
    st.session_state.uploaded_profile = None

if "last_uploaded_file" not in st.session_state:
    st.session_state.last_uploaded_file = None

if "connected_email" not in st.session_state:
    st.session_state.connected_email = ""

if "connected_pass" not in st.session_state:
    st.session_state.connected_pass = ""

if "uploaded_resume_bytes" not in st.session_state:
    st.session_state.uploaded_resume_bytes = None

if "uploaded_resume_name" not in st.session_state:
    st.session_state.uploaded_resume_name = None



# ==========================================
# 👤 Sidebar: Student Profile Form & Resume Upload
# ==========================================
with st.sidebar:
    st.markdown("## 👤 Student Profile")
    st.caption("Auto-extract from your Resume PDF or choose a preset persona.")

    # Resume PDF Upload Widget
    uploaded_pdf = st.file_uploader(
        "📄 Upload Resume (PDF):",
        type=["pdf"],
        help="Upload your resume.pdf to extract degree, skills, and projects."
    )

    if uploaded_pdf is not None and st.session_state.last_uploaded_file != uploaded_pdf.name:
        with st.spinner("Extracting profile intelligence from resume..."):
            pdf_bytes = uploaded_pdf.getvalue()
            st.session_state.uploaded_resume_bytes = pdf_bytes
            st.session_state.uploaded_resume_name = uploaded_pdf.name
            extracted = ResumeParserService.parse_resume(pdf_bytes, api_key=GEMINI_API_KEY)
            if extracted:
                st.session_state.uploaded_profile = extracted
                st.session_state.last_uploaded_file = uploaded_pdf.name
                if extracted.cgpa is not None and extracted.cgpa > 0:
                    st.success(f"✅ Extracted: **{extracted.name}** | **{extracted.degree}** (CGPA: **{extracted.cgpa:.2f}**)")
                else:
                    st.warning(f"📄 Extracted: **{extracted.name}** | **{extracted.degree}**\n\n⚠️ *CGPA not detected in resume. Please enter your CGPA below.*")
            else:
                st.error("Could not parse text from this PDF. Please verify the file is not scanned/empty.")


    # 1-Click Persona Selector
    preset_names = [p["name"] for p in preset_profiles]
    preset_options = ["Custom Profile"]
    if st.session_state.uploaded_profile:
        preset_options.append("📄 Uploaded Resume Profile")
    preset_options.extend(preset_names)

    selected_preset_name = st.selectbox(
        "⚡ Quick Persona Preset:",
        preset_options,
        index=1 if len(preset_options) > 1 else 0,
        help="Select a persona or your uploaded resume to test dynamic re-ranking instantly."
    )

    if selected_preset_name == "📄 Uploaded Resume Profile" and st.session_state.uploaded_profile:
        up = st.session_state.uploaded_profile
        default_degree = up.degree
        default_semester = up.semester
        default_cgpa = up.cgpa if up.cgpa is not None else 0.00
        default_skills = up.skills
        default_interests = up.interests
        default_types = ["Internship", "Scholarship", "Hackathon / Competition"]
        default_need = False
        default_loc = up.location_preference
    elif selected_preset_name != "Custom Profile" and selected_preset_name != "📄 Uploaded Resume Profile":
        preset_data = next(p for p in preset_profiles if p["name"] == selected_preset_name)
        default_degree = preset_data["degree"]
        default_semester = preset_data["semester"]
        default_cgpa = preset_data.get("cgpa", 0.00)
        default_skills = preset_data["skills"]
        default_interests = preset_data["interests"]
        default_types = preset_data.get("preferred_types", ["Internship", "Scholarship"])
        default_need = preset_data.get("financial_need", False)
        default_loc = preset_data.get("location_preference", "Any")
    else:
        default_degree = "BS Computer Science"
        default_semester = 6
        default_cgpa = 3.65
        default_skills = ["Python", "Machine Learning", "FastAPI"]
        default_interests = ["Artificial Intelligence", "Software Engineering"]
        default_types = ["Internship", "Scholarship", "Hackathon / Competition"]
        default_need = False
        default_loc = "Any"

    # Form Fields: Section 1 (Academic & Skills)
    with st.expander("🎓 Academic & Technical Profile", expanded=True):
        available_degrees = [
            "BS Computer Science",
            "BS Software Engineering",
            "BS Data Science",
            "BS Artificial Intelligence",
            "Bachelor of Business Administration (BBA)",
            "BS Electrical Engineering"
        ]
        degree_idx = 0
        for i, d in enumerate(available_degrees):
            if d.lower() in default_degree.lower() or default_degree.lower() in d.lower():
                degree_idx = i
                break

        degree = st.selectbox(
            "Degree / Major",
            available_degrees,
            index=degree_idx
        )
        col_s, col_g = st.columns(2)
        with col_s:
            semester = st.number_input("Semester", min_value=1, max_value=8, value=int(default_semester))
        with col_g:
            cgpa_val = float(default_cgpa) if default_cgpa is not None else 0.00
            cgpa = st.number_input(
                "CGPA",
                min_value=0.00,
                max_value=4.00,
                value=cgpa_val,
                step=0.05,
                format="%.2f",
                help="Set your current CGPA. Set to 0.00 if unassigned."
            )

        if cgpa == 0.00:
            st.caption("ℹ️ *CGPA is 0.00 (Opportunities requiring min CGPA will be flagged).*")

        skills_list = [
            "Python", "PyTorch", "Machine Learning", "FastAPI", "JavaScript",
            "HTML/CSS", "SQL", "Docker", "ROS", "Financial Modeling",
            "Business Strategy", "Data Analysis", "C++", "Git", "Deep Learning",
            "React", "Node.js", "Java", "NLP", "Pandas", "Scikit-Learn"
        ]
        combined_skills = list(dict.fromkeys(default_skills + skills_list))
        selected_skills = st.multiselect("Skills (from Resume / Input)", combined_skills, default=default_skills)

    # Form Fields: Section 2 (User's Active Search Intent - Manual Selectors)
    with st.expander("🎯 Active Search Intent (Manual Choice)", expanded=True):
        st.caption("Select what opportunities you are actively targeting this term:")
        all_types = ["Scholarship", "Internship", "Hackathon / Competition", "Research / Fellowship", "Workshop / Conference", "Job"]
        valid_default_types = [t for t in default_types if t in all_types] or ["Internship", "Scholarship"]
        selected_types = st.multiselect(
            "Target Opportunity Types:",
            all_types,
            default=valid_default_types,
            help="Opportunities matching these types will receive a +25 pts category fit boost."
        )

        financial_need = st.checkbox(
            "Demonstrated Financial Need",
            value=default_need,
            help="Check this if you are actively applying for need-based scholarships & fee waivers."
        )

    # Construct active profile object
    current_profile = StudentProfile(
        student_id="active_student",
        name=selected_preset_name,
        degree=degree,
        semester=int(semester),
        cgpa=float(cgpa) if cgpa > 0 else None,
        skills=selected_skills,
        interests=default_interests,
        preferred_types=selected_types,
        financial_need=financial_need,
        location_preference=default_loc,
    )


    st.divider()
    st.markdown("### 🔑 AI API Configuration")
    user_api_key = st.text_input("Gemini API Key (Optional)", value=GEMINI_API_KEY, type="password", help="Leave blank to use intelligent offline heuristic parser.")

    if st.button("🔄 Re-Parse Emails with AI", use_container_width=True):
        with st.spinner("AI Parsing & extracting entities from emails..."):
            st.session_state.parsed_opportunities = EmailParserService.parse_email_batch(
                st.session_state.active_emails,
                api_key=user_api_key
            )
            st.success("Successfully parsed and updated opportunities!")

    st.divider()
    st.markdown("### 📧 Live Mailbox Sync")
    with st.expander("🔗 Connect Gmail / IMAP Inbox", expanded=False):
        st.caption("Fetch real emails from your personal Gmail, Outlook, or university webmail.")
        mail_provider = st.selectbox(
            "Mail Provider:",
            ["Gmail", "Outlook / Office 365", "Yahoo Mail", "Custom / University Webmail"],
            index=0,
            key="sb_mail_prov"
        )

        preset_config = ImapSyncService.PRESET_SERVERS.get(mail_provider, {"host": "imap.gmail.com", "port": 993})
        default_host = preset_config["host"] if preset_config["host"] else "imap.nu.edu.pk"
        imap_host = st.text_input("IMAP Host:", value=default_host, key="sb_imap_host")
        imap_user = st.text_input("Email Address:", placeholder="your.name@gmail.com", key="sb_imap_user")
        imap_pass = st.text_input("App Password (16-char):", type="password", help="Use your 16-letter Google App Password from myaccount.google.com/apppasswords", key="sb_imap_pass")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fetch_limit = st.number_input("Max Emails:", min_value=1, max_value=50, value=10, key="sb_fetch_limit")
        with col_f2:
            unread_only = st.checkbox("Unread only", value=False, key="sb_unread_only")

        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if st.button("📥 Fetch & Rank Live Emails", use_container_width=True, key="sb_btn_fetch"):
                if not imap_user or not imap_pass:
                    st.error("Please provide both your email address and App Password.")
                else:
                    with st.spinner(f"Connecting to {imap_host} and retrieving live emails..."):
                        success, live_emails, msg = ImapSyncService.fetch_live_emails(
                            imap_host=imap_host,
                            email_address=imap_user,
                            app_password=imap_pass,
                            limit=int(fetch_limit),
                            unread_only=unread_only,
                        )
                        if success:
                            st.session_state.connected_email = imap_user.strip()
                            st.session_state.connected_pass = imap_pass.strip()
                            if live_emails:
                                st.session_state.active_emails.extend(live_emails)
                                new_parsed = EmailParserService.parse_email_batch(live_emails, api_key=user_api_key)
                                st.session_state.parsed_opportunities.extend(new_parsed)
                                st.success(f"🎉 {msg}")
                                st.rerun()
                            else:
                                st.info(msg)
                        else:
                            st.error(f"❌ {msg}")
        with col_btn2:
            if st.button("🗑️ Clear", use_container_width=True, help="Clear active inbox to start fresh"):
                st.session_state.active_emails = []
                st.session_state.parsed_opportunities = []
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚡ Live Auto-Watcher")
        auto_watch_enabled = st.toggle(
            "Enable Background Live Polling",
            value=st.session_state.get("auto_watcher_active", False),
            key="toggle_auto_watcher",
            help="Automatically checks your mailbox in the background every 15s and auto-ranks new opportunities!"
        )

        if auto_watch_enabled:
            st.session_state.auto_watcher_active = True
            if imap_user and imap_pass:
                if not MailboxWatcherService.is_running():
                    existing_ids = [e.get("id") for e in st.session_state.active_emails if e.get("id")]
                    MailboxWatcherService.register_existing_ids(existing_ids)
                    MailboxWatcherService.start_watcher(
                        imap_host=imap_host,
                        email_address=imap_user,
                        app_password=imap_pass,
                        interval_seconds=15,
                        api_key=user_api_key,
                    )
                st.markdown("""
                <div style="display: flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); padding: 8px 12px; border-radius: 8px; font-size: 12.5px; color: #6EE7B7; margin-top: 6px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981;"></span>
                    <b>Live Auto-Watcher Active</b> (Checking every 15s)
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ Enter your email & App Password above to activate auto-watcher.")
        else:
            st.session_state.auto_watcher_active = False
            if MailboxWatcherService.is_running():
                MailboxWatcherService.stop_watcher()






# ==========================================
# 📊 Main Dashboard Area
# ==========================================
# Drain pending auto-watcher events if any
if MailboxWatcherService.is_running():
    drained = MailboxWatcherService.drain_pending_items()
    if drained["raw_emails"]:
        st.session_state.active_emails.extend(drained["raw_emails"])
        st.session_state.parsed_opportunities.extend(drained["opportunities"])
        for notif in drained["notifications"]:
            if notif["type"] == "opportunity":
                st.toast(f"{notif['title']}\n{notif['body']}", icon="🎉")
            else:
                st.toast(f"{notif['title']}\n{notif['body']}", icon="🗑️")
        st.rerun()

st.markdown("# 🎓 Opportunity Inbox Copilot")
st.markdown("*Intelligent Email Parsing, Noise Filtering, & Deterministic Opportunity Ranking*")


# Compute dynamic ranking
all_parsed = st.session_state.parsed_opportunities
ranked_items = ScoringEngine.rank_opportunities(current_profile, all_parsed)

# Categorized subsets
active_ranked = [r for r in ranked_items if r.scoring.urgency_score >= 0]
urgent_ranked = [r for r in active_ranked if (r.opportunity.days_until_deadline is not None and r.opportunity.days_until_deadline <= 7) or r.scoring.urgency_score >= 70]
critical_ranked = [r for r in active_ranked if (r.opportunity.days_until_deadline is not None and r.opportunity.days_until_deadline <= 2) or r.scoring.urgency_score >= 90]
expired_ranked = [r for r in ranked_items if r.scoring.urgency_score < 0 or (r.opportunity.days_until_deadline is not None and r.opportunity.days_until_deadline < 0)]
spam_list = [p for p in all_parsed if not p.is_opportunity]

if "dashboard_view" not in st.session_state:
    st.session_state.dashboard_view = "active"

# ==========================================
# 🔘 Interactive Top Metric Filter Cards
# ==========================================
st.markdown("##### ⚡ Quick Filter & Inbox Overview (Click to inspect list):")
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

with col_m1:
    btn_label_1 = f"📬 All Scanned\n\n**{len(all_parsed)} Emails**"
    if st.button(btn_label_1, use_container_width=True, type="primary" if st.session_state.dashboard_view == "all_scanned" else "secondary"):
        st.session_state.dashboard_view = "all_scanned"
        st.rerun()

with col_m2:
    btn_label_2 = f"✨ Active Matches\n\n**{len(active_ranked)} Found**"
    if st.button(btn_label_2, use_container_width=True, type="primary" if st.session_state.dashboard_view == "active" else "secondary"):
        st.session_state.dashboard_view = "active"
        st.rerun()

with col_m3:
    btn_label_3 = f"🚨 Urgent (<7d)\n\n**{len(urgent_ranked)} Closing**"
    if st.button(btn_label_3, use_container_width=True, type="primary" if st.session_state.dashboard_view == "urgent" else "secondary"):
        st.session_state.dashboard_view = "urgent"
        st.rerun()

with col_m4:
    btn_label_4 = f"❌ Expired\n\n**{len(expired_ranked)} Archived**"
    if st.button(btn_label_4, use_container_width=True, type="primary" if st.session_state.dashboard_view == "expired" else "secondary"):
        st.session_state.dashboard_view = "expired"
        st.rerun()

with col_m5:
    btn_label_5 = f"🗑️ Noise / Spam\n\n**{len(spam_list)} Filtered**"
    if st.button(btn_label_5, use_container_width=True, type="primary" if st.session_state.dashboard_view == "spam" else "secondary"):
        st.session_state.dashboard_view = "spam"
        st.rerun()

st.write("")


# ==========================================
# 🛠️ Reusable Card Renderer
# ==========================================
def render_opportunity_card(item: RankedOpportunity, show_rank: bool = True, is_expired_view: bool = False, key_prefix: str = "main"):
    opp = item.opportunity
    score = item.scoring

    # Urgency badge styling
    if is_expired_view or score.urgency_score < 0:
        urgency_html = f'<span class="urgency-expired">❌ EXPIRED ({score.urgency_reason})</span>'
    elif score.urgency_score >= 90:
        urgency_html = f'<span class="urgency-critical">🚨 {score.urgency_reason}</span>'
    elif score.urgency_score >= 70:
        urgency_html = f'<span class="urgency-high">⚡ {score.urgency_reason}</span>'
    else:
        urgency_html = f'<span class="urgency-medium">⏳ {score.urgency_reason}</span>'

    # Rank badge
    if not is_expired_view and show_rank:
        if item.rank == 1:
            rank_html = f'<span class="rank-badge-1">🥇 RANK #{item.rank} TOP MATCH</span>'
        elif item.rank == 2:
            rank_html = f'<span class="rank-badge-2">🥈 RANK #{item.rank}</span>'
        elif item.rank == 3:
            rank_html = f'<span class="rank-badge-3">🥉 RANK #{item.rank}</span>'
        else:
            rank_html = f'<span class="rank-badge-normal">RANK #{item.rank}</span>'
    else:
        rank_html = f'<span class="rank-badge-normal">ARCHIVE</span>'

    # Portal link or direct contact HTML
    portal_html = ""
    if opp.application_link and opp.application_link.startswith("http"):
        portal_html = f"""
        <div class="portal-link-box">
            <div class="portal-link-text">
                🔗 <b>Official Portal Link:</b> <a href="{opp.application_link}" target="_blank">{opp.application_link}</a>
            </div>
            <span style="font-size: 11px; background: rgba(99,102,241,0.25); color: #C7D2FE; padding: 3px 8px; border-radius: 6px;">Direct Web Portal</span>
        </div>
        """
    elif opp.contact_email and "no-reply" not in opp.contact_email.lower():
        portal_html = f"""
        <div class="portal-link-box">
            <div class="portal-link-text">
                ✉️ <b>Direct Recruiter Inbox:</b> <a href="mailto:{opp.contact_email}">{opp.contact_email}</a>
            </div>
            <span style="font-size: 11px; background: rgba(16,185,129,0.2); color: #6EE7B7; padding: 3px 8px; border-radius: 6px;">Email Submission</span>
        </div>
        """

    with st.container():
        st.markdown(f"""
        <div class="opportunity-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>
                    {rank_html} &nbsp;
                    <span style="background: rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 6px; font-size: 12px; color: #94A3B8;">
                        🏢 {opp.organization or 'Organization'} • 🏷️ {opp.opportunity_type}
                    </span>
                </div>
                <div>
                    {urgency_html}
                </div>
            </div>
            <h3 style="margin: 6px 0 10px 0; color: #FFFFFF;">{opp.title}</h3>
            <div class="evidence-pill">
                💡 <b>Evidence Rationale:</b> {item.evidence_tag}
            </div>
            {portal_html}
            <p style="color: #CBD5E1; font-size: 14px; line-height: 1.6; margin: 8px 0;">{opp.summary}</p>
        </div>
        """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1.5, 1.3])

        with col_left:
            with st.expander(f"🔍 Score Breakdown & Requirements ({score.final_score:.1f}/100 pts)"):
                st.markdown("**Profile Fit Analysis (40% Weight):**")
                for r in score.fit_reasons:
                    st.markdown(f"- ✅ {r}")
                if score.ineligibility_reasons:
                    for ir in score.ineligibility_reasons:
                        st.markdown(f"- ❌ **Ineligibility Warning:** {ir}")

                st.markdown(f"**Urgency Factor (35% Weight):** {score.urgency_score}/100 pts")
                st.markdown(f"**Completeness & Actionability (25% Weight):** {score.completeness_score}/100 pts")
                for cr in score.completeness_reasons:
                    st.markdown(f"- 🔹 {cr}")

                if opp.benefits:
                    st.markdown(f"🎁 **Benefits / Perks:** `{opp.benefits}`")
                if opp.deadline:
                    st.markdown(f"📅 **Application Deadline:** `{opp.deadline}`")

        with col_right:
            with st.expander("📋 Action Checklist & Apply", expanded=True):
                for idx, act in enumerate(item.action_checklist):
                    st.checkbox(f"{act.task}", key=f"chk_{key_prefix}_{item.rank}_{idx}_{opp.email_id}", value=False)

                portal_url = opp.application_link
                if not portal_url or not portal_url.startswith("http"):
                    search_query = f"{opp.organization or ''} {opp.title or ''} careers apply portal"
                    portal_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"

                st.link_button(
                    f"🚀 Direct Apply on {opp.organization or 'Official'} Portal",
                    portal_url,
                    use_container_width=True
                )
                if opp.contact_email and "no-reply" not in opp.contact_email.lower():
                    st.link_button("✉️ Send Direct Recruiter Email", f"mailto:{opp.contact_email}", use_container_width=True)

        # 📋 1-Click Portal Autofill Assistant (Copy-paste answers for company portal)
        with st.expander("📋 Portal Autofill Assistant (Copy & Paste to Form)", expanded=False):
            st.caption("Use these pre-formatted snippets to quickly fill out the company's application form:")
            c_af1, c_af2 = st.columns(2)
            with c_af1:
                st.text_input("Full Name:", value=current_profile.name, key=f"af_name_{key_prefix}_{item.rank}_{opp.email_id}")
                st.text_input("Degree & Major:", value=current_profile.degree, key=f"af_deg_{key_prefix}_{item.rank}_{opp.email_id}")
            with c_af2:
                st.text_input("CGPA:", value=f"{current_profile.cgpa:.2f} / 4.00" if current_profile.cgpa else "N/A", key=f"af_cgpa_{key_prefix}_{item.rank}_{opp.email_id}")
                st.text_input("Key Skills:", value=", ".join(current_profile.skills[:6]) if current_profile.skills else "", key=f"af_skills_{key_prefix}_{item.rank}_{opp.email_id}")
            
            why_pitch = f"I am a {current_profile.degree} student with strong expertise in {', '.join(current_profile.skills[:4])}. I am excited to apply for the {opp.title} role at {opp.organization or 'your company'} to contribute to impactful initiatives."
            st.text_area("Summary / Why Hire Me Statement:", value=why_pitch, height=75, key=f"af_pitch_{key_prefix}_{item.rank}_{opp.email_id}")

        # ✨ 1-Click AI Application Drafter & Direct Sender

        with st.expander("✨ 1-Click AI Application Drafter & Sender", expanded=False):
            draft = ApplicationService.generate_application_draft(current_profile, opp)
            curr_user_email = (st.session_state.get("connected_email") or st.session_state.get("sb_imap_user", "")).strip().lower()
            recip_val = draft["recipient"]
            if recip_val and recip_val.strip().lower() == curr_user_email:
                recip_val = ""

            draft_recip = st.text_input(
                "Recipient Email (Recruiter / Company):",
                value=recip_val,
                placeholder="e.g. careers@company.com or admissions@university.edu",
                key=f"app_recip_{key_prefix}_{item.rank}_{opp.email_id}"
            )
            draft_subj = st.text_input("Subject Line:", value=draft["subject"], key=f"app_subj_{key_prefix}_{item.rank}_{opp.email_id}")
            draft_body = st.text_area("Tailored Application / Cover Letter:", value=draft["body"], height=160, key=f"app_body_{key_prefix}_{item.rank}_{opp.email_id}")

            has_resume = bool(st.session_state.get("uploaded_resume_bytes"))
            resume_fname = st.session_state.get("uploaded_resume_name", "Resume.pdf")
            attach_resume_val = False
            if has_resume:
                attach_resume_val = st.checkbox(
                    f"📎 Attach my uploaded resume ({resume_fname})",
                    value=True,
                    key=f"chk_att_{key_prefix}_{item.rank}_{opp.email_id}"
                )
            else:
                st.caption("ℹ️ *Tip: Upload your Resume PDF in the sidebar to automatically attach it to your application email!*")

            c_send1, c_send2 = st.columns([1.5, 1])
            with c_send1:
                btn_send_label = "🚀 Send Application with Attached Resume" if (has_resume and attach_resume_val) else "🚀 Send Application from my Gmail"
                if st.button(btn_send_label, key=f"btn_send_{key_prefix}_{item.rank}_{opp.email_id}", use_container_width=True):
                    sender_addr = st.session_state.get("connected_email") or st.session_state.get("sb_imap_user", "")
                    sender_pwd = st.session_state.get("connected_pass") or st.session_state.get("sb_imap_pass", "")
                    if not sender_addr or not sender_pwd:
                        st.warning("⚠️ Please connect your Gmail in the sidebar to enable 1-click email sending.")
                    elif not draft_recip:
                        st.error("Please specify a recipient email address.")
                    else:
                        with st.spinner(f"Sending application to {draft_recip}..."):
                            ok, msg = ApplicationService.send_email_smtp(
                                smtp_host="smtp.gmail.com",
                                sender_email=sender_addr,
                                app_password=sender_pwd,
                                recipient_email=draft_recip,
                                subject=draft_subj,
                                body=draft_body,
                                attachment_bytes=st.session_state.get("uploaded_resume_bytes") if attach_resume_val else None,
                                attachment_filename=resume_fname if attach_resume_val else None,
                            )
                            if ok:
                                st.success(f"🎉 {msg}")
                            else:
                                st.error(f"❌ {msg}")
            with c_send2:
                mailto_url = f"mailto:{draft_recip}?subject={draft_subj}"
                st.link_button("📋 Open in Mail Client", mailto_url, use_container_width=True)


        # ✉️ Interactive Original Email Viewer
        orig_email = next((e for e in st.session_state.active_emails if str(e.get("id")) == str(opp.email_id)), None)
        with st.expander("✉️ View Original Email Message", expanded=False):
            if orig_email:
                sender_val = orig_email.get("sender", "Unknown Sender")
                subject_val = orig_email.get("subject", "No Subject")
                date_val = orig_email.get("date_received", "2026-03-01")
                body_val = orig_email.get("body", "No message body found.")

                st.markdown(f"""
                <div class="raw-email-box">
                    <div class="raw-email-header">
                        <div><b>From:</b> {sender_val}</div>
                        <div><b>Subject:</b> {subject_val}</div>
                        <div><b>Date Received:</b> {date_val}</div>
                    </div>
                    <div style="white-space: pre-wrap; word-break: break-word; max-height: 280px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #E2E8F0;">{body_val}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"Original email content for `{opp.email_id}` is summarized: {opp.summary}")


        st.write("")


# ==========================================
# 📑 Main Navigation Tabs & Filter Routing
# ==========================================
if st.session_state.dashboard_view != "active":
    col_info, col_reset = st.columns([4, 1.2])
    with col_info:
        view_title = {
            "all_scanned": "📬 All Scanned Inbox Emails",
            "urgent": "🚨 Urgent Deadlines (<7 Days)",
            "expired": "❌ Expired Opportunities Archive",
            "spam": "🗑️ Filtered Non-Opportunity Noise Bin",
        }.get(st.session_state.dashboard_view, st.session_state.dashboard_view)
        st.info(f"🔍 **Active Filter View:** {view_title}")
    with col_reset:
        if st.button("✖️ Reset Filter", use_container_width=True):
            st.session_state.dashboard_view = "active"
            st.rerun()

tab_ranked, tab_urgent, tab_expired, tab_matrix, tab_spam, tab_ingest = st.tabs([
    f"🏆 Priority Feed ({len(active_ranked)})",
    f"🚨 Urgent Watchlist ({len(urgent_ranked)})",
    f"❌ Expired Archive ({len(expired_ranked)})",
    "📊 Scoring Matrix",
    f"🗑️ Noise Bin ({len(spam_list)})",
    "📥 Ingest Emails",
])



# ==========================================
# 🏆 TAB 1: Priority Opportunity Feed
# ==========================================
with tab_ranked:
    cgpa_str = f"CGPA: **{cgpa:.2f}**" if cgpa > 0 else "*CGPA Unassigned*"
    st.markdown(f"### 🎯 Personalized Priority Feed for **{degree}** ({cgpa_str})")
    st.caption("Rankings are computed deterministically using Profile Fit (40%) + Urgency (35%) + Completeness (25%).")

    # Critical Urgency Banner
    if critical_ranked and st.session_state.dashboard_view in ["active", "urgent"]:
        crit_titles = ", ".join([f"'{c.opportunity.title[:30]}...'" for c in critical_ranked])
        st.markdown(f"""
        <div class="urgent-banner">
            <div style="font-size: 24px;">🚨</div>
            <div>
                <b>Critical Deadlines Closing in &lt;48 Hours!</b><br/>
                <span style="font-size: 13px; color: #FEE2E2;">Immediate action required for {len(critical_ranked)} opportunity: {crit_titles}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Determine items to render based on active top filter
    if st.session_state.dashboard_view == "urgent":
        display_items = urgent_ranked
    elif st.session_state.dashboard_view == "expired":
        display_items = expired_ranked
    elif st.session_state.dashboard_view == "all_scanned":
        display_items = ranked_items
    elif st.session_state.dashboard_view == "spam":
        display_items = []
        st.info(f"Displaying {len(spam_list)} filtered noise emails in the Spam Bin below:")
        for s in spam_list:
            with st.expander(f"🚫 {s.summary or s.email_id}"):
                st.markdown(f"**AI Filter Reason:** `{s.rejection_reason or 'Non-actionable campus announcement'}`")
                st.caption(f"Email ID: `{s.email_id}` | Organization: `{s.organization or 'University Campus'}`")
    else:
        display_items = active_ranked

    if not all_parsed:
        st.markdown("""
        <div style="background: rgba(99, 102, 241, 0.08); border: 1px dashed rgba(99, 102, 241, 0.35); border-radius: 16px; padding: 36px 24px; text-align: center; margin: 24px 0;">
            <div style="font-size: 36px; margin-bottom: 10px;">📬</div>
            <h3 style="color: #FFFFFF; margin: 0 0 8px 0;">Live Mailbox Mode Active</h3>
            <p style="color: #94A3B8; font-size: 14px; max-width: 580px; margin: 0 auto 16px auto; line-height: 1.6;">
                Your Opportunity Inbox is clean and ready. Open <b>📧 Live Mailbox Sync</b> in the left sidebar (or Tab 6) to connect your <b>Gmail</b> or <b>University Mailbox</b> and pull real-time opportunities.
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif display_items:
        for item in display_items:
            is_exp = (item.scoring.urgency_score < 0) or (item.opportunity.days_until_deadline is not None and item.opportunity.days_until_deadline < 0)
            render_opportunity_card(item, show_rank=not is_exp, is_expired_view=is_exp, key_prefix="feed")
    elif st.session_state.dashboard_view != "spam":
        st.info("No opportunities match the current filter criteria.")




# ==========================================
# 🚨 TAB 2: Urgent Watchlist (<7 Days)
# ==========================================
with tab_urgent:
    st.markdown(f"### 🚨 Urgent Opportunities Expiring Soon ({len(urgent_ranked)} Items)")
    st.caption("Opportunities with deadlines in the next 7 days prioritized for fast action.")

    if not urgent_ranked:
        st.success("🎉 No urgent deadlines closing in the next 7 days!")
    else:
        for item in urgent_ranked:
            render_opportunity_card(item, show_rank=True, is_expired_view=False, key_prefix="urgent")


# ==========================================
# ❌ TAB 3: Expired Opportunities Archive
# ==========================================
with tab_expired:
    st.markdown(f"### ❌ Expired Opportunities Archive ({len(expired_ranked)} Items)")
    st.caption("Past opportunities whose application deadline has already elapsed.")

    if not expired_ranked:
        st.info("No expired opportunities detected in this batch.")
    else:
        for item in expired_ranked:
            render_opportunity_card(item, show_rank=False, is_expired_view=True, key_prefix="expired")



# ==========================================
# 📊 TAB 4: Scoring Engine Matrix
# ==========================================
with tab_matrix:
    st.markdown("### 🔬 Mathematical Scoring & Ranking Matrix")
    st.markdown("Every score is 100% auditable and calculated via deterministic weighted formula:")
    st.latex(r"\text{Score} = (0.40 \times S_{\text{fit}}) + (0.35 \times S_{\text{urgency}}) + (0.25 \times S_{\text{completeness}}) - \text{Penalty}_{\text{ineligible}}")

    matrix_data = []
    for it in ranked_items:
        matrix_data.append({
            "Rank": f"#{it.rank}" if it.scoring.urgency_score >= 0 else "EXPIRED",
            "Title": it.opportunity.title[:35] + "...",
            "Type": it.opportunity.opportunity_type,
            "Fit (40%)": it.scoring.fit_score,
            "Urgency (35%)": it.scoring.urgency_score,
            "Completeness (25%)": it.scoring.completeness_score,
            "Penalty": it.scoring.ineligible_penalty,
            "Eligible?": "✅ Yes" if it.scoring.is_eligible else "❌ No",
            "Final Composite Score": it.scoring.final_score,
        })

    df_matrix = pd.DataFrame(matrix_data)
    st.dataframe(df_matrix, use_container_width=True, hide_index=True)


# ==========================================
# 🗑️ TAB 5: Filtered Spam / Noise Bin
# ==========================================
with tab_spam:
    st.markdown(f"### 🗑️ Filtered Non-Opportunity Emails ({len(spam_list)} Items)")
    st.caption("Emails detected as general campus notices, ads, or lost & found are automatically routed here.")

    if not spam_list:
        st.info("No spam detected in current email batch.")

    for s in spam_list:
        with st.expander(f"🚫 {s.summary or s.email_id}"):
            st.markdown(f"**AI Filter Reason:** `{s.rejection_reason or 'Non-actionable campus announcement'}`")
            st.caption(f"Email ID: `{s.email_id}` | Organization: `{s.organization or 'University Campus'}`")
            
            raw_s = next((e for e in st.session_state.active_emails if str(e.get("id")) == str(s.email_id)), None)
            if raw_s:
                st.markdown(f"""
                <div class="raw-email-box">
                    <div class="raw-email-header">
                        <div><b>From:</b> {raw_s.get('sender', 'Unknown')}</div>
                        <div><b>Subject:</b> {raw_s.get('subject', 'No Subject')}</div>
                    </div>
                    <div style="white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; color: #CBD5E1;">{raw_s.get('body', 'No message body text.')}</div>
                </div>
                """, unsafe_allow_html=True)



# ==========================================
# 📥 TAB 6: Ingest / Live Mailbox Sync
# ==========================================
with tab_ingest:
    ingest_mode = st.radio("Choose Ingestion Source:", ["📧 Live Gmail / IMAP Sync", "📝 Paste Custom Email"], horizontal=True)

    if ingest_mode == "📧 Live Gmail / IMAP Sync":
        st.markdown("### 📧 Live Gmail / University Mailbox Sync")
        st.caption("Securely connect to your inbox over SSL to pull real-time student opportunities.")

        c_prov, c_host = st.columns([1, 1])
        with c_prov:
            t_provider = st.selectbox(
                "Mail Provider Preset:",
                ["Gmail", "Outlook / Office 365", "Yahoo Mail", "Custom / University Webmail"],
                index=0,
                key="tab_provider"
            )
        with c_host:
            t_preset_cfg = ImapSyncService.PRESET_SERVERS.get(t_provider, {"host": "imap.gmail.com", "port": 993})
            t_host_val = t_preset_cfg["host"] if t_preset_cfg["host"] else "imap.nu.edu.pk"
            t_imap_host = st.text_input("IMAP Host:", value=t_host_val, key="tab_imap_host")

        c_user, c_pass = st.columns([1, 1])
        with c_user:
            t_imap_user = st.text_input("Email Address:", placeholder="student@gmail.com", key="tab_imap_user")
        with c_pass:
            t_imap_pass = st.text_input("Google App Password (16 Letters):", type="password", help="Create at myaccount.google.com/apppasswords", key="tab_imap_pass")

        c_lim, c_unr = st.columns([1, 1])
        with c_lim:
            t_limit = st.slider("Number of recent emails to scan:", min_value=1, max_value=30, value=10, key="tab_limit")
        with c_unr:
            t_unread = st.checkbox("Fetch unread emails only", value=False, key="tab_unread")

        if st.button("🚀 Connect & Fetch Live Emails from Inbox", use_container_width=True, key="tab_btn_fetch"):
            if not t_imap_user or not t_imap_pass:
                st.error("Please enter your email and App Password.")
            else:
                with st.spinner(f"Connecting to {t_imap_host} via IMAP SSL..."):
                    t_success, t_live_emails, t_msg = ImapSyncService.fetch_live_emails(
                        imap_host=t_imap_host,
                        email_address=t_imap_user,
                        app_password=t_imap_pass,
                        limit=int(t_limit),
                        unread_only=t_unread,
                    )
                    if t_success:
                        if t_live_emails:
                            st.session_state.active_emails.extend(t_live_emails)
                            t_parsed = EmailParserService.parse_email_batch(t_live_emails, api_key=user_api_key)
                            st.session_state.parsed_opportunities.extend(t_parsed)
                            st.success(f"🎉 {t_msg}")
                            st.rerun()
                        else:
                            st.info(t_msg)
                    else:
                        st.error(f"❌ {t_msg}")

    else:
        st.markdown("### 📥 Test with Custom Email Batch")
        custom_subject = st.text_input("Email Subject:", value="DeepMind Frontier AI Summer Research Internship 2026")
        custom_sender = st.text_input("Sender:", value="admissions@deepmind.com")
        custom_body = st.text_area(
            "Email Body Text:",
            height=180,
            value="We are hiring undergraduate interns in Computer Science / AI with CGPA >= 3.6. 12-week fully paid research fellowship with $4000/mo stipend. Must submit CV, transcript, and project proposal by March 6, 2026. Apply at: https://deepmind.google/internships"
        )

        if st.button("➕ Parse and Add to Active Inbox", use_container_width=True):
            new_email = {
                "id": f"custom_{len(st.session_state.active_emails) + 1}",
                "subject": custom_subject,
                "sender": custom_sender,
                "date_received": "2026-03-01",
                "body": custom_body
            }
            st.session_state.active_emails.append(new_email)
            parsed_new = EmailParserService.parse_email_batch([new_email], api_key=user_api_key)
            st.session_state.parsed_opportunities.extend(parsed_new)
            st.success("New email parsed and added to active inbox! Check the Priority Feed.")
            st.rerun()
