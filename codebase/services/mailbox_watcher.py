import time
import threading
from typing import Dict, Any, List, Optional, Set
from services.imap_sync_service import ImapSyncService
from services.email_parser import EmailParserService
from models.opportunity import ParsedOpportunity


class MailboxWatcherService:
    """
    Background Real-Time Mailbox Watcher & Auto-Ranking Daemon.
    Monitors an active IMAP mailbox in the background, detects new incoming messages,
    automatically extracts & parses opportunities, and queues real-time notifications.
    """

    _watcher_thread: Optional[threading.Thread] = None
    _stop_event = threading.Event()
    _lock = threading.Lock()

    # Tracked seen message IDs
    _seen_ids: Set[str] = set()

    # Newly arrived unconsumed opportunities & notification events
    _pending_opportunities: List[ParsedOpportunity] = []
    _pending_raw_emails: List[Dict[str, Any]] = []
    _notifications: List[Dict[str, Any]] = []

    _is_active: bool = False
    _last_check_time: float = 0.0
    _last_error: Optional[str] = None
    _poll_count: int = 0

    @classmethod
    def register_existing_ids(cls, email_ids: List[str]):
        """Registers already loaded email IDs so they don't trigger duplicate alerts."""
        with cls._lock:
            for eid in email_ids:
                cls._seen_ids.add(str(eid))

    @classmethod
    def is_running(cls) -> bool:
        return cls._is_active and cls._watcher_thread is not None and cls._watcher_thread.is_alive()

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        with cls._lock:
            return {
                "active": cls.is_running(),
                "seen_count": len(cls._seen_ids),
                "pending_opportunities": len(cls._pending_opportunities),
                "last_check_time": cls._last_check_time,
                "last_error": cls._last_error,
                "poll_count": cls._poll_count,
            }

    @classmethod
    def start_watcher(
        cls,
        imap_host: str,
        email_address: str,
        app_password: str,
        interval_seconds: int = 15,
        api_key: Optional[str] = None,
    ):
        """Starts the background mailbox listener daemon if not already running."""
        with cls._lock:
            if cls.is_running():
                return

            cls._stop_event.clear()
            cls._is_active = True
            cls._last_error = None

            cls._watcher_thread = threading.Thread(
                target=cls._worker_loop,
                args=(imap_host, email_address, app_password, interval_seconds, api_key),
                daemon=True,
                name="MailboxWatcherThread",
            )
            cls._watcher_thread.start()

    @classmethod
    def stop_watcher(cls):
        """Signals the background watcher daemon to stop."""
        cls._stop_event.set()
        with cls._lock:
            cls._is_active = False

    @classmethod
    def drain_pending_items(cls) -> Dict[str, Any]:
        """
        Drains all newly parsed opportunities, raw emails, and notifications
        and returns them to the UI thread.
        """
        with cls._lock:
            opps = list(cls._pending_opportunities)
            emails = list(cls._pending_raw_emails)
            notifs = list(cls._notifications)

            cls._pending_opportunities.clear()
            cls._pending_raw_emails.clear()
            cls._notifications.clear()

            return {
                "opportunities": opps,
                "raw_emails": emails,
                "notifications": notifs,
            }

    @classmethod
    def _worker_loop(
        cls,
        imap_host: str,
        email_address: str,
        app_password: str,
        interval_seconds: int,
        api_key: Optional[str],
    ):
        while not cls._stop_event.is_set():
            try:
                # Fetch recent unread or latest emails
                success, live_emails, msg = ImapSyncService.fetch_live_emails(
                    imap_host=imap_host,
                    email_address=email_address,
                    app_password=app_password,
                    limit=10,
                    unread_only=False,
                )

                with cls._lock:
                    cls._last_check_time = time.time()
                    cls._poll_count += 1

                if success and live_emails:
                    new_emails = []
                    with cls._lock:
                        for em in live_emails:
                            em_id = str(em.get("id"))
                            if em_id not in cls._seen_ids:
                                cls._seen_ids.add(em_id)
                                new_emails.append(em)

                    if new_emails:
                        # Parse newly detected emails
                        new_parsed = EmailParserService.parse_email_batch(new_emails, api_key=api_key)

                        with cls._lock:
                            cls._pending_raw_emails.extend(new_emails)
                            cls._pending_opportunities.extend(new_parsed)

                            for opp in new_parsed:
                                if opp.is_opportunity:
                                    cls._notifications.append({
                                        "title": f"🎉 New Opportunity: {opp.title}",
                                        "body": f"From {opp.organization} ({opp.opportunity_type}) • Deadline: {opp.deadline or 'Ongoing'}",
                                        "type": "opportunity",
                                        "timestamp": time.time(),
                                    })
                                else:
                                    cls._notifications.append({
                                        "title": f"🗑️ Filtered: {opp.title}",
                                        "body": f"{opp.rejection_reason}",
                                        "type": "filtered",
                                        "timestamp": time.time(),
                                    })

            except Exception as e:
                with cls._lock:
                    cls._last_error = str(e)

            # Wait for next poll interval or stop event
            cls._stop_event.wait(interval_seconds)
