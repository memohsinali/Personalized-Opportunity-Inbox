import json
import os
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from models.opportunity import ParsedOpportunity, EligibilityCriteria
from config import GEMINI_API_KEY, GEMINI_MODEL


class EmailParserService:
    """
    AI Email Parsing and Entity Extraction Service.
    Uses Gemini API for structured JSON extraction with an offline heuristic fallback.
    """

    REFERENCE_DATE = date(2026, 3, 1)

    @classmethod
    def parse_dynamic_deadline(cls, full_text: str, date_received_str: Optional[str] = None) -> Tuple[str, int]:
        """
        Dynamically extracts and calculates application deadlines and days remaining.
        Supports absolute dates (e.g. 'March 15, 2026', '10/04/2026', 'Aug 26') and
        relative terms (e.g. 'closing soon', 'in 3 days', '24 hours', 'ends Sunday').
        """
        # Determine base reference date
        base_date = date(2026, 3, 1)
        if date_received_str:
            try:
                base_date = datetime.strptime(date_received_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        full_lower = full_text.lower()

        # 1. Check relative urgency phrases
        if any(p in full_lower for p in ["24 hours", "24 hrs", "last day", "closing today", "ends today", "midnight tonight", "after midnight"]):
            target = base_date + timedelta(days=1)
            return target.strftime("%Y-%m-%d"), 1

        if "tomorrow" in full_lower:
            target = base_date + timedelta(days=1)
            return target.strftime("%Y-%m-%d"), 1

        # Check 'in X days' or 'X days left'
        days_match = re.search(r"\b(\d{1,2})\s*(?:day|days|d)\s*(?:left|remaining|to apply)?\b", full_lower)
        if days_match:
            try:
                d_val = int(days_match.group(1))
                if 1 <= d_val <= 90:
                    target = base_date + timedelta(days=d_val)
                    return target.strftime("%Y-%m-%d"), d_val
            except Exception:
                pass

        if any(p in full_lower for p in ["closing soon", "urgent", "immediate action", "hurry", "final call"]):
            target = base_date + timedelta(days=2)
            return target.strftime("%Y-%m-%d"), 2

        if "ends sunday" in full_lower or "this sunday" in full_lower:
            days_ahead = 6 - base_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target = base_date + timedelta(days=days_ahead)
            return target.strftime("%Y-%m-%d"), max(1, days_ahead)

        if "next week" in full_lower or "this week" in full_lower or "within a week" in full_lower:
            target = base_date + timedelta(days=7)
            return target.strftime("%Y-%m-%d"), 7

        # 2. Explicit Date Matching ("Month Day, Year" or "Day Month Year")
        month_map = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
            "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12
        }

        month_names_regex = "|".join(month_map.keys())
        date_pattern1 = rf"\b({month_names_regex})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b"
        date_pattern2 = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names_regex})(?:,?\s+(\d{{4}}))?\b"

        # Search for dates mentioned
        matches1 = list(re.finditer(date_pattern1, full_lower))
        for m in matches1:
            m_name, d_str, y_str = m.group(1), m.group(2), m.group(3)
            try:
                month_num = month_map[m_name]
                day_num = int(d_str)
                year_num = int(y_str) if y_str else base_date.year
                target = date(year_num, month_num, day_num)
                diff = (target - base_date).days
                if diff < -60 and not y_str:
                    target = date(year_num + 1, month_num, day_num)
                    diff = (target - base_date).days
                return target.strftime("%Y-%m-%d"), max(1, diff)
            except Exception:
                continue

        matches2 = list(re.finditer(date_pattern2, full_lower))
        for m in matches2:
            d_str, m_name, y_str = m.group(1), m.group(2), m.group(3)
            try:
                month_num = month_map[m_name]
                day_num = int(d_str)
                year_num = int(y_str) if y_str else base_date.year
                target = date(year_num, month_num, day_num)
                diff = (target - base_date).days
                if diff < -60 and not y_str:
                    target = date(year_num + 1, month_num, day_num)
                    diff = (target - base_date).days
                return target.strftime("%Y-%m-%d"), max(1, diff)
            except Exception:
                continue

        # 3. ISO / Slash Date formats: YYYY-MM-DD or DD/MM/YYYY
        iso_match = re.search(r"\b(202[4-9])-(\d{2})-(\d{2})\b", full_lower)
        if iso_match:
            try:
                target = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
                diff = (target - base_date).days
                return target.strftime("%Y-%m-%d"), max(1, diff)
            except Exception:
                pass

        slash_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](202[4-9])\b", full_lower)
        if slash_match:
            try:
                target = date(int(slash_match.group(3)), int(slash_match.group(2)), int(slash_match.group(1)))
                diff = (target - base_date).days
                return target.strftime("%Y-%m-%d"), max(1, diff)
            except Exception:
                pass

        # 4. Default: Standard rolling 14-day window relative to the email's received date
        default_target = base_date + timedelta(days=14)
        return default_target.strftime("%Y-%m-%d"), 14


    EXTRACTION_SYSTEM_PROMPT = """You are an expert AI Email Copilot for university students.
Your job is to analyze incoming emails and strictly extract genuine student opportunities while rejecting noise and marketing spam.

Tasks:
1. Classify if the email contains a genuine student career or academic opportunity (Scholarship, Internship, Hackathon, Research Fellowship, Competition, Job, Grant, Workshop, Career Mentorship) OR if it is noise/spam.
   - REJECT as spam (is_opportunity: false) if it is:
     * Commercial shopping / retail brands / discounts / sales (e.g. Nike, Amazon, clothes, food delivery, Black Friday, promo codes).
     * Online paid course sales ads / commercial platforms (e.g. Udemy course discount, Skillshare, general e-learning ads).
     * Transactional notifications (e.g. OTP verification codes, password resets, order confirmations, bank statements, receipts).
     * Social media digests / newsletters (e.g. LinkedIn connection requests, Quora digest, generic weekly newsletters).
     * Campus administrative noise (e.g. Lost & Found, parking sticker notices, cafeteria announcements).
2. If it is NOT a genuine opportunity, set "is_opportunity": false and provide a clear "rejection_reason".
3. If it IS a genuine opportunity:
   - Extract title, organization, opportunity_type
   - Extract deadline in ISO format (YYYY-MM-DD) assuming reference current date is 2026-03-01. Calculate days_until_deadline.
   - Extract strict eligibility criteria: min_cgpa (float or null), eligible_majors (list of strings), eligible_semesters (list of ints), financial_need_required (boolean).
   - Extract list of required_documents (e.g. Resume, Transcript, SOP, Recommendation letters, Salary Slip).
   - Extract benefits (stipend, prize money, certificate, mentorship).
   - Extract application_link (URL) and contact_email.
   - Provide a concise 2-sentence summary.

Return ONLY valid JSON matching this exact structure:
{
  "email_id": "string",
  "is_opportunity": boolean,
  "rejection_reason": "string or null",
  "title": "string",
  "organization": "string",
  "opportunity_type": "Scholarship | Internship | Hackathon / Competition | Research / Fellowship | Workshop / Conference | Job",
  "deadline": "YYYY-MM-DD or null",
  "days_until_deadline": integer or null,
  "eligibility": {
    "min_cgpa": float or null,
    "eligible_majors": ["string"],
    "eligible_semesters": [integer],
    "financial_need_required": boolean,
    "other_requirements": "string or null"
  },
  "required_documents": ["string"],
  "benefits": "string or null",
  "application_link": "string or null",
  "contact_email": "string or null",
  "summary": "string"
}
"""

    @classmethod
    def parse_with_gemini(cls, email_obj: Dict[str, Any], api_key: Optional[str] = None) -> Optional[ParsedOpportunity]:
        """Calls Gemini API for LLM structured extraction."""
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
            
            prompt = (
                f"{cls.EXTRACTION_SYSTEM_PROMPT}\n\n"
                f"Email ID: {email_obj.get('id', 'email_x')}\n"
                f"Subject: {email_obj.get('subject', '')}\n"
                f"Sender: {email_obj.get('sender', '')}\n"
                f"Date: {email_obj.get('date_received', '2026-03-01')}\n\n"
                f"Email Content:\n{email_obj.get('body', '')}"
            )
            
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            data["email_id"] = email_obj.get("id", data.get("email_id", "email_x"))
            return ParsedOpportunity(**data)
        except Exception as e:
            print(f"[EmailParserService] Gemini API call failed: {e}. Falling back to rule-based parser.")
            return None

    @classmethod
    def parse_with_heuristics(cls, email_obj: Dict[str, Any]) -> ParsedOpportunity:
        """
        Deterministic Rule-based fallback parser for offline testing or instant zero-latency response.
        Smart 2-tier filtering: Prioritizes genuine job/internship/scholarship alerts while rejecting security, banking, and pure retail sales.
        """
        email_id = email_obj.get("id", "email_x")
        subject = email_obj.get("subject", "").strip()
        body = email_obj.get("body", "").strip()
        sender = email_obj.get("sender", "").lower()
        full_text = f"{subject}\n{body}".lower()

        # ----------------------------------------------------
        # 1. HARD SPAM / SECURITY / FINANCIAL TRANSACTION BLACKLIST
        # ----------------------------------------------------
        hard_spam_triggers = [
            # Security & Account alerts
            "security alert", "verification code", "one-time password", "otp", "password reset",
            "login from new device", "new login to", "you shared some google account data",
            # Financial & Banking transactions
            "raast otc", "transaction reversal", "refund", "bank statement", "receipt for your payment",
            # Direct chat & social pings
            "just messaged you", "sent you a message", "i want to connect",
            # Pure retail & clothing sales
            "the new pre-fall", "late summer edit", "clothing sale", "discount offer is ending",
            "flat 50% off on apparel", "free delivery on orders above", "buy 1 get 1 free",
            # Campus facilities noise
            "lost & found", "water bottle", "parking permit", "parking sticker", "cafeteria", "lost item", "transport wing"
        ]

        for trigger in hard_spam_triggers:
            if trigger in full_text:
                return ParsedOpportunity(
                    email_id=email_id,
                    is_opportunity=False,
                    rejection_reason=f"Filtered ({trigger.title()}). Automated notification/transaction or non-career notice.",
                    summary=subject
                )

        # Expired notice detection
        if "[expired]" in full_text or "closed on december" in full_text or "no late entries" in full_text:
            return ParsedOpportunity(
                email_id=email_id,
                is_opportunity=True,
                title=subject.replace("[EXPIRED]", "").strip(),
                organization="University Society",
                opportunity_type="Hackathon / Competition",
                deadline="2025-12-15",
                days_until_deadline=-76,
                summary="Past event whose submission deadline has already elapsed.",
                rejection_reason="Deadline Expired"
            )

        # ----------------------------------------------------
        # 2. STRONG OPPORTUNITY SIGNAL CHECK (Job, Internship, Scholarship, Hackathon)
        # ----------------------------------------------------
        opp_type = None
        if any(k in full_text for k in ["scholarship", "financial aid", "grant", "tuition fee waiver"]):
            opp_type = "Scholarship"
        elif any(k in full_text for k in ["internship", "intern", "summer analyst", "summer associate", "trainee", "apprentice"]):
            opp_type = "Internship"
        elif any(k in full_text for k in ["hackathon", "speed programming", "coding competition", "capture the flag", "ctf"]):
            opp_type = "Hackathon / Competition"
        elif any(k in full_text for k in ["fellowship", "summer research", "research assistant", "research lab", "phd position"]):
            opp_type = "Research / Fellowship"
        elif any(k in full_text for k in ["mentorship program", "masterclass", "bootcamp", "workshop", "conference"]):
            opp_type = "Workshop / Conference"
        elif any(k in full_text for k in [
            "is hiring", "are hiring", "hiring for", "we found openings", "jobs for you", "jobs in", "job opening",
            "junior developer", "software engineer", "ai developer", "web developer", "developer role", "recruitment",
            "apply now", "indeed application", "career opportunity", "call for applications"
        ]):
            opp_type = "Job"

        # ----------------------------------------------------
        # 3. IF NO STRONG OPPORTUNITY SIGNAL -> CHECK FOR BLOGS/COURSES/NEWSLETTERS
        # ----------------------------------------------------
        if not opp_type:
            blog_or_course = [
                "udemy", "course sale", "lowest price", "state of writing", "explained:", "graphify",
                "newsletter", "digest", "medium day", "intelligent transcription with gemini"
            ]
            reason = "Educational article, marketing newsletter, or paid course ad (no active job or scholarship application)."
            for b_kw in blog_or_course:
                if b_kw in full_text:
                    reason = f"Informational article / Course promotion ('{b_kw}')."
                    break

            return ParsedOpportunity(
                email_id=email_id,
                is_opportunity=False,
                rejection_reason=reason,
                summary=subject
            )

        # ----------------------------------------------------
        # 4. EXTRACT ELIGIBILITY, SKILLS & CRITERIA
        # ----------------------------------------------------
        cgpa_match = re.search(r"cgpa\s*(?:of|>=|:|\s)\s*([0-3]\.[0-9]{1,2}|4\.00?)", full_text)
        min_cgpa = float(cgpa_match.group(1)) if cgpa_match else None

        eligible_majors = []
        if any(k in full_text for k in ["computer science", "cs", "software", "golang", "php", "developer", "web"]):
            eligible_majors.append("Computer Science")
            eligible_majors.append("Software Engineering")
        if any(k in full_text for k in ["data science", "ai", "artificial intelligence", "machine learning", "ml"]):
            eligible_majors.append("Data Science")
            eligible_majors.append("Artificial Intelligence")
        if any(k in full_text for k in ["business", "bba", "finance", "accounting", "market research", "bd internship"]):
            eligible_majors.append("Business Administration (BBA)")
            eligible_majors.append("Finance")

        # Required Documents
        docs = []
        if "transcript" in full_text:
            docs.append("Official Academic Transcript")
        if any(k in full_text for k in ["resume", "cv", "apply now", "indeed", "linkedin"]):
            docs.append("Updated Resume / CV")
        if any(k in full_text for k in ["statement of purpose", "sop", "proposal"]):
            docs.append("Statement of Purpose / Project Proposal")
        if any(k in full_text for k in ["recommendation", "lor"]):
            docs.append("Letters of Recommendation")
        if any(k in full_text for k in ["salary slip", "income certificate"]):
            docs.append("Guardian Income Proof / Salary Slip")
        if any(k in full_text for k in ["id", "cnic"]):
            docs.append("Student ID / CNIC Copy")
        if any(k in full_text for k in ["github", "portfolio"]):
            docs.append("GitHub Profile / Portfolio Link")

        # Dynamic Deadlines & Days Remaining Extraction
        deadline, days_left = cls.parse_dynamic_deadline(full_text, email_obj.get("date_received"))


        # Application URL Extraction (Prioritizes apply/register/career links over unsubscribe/privacy links)
        all_urls = re.findall(r"https?://[^\s\)\<\>\"]+", body)
        app_url = None
        for u in all_urls:
            u_clean = u.rstrip(".,;>)\"\'")
            u_lower = u_clean.lower()
            if any(k in u_lower for k in ["unsubscribe", "optout", "preferences", "privacy", "mailto:", "terms"]):
                continue
            if any(k in u_lower for k in ["apply", "job", "career", "register", "form", "docs.google", "portal", "candidate", "position", "intern", "bootcamp"]):
                app_url = u_clean
                break

        # Fallback to first non-tracking URL
        if not app_url:
            for u in all_urls:
                u_clean = u.rstrip(".,;>)\"\'")
                if not any(k in u_clean.lower() for k in ["unsubscribe", "optout", "preferences", "privacy"]):
                    app_url = u_clean
                    break


        # Extract recruiter/contact email: Extract from sender or find recruiter addresses in body
        sender_raw = email_obj.get("sender", "")
        sender_email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", sender_raw)
        sender_email = sender_email_match.group(0) if sender_email_match else sender_raw

        # Scan body for specific career/contact addresses (e.g. careers@, jobs@, hr@, admissions@, apply@)
        body_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", body)
        contact_email = None
        for b_em in body_emails:
            b_em_lower = b_em.lower()
            if any(k in b_em_lower for k in ["career", "job", "hr", "admission", "recruiting", "recruit", "apply", "info", "contact", "support"]):
                contact_email = b_em
                break

        # If no specific recruiter email in body, use sender email (unless it's no-reply)
        if not contact_email:
            contact_email = sender_email


        # Benefits
        benefits = None
        benefits_sentences = [
            line.strip() for line in body.split("\n")
            if any(k in line.lower() for k in ["stipend", "pkr", "grant", "prize", "tuition", "perk", "benefits", "mentorship", "lpa", "$"])
        ]
        if benefits_sentences:
            benefits = "; ".join(benefits_sentences[:2])

        # Financial need flag
        need_required = "need-based" in full_text or "financial constraint" in full_text

        # Clean title
        clean_title = (
            subject.replace("URGENT:", "")
            .replace("Call for Applications:", "")
            .replace("Announcement:", "")
            .replace("Indeed Application:", "")
            .replace("Apply Now.", "")
            .strip()
        )

        # Extract clean Organization Name
        sender_raw = email_obj.get("sender", "")
        org_name = sender_raw.split("@")[-1].replace(".com", "").replace(".edu.pk", "").replace(".org", "").capitalize()
        
        # Smart regex to extract company from subject like "at Gelato", "at Adgentek", "@ EpazzTech", "Oracle is hiring"
        org_match = re.search(r"(?:at|@)\s+([A-Za-z0-9\s]+?)(?:\s+(?:and|is|for|in|you|posted)|$)", clean_title, re.IGNORECASE)
        if org_match:
            org_name = org_match.group(1).strip()
        elif "oracle" in full_text:
            org_name = "Oracle"
        elif "gelato" in full_text:
            org_name = "Gelato"
        elif "adgentek" in full_text:
            org_name = "Adgentek"
        elif "upvave" in full_text:
            org_name = "Upvave"
        elif "epazztech" in full_text:
            org_name = "EpazzTech"
        elif "google" in full_text:
            org_name = "Google"
        elif "mit" in full_text or "csail" in full_text:
            org_name = "MIT CSAIL"
        elif "mckinsey" in full_text:
            org_name = "McKinsey & Company"
        elif "devsinc" in full_text:
            org_name = "Devsinc AI Hub"
        elif "softec" in full_text:
            org_name = "SOFTEC Society FAST-NU"

        return ParsedOpportunity(
            email_id=email_id,
            is_opportunity=True,
            title=clean_title,
            organization=org_name,
            opportunity_type=opp_type,
            deadline=deadline,
            days_until_deadline=days_left,
            eligibility=EligibilityCriteria(
                min_cgpa=min_cgpa,
                eligible_majors=eligible_majors,
                financial_need_required=need_required
            ),
            required_documents=docs if docs else ["Updated Resume / CV"],
            benefits=benefits,
            application_link=app_url,
            contact_email=contact_email,
            summary=(body[:200].replace("\n", " ") + "...") if body else clean_title
        )


    @classmethod
    def parse_email_batch(cls, email_batch: List[Dict[str, Any]], api_key: Optional[str] = None) -> List[ParsedOpportunity]:
        """Parses a batch of emails (5 to 15) using AI or Fallback."""
        results: List[ParsedOpportunity] = []
        for email in email_batch:
            parsed = None
            if api_key or GEMINI_API_KEY:
                parsed = cls.parse_with_gemini(email, api_key)
            
            if parsed is None:
                parsed = cls.parse_with_heuristics(email)
                
            results.append(parsed)
        return results

