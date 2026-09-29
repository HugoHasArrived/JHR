from __future__ import annotations
import os
import html
import sqlite3
import io
import secrets
import hashlib
import re
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template_string,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    from gridfs import GridFSBucket
    MONGODB_DRIVER_AVAILABLE = True
except ImportError:
    MongoClient = None
    PyMongoError = Exception
    GridFSBucket = None
    MONGODB_DRIVER_AVAILABLE = False
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "/var/data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir_ok = os.access(DATA_DIR, os.W_OK)
except OSError:
    _data_dir_ok = False
if not _data_dir_ok:
    DATA_DIR = Path(os.environ.get("FALLBACK_DATA_DIR", BASE_DIR / "data"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _data_dir_ok = os.access(DATA_DIR, os.W_OK)
if not _data_dir_ok:
    raise RuntimeError(
        "Application data directory is not writable. Set DATA_DIR to a writable "
        "directory (on Render, /var/data is recommended)."
    )
DB_PATH = DATA_DIR / "mctc_court.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-in-render",
)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
STAFF_IDLE_TIMEOUT = timedelta(minutes=5)
if os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True
COURT_NAME = "Municipal Circuit Trial Court of Silang-Amadeo, Cavite"
COURT_SHORT_NAME = "MCTC Silang-Amadeo"
COURT_ADDRESS = "PNP Bldg, Plaza Libertad, Poblacion 2, Silang, Cavite"
COURT_PHONE = "09284621305"
COURT_EMAIL = "mctc2sad000@judiciary.gov.ph"
COURT_OFFICE_HOURS = "Monday to Friday, 8:00 AM - 5:00 PM"
MCTC_LOGO = "image0.png"
MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
MONGODB_DB_NAME = os.environ.get("MONGODB_DB", "mctc_silang_amadeo").strip() or "mctc_silang_amadeo"
MONGO_CLIENT = None
MONGO_DB = None
MONGO_UPLOADS = None
MONGO_STATE = None
MONGO_READY = False
MONGO_ERROR = ""
MONGO_LAST_SYNC = ""
MONGO_COLLECTIONS = (
    "staff",
    "cases",
    "hearings",
    "notices",
    "legal_resources",
    "requirements",
    "schedule",
    "audit_logs",
    "private_notepad",
)
SUPREME_LOGO = "1280px-Seal_of_the_Supreme_Court_(Philippines).png"
MAP_QUERY = quote_plus(f"{COURT_NAME}, {COURT_ADDRESS}")
GOOGLE_MAPS_URL = (
    "https://www.google.com/maps/search/?api=1&query=" + MAP_QUERY
)
ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp", "gif",
    "doc", "docx", "xls", "xlsx", "txt",
}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
T = {
    "en": {
        "home": "Home",
        "about": "About Us",
        "search": "Search Case",
        "calendar": "Tuesday Calendar",
        "requirements": "Requirements",
        "news": "News and Announcements",
        "contact": "Contact Us",
        "language": "Language",
        "light": "Light",
        "dark": "Dark",
        "staff_login": "Staff Login",
        "staff_dashboard": "Staff Dashboard",
        "cases": "Cases",
        "notices": "Notices",
        "laws": "Laws, Decisions and Rules",
        "staff_accounts": "Staff Accounts",
        "logout": "Log Out",
        "save": "Save",
        "add": "Add",
        "edit": "Edit",
        "delete": "Delete",
        "view": "View",
        "open": "Open",
        "upload": "Upload",
        "case_number": "Case Number",
        "plaintiff": "Plaintiff's Last Name / Corporation Name",
        "defendant": "Accused",
        "accused": "Accused's Last Name",
        "case_category": "Case Category",
        "criminal": "Criminal",
        "civil": "Civil",
        "parties": "Parties",
        "case_type": "Case Type",
        "status": "Status",
        "description": "Public Description",
        "hearing": "Hearing",
        "hearing_date": "Hearing Date",
        "hearing_time": "Hearing Time",
        "hearing_nature": "Nature of Hearing",
        "hearing_status": "Hearing Status",
        "remarks": "Remarks",
        "courtroom": "Courtroom",
        "required_search": "Enter the complete case number and the required party name.",
        "how_search": "How to Search",
        "step1": "Enter the complete case number.",
        "step2": "Enter the plaintiff's last name or corporation name.",
        "step3": "Both fields are required.",
        "step4": "Select Search Case.",
        "no_results": "No matching public case was found.",
        "invalid_login": "Invalid username or password.",
        "login_required": "Please log in as authorized staff.",
        "forgot_password": "Forgot Password?",
        "forgot_password_title": "Reset Staff Password",
        "forgot_password_help": "Enter your staff username or registered email address. If the account exists, a reset link will be sent to its registered email.",
        "welcome": "Welcome, Court Staff!",
        "signed_in": "Signed in as",
        "office_hours": "Office Hours",
        "open_maps": "Open Google Maps",
        "not_uploaded": "Not yet uploaded",
        "copyright": "© 2026 Municipal Circuit Trial Court of Silang-Amadeo, Cavite. All rights reserved.",
    },
    "fil": {
        "home": "Home",
        "about": "Tungkol sa Amin",
        "search": "Maghanap ng Kaso",
        "calendar": "Kalendaryo ng Martes",
        "requirements": "Mga Kinakailangan",
        "news": "Balita at mga Anunsyo",
        "contact": "Makipag-ugnayan",
        "language": "Wika",
        "light": "Liwanag",
        "dark": "Madilim",
        "staff_login": "Staff Login",
        "staff_dashboard": "Dashboard ng Staff",
        "cases": "Mga Kaso",
        "notices": "Mga Abiso",
        "laws": "Mga Batas, Desisyon at Alituntunin",
        "staff_accounts": "Mga Account ng Staff",
        "logout": "Mag-Logout",
        "save": "I-save",
        "add": "Magdagdag",
        "edit": "I-edit",
        "delete": "Burahin",
        "view": "Tingnan",
        "open": "Buksan",
        "upload": "Mag-upload",
        "case_number": "Numero ng Kaso",
        "plaintiff": "Apelyido ng Plaintiff / Pangalan ng Corporation",
        "defendant": "Akusado",
        "accused": "Apelyido ng Akusado",
        "case_category": "Kategorya ng Kaso",
        "criminal": "Kriminal",
        "civil": "Sibil",
        "parties": "Mga Partido",
        "case_type": "Uri ng Kaso",
        "status": "Katayuan",
        "description": "Pampublikong Deskripsyon",
        "hearing": "Pagdinig",
        "hearing_date": "Petsa ng Pagdinig",
        "hearing_time": "Oras ng Pagdinig",
        "hearing_nature": "Uri ng Pagdinig",
        "hearing_status": "Katayuan ng Pagdinig",
        "remarks": "Mga Tala",
        "courtroom": "Silid ng Hukuman",
        "required_search": "Kinakailangan ang parehong kumpletong case number at apelyido ng plaintiff / pangalan ng corporation.",
        "how_search": "Paano Maghanap",
        "step1": "Ilagay ang buong case number.",
        "step2": "Ilagay ang apelyido ng plaintiff o pangalan ng corporation.",
        "step3": "Kinakailangan ang parehong field.",
        "step4": "Piliin ang Maghanap ng Kaso.",
        "no_results": "Walang nakitang pampublikong kaso.",
        "invalid_login": "Mali ang username o password.",
        "login_required": "Mag-login bilang awtorisadong staff.",
        "forgot_password": "Nakalimutan ang Password?",
        "forgot_password_title": "I-reset ang Password ng Staff",
        "forgot_password_help": "Ilagay ang username o nakarehistrong email. Kung umiiral ang account, magpapadala ng reset link sa rehistradong email.",
        "welcome": "Maligayang Pagdating, Kawani ng Hukuman!",
        "signed_in": "Naka-sign in bilang",
        "office_hours": "Oras ng Opisina",
        "open_maps": "Buksan ang Google Maps",
        "not_uploaded": "Hindi pa naiu-upload",
        "copyright": "© 2026 Municipal Circuit Trial Court of Silang-Amadeo, Cavite. Lahat ng karapatan ay nakalaan.",
    },
}
def tr(key):
    language = session.get("language", "en")
    if language not in T:
        language = "en"
    return T[language].get(key, T["en"].get(key, key))
def esc(value):
    return html.escape(str(value or ""), quote=True)
def now():
    return datetime.utcnow().isoformat(timespec="seconds")
def viewer_now():
    return datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Manila")).strftime("%Y-%m-%d %H:%M:%S")

def get_visitor_id():
    visitor_id = session.get("visitor_id")
    if not visitor_id:
        visitor_id = secrets.token_hex(16)
        session["visitor_id"] = visitor_id
    return visitor_id

