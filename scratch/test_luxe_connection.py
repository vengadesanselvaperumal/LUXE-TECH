#!/usr/bin/env python3
"""
LUXE.TECH — Temporary Local PostgreSQL Connection Probe
Location: scratch/test_luxe_connection.py

Requirements:
- Supports password provided through 'LUXE_DB_PASSWORD' environment variable for a one-time test.
- Keeps hidden interactive prompt as default if LUXE_DB_PASSWORD is not set.
- Does not strip or modify the password (preserves exact character sequence).
- Adds safe diagnostics reporting password detection and exact character count (never contents).
- Accurately builds connection parameters and URL with RFC 3986 percent-encoding (quote with safe='').
- Connects using dedicated LUXE.TECH Supabase host (aws-0-ap-northeast-1.pooler.supabase.com),
  port 6543, database postgres, username luxe_app_user.nmmtbbmksyyfjgtkczot, and SSL require.
- Executes strictly 'SELECT 1'.
- Purges LUXE_DB_PASSWORD from environment memory upon ingestion and in finally block.
- Sanitizes error messages (redacts passwords and credentials).
- Zero cloud resource modifications, zero migrations, zero .env changes.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse
from dotenv import dotenv_values


def sanitize_message(message: str, secrets_to_redact: list) -> str:
    """Sanitize error messages to eliminate credentials, URLs with passwords, or secret tokens."""
    sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", message)
    sanitized = re.sub(r"password=[^\s;&]+", "password=***", sanitized, flags=re.IGNORECASE)
    for s in secrets_to_redact:
        if s and len(s) >= 2:
            sanitized = sanitized.replace(s, "***")
    return sanitized


def clear_env_password():
    """Ensure LUXE_DB_PASSWORD is wiped from environment memory."""
    os.environ.pop("LUXE_DB_PASSWORD", None)
    if hasattr(os, "unsetenv"):
        os.unsetenv("LUXE_DB_PASSWORD")


def find_env_file() -> Path:
    """Locate the project .env file reliably regardless of invocation directory."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / ".env",          # project root from scratch/
        Path.cwd() / ".env",                 # current working directory
        Path.cwd().parent / ".env",          # parent of working directory
    ]
    for path in candidates:
        if path.exists():
            return path
    print("FAIL: '.env' configuration file not found.")
    sys.exit(1)


