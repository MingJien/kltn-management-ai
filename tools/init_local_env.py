"""Tạo .env development một lần mà không in mật khẩu ra stdout."""

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / ".env"


def main() -> None:
    if TARGET.exists():
        print("local_env_exists_no_overwrite")
        return
    password = token_urlsafe(32)
    encoded = quote_plus(password)
    content = (
        "POSTGRES_DB=kltn_management\n"
        "POSTGRES_USER=kltn_app\n"
        f"POSTGRES_PASSWORD={password}\n"
        "POSTGRES_PORT=5432\n"
        f"DATABASE_URL=postgresql+psycopg://kltn_app:{encoded}@127.0.0.1:5432/kltn_management\n"
    )
    TARGET.write_text(content, encoding="utf-8")
    print("local_env_created_secret_not_displayed")


if __name__ == "__main__":
    main()
