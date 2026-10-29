"""User accounts, sign-in identities and private history (SQLite).

Tables: users, identities (Google sign-in), history (speech-to-text), tts_history (text-to-speech),
conversations + messages (older conversations, read and delete only). Every private table is scoped by user_id.
Upgrading from an older database is automatic: init_db() makes a backup copy first.

- Passwords are hashed with scrypt (Python standard library) using a unique random salt
  per user. Plaintext passwords are never stored or logged.
- Every history query is filtered by the logged-in user's id, which always comes from the
  server-side session, never from anything a user can type or click.
- The database is a single file (voice_studio.db by default). Keep it out of git and out
  of any shared folder. Set VOICE_STUDIO_DB in .env to store it elsewhere.
"""

import base64
import hashlib
import hmac
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("VOICE_STUDIO_DB") or Path(__file__).with_name("voice_studio.db"))

# scrypt cost: N=2^16, r=8, p=2 is within OWASP's recommended minimums (~64 MB, a fraction of a second).
_N, _R, _P = 2**16, 8, 2
_MAXMEM = 256 * 1024 * 1024

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_COMMON_PASSWORDS = {"password", "password1", "12345678", "123456789", "qwerty123", "iloveyou1", "admin123"}


# ----------------------------------------------------------------------------- database
@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


SCHEMA_VERSION = 2
UNUSABLE_PASSWORD = "!"          # stored for accounts that only sign in with Google
MAX_STORED_AUDIO_BYTES = 3 * 1024 * 1024
MAX_STORED_AUDIO_ITEMS = 20


def init_db():
    """Create or upgrade the database. Safe to call on every start.

    If an older database exists, a backup copy is saved next to it before any change.
    """
    existing = DB_PATH.exists()
    if existing:
        probe = sqlite3.connect(DB_PATH)
        try:
            old_version = probe.execute("PRAGMA user_version").fetchone()[0]
            has_users = probe.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone() is not None
            if has_users and old_version < SCHEMA_VERSION:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup = DB_PATH.with_name(f"{DB_PATH.stem}.backup-v{old_version}-{stamp}.db")
                dst = sqlite3.connect(backup)
                try:
                    probe.backup(dst)
                finally:
                    dst.close()
        finally:
            probe.close()

    with _conn() as con:
        con.execute("PRAGMA journal_mode = WAL")
        # --- version 1: the original tables (unchanged) ---
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT NOT NULL UNIQUE,
                display_name    TEXT NOT NULL,
                password_hash   TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until    TEXT,
                default_language TEXT NOT NULL DEFAULT 'telugu',
                save_history    INTEGER NOT NULL DEFAULT 1,
                apply_itn       INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at    TEXT NOT NULL,
                source        TEXT NOT NULL,
                language_name TEXT NOT NULL,
                language_code TEXT NOT NULL,
                filename      TEXT,
                transcript    TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, created_at DESC);
            """
        )
        # --- version 2: Google sign-in, text-to-speech history, voice-agent conversations ---
        version = con.execute("PRAGMA user_version").fetchone()[0]
        if version < 2:
            cols = {r["name"] for r in con.execute("PRAGMA table_info(users)")}
            if "auth_version" not in cols:
                con.execute("ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0")
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS identities (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider   TEXT NOT NULL,
                    subject    TEXT NOT NULL,
                    email      TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (provider, subject)
                );
                CREATE TABLE IF NOT EXISTS tts_history (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at    TEXT NOT NULL,
                    text          TEXT NOT NULL,
                    language_name TEXT NOT NULL,
                    language_code TEXT NOT NULL,
                    voice         TEXT NOT NULL,
                    model         TEXT NOT NULL,
                    container     TEXT NOT NULL,
                    speed         REAL NOT NULL DEFAULT 1.0,
                    audio         BLOB
                );
                CREATE INDEX IF NOT EXISTS idx_tts_user ON tts_history(user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS conversations (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title         TEXT NOT NULL,
                    language_name TEXT NOT NULL,
                    language_code TEXT NOT NULL,
                    created_at    TEXT NOT NULL,
                    updated_at    TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS messages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content         TEXT NOT NULL,
                    created_at      TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, id);
                """
            )
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


# ----------------------------------------------------------------------------- passwords
def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, maxmem=_MAXMEM, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(salt),
            n=int(n), r=int(r), p=int(p), maxmem=_MAXMEM, dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