def log_case_view(case_row):
    """Record a public case-detail view for staff/super-admin analytics."""
    try:
        connection = db()
        connection.execute(
            """
            INSERT INTO viewer_logs
            (case_id, case_number, case_category, visitor_id, viewed_at, ip_address, user_agent, referrer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_row["id"],
                str(case_row["case_number"] or ""),
                str(case_row["case_category"] or ""),
                get_visitor_id(),
                viewer_now(),
                (request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""),
                request.headers.get("User-Agent", "")[:1000],
                request.headers.get("Referer", "")[:1000],
            ),
        )
        durable_commit(connection)
        connection.close()
    except Exception as error:
        print("Viewer logging failed:", type(error).__name__, error)
def current_theme():
    theme = session.get("theme", "light")
    return theme if theme in {"light", "dark"} else "light"
def configure_mongodb():
    global MONGO_CLIENT, MONGO_DB, MONGO_UPLOADS, MONGO_STATE
    global MONGO_READY, MONGO_ERROR
    if not MONGODB_URI:
        MONGO_READY = False
        MONGO_ERROR = "MONGODB_URI is not configured."
        return
    if not MONGODB_DRIVER_AVAILABLE:
        MONGO_READY = False
        MONGO_ERROR = "pymongo is not installed. Add pymongo[srv] to requirements.txt."
        return
    try:
        MONGO_CLIENT = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=20000,
            retryWrites=True,
        )
        MONGO_CLIENT.admin.command("ping")
        MONGO_DB = MONGO_CLIENT[MONGODB_DB_NAME]
        MONGO_UPLOADS = GridFSBucket(MONGO_DB, bucket_name="uploads")
        MONGO_STATE = GridFSBucket(MONGO_DB, bucket_name="application_state")
        MONGO_READY = True
        MONGO_ERROR = ""
    except Exception as error:
        MONGO_READY = False
        MONGO_ERROR = f"{type(error).__name__}: {error}"

def restore_sqlite_from_mongodb():
    if not MONGO_READY or MONGO_STATE is None:
        return False
    try:
        latest = None
        for item in MONGO_STATE.find({"filename": "mctc_court.db"}).sort("uploadDate", -1).limit(1):
            latest = item
            break
        if latest is None:
          print("MONGO RESTORE: No SQLite backup found.")
          return False
        data = MONGO_STATE.open_download_stream(latest._id).read()
        print("MONGO RESTORE: Backup downloaded successfully.")
        temp = DB_PATH.with_suffix(".mongo-restored.db")
        temp.write_bytes(data)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(DB_PATH) + suffix)
            if sidecar.exists():
                try:
                    sidecar.unlink()
                except OSError:
                    pass
        temp.replace(DB_PATH)
        return True
    except Exception as error:
        global MONGO_ERROR
        MONGO_ERROR = f"Restore failed: {type(error).__name__}: {error}"
        return False

def restore_uploads_from_mongodb():
    if not MONGO_READY or MONGO_UPLOADS is None:
        return
    try:
        for item in MONGO_UPLOADS.find({"metadata.kind": "application-upload"}):
            local_name = (item.metadata or {}).get("local_name")
            if not local_name:
                continue
            safe_name = secure_filename(local_name)
            if not safe_name:
                continue
            destination = UPLOAD_DIR / safe_name
            if destination.exists():
                continue
            data = MONGO_UPLOADS.open_download_stream(item._id).read()
            destination.write_bytes(data)
    except Exception as error:
        global MONGO_ERROR
        MONGO_ERROR = f"Upload restore failed: {type(error).__name__}: {error}"

def sync_sqlite_to_mongodb():
    global MONGO_LAST_SYNC, MONGO_ERROR
    if not MONGO_READY or MONGO_STATE is None:
        return False
    try:
        for old in MONGO_STATE.find({"filename": "mctc_court.db"}):
            MONGO_STATE.delete(old._id)
        data = DB_PATH.read_bytes()
        with MONGO_STATE.open_upload_stream(
            "mctc_court.db",
            metadata={"kind": "sqlite-snapshot", "updated_at": now()},
        ) as stream:
            stream.write(data)
        MONGO_LAST_SYNC = now()
        MONGO_ERROR = ""
        return True
    except Exception as error:
        MONGO_ERROR = f"Sync failed: {type(error).__name__}: {error}"
        return False

def sync_sqlite_collections_to_mongodb(connection):
    if not MONGO_READY or MONGO_DB is None:
        return False
    try:
        for table_name in MONGO_COLLECTIONS:
            rows = connection.execute(f"SELECT * FROM {table_name}").fetchall()
            documents = []
            for row in rows:
                item = {key: row[key] for key in row.keys()}
                if "id" in item:
                    item["_legacy_id"] = item["id"]
                item["_source_table"] = table_name
                item["_synced_at"] = now()
                item["_id"] = f"{table_name}:{item.get('id', 'singleton')}"
                documents.append(item)
            collection = MONGO_DB[table_name]
            collection.delete_many({})
            if documents:
                collection.insert_many(documents, ordered=False)
        return True
    except Exception as error:
        global MONGO_ERROR
        MONGO_ERROR = f"Collection sync failed: {type(error).__name__}: {error}"
        return False

def sync_uploaded_file_to_mongodb(local_name, original_name=None):
    if not MONGO_READY or MONGO_UPLOADS is None:
        return True
    try:
        path = UPLOAD_DIR / local_name
        if not path.exists():
            return False
        data = path.read_bytes()
        with MONGO_UPLOADS.open_upload_stream(
            local_name,
            metadata={
                "kind": "application-upload",
                "local_name": local_name,
                "original_name": original_name or local_name,
                "updated_at": now(),
            },
        ) as stream:
            stream.write(data)
        return True
    except Exception as error:
        global MONGO_ERROR
        MONGO_ERROR = f"File sync failed: {type(error).__name__}: {error}"
        return False

def delete_uploaded_file_from_mongodb(local_name):
    if not MONGO_READY or MONGO_UPLOADS is None:
        return
    try:
        for item in MONGO_UPLOADS.find({"metadata.local_name": local_name}):
            MONGO_UPLOADS.delete(item._id)
    except Exception as error:
        global MONGO_ERROR
        MONGO_ERROR = f"File delete sync failed: {type(error).__name__}: {error}"

def db():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection

def durable_commit(connection):
    """Commit changes and mirror the current database into MongoDB when configured."""
    connection.commit()
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error:
        try:
            connection.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except sqlite3.Error:
            pass
    if MONGO_READY:
        sync_sqlite_collections_to_mongodb(connection)
        if not sync_sqlite_to_mongodb():
            return False
    return True
def initialize_database():
    connection = db()
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT UNIQUE NOT NULL,
            plaintiff_name TEXT NOT NULL,
            defendant_name TEXT NOT NULL DEFAULT '',
            parties TEXT NOT NULL DEFAULT '',
            case_category TEXT NOT NULL DEFAULT 'Civil',
            case_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Active',
            termination_reason TEXT NOT NULL DEFAULT '',
            internal_notes TEXT NOT NULL DEFAULT '',
            public_description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS hearings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            hearing_date TEXT NOT NULL,
            hearing_time TEXT NOT NULL DEFAULT '',
            hearing_nature TEXT NOT NULL DEFAULT 'Initial Hearing',
            hearing_status TEXT NOT NULL DEFAULT 'Scheduled',
            remarks TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_en TEXT NOT NULL,
            title_fil TEXT NOT NULL,
            body_en TEXT NOT NULL,
            body_fil TEXT NOT NULL,
            attachment TEXT,
            original_filename TEXT,
            published INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS legal_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            file_name TEXT,
            original_filename TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            title_en TEXT NOT NULL,
            title_fil TEXT NOT NULL,
            description_en TEXT NOT NULL DEFAULT 'Not yet uploaded',
            description_fil TEXT NOT NULL DEFAULT 'Hindi pa naiu-upload',
            file_name TEXT,
            original_filename TEXT,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            file_name TEXT,
            original_filename TEXT,
            file_type TEXT,
            updated_at TEXT,
            uploaded_by TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS viewer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            case_number TEXT NOT NULL DEFAULT '',
            case_category TEXT NOT NULL DEFAULT '',
            visitor_id TEXT NOT NULL,
            viewed_at TEXT NOT NULL,
            ip_address TEXT NOT NULL DEFAULT '',
            user_agent TEXT NOT NULL DEFAULT '',
            referrer TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS private_notepad (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL DEFAULT ''
        );
        """
    )
    requirement_seeds = [
        (
            "bond",
            "Requirements for Posting Bail Bond",
            "Mga Kinakailangan para sa Posting Bail Bond",
        ),
        (
            "clearance",
            "Requirements for Clearance",
            "Mga Kinakailangan para sa Clearance",
        ),
    ]
    case_columns = {row[1] for row in connection.execute("PRAGMA table_info(cases)").fetchall()}
    if "case_category" not in case_columns:
        connection.execute("ALTER TABLE cases ADD COLUMN case_category TEXT NOT NULL DEFAULT 'Civil'")
        case_columns.add("case_category")
    if "termination_reason" not in case_columns:
        connection.execute("ALTER TABLE cases ADD COLUMN termination_reason TEXT NOT NULL DEFAULT ''")
        case_columns.add("termination_reason")
    if "internal_notes" not in case_columns:
        connection.execute("ALTER TABLE cases ADD COLUMN internal_notes TEXT NOT NULL DEFAULT ''")
        case_columns.add("internal_notes")

    # Keep legacy Pending records compatible with the new Active/Archived/Terminated workflow.
    connection.execute("UPDATE cases SET status = 'Active' WHERE status = 'Pending'")

    for category, title_en, title_fil in requirement_seeds:
        exists = connection.execute(
            "SELECT id FROM requirements WHERE category = ?",
            (category,),
        ).fetchone()
        if exists is None:
            connection.execute(
                """
                INSERT INTO requirements
                (category, title_en, title_fil, description_en,
                 description_fil, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    title_en,
                    title_fil,
                    "Not yet uploaded",
                    "Hindi pa naiu-upload",
                    now(),
                ),
            )
    admin = connection.execute(
        "SELECT * FROM staff WHERE lower(username) = 'admin' LIMIT 1"
    ).fetchone()
    if admin is None:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Admin",
                "josehr.tan@gmail.com",
                generate_password_hash("ChangeMe123!"),
                "admin",
                1,
                now(),
            ),
        )
    else:
        connection.execute(
            "UPDATE staff SET username = ?, email = ?, role = ?, active = 1 WHERE id = ?",
            ("Admin", "josehr.tan@gmail.com", "admin", admin["id"]),
        )
    superadmin = connection.execute(
        "SELECT * FROM staff WHERE username = ? LIMIT 1",
        ("26-0054",),
    ).fetchone()
    if superadmin is None:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "26-0054",
                "26-0054@staff.local",
                generate_password_hash("ThisWasHugo"),
                "superadmin",
                1,
                now(),
            ),
        )
    else:
        connection.execute(
            "UPDATE staff SET email = ?, role = ?, active = 1 WHERE id = ?",
            ("26-0054@staff.local", "superadmin", superadmin["id"]),
        )
    note = connection.execute("SELECT id FROM private_notepad WHERE id = 1").fetchone()
    if note is None:
        connection.execute(
            "INSERT INTO private_notepad (id, content, updated_at, updated_by) VALUES (1, '', ?, ?)",
            (now(), "system"),
        )
    connection.commit()
    connection.close()
configure_mongodb()
# Restore the latest MongoDB snapshot first, then run schema migrations.
# This prevents an older snapshot from overwriting newly added SQLite columns.
restore_sqlite_from_mongodb()
initialize_database()
restore_uploads_from_mongodb()
BOND_REQUIREMENTS = [
    "Personal Data (form from court)",
    "Pictures 2x2 with name tag, signature, case, case number and date",
    "4 pcs. Front",
    "4 pcs. Left side",
    "4 pcs. Right side",
    "Barangay Clearance attesting the real name and residence of the accused",
    "Certification attesting the length of residency",
    "House Sketch - dated, certified, signed and sealed by the barangay captain",
    "Certificate of Detention, if detained or arrested, or Affidavit of Voluntary Surrender, if not detained",
    "Fingerprint (piano)",
    "Specimen signature, at least 5 signatures",
    "Affidavit of Undertaking",
    "Valid government-issued identification card, original and xerox copy (back-to-back)",
    "Original Copy of PSA Birth Certificate with attached receipt",
    "If married, female, original copy of PSA Marriage Certificate with attached receipt",
]

CLEARANCE_REQUIREMENTS = [
    {
        "title": "MCTC CLEARANCE - FOR EMPLOYMENT/BOARD EXAMINATION",
        "items": [
            "Valid Police Clearance or NBI Clearance",
            "Latest Cedula",
        ],
    },
    {
        "title": "MCTC CLEARANCE / NO PENDING CASE CERTIFICATION",
        "items": [
            "Information/order/any document about the case",
            "Authorization letter in case of processing through a representative",
            "Valid identification card of the party and the representative",
        ],
    },
    {
        "title": "MCTC CLEARANCE/CERTIFICATION - FOR LAND-TITLING/TAX DECLARATION",
        "items": [
            "Original latest tax declaration",
            "Authorization letter in case of processing through a representative",
            "Valid identification card of the landowner and the representative",
        ],
    },
]

CLEARANCE_NOTES = [
    "No cash transaction. Payment is made through GCash or bank transfer.",
    "Amount to be paid is ₱120.00 (₱90.00 certification fee + ₱30.00 convenience fee per transaction).",
    "First-time job seekers are exempt from paying the fee pursuant to the First Time Jobseekers Assistance Act.",
]
def audit(action, target=""):
    try:
        connection = db()
        connection.execute(
            """
            INSERT INTO audit_logs (username, action, target, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session.get("staff_username", "system"),
                action,
                str(target),
                now(),
            ),
        )
        durable_commit(connection)
        connection.close()
    except sqlite3.Error:
        pass
def staff_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            flash(tr("login_required"), "warning")
            return redirect(url_for("staff_login"))
        last_activity = session.get("staff_last_activity")
        try:
            last_activity_at = datetime.fromisoformat(last_activity) if last_activity else None
        except (TypeError, ValueError):
            last_activity_at = None
        current_time = datetime.utcnow()
        if last_activity_at is None or current_time - last_activity_at >= STAFF_IDLE_TIMEOUT:
            username = session.get("staff_username", "")
            session.clear()
            audit("auto_logout", username)
            flash("You were automatically logged out after 5 minutes of inactivity.", "warning")
            return redirect(url_for("staff_login"))
        session["staff_last_activity"] = current_time.isoformat(timespec="seconds")
        return function(*args, **kwargs)
    return wrapper
def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            return redirect(url_for("staff_login"))
        if session.get("staff_role") not in {"admin", "superadmin"}:
            abort(403)
        return function(*args, **kwargs)
    return wrapper

def superadmin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("staff_logged_in", False):
            return redirect(url_for("staff_login"))
        if session.get("staff_role") != "superadmin":
            abort(403)
        return function(*args, **kwargs)
    return wrapper
def save_upload(file):
    if file is None or not file.filename:
        return None, None, None
    original = secure_filename(file.filename)
    if not original:
        return None, None, None
    extension = Path(original).suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("That file type is not allowed.")
    generated = f"{secrets.token_hex(16)}_{original}"
    file.save(UPLOAD_DIR / generated)
    if MONGO_READY and not sync_uploaded_file_to_mongodb(generated, original):
        try:
            (UPLOAD_DIR / generated).unlink()
        except OSError:
            pass
        raise ValueError("The upload could not be synchronized to MongoDB.")
    return generated, original, extension
