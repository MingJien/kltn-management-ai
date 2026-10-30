"""Send one harmless test message to the configured sender, without printing secrets."""

from __future__ import annotations

import argparse
import os

from backend.db.validate_schema import load_env
from backend.services.account_mail import mail_delivery_ready, send_account_link


def main() -> None:
    parser = argparse.ArgumentParser(description="Check KLTN SMTP delivery to your own inbox")
    parser.add_argument("--send-test", action="store_true", help="Send one test email")
    args = parser.parse_args()
    load_env()
    sender = os.getenv("KLTN_MAIL_FROM", "").strip()
    if not args.send_test:
        print("Pass --send-test to send one message to the configured sender")
        return
    if not all(os.getenv(key, "").strip() for key in (
            "KLTN_MAIL_FROM", "KLTN_SMTP_HOST", "KLTN_SMTP_USER", "KLTN_SMTP_PASSWORD")) \
            or not mail_delivery_ready():
        parser.error("Complete the SMTP settings, including KLTN_SMTP_PASSWORD, first")
    try:
        send_account_link(sender, "Kiểm tra gửi thư KLTN local",
                          "Đây là thư thử cấu hình SMTP KLTN local. Không cần trả lời.\n")
    except Exception as exc:
        parser.exit(1, f"SMTP test failed: {type(exc).__name__}. Check Gmail App Password and network.\n")
    print(f"SMTP accepted the test message for {sender}; check Inbox and Spam")


if __name__ == "__main__":
    main()