_DUMMY_HASH = None


def _dummy_verify(password: str):
    """Spend the same time as a real check so response time does not reveal whether an email exists."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-real-password")
    verify_password(password, _DUMMY_HASH)


# ----------------------------------------------------------------------------- validation
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str):
    if not email:
        return "Enter your email address."
    if len(email) > 254 or not _EMAIL_RE.match(email):
        return "Enter a valid email address, like name@example.com."
    return None


def normalize_name(name: str) -> str:
    return " ".join((name or "").split())


def validate_name(name: str):
    if len(name) < 2:
        return "Enter a display name with at least 2 characters."
    if len(name) > 60:
        return "Keep the display name to 60 characters or fewer."
    if any(ord(c) < 32 for c in name):
        return "The display name contains characters that are not allowed."
    return None


def validate_password(password: str, email: str = ""):
    if len(password) < 8:
        return "Use at least 8 characters for your password."
    if len(password) > 128:
        return "Keep your password to 128 characters or fewer."
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        return "Include at least one letter and one number in your password."
    if password.lower() in _COMMON_PASSWORDS or (email and password.lower() == email.lower()):
        return "That password is too easy to guess. Choose a different one."
    return None


# ----------------------------------------------------------------------------- users
def _public(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "created_at": row["created_at"],
        "default_language": row["default_language"],
        "save_history": bool(row["save_history"]),
        "apply_itn": bool(row["apply_itn"]),
        "auth_version": row["auth_version"],
        "has_password": row["password_hash"] != UNUSABLE_PASSWORD,
    }


def create_user(email: str, display_name: str, password: str):
    """Return (user, None) on success or (None, error message)."""
    email, display_name = normalize_email(email), normalize_name(display_name)
    error = validate_name(display_name) or validate_email(email) or validate_password(password, email)
    if error:
        return None, error
    try:
        with _conn() as con:
            cur = con.execute(
                "INSERT INTO users (email, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (email, display_name, hash_password(password), _iso(_now())),
            )
            row = con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _public(row), None
    except sqlite3.IntegrityError:
        return None, "An account with this email already exists. Try logging in instead."


def authenticate(email: str, password: str):
    """Return (user, None) or (None, error message). Locks the account after repeated failures."""
    email = normalize_email(email)
    if not email or not password:
        return None, "Enter your email and password."
    generic = "Incorrect email or password."
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            _dummy_verify(password)
            return None, generic
        if row["locked_until"]:
            until = datetime.fromisoformat(row["locked_until"])
            if until > _now():
                minutes = max(1, int((until - _now()).total_seconds() // 60) + 1)
                return None, f"Too many failed attempts. Try again in about {minutes} minute(s)."
        if not verify_password(password, row["password_hash"]):
            attempts = row["failed_attempts"] + 1
            if attempts >= MAX_FAILED_LOGINS:
                con.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = ? WHERE id = ?",
                    (_iso(_now() + timedelta(minutes=LOCKOUT_MINUTES)), row["id"]),
                )
                return None, f"Too many failed attempts. This account is locked for {LOCKOUT_MINUTES} minutes."
            con.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (attempts, row["id"]))
            return None, generic
        con.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (row["id"],))
        return _public(row), None


def get_user(user_id: int):
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public(row) if row else None


def update_display_name(user_id: int, name: str):
    name = normalize_name(name)
    error = validate_name(name)
    if error:
        return error
    with _conn() as con:
        con.execute("UPDATE users SET display_name = ? WHERE id = ?", (name, user_id))
    return None


def update_preferences(user_id: int, default_language: str, save_history: bool, apply_itn: bool):
    with _conn() as con:
        con.execute(
            "UPDATE users SET default_language = ?, save_history = ?, apply_itn = ? WHERE id = ?",
            (default_language, int(save_history), int(apply_itn), user_id),
        )


def change_password(user_id: int, current: str, new: str):
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is not None and row["password_hash"] == UNUSABLE_PASSWORD:
            return "This account signs in with Google, so it has no password to change."
        if row is None or not verify_password(current, row["password_hash"]):
            return "Your current password is incorrect."
        error = validate_password(new, row["email"])
        if error:
            return error
        if verify_password(new, row["password_hash"]):
            return "Choose a new password that is different from the current one."
        con.execute(
            "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
            (hash_password(new), user_id),
        )
    return None


def delete_user(user_id: int, password: str = "", confirm_text: str = ""):
    """Delete the account and everything it owns (history, speech, conversations, identities)."""
    with _conn() as con:
        row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return "Account not found."
        if row["password_hash"] == UNUSABLE_PASSWORD:
            if confirm_text.strip() != "DELETE":
                return "Type DELETE (in capital letters) to confirm."
        elif not verify_password(password, row["password_hash"]):
            return "Your password is incorrect."
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))  # everything else goes via ON DELETE CASCADE
    return None


# ----------------------------------------------------------------------------- history
def add_history(user_id: int, source: str, language_name: str, language_code: str, filename, transcript: str):
    if not transcript.strip():
        return
    with _conn() as con:
        con.execute(
            "INSERT INTO history (user_id, created_at, source, language_name, language_code, filename, transcript) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, _iso(_now()), source, language_name, language_code, filename, transcript),
        )


def list_history(user_id: int, limit: int = 20):
    with _conn() as con:
        rows = con.execute(
            "SELECT id, created_at, source, language_name, language_code, filename, transcript "
            "FROM history WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def count_history(user_id: int) -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM history WHERE user_id = ?", (user_id,)).fetchone()[0]


def delete_history_item(user_id: int, item_id: int):
    with _conn() as con:  # the user_id condition stops anyone deleting another user's item
        con.execute("DELETE FROM history WHERE id = ? AND user_id = ?", (item_id, user_id))


def clear_history(user_id: int):
    with _conn() as con:
        con.execute("DELETE FROM history WHERE user_id = ?", (user_id,))


# ----------------------------------------------------------------------------- Google sign-in
def _name_from_google(name: str, email: str) -> str:
    candidate = normalize_name(name)[:60]
    if validate_name(candidate):
        candidate = normalize_name(email.split("@")[0])[:60]
    return candidate if not validate_name(candidate) else "Google user"


def sign_in_with_google(subject: str, email: str, email_verified, name: str = ""):
    """Find or create the local account for a Google identity.

    Returns (user, error, notice). Rules:
      1. The Google `sub` (a permanent id) identifies the person, never the email alone.
      2. The email must be verified by Google.
      3. If the email already belongs to a password account, the Google identity is linked to it and the
         old password is REMOVED. Our own sign-up does not verify emails, so without this, someone could
         pre-register your email and keep a back door. Google has just proven you own the address.
    """
    email = normalize_email(email)
    verified = email_verified is True or str(email_verified).lower() == "true"
    if not subject or not email or not verified:
        return None, "Google did not confirm a verified email address for this account.", None
    if validate_email(email):
        return None, "Google returned an email address this app cannot use.", None

    try:
        with _conn() as con:
            ident = con.execute(
                "SELECT user_id FROM identities WHERE provider = 'google' AND subject = ?", (subject,)
            ).fetchone()
            if ident:
                row = con.execute("SELECT * FROM users WHERE id = ?", (ident["user_id"],)).fetchone()
                return _public(row), None, None

            row = con.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            notice = None
            if row is None:
                cur = con.execute(
                    "INSERT INTO users (email, display_name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (email, _name_from_google(name, email), UNUSABLE_PASSWORD, _iso(_now())),
                )
                user_id = cur.lastrowid
            else:
                user_id = row["id"]
                if row["password_hash"] != UNUSABLE_PASSWORD:
                    con.execute(
                        "UPDATE users SET password_hash = ?, auth_version = auth_version + 1, "
                        "failed_attempts = 0, locked_until = NULL WHERE id = ?",
                        (UNUSABLE_PASSWORD, user_id),
                    )
                    notice = ("We linked your Google account to your existing account and removed its old password "
                              "for security. From now on, use Continue with Google.")
                else:
                    notice = "We linked your Google account to your existing account."
            con.execute(
                "INSERT INTO identities (user_id, provider, subject, email, created_at) VALUES (?, 'google', ?, ?, ?)",
                (user_id, subject, email, _iso(_now())),
            )
            row = con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public(row), None, notice
    except sqlite3.IntegrityError:
        return None, "That Google account is already linked to another user. Try again.", None


def sign_in_methods(user_id: int) -> list:
    with _conn() as con:
        has_pw = con.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        google = con.execute("SELECT 1 FROM identities WHERE user_id = ? AND provider = 'google'", (user_id,)).fetchone()
    methods = []
    if has_pw and has_pw["password_hash"] != UNUSABLE_PASSWORD:
        methods.append("Email and password")
    if google:
        methods.append("Google")
    return methods


# ----------------------------------------------------------------------------- text-to-speech history
def add_tts(user_id: int, text: str, language_name: str, language_code: str, voice: str, model: str,
            container: str, speed: float, audio: bytes | None):
    stored = audio if audio and len(audio) <= MAX_STORED_AUDIO_BYTES else None
    with _conn() as con:
        if stored:  # keep the database small: only the newest MAX_STORED_AUDIO_ITEMS audio files are kept per user
            con.execute(
                "UPDATE tts_history SET audio = NULL WHERE user_id = ? AND audio IS NOT NULL AND id NOT IN "
                "(SELECT id FROM tts_history WHERE user_id = ? AND audio IS NOT NULL ORDER BY id DESC LIMIT ?)",
                (user_id, user_id, MAX_STORED_AUDIO_ITEMS - 1),
            )
        cur = con.execute(
            "INSERT INTO tts_history (user_id, created_at, text, language_name, language_code, voice, model, "
            "container, speed, audio) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, _iso(_now()), text, language_name, language_code, voice, model, container, speed, stored),
        )
        return cur.lastrowid


def list_tts(user_id: int, limit: int = 10):
    with _conn() as con:
        rows = con.execute(
            "SELECT id, created_at, text, language_name, language_code, voice, model, container, speed, "
            "(audio IS NOT NULL) AS has_audio FROM tts_history WHERE user_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?", (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_tts_audio(user_id: int, item_id: int):
    with _conn() as con:  # user_id condition: nobody can fetch another user's audio
        row = con.execute("SELECT audio, container FROM tts_history WHERE id = ? AND user_id = ?",
                          (item_id, user_id)).fetchone()
    return (row["audio"], row["container"]) if row and row["audio"] else (None, None)


def count_tts(user_id: int) -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM tts_history WHERE user_id = ?", (user_id,)).fetchone()[0]


def delete_tts(user_id: int, item_id: int):
    with _conn() as con:
        con.execute("DELETE FROM tts_history WHERE id = ? AND user_id = ?", (item_id, user_id))


def clear_tts(user_id: int):
    with _conn() as con:
        con.execute("DELETE FROM tts_history WHERE user_id = ?", (user_id,))


# ----------------------------------------------------------------------------- older conversations (read and delete only)
def get_messages(user_id: int, conversation_id: int):
    with _conn() as con:
        rows = con.execute(
            "SELECT m.role, m.content, m.created_at FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id "
            "WHERE m.conversation_id = ? AND c.user_id = ? ORDER BY m.id", (conversation_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def list_conversations(user_id: int, limit: int = 10):
    with _conn() as con:
        rows = con.execute(
            "SELECT c.id, c.title, c.language_name, c.created_at, c.updated_at, "
            "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
            "FROM conversations c WHERE c.user_id = ? ORDER BY c.updated_at DESC, c.id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def count_conversations(user_id: int) -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,)).fetchone()[0]


def delete_conversation(user_id: int, conversation_id: int):
    with _conn() as con:
        con.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))


def clear_conversations(user_id: int):
    with _conn() as con:
        con.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))


# ----------------------------------------------------------------------------- dashboard numbers
def usage_stats(user_id: int) -> dict:
    """Real counts from this user's own records (cheap COUNT queries)."""
    with _conn() as con:
        one = lambda q: con.execute(q, (user_id,)).fetchone()[0]
        return {
            "transcripts": one("SELECT COUNT(*) FROM history WHERE user_id = ?"),
            "speech": one("SELECT COUNT(*) FROM tts_history WHERE user_id = ?"),
        }


def recent_activity(user_id: int, limit: int = 6):
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM ("
            " SELECT 'Transcription' AS kind, created_at, language_name AS detail, substr(transcript, 1, 90) AS preview FROM history WHERE user_id = ?1"
            " UNION ALL"
            " SELECT 'Text-to-Speech', created_at, language_name || ', voice ' || voice, substr(text, 1, 90) FROM tts_history WHERE user_id = ?1"
            " UNION ALL"
            " SELECT 'Conversation', updated_at, language_name, title FROM conversations WHERE user_id = ?1"
            ") ORDER BY created_at DESC LIMIT ?2", (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