def delete_uploaded_file(filename):
    if not filename:
        return
    path = UPLOAD_DIR / filename
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    delete_uploaded_file_from_mongodb(filename)
STYLE = r"""
:root {
    --bg: #faf8fd;
    --surface: #ffffff;
    --surface-soft: #f2eafa;
    --text: #24152d;
    --muted: #716178;
    --border: #ded0e7;
    --purple: #6d28d9;
    --purple-dark: #3b0764;
    --purple-light: #8b5cf6;
    --danger: #a61d3f;
    --success: #18723c;
    --warning: #a16207;
    --shadow: rgba(55, 18, 72, .10);
}
body.dark {
    --bg: #110d15;
    --surface: #211825;
    --surface-soft: #30203a;
    --text: #fff8ff;
    --muted: #d2c2db;
    --border: #513d5a;
    --shadow: rgba(0,0,0,.30);
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
    margin: 0;
    min-height: 100vh;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.6;
}
a { color: var(--purple); text-decoration: none; }
body.dark a { color: #cfb8ff; }
a:hover { text-decoration: underline; }
.site-header {
    position: sticky;
    top: 0;
    z-index: 1000;
    background: linear-gradient(135deg, var(--purple-dark), var(--purple), var(--purple-light));
    color: white;
    box-shadow: 0 7px 25px rgba(30, 3, 48, .32);
}
.header-top {
    min-height: 86px;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 12px 18px 5px;
}
.header-title-wrap {
    text-align: center;
}
.header-title {
    margin: 0;
    font-size: 23px;
    font-weight: 900;
    line-height: 1.15;
}
.header-subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    font-weight: 700;
    opacity: .9;
}
.header-nav {
    width: 100%;
    min-height: 140px;
    padding: 8px 18px 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    align-content: center;
    gap: 6px;
    flex-wrap: wrap;
    margin: 0 auto;
    box-sizing: border-box;
}
.header-nav a,
.header-nav button,
.header-nav .nav-form {
    min-height: 42px;
}
.header-nav a,
.header-nav button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 8px 10px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: white;
    font-size: 12px;
    font-weight: 900;
    white-space: nowrap;
    cursor: pointer;
}
.header-nav a:hover,
.header-nav button:hover {
    background: rgba(255,255,255,.14);
    text-decoration: none;
}
@media (min-width: 1200px) {
    .header-nav {
        flex-wrap: nowrap;
        gap: 5px;
        padding: 8px 18px 12px;
    }
    .header-nav a,
    .header-nav button {
        padding: 8px 9px;
        font-size: 13px;
    }
}
.nav-logo {
    width: 112px;
    height: 112px;
    padding: 3px;
    object-fit: contain;
    background: white;
    border-radius: 50%;
    box-shadow: 0 4px 14px rgba(0,0,0,.25);
}
.container {
    width: 94%;
    max-width: 1180px;
    margin: 0 auto;
    padding: 28px 0 72px;
}
.center { text-align: center; }
.staff-interface .card h1,
.staff-interface .card h2,
.staff-interface .card h3,
.staff-interface .hero,
.staff-interface  .stat {
    text-align: center;
}
.unique-viewers-stat {
    grid-column: 1 / -1;
}
.viewer-definition {
    margin: 0 0 24px;
    padding: 18px 22px;
    border-radius: 16px;
    background: var(--surface-soft);
    border: 1px solid var(--border);
    text-align: left;
}
.viewer-definition h3 {
    margin: 0 0 10px;
}
.viewer-definition p {
    margin: 7px 0;
    line-height: 1.55;
}
@media (max-width: 650px) {
    .unique-viewers-stat {
        grid-column: auto;
    }
}
.staff-interface .actions {
    justify-content: center;
}
.staff-interface .grid {
    align-items: stretch;
}
.staff-quick-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    align-items: stretch;
}
.staff-quick-row.notice-row {
    grid-template-columns: 1fr;
    margin-top: 16px;
}
.staff-quick-row.notice-row > .card {
    width: 100%;
}
.staff-quick-row.third-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 16px;
}
@media (max-width: 1050px) {
    .staff-quick-row {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .staff-quick-row.third-row {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
@media (max-width: 650px) {
    .staff-quick-row,
    .staff-quick-row.third-row {
        grid-template-columns: 1fr;
    }
}
.superadmin-tabs-card { margin-top: 24px; }
.superadmin-tabs { display: flex; gap: 10px; flex-wrap: wrap; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
.superadmin-tab { width: auto; border: 1px solid var(--border); border-bottom: 0; border-radius: 12px 12px 0 0; padding: 12px 18px; background: var(--surface-soft); color: var(--text); font-weight: 800; cursor: pointer; }
.superadmin-tab.active { background: var(--primary); color: #fff; }
.superadmin-tab-panel { display: none; }
.superadmin-tab-panel.active { display: block; }
.viewer-detail-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 18px 0; }
@media (max-width: 650px) { .viewer-detail-stats { grid-template-columns: 1fr; } }
.hero {
    margin: 12px 0 24px;
    padding: 45px 22px;
    border-radius: 26px;
    background: linear-gradient(135deg, var(--purple-dark), var(--purple), var(--purple-light));
    color: white;
    text-align: center;
}
.hero h1 {
    max-width: 950px;
    margin: 14px auto;
    font-size: clamp(32px, 5vw, 58px);
    line-height: 1.04;
}
.hero p { max-width: 850px; margin: 0 auto; }
.hero-logo {
    width: 150px;
    height: 150px;
    object-fit: contain;
    border-radius: 50%;
    padding: 5px;
    background: white;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(245px, 1fr));
    gap: 16px;
}
.card {
    margin: 16px 0;
    padding: 22px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    box-shadow: 0 8px 24px var(--shadow);
}
.card.centered { text-align: center; }
/* Homepage feature cards: keep every purple action button on the same baseline. */
.home-feature-grid {
    align-items: stretch;
    gap: 12px;
    margin-bottom: 12px;
}
/* Remove the extra vertical margin from cards inside the homepage grid.
   This prevents the default card margin + grid gap from creating a large
   space between the feature-card row and the News section. */
.home-feature-grid .home-feature-card {
    margin: 0;
}
.home-feature-row-center {
    grid-template-columns: repeat(2, minmax(245px, 1fr));
    max-width: 760px;
    margin-left: auto;
    margin-right: auto;
}
.home-news-section {
    margin-top: 0;
}
.home-feature-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    height: 100%;
    box-sizing: border-box;
}
.home-feature-card h2 {
    min-height: 76px;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 0 12px;
    line-height: 1.35;
}
.home-feature-card p {
    min-height: 84px;
    width: 100%;
    margin: 0 0 18px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
}
.home-feature-card .button {
    margin-top: auto;
}
.actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 9px;
    margin-top: 15px;
}
button,
.button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 10px 15px;
    border: 0;
    border-radius: 10px;
    background: var(--purple);
    color: white;
    font-weight: 900;
    cursor: pointer;
    text-decoration: none;
}
button:hover,
.button:hover {
    background: var(--purple-dark);
    color: white;
    text-decoration: none;
}
.secondary {
    background: var(--surface-soft);
    color: var(--text);
    border: 1px solid var(--border);
}
.danger { background: var(--danger); }
.success { background: var(--success); }
.notice {
    margin: 13px 0;
    padding: 14px 16px;
    border-left: 5px solid var(--purple);
    border-radius: 10px;
    background: var(--surface-soft);
}
.notice.warning { border-left-color: var(--warning); }
.notice.success { border-left-color: var(--success); }
.notice.danger { border-left-color: var(--danger); }
.status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--surface-soft);
    color: var(--purple);
    font-size: 12px;
    font-weight: 900;
}
label {
    display: block;
    margin: 10px 0 5px;
    font-weight: 900;
}
input,
textarea,
select {
    width: 100%;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--surface);
    color: var(--text);
    font: inherit;
}
textarea { min-height: 110px; resize: vertical; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td {
    padding: 10px;
    text-align: center;
    vertical-align: top;
    border-bottom: 1px solid var(--border);
}
th { background: var(--surface-soft); }
.requirement-list { text-align: left; }
.requirement-list li { margin: 7px 0; }
.schedule-image {
    display: block;
    max-width: 100%;
    max-height: 850px;
    height: auto;
    margin: 18px auto;
    border-radius: 14px;
    box-shadow: 0 8px 22px var(--shadow);
}
.schedule-pdf {
    display: block;
    width: 100%;
    height: 850px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--surface);
}
.stat {
    text-align: center;
}
.stat-number {
    display: block;
    font-size: 42px;
    font-weight: 900;
    color: var(--purple);
}
.small { color: var(--muted); font-size: 13px; }
.empty { text-align: center; padding: 40px; color: var(--muted); }
.staff-only-note { border-left-color: var(--warning); }
footer {
    text-align: center;
    background: var(--surface);
    border-top: 1px solid var(--border);
    color: var(--muted);
    padding: 30px 15px;
}
footer p { margin: 8px 0; }
.staff-interface .header-nav {
    justify-content: center;
    text-align: center;
}
.staff-interface .header-nav .nav-form {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin: 0;
}
.staff-interface .header-nav .nav-form button {
    margin: 0;
}
@media (max-width: 1100px) {
    .header-nav {
        gap: 4px;
        padding-left: 10px;
        padding-right: 10px;
    }
    .header-nav a,
    .header-nav button {
        font-size: 11px;
        padding: 7px 8px;
    }
    .nav-logo {
        width: 78px;
        height: 78px;
    }
}
@media (max-width: 850px) {
    .header-title { font-size: 18px; }
    .header-subtitle { font-size: 12px; }
    .header-nav { gap: 3px; }
    .header-nav a,
    .header-nav button { font-size: 11px; padding: 8px; }
    .nav-logo { width: 82px; height: 82px; }
}
@media (max-width: 600px) {
    .header-nav { flex-direction: row; }
    .hero { padding: 36px 16px; }
    .hero h1 { font-size: 34px; }
    .two { grid-template-columns: 1fr; }
}
"""
def render_page(title, body, staff_page=False):
    theme = current_theme()
    other_theme = "dark" if theme == "light" else "light"
    other_language = "fil" if lang_value() == "en" else "en"
    language_label = "FIL" if lang_value() == "en" else "EN"
    theme_label = "🌙" if theme == "light" else "☀️"
    nav = []
    if staff_page or session.get("staff_logged_in", False):
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=MCTC_LOGO)}' "
            f"alt='MCTC Silang-Amadeo logo'>"
        )
        nav.append(
            f"<a href='{url_for('staff_dashboard')}'>{tr('staff_dashboard')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_cases')}'>{tr('cases')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_calendar')}'>{tr('calendar')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_requirements')}'>{tr('requirements')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_notices')}'>{tr('notices')}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_laws')}'>{tr('laws')}</a>"
        )
        if session.get("staff_role") in {"admin", "superadmin"}:
            nav.append(
                f"<a href='{url_for('staff_accounts')}'>{tr('staff_accounts')}</a>"
            )
        if session.get("staff_role") == "superadmin":
            nav.append(
                f"<a href='{url_for('superadmin_dashboard')}'>🛡️ Super Admin</a>"
            )
            nav.append(
                f"<a href='{url_for('private_notepad')}'>📝 Private Notepad</a>"
            )
        nav.append(
            f"<a href='{url_for('change_password')}'>🔑 Change Password</a>"
        )
        nav.append(
            f"<a href='{url_for('change_language', language=other_language)}'>{language_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('change_theme', theme=other_theme)}'>{theme_label}</a>"
        )
        nav.append(
            f"<form class='nav-form' method='post' action='{url_for('logout')}'>"
            f"<button type='submit'>{tr('logout')}</button></form>"
        )
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=SUPREME_LOGO)}' "
            f"alt='Supreme Court of the Philippines seal'>"
        )
    else:
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=MCTC_LOGO)}' "
            f"alt='MCTC Silang-Amadeo logo'>"
        )
        nav.append(f"<a href='{url_for('home')}'>{tr('home')}</a>")
        nav.append(f"<a href='{url_for('about')}'>{tr('about')}</a>")
        nav.append(f"<a href='{url_for('search_cases')}'>{tr('search')}</a>")
        nav.append(f"<a href='{url_for('public_calendar')}'>{tr('calendar')}</a>")
        nav.append(f"<a href='{url_for('requirements')}'>{tr('requirements')}</a>")
        nav.append(f"<a href='{url_for('public_laws')}'>{tr('laws')}</a>")
        nav.append(f"<a href='{url_for('news')}'>{tr('news')}</a>")
        nav.append(f"<a href='{url_for('contact')}'>{tr('contact')}</a>")
        nav.append(
            f"<a href='{url_for('change_language', language=other_language)}'>{language_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('change_theme', theme=other_theme)}'>{theme_label}</a>"
        )
        nav.append(
            f"<a href='{url_for('staff_login')}'>{tr('staff_login')}</a>"
        )
        nav.append(
            f"<img class='nav-logo' src='{url_for('static', filename=SUPREME_LOGO)}' "
            f"alt='Supreme Court of the Philippines seal'>"
        )
    flashes = ""
    for category, message in __import__("flask").get_flashed_messages(with_categories=True):
        flashes += f"<div class='notice {esc(category)}'>{esc(message)}</div>"
    staff_identity = ""
    if session.get("staff_logged_in"):
        staff_identity = (
            f"<p>{esc(tr('signed_in'))} "
            f"<strong>{esc(session.get('staff_username', ''))}</strong>.</p>"
        )
    return render_template_string(
        """
        <!doctype html>
        <html lang="{{ language }}">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta name="description" content="MCTC Silang-Amadeo Court Information Portal">
            <title>{{ title }} - {{ court_name }}</title>
            <style>{{ style|safe }}</style>
        </head>
        <body class="{{ theme }}{% if staff_page %} staff-interface{% endif %}">
            <header class="site-header">
                <div class="header-top">
                    <div class="header-title-wrap">
                        <h1 class="header-title">{{ court_name }}</h1>
                        <div class="header-subtitle">Official Court Information Portal</div>
                    </div>
                </div>
                <nav class="header-nav">
                    {{ navigation|safe }}
                </nav>
            </header>
            <main class="container">
                {{ flashes|safe }}
                {% if staff_identity %}
                <div class="small center">{{ staff_identity|safe }}</div>
                {% endif %}
                {{ body|safe }}
            </main>
            <footer>
                <strong>{{ court_name }}</strong>
                <p>{{ court_address }}</p>
                <p>{{ court_phone }} · <a href="mailto:{{ court_email }}">{{ court_email }}</a></p>
                <p><strong>{{ office_label }}:</strong> {{ office_hours }}</p>
                <p><a href="{{ maps_url }}" target="_blank" rel="noopener noreferrer">🗺️ {{ maps_label }}</a></p>
                <p>by JHR</p>
                <p>{{ copyright }}</p>
            </footer>
            {% if staff_logged_in %}
            <script>
            (function () {
                const logoutUrl = {{ url_for('logout')|tojson }};
                let timer;
                function resetTimer() {
                    clearTimeout(timer);
                    timer = setTimeout(() => { window.location.href = logoutUrl; }, 5 * 60 * 1000);
                }
                ['click', 'keydown', 'mousemove', 'scroll', 'touchstart'].forEach(eventName => document.addEventListener(eventName, resetTimer, {passive: true}));
                resetTimer();
            })();
            </script>
            {% endif %}
        </body>
        </html>
        """,
        language=lang_value(),
        theme=theme,
        title=title,
        court_name=COURT_NAME,
        court_address=COURT_ADDRESS,
        court_phone=COURT_PHONE,
        court_email=COURT_EMAIL,
        office_label=tr("office_hours"),
        office_hours=COURT_OFFICE_HOURS,
        maps_url=GOOGLE_MAPS_URL,
        maps_label=tr("open_maps"),
        copyright=tr("copyright"),
        style=STYLE,
        navigation="".join(nav),
        flashes=flashes,
        staff_identity=staff_identity,
        staff_logged_in=session.get("staff_logged_in", False),
        staff_page=staff_page,
        body=body,
    )
def lang_value():
    value = session.get("language", "en")
    return value if value in T else "en"
@app.route("/")
def home():
    connection = db()
    notices = connection.execute(
        """
        SELECT * FROM notices
        WHERE published = 1
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()
    connection.close()
    notices_html = ""
    for item in notices:
        title = item["title_fil"] if lang_value() == "fil" else item["title_en"]
        body_text = item["body_fil"] if lang_value() == "fil" else item["body_en"]
        attachment = ""
        if item["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=item['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        notices_html += (
            f"<div class='notice'>"
            f"<h3>{esc(title)}</h3>"
            f"<p>{esc(body_text)}</p>"
            f"{attachment}"
            f"</div>"
        )
    body = f"""
    <section class="hero">
        <img class="hero-logo"
             src="{url_for('static', filename=MCTC_LOGO)}"
             alt="MCTC logo">
        <h1>{esc(COURT_NAME)}</h1>
        <div class="actions">
            <a class="button" href="{url_for('search_cases')}">🔎 {tr('search')}</a>
        </div>
    </section>
    <section class="grid home-feature-grid">
        <div class="card centered home-feature-card">
            <h2>🔎 {tr('search')}</h2>
            <p>{tr('required_search')}</p>
            <a class="button" href="{url_for('search_cases')}">{tr('search')}</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📅 {tr('calendar')}</h2>
            <p>View the Tuesday court schedule uploaded by authorized court staff.</p>
            <a class="button" href="{url_for('public_calendar')}">View Tuesday Calendar</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📄 {tr('requirements')}</h2>
            <p>View the publicly available posting bail bond and clearance information.</p>
            <a class="button" href="{url_for('requirements')}">{tr('view')}</a>
        </div>
    </section>
    <section class="grid home-feature-grid home-feature-row-center">
        <div class="card centered home-feature-card">
            <h2>⚖️ {tr('laws')}</h2>
            <p>View publicly available laws, decisions and rules.</p>
            <a class="button" href="{url_for('public_laws')}">{tr('view')}</a>
        </div>
        <div class="card centered home-feature-card">
            <h2>📢 {tr('news')}</h2>
            <p>Read public notices and announcements from authorized staff.</p>
            <a class="button" href="{url_for('news')}">{tr('view')}</a>
        </div>
    </section>
    <section class="card home-news-section">
        <h2>📢 {tr('news')}</h2>
        {notices_html or '<p class="empty">No announcements yet.</p>'}
    </section>
    """
    return render_page(tr("home"), body)
@app.route("/about")
def about():
    body = f"""
    <section class="card centered">
        <h1>{tr('about')}</h1>
        <h2>{esc(COURT_NAME)}</h2>
        <p>
            The Municipal Circuit Trial Court of Silang–Amadeo, Cavite, formally identified by the Supreme Court as the 2nd Municipal Circuit Trial Court of Silang–Amadeo, Cavite, is a first level trial court of the Fourth Judicial Region of the Philippines. Its territorial jurisdiction covers the municipalities of Silang and Amadeo, Cavite. It handles cases within the jurisdiction of first level courts, which generally includes appropriate civil, criminal, and other cases specifically assigned by law, subject to statutory jurisdictional limits.
        </p>
        <div class="notice warning">
            Online information does not replace official court records,
            court orders, notices or certified documents.
        </div>
    </section>
    """
    return render_page(tr("about"), body)
@app.route("/contact")
def contact():
    body = f"""
    <section class="card centered">
        <h1>{tr('contact')}</h1>
        <h2>{esc(COURT_NAME)}</h2>
        <p><strong>{tr('address')}:</strong><br>{esc(COURT_ADDRESS)}</p>
        <p><strong>{tr('phone')}:</strong><br>{esc(COURT_PHONE)}</p>
        <p><strong>{tr('email') if 'email' in T[lang_value()] else 'Email Address'}:</strong><br>
           <a href="mailto:{esc(COURT_EMAIL)}">{esc(COURT_EMAIL)}</a></p>
        <p><strong>{tr('office_hours')}:</strong><br>{esc(COURT_OFFICE_HOURS)}</p>
        <a class="button" href="{GOOGLE_MAPS_URL}" target="_blank" rel="noopener noreferrer">
            🗺️ {tr('open_maps')}
        </a>
    </section>
    """
    return render_page(tr("contact"), body)
@app.route("/jhr")
def jhr():
    body = f"""
    <section class="card centered">
        <h1>JHR</h1>
        <p>JHR information page.</p>
    </section>
    """
    return render_page("JHR", body)
@app.route("/news")
def news():
    connection = db()
    notices = connection.execute(
        """
        SELECT * FROM notices
        WHERE published = 1
        ORDER BY created_at DESC
        """
    ).fetchall()
    connection.close()
    cards = ""
    for item in notices:
        title = item["title_fil"] if lang_value() == "fil" else item["title_en"]
        text = item["body_fil"] if lang_value() == "fil" else item["body_en"]
        attachment = ""
        if item["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=item['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        cards += (
            f"<article class='card'>"
            f"<h2>{esc(title)}</h2>"
            f"<p>{esc(text)}</p>"
            f"{attachment}"
            f"</article>"
        )
    body = (
        f"<section class='card centered'><h1>📢 {tr('news')}</h1></section>"
        + (cards or "<div class='card empty'>No announcements have been published.</div>")
    )
    return render_page(tr("news"), body)
@app.route("/search", methods=["GET"])
def search_cases():
    criminal_case_number = request.args.get("criminal_case_number", "").strip()
    criminal_name = request.args.get("criminal_name", "").strip()
    civil_case_number = request.args.get("civil_case_number", "").strip()
    civil_name = request.args.get("civil_name", "").strip().upper()

    criminal_result = None
    civil_result = None

    def find_case(category, case_number, name):
        if not case_number or not name:
            return None
        upper_case_number = case_number.upper()
        if category == "Criminal":
            # Criminal cases: AC or SC, but not SCC.
            if not (upper_case_number.startswith("AC") or (upper_case_number.startswith("SC") and not upper_case_number.startswith("SCC"))):
                return "invalid_case_number"
        else:
            # Civil cases: SC or SCC. AC is not allowed.
            if not (upper_case_number.startswith("CC") or upper_case_number.startswith("SCC")):
                return "invalid_case_number"

        connection = db()
        try:
            if category == "Criminal":
                return connection.execute(
                    """
                    SELECT * FROM cases
                    WHERE case_category = 'Criminal'
                    AND lower(case_number) = lower(?)
                    AND lower(defendant_name) = lower(?)
                    LIMIT 1
                    """,
                    (case_number, name),
                ).fetchone()
            return connection.execute(
                """
                SELECT * FROM cases
                WHERE case_category = 'Civil'
                AND lower(case_number) = lower(?)
                AND lower(plaintiff_name) = lower(?)
                LIMIT 1
                """,
                (case_number, name),
            ).fetchone()
        finally:
            connection.close()

    if criminal_case_number or criminal_name:
        if not criminal_case_number or not criminal_name:
            flash("For criminal cases, enter both the case number and the accused's last name or first-named accused.", "danger")
        else:
            criminal_result = find_case("Criminal", criminal_case_number, criminal_name)
            if criminal_result == "invalid_case_number":
                criminal_result = None
                flash("The criminal case number must start with AC or SC.", "danger")
            elif criminal_result is None:
                flash("No matching criminal case was found. Please call the court.", "warning")

    if civil_case_number or civil_name:
        if not civil_case_number or not civil_name:
            flash("For civil cases, enter both the case number and the plaintiff's last name or corporation name.", "danger")
        else:
            civil_result = find_case("Civil", civil_case_number, civil_name)
            if civil_result == "invalid_case_number":
                civil_result = None
                flash("The civil case number must start with CC or SCC. AC is not allowed for civil cases.", "danger")
            elif civil_result is None:
                flash("No matching civil case was found. Please call the court.", "warning")

    body = f"""
    <section class="card centered">
        <h1>🔎 {tr('search')}</h1>
        <p><strong>Search case for case status; if none is available, call the court.</strong></p>
        <p>Criminal and civil cases have separate search forms.</p>
    </section>

    <section class="card">
        <h2>⚖️ Criminal Case:</h2>
        <div class="notice">
            <ol>
                <li>Enter the case number beginning with <strong>AC</strong> or <strong>SC</strong>.</li>
                <li>Enter only the last name of the accused or the first-named accused.</li>
            </ol>
        </div>
        <form method="get" action="{url_for('search_cases')}">
            <label>Criminal Case Number</label>
            <input name="criminal_case_number" value="{esc(criminal_case_number)}" autocomplete="off" placeholder="AC... or SC..." required>
            <label>Accused's Last Name</label>
            <input name="criminal_name" value="{esc(criminal_name)}" autocomplete="off" required>
            <button type="submit">🔎 Search Criminal Case</button>
        </form>
    </section>

    <section class="card">
        <h2>⚖️ Civil Case</h2>
        <div class="notice">
            <ol>
                <li>Enter the case number beginning with <strong>CC</strong> or <strong>SCC</strong>.</li>
                <li>Enter only the last name or corporation name of the plaintiff or the first-named plaintiff.</li>
            </ol>
        </div>
        <form method="get" action="{url_for('search_cases')}">
            <label>Civil Case Number</label>
            <input name="civil_case_number" value="{esc(civil_case_number)}" autocomplete="off" placeholder="CC... or SCC..." required>
            <label>Plaintiff's Last Name/Corporation Name</label>
            <input name="civil_name" value="{esc(civil_name)}" autocomplete="off" required style="text-transform: uppercase" oninput="this.value = this.value.toUpperCase()">
            <button type="submit">🔎 Search Civil Case</button>
        </form>
    </section>
    """

    if criminal_result:
        body += f"""
        <section class="card">
            <h2>Criminal Case Result</h2>
            <span class="status">{esc(criminal_result['status'])}</span>
            {f"<p><strong>Termination Outcome:</strong> {esc(criminal_result['termination_reason'])}</p>" if criminal_result['status'] == 'Terminated' and criminal_result['termination_reason'] else ''}
            <h2>{esc(criminal_result['case_number'])}</h2>
            <p><strong>Accused:</strong> {esc(criminal_result['defendant_name'])}</p>
            <p><strong>{tr('parties')}:</strong> {esc(criminal_result['parties'])}</p>
            <p><strong>{tr('case_type')}:</strong> {esc(criminal_result['case_type'])}</p>
            <p>{esc(criminal_result['public_description'])}</p>
            <a class="button" href="{url_for('public_case', case_id=criminal_result['id'])}">{tr('view')}</a>
        </section>
        """

    if civil_result:
        body += f"""
        <section class="card">
            <h2>Civil Case Result</h2>
            <span class="status">{esc(civil_result['status'])}</span>
            {f"<p><strong>Termination Outcome:</strong> {esc(civil_result['termination_reason'])}</p>" if civil_result['status'] == 'Terminated' and civil_result['termination_reason'] else ''}
            <h2>{esc(civil_result['case_number'])}</h2>
            <p><strong>{tr('plaintiff')}:</strong> {esc(civil_result['plaintiff_name'])}</p>
            <p><strong>{tr('parties')}:</strong> {esc(civil_result['parties'])}</p>
            <p><strong>{tr('case_type')}:</strong> {esc(civil_result['case_type'])}</p>
            <p>{esc(civil_result['public_description'])}</p>
            <a class="button" href="{url_for('public_case', case_id=civil_result['id'])}">{tr('view')}</a>
        </section>
        """

    return render_page(tr("search"), body)
@app.route("/case/<int:case_id>")
def public_case(case_id):
    connection = db()
    case = connection.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    hearings = connection.execute(
        """
        SELECT * FROM hearings
        WHERE case_id = ?
        ORDER BY hearing_date, hearing_time, id
        """,
        (case_id,),
    ).fetchall()
    connection.close()
    if case is None:
        abort(404)
    log_case_view(case)
    hearing_html = ""
    for hearing in hearings:
        hearing_html += f"""
        <div class="notice">
            <p><strong>{tr('hearing_date')}:</strong> {esc(hearing['hearing_date'])}</p>
            <p><strong>{tr('hearing_time')}:</strong> {esc(hearing['hearing_time'])}</p>
            <p><strong>{tr('hearing_nature')}:</strong> {esc(hearing['hearing_nature'])}</p>
            <p><strong>{tr('hearing_status')}:</strong> <span class="status">{esc(hearing['hearing_status'])}</span></p>
            <p><strong>{tr('remarks')}:</strong> {esc(hearing['remarks'])}</p>
        </div>
        """
    body = f"""
    <section class="card">
        <span class="status">{esc(case['status'])}</span>
        {f"<p><strong>Termination Outcome:</strong> {esc(case['termination_reason'])}</p>" if case['status'] == 'Terminated' and case['termination_reason'] else ''}
        <h1>{esc(case['case_number'])}</h1>
        {f"<p><strong>{tr('plaintiff')}:</strong> {esc(case['plaintiff_name'])}</p>" if case['case_category'] == 'Civil' else f"<p><strong>Accused:</strong> {esc(case['defendant_name'])}</p>"}
        <p><strong>{tr('parties')}:</strong> {esc(case['parties'])}</p>
        <p><strong>{tr('case_type')}:</strong> {esc(case['case_type'])}</p>
        <p>{esc(case['public_description'])}</p>
    </section>
    <section class="card">
        <h2>📅 {tr('hearing')}</h2>
        {hearing_html or '<p class="empty">No published hearing information.</p>'}
    </section>
    """
    return render_page(tr("cases"), body)
@app.route("/requirements")
def requirements():
    connection = db()
    rows = connection.execute(
        """
        SELECT * FROM requirements
        ORDER BY CASE category WHEN 'bond' THEN 1 WHEN 'clearance' THEN 2 ELSE 3 END
        """
    ).fetchall()
    connection.close()
    body = f"""
    <section class="card centered">
        <h1>📄 {tr('requirements')}</h1>
        <p>
            The following public checklist was transcribed from the
            requirement notice supplied for this project.
        </p>
        <div class="notice warning">
            Please contact the court to confirm the current official requirements
            before submitting documents.
        </div>
    </section>
    """
    for row in rows:
        title = row["title_fil"] if lang_value() == "fil" else row["title_en"]
        description = row["description_fil"] if lang_value() == "fil" else row["description_en"]
        checklist = ""
        if row["category"] == "bond":
            checklist = "<ol class='requirement-list'>" + "".join(
                f"<li>{esc(item)}</li>" for item in BOND_REQUIREMENTS
            ) + "</ol>"
        else:
            clearance_sections = []
            for section in CLEARANCE_REQUIREMENTS:
                items_html = "<ol class='requirement-list'>" + "".join(
                    f"<li>{esc(item)}</li>" for item in section["items"]
                ) + "</ol>"
                clearance_sections.append(
                    f"<h3>{esc(section['title'])}</h3>{items_html}"
                )
            notes_html = (
                "<h3>NOTE:</h3><ol class='requirement-list'>"
                + "".join(f"<li>{esc(item)}</li>" for item in CLEARANCE_NOTES)
                + "</ol>"
            )
            checklist = "".join(clearance_sections) + notes_html
        file_link = ""
        if row["file_name"]:
            file_link = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        body += f"""
        <section class="card">
            <h2>{esc(title)}</h2>
            {checklist}
            <p class="small"><strong>Current uploaded information:</strong> {esc(description or tr('not_uploaded'))}</p>
            {file_link}
        </section>
        """
    return render_page(tr("requirements"), body)
@app.route("/calendar")
def public_calendar():
    connection = db()
    schedule = connection.execute(
        "SELECT * FROM schedule WHERE id = 1"
    ).fetchone()
    connection.close()
    schedule_html = (
        "<p class='empty'>No Tuesday schedule has been uploaded yet.</p>"
    )
    if schedule and schedule["file_name"]:
        filename = schedule["file_name"]
        extension = schedule["file_type"] or Path(filename).suffix.lower().lstrip(".")
        url = url_for("uploaded_file", filename=filename)
        if extension == "pdf":
            schedule_html = (
                f"<iframe class='schedule-pdf' src='{url}' title='Tuesday schedule PDF'></iframe>"
            )
        elif extension in IMAGE_EXTENSIONS:
            schedule_html = (
                f"<img class='schedule-image' src='{url}' alt='Tuesday schedule'>"
            )
        else:
            schedule_html = (
                f"<p><a class='button' href='{url}'>{tr('open')}</a></p>"
            )
    body = f"""
    <section class="card centered">
        <h1>📅 {tr('calendar')}</h1>
        <p>
            The Tuesday calendar is published as one staff-uploaded schedule.
        </p>
    </section>
    <section class="card">
        {schedule_html}
    </section>
    """
    return render_page(tr("calendar"), body)
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)

    local_path = UPLOAD_DIR / safe_name

    if local_path.exists() and local_path.is_file():
        return send_from_directory(UPLOAD_DIR, safe_name)

    if MONGO_READY and MONGO_UPLOADS is not None:
        try:
            for item in MONGO_UPLOADS.find({
                "metadata.kind": "application-upload",
                "metadata.local_name": safe_name,
            }).sort("uploadDate", -1).limit(1):
                data = MONGO_UPLOADS.open_download_stream(item._id).read()
                metadata = item.metadata or {}
                original_name = metadata.get("original_name") or safe_name
                extension = Path(safe_name).suffix.lower()
                mime_types = {
                    ".pdf": "application/pdf",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                    ".txt": "text/plain",
                    ".doc": "application/msword",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".xls": "application/vnd.ms-excel",
                    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
                return send_file(
                    io.BytesIO(data),
                    mimetype=mime_types.get(extension, "application/octet-stream"),
                    as_attachment=False,
                    download_name=original_name,
                )
        except Exception as error:
            print(
                "MongoDB file retrieval failed:",
                type(error).__name__,
                error,
            )

    abort(404)
@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if session.get("staff_logged_in"):
        return redirect(url_for("staff_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        connection = db()
        staff = connection.execute(
            """
            SELECT * FROM staff
            WHERE lower(username) = lower(?) AND active = 1
            """,
            (username,),
        ).fetchone()
        connection.close()
        if staff and check_password_hash(staff["password_hash"], password):
            session.clear()
            session.permanent = True
            session["staff_logged_in"] = True
            session["staff_last_activity"] = datetime.utcnow().isoformat(timespec="seconds")
            session["staff_id"] = staff["id"]
            session["staff_username"] = staff["username"]
            session["staff_role"] = staff["role"]
            session["language"] = "en"
            session["theme"] = "light"
            audit("login", username)
            return redirect(url_for("staff_dashboard"))
        flash(tr("invalid_login"), "danger")
    body = f"""
    <section class="card centered" style="max-width:520px;margin:45px auto">
        <h1>🔐 {tr('staff_login')}</h1>
        <p class="small">Authorized court staff only.</p>
        <form method="post" autocomplete="off">
            <label>{tr('username')}</label>
            <input name="username" autocomplete="username" required>
            <label>{tr('password')}</label>
            <input type="password" name="password" autocomplete="current-password" required>
            <br>
            <button type="submit">{tr('login') if 'login' in T[lang_value()] else 'Log In'}</button>
        </form>
        <p class="center" style="margin-top:18px"><a href="{url_for('forgot_password')}">🔐 {tr('forgot_password')}</a></p>
    </section>
    """
    return render_page(tr("staff_login"), body)
@app.route("/staff/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Reset a password locally without email using the court recovery code."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        recovery_code = request.form.get("recovery_code", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        expected_code = os.environ.get("STAFF_RECOVERY_CODE", "MCTC-RESET-2026")
        if not username or not recovery_code or not new_password or not confirm_password:
            flash("Please fill in all recovery fields.", "danger")
            return redirect(url_for("forgot_password"))
        if not secrets.compare_digest(recovery_code, expected_code):
            flash("The recovery code is incorrect.", "danger")
            return redirect(url_for("forgot_password"))
        if len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "danger")
            return redirect(url_for("forgot_password"))
        if new_password != confirm_password:
            flash("The new passwords do not match.", "danger")
            return redirect(url_for("forgot_password"))
        connection = db()
        staff = connection.execute(
            "SELECT id, username, password_hash, active FROM staff WHERE lower(username) = lower(?) LIMIT 1",
            (username,),
        ).fetchone()
        if staff is None or not staff["active"]:
            connection.close()
            flash("That account was not found or is disabled.", "danger")
            return redirect(url_for("forgot_password"))
        if check_password_hash(staff["password_hash"], new_password):
            connection.close()
            flash("New password must be different from the current password.", "danger")
            return redirect(url_for("forgot_password"))
        connection.execute(
            "UPDATE staff SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), staff["id"]),
        )
        durable_commit(connection)
        connection.close()
        audit("password_recovered", staff["username"])
        flash("Password changed successfully. You can now log in.", "success")
        return redirect(url_for("staff_login"))
    body = """
    <section class="card centered" style="max-width:620px;margin:45px auto">
        <h1>🔐 Forgot Password</h1>
        <p class="small">No email is required. Enter your username, the court recovery code, and your new password.</p>
        <form method="post" autocomplete="off">
            <label for="username">Username</label>
            <input id="username" name="username" autocomplete="username" required>
            <label for="recovery_code">Recovery Code</label>
            <input id="recovery_code" type="password" name="recovery_code" autocomplete="off" required>
            <label for="new_password">New Password</label>
            <input id="new_password" type="password" name="new_password" minlength="8" autocomplete="new-password" required>
            <label for="confirm_password">Confirm New Password</label>
            <input id="confirm_password" type="password" name="confirm_password" minlength="8" autocomplete="new-password" required>
            <br>
            <button type="submit">Change Password</button>
        </form>
        <p class="center" style="margin-top:18px"><a href="{url_for('staff_login')}">← Back to Staff Login</a></p>
    </section>
    """
    return render_page("Forgot Password", body, staff_page=True)

@app.route("/staff/change-password", methods=["GET", "POST"])
@staff_required
def change_password():
    """Change the password of the currently signed-in staff account."""
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not current_password or not new_password or not confirm_password:
            flash("Please fill in all password fields.", "danger")
            return redirect(url_for("change_password"))
        if len(new_password) < 8:
            flash("New password must contain at least 8 characters.", "danger")
            return redirect(url_for("change_password"))
        if new_password != confirm_password:
            flash("The new passwords do not match.", "danger")
            return redirect(url_for("change_password"))
        staff_id = session.get("staff_id")
        connection = db()
        staff = connection.execute(
            "SELECT id, username, password_hash FROM staff WHERE id = ? AND active = 1",
            (staff_id,),
        ).fetchone()
        if staff is None:
            connection.close()
            session.clear()
            flash("Your staff session is no longer valid. Please log in again.", "danger")
            return redirect(url_for("staff_login"))
        if not check_password_hash(staff["password_hash"], current_password):
            connection.close()
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        if check_password_hash(staff["password_hash"], new_password):
            connection.close()
            flash("New password must be different from the current password.", "danger")
            return redirect(url_for("change_password"))
        connection.execute(
            "UPDATE staff SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), staff["id"]),
        )
        durable_commit(connection)
        connection.close()
        audit("password_changed", staff["username"])
        flash("Password changed successfully.", "success")
        return redirect(url_for("staff_dashboard"))
    body = """
    <section class="card centered" style="max-width:620px;margin:45px auto">
        <h1>🔑 Change Password</h1>
        <p class="small">Update the password for your currently signed-in staff account.</p>
        <form method="post" autocomplete="off">
            <label for="current_password">Current Password</label>
            <input id="current_password" type="password" name="current_password" autocomplete="current-password" required>
            <label for="new_password">New Password</label>
            <input id="new_password" type="password" name="new_password" minlength="8" autocomplete="new-password" required>
            <label for="confirm_password">Confirm New Password</label>
            <input id="confirm_password" type="password" name="confirm_password" minlength="8" autocomplete="new-password" required>
            <br>
            <button type="submit">Change Password</button>
        </form>
    </section>
    """
    return render_page("Change Password", body, staff_page=True)
@app.route("/staff/logout", methods=["GET", "POST"])
def logout():
    username = session.get("staff_username", "unknown")
    if session.get("staff_logged_in"):
        audit("logout", username)
    session.clear()
    response = redirect(url_for("home"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    flash("You have been logged out.", "success")
    return response
@app.route("/staff")
@app.route("/staff/dashboard")
@staff_required
def staff_dashboard():
    connection = db()
    counts = {
        "cases": connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "notices": connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0],
        "laws": connection.execute("SELECT COUNT(*) FROM legal_resources").fetchone()[0],
        "views": connection.execute("SELECT COUNT(*) FROM viewer_logs").fetchone()[0],
        "unique_viewers": connection.execute("SELECT COUNT(DISTINCT visitor_id) FROM viewer_logs").fetchone()[0],
    }
    schedule = connection.execute("SELECT file_name FROM schedule WHERE id = 1").fetchone()
    connection.close()
    schedule_text = "Uploaded" if schedule and schedule["file_name"] else tr("not_uploaded")
    body = f"""
    <section class="hero">
        <h1>{tr('welcome')}</h1>
        <p>{esc(tr('signed_in'))} <strong>{esc(session.get('staff_username', ''))}</strong>.</p>
    </section>
    <section class="grid">
        <div class="card stat"><span class="stat-number">{counts['cases']}</span>{tr('cases')}</div>
        <div class="card stat"><span class="stat-number">{counts['notices']}</span>{tr('notices')}</div>
        <div class="card stat"><span class="stat-number">{counts['laws']}</span>{tr('laws')}</div>
        <div class="card stat"><span class="stat-number">{counts['views']}</span>Case Views</div>
        <div class="card stat unique-viewers-stat"><span class="stat-number">{counts['unique_viewers']}</span>Unique Viewers</div>
    </section>
    <section class="card">
        <h2 class="center">Quick Actions</h2>
        <!-- FIRST LINE: Tuesday Calendar, Requirements, Notices, News and Announcements -->
        <div class="staff-quick-row">
            <a class="card centered" href="{url_for('staff_calendar')}">
                <h3>📅 {tr('calendar')}</h3><p>Upload the Tuesday schedule.</p>
            </a>
            <a class="card centered" href="{url_for('staff_requirements')}">
                <h3>📄 {tr('requirements')}</h3><p>Manage public requirements.</p>
            </a>
            <a class="card centered" href="{url_for('staff_notices')}">
                <h3>📢 Notices</h3><p>Manage official court notices.</p>
            </a>
            <a class="card centered" href="{url_for('staff_notices')}">
                <h3>📰 News and Announcements</h3><p>Publish announcements and attachments.</p>
            </a>
        </div>

        <!-- SECOND LINE: Cases full-width bar -->
        <div class="staff-quick-row notice-row">
            <a class="card centered" href="{url_for('staff_cases')}">
                <h3>📋 {tr('cases')}</h3><p>Add, edit and delete cases.</p>
            </a>
        </div>

        <!-- THIRD LINE: Viewer Activity, Staff Accounts, Change Password -->
        <div class="staff-quick-row third-row">
            <a class="card centered" href="{url_for('staff_viewers')}">
                <h3>👁️ Viewer Activity</h3><p>View case viewer counts and viewing times.</p>
            </a>
            {'<a class="card centered" href="' + url_for('staff_accounts') + '"><h3>👥 ' + tr('staff_accounts') + '</h3><p>Add and manage staff accounts.</p></a>' if session.get('staff_role') in {'admin','superadmin'} else ''}
            <a class="card centered" href="{url_for('change_password')}">
                <h3>🔑 Change Password</h3><p>Update your staff account password.</p>
            </a>
        </div>
    </section>
    """
    return render_page(tr("staff_dashboard"), body, staff_page=True)
CASE_STATUSES = ("Archived", "Active", "Terminated")
TERMINATION_REASONS = ("Provisionally Dismissed", "Dismissed", "Decided")


@app.route("/staff/cases")
@staff_required
def staff_cases():
    query = request.args.get("q", "").strip()
    connection = db()
    if query:
        like = f"%{query}%"
        criminal_rows = connection.execute(
            """
            SELECT * FROM cases
            WHERE case_category = 'Criminal'
              AND (case_number LIKE ? OR plaintiff_name LIKE ? OR defendant_name LIKE ?
                   OR parties LIKE ? OR case_type LIKE ? OR status LIKE ?)
            ORDER BY updated_at DESC
            """,
            (like, like, like, like, like, like),
        ).fetchall()
        civil_rows = connection.execute(
            """
            SELECT * FROM cases
            WHERE case_category = 'Civil'
              AND (case_number LIKE ? OR plaintiff_name LIKE ? OR defendant_name LIKE ?
                   OR parties LIKE ? OR case_type LIKE ? OR status LIKE ?)
            ORDER BY updated_at DESC
            """,
            (like, like, like, like, like, like),
        ).fetchall()
    else:
        criminal_rows = connection.execute("SELECT * FROM cases WHERE case_category = 'Criminal' ORDER BY updated_at DESC").fetchall()
        civil_rows = connection.execute("SELECT * FROM cases WHERE case_category = 'Civil' ORDER BY updated_at DESC").fetchall()
    connection.close()

    # Group cases by status first, then sort each status group by case number.
    # This keeps all Archived cases together, all Active cases together, and
    # all Terminated cases together.
    status_order = {status: index for index, status in enumerate(CASE_STATUSES)}

    def case_number_sort_key(row):
        case_number = str(row["case_number"] or "").upper().strip()
        parts = re.split(r"(\d+)", case_number)
        key = []
        for part in parts:
            if part.isdigit():
                key.append((1, int(part)))
            else:
                key.append((0, part))
        return key

    def case_sort_key(row):
        status = str(row["status"] or "Active").strip()
        return (status_order.get(status, len(status_order)), case_number_sort_key(row))

    criminal_rows = sorted(criminal_rows, key=case_sort_key)
    civil_rows = sorted(civil_rows, key=case_sort_key)

    def rows_html(rows, criminal):
        if not rows:
            return f"<tr><td colspan='5' class='empty'>No {'criminal' if criminal else 'civil'} cases.</td></tr>"
        out = ""
        for row in rows:
            party_cell = f"<td>{esc(row['defendant_name'])}</td>" if criminal else ""
            out += f"""
            <tr>
                <td><strong>{esc(row['case_number'])}</strong></td>
                {'' if criminal else f"<td>{esc(row['plaintiff_name'])}</td>"}
                {party_cell}
                <td>{esc(row['case_type'])}</td>
                <td>
                    <span class="status">{esc(row['status'])}</span>
                    {f'<div class="small"><strong>Outcome:</strong> {esc(row["termination_reason"])}</div>' if row["status"] == "Terminated" and row["termination_reason"] else ''}
                </td>
                <td>
                    <a class="button secondary" href="{url_for("staff_edit_case", case_id=row["id"])}">{tr("edit")}</a>
                    <a class="button secondary" href="{url_for('staff_hearing', case_id=row['id'])}">{tr('hearing')}</a>
                    <form method="post" action="{url_for('staff_delete_case', case_id=row['id'])}" style="display:inline">
                        <button class="danger" type="submit" onclick="return confirm('Delete this case permanently?')">{tr('delete')}</button>
                    </form>
                </td>
            </tr>
            """
        return out

    body = f"""
    <section class="card centered">
        <h1>📋 {tr('cases')}</h1>
        <form method="get" action="{url_for('staff_cases')}" style="max-width: 700px; margin: 0 auto 15px;">
            <label>Search Cases</label>
            <input name="q" value="{esc(query)}" placeholder="Case number, plaintiff, or accused" autocomplete="off">
            <div class="actions">
                <button type="submit">🔎 Search</button>
                {('<a class="button secondary" href="' + url_for('staff_cases') + '">Clear</a>') if query else ''}
            </div>
        </form>
        <a class="button" href="{url_for('staff_add_case')}">➕ {tr('add')}</a>
    </section>
    <section class="card"><h2>⚖️ {tr('criminal')} Cases</h2><div class="table-wrap"><table><thead><tr><th>{tr('case_number')}</th><th>{tr('accused')}</th><th>{tr('case_type')}</th><th>{tr('status')}</th><th>Actions</th></tr></thead><tbody>{rows_html(criminal_rows, True)}</tbody></table></div></section>
    <section class="card"><h2>⚖️ {tr('civil')} Cases</h2><div class="table-wrap"><table><thead><tr><th>{tr('case_number')}</th><th>{tr('plaintiff')}</th><th>{tr('case_type')}</th><th>{tr('status')}</th><th>Actions</th></tr></thead><tbody>{rows_html(civil_rows, False)}</tbody></table></div></section>
    """
    return render_page(tr("cases"), body, staff_page=True)
@app.route("/staff/cases/add", methods=["GET", "POST"])
@staff_required
def staff_add_case():
    if request.method == "POST":
        form = request.form
        case_number = form.get("case_number", "").strip()
        category = form.get("case_category", "Civil").strip().title()
        if category not in {"Criminal", "Civil"}:
            category = "Civil"

        plaintiff = form.get("plaintiff", "").strip().upper() if category == "Civil" else ""
        defendant = form.get("defendant", "").strip() if category == "Criminal" else ""

        if not case_number:
            flash("Case number is required.", "danger")
            return redirect(url_for("staff_add_case"))

        if category == "Civil" and not plaintiff:
            flash("Plaintiff name is required for civil cases.", "danger")
            return redirect(url_for("staff_add_case"))
        upper_case_number = case_number.upper()
        if category == "Criminal":
            if not (upper_case_number.startswith("AC") or (upper_case_number.startswith("SC") and not upper_case_number.startswith("SCC"))):
                flash("The criminal case number must start with AC or SC.", "danger")
                return redirect(url_for("staff_add_case"))
        else:
            if not (upper_case_number.startswith("CC") or upper_case_number.startswith("SCC")):
                flash("The civil case number must start with CC or SCC. AC is not allowed for civil cases.", "danger")
                return redirect(url_for("staff_add_case"))
        if category == "Criminal" and not defendant:
            flash("The accused's last name is required for criminal cases.", "danger")
            return redirect(url_for("staff_add_case"))
        connection = db()
        try:
            connection.execute(
                """INSERT INTO cases
                (case_number, plaintiff_name, defendant_name, parties, case_category,
                 case_type, status, termination_reason, internal_notes,
                 public_description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'Active', '', ?, ?, ?, ?)""",
                (
                    upper_case_number,
                    plaintiff,
                    defendant,
                    form.get("parties", "").strip(),
                    category,
                    form.get("case_type", "").strip(),
                    form.get("internal_notes", "").strip(),
                    form.get("public_description", "").strip(),
                    now(),
                    now(),
                ),
            )
            durable_commit(connection)
        except sqlite3.IntegrityError:
            connection.close()
            flash("That case number already exists.", "danger")
            return redirect(url_for("staff_add_case"))
        connection.close()
        audit("case_created", case_number)
        flash("Case created successfully.", "success")
        return redirect(url_for("staff_cases"))
    body = f"""
    <section class="card"><h1 class="center">➕ {tr('add')}</h1>
        <form method="post">
            <label>{tr('case_category')}</label>
            <select name="case_category" id="case_category" onchange="toggleCaseFields()" required>
                <option value="Civil">{tr('civil')}</option>
                <option value="Criminal">{tr('criminal')}</option>
            </select>

            <label>{tr('case_number')}</label>
            <input name="case_number" id="case-number-input" placeholder="CC... or SCC..." required>

            <div id="plaintiff-field">
                <label>Plaintiff's Last Name / Corporation Name</label>
                <input name="plaintiff" id="plaintiff-input" style="text-transform: uppercase" oninput="this.value = this.value.toUpperCase()">
            </div>

            <div id="defendant-field" style="display:none">
                <label>Accused's Last Name</label>
                <input name="defendant" id="defendant-input">
            </div>

            <label>{tr('parties')}</label><input name="parties">
            <label>{tr('case_type')}</label><input name="case_type">
            <label>{tr('description')}</label><textarea name="public_description"></textarea>

            <div class="notice warning">
                <strong>🔒 Staff-Only Notes</strong>
                <p class="small">These notes are private. Only authorized staff can view or edit them. They are never shown on the public case search.</p>
            </div>
            <label>Staff-Only Notes</label><textarea name="internal_notes" placeholder="Private notes for authorized court staff only."></textarea>

            <button type="submit">{tr('save')}</button>
        </form>

        <script>
        function toggleCaseFields() {{
            const category = document.getElementById('case_category').value;
            const plaintiffField = document.getElementById('plaintiff-field');
            const plaintiffInput = document.getElementById('plaintiff-input');
            const defendantField = document.getElementById('defendant-field');
            const defendantInput = document.getElementById('defendant-input');
            const criminal = category === 'Criminal';
            const caseNumberInput = document.getElementById('case-number-input');
            caseNumberInput.placeholder = criminal ? 'AC... or SC...' : 'CC... or SCC...';

            plaintiffField.style.display = criminal ? 'none' : 'block';
            defendantField.style.display = criminal ? 'block' : 'none';
            plaintiffInput.required = !criminal;
            defendantInput.required = criminal;

            if (criminal) {{
                plaintiffInput.value = '';
            }} else {{
                defendantInput.value = '';
            }}
        }}
        toggleCaseFields();
        </script>
    </section>
    """
    return render_page(tr("add"), body, staff_page=True)
@app.route("/staff/cases/<int:case_id>/edit", methods=["GET", "POST"])
@staff_required
def staff_edit_case(case_id):
    connection = db()
    case = connection.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    connection.close()
    if case is None:
        abort(404)
    if request.method == "POST":
        form = request.form
        category = form.get("case_category", "Civil").strip().title()
        if category not in {"Criminal", "Civil"}: category = "Civil"
        case_number = form.get("case_number", "").strip().upper()
        plaintiff = form.get("plaintiff", "").strip().upper() if category == "Civil" else ""
        defendant = form.get("defendant", "").strip() if category == "Criminal" else ""
        if not case_number:
            flash("Case number is required.", "danger")
            return redirect(url_for("staff_edit_case", case_id=case_id))
        if category == "Civil" and not plaintiff:
            flash("Plaintiff name is required for civil cases.", "danger")
            return redirect(url_for("staff_edit_case", case_id=case_id))
        if category == "Criminal" and not defendant:
            flash("The accused's last name is required for criminal cases.", "danger")
            return redirect(url_for("staff_edit_case", case_id=case_id))
        if category == "Criminal":
            if not (case_number.startswith("AC") or (case_number.startswith("SC") and not case_number.startswith("SCC"))):
                flash("The criminal case number must start with AC or SC.", "danger")
                return redirect(url_for("staff_edit_case", case_id=case_id))
        else:
            if not (case_number.startswith("CC") or case_number.startswith("SCC")):
                flash("The civil case number must start with CC or SCC. AC is not allowed for civil cases.", "danger")
                return redirect(url_for("staff_edit_case", case_id=case_id))
        status = form.get("status", "Active").strip()
        if status not in CASE_STATUSES:
            flash("Invalid case status.", "danger")
            return redirect(url_for("staff_edit_case", case_id=case_id))

        termination_reason = form.get("termination_reason", "").strip()
        if status == "Terminated":
            if termination_reason not in TERMINATION_REASONS:
                flash("Please select a termination outcome for a terminated case.", "danger")
                return redirect(url_for("staff_edit_case", case_id=case_id))
        else:
            termination_reason = ""

        internal_notes = form.get("internal_notes", "").strip()

        connection = db()
        try:
            connection.execute(
                """
                UPDATE cases
                SET case_number=?, plaintiff_name=?, defendant_name=?, parties=?,
                    case_category=?, case_type=?, status=?, termination_reason=?,
                    internal_notes=?, public_description=?, updated_at=?
                WHERE id=?
                """,
                (
                    case_number,
                    plaintiff,
                    defendant,
                    form.get("parties", "").strip(),
                    category,
                    form.get("case_type", "").strip(),
                    status,
                    termination_reason,
                    internal_notes,
                    form.get("public_description", "").strip(),
                    now(),
                    case_id,
                ),
            )
            durable_commit(connection)
        except sqlite3.IntegrityError:
            connection.close()
            flash("That case number already exists.", "danger")
            return redirect(url_for("staff_edit_case", case_id=case_id))
        connection.close()
        audit("case_updated", case["case_number"])
        flash("Case updated successfully.", "success")
        return redirect(url_for("staff_cases"))
    criminal = case["case_category"] == "Criminal"
    body = f"""
    <section class="card"><h1 class="center">✏️ {tr('edit')}</h1>
        <form method="post">
            <label>{tr('case_category')}</label><select name="case_category" id="case_category" onchange="toggleCaseFields()"><option value="Civil" {'selected' if not criminal else ''}>{tr('civil')}</option><option value="Criminal" {'selected' if criminal else ''}>{tr('criminal')}</option></select>
            <label>{tr('case_number')}</label><input name="case_number" value="{esc(case['case_number'])}" style="text-transform: uppercase" oninput="this.value = this.value.toUpperCase()" required>
            <div id="plaintiff-field" style="display:{'none' if criminal else 'block'}">
                <label>Plaintiff's Last Name / Corporation Name</label><input name="plaintiff" id="plaintiff-input" style="text-transform: uppercase" oninput="this.value = this.value.toUpperCase()" value="{esc(case['plaintiff_name'])}" {'required' if not criminal else ''}>
            </div>
            <div id="defendant-field" style="display:{'block' if criminal else 'none'}">
                <label>Accused's Last Name</label><input name="defendant" id="defendant-input" value="{esc(case['defendant_name'])}" {'required' if criminal else ''}>
            </div>
            <label>{tr('parties')}</label><input name="parties" value="{esc(case['parties'])}">
            <label>{tr('case_type')}</label><input name="case_type" value="{esc(case['case_type'])}">

            <label>{tr('status')}</label>
            <select name="status" id="case-status" onchange="toggleTerminationFields()" required>
                {''.join(f'<option value="{esc(value)}" {"selected" if value == case["status"] else ""}>{esc(value)}</option>' for value in CASE_STATUSES)}
            </select>

            <div id="termination-fields" style="display:{'block' if case['status'] == 'Terminated' else 'none'}">
                <label>Termination Outcome</label>
                <select name="termination_reason" id="termination-reason">
                    <option value="">Select outcome</option>
                    {''.join(f'<option value="{esc(value)}" {"selected" if value == case["termination_reason"] else ""}>{esc(value)}</option>' for value in TERMINATION_REASONS)}
                </select>
                <p class="small">For terminated cases, select one: Provisionally Dismissed, Dismissed, or Decided.</p>
            </div>

            <label>{tr('description')}</label><textarea name="public_description">{esc(case['public_description'])}</textarea>

            <div class="notice warning">
                <strong>🔒 Staff-Only Notes</strong>
                <p class="small">These notes are private. Only authorized staff can view or edit them. They are never shown on the public case search.</p>
            </div>
            <label>Staff-Only Notes</label>
            <textarea name="internal_notes" placeholder="Private notes for authorized court staff only.">{esc(case['internal_notes'])}</textarea>

            <button type="submit">{tr('save')}</button>
        </form>
        <script>
        function toggleCaseFields() {{
            const criminal = document.getElementById('case_category').value === 'Criminal';
            const plaintiffField = document.getElementById('plaintiff-field');
            const plaintiffInput = document.getElementById('plaintiff-input');
            const defendantField = document.getElementById('defendant-field');
            const defendantInput = document.getElementById('defendant-input');

            plaintiffField.style.display = criminal ? 'none' : 'block';
            defendantField.style.display = criminal ? 'block' : 'none';
            plaintiffInput.required = !criminal;
            defendantInput.required = criminal;
        }}

        function toggleTerminationFields() {{
            const status = document.getElementById('case-status').value;
            const fields = document.getElementById('termination-fields');
            const reason = document.getElementById('termination-reason');
            const terminated = status === 'Terminated';
            fields.style.display = terminated ? 'block' : 'none';
            reason.required = terminated;
            if (!terminated) reason.value = '';
        }}

        toggleCaseFields();
        toggleTerminationFields();
        </script>
    </section>
    """
    return render_page(tr("edit"), body, staff_page=True)
@app.post("/staff/cases/<int:case_id>/delete")
@staff_required
def staff_delete_case(case_id):
    connection = db()
    case = connection.execute(
        "SELECT case_number FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    if case is None:
        connection.close()
        abort(404)
    connection.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    durable_commit(connection)
    connection.close()
    audit("case_deleted", case["case_number"])
    flash("Case deleted successfully.", "success")
    return redirect(url_for("staff_cases"))
@app.route("/staff/cases/<int:case_id>/hearing", methods=["GET", "POST"])
@staff_required
def staff_hearing(case_id):
    connection = db()
    case = connection.execute(
        "SELECT * FROM cases WHERE id = ?",
        (case_id,),
    ).fetchone()
    hearing = connection.execute(
        "SELECT * FROM hearings WHERE case_id = ? ORDER BY id DESC LIMIT 1",
        (case_id,),
    ).fetchone()
    connection.close()
    if case is None:
        abort(404)
    if request.method == "POST":
        form = request.form
        values = (
            form.get("hearing_date", "").strip(),
            form.get("hearing_time", "").strip(),
            form.get("hearing_nature", "").strip(),
            form.get("hearing_status", "Scheduled").strip(),
            form.get("remarks", "").strip(),
        )
        connection = db()
        if hearing:
            connection.execute(
                """
                UPDATE hearings
                SET
                    hearing_date = ?,
                    hearing_time = ?,
                    hearing_nature = ?,
                    hearing_status = ?,
                    remarks = ?
                WHERE id = ?
                """,
                values + (hearing["id"],),
            )
        else:
            connection.execute(
                """
                INSERT INTO hearings
                (case_id, hearing_date, hearing_time, hearing_nature, hearing_status, remarks)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (case_id,) + values,
            )
        durable_commit(connection)
        connection.close()
        audit("hearing_updated", case["case_number"])
        flash("Hearing updated successfully.", "success")
        return redirect(url_for("staff_hearing", case_id=case_id))
    date_value = hearing["hearing_date"] if hearing else ""
    time_value = hearing["hearing_time"] if hearing else ""
    nature_value = hearing["hearing_nature"] if hearing else "Initial Hearing"
    status_value = hearing["hearing_status"] if hearing else "Scheduled"
    remarks_value = hearing["remarks"] if hearing else ""
    natures = [
        "Initial Hearing",
        "Arraignment",
        "Pre-Trial Conference/Preliminary Conference",
        "Trial",
        "Motion",
        "Compliance",
        "Judgment",
        "Promulgation",
        "Clarificatory Hearing",
        "Other",
    ]
    statuses = [
        "Scheduled",
        "Ongoing",
        "Completed",
        "Reset",
        "Cancelled",
    ]
    nature_options = "".join(
        f"<option {'selected' if value == nature_value else ''}>{esc(value)}</option>"
        for value in natures
    )
    status_options = "".join(
        f"<option {'selected' if value == status_value else ''}>{esc(value)}</option>"
        for value in statuses
    )
    delete_hearing_button = ""
    if hearing:
        delete_hearing_button = (
            f"<form method='post' action='{url_for('staff_delete_hearing', case_id=case_id)}' class='actions'>"
            f"<button class='danger' type='submit' onclick='return confirm(&quot;Delete this hearing information?&quot;)'>{tr('delete')} Hearing</button>"
            "</form>"
        )
    body = f"""
    <section class="card">
        <h1 class="center">📅 {tr('hearing')}</h1>
        <p class="center"><strong>{esc(case['case_number'])}</strong> · {esc(case['defendant_name'] if case['case_category'] == 'Criminal' else case['plaintiff_name'])}</p>
        <form method="post">
            <label>{tr('hearing_date')}</label>
            <input type="date" name="hearing_date" value="{esc(date_value)}" required>
            <label>{tr('hearing_time')}</label>
            <input type="time" name="hearing_time" value="{esc(time_value)}">
            <label>{tr('hearing_nature')}</label>
            <select name="hearing_nature">{nature_options}</select>
            <label>{tr('hearing_status')}</label>
            <select name="hearing_status">{status_options}</select>
            <label>{tr('remarks')}</label>
            <textarea name="remarks">{esc(remarks_value)}</textarea>
            <button type="submit">{tr('save')}</button>
        </form>
        {delete_hearing_button}
    </section>
    """
    return render_page(tr("hearing"), body, staff_page=True)

@app.post("/staff/cases/<int:case_id>/hearing/delete")
@staff_required
def staff_delete_hearing(case_id):
    connection = db()
    case = connection.execute("SELECT case_number FROM cases WHERE id = ?", (case_id,)).fetchone()
    hearing = connection.execute("SELECT id FROM hearings WHERE case_id = ? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    if case is None:
        connection.close()
        abort(404)
    if hearing is None:
        connection.close()
        flash("No hearing information to delete.", "warning")
        return redirect(url_for("staff_hearing", case_id=case_id))
    connection.execute("DELETE FROM hearings WHERE id = ?", (hearing["id"],))
    durable_commit(connection)
    connection.close()
    audit("hearing_deleted", case["case_number"])
    flash("Hearing information deleted successfully.", "success")
    return redirect(url_for("staff_hearing", case_id=case_id))

@app.route("/staff/calendar")
@staff_required
def staff_calendar():
    connection = db()
    schedule = connection.execute(
        "SELECT * FROM schedule WHERE id = 1"
    ).fetchone()
    connection.close()
    current = "<p class='small'>No schedule uploaded yet.</p>"
    delete_link = ""
    if schedule and schedule["file_name"]:
        url = url_for("uploaded_file", filename=schedule["file_name"])
        extension = schedule["file_type"] or ""
        if extension == "pdf":
            current = f"<iframe class='schedule-pdf' src='{url}' title='Current Tuesday schedule'></iframe>"
        elif extension in IMAGE_EXTENSIONS:
            current = f"<img class='schedule-image' src='{url}' alt='Current Tuesday schedule'>"
        else:
            current = f"<p><a class='button secondary' href='{url}'>{tr('open')}</a></p>"
        delete_link = (
            f"<form method='post' action='{url_for('delete_schedule')}' style='display:inline'>"
            f"<button class='danger' type='submit' onclick=\"return confirm('Delete the Tuesday schedule?')\">{tr('delete')}</button>"
            f"</form>"
        )
    body = f"""
    <section class="card centered">
        <h1>📅 {tr('calendar')}</h1>
        <p>
            Upload one Tuesday schedule as an image or PDF.
            Civilians will see the latest published schedule.
        </p>
    </section>
    <section class="card">
        <h2 class="center">Upload / Replace Tuesday Schedule</h2>
        <form method="post" action="{url_for('upload_schedule')}" enctype="multipart/form-data">
            <label>{tr('upload')}</label>
            <input type="file" name="schedule" accept=".pdf,.png,.jpg,.jpeg,.webp,.gif" required>
            <button type="submit">{tr('upload')}</button>
        </form>
    </section>
    <section class="card">
        <h2 class="center">Current Schedule</h2>
        {current}
        <div class="actions">{delete_link}</div>
    </section>
    """
    return render_page(tr("calendar"), body, staff_page=True)
@app.post("/staff/calendar/upload")
@staff_required
def upload_schedule():
    file = request.files.get("schedule")
    try:
        filename, original, extension = save_upload(file)
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_calendar"))
    if not filename:
        flash("Please select a schedule file.", "danger")
        return redirect(url_for("staff_calendar"))
    connection = db()
    old = connection.execute(
        "SELECT file_name FROM schedule WHERE id = 1"
    ).fetchone()
    connection.execute(
        """
        INSERT INTO schedule
        (id, file_name, original_filename, file_type, updated_at, uploaded_by)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            file_name = excluded.file_name,
            original_filename = excluded.original_filename,
            file_type = excluded.file_type,
            updated_at = excluded.updated_at,
            uploaded_by = excluded.uploaded_by
        """,
        (
            filename,
            original,
            extension,
            now(),
            session.get("staff_username", ""),
        ),
    )
    durable_commit(connection)
    connection.close()
    if old and old["file_name"] and old["file_name"] != filename:
        delete_uploaded_file(old["file_name"])
    audit("schedule_uploaded", original or filename)
    flash("Tuesday schedule uploaded successfully.", "success")
    return redirect(url_for("staff_calendar"))
@app.post("/staff/calendar/delete")
@staff_required
def delete_schedule():
    connection = db()
    row = connection.execute(
        "SELECT file_name FROM schedule WHERE id = 1"
    ).fetchone()
    connection.execute("DELETE FROM schedule WHERE id = 1")
    durable_commit(connection)
    connection.close()
    if row and row["file_name"]:
        delete_uploaded_file(row["file_name"])
    audit("schedule_deleted", "Tuesday schedule")
    flash("Tuesday schedule deleted.", "success")
    return redirect(url_for("staff_calendar"))
@app.route("/staff/notices")
@staff_required
def staff_notices():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM notices ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        attachment = ""
        if row["attachment"]:
            attachment = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['attachment'])}'>"
                f"📎 {tr('open')}</a></p>"
            )
        cards += f"""
        <article class="notice">
            <h3>{esc(row['title_en'])}</h3>
            <p>{esc(row['body_en'])}</p>
            {attachment}
            <form method="post" action="{url_for('delete_notice', notice_id=row['id'])}" style="display:inline">
                <button class="danger" type="submit" onclick="return confirm('Delete this notice?')">{tr('delete')}</button>
            </form>
        </article>
        """
    body = f"""
    <section class="card">
        <h1 class="center">📢 {tr('notices')}</h1>
        <form method="post" action="{url_for('add_notice')}" enctype="multipart/form-data">
            <label>English Title</label>
            <input name="title_en" required>
            <label>Filipino Title</label>
            <input name="title_fil" required>
            <label>English Notice</label>
            <textarea name="body_en" required></textarea>
            <label>Filipino Notice</label>
            <textarea name="body_fil" required></textarea>
            <label>{tr('attachment')}</label>
            <input type="file" name="attachment" accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.doc,.docx">
            <button type="submit">{tr('upload')}</button>
        </form>
    </section>
    <section class="card">
        {cards or '<p class="empty">No notices yet.</p>'}
    </section>
    """
    return render_page(tr("notices"), body, staff_page=True)
@app.post("/staff/notices/add")
@staff_required
def add_notice():
    form = request.form
    values = (
        form.get("title_en", "").strip(),
        form.get("title_fil", "").strip(),
        form.get("body_en", "").strip(),
        form.get("body_fil", "").strip(),
    )
    if not all(values):
        flash("Complete all notice fields.", "danger")
        return redirect(url_for("staff_notices"))
    try:
        filename, original, _ = save_upload(request.files.get("attachment"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_notices"))
    connection = db()
    connection.execute(
        """
        INSERT INTO notices
        (title_en, title_fil, body_en, body_fil, attachment,
         original_filename, published, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        values + (filename, original, now(), now()),
    )
    durable_commit(connection)
    connection.close()
    audit("notice_created", values[0])
    flash("Notice published successfully.", "success")
    return redirect(url_for("staff_notices"))
@app.post("/staff/notices/<int:notice_id>/delete")
@staff_required
def delete_notice(notice_id):
    connection = db()
    row = connection.execute(
        "SELECT attachment FROM notices WHERE id = ?",
        (notice_id,),
    ).fetchone()
    connection.execute(
        "DELETE FROM notices WHERE id = ?",
        (notice_id,),
    )
    durable_commit(connection)
    connection.close()
    if row:
        delete_uploaded_file(row["attachment"])
    audit("notice_deleted", notice_id)
    flash("Notice deleted.", "success")
    return redirect(url_for("staff_notices"))
@app.route("/laws")
def public_laws():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM legal_resources ORDER BY created_at DESC"
    ).fetchall()
    connection.close()

    cards = ""
    for row in rows:
        links = ""
        if row["source_url"]:
            links += (
                f"<a class='button secondary' href='{esc(row['source_url'])}' target='_blank' rel='noopener noreferrer'>"
                f"{tr('official_source')}</a> "
            )
        if row["file_name"]:
            links += (
                f"<a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"{tr('open')}</a> "
            )
        cards += f"""
        <article class="notice">
            <span class="status">{esc(row['category'])}</span>
            <h3>{esc(row['title'])}</h3>
            <p>{esc(row['description'])}</p>
            {links}
        </article>
        """

    body = f"""
    <section class="card centered">
        <h1>⚖️ {tr('laws')}</h1>
        <p>Publicly available laws, decisions and rules.</p>
        <div class="notice warning">
            Official court records and certified documents should be obtained from the court.
        </div>
    </section>
    <section class="card">
        {cards or '<p class="empty">No legal resources have been published yet.</p>'}
    </section>
    """
    return render_page(tr("laws"), body)

@app.route("/staff/laws")
@staff_required
def staff_laws():
    connection = db()
    rows = connection.execute(
        "SELECT * FROM legal_resources ORDER BY created_at DESC"
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        links = ""
        if row["source_url"]:
            links += (
                f"<a class='button secondary' href='{esc(row['source_url'])}' target='_blank' rel='noopener noreferrer'>"
                f"{tr('official_source')}</a> "
            )
        if row["file_name"]:
            links += (
                f"<a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"{tr('open')}</a> "
            )
        cards += f"""
        <article class="notice">
            <span class="status">{esc(row['category'])}</span>
            <h3>{esc(row['title'])}</h3>
            <p>{esc(row['description'])}</p>
            {links}
            <form method="post" action="{url_for('delete_law', law_id=row['id'])}" style="display:inline">
                <button class="danger" type="submit">{tr('delete')}</button>
            </form>
        </article>
        """
    body = f"""
    <section class="card">
        <h1 class="center">⚖️ {tr('laws')}</h1>
        <form method="post" action="{url_for('add_law')}" enctype="multipart/form-data">
            <label>Category</label>
            <select name="category">
                <option>Philippine Laws</option>
                <option>Supreme Court Decisions</option>
                <option>Rules of Court</option>
                <option>Supreme Court Rules</option>
                <option>Administrative Matters</option>
                <option>Other Official Resource</option>
            </select>
            <label>Title</label>
            <input name="title" required>
            <label>Description</label>
            <textarea name="description"></textarea>
            <label>Official Source URL</label>
            <input type="url" name="source_url">
            <label>Document</label>
            <input type="file" name="file">
            <button type="submit">{tr('add')}</button>
        </form>
    </section>
    <section class="card">
        {cards or '<p class="empty">No legal resources yet.</p>'}
    </section>
    """
    return render_page(tr("laws"), body, staff_page=True)
@app.post("/staff/laws/add")
@staff_required
def add_law():
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required.", "danger")
        return redirect(url_for("staff_laws"))
    try:
        filename, original, _ = save_upload(request.files.get("file"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_laws"))
    connection = db()
    connection.execute(
        """
        INSERT INTO legal_resources
        (category, title, description, source_url, file_name,
         original_filename, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.form.get("category", "").strip(),
            title,
            request.form.get("description", "").strip(),
            request.form.get("source_url", "").strip(),
            filename,
            original,
            now(),
            now(),
        ),
    )
    durable_commit(connection)
    connection.close()
    audit("legal_resource_created", title)
    flash("Legal resource added.", "success")
    return redirect(url_for("staff_laws"))
@app.post("/staff/laws/<int:law_id>/delete")
@staff_required
def delete_law(law_id):
    connection = db()
    row = connection.execute(
        "SELECT file_name FROM legal_resources WHERE id = ?",
        (law_id,),
    ).fetchone()
    connection.execute(
        "DELETE FROM legal_resources WHERE id = ?",
        (law_id,),
    )
    durable_commit(connection)
    connection.close()
    if row:
        delete_uploaded_file(row["file_name"])
    audit("legal_resource_deleted", law_id)
    flash("Legal resource deleted.", "success")
    return redirect(url_for("staff_laws"))
@app.route("/staff/requirements")
@staff_required
def staff_requirements():
    connection = db()
    rows = connection.execute(
        """
        SELECT * FROM requirements
        ORDER BY CASE category WHEN 'bond' THEN 1 WHEN 'clearance' THEN 2 ELSE 3 END
        """
    ).fetchall()
    connection.close()
    cards = ""
    for row in rows:
        title = row["title_fil"] if lang_value() == "fil" else row["title_en"]
        description = row["description_fil"] if lang_value() == "fil" else row["description_en"]
        checklist = ""
        if row["category"] == "bond":
            checklist = "<ol class='requirement-list'>" + "".join(
                f"<li>{esc(item)}</li>" for item in BOND_REQUIREMENTS
            ) + "</ol>"
        file_link = ""
        if row["file_name"]:
            file_link = (
                f"<p><a class='button secondary' href='{url_for('uploaded_file', filename=row['file_name'])}'>"
                f"{tr('open')}</a></p>"
            )
        cards += f"""
        <article class="card">
            <h2>{esc(title)}</h2>
            {checklist}
            <p class="small">{esc(description or tr('not_uploaded'))}</p>
            <form method="post" action="{url_for('update_requirement', category=row['category'])}" enctype="multipart/form-data">
                <label>Description</label>
                <textarea name="description">{esc(description)}</textarea>
                <label>Official Document</label>
                <input type="file" name="document">
                <button type="submit">{tr('save')}</button>
            </form>
            {file_link}
        </article>
        """
    body = f"""
    <section class="card centered">
        <h1>📄 {tr('requirements')}</h1>
        <p>Update the public requirements information.</p>
    </section>
    {cards}
    """
    return render_page(tr("requirements"), body, staff_page=True)
@app.post("/staff/requirements/<category>/update")
@staff_required
def update_requirement(category):
    if category not in {"bond", "clearance"}:
        abort(404)
    description = request.form.get("description", "").strip()
    try:
        filename, original, _ = save_upload(request.files.get("document"))
    except ValueError as error:
        flash(str(error), "danger")
        return redirect(url_for("staff_requirements"))
    connection = db()
    if filename:
        connection.execute(
            """
            UPDATE requirements
            SET description_en = ?, description_fil = ?,
                file_name = ?, original_filename = ?, updated_at = ?
            WHERE category = ?
            """,
            (
                description,
                description,
                filename,
                original,
                now(),
                category,
            ),
        )
    else:
        connection.execute(
            """
            UPDATE requirements
            SET description_en = ?, description_fil = ?, updated_at = ?
            WHERE category = ?
            """,
            (
                description,
                description,
                now(),
                category,
            ),
        )
    durable_commit(connection)
    connection.close()
    audit("requirement_updated", category)
    flash("Requirement updated.", "success")
    return redirect(url_for("staff_requirements"))
# Private Super Admin Notepad
@app.route("/staff/private-notepad", methods=["GET", "POST"])
@superadmin_required
def private_notepad():
    if request.method == "POST":
        content = request.form.get("content", "")
        connection = db()
        connection.execute(
            "UPDATE private_notepad SET content = ?, updated_at = ?, updated_by = ? WHERE id = 1",
            (content, now(), session.get("staff_username", "26-0054")),
        )
        durable_commit(connection)
        connection.close()
        audit("private_notepad_saved", "superadmin")
        flash("Private note saved.", "success")
        return redirect(url_for("private_notepad"))
    connection = db()
    note = connection.execute("SELECT content, updated_at, updated_by FROM private_notepad WHERE id = 1").fetchone()
    connection.close()
    content = note["content"] if note else ""
    updated_at = note["updated_at"] if note else ""
    updated_by = note["updated_by"] if note else ""
    body = f"""
    <section class="hero">
        <h1>📝 Private Notepad</h1>
        <p><strong>SUPER ADMIN ONLY</strong></p>
        <p class="small">This note is restricted to the Super Admin account and is stored in the court database.</p>
    </section>
    <section class="card" style="max-width:1000px;margin:0 auto">
        <form method="post" autocomplete="off">
            <textarea name="content" style="min-height:480px;width:100%;resize:vertical" placeholder="Write anything here...">{esc(content)}</textarea>
            <div class="actions" style="justify-content:center">
                <button type="submit">💾 Save Private Note</button>
                <a class="button secondary" href="{url_for('superadmin_dashboard')}">Back to Super Admin</a>
            </div>
        </form>
        <p class="small center">Last saved: {esc(updated_at)} by {esc(updated_by or '—')}</p>
    </section>
    """
    return render_page("Private Notepad", body, staff_page=True)

@app.route("/staff/viewers")
@staff_required
def staff_viewers():
    connection = db()
    summary_rows = connection.execute(
        """
        SELECT case_id, case_number, case_category,
               COUNT(*) AS total_views,
               COUNT(DISTINCT visitor_id) AS unique_viewers,
               MAX(viewed_at) AS last_viewed
        FROM viewer_logs
        GROUP BY case_id, case_number, case_category
        ORDER BY last_viewed DESC
        """
    ).fetchall()
    recent_rows = connection.execute(
        """
        SELECT case_number, case_category, viewed_at
        FROM viewer_logs
        ORDER BY id DESC
        LIMIT 100
        """
    ).fetchall()
    connection.close()
    summary_table = "".join(
        f"<tr><td>{esc(r['case_number'])}</td><td>{esc(r['case_category'])}</td>"
        f"<td>{r['unique_viewers']}</td><td>{r['total_views']}</td><td>{esc(r['last_viewed'])}</td></tr>"
        for r in summary_rows
    )
    recent_table = "".join(
        f"<tr><td>{esc(r['case_number'])}</td><td>{esc(r['case_category'])}</td><td>{esc(r['viewed_at'])}</td></tr>"
        for r in recent_rows
    )
    body = f"""
    <section class="hero">
        <h1>👁️ Viewer Activity</h1>
        <p>Case-view statistics for authorized staff. Visitor identity and technical details are restricted to Super Admin.</p>
    </section>
    <section class="viewer-definition">
        <h3>What do Unique Views and Total Views mean?</h3>
        <p><strong>Unique Views:</strong> the number of different tracked visitors who viewed a case. Repeated visits from the same visitor are counted only once.</p>
        <p><strong>Total Views:</strong> the total number of recorded case-page views, including repeated visits from the same visitor.</p>
        <p><strong>Example:</strong> If Visitor A opens a case 3 times and Visitor B opens it once, there are <strong>2 Unique Views</strong> and <strong>4 Total Views</strong>.</p>
    </section>
    <section class="card table-wrap">
        <h2 class="center">Case Viewer Summary</h2>
        <table><thead><tr><th>Case Number</th><th>Category</th><th>Unique Viewers</th><th>Total Views</th><th>Last Viewed</th></tr></thead>
        <tbody>{summary_table or '<tr><td colspan="5">No public case views yet.</td></tr>'}</tbody></table>
    </section>
    <section class="card table-wrap">
        <h2 class="center">Recent Case Views</h2>
        <table><thead><tr><th>Case Number</th><th>Category</th><th>Viewed At (Philippine Time)</th></tr></thead>
        <tbody>{recent_table or '<tr><td colspan="3">No public case views yet.</td></tr>'}</tbody></table>
    </section>
    """
    return render_page("Viewer Activity", body, staff_page=True)

@app.route("/staff/super-admin")
@superadmin_required
def superadmin_dashboard():
    connection = db()
    counts = {
        "staff": connection.execute("SELECT COUNT(*) FROM staff").fetchone()[0],
        "cases": connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "hearings": connection.execute("SELECT COUNT(*) FROM hearings").fetchone()[0],
        "notices": connection.execute("SELECT COUNT(*) FROM notices").fetchone()[0],
        "laws": connection.execute("SELECT COUNT(*) FROM legal_resources").fetchone()[0],
        "requirements": connection.execute("SELECT COUNT(*) FROM requirements").fetchone()[0],
        "audit": connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0],
        "views": connection.execute("SELECT COUNT(*) FROM viewer_logs").fetchone()[0],
        "unique_viewers": connection.execute("SELECT COUNT(DISTINCT visitor_id) FROM viewer_logs").fetchone()[0],
    }
    staff_rows = connection.execute(
        "SELECT username, role, active FROM staff ORDER BY username"
    ).fetchall()
    case_rows = connection.execute(
        "SELECT case_number, plaintiff_name, defendant_name, case_category, status, updated_at FROM cases ORDER BY updated_at DESC LIMIT 100"
    ).fetchall()
    audit_rows = connection.execute(
        "SELECT username, action, target, created_at FROM audit_logs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    viewer_rows = connection.execute(
        """
        SELECT case_number, case_category, visitor_id, viewed_at, ip_address, user_agent, referrer
        FROM viewer_logs
        ORDER BY id DESC LIMIT 200
        """
    ).fetchall()
    visitor_summary_rows = connection.execute(
        """
        SELECT visitor_id,
               COUNT(*) AS total_views,
               COUNT(DISTINCT case_id) AS cases_viewed,
               MIN(viewed_at) AS first_viewed,
               MAX(viewed_at) AS last_viewed,
               MAX(ip_address) AS ip_address,
               MAX(user_agent) AS user_agent,
               MAX(referrer) AS referrer
        FROM viewer_logs
        GROUP BY visitor_id
        ORDER BY last_viewed DESC
        LIMIT 200
        """
    ).fetchall()
    connection.close()
    staff_table = "".join(
        f"<tr><td>{esc(r['username'])}</td><td>{esc(r['role'])}</td><td>{'Active' if r['active'] else 'Disabled'}</td></tr>"
        for r in staff_rows
    )
    case_table = "".join(
        f"<tr><td>{esc(r['case_number'])}</td><td>{esc(r['plaintiff_name'])}</td><td>{esc(r['defendant_name']) if r['case_category'] == 'Criminal' else ''}</td><td>{esc(r['status'])}</td><td>{esc(r['updated_at'])}</td></tr>"
        for r in case_rows
    )
    audit_table = "".join(
        f"<tr><td>{esc(r['username'])}</td><td>{esc(r['action'])}</td><td>{esc(r['target'])}</td><td>{esc(r['created_at'])}</td></tr>"
        for r in audit_rows
    )
    viewer_table = "".join(
        f"<tr><td>{esc(r['case_number'])}</td><td>{esc(r['case_category'])}</td>"
        f"<td>{esc(r['visitor_id'])}</td><td>{esc(r['viewed_at'])}</td><td>{esc(r['ip_address'])}</td>"
        f"<td>{esc(r['user_agent'])}</td><td>{esc(r['referrer']) or 'Direct'}</td></tr>"
        for r in viewer_rows
    )
    visitor_summary_table = "".join(
        f"<tr><td>{esc(r['visitor_id'])}</td><td>{r['total_views']}</td>"
        f"<td>{r['cases_viewed']}</td><td>{esc(r['first_viewed'])}</td>"
        f"<td>{esc(r['last_viewed'])}</td><td>{esc(r['ip_address'])}</td>"
        f"<td>{esc(r['user_agent'])}</td><td>{esc(r['referrer']) or 'Direct'}</td></tr>"
        for r in visitor_summary_rows
    )
    body = f"""
    <section class="hero">
        <h1>🛡️ Super Admin</h1>
        <p><strong>Hello everyone, hahahaha. 😈</strong></p>
        <p class="small">Full system overview for the authorized super administrator. Passwords and reset tokens are never displayed.</p>
    </section>
    <section class="grid">
        {''.join(f'<div class="card stat"><span class="stat-number">{value}</span>{label}</div>' for label, value in [("Staff Accounts", counts["staff"]),("Cases", counts["cases"]),("Hearings", counts["hearings"]),("Announcements", counts["notices"]),("Legal Resources", counts["laws"]),("Requirements", counts["requirements"]),("Audit Entries", counts["audit"]),("Case Views", counts["views"]),("Unique Viewers", counts["unique_viewers"])])}
    </section>
    <section class="card table-wrap">
        <h2 class="center">Registered Accounts</h2>
        <table><thead><tr><th>Username</th><th>Role</th><th>Status</th></tr></thead><tbody>{staff_table or '<tr><td colspan="3">None</td></tr>'}</tbody></table>
    </section>
    <section class="card table-wrap">
        <h2 class="center">Case Overview</h2>
        <table><thead><tr><th>Case Number</th><th>Plaintiff</th><th>Defendant</th><th>Status</th><th>Updated</th></tr></thead><tbody>{case_table or '<tr><td colspan="5">No cases</td></tr>'}</tbody></table>
    </section>
    <section class="card centered">
        <h2>🔒 Private Super Admin Area</h2>
        <p>This area is unavailable to normal Admin and Staff accounts.</p>
        <p><a class="button" href="{url_for('private_notepad')}">📝 Open Private Notepad</a></p>
    </section>
    <section class="card superadmin-tabs-card">
        <div class="superadmin-tabs" role="tablist" aria-label="Super Admin sections">
            <button type="button" class="superadmin-tab active" onclick="showSuperAdminTab('overview-tab', this)">System Overview</button>
            <button type="button" class="superadmin-tab" onclick="showSuperAdminTab('viewer-tab', this)">👁️ Viewer Information</button>
            <button type="button" class="superadmin-tab" onclick="showSuperAdminTab('audit-tab', this)">Audit Activity</button>
        </div>
        <div id="overview-tab" class="superadmin-tab-panel active">
            <h2 class="center">System Overview</h2>
            <p class="center small">Registered accounts, case status, and private Super Admin tools.</p>
        </div>
        <div id="viewer-tab" class="superadmin-tab-panel">
            <h2 class="center">🔎 Detailed Viewer Information</h2>
            <p class="small">Super Admin only. This tab shows anonymous visitor information collected when a public case page is opened. Timestamps are Philippine Time. The system records an anonymous visitor ID, number of views, cases viewed, first/last viewing time, IP address, browser/device information, and referrer.</p>
            <div class="grid viewer-detail-stats">
                <div class="card stat"><span class="stat-number">{counts['views']}</span>Total Case Views</div>
                <div class="card stat"><span class="stat-number">{counts['unique_viewers']}</span>Unique Visitors</div>
                <div class="card stat"><span class="stat-number">{len(visitor_summary_rows)}</span>Tracked Visitor IDs</div>
            </div>
            <section class="card table-wrap">
                <h3 class="center">Visitor Summary</h3>
                <table><thead><tr><th>Visitor ID</th><th>Total Views</th><th>Cases Viewed</th><th>First Viewed</th><th>Last Viewed</th><th>IP Address</th><th>Browser / Device</th><th>Referrer</th></tr></thead>
                <tbody>{visitor_summary_table or '<tr><td colspan="8">No public case views yet.</td></tr>'}</tbody></table>
            </section>
            <section class="card table-wrap">
                <h3 class="center">Detailed View Log</h3>
                <table><thead><tr><th>Case</th><th>Category</th><th>Visitor ID</th><th>Viewed At</th><th>IP Address</th><th>Browser / Device</th><th>Referrer</th></tr></thead>
                <tbody>{viewer_table or '<tr><td colspan="7">No public case views yet.</td></tr>'}</tbody></table>
            </section>
        </div>
        <div id="audit-tab" class="superadmin-tab-panel">
            <h2 class="center">Recent Audit Activity</h2>
            <div class="table-wrap"><table><thead><tr><th>User</th><th>Action</th><th>Target</th><th>Time</th></tr></thead><tbody>{audit_table or '<tr><td colspan="4">No audit activity</td></tr>'}</tbody></table></div>
        </div>
    </section>
    <script>
    function showSuperAdminTab(tabId, button) {{
        document.querySelectorAll('.superadmin-tab-panel').forEach(function(panel) {{ panel.classList.remove('active'); }});
        document.querySelectorAll('.superadmin-tab').forEach(function(tab) {{ tab.classList.remove('active'); }});
        var panel = document.getElementById(tabId);
        if (panel) panel.classList.add('active');
        if (button) button.classList.add('active');
    }}
    </script>
    """
    return render_page("Super Admin", body, staff_page=True)

@app.route("/staff/accounts")
@admin_required
def staff_accounts():
    connection = db()
    if session.get("staff_role") == "superadmin":
        rows = connection.execute(
            "SELECT id, username, role, active FROM staff ORDER BY username"
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT id, username, role, active FROM staff WHERE lower(username) <> ? ORDER BY username",
            ("26-0054",),
        ).fetchall()
    connection.close()
    table = ""
    for row in rows:
        controls = (
            f"<form method='post' action='{url_for('toggle_staff', staff_id=row['id'])}' style='display:inline'>"
            f"<button type='submit'>{'Disable' if row['active'] else 'Enable'}</button>"
            f"</form>"
        )
        if row["username"].lower() not in {"admin", "26-0054"}:
            controls += (
                f" <form method='post' action='{url_for('delete_staff', staff_id=row['id'])}' style='display:inline'>"
                f"<button class='danger' type='submit' onclick=\"return confirm('Delete this account?')\">{tr('delete')}</button>"
                f"</form>"
            )
        reset_html = ""
        if session.get("staff_role") == "superadmin":
            reset_html = f"""
            <form method="post" action="{url_for('reset_staff_password', staff_id=row['id'])}" style="margin-top:8px">
                <input type="password" name="new_password" minlength="8" placeholder="New password" required autocomplete="new-password">
                <input type="password" name="confirm_password" minlength="8" placeholder="Confirm password" required autocomplete="new-password">
                <button type="submit">Reset Password</button>
            </form>
            """
        table += f"""
        <tr>
            <td>{esc(row['username'])}</td>
            <td>{esc(row['role'])}</td>
            <td><span class="status">{'Active' if row['active'] else 'Disabled'}</span></td>
            <td>{controls}{reset_html}</td>
        </tr>
        """
    body = f"""
    <section class="card">
        <h1 class="center">👥 {tr('staff_accounts')}</h1>
        {"<p class='small'>Super Admin can reset account passwords. Passwords are securely hashed and cannot be displayed.</p>" if session.get("staff_role") == "superadmin" else ""}
        <form method="post" action="{url_for('add_staff')}" autocomplete="off">
            <label>{tr('email')}</label>
            <input type="email" name="email" required>
            <label>{tr('username')}</label>
            <input name="username" required>
            <label>{tr('password')}</label>
            <input type="password" name="password" minlength="8" required autocomplete="new-password">
            <label>Role</label>
            <select name="role"><option value="staff">Staff</option><option value="admin">Administrator</option></select>
            <button type="submit">{tr('add')}</button>
        </form>
    </section>
    <section class="card table-wrap">
        <table>
            <thead><tr><th>Username</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{table}</tbody>
        </table>
    </section>
    """
    return render_page(tr("staff_accounts"), body, staff_page=True)
@app.post("/staff/accounts/add")
@admin_required
def add_staff():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "staff")
    if role not in {"staff", "admin"}:
        role = "staff"
    if not username or not email or not password:
        flash("Username, email and password are required.", "danger")
        return redirect(url_for("staff_accounts"))
    if len(password) < 8:
        flash("Password must contain at least 8 characters.", "danger")
        return redirect(url_for("staff_accounts"))
    connection = db()
    try:
        connection.execute(
            """
            INSERT INTO staff
            (username, email, password_hash, role, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                username,
                email,
                generate_password_hash(password),
                role,
                now(),
            ),
        )
        durable_commit(connection)
    except sqlite3.IntegrityError:
        connection.close()
        flash("That username or email already exists.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.close()
    audit("staff_created", username)
    flash("Staff account created successfully.", "success")
    return redirect(url_for("staff_accounts"))
@app.post("/staff/accounts/<int:staff_id>/toggle")
@admin_required
def toggle_staff(staff_id):
    connection = db()
    row = connection.execute(
        "SELECT username, active FROM staff WHERE id = ?",
        (staff_id,),
    ).fetchone()
    if row is None:
        connection.close()
        abort(404)
    if row["username"].lower() in {"admin", "26-0054"}:
        connection.close()
        flash("A protected administrator account cannot be disabled.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.execute(
        "UPDATE staff SET active = ? WHERE id = ?",
        (0 if row["active"] else 1, staff_id),
    )
    durable_commit(connection)
    connection.close()
    return redirect(url_for("staff_accounts"))
@app.route("/staff/accounts/<int:staff_id>/reset-password", methods=["POST"])
@superadmin_required
def reset_staff_password(staff_id):
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if len(new_password) < 8:
        flash("Password must contain at least 8 characters.", "danger")
        return redirect(url_for("staff_accounts"))
    if new_password != confirm_password:
        flash("The passwords do not match.", "danger")
        return redirect(url_for("staff_accounts"))
    connection = db()
    row = connection.execute("SELECT id, username FROM staff WHERE id = ?", (staff_id,)).fetchone()
    if row is None:
        connection.close()
        abort(404)
    connection.execute("UPDATE staff SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), staff_id))
    durable_commit(connection)
    connection.close()
    audit("superadmin_password_reset", row["username"])
    flash(f"Password reset successfully for {row['username']}.", "success")
    return redirect(url_for("staff_accounts"))

@app.post("/staff/accounts/<int:staff_id>/delete")
@admin_required
def delete_staff(staff_id):
    connection = db()
    row = connection.execute(
        "SELECT username FROM staff WHERE id = ?",
        (staff_id,),
    ).fetchone()
    if row is None:
        connection.close()
        abort(404)
    if row["username"].lower() in {"admin", "26-0054"}:
        connection.close()
        flash("A protected administrator account cannot be deleted.", "danger")
        return redirect(url_for("staff_accounts"))
    connection.execute(
        "DELETE FROM staff WHERE id = ?",
        (staff_id,),
    )
    durable_commit(connection)
    connection.close()
    flash("Staff account deleted.", "success")
    return redirect(url_for("staff_accounts"))
@app.route("/language/<language>")
def change_language(language):
    if language not in T:
        language = "en"
    session["language"] = language
    return redirect(request.referrer or url_for("home"))
@app.route("/theme/<theme>")
def change_theme(theme):
    if theme not in {"light", "dark"}:
        theme = "light"
    session["theme"] = theme
    return redirect(request.referrer or url_for("home"))
@app.route("/health")
def health():
    return {
        "status": "ok",
        "service": COURT_NAME,
        "mongodb": {
            "configured": bool(MONGODB_URI),
            "connected": bool(MONGO_READY),
            "database": MONGODB_DB_NAME if MONGODB_URI else "",
            "last_sync": MONGO_LAST_SYNC,
            "error": MONGO_ERROR,
        },
    }
@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
@app.errorhandler(403)
def error_403(error):
    body = """
    <section class="card centered">
        <h1>403</h1>
        <h2>Access Denied</h2>
        <p>You do not have permission to access this page.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("403", body, staff_page=bool(session.get("staff_logged_in"))), 403
@app.errorhandler(404)
def error_404(error):
    body = """
    <section class="card centered">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>The requested page could not be found.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("404", body, staff_page=bool(session.get("staff_logged_in"))), 404
@app.errorhandler(413)
def error_413(error):
    body = """
    <section class="card centered">
        <h1>413</h1>
        <h2>File Too Large</h2>
        <p>The maximum upload size is 25 MB.</p>
        <a class="button" href="/">Home</a>
    </section>
    """
    return render_page("413", body, staff_page=bool(session.get("staff_logged_in"))), 413
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
