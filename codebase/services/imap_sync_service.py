import imaplib
import email
from email.header import decode_header
import re
import html
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class ImapSyncService:
    """
    Live IMAP Connector for personal Gmail, Outlook, and University Webmail.
    Connects securely over SSL to fetch and clean recent/unread emails.
    """

    PRESET_SERVERS = {
        "Gmail": {"host": "imap.gmail.com", "port": 993},
        "Outlook / Office 365": {"host": "outlook.office365.com", "port": 993},
        "Yahoo Mail": {"host": "imap.mail.yahoo.com", "port": 993},
        "Custom / University Webmail": {"host": "", "port": 993},
    }

    @classmethod
    def clean_html_body(cls, html_content: str) -> str:
        """Converts raw HTML email markup into clean, readable text."""
        # Replace breaks and paragraphs with newlines
        text = re.sub(r'<(?:br|p|div|tr)[\s/]*>', '\n', html_content, flags=re.IGNORECASE)
        # Strip script and style blocks
        text = re.sub(r'<(?:script|style)[^>]*>[\s\S]*?</(?:script|style)>', '', text, flags=re.IGNORECASE)
        # Strip remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Unescape HTML entities (&nbsp;, &amp;, etc.)
        text = html.unescape(text)
        # Collapse excessive whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    @classmethod
    def decode_mime_header(cls, header_value: Optional[Any]) -> str:
        """Decodes MIME encoded headers like UTF-8 subjects or sender names safely."""
        if not header_value:
            return ""
        try:
            str_val = str(header_value)
            decoded_fragments = decode_header(str_val)
            text_parts = []
            for fragment, encoding in decoded_fragments:
                if isinstance(fragment, bytes):
                    try:
                        text_parts.append(fragment.decode(encoding or "utf-8", errors="replace"))
                    except Exception:
                        text_parts.append(fragment.decode("utf-8", errors="replace"))
                else:
                    text_parts.append(str(fragment))
            return "".join(text_parts)
        except Exception:
            # Safe fallback if decode_header encounters unencoded emojis/unicode
            return str(header_value)


    @classmethod
    def extract_email_payload(cls, msg: email.message.Message) -> str:
        """Recursively extracts plain text or cleaned HTML body from an email Message object."""
        plain_texts = []
        html_texts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            charset = part.get_content_charset() or "utf-8"
                            text = body_bytes.decode(charset, errors="replace").strip()
                            if text:
                                plain_texts.append(text)
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        body_bytes = part.get_payload(decode=True)
                        if body_bytes:
                            charset = part.get_content_charset() or "utf-8"
                            raw_html = body_bytes.decode(charset, errors="replace")
                            cleaned = cls.clean_html_body(raw_html)
                            if cleaned:
                                html_texts.append(cleaned)
                    except Exception:
                        pass
        else:
            try:
                body_bytes = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                raw_content = body_bytes.decode(charset, errors="replace") if body_bytes else str(msg.get_payload())
                if msg.get_content_type() == "text/html":
                    return cls.clean_html_body(raw_content)
                else:
                    return raw_content.strip()
            except Exception:
                return str(msg.get_payload()).strip()

        combined_plain = "\n\n".join(plain_texts).strip()
        combined_html = "\n\n".join(html_texts).strip()

        # If plain text is a placeholder or stub (<50 chars), but HTML has real content, prefer HTML!
        if combined_plain and len(combined_plain) > 50 and "this is the body" not in combined_plain.lower():
            return combined_plain
        elif combined_html:
            return combined_html

        return combined_plain or combined_html or "No email body content found."


    @classmethod
    def fetch_live_emails(
        cls,
        imap_host: str,
        email_address: str,
        app_password: str,
        port: int = 993,
        limit: int = 10,
        unread_only: bool = False,
    ) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Connects over IMAP SSL, authenticates, and retrieves emails.
        Returns (success: bool, emails: List[Dict], message: str)
        """
        if not imap_host or not email_address or not app_password:
            return False, [], "Missing IMAP host, email address, or App Password."

        cleaned_password = app_password.replace(" ", "").strip()
        mail = None

        try:
            # 1. Connect over SSL
            mail = imaplib.IMAP4_SSL(imap_host, port)
            mail.login(email_address.strip(), cleaned_password)

            # 2. Select Inbox
            status, _ = mail.select("INBOX", readonly=True)
            if status != "OK":
                return False, [], "Failed to open INBOX folder on mail server."

            # 3. Search criteria
            search_criterion = "UNSEEN" if unread_only else "ALL"
            status, search_data = mail.search(None, search_criterion)
            if status != "OK" or not search_data or not search_data[0]:
                return True, [], f"Connected to {email_address} successfully! No {'unread ' if unread_only else ''}emails found."

            msg_ids = search_data[0].split()
            # Fetch the most recent N messages (last IDs in the list)
            target_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids
            target_ids = list(reversed(target_ids))  # Most recent first

            fetched_emails = []
            for m_id in target_ids:
                try:
                    status, msg_data = mail.fetch(m_id, "(RFC822)")
                    if status != "OK" or not msg_data:
                        continue

                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            raw_msg = email.message_from_bytes(response_part[1])
                            subject = cls.decode_mime_header(raw_msg.get("Subject", "(No Subject)"))
                            sender = cls.decode_mime_header(raw_msg.get("From", "Unknown Sender"))
                            date_raw = raw_msg.get("Date", "")
                            body = cls.extract_email_payload(raw_msg)

                            # Format date
                            date_str = "2026-03-01"
                            if date_raw:
                                try:
                                    parsed_date = email.utils.parsedate_to_datetime(date_raw)
                                    date_str = parsed_date.strftime("%Y-%m-%d")
                                    if parsed_date.year < 2020 or parsed_date.year > 2030:
                                        date_str = "2026-03-01"
                                except Exception:
                                    pass

                            clean_id = f"live_{m_id.decode('utf-8', errors='ignore') if isinstance(m_id, bytes) else str(m_id)}"
                            fetched_emails.append({
                                "id": clean_id,
                                "subject": str(subject),
                                "sender": str(sender),
                                "date_received": str(date_str),
                                "body": str(body),
                            })
                except Exception as msg_err:
                    print(f"[ImapSyncService] Skipping problematic message {m_id}: {msg_err}")
                    continue

            return True, fetched_emails, f"Successfully fetched {len(fetched_emails)} live emails from {email_address}!"


        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg.upper() or "INVALID CREDENTIALS" in error_msg.upper():
                return False, [], "Authentication failed. Please verify your Google App Password (16 letters, not regular password)."
            return False, [], f"IMAP Protocol Error: {error_msg}"
        except Exception as e:
            return False, [], f"Connection error: {str(e)}"
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass
