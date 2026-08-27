import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional, Tuple

from models import StudentProfile, ParsedOpportunity


class ApplicationService:
    """
    Automates cover letter generation and 1-click email dispatch via Gmail SMTP with optional attachments.
    """

    @classmethod
    def generate_application_draft(
        cls, profile: StudentProfile, opp: ParsedOpportunity
    ) -> Dict[str, str]:
        """
        Generates a tailored, professional application email draft based on student profile and opportunity.
        """
        skills_str = ", ".join(profile.skills[:4]) if profile.skills else "software engineering and problem solving"
        cgpa_line = f" with a current CGPA of {profile.cgpa:.2f}" if (profile.cgpa and profile.cgpa > 0) else ""
        
        subject = f"Application for {opp.title} - {profile.name} ({profile.degree})"

        salutation = f"Dear Hiring Team at {opp.organization}," if opp.organization else "Dear Hiring Manager,"

        body = (
            f"{salutation}\n\n"
            f"I hope this email finds you well. I am writing to express my strong interest in the {opp.title} "
            f"opportunity at {opp.organization or 'your organization'}.\n\n"
            f"I am currently an undergraduate student pursuing my {profile.degree} (Semester {profile.semester}){cgpa_line}. "
            f"With practical experience and technical proficiency in {skills_str}, I am confident in my ability "
            f"to contribute meaningfully to your team.\n\n"
            f"Key highlights of my background include:\n"
            f"- Technical & Domain Strengths: {skills_str}\n"
            f"- Academic & Project Work: Demonstrated problem-solving and rapid learning agility in core coursework.\n\n"
            f"Please find my resume attached for your review. I have reviewed the requirements and believe my background "
            f"aligns closely with what you are seeking. I would welcome the opportunity to discuss how my skillset can support your upcoming initiatives.\n\n"
            f"Thank you for your time and consideration. I look forward to hearing from you.\n\n"
            f"Sincerely,\n"
            f"{profile.name}\n"
            f"{profile.degree} Undergraduate\n"
        )

        return {
            "subject": subject,
            "body": body,
            "recipient": opp.contact_email if (opp.contact_email and "no-reply" not in opp.contact_email.lower()) else "",
        }

    @classmethod
    def send_email_smtp(
        cls,
        smtp_host: str,
        sender_email: str,
        app_password: str,
        recipient_email: str,
        subject: str,
        body: str,
        port: int = 465,
        attachment_bytes: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Connects over SMTP SSL to dispatch the email directly from the student's authenticated mailbox,
        optionally attaching the student's uploaded resume PDF.
        """
        if not recipient_email or "@" not in recipient_email:
            return False, "Please enter a valid recipient email address."
        if sender_email.strip().lower() == recipient_email.strip().lower():
            return False, "Recipient cannot be your own email address. Please enter the recruiter/company email address."

        cleaned_password = app_password.replace(" ", "").strip()

        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email.strip()
            msg["To"] = recipient_email.strip()
            msg["Subject"] = subject.strip()

            # Attach text body
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Attach PDF resume if provided
            if attachment_bytes:
                clean_filename = attachment_filename or "Resume.pdf"
                part = MIMEApplication(attachment_bytes, _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename=clean_filename)
                msg.attach(part)

            with smtplib.SMTP_SSL(smtp_host, port) as server:
                server.login(sender_email.strip(), cleaned_password)
                server.send_message(msg)

            attach_msg = f" (with '{attachment_filename or 'Resume.pdf'}' attached)" if attachment_bytes else ""
            return True, f"Application email successfully sent to {recipient_email}{attach_msg}!"

        except smtplib.SMTPAuthenticationError:
            return False, "SMTP Authentication failed. Please verify your 16-letter Google App Password."
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"