def get_clipboard_text() -> str:
    """Read plain text from Windows clipboard via user32 APIs without third-party dependencies."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        CF_UNICODETEXT = 13
        if not user32.OpenClipboard(0):
            return ""
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            kernel32.GlobalLock.restype = ctypes.c_void_p
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def get_windows_secure_input(prompt: str) -> str:
    """
    Secure hidden password entry tailored for Windows PowerShell and VS Code terminal.
    - Suppresses console echo.
    - Intercepts Ctrl+V (ASCII 22) and pastes directly from Windows clipboard.
    - Supports normal character entry, backspace, and enter.
    - Supports piped standard input from PowerShell in-memory streams.
    """
    if not sys.stdin.isatty():
        try:
            line = sys.stdin.readline()
            return line.rstrip("\r\n")
        except Exception:
            return ""

    try:
        import msvcrt
    except ImportError:
        import getpass
        return getpass.getpass(prompt).rstrip("\r\n")

    sys.stderr.write(prompt)
    sys.stderr.flush()

    pw_chars = []
    while True:
        try:
            ch = msvcrt.getwch()
        except KeyboardInterrupt:
            sys.stderr.write("\n")
            print("FAIL: Password entry cancelled by user.")
            sys.exit(1)

        if ch in ("\r", "\n"):
            sys.stderr.write("\n")
            break

        if ch == "\x03":
            sys.stderr.write("\n")
            print("FAIL: Password entry cancelled by user.")
            sys.exit(1)

        elif ch in ("\b", "\x7f"):
            if pw_chars:
                pw_chars.pop()

        elif ch == "\x16":
            clip_text = get_clipboard_text()
            if clip_text:
                clip_text = clip_text.replace("\r", "").replace("\n", "")
                pw_chars.extend(list(clip_text))

        elif ch in ("\x00", "\xe0"):
            try:
                msvcrt.getwch()
            except Exception:
                pass

        else:
            pw_chars.append(ch)

    return "".join(pw_chars).rstrip("\r\n")


def run_probe():
    password = ""
    encoded_pass = ""
    secrets_to_redact = []

    try:
        # 1. Locate .env and resolve dedicated pooler settings without exposing secrets
        env_file = find_env_file()
        env_values = dotenv_values(env_file)
        raw_db_url = env_values.get("DATABASE_URL", "")
        supabase_url = env_values.get("SUPABASE_URL", "")

        # 2. Extract dedicated LUXE.TECH pooler host and project reference
        parsed_db = urlparse(raw_db_url) if raw_db_url else None
        pooler_host = (
            parsed_db.hostname
            if (parsed_db and parsed_db.hostname)
            else "aws-0-ap-northeast-1.pooler.supabase.com"
        )
        port = 6543
        dbname = "postgres"

        project_ref = "nmmtbbmksyyfjgtkczot"
        if supabase_url:
            parsed_sub = urlparse(supabase_url)
            if parsed_sub.hostname and ".supabase.co" in parsed_sub.hostname:
                project_ref = parsed_sub.hostname.split(".")[0]

        username = f"luxe_app_user.{project_ref}"

        # 3. Read password: check LUXE_DB_PASSWORD environment variable first
        #    Preserve exact character sequence (only rstrip trailing \r\n, do NOT strip whitespace).
        raw_env_password = os.environ.get("LUXE_DB_PASSWORD")
        clear_env_password()

        password_source = ""
        if raw_env_password is not None and len(raw_env_password) > 0:
            password = raw_env_password.rstrip("\r\n")
            password_source = "LUXE_DB_PASSWORD (environment variable)"
        else:
            password = get_windows_secure_input(f"Enter password for '{username}': ")
            password_source = "Hidden interactive prompt"

        if not password:
            print("FAIL: Password cannot be empty.")
            sys.exit(1)

        # 4. Safe Diagnostics (Reports ONLY non-sensitive metadata and password length)
        print("------------------------------------------------------------")
        print("LUXE.TECH POSTGRESQL PROBE DIAGNOSTICS")
        print("------------------------------------------------------------")
        print(f"Password source:       {password_source}")
        print(f"Password detected:     True")
        print(f"Password length:       {len(password)} characters")
        print(f"Target pooler host:    {pooler_host}")
        print(f"Target port:           {port} (transaction pooler)")
        print(f"Target database:       {dbname}")
        print(f"Target username:       {username}")
        print(f"SSL mode:              require")
        print("------------------------------------------------------------")

        # 5. Build in-memory URI with RFC 3986 percent-encoding (quote with safe='')
        # Note: quote with safe='' correctly encodes spaces as %20 and pluses as %2B.
        encoded_user = quote(username, safe="")
        encoded_pass = quote(password, safe="")
        conn_uri = f"postgresql://{encoded_user}:{encoded_pass}@{pooler_host}:{port}/{dbname}?sslmode=require"

        # 6. Connect via installed PostgreSQL driver (psycopg 3) and execute SELECT 1
        try:
            import psycopg
        except ImportError:
            print("FAIL: Installed PostgreSQL driver 'psycopg' could not be loaded.")
            sys.exit(1)

        secrets_to_redact = [password, encoded_pass]
        if raw_env_password:
            secrets_to_redact.append(raw_env_password)

        # Connect directly with native parameters (bypasses any potential URI parsing edge cases)
        conn_params = {
            "host": pooler_host,
            "port": port,
            "user": username,
            "password": password,
            "dbname": dbname,
            "sslmode": "require",
            "connect_timeout": 10,
        }

        try:
            with psycopg.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    row = cur.fetchone()
                    if row and row[0] == 1:
                        print("PASS: Successfully connected to dedicated LUXE.TECH database as 'luxe_app_user' and executed SELECT 1.")
                        sys.exit(0)
                    else:
                        print("FAIL: Probe query executed but returned unexpected result.")
                        sys.exit(1)
        except Exception as exc:
            sanitized_err = sanitize_message(str(exc), secrets_to_redact)
            print(f"FAIL: Connection probe failed: {sanitized_err}")
            if "password authentication failed" in sanitized_err:
                print("\nDIAGNOSTIC CHECKS FOR 'password authentication failed':")
                print(f"  * Reported password length is {len(password)} characters. Verify this matches the exact secret created in Supabase.")
                print("  * If the password was enclosed in quotes in SQL (e.g. PASSWORD '...'), ensure those literal single quotes were not copied into the password value.")
                print("  * If the role was just created or altered, verify the transaction was committed in the Supabase SQL Editor.")
                print("  * Supabase Pooler userlist sync: The pooler on port 6543 authenticates via Supavisor. In some instances, pooler cache synchronization can take up to 30-60 seconds after role creation.")
            sys.exit(1)

    finally:
        clear_env_password()


if __name__ == "__main__":
    run_probe()
