"""Run the local ClamAV CLI before a stored upload can be read or approved."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException


def executable() -> str | None:
    configured = os.getenv("KLTN_CLAMSCAN_PATH", "").strip()
    if configured:
        path = Path(configured)
        return str(path) if path.is_file() else None
    installed = Path(r"C:\Program Files\ClamAV\clamscan.exe")
    if os.name == "nt" and installed.is_file():
        return str(installed)
    return shutil.which("clamscan.exe" if os.name == "nt" else "clamscan")


def clamdscan_executable() -> str | None:
    configured = os.getenv("KLTN_CLAMDSCAN_PATH", "").strip()
    if configured:
        path = Path(configured)
        return str(path) if path.is_file() else None
    installed = Path(r"C:\Program Files\ClamAV\clamdscan.exe")
    if os.name == "nt" and installed.is_file():
        return str(installed)
    return shutil.which("clamdscan.exe" if os.name == "nt" else "clamdscan")


def database_dir() -> Path | None:
    configured = os.getenv("KLTN_CLAMAV_DATABASE_DIR", "").strip()
    if configured:
        return Path(configured)
    if os.name == "nt":
        return Path(r"C:\ProgramData\ClamAV\database")
    return None


def clamd_conf() -> Path | None:
    configured = os.getenv("KLTN_CLAMD_CONF", "").strip()
    if configured:
        return Path(configured)
    if os.name == "nt":
        conf = Path(r"C:\ProgramData\ClamAV\clamd.conf")
        if conf.is_file():
            return conf
    return None


def daemon_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 3310), timeout=1) as connection:
            connection.sendall(b"zPING\0")
            return connection.recv(64).rstrip(b"\0\r\n") == b"PONG"
    except OSError:
        return False


def start_local_daemon(timeout: float = 90) -> bool:
    """Reuse/start the installed Windows scanner on loopback, without changing system services."""
    if daemon_ready():
        return True
    daemon = Path(r"C:\Program Files\ClamAV\clamd.exe")
    conf = clamd_conf()
    if os.name != "nt" or not daemon.is_file() or not conf:
        return False
    # Only start the known local configuration; never expose a scanner on the LAN.
    settings = conf.read_text(encoding="utf-8").splitlines()
    if "TCPAddr 127.0.0.1" not in settings or "TCPSocket 3310" not in settings:
        return False
    log_dir = Path(__file__).resolve().parents[2] / "local" / "clamav"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "daemon.log").open("ab") as output:
        process = subprocess.Popen([str(daemon), f"--config-file={conf}", "--foreground", "--fail-if-cvd-older-than=14"],
            stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    until = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < until:
        if daemon_ready():
            return True
        time.sleep(.25)
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)
    return False


def scan(file, path: Path) -> str:
    """Return the persisted verdict; absent/broken scanner never means CLEAN."""
    binary = executable()
    daemon_client = clamdscan_executable()
    conf = clamd_conf()

    if not binary and not daemon_client:
        return file.scan_state  # Keep uploads quarantined until a real scanner exists.
    try:
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        if before != file.sha256 or path.is_symlink():
            file.scan_state = "FAILED"
            return file.scan_state

        result = None
        # Try clamdscan first if clamd daemon is configured
        if daemon_client and conf:
            try:
                res = subprocess.run(
                    [daemon_client, f"--config-file={conf}", "--stdout", "--no-summary", str(path)],
                    capture_output=True, text=True, timeout=10, check=False, shell=False,
                )
                if res.returncode in (0, 1):
                    result = res
            except (OSError, subprocess.TimeoutExpired):
                result = None

        if result is None:
            if not binary:
                file.scan_state = "FAILED"
                file.scanned_at = datetime.now(timezone.utc)
                return file.scan_state
            db = database_dir()
            arguments = [binary, "--stdout", "--no-summary", "--fail-if-cvd-older-than=14"]
            if db:
                arguments.append(f"--database={db}")
            result = subprocess.run(
                [*arguments, str(path)],
                capture_output=True, text=True, timeout=90, check=False, shell=False,
            )

        after = hashlib.sha256(path.read_bytes()).hexdigest()
        if after != before:
            file.scan_state = "FAILED"
        elif result.returncode == 0 and ": OK" in result.stdout:
            file.scan_state = "CLEAN"
        elif result.returncode == 1 and "FOUND" in result.stdout:
            file.scan_state = "INFECTED"
        else:
            file.scan_state = "FAILED"
    except (OSError, subprocess.TimeoutExpired):
        file.scan_state = "FAILED"
    file.scanned_at = datetime.now(timezone.utc)
    return file.scan_state


def require_available() -> None:
    if not executable() and not clamdscan_executable():
        raise HTTPException(503, "ClamAV chưa được cài hoặc chưa được cấu hình trên máy chủ")
