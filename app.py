from flask import Flask, render_template_string, send_from_directory, send_file, abort, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import mimetypes
from functools import wraps
from datetime import datetime, timedelta
import time
import csv
import io

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
import gridfs
from bson import ObjectId
from uuid import uuid4
import re
from bson.errors import InvalidId

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

viewer_count = 0

# Staff sessions expire after 5 minutes of inactivity.
STAFF_SESSION_TIMEOUT = timedelta(minutes=5)
app.config["PERMANENT_SESSION_LIFETIME"] = STAFF_SESSION_TIMEOUT
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

# =========================================================
# LOGIN / GALLERY / MONGODB SETTINGS
# =========================================================

app.secret_key = os.environ.get(
    "JHR_SECRET_KEY",
    "change-this-secret-key"
)

# MongoDB Atlas example:
# mongodb+srv://USERNAME:PASSWORD@CLUSTER.mongodb.net/?retryWrites=true&w=majority
# Local MongoDB example:
# mongodb://127.0.0.1:27017/
# Render sometimes receives environment values with accidental surrounding
# quotes when they are pasted into the dashboard. Remove only those outer
# quotes; do not modify the actual MongoDB URI contents.
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
if len(MONGO_URI) >= 2 and MONGO_URI[0] == MONGO_URI[-1] and MONGO_URI[0] in {"\"", "'"}:
    MONGO_URI = MONGO_URI[1:-1].strip()

if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is missing. Add MONGO_URI to Render Environment Variables "
        "using your MongoDB Atlas connection string."
    )

MONGO_DB_NAME = os.environ.get(
    "MONGO_DB_NAME",
    "jhr_database"
)

GALLERY_FOLDER = os.path.abspath(os.path.join(app.static_folder, "gallery"))
NEWS_FOLDER = os.path.abspath(os.path.join(app.static_folder, "news_uploads"))
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
os.makedirs(GALLERY_FOLDER, exist_ok=True)
os.makedirs(NEWS_FOLDER, exist_ok=True)


# =========================================================
# MONGODB CONNECTION
# =========================================================

def connect_mongodb():
    """Connect to MongoDB Atlas with retries so Render cold starts are reliable."""
    last_error = None
    is_srv = MONGO_URI.lower().startswith("mongodb+srv://")

    for attempt in range(1, 7):
        try:
            client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=30000,
                retryWrites=True,
                tls=is_srv,
                appname="JHR-Website"
            )
            client.admin.command("ping")
            db = client[MONGO_DB_NAME]
            return client, db
        except PyMongoError as exc:
            last_error = exc
            app.logger.warning(
                "MongoDB connection attempt %s/6 failed: %s", attempt, exc
            )
            if attempt < 6:
                time.sleep(3)

    raise RuntimeError(
        "JHR could not connect to MongoDB Atlas after 6 attempts. "
        "The Python dependencies and Flask app started correctly. "
        "Check MongoDB Atlas Network Access (allow the Render service), "
        "Database Access credentials, and the exact MONGO_URI value in Render."
    ) from last_error


mongo_client, mongo_db = connect_mongodb()

staff_accounts_collection = mongo_db["staff_accounts"]
class_messages_collection = mongo_db["class_messages"]
news_collection = mongo_db["news_items"]
gallery_collection = mongo_db["gallery_items"]
viewers_collection = mongo_db["viewers"]
audit_collection = mongo_db["superadmin_audit"]

staff_accounts_collection.create_index("username", unique=True)
gallery_collection.create_index("filename", unique=True)
# Viewer IDs are generated for new visitors, but older records may not have a viewer_id.
# Keep this index non-unique so legacy null/missing viewer_id records cannot crash startup.
viewers_collection.create_index("viewer_id", name="viewer_id_lookup", unique=False)
viewers_collection.create_index([("last_seen", -1)])

# MongoDB GridFS stores uploaded gallery images permanently in Atlas.
# Render's local filesystem is ephemeral, so uploaded photos must not rely on it.
gallery_fs = gridfs.GridFS(mongo_db, collection="gallery_files")


def parse_user_agent(user_agent):
    """Return a simple, readable browser/device/OS summary without extra dependencies."""
    ua = user_agent or ""

    if re.search(r"Edg/", ua):
        browser = "Microsoft Edge"
    elif re.search(r"OPR/|Opera", ua):
        browser = "Opera"
    elif re.search(r"Chrome/", ua) and not re.search(r"Edg/", ua):
        browser = "Google Chrome"
    elif re.search(r"Firefox/", ua):
        browser = "Mozilla Firefox"
    elif re.search(r"Safari/", ua) and not re.search(r"Chrome/", ua):
        browser = "Safari"
    else:
        browser = "Other / Unknown browser"

    if re.search(r"Windows NT", ua):
        operating_system = "Windows"
    elif re.search(r"Android", ua):
        operating_system = "Android"
    elif re.search(r"iPhone|iPad|iPod", ua):
        operating_system = "iOS / iPadOS"
    elif re.search(r"Mac OS X", ua):
        operating_system = "macOS"
    elif re.search(r"Linux", ua):
        operating_system = "Linux"
    else:
        operating_system = "Other / Unknown OS"

    if re.search(r"Mobile|Android|iPhone|iPod", ua):
        device = "Mobile"
    elif re.search(r"iPad|Tablet", ua):
        device = "Tablet"
    else:
        device = "Desktop / Laptop"

    return {
        "browser": browser,
        "operating_system": operating_system,
        "device": device,
    }


def get_client_ip():
    """Get the visitor IP, including the forwarded IP used by Render/proxies."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "Unknown"


def track_viewer(page="/"):
    """Atomically record one page view for a stable anonymous browser ID."""
    viewer_id = request.cookies.get("jhr_viewer_id")
    if not viewer_id or not re.fullmatch(r"[a-f0-9]{32}", viewer_id):
        viewer_id = uuid4().hex

    now = now_string()
    device_info = parse_user_agent(request.headers.get("User-Agent", ""))
    client_ip = get_client_ip()

    # One atomic upsert prevents simultaneous requests from creating duplicate
    # records for the same browser. $setOnInsert preserves the first visit/IP.
    viewers_collection.update_one(
        {"viewer_id": viewer_id},
        {
            "$set": {
                "last_seen": now,
                "last_page": page,
                "last_ip": client_ip,
                **device_info,
            },
            "$setOnInsert": {
                "viewer_id": viewer_id,
                "first_seen": now,
                "first_ip": client_ip,
            },
            "$inc": {"total_views": 1},
        },
        upsert=True,
    )
    return viewer_id, True


def detailed_viewers():
    """Return organized viewer records for the staff viewer area."""
    records = []
    for doc in viewers_collection.find().sort("last_seen", -1):
        viewer_id = doc.get("viewer_id", "")
        records.append({
            "id": viewer_id[-8:].upper() if viewer_id else "UNKNOWN",
            "full_id": viewer_id,
            "first_seen": doc.get("first_seen", ""),
            "last_seen": doc.get("last_seen", ""),
            "total_views": int(doc.get("total_views", 0)),
            "last_page": doc.get("last_page", "/"),
            "first_ip": doc.get("first_ip", doc.get("last_ip", "Unknown")),
            "last_ip": doc.get("last_ip", "Unknown"),
            "device": doc.get("device", "Unknown"),
            "browser": doc.get("browser", "Unknown"),
            "operating_system": doc.get("operating_system", "Unknown"),
        })
    return records


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_mongodb():
    # Default staff login:
    # username = admin
    # password = ChangeMe123!
    admin_account = staff_accounts_collection.find_one({"username": "admin"})
    if not admin_account:
        try:
            staff_accounts_collection.insert_one({
                "username": "admin",
                "password": generate_password_hash("ChangeMe123!"),
                "created_at": now_string()
            })
        except DuplicateKeyError:
            pass
    else:
        # Keep the requested default admin password active for the existing admin account.
        staff_accounts_collection.update_one(
            {"_id": admin_account["_id"]},
            {"$set": {"password": generate_password_hash("ChangeMe123!")}}
        )

    superadmin_username = "26-0054"
    superadmin = staff_accounts_collection.find_one({"username": superadmin_username})
    if not superadmin:
        try:
            staff_accounts_collection.insert_one({"username": superadmin_username, "password": generate_password_hash("ThisWasHugo"), "role": "superadmin", "created_at": now_string()})
        except DuplicateKeyError:
            pass
    else:
        staff_accounts_collection.update_one({"_id": superadmin["_id"]}, {"$set": {"role": "superadmin", "password": generate_password_hash("ThisWasHugo")}})


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def uploaded_image_response(folder, filename):
    """Safely serve an uploaded image with the correct MIME type."""
    safe_name = os.path.basename(filename or "")
    if not safe_name or not allowed_file(safe_name):
        abort(404)

    root = os.path.abspath(folder)
    filepath = os.path.abspath(os.path.join(root, safe_name))

    if not filepath.startswith(root + os.sep) or not os.path.isfile(filepath):
        abort(404)

    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        abort(404)

    response = send_file(filepath, mimetype=mime_type, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def normalize_staff(doc):
    return {
        "id": str(doc["_id"]),
        "username": doc.get("username", ""),
        "role": doc.get("role", "staff"),
        "created_at": doc.get("created_at", "")
    }


def audit_superadmin(action, details=""):
    try:
        audit_collection.insert_one({
            "action": str(action)[:160],
            "details": str(details)[:500],
            "username": session.get("staff_username", ""),
            "created_at": now_string(),
        })
    except Exception as exc:
        app.logger.warning("Superadmin audit log failed: %s", exc)


def normalize_audit(doc):
    return {
        "action": doc.get("action", ""),
        "details": doc.get("details", ""),
        "username": doc.get("username", ""),
        "created_at": doc.get("created_at", ""),
    }


def normalize_message(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "email": doc.get("email", ""),
        "message": doc.get("message", ""),
        "created_at": doc.get("created_at", "")
    }


def news_items():
    items = []
    for doc in news_collection.find().sort("created_at", -1):
        author = ""
        author_id = doc.get("author_id")
        if author_id:
            try:
                author_doc = staff_accounts_collection.find_one({"_id": ObjectId(author_id)})
                if author_doc:
                    author = author_doc.get("username", "")
            except (InvalidId, TypeError):
                pass

        image_files = [
            name for name in doc.get("images", [])
            if name and os.path.isfile(os.path.join(NEWS_FOLDER, os.path.basename(name)))
        ]

        items.append({
            "id": str(doc["_id"]),
            "kind": doc.get("kind", "Announcement"),
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "created_at": doc.get("created_at", ""),
            "author": author,
            "images": image_files
        })
    return items


def migrate_local_gallery_files_to_gridfs():
    """Move any gallery files still on disk into MongoDB GridFS."""
    if not os.path.isdir(GALLERY_FOLDER):
        return

    for filename in os.listdir(GALLERY_FOLDER):
        if not allowed_file(filename):
            continue

        filepath = os.path.join(GALLERY_FOLDER, filename)
        if not os.path.isfile(filepath):
            continue

        doc = gallery_collection.find_one({"filename": filename})
        try:
            if doc and doc.get("gridfs_id"):
                continue

            with open(filepath, "rb") as local_file:
                gridfs_id = gallery_fs.put(
                    local_file,
                    filename=filename,
                    content_type=mimetypes.guess_type(filename)[0] or "application/octet-stream"
                )

            if doc:
                gallery_collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"gridfs_id": gridfs_id}}
                )
            else:
                gallery_collection.insert_one({
                    "filename": filename,
                    "original_filename": filename,
                    "title": os.path.splitext(filename)[0][:160],
                    "description": "Imported picture",
                    "created_at": now_string(),
                    "gridfs_id": gridfs_id
                })
        except Exception:
            app.logger.exception("Could not migrate gallery file %s to GridFS", filename)


def gallery_images():
    """Return all gallery metadata, including persistent GridFS images."""
    migrate_local_gallery_files_to_gridfs()
    images = []

    for doc in gallery_collection.find().sort("created_at", 1):
        filename = doc.get("filename")
        if not filename:
            continue

        gridfs_id = doc.get("gridfs_id")
        local_exists = os.path.isfile(os.path.join(GALLERY_FOLDER, os.path.basename(filename)))
        if not gridfs_id and not local_exists:
            # An old ephemeral Render file may already be gone. Keep the
            # metadata out of the public gallery until a file exists.
            continue

        images.append({
            "id": str(doc.get("_id", "")),
            "filename": filename,
            "title": doc.get("title") or os.path.splitext(filename)[0],
            "description": doc.get("description") or "Imported picture"
        })

    return images


init_mongodb()


# =========================================================
# AUTOMATIC IMAGE ROUTE
# =========================================================
#
# The website can request:
#
# /media/IMG_12345
#
# and this route will automatically look for:
#
# IMG_12345
# IMG_12345.jpg
# IMG_12345.jpeg
# IMG_12345.png
# IMG_12345.webp
#
# This prevents image-extension problems.
# =========================================================

IMAGE_EXTENSIONS = [
    "",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
]


@app.route("/media/<path:image_name>")
def media(image_name):

    # Prevent directory traversal.
    image_name = os.path.basename(image_name)

    # If the filename already includes an extension,
    # first try it exactly as provided.
    supplied_extension = os.path.splitext(image_name)[1]

    if supplied_extension:

        possible_files = [
            image_name
        ]

    else:

        possible_files = [
            image_name + extension
            for extension in IMAGE_EXTENSIONS
        ]

    for filename in possible_files:

        filepath = os.path.join(
            app.static_folder,
            filename
        )

        if os.path.isfile(filepath):

            return send_from_directory(
                app.static_folder,
                filename,
                max_age=86400
            )

    abort(404)


# =========================================================
# WEBSITE
# =========================================================

STAFF_DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JHR | Staff Dashboard</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;background:#10131a;color:#fff;padding:30px}
.wrap{max-width:1100px;margin:auto}
.card{background:#191e28;border:1px solid #303746;border-radius:18px;padding:24px;margin:0 0 22px;box-shadow:0 12px 35px rgba(0,0,0,.18)}
h1,h2{margin-top:0}
input,textarea,select{width:100%;padding:13px;border:1px solid #3c4658;border-radius:11px;background:#0f131a;color:#fff;margin:7px 0 12px;font:inherit}
textarea{min-height:130px;resize:vertical}
button{border:0;border-radius:11px;padding:12px 17px;background:linear-gradient(135deg,#7c3aed,#c026d3);color:#fff;cursor:pointer;font-weight:800}
a{color:#b894ff}
.message{border-top:1px solid #303746;padding:16px 0}
.message:first-child{border-top:0}
.meta{color:#aab4c2;font-size:14px}
.notice{padding:12px;border-radius:10px;background:#241d3c;margin-bottom:8px}
.staff-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0}.staff-tab{background:#0f131a;border:1px solid #303746;color:#cbd5e1;padding:11px 15px;border-radius:10px;cursor:pointer;font-weight:800}.staff-tab.active{background:linear-gradient(135deg,#7c3aed,#c026d3);color:#fff;border-color:transparent}.staff-panel{display:none}.staff-panel.active{display:block}.viewer-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:18px 0}.viewer-summary>div{background:#0f131a;border:1px solid #303746;border-radius:14px;padding:16px}.viewer-summary strong{display:block;font-size:24px;color:#fff}.viewer-summary span{display:block;margin-top:5px;color:#aab4c2;font-size:13px}.viewer-table-wrap{overflow:auto;border:1px solid #303746;border-radius:14px}.viewer-table{width:100%;min-width:1350px;border-collapse:collapse}.viewer-table th,.viewer-table td{padding:12px 13px;text-align:left;border-bottom:1px solid #303746;vertical-align:top}.viewer-table th{background:#0f131a;color:#d8c9ff;font-size:13px;position:sticky;top:0}.viewer-table td{font-size:13px}.viewer-table tr:last-child td{border-bottom:0}.viewer-table code{color:#cfc4ff}.viewer-table tbody tr:hover{background:#202631}.ip-cell{font-family:monospace;color:#e9d5ff;font-weight:700}.viewer-detail{font-size:12px;color:#aab4c2;margin-top:4px}
@media(max-width:800px){.viewer-summary{grid-template-columns:1fr}.viewer-table{min-width:1350px}}

.who-are-we-cards{display:flex;justify-content:center;align-items:center}
.who-we-are-box{width:min(950px,100%);margin:0 auto;text-align:center}
.who-we-are-box p{margin:0;text-align:center;font-weight:700;text-indent:2em;line-height:1.9}
.who-we-are-box p + p{margin-top:32px}


/* JHR PREMIUM STAFF UI */
body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Arial,sans-serif!important;background:radial-gradient(circle at 10% 0%,rgba(139,92,246,.18),transparent 28%),linear-gradient(180deg,#0b0712,#170d24)!important;padding:28px!important;color:#fff!important}
.wrap{max-width:1280px!important}.card{background:rgba(27,18,42,.78)!important;border:1px solid rgba(196,160,255,.16)!important;border-radius:24px!important;box-shadow:0 22px 65px rgba(0,0,0,.28)!important;backdrop-filter:blur(18px)!important}.staff-tabs{gap:10px!important}.staff-tab{border:1px solid rgba(196,160,255,.15)!important;border-radius:14px!important;background:rgba(255,255,255,.045)!important;padding:12px 16px!important;transition:.2s ease!important}.staff-tab:hover{transform:translateY(-2px)!important;background:rgba(139,92,246,.15)!important}.staff-tab.active{background:linear-gradient(135deg,#7c3aed,#db2777)!important;box-shadow:0 12px 30px rgba(124,58,237,.25)!important}.viewer-summary>div{border-radius:18px!important;background:rgba(255,255,255,.045)!important;border-color:rgba(196,160,255,.13)!important}.viewer-table-wrap{border-radius:18px!important;border-color:rgba(196,160,255,.13)!important}.viewer-table th{background:#130b1f!important}.notice{border:1px solid rgba(196,160,255,.15)!important;background:rgba(124,58,237,.12)!important;border-radius:14px!important}.secret-tab{background:linear-gradient(135deg,rgba(234,179,8,.12),rgba(124,58,237,.14))!important}.account-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:13px 0;border-bottom:1px solid rgba(196,160,255,.1)}.account-row .meta{display:block;margin-top:4px}.danger-mini{background:#b42318!important}.secret-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}.secret-grid>div{padding:16px;border-radius:16px;background:rgba(255,255,255,.045);border:1px solid rgba(196,160,255,.12)}.secret-grid strong{font-size:25px;display:block}.secret-grid span{color:#aab4c2;font-size:13px}.secret-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.secret-health{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:16px}.secret-health>div{padding:12px;border:1px solid rgba(124,58,237,.14);border-radius:14px;background:rgba(124,58,237,.05)}.secret-health span{display:block;color:var(--muted);font-size:.75rem}.secret-health strong{display:block;margin-top:4px}.secret-danger-zone{margin-top:18px;padding:16px;border:1px solid rgba(239,68,68,.22);border-radius:16px;background:rgba(239,68,68,.04)}.secret-danger-zone h3{margin:0 0 4px}.secret-danger-zone form{margin-top:10px}@media(max-width:700px){.secret-health{grid-template-columns:1fr}}
.secret-note{margin-top:16px;padding:12px;border-radius:12px;background:rgba(234,179,8,.08);color:#f3d98a}@media(max-width:800px){.secret-grid,.secret-actions{grid-template-columns:1fr}}

/* Viewer analytics contrast fix: keep every value readable on the dark dashboard */
#panel-viewers, #panel-viewers p, #panel-viewers label, #panel-viewers td,
#panel-viewers th, #panel-viewers strong, #panel-viewers span, #panel-viewers code,
#panel-viewers .viewer-detail { color: #f5f3ff !important; }
#panel-viewers .meta, #panel-viewers .viewer-summary span,
#panel-viewers .viewer-detail { color: #c4b8d8 !important; }
#panel-viewers .viewer-table th { color: #e9d5ff !important; background: #130b1f !important; }
#panel-viewers .viewer-table td { background: rgba(15, 10, 25, .28); }
#panel-viewers .viewer-table tbody tr:hover td { background: rgba(124, 58, 237, .16) !important; }
#panel-viewers .ip-cell { color: #f0abfc !important; }
#panel-viewers .viewer-table code { color: #ddd6fe !important; overflow-wrap: anywhere; }





/* Shared gallery event upload fields */
.gallery-upload{max-width:760px!important;padding:30px!important}
.gallery-upload-header{display:flex;align-items:center;gap:16px;text-align:left;margin-bottom:24px}
.gallery-upload-icon{width:58px;height:58px;display:grid;place-items:center;border-radius:18px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;font-size:28px;box-shadow:0 12px 25px rgba(124,58,237,.25);flex:0 0 auto}
.gallery-upload-header h3{margin:0 0 5px;font-size:1.55rem}
.gallery-upload-header p{margin:0;color:var(--muted);line-height:1.55}
.gallery-upload-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 24px}
.gallery-step{padding:14px;border:1px solid rgba(124,58,237,.14);background:rgba(124,58,237,.055);border-radius:16px;text-align:left;display:grid;grid-template-columns:auto 1fr;column-gap:10px;align-items:center}
.gallery-step span{grid-row:span 2;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:#7c3aed;color:#fff;font-weight:900}
.gallery-step strong{font-size:.92rem}.gallery-step small{color:var(--muted);font-size:.78rem}
.gallery-input-section{padding:18px;margin:14px 0;border:1px solid rgba(124,58,237,.14);border-radius:18px;background:rgba(255,255,255,.48);text-align:left}
body.dark .gallery-input-section{background:rgba(20,20,35,.35)}
.gallery-input-heading{display:flex;gap:11px;align-items:flex-start;margin-bottom:13px}
.gallery-input-number{width:28px;height:28px;display:grid;place-items:center;border-radius:9px;background:linear-gradient(135deg,#7c3aed,#ec4899);color:#fff;font-weight:900;flex:0 0 auto}
.gallery-input-heading strong{display:block;font-size:1rem}.gallery-input-heading small{display:block;color:var(--muted);margin-top:2px;line-height:1.4}
.gallery-input-section input[type=text],.gallery-input-section textarea{width:100%;box-sizing:border-box;border:1px solid rgba(109,40,217,.2);border-radius:14px;padding:14px 15px;background:rgba(255,255,255,.92);color:var(--text);font:inherit;outline:none;transition:.2s;resize:vertical}
body.dark .gallery-input-section input[type=text],body.dark .gallery-input-section textarea{background:rgba(15,15,25,.8)}
.gallery-input-section input[type=text]:focus,.gallery-input-section textarea:focus{border-color:#8b5cf6;box-shadow:0 0 0 4px rgba(139,92,246,.12)}
.gallery-dropzone{min-height:155px;border:2px dashed #a855f7;border-radius:18px;background:linear-gradient(135deg,rgba(124,58,237,.06),rgba(236,72,153,.05));display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;text-align:center;cursor:pointer;transition:.2s;padding:18px;box-sizing:border-box}
.gallery-dropzone:hover,.gallery-dropzone.is-dragging{border-color:#ec4899;background:linear-gradient(135deg,rgba(124,58,237,.12),rgba(236,72,153,.1));transform:translateY(-1px)}
.gallery-dropzone input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
.gallery-drop-icon{font-size:30px}.gallery-dropzone strong{font-size:1.05rem}.gallery-dropzone span{color:var(--muted)}.gallery-dropzone small{color:var(--muted);margin-top:5px}
.gallery-selection{margin:14px 0 0;text-align:left}.gallery-selection-top{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:10px;padding:10px 12px;border-radius:12px;background:rgba(124,58,237,.07)}.gallery-selection-top span{font-size:.8rem;color:var(--muted);text-align:right}.gallery-selection-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.gallery-selection-item{padding:9px 11px;border-radius:12px;background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.1);display:flex;gap:9px;align-items:center;min-width:0}.gallery-selection-item>span{font-size:18px}.gallery-selection-item div{min-width:0}.gallery-selection-item strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.84rem}.gallery-selection-item small{display:block;color:var(--muted);font-size:.73rem;margin-top:2px}.gallery-upload-summary{display:flex;gap:11px;align-items:center;margin:16px 0;padding:13px 15px;border-radius:14px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.16);text-align:left}.gallery-upload-summary>span{font-size:21px}.gallery-upload-summary strong{display:block}.gallery-upload-summary small{display:block;color:var(--muted);margin-top:2px}.gallery-main-submit{width:100%;padding:15px!important;font-size:1rem;box-shadow:0 12px 25px rgba(124,58,237,.2)}
.sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:700px){.gallery-upload{padding:20px!important}.gallery-upload-steps{grid-template-columns:1fr}.gallery-selection-list{grid-template-columns:1fr}.gallery-selection-top{flex-direction:column;align-items:flex-start}.gallery-selection-top span{text-align:left}.gallery-upload-header{align-items:flex-start}}

/* =====================================================
   THEME + READABILITY FIX
   Keep light mode readable and make dark mode apply consistently.
===================================================== */
:root{
  color-scheme:light;
  --jhr-ink:#171225;
  --jhr-muted:#6d6680;
  --jhr-solid:#ffffff;
  --jhr-surface:rgba(255,255,255,.78);
  --jhr-line:rgba(111,76,190,.16);
}
body.dark{
  color-scheme:dark;
  --text:#f7f3ff;
  --muted:#c7bdd4;
  --background:#0b0712;
  --card:#1b1228;
  --border:rgba(196,160,255,.20);
  --jhr-ink:#f7f3ff;
  --jhr-muted:#c7bdd4;
  --jhr-solid:#1b1228;
  --jhr-surface:rgba(27,18,42,.88);
  --jhr-line:rgba(196,160,255,.20);
}

/* Light-mode text that was accidentally left white */
body:not(.dark) .card:not(.mission-card):not(.color-section),
body:not(.dark) .news-card,
body:not(.dark) .project-mini-card,
body:not(.dark) .service-card,
body:not(.dark) .owner-card,
body:not(.dark) .gallery-card,
body:not(.dark) .game,
body:not(.dark) .contact,
body:not(.dark) .gallery-upload,
body:not(.dark) .gallery-input-section,
body:not(.dark) .gallery-selection-item,
body:not(.dark) .gallery-selection-top,
body:not(.dark) .gallery-upload-summary{
  color:var(--jhr-ink);
}
body:not(.dark) .card:not(.mission-card) h1,
body:not(.dark) .card:not(.mission-card) h2,
body:not(.dark) .card:not(.mission-card) h3,
body:not(.dark) .card:not(.mission-card) h4,
body:not(.dark) .news-card h3,
body:not(.dark) .project-mini-card h3,
body:not(.dark) .service-card h3,
body:not(.dark) .owner-card h3,
body:not(.dark) .gallery-card h3,
body:not(.dark) .gallery-upload h3,
body:not(.dark) .gallery-input-heading strong,
body:not(.dark) .gallery-step strong,
body:not(.dark) .gallery-selection-item strong,
body:not(.dark) .gallery-upload-summary strong{
  color:var(--jhr-ink)!important;
}
body:not(.dark) .card:not(.mission-card) p,
body:not(.dark) .news-card p,
body:not(.dark) .project-mini-card p,
body:not(.dark) .service-card p,
body:not(.dark) .owner-card p,
body:not(.dark) .gallery-card p,
body:not(.dark) .gallery-upload-header p,
body:not(.dark) .gallery-step small,
body:not(.dark) .gallery-input-heading small,
body:not(.dark) .gallery-dropzone span,
body:not(.dark) .gallery-dropzone small,
body:not(.dark) .gallery-selection-top span,
body:not(.dark) .gallery-selection-item small,
body:not(.dark) .gallery-upload-summary small{
  color:var(--jhr-muted)!important;
}

/* Inputs */
body:not(.dark) input,
body:not(.dark) textarea,
body:not(.dark) select{
  color:#24113f!important;
  background:#fff!important;
}
body.dark input,
body.dark textarea,
body.dark select{
  color:#f7f3ff!important;
  background:#15101f!important;
  border-color:var(--jhr-line)!important;
}
body.dark input::placeholder,
body.dark textarea::placeholder{color:#9f94ad!important}

/* Dark mode for common cards/forms */
body.dark .card,body.dark .mission-card,body.dark .service-card,body.dark .project-mini-card,body.dark .news-card,body.dark .owner-card,body.dark .gallery-card,body.dark .game,body.dark .contact,body.dark .gallery-upload,body.dark .gallery-input-section{
  color:#f7f3ff!important;
}
body.dark .card:not(.mission-card) p,body.dark .news-card p,body.dark .project-mini-card p,body.dark .service-card p,body.dark .owner-card p,body.dark .gallery-card p,body.dark .gallery-upload-header p,body.dark .gallery-step small,body.dark .gallery-input-heading small,body.dark .gallery-dropzone span,body.dark .gallery-dropzone small{
  color:#c7bdd4!important;
}
body.dark .gallery-input-section{background:rgba(27,18,42,.72)!important;border-color:var(--jhr-line)!important}
body.dark .gallery-input-section input[type=text],body.dark .gallery-input-section textarea{background:#15101f!important;color:#f7f3ff!important}
body.dark .gallery-selection-item,body.dark .gallery-selection-top{background:rgba(139,92,246,.09)!important;color:#f7f3ff!important}

/* Make theme switch visible */
#themeBtn,#langBtn{color:var(--jhr-ink)!important}
body.dark #themeBtn,body.dark #langBtn{color:#fff!important}




/* Refined viewer analytics: clearer hierarchy, softer surfaces, and responsive layout */
#panel-viewers{position:relative;overflow:hidden;padding:clamp(18px,3vw,32px)!important}
#panel-viewers:before{content:"";position:absolute;inset:0 0 auto;height:5px;background:linear-gradient(90deg,#8b5cf6,#ec4899,#38bdf8);pointer-events:none}
#panel-viewers h2{display:flex;align-items:center;gap:10px;font-size:clamp(1.35rem,2.4vw,1.9rem);letter-spacing:-.035em;margin-bottom:8px;color:#fff!important}
#panel-viewers h2:after{content:"LIVE ANALYTICS";font-size:10px;letter-spacing:.13em;font-weight:800;color:#ddd6fe;background:rgba(139,92,246,.15);border:1px solid rgba(196,181,253,.24);padding:6px 9px;border-radius:999px;margin-left:auto}
#panel-viewers>p.meta{max-width:850px;line-height:1.75;color:#c4b8d8!important;margin:0 0 24px}
#panel-viewers .viewer-summary{grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:22px 0 26px}
#panel-viewers .viewer-summary>div{position:relative;min-height:126px;padding:22px!important;overflow:hidden;border-radius:20px!important;background:linear-gradient(145deg,rgba(139,92,246,.15),rgba(255,255,255,.035))!important;border:1px solid rgba(196,181,253,.19)!important;box-shadow:0 12px 32px rgba(0,0,0,.13);transition:transform .2s ease,border-color .2s ease}
#panel-viewers .viewer-summary>div:hover{transform:translateY(-3px);border-color:rgba(196,181,253,.42)!important}
#panel-viewers .viewer-summary>div:after{content:"";position:absolute;width:90px;height:90px;right:-35px;top:-35px;border-radius:50%;background:rgba(196,181,253,.07)}
#panel-viewers .viewer-summary strong{font-size:clamp(1.7rem,3vw,2.35rem);line-height:1.2;letter-spacing:-.045em;color:#fff!important;overflow-wrap:anywhere}
#panel-viewers .viewer-summary span{font-size:12px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;color:#c4b8d8!important;line-height:1.5}
#panel-viewers .viewer-summary>div:last-child strong{font-size:clamp(1rem,1.8vw,1.35rem);letter-spacing:0;line-height:1.5}
#panel-viewers .viewer-table-wrap{background:rgba(10,7,18,.48)!important;border:1px solid rgba(196,181,253,.18)!important;border-radius:20px!important;box-shadow:inset 0 1px rgba(255,255,255,.025);scrollbar-color:#7c3aed #171020;scrollbar-width:thin}
#panel-viewers .viewer-table{min-width:1280px;border-collapse:separate;border-spacing:0}
#panel-viewers .viewer-table th{padding:15px 16px!important;background:#1a1028!important;color:#dcd0ff!important;font-size:11px;text-transform:uppercase;letter-spacing:.09em;border-bottom:1px solid rgba(196,181,253,.2)!important;white-space:nowrap}
#panel-viewers .viewer-table th:first-child{border-top-left-radius:12px}
#panel-viewers .viewer-table td{padding:16px!important;background:rgba(20,13,32,.45)!important;color:#f5f3ff!important;border-bottom:1px solid rgba(196,181,253,.09)!important;line-height:1.55;font-size:13px;max-width:240px;overflow-wrap:anywhere}
#panel-viewers .viewer-table tbody tr:nth-child(even) td{background:rgba(139,92,246,.035)!important}
#panel-viewers .viewer-table tbody tr:hover td{background:rgba(139,92,246,.14)!important}
#panel-viewers .viewer-table tbody tr:last-child td{border-bottom:0!important}
#panel-viewers .viewer-table td:first-child strong{display:inline-block;color:#fff!important;background:rgba(139,92,246,.17);border:1px solid rgba(196,181,253,.17);padding:6px 9px;border-radius:9px;white-space:nowrap}
#panel-viewers .viewer-table td:nth-child(4) strong{display:inline-flex;align-items:center;justify-content:center;min-width:34px;padding:5px 9px;border-radius:9px;background:rgba(34,197,94,.12);color:#86efac!important;border:1px solid rgba(134,239,172,.15)}
#panel-viewers .viewer-table code{display:inline-block;padding:4px 7px;border-radius:7px;background:rgba(139,92,246,.12);font-size:12px;color:#ddd6fe!important}
#panel-viewers .ip-cell{color:#f0abfc!important;font-weight:700}
#panel-viewers .viewer-detail{color:#c4b8d8!important;line-height:1.5}
#panel-viewers .viewer-table-wrap+ p{padding:28px 18px;text-align:center;color:#c4b8d8!important;background:rgba(139,92,246,.06);border:1px dashed rgba(196,181,253,.2);border-radius:16px}
@media(max-width:800px){body{padding:14px!important}#panel-viewers .viewer-summary{grid-template-columns:1fr;gap:10px}#panel-viewers .viewer-summary>div{min-height:100px;padding:18px!important}#panel-viewers h2{flex-wrap:wrap}#panel-viewers h2:after{margin-left:0}#panel-viewers .viewer-table{min-width:1180px}}
@media(prefers-reduced-motion:reduce){#panel-viewers .viewer-summary>div{transition:none}#panel-viewers .viewer-summary>div:hover{transform:none}}



/* JHR COMMAND-CENTER POLISH */
:root{--jhr-accent:#a78bfa;--jhr-pink:#f0abfc;--jhr-cyan:#67e8f9}
body{background:radial-gradient(ellipse at 15% -10%,rgba(124,58,237,.24),transparent 40%),radial-gradient(ellipse at 100% 5%,rgba(219,39,119,.14),transparent 34%),#090711!important;color:#f8f5ff!important;padding:clamp(14px,3vw,34px)!important;min-height:100vh}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:-1;background-image:linear-gradient(rgba(167,139,250,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(167,139,250,.035) 1px,transparent 1px);background-size:34px 34px;mask-image:linear-gradient(#000,transparent 88%)}
.wrap{max-width:1450px!important}
.wrap>p:first-child a{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:800;padding:10px 14px;border:1px solid rgba(196,181,253,.22);border-radius:999px;background:rgba(255,255,255,.045);transition:.2s ease}
.wrap>p:first-child a:hover{background:rgba(139,92,246,.17);transform:translateX(-3px)}
.wrap>h1{font-size:clamp(2rem,4vw,3.2rem);line-height:1.08;letter-spacing:-.055em;margin:28px 0 10px!important;background:linear-gradient(100deg,#fff 5%,#ddd6fe 48%,#f0abfc 90%);-webkit-background-clip:text;background-clip:text;color:transparent!important}
.wrap>h1+p{color:#c4b8d8!important;font-size:15px}
.staff-tabs{padding:8px!important;gap:8px!important;border:1px solid rgba(196,181,253,.14);border-radius:18px;background:rgba(255,255,255,.035);backdrop-filter:blur(16px);position:sticky;top:10px;z-index:100;box-shadow:0 12px 38px rgba(0,0,0,.18)}
.staff-tab{background:transparent!important;border:1px solid transparent!important;color:#c4b8d8!important;border-radius:12px!important;padding:12px 15px!important;transition:background .2s ease,transform .2s ease,color .2s ease!important}
.staff-tab:hover{background:rgba(167,139,250,.11)!important;color:#fff!important;transform:translateY(-1px)}
.staff-tab.active{background:linear-gradient(115deg,#7c3aed,#a855f7 55%,#db2777)!important;color:#fff!important;box-shadow:0 8px 24px rgba(124,58,237,.28)!important}
.card{background:linear-gradient(145deg,rgba(26,19,41,.94),rgba(15,12,25,.94))!important;border:1px solid rgba(196,181,253,.15)!important;border-radius:24px!important;box-shadow:0 24px 70px rgba(0,0,0,.22)!important}
.card h2{letter-spacing:-.035em;font-size:clamp(1.35rem,2.5vw,1.85rem);color:#faf7ff!important}
input,textarea,select{background:rgba(8,7,16,.8)!important;color:#fff!important;border:1px solid rgba(196,181,253,.2)!important;border-radius:13px!important;transition:border-color .2s,box-shadow .2s!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:#a78bfa!important;box-shadow:0 0 0 4px rgba(167,139,250,.12)!important}
button{box-shadow:0 8px 20px rgba(124,58,237,.14);transition:transform .2s,filter .2s,box-shadow .2s!important}
button:hover{transform:translateY(-2px);filter:brightness(1.08);box-shadow:0 12px 28px rgba(124,58,237,.25)}
.message,.account-row{border-color:rgba(196,181,253,.13)!important}
.notice{color:#f5efff!important;border:1px solid rgba(196,181,253,.17);background:linear-gradient(120deg,rgba(124,58,237,.22),rgba(219,39,119,.1))!important}
.viewer-summary>div,.secret-grid>div{background:linear-gradient(145deg,rgba(139,92,246,.14),rgba(255,255,255,.025))!important;border:1px solid rgba(196,181,253,.18)!important;box-shadow:0 12px 30px rgba(0,0,0,.12);border-radius:18px!important}
.viewer-table-wrap{max-width:100%;}
@media(max-width:720px){.staff-tabs{position:static}.staff-tab{flex:1 1 auto;font-size:12px;padding:10px!important}.wrap>h1{margin-top:20px!important}.card{padding:18px!important}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}



/* JHR SIGNATURE EXPERIENCE — immersive, crisp, and responsive */
:root{--jhr-glow:rgba(139,92,246,.28);--jhr-ease:cubic-bezier(.2,.8,.2,1)}
body{isolation:isolate}
nav{border-color:rgba(167,139,250,.24)!important}
.hero{isolation:isolate!important;border:1px solid rgba(255,255,255,.17)!important;background:radial-gradient(ellipse at 50% 0%,rgba(255,255,255,.17),transparent 40%),linear-gradient(135deg,#170b32 0%,#35106c 30%,#7027c7 63%,#b52b83 100%)!important}
.hero:before{width:560px!important;height:560px!important;left:-180px!important;top:-180px!important;background:radial-gradient(circle,rgba(236,72,153,.5),transparent 68%)!important}
.hero:after{width:650px!important;height:650px!important;right:-230px!important;bottom:-320px!important;background:radial-gradient(circle,rgba(34,211,238,.28),transparent 68%)!important}
.hero-content{animation:jhrHeroEnter .85s var(--jhr-ease) both}
.hero .badge{font-size:11px!important;letter-spacing:.16em!important;text-transform:uppercase!important;box-shadow:0 0 35px rgba(255,255,255,.08),inset 0 1px rgba(255,255,255,.12)!important}
.hero h1{filter:drop-shadow(0 12px 35px rgba(0,0,0,.22));}
.hero .button,.hero a.button{box-shadow:0 12px 32px rgba(8,3,20,.24),inset 0 1px rgba(255,255,255,.22)!important}
.section:not(.color-section){scroll-margin-top:100px}
.section>.title,.color-section>.title{position:relative;text-wrap:balance}
.section>.title:after{content:"";display:block;width:68px;height:4px;margin:18px auto 0;border-radius:99px;background:linear-gradient(90deg,#8b5cf6,#ec4899,#22d3ee);box-shadow:0 0 20px rgba(139,92,246,.22)}
.card,.mission-card,.service-card,.project-mini-card,.news-card,.owner-card,.gallery-card{overflow:hidden;isolation:isolate}
.service-card,.project-mini-card,.news-card,.owner-card,.mission-card{position:relative}
.service-card:after,.project-mini-card:after,.news-card:after,.owner-card:after,.mission-card:after{content:"";position:absolute;inset:auto -35px -55px auto;width:140px;height:140px;border-radius:50%;background:radial-gradient(circle,rgba(139,92,246,.13),transparent 70%);pointer-events:none;z-index:-1;transition:transform .45s var(--jhr-ease)}
.service-card:hover:after,.project-mini-card:hover:after,.news-card:hover:after,.owner-card:hover:after,.mission-card:hover:after{transform:scale(1.45)}
.gallery-card{border-radius:24px!important}
.gallery-card .gallery-image-link img{filter:saturate(1.04) contrast(1.02)}
.gallery-card:hover .gallery-image-link img{transform:scale(1.065) rotate(.4deg)!important}
.button,button,.nav-btn{position:relative;isolation:isolate;overflow:hidden}
.button:focus-visible,button:focus-visible,a:focus-visible,.nav-btn:focus-visible{outline:3px solid #c4b5fd!important;outline-offset:3px!important}
.nav-controls .nav-btn{backdrop-filter:blur(12px)}
footer{position:relative;overflow:hidden}
footer:before{content:"";display:block;height:3px;width:100%;background:linear-gradient(90deg,#7c3aed,#ec4899,#22d3ee,#7c3aed);background-size:200% 100%;animation:jhrGradient 8s linear infinite}
body.dark .section:not(.color-section) .title{color:#fbf7ff!important}
body.dark .subtitle{color:#c8bdd9!important}
@keyframes jhrHeroEnter{from{opacity:0;transform:translateY(22px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
@media(max-width:700px){.hero{box-shadow:0 20px 60px rgba(76,29,149,.25)!important}.hero-content{padding:58px 14px!important}.hero h1{font-size:clamp(64px,18vw,100px)!important}.section>.title:after{margin-top:14px}.service-card:hover,.project-mini-card:hover,.news-card:hover,.owner-card:hover,.mission-card:hover,.gallery-card:hover{transform:translateY(-3px)!important}}
@media(prefers-reduced-motion:reduce){.hero-content{animation:none!important}footer:before{animation:none!important}}



/* JHR FUTURE OPS — staff command center */
:root{color-scheme:dark;--ops-bg:#050712;--ops-panel:rgba(12,17,36,.88);--ops-line:rgba(76,224,255,.22);--ops-cyan:#55f4ff;--ops-violet:#a78bfa;--ops-pink:#ff4fd8}
html{background:#050712}
body{position:relative;isolation:isolate;background:radial-gradient(ellipse at 12% -5%,rgba(93,54,255,.22),transparent 35%),radial-gradient(ellipse at 90% 15%,rgba(0,219,255,.11),transparent 28%),#050712!important;color:#eef7ff!important;padding:clamp(14px,3vw,38px)!important}
body:before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background-image:linear-gradient(rgba(86,226,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(86,226,255,.035) 1px,transparent 1px);background-size:36px 36px;mask-image:linear-gradient(to bottom,black,transparent 92%)}
.wrap{max-width:1440px!important}
.wrap>p:first-child a{display:inline-flex;align-items:center;gap:8px;padding:10px 14px;border:1px solid rgba(85,244,255,.2);border-radius:12px;background:rgba(6,17,35,.72);color:#9df8ff!important;text-decoration:none;font-size:13px;letter-spacing:.03em}
.wrap>h1{font-size:clamp(30px,4vw,48px);letter-spacing:-.055em;margin:22px 0 8px;text-shadow:0 0 32px rgba(85,244,255,.16)}
.wrap>h1:before{content:"JHR / COMMAND INTERFACE";display:block;margin-bottom:13px;color:var(--ops-cyan);font-size:10px;letter-spacing:.24em;font-weight:900}
.wrap>h1+p{color:#8da8c4!important}
.card{position:relative;overflow:hidden;background:linear-gradient(145deg,rgba(13,20,43,.96),rgba(8,12,27,.96))!important;border:1px solid var(--ops-line)!important;border-radius:20px!important;box-shadow:0 18px 70px rgba(0,0,0,.28),inset 0 1px rgba(255,255,255,.035)!important;backdrop-filter:blur(22px)!important}
.card:before{content:"";position:absolute;top:0;left:24px;right:24px;height:1px;background:linear-gradient(90deg,transparent,var(--ops-cyan),rgba(167,139,250,.8),transparent);opacity:.55;pointer-events:none}
.card h2{color:#f1fbff;letter-spacing:-.035em;font-size:clamp(21px,2vw,28px)}
.staff-tabs{display:flex;gap:9px;padding:10px;margin:24px 0 20px;border:1px solid rgba(85,244,255,.13);border-radius:18px;background:rgba(5,10,25,.8);box-shadow:inset 0 1px rgba(255,255,255,.025)}
.staff-tab{border:1px solid transparent!important;background:transparent!important;color:#9cb1cb!important;border-radius:11px!important;padding:12px 15px!important;font-size:13px!important;letter-spacing:.015em;white-space:nowrap}
.staff-tab:hover{border-color:rgba(85,244,255,.25)!important;background:rgba(85,244,255,.07)!important;color:#fff!important;transform:translateY(-1px)}
.staff-tab.active{color:#04101b!important;background:linear-gradient(110deg,#55f4ff,#a78bfa 72%,#ff4fd8)!important;box-shadow:0 0 28px rgba(85,244,255,.16)!important;border:0!important}
.viewer-summary{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:16px!important}
.viewer-summary>div{position:relative;overflow:hidden;min-height:128px;background:linear-gradient(145deg,rgba(16,31,60,.94),rgba(7,14,31,.95))!important;border:1px solid rgba(85,244,255,.18)!important;border-radius:18px!important;padding:22px!important}
.viewer-summary>div:after{content:"";position:absolute;width:120px;height:120px;right:-45px;top:-50px;border-radius:50%;border:1px solid rgba(85,244,255,.13);box-shadow:0 0 0 12px rgba(85,244,255,.025),0 0 0 26px rgba(85,244,255,.018)}
.viewer-summary strong{font-size:clamp(28px,3vw,38px)!important;line-height:1.2;color:#efffff!important;text-shadow:0 0 22px rgba(85,244,255,.18)}
.viewer-summary span{color:#86a9c7!important;text-transform:uppercase;font-size:10px!important;font-weight:800;letter-spacing:.13em}
.viewer-table-wrap{border:1px solid rgba(85,244,255,.19)!important;border-radius:16px!important;background:rgba(3,8,20,.75);box-shadow:0 14px 50px rgba(0,0,0,.2)}
.viewer-table{min-width:1250px!important}
.viewer-table th{background:#0b1730!important;color:#70f5ff!important;text-transform:uppercase;letter-spacing:.1em;font-size:10px!important;padding:16px!important;border-bottom:1px solid rgba(85,244,255,.25)!important}
.viewer-table td{color:#e4efff!important;border-bottom:1px solid rgba(137,171,210,.1)!important;padding:15px!important;font-size:12px!important;background:rgba(5,12,28,.58)!important}
.viewer-table tbody tr:nth-child(even) td{background:rgba(15,24,48,.65)!important}
.viewer-table tbody tr:hover td{background:rgba(30,83,119,.3)!important;color:#fff!important}
.viewer-table td strong{color:#fff!important}
.viewer-table code{padding:4px 7px;border:1px solid rgba(167,139,250,.2);border-radius:6px;background:rgba(167,139,250,.08);color:#c4b5fd!important}
.viewer-table .ip-cell{color:#ff9df0!important}
.viewer-detail,.meta{color:#87a3c0!important}
input,textarea,select{background:rgba(3,9,23,.92)!important;border:1px solid rgba(85,244,255,.18)!important;color:#f1f8ff!important;border-radius:12px!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:var(--ops-cyan)!important;box-shadow:0 0 0 3px rgba(85,244,255,.1),0 0 22px rgba(85,244,255,.07)!important}
button:not(.staff-tab){background:linear-gradient(105deg,#167e9a,#6552d9 65%,#b93f9d)!important;border:1px solid rgba(136,238,255,.28)!important;color:#fff!important;box-shadow:0 7px 22px rgba(45,124,210,.14)}
button:not(.staff-tab):hover{filter:brightness(1.15);transform:translateY(-1px)}
.notice{background:rgba(85,244,255,.07)!important;border:1px solid rgba(85,244,255,.22)!important;color:#d8fbff!important}
.account-row,.message{border-color:rgba(85,244,255,.13)!important}
.secret-grid>div,.secret-health>div{background:rgba(85,244,255,.045)!important;border-color:rgba(85,244,255,.15)!important}
.secret-grid span,.secret-health span{color:#8aa6c3!important}
.danger-mini{background:linear-gradient(110deg,#a5224d,#e04465)!important}
@media(max-width:800px){.viewer-summary{grid-template-columns:1fr!important}.staff-tabs{overflow-x:auto;flex-wrap:nowrap}.staff-tab{flex:0 0 auto}.card{padding:19px!important}}
@media(prefers-reduced-motion:reduce){.staff-tab,.card,button{transition:none!important}}


/* JHR PURPLE NEBULA REDESIGN — vivid, layered, unmistakably purple */
/* ACCESSIBILITY FIX: calmer purple palette, comfortable contrast */
body{background-image:radial-gradient(ellipse at 15% 8%,rgba(124,58,237,.13),transparent 36%),radial-gradient(ellipse at 85% 18%,rgba(168,85,247,.09),transparent 32%),linear-gradient(180deg,#10091b 0%,#0b0712 55%,#08050d 100%)!important;background-color:#0b0712!important;color:#f4edff!important}
body:before{opacity:.055!important;background-size:64px 64px!important}
.join{background:linear-gradient(145deg,rgba(35,18,56,.98),rgba(19,10,32,.98))!important;color:#f4edff!important;border:1px solid rgba(192,132,252,.25)!important;box-shadow:0 18px 55px rgba(0,0,0,.28),0 0 28px rgba(124,58,237,.08)!important}
.join h2{color:#fff!important;text-shadow:0 2px 18px rgba(168,85,247,.22)!important}
.join p{color:#d7c9e8!important}
.join .viewer-counter{background:linear-gradient(110deg,#6d28d9,#8b5cf6)!important;color:#fff!important;border:1px solid rgba(233,213,255,.28)!important;box-shadow:0 6px 18px rgba(109,40,217,.2)!important}
.join .viewer-counter strong,.join .viewer-counter span{color:#fff!important}
footer{background:#090610!important;color:#e7ddf4!important}
footer p{color:#c5b7d8!important}
footer .footer-logo,footer h2,footer h3{color:#c4a1ff!important;text-shadow:none!important}
button,.btn,.button{box-shadow:0 5px 14px rgba(124,58,237,.16)!important}
@media(prefers-reduced-motion:reduce){body:before{display:none!important}}

:root{--jhr-purple:#a855f7;--jhr-violet:#7c3aed;--jhr-lilac:#e9d5ff;--jhr-pink:#f0abfc;--jhr-night:#090511;--jhr-panel:rgba(25,12,43,.82);--jhr-edge:rgba(192,132,252,.28);--jhr-glow:rgba(168,85,247,.28)}
html{scroll-behavior:smooth;scroll-padding-top:90px}
body{background-color:#090511!important;background-image:radial-gradient(ellipse at 12% 4%,rgba(147,51,234,.26),transparent 34%),radial-gradient(ellipse at 88% 16%,rgba(192,38,211,.17),transparent 29%),radial-gradient(ellipse at 52% 100%,rgba(109,40,217,.17),transparent 42%),linear-gradient(180deg,#090511 0%,#10071d 48%,#08040f 100%)!important;color:#fbf7ff!important}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.20;background-image:linear-gradient(rgba(192,132,252,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(192,132,252,.08) 1px,transparent 1px);background-size:46px 46px;mask-image:linear-gradient(to bottom,black,transparent 88%)}
body>*{position:relative;z-index:1}
nav{background:rgba(12,5,22,.82)!important;border:1px solid rgba(192,132,252,.2)!important;box-shadow:0 12px 50px rgba(0,0,0,.28),0 0 30px rgba(147,51,234,.08)!important;backdrop-filter:blur(22px)!important}
.logo strong,.logo-name-wrap strong,.footer-logo{color:#e9d5ff!important;text-shadow:0 0 22px rgba(168,85,247,.38)}
.nav-links a{transition:color .2s,background .2s,transform .2s!important;border-radius:999px}
.nav-links a:hover,.nav-links a.active-nav{color:#fff!important;background:rgba(168,85,247,.15)!important;box-shadow:inset 0 0 0 1px rgba(192,132,252,.2),0 0 22px rgba(168,85,247,.09)}
.hero{isolation:isolate!important;overflow:hidden!important;background:radial-gradient(ellipse at 50% 42%,rgba(124,58,237,.35),transparent 42%),linear-gradient(135deg,rgba(29,10,51,.97),rgba(10,5,21,.98) 56%,rgba(45,8,53,.9))!important;border:1px solid rgba(192,132,252,.35)!important;box-shadow:0 35px 100px rgba(0,0,0,.48),inset 0 0 80px rgba(124,58,237,.12),0 0 55px rgba(147,51,234,.13)!important}
.hero:before{content:""!important;position:absolute!important;inset:-20%!important;width:auto!important;height:auto!important;opacity:.75!important;pointer-events:none!important;background:radial-gradient(circle at 50% 45%,rgba(168,85,247,.22),transparent 28%),radial-gradient(circle at 18% 75%,rgba(236,72,153,.13),transparent 25%),radial-gradient(circle at 80% 22%,rgba(124,58,237,.22),transparent 28%)!important;filter:blur(18px)!important;animation:nebulaDrift 14s ease-in-out infinite alternate!important}
.hero:after{border-color:rgba(216,180,254,.48)!important;opacity:.72!important}
.hero h1{color:#fff!important;text-shadow:0 0 14px rgba(216,180,254,.4),0 0 55px rgba(168,85,247,.34)!important;letter-spacing:-.065em!important}
.hero p,.hero .subtitle,.hero-content p{color:#d8c7ed!important}
button,.btn,.button,.hero a[role=button],a.button{background:linear-gradient(115deg,#6d28d9,#a855f7 52%,#db2777)!important;border:1px solid rgba(233,213,255,.32)!important;color:white!important;box-shadow:0 10px 28px rgba(124,58,237,.25),inset 0 1px rgba(255,255,255,.18)!important;transition:transform .22s,filter .22s,box-shadow .22s!important}
button:hover,.btn:hover,.button:hover,.hero a[role=button]:hover,a.button:hover{transform:translateY(-2px)!important;filter:brightness(1.12)!important;box-shadow:0 15px 38px rgba(168,85,247,.34),0 0 24px rgba(217,70,239,.12)!important}
a{color:#d8b4fe}
.section>.title,.section h2,.section-title{color:#f5eaff!important;text-shadow:0 0 30px rgba(168,85,247,.16)}
.section>.title:after,.section-title:after{background:linear-gradient(90deg,#7c3aed,#d946ef,#f0abfc)!important;box-shadow:0 0 18px rgba(192,132,252,.32)!important}
.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card,.game,.contact,.mission-card{background:linear-gradient(145deg,rgba(34,17,54,.88),rgba(15,8,27,.91))!important;border:1px solid rgba(192,132,252,.19)!important;border-radius:22px!important;box-shadow:0 18px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)!important;backdrop-filter:blur(16px)!important;transition:transform .24s,border-color .24s,box-shadow .24s!important}
.news-card:hover,.project-mini-card:hover,.service-card:hover,.owner-card:hover,.gallery-card:hover,.game:hover,.contact:hover{border-color:rgba(216,180,254,.48)!important;box-shadow:0 24px 62px rgba(0,0,0,.32),0 0 32px rgba(147,51,234,.12)!important}
input,textarea,select{background:rgba(11,5,22,.9)!important;color:#fbf7ff!important;border:1px solid rgba(192,132,252,.28)!important;border-radius:13px!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 24px rgba(168,85,247,.12)!important}
footer{background:linear-gradient(180deg,#10071d,#07030d)!important;border-top:1px solid rgba(192,132,252,.22)!important;color:#e9d5ff!important}
footer p{color:#b8a4d2!important}
#jhr-progress{background:linear-gradient(90deg,#6d28d9,#a855f7,#e879f9,#f0abfc)!important;box-shadow:0 0 18px rgba(168,85,247,.6)!important}
::selection{background:#a855f7!important;color:#fff!important}
@keyframes nebulaDrift{from{transform:translate3d(-1.5%,1%,0) scale(1)}to{transform:translate3d(1.5%,-1%,0) scale(1.08)}}
/* Staff command center uses the same rich purple visual language */
.wrap{max-width:1360px!important}
.wrap>h1{color:#f5eaff!important;text-shadow:0 0 28px rgba(168,85,247,.2)!important}
.wrap>h1:before{color:#d8b4fe!important}
.staff-tab{color:#e9d5ff!important;border-color:rgba(192,132,252,.2)!important;background:rgba(38,18,61,.65)!important}
.staff-tab.active{background:linear-gradient(120deg,#6d28d9,#a855f7,#db2777)!important;box-shadow:0 10px 28px rgba(124,58,237,.3)!important}
.staff-tab:hover{background:rgba(168,85,247,.18)!important}
.viewer-table th{background:#241038!important;color:#e9d5ff!important}
.viewer-table td{background:rgba(18,8,32,.68)!important;color:#f5edff!important}
.viewer-table tbody tr:nth-child(even) td{background:rgba(38,17,60,.55)!important}
.viewer-table tbody tr:hover td{background:rgba(124,58,237,.22)!important}
input:focus,textarea:focus,select:focus{border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 22px rgba(168,85,247,.1)!important}
@media(max-width:700px){body{padding:16px!important}.hero{min-height:590px!important}.hero h1{font-size:clamp(62px,17vw,100px)!important}.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card{border-radius:17px!important}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;scroll-behavior:auto!important;transition:none!important}}

</style>
</head>
<body>
<div class="wrap">
<p><a href="{{ url_for('home') }}">← Back to JHR website</a></p>
<h1>👨‍💼 JHR Staff Dashboard</h1>
<p>You are logged in as <strong>{{ staff_username }}</strong>.</p>

<div class="staff-tabs" role="tablist" aria-label="Staff dashboard sections">
    <button class="staff-tab active" type="button" data-panel="messages">📨 Messages</button>
    <button class="staff-tab" type="button" data-panel="news">📰 News & Announcements</button>
    <button class="staff-tab" type="button" data-panel="viewers">👁️ Detailed Viewers</button>
    <button class="staff-tab" type="button" data-panel="accounts">👤 Staff Accounts</button>
    <button class="staff-tab" type="button" data-panel="password">🔑 Change Password</button>
    {% if staff_role == "superadmin" %}<button class="staff-tab secret-tab" type="button" data-panel="control">🔐 Control Room</button>{% endif %}
</div>

{% with notices = get_flashed_messages() %}
{% for notice in notices %}
<div class="notice">{{ notice }}</div>
{% endfor %}
{% endwith %}

<div class="card staff-panel active" id="panel-messages">
<h2>📨 Free Coding Class Messages</h2>
{% if messages %}
    {% for msg in messages %}
    <div class="message">
        <strong>{{ msg["name"] }}</strong><br>
        <span class="meta">{{ msg["email"] }} · {{ msg["created_at"] }}</span>
        <p style="white-space:pre-wrap;">{{ msg["message"] }}</p>
        <form method="POST"
              action="{{ url_for('delete_staff_message', message_id=msg['id']) }}"
              onsubmit="return confirm('Are you sure you want to permanently delete this message?');">
            <button type="submit"
                    style="background:#b42318;color:#fff;padding:9px 14px;border:0;border-radius:9px;cursor:pointer;font-weight:800;">
                🗑️ Delete Message
            </button>
        </form>
    </div>
    {% endfor %}
{% else %}
    <p>No coding-class messages yet.</p>
{% endif %}
</div>

<div class="card staff-panel" id="panel-password">
<h2>🔑 Change My Staff Password</h2>
<form method="POST" action="{{ url_for('change_staff_password') }}">
<label>Current password</label>
<input type="password" name="current_password" required autocomplete="current-password">
<label>New password</label>
<input type="password" name="new_password" minlength="6" required autocomplete="new-password">
<label>Confirm new password</label>
<input type="password" name="confirm_password" minlength="6" required autocomplete="new-password">
<button type="submit">Change Password</button>
</form>
</div>

<div class="card staff-panel" id="panel-staff">
<h2>👥 Add New Staff Account</h2>
<form method="POST" action="{{ url_for('add_staff_account') }}">
<label>Username</label>
<input type="text" name="username" minlength="3" maxlength="80" required autocomplete="off">
<label>Password</label>
<input type="password" name="password" minlength="6" required autocomplete="new-password">
<label>Confirm password</label>
<input type="password" name="confirm_password" minlength="6" required autocomplete="new-password">
<button type="submit">Create Staff Account</button>
</form>
</div>

<div class="card staff-panel" id="panel-news">
<h2>📰 Add News / Announcement</h2>
<form method="POST" action="{{ url_for('add_news_item') }}" enctype="multipart/form-data">
<label>Type</label>
<select name="kind" required style="width:100%;padding:13px;border:1px solid #3c4658;border-radius:11px;background:#0f131a;color:#fff;margin:7px 0 12px;font:inherit;">
<option value="Announcement">Announcement</option>
<option value="News">News</option>
</select>
<label>Title</label>
<input type="text" name="title" maxlength="160" required placeholder="News or announcement title">
<label>Content</label>
<textarea name="content" maxlength="10000" required placeholder="Write the news or announcement..."></textarea>
<label>Pictures (optional)</label>
<input type="file" name="news_images" accept="image/jpeg,image/png,image/webp,image/gif" multiple>
<small class="meta">You can attach one or more pictures to this news/announcement.</small>
<button type="submit">📢 Publish</button>
</form>
</div>

<div class="card staff-panel" id="panel-published-news">
<h2>🗞️ Published News & Announcements</h2>
{% if news_items %}
    {% for item in news_items %}
    <div class="message">
        <strong>{{ item["kind"] }} — {{ item["title"] }}</strong><br>
        <span class="meta">{{ item["created_at"] }}{% if item["author"] %} · Posted by {{ item["author"] }}{% endif %}</span>
        <p style="white-space:pre-wrap;">{{ item["content"] }}</p>
        {% if item["images"] %}
        <div class="staff-news-images">
            {% for image in item["images"] %}
            <img src="{{ url_for('news_image', filename=image) }}" alt="{{ item['title'] }}" loading="lazy">
            {% endfor %}
        </div>
        {% endif %}
        <form method="POST" action="{{ url_for('delete_news_item', news_id=item['id']) }}" onsubmit="return confirm('Delete this news or announcement permanently?');">
            <button type="submit" style="background:#b42318;color:#fff;padding:9px 14px;border:0;border-radius:9px;cursor:pointer;font-weight:800;">🗑️ Delete</button>
        </form>
    </div>
    {% endfor %}
{% else %}
    <p>No news or announcements published yet.</p>
{% endif %}
</div>

<div class="card staff-panel" id="panel-viewers">
<h2>👁️ Detailed Viewers</h2>
<p class="meta">Detailed visitor activity for staff. Each browser receives an anonymous Viewer ID. IP address, device, browser, operating system, visit times, page activity, and view count are shown here.</p>

<div class="viewer-summary">
    <div><strong>{{ viewer_total }}</strong><span>Unique Viewers</span></div>
    <div><strong>{{ viewer_views }}</strong><span>Total Page Views</span></div>
    <div><strong>{{ viewers[0]['last_seen'] if viewers else '—' }}</strong><span>Latest Activity</span></div>
</div>

{% if viewers %}
<div class="viewer-table-wrap">
<table class="viewer-table">
<thead>
<tr>
    <th>Viewer</th>
    <th>First Visit</th>
    <th>Last Activity</th>
    <th>Views</th>
    <th>Last Page</th>
    <th>IP Address</th>
    <th>Device</th>
    <th>Browser</th>
    <th>Operating System</th>
</tr>
</thead>
<tbody>
{% for viewer in viewers %}
<tr>
    <td><strong>Viewer #{{ viewer['id'] }}</strong></td>
    <td>{{ viewer['first_seen'] }}</td>
    <td>{{ viewer['last_seen'] }}</td>
    <td><strong>{{ viewer['total_views'] }}</strong></td>
    <td><code>{{ viewer['last_page'] }}</code></td>
    <td class="ip-cell">{{ viewer['last_ip'] }}<div class="viewer-detail">First: {{ viewer['first_ip'] }}</div></td>
    <td>{{ viewer['device'] }}</td>
    <td>{{ viewer['browser'] }}</td>
    <td>{{ viewer['operating_system'] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% else %}
<p>No viewer activity has been recorded yet.</p>
{% endif %}
</div>

<div class="card staff-panel" id="panel-accounts">
<h2>👤 Current Staff Accounts</h2>
{% for staff in staff_accounts %}
<div class="account-row"><div><strong>{{ staff["username"] }}</strong><span class="meta">{{ staff.get("role", "staff") }} · {{ staff["created_at"] }}</span></div>{% if staff_role == "superadmin" and staff["username"] != staff_username and staff.get("role") != "superadmin" %}<form method="POST" action="{{ url_for('superadmin_delete_account', account_id=staff['id']) }}" onsubmit="return confirm('Delete this staff account?');"><button class="danger-mini">Delete</button></form>{% endif %}</div>
{% endfor %}
</div>
{% if staff_role == "superadmin" %}
<div class="card staff-panel" id="panel-control">
<h2>🔐 Control Room</h2><p class="meta">Private superadmin tools.</p>
<div class="secret-grid">
<div><strong>{{ superadmin_stats.accounts }}</strong><span>Accounts</span></div><div><strong>{{ superadmin_stats.gallery }}</strong><span>Gallery</span></div><div><strong>{{ superadmin_stats.news }}</strong><span>News</span></div><div><strong>{{ superadmin_stats.messages }}</strong><span>Messages</span></div><div><strong>{{ superadmin_stats.viewers }}</strong><span>Viewers</span></div><div><strong>{{ superadmin_stats.gridfs }}</strong><span>Stored Photos</span></div><div><strong>{{ superadmin_stats.audit }}</strong><span>Audit Logs</span></div>
</div>
<div class="secret-actions">
<form method="POST" action="{{ url_for('superadmin_reset_admin') }}" onsubmit="return confirm('Reset admin password?');"><button type="submit">🔑 Reset Admin</button></form>
<form method="POST" action="{{ url_for('superadmin_clear_viewers') }}" onsubmit="return confirm('Clear all viewer analytics?');"><button type="submit" class="danger-mini">🧹 Clear Viewers</button></form>
<form method="POST" action="{{ url_for('superadmin_cleanup_gridfs') }}" onsubmit="return confirm('Remove orphaned stored photos?');"><button type="submit">🗂️ Clean Storage</button></form>
<form method="POST" action="{{ url_for('superadmin_clear_audit') }}" onsubmit="return confirm('Clear all superadmin audit logs?');"><button type="submit" class="danger-mini">🧾 Clear Logs</button></form>
<a class="button" href="{{ url_for('superadmin_export_viewers') }}">📊 Export Viewers</a>
<a class="button" href="{{ url_for('superadmin_export_gallery') }}">🖼️ Export Gallery</a>
<a class="button" href="{{ url_for('staff_dashboard') }}#control">🔄 Refresh</a>
</div>
<div class="secret-health">
<div><span>Database</span><strong>{{ superadmin_stats.db }}</strong></div>
<div><span>Storage</span><strong>{{ superadmin_stats.storage_mb }} MB</strong></div>
<div><span>Session</span><strong>5 min</strong></div>
</div>
<div class="secret-danger-zone">
<h3>⚠️ Danger Zone</h3>
<p class="meta">These actions are permanent.</p>
<form method="POST" action="{{ url_for('superadmin_clear_gallery') }}" onsubmit="return confirm('DELETE ALL GALLERY PHOTOS AND THEIR STORED FILES? This cannot be undone.');"><button type="submit" class="danger-mini">🗑️ Delete Entire Gallery</button></form>
</div>
<h3 style="margin-top:22px">🛡️ Account Roles</h3>
{% for staff in staff_accounts %}
<div class="account-row"><div><strong>{{ staff["username"] }}</strong><span class="meta">{{ staff.get("role", "staff") }}</span></div>{% if staff["username"] != staff_username %}<form method="POST" action="{{ url_for('superadmin_toggle_role', account_id=staff['id']) }}"><button type="submit">{% if staff.get("role") == "superadmin" %}Make Staff{% else %}Make Superadmin{% endif %}</button></form>{% endif %}</div>
{% endfor %}
<h3 style="margin-top:22px">🧾 Recent Activity</h3>
<div class="audit-list">{% for item in superadmin_audit %}<div class="audit-item"><strong>{{ item["action"] }}</strong><span>{{ item["details"] }}</span><small>{{ item["username"] }} · {{ item["created_at"] }}</small></div>{% else %}<p class="meta">No activity yet.</p>{% endfor %}</div>
<div class="secret-note">🕶️ Superadmin mode active.</div>
</div>
{% endif %}
</div>
<script>
(function () {
    const tabs = document.querySelectorAll('.staff-tab');
    const panels = document.querySelectorAll('.staff-panel');
    function activate(name) {
        tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.panel === name));
        panels.forEach(panel => panel.classList.toggle('active', panel.id === 'panel-' + name));
        history.replaceState(null, '', '#' + name);
    }
    tabs.forEach(tab => tab.addEventListener('click', () => activate(tab.dataset.panel)));
    const initial = location.hash.replace('#', '');
    if (['messages','news','viewers','accounts','password','control'].includes(initial)) {
        activate(initial);
    }
})();
</script>
<script>
(function () {
    const timeoutMs = 5 * 60 * 1000;
    let lastActivity = Date.now();

    ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach(function (eventName) {
        window.addEventListener(eventName, function () {
            lastActivity = Date.now();
        }, { passive: true });
    });

    setInterval(function () {
        if (Date.now() - lastActivity >= timeoutMs) {
            window.location.href = "{{ url_for('logout') }}";
        } else {
            fetch("{{ url_for('staff_heartbeat') }}", {
                method: "POST",
                credentials: "same-origin",
                headers: {"X-Requested-With": "XMLHttpRequest"}
            }).catch(function () {});
        }
    }, 60 * 1000);
})();
</script>
</body>
</html>
"""

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="theme-color"
    content="#7c3aed"
>

<meta
    name="description"
    content="JHR — Technology, Creativity, and Learning"
>

<title>
JHR | Technology, Creativity, and Learning
</title>


<style>

/* =====================================================
   RESET
===================================================== */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    scroll-behavior: smooth;
}


/* =====================================================
   VARIABLES
===================================================== */

:root {

    --purple:
        #7c3aed;

    --purple-dark:
        #4c1d95;

    --purple-deep:
        #2e1065;

    --purple-light:
        #a78bfa;

    --purple-soft:
        #ede9fe;

    --pink:
        #c026d3;

    --background:
        #faf7ff;

    --card:
        #ffffff;

    --text:
        #24113f;

    --muted:
        #6b5b82;

    --border:
        #ded0ff;

    --shadow:
        0 12px 35px
        rgba(76,29,149,.14);
}


/* =====================================================
   BODY
===================================================== */

body {

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        linear-gradient(
            180deg,
            #faf7ff,
            #f3e8ff
        );

    color:
        var(--text);

    line-height:
        1.6;

    overflow-x:
        hidden;

    transition:
        background .25s ease,
        color .25s ease;
}


/* =====================================================
   DARK MODE
===================================================== */

body.dark {

    --background:
        #12091d;

    --card:
        #21122f;

    --text:
        #ffffff;

    --muted:
        #d9cce5;

    --border:
        #563574;

    background:
        linear-gradient(
            180deg,
            #12091d,
            #1e0f2d
        );
}


body.dark nav {

    background:
        rgba(24,10,39,.98);
}


body.dark .nav-links a {

    color:
        white;
}


body.dark .card,
body.dark .stat,
body.dark .service-card,
body.dark .owner-card,
body.dark .gallery-card,
body.dark .game,
body.dark .contact {

    background:
        #21122f;
}


body.dark .games {

    background:
        #1e0f2d;
}


body.dark .join {

    background:
        #241234;
}


/* =====================================================
   NAVIGATION
===================================================== */

nav {

    position:
        sticky;

    top:
        0;

    z-index:
        10000;

    display:
        flex;

    align-items:
        center;

    justify-content:
        space-between;

    gap:
        15px;

    padding:
        10px 22px;

    background:
        rgba(255,255,255,.98);

    box-shadow:
        0 5px 25px
        rgba(0,0,0,.12);
}


.logo {

    display:
        flex;

    align-items:
        center;

    gap:
        9px;

    color:
        var(--purple);

    text-decoration:
        none;

    font-size:
        25px;

    font-weight:
        900;

    white-space:
        nowrap;
}


.logo img {

    width:
        48px;

    height:
        48px;

    display:
        block;

    object-fit:
        contain;
}


.nav-links {

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    gap:
        9px;

    flex-wrap:
        wrap;
}


.nav-links a {

    color:
        var(--text);

    text-decoration:
        none;

    font-size:
        12px;

    font-weight:
        800;

    transition:
        .2s;
}


.nav-links a:hover {

    color:
        var(--purple);
}


.nav-controls {

    display:
        flex;

    align-items:
        center;

    gap:
        6px;
}


.nav-btn {

    border:
        none;

    border-radius:
        20px;

    padding:
        8px 11px;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--pink)
        );

    color:
        white;

    cursor:
        pointer;

    font-weight:
        800;

    transition:
        .2s;
}


.nav-btn:hover {

    transform:
        translateY(-2px);
}


/* =====================================================
   HERO
===================================================== */

.hero {

    min-height:
        700px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    text-align:
        center;

    padding:
        80px 20px;

    color:
        white;

    background:
        linear-gradient(
            135deg,
            #2e1065,
            #6d28d9,
            #7c3aed,
            #581c87
        );
}


.hero-content {

    max-width:
        1050px;
}


.badge {

    display:
        inline-block;

    padding:
        11px 20px;

    margin-bottom:
        22px;

    border:
        1px solid
        rgba(255,255,255,.35);

    border-radius:
        30px;

    background:
        rgba(255,255,255,.12);

    font-weight:
        800;
}


.hero h1 {

    font-size:
        clamp(
            76px,
            14vw,
            155px
        );

    line-height:
        .85;

    letter-spacing:
        8px;

    font-weight:
        1000;
}


.hero h2 {

    font-size:
        clamp(
            22px,
            4vw,
            42px
        );

    margin:
        25px 0 15px;
}


.hero p {

    max-width:
        800px;

    margin:
        auto;

    font-size:
        19px;

    color:
        #f4edff;
}


.button {

    display:
        inline-block;

    margin:
        25px 7px 0;

    padding:
        13px 22px;

    border-radius:
        30px;

    background:
        white;

    color:
        var(--purple);

    text-decoration:
        none;

    font-weight:
        900;

    transition:
        .2s;
}


.button:hover {

    transform:
        translateY(-3px);
}


.button.alt {

    background:
        var(--purple-light);

    color:
        white;
}


/* =====================================================
   SECTIONS
===================================================== */

.section {

    max-width:
        1180px;

    margin:
        0 auto;

    padding:
        85px 22px;
}


.title {

    text-align:
        center;

    font-size:
        clamp(
            32px,
            5vw,
            48px
        );

    margin-bottom:
        12px;

    color:
        var(--purple-dark);
}


body.dark .title {

    color:
        white;
}


.subtitle {

    max-width:
        800px;

    margin:
        0 auto 42px;

    text-align:
        center;

    color:
        var(--muted);

    font-size:
        18px;
}


/* =====================================================
   CARDS
===================================================== */

.cards {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(230px,1fr)
        );

    gap:
        20px;
}


.card {

    background:
        var(--card);

    padding:
        28px;

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    border-top:
        5px solid
        var(--purple);
}


.card h3 {

    color:
        var(--purple);

    margin-bottom:
        10px;
}


.card p {

    color:
        var(--muted);
}


/* =====================================================
   MISSION
===================================================== */

.color-section {

    padding:
        85px 22px;

    color:
        white;

    background:
        linear-gradient(
            135deg,
            #4c1d95,
            #7c3aed
        );
}


.color-section .title {

    color:
        white;
}


.mission {

    max-width:
        1180px;

    margin:
        auto;

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px,1fr)
        );

    gap:
        20px;
}


.mission-card {

    padding:
        28px;

    border-radius:
        22px;

    background:
        rgba(255,255,255,.1);

    border:
        1px solid
        rgba(255,255,255,.2);

    text-align:
        center;
}


.mission-icon {

    font-size:
        42px;

    margin-bottom:
        10px;
}


.mission-card p {

    color:
        #eee7ff;
}


/* =====================================================
   STATS
===================================================== */

.stats {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(170px,1fr)
        );

    gap:
        20px;
}


.stat {

    background:
        var(--card);

    padding:
        28px;

    text-align:
        center;

    border-radius:
        22px;

    box-shadow:
        var(--shadow);
}


.stat-number {

    font-size:
        45px;

    font-weight:
        1000;

    color:
        var(--purple);
}


/* =====================================================
   SERVICES
===================================================== */

.services {

    display:
        grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(230px,1fr)
        );

    gap:
        20px;
}


.service-card {

    background:
        var(--card);

    padding:
        30px;

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    border-top:
        5px solid
        var(--purple);
}


.service-icon {

    font-size:
        42px;

    margin-bottom:
        10px;
}


.service-card h3 {

    color:
        var(--purple);

    margin-bottom:
        10px;
}


.service-card p {

    color:
        var(--muted);
}


.free {

    display:
        inline-block;

    margin-top:
        15px;

    padding:
        6px 12px;

    border-radius:
        20px;

    background:
        var(--purple-soft);

    color:
        var(--purple);

    font-size:
        12px;

    font-weight:
        900;
}


/* =====================================================
   REQUESTED JHR LAYOUT
===================================================== */
.mission-subtitle{color:#fff !important}
.who-are-we-cards{display:flex;justify-content:center}
.who-we-are-box{width:min(950px,100%);text-align:left}
.project-mini-grid{justify-content:center;align-items:stretch}
.project-mini-card{max-width:330px;margin:0 auto;text-align:center}
.service-center{justify-content:center;align-items:stretch}
.service-center .service-card{max-width:360px;margin:0 auto;text-align:center}
.news-grid{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}
.news-card{background:var(--card);border:1px solid var(--border);border-top:5px solid var(--purple);border-radius:22px;padding:24px;box-shadow:var(--shadow);text-align:left}
.news-card .news-kind{color:var(--purple);font-weight:900;text-transform:uppercase;font-size:12px;letter-spacing:.06em}
.news-card h3{color:var(--text);margin:8px 0}
.news-card p{color:var(--muted);white-space:pre-wrap}
.news-meta{color:var(--muted);font-size:13px;margin-bottom:8px}

.news-images,.staff-news-images{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:14px 0}
.news-images img,.staff-news-images img{width:100%;height:220px;object-fit:cover;border-radius:14px;border:1px solid var(--border);background:var(--purple-soft)}
.staff-news-images img{height:180px}
.gallery-metadata{margin-top:14px}
.gallery-meta-row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:12px 0 16px;padding:14px;border:1px solid var(--border);border-radius:14px;background:var(--card)}
.gallery-meta-row input,.gallery-meta-row textarea{width:100%;padding:10px;border:1px solid var(--border);border-radius:10px;background:var(--background);color:var(--text);font:inherit}
.gallery-meta-row textarea{min-height:80px;resize:vertical}
.gallery-file-name{font-weight:800;color:var(--purple);margin-top:12px}
@media(max-width:650px){.gallery-meta-row{grid-template-columns:1fr}.news-images img,.staff-news-images img{height:200px}}


/* Final requested visual refinements */
.hero-content { text-align: center; }
.hero-content .hero-message {
    text-align:center;
    max-width:1000px;
    margin:18px auto 0;
    white-space:pre-line;
}
.hero-organization-title {
    text-align:center;
    color:#ffffff;
    font-size:clamp(24px,3.2vw,42px);
    font-weight:900;
    line-height:1.15;
    margin:12px 0 18px;
}

.who-are-we-cards {
    display: flex;
    justify-content: center;
    align-items: center;
}
.who-we-are-box {
    width: min(950px, 100%);
    margin: 0 auto;
    text-align: center;
}
.who-we-are-box p {
    text-align: center;
    font-weight: 700;
    text-indent: 2em;
    line-height: 1.9;
    margin: 0;
}
.who-we-are-box p + p {
    margin-top: 32px;
}
.mission-white { color: #fff !important; text-align: center; }
.project-mini-grid { justify-content: center; align-items: stretch; }
.project-mini-card { max-width: 330px; margin: 0 auto; text-align: center; }
.project-mini-card p { text-align: center; }
.service-center { justify-content: center; align-items: stretch; }
.service-center .service-card { max-width: 360px; margin: 0 auto; text-align: center; }
.service-center .service-card p { text-align: center; white-space: pre-line; }
.gallery-grid { justify-items: center; }
.gallery-card { text-align: center; }
.gallery-caption { text-align: center; }
.gallery-caption h3, .gallery-caption p { text-align: center; }
.news-grid { text-align: center; }

/* =====================================================
   GALLERY
===================================================== */

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 24px;
    align-items: stretch;
}

.gallery-card {
    width: 100%;
    height: 520px;
    min-height: 520px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: var(--card);
    border-radius: 22px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border);
    box-sizing: border-box;
}

.gallery-image-link {
    display: block;
    position: relative;
    flex: 0 0 300px;
    width: 100%;
    height: 300px;
    overflow: hidden;
    background: var(--purple-soft);
    text-decoration: none;
}

.gallery-card img,
.gallery-image-link img {
    display: block;
    width: 100%;
    height: 300px;
    object-fit: cover;
    object-position: center;
    background: var(--purple-soft);
    content-visibility: auto;
    transition: transform .25s ease, opacity .2s ease;
}

.gallery-image-link:hover img {
    transform: scale(1.035);
}

.gallery-image-error {
    display: none;
    width: 100%;
    height: 300px;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    text-align: center;
}

.gallery-caption {
    flex: 1 1 auto;
    min-height: 220px;
    box-sizing: border-box;
    width: 100%;
    padding: 22px 20px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    background: var(--card);
}

.gallery-caption h3 {
    width: 100%;
    min-height: 32px;
    margin: 0 0 10px;
    color: var(--purple);
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.gallery-caption p {
    width: 100%;
    min-height: 52px;
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
    text-align: center;
}

.gallery-delete-form {
    width: 100%;
    margin-top: auto;
    padding-top: 16px;
}

.gallery-delete-button {
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 11px 16px;
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #fff;
    font-weight: 800;
    cursor: pointer;
    transition: transform .2s ease, box-shadow .2s ease;
}

.gallery-delete-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 22px rgba(220, 38, 38, .22);
}

@media (max-width: 900px) {
    .gallery-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 650px) {
    .gallery-grid {
        grid-template-columns: 1fr;
    }
}


/* =====================================================
   FOUNDERS
===================================================== */

.owners {

    display:
        grid;

    grid-template-columns:
        repeat(
            2,
            minmax(0,1fr)
        );

    gap:
        28px;
}


.owner-card {

    overflow:
        hidden;

    background:
        var(--card);

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    border-top:
        5px solid
        var(--pink);
}


.owner-photo {

    width:
        100%;

    height:
        430px;

    object-fit:
        cover;

    object-position:
        center top;

    display:
        block;

    background:
        var(--purple-soft);
}


.owner-info {

    padding:
        25px;
}


.owner-info h3 {

    color:
        var(--purple);

    font-size:
        24px;

    margin-bottom:
        5px;
}


.owner-role {

    color:
        var(--pink);

    font-weight:
        900;

    margin-bottom:
        12px;
}


.owner-info p {

    color:
        var(--muted);
}



.coordinator-section {
    margin-top: 55px;
    text-align: center;
}

.coordinator-section-title {
    color: var(--purple);
    font-size: clamp(28px, 4vw, 40px);
    margin: 0 0 10px;
}

.coordinator-grid {
    max-width: 1050px;
    margin: 25px auto 0;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 28px;
}

.coordinator-card {
    overflow: hidden;
    background: var(--card);
    border-radius: 22px;
    box-shadow: var(--shadow);
    border-top: 5px solid var(--purple);
    text-align: center;
}

.coordinator-photo {
    width: 100%;
    height: 430px;
    object-fit: cover;
    object-position: center top;
    display: block;
    background: var(--purple-soft);
}

.coordinator-info {
    padding: 25px;
}

.coordinator-info h3 {
    color: var(--purple);
    font-size: 24px;
    margin: 0 0 8px;
}

.coordinator-role {
    color: var(--pink);
    font-weight: 900;
    margin-bottom: 8px;
}

.coordinator-location {
    color: var(--muted);
    font-weight: 700;
    margin: 0;
}

@media (max-width: 760px) {
    .coordinator-grid {
        grid-template-columns: 1fr;
    }
}

/* =====================================================
   GAMES
===================================================== */

.games {

    padding:
        85px 22px;

    background:
        var(--purple-soft);
}


.game-grid {

    max-width:
        1200px;

    margin:
        auto;

    display:
        grid;

    grid-template-columns:
        repeat(
            4,
            minmax(0,1fr)
        );

    gap:
        20px;
}


.game {

    background:
        var(--card);

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    padding:
        25px;

    text-align:
        center;
}


.game h3 {

    color:
        var(--purple);

    margin-bottom:
        8px;
}


.game p {

    color:
        var(--muted);

    margin-bottom:
        10px;
}


.game button {

    margin:
        5px 3px;

    padding:
        9px 13px;

    border:
        0;

    border-radius:
        12px;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--pink)
        );

    color:
        white;

    cursor:
        pointer;

    font-weight:
        800;
}


.result {

    min-height:
        28px;

    margin-top:
        10px;

    color:
        var(--purple);

    font-weight:
        900;
}


/* =====================================================
   CONTACT
===================================================== */

.contact {

    max-width:
        900px;

    margin:
        auto;

    padding:
        40px 25px;

    background:
        var(--card);

    border-radius:
        25px;

    text-align:
        center;

    box-shadow:
        var(--shadow);
}


.contact h2 {

    color:
        var(--purple);

    font-size:
        38px;
}


.contact p {

    color:
        var(--muted);

    margin:
        8px 0;
}


/* =====================================================
   JOURNEY
===================================================== */

.join {

    max-width:
        900px;

    margin:
        30px auto 0;

    padding:
        35px 20px;

    text-align:
        center;

    border-radius:
        25px;

    background:
        var(--purple-soft);

    box-shadow:
        var(--shadow);
}


.join h2 {

    color:
        var(--purple);

    font-size:
        38px;

    margin-bottom:
        8px;
}


.join p {

    color:
        var(--muted);

    margin:
        5px 0;
}


/* =====================================================
   VIEWER COUNTER
===================================================== */

.viewer-counter {

    display:
        inline-block;

    margin-top:
        18px;

    padding:
        10px 18px;

    border-radius:
        25px;

    background:
        var(--purple);

    color:
        white;

    font-size:
        16px;

    font-weight:
        900;
}


.viewer-counter strong {

    color:
        #e9d5ff;

    font-size:
        21px;
}


/* =====================================================
   FOOTER
===================================================== */

footer {

    margin-top:
        50px;

    padding:
        30px 20px;

    text-align:
        center;

    background:
        var(--purple-deep);

    color:
        #eee7ff;
}


.footer-logo {

    font-size:
        36px;

    font-weight:
        1000;

    color:
        #e9d5ff;
}


/* =====================================================
   TOP BUTTON
===================================================== */

.top {

    position:
        fixed;

    right:
        20px;

    bottom:
        20px;

    display:
        none;

    width:
        48px;

    height:
        48px;

    border:
        none;

    border-radius:
        50%;

    background:
        var(--purple);

    color:
        white;

    font-size:
        20px;

    cursor:
        pointer;

    z-index:
        9999;
}


/* =====================================================
   MOBILE
===================================================== */

@media(max-width:1100px) {

    .gallery-grid {

        grid-template-columns:
            repeat(
                2,
                minmax(0,1fr)
            );
    }

    .game-grid {

        grid-template-columns:
            repeat(
                2,
                minmax(0,1fr)
            );
    }

}


@media(max-width:850px) {

    nav {

        flex-direction:
            column;
    }

    .owners {

        grid-template-columns:
            1fr;
    }

}


@media(max-width:650px) {

    .nav-links {

        gap:
            6px;
    }

    .nav-links a {

        font-size:
            10px;
    }

    .gallery-grid,
    .cards,
    .mission,
    .services,
    .stats,
    .game-grid {

        grid-template-columns:
            1fr;
    }

    .owner-photo {

        height:
            360px;
    }

    .gallery-card img {

        height:
            300px;
    }

    .title {

        font-size:
            34px;
    }

    .hero {

        min-height:
            620px;
    }

}


/* =====================================================
   LOGIN / REGISTER / UPLOAD
===================================================== */
.auth-box {
    max-width: 520px;
    margin: 35px auto;
    padding: 30px;
    background: var(--card);
    border-radius: 22px;
    box-shadow: var(--shadow);
    border-top: 5px solid var(--purple);
}
.auth-box input[type="text"],
.auth-box input[type="password"],
.auth-box input[type="file"] {
    width: 100%;
    padding: 13px;
    margin: 8px 0 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--background);
    color: var(--text);
}
.auth-submit, .upload-submit {
    border: 0;
    border-radius: 12px;
    padding: 12px 18px;
    background: linear-gradient(135deg,var(--purple),var(--pink));
    color: white;
    cursor: pointer;
    font-weight: 800;
}
.auth-message {
    padding: 10px 14px;
    margin-bottom: 15px;
    border-radius: 10px;
    background: var(--purple-soft);
    color: var(--purple);
    font-weight: 700;
}
.gallery-upload {
    margin-bottom: 30px;
}
.gallery-upload small {
    color: var(--muted);
}
.gallery-card img {
    object-fit: cover;
}

/* =====================================================
   COLORFUL / INTERACTIVE GALLERY
===================================================== */
.gallery-upload {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(124,58,237,.16), rgba(236,72,153,.14), rgba(59,130,246,.12));
    border: 2px solid transparent;
    background-clip: padding-box;
    box-shadow: 0 18px 45px rgba(124,58,237,.15);
}
.gallery-upload::before {
    content: "";
    position: absolute;
    width: 180px;
    height: 180px;
    right: -70px;
    top: -80px;
    border-radius: 50%;
    background: rgba(236,72,153,.20);
    pointer-events: none;
}
.gallery-upload input[type=file] {
    border: 2px dashed #a855f7;
    background: rgba(255,255,255,.65);
    transition: .2s ease;
}
body.dark .gallery-upload input[type=file] { background: rgba(20,20,35,.7); }
.gallery-upload input[type=file]:hover {
    border-color: #ec4899;
    transform: translateY(-1px);
}
.gallery-meta-row {
    position: relative;
    background: linear-gradient(135deg, rgba(124,58,237,.09), rgba(236,72,153,.08));
    border: 1px solid rgba(124,58,237,.28);
    box-shadow: 0 8px 24px rgba(124,58,237,.08);
}
.gallery-file-name {
    font-weight: 800;
    color: var(--purple);
    margin-bottom: 9px;
    overflow-wrap: anywhere;
}
.gallery-meta-row input:focus, .gallery-meta-row textarea:focus {
    outline: none;
    border-color: #a855f7;
    box-shadow: 0 0 0 4px rgba(168,85,247,.13);
}
.gallery-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    align-items: stretch;
}
.gallery-card {
    transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
    position: relative;
}
.gallery-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 4px;
    background: linear-gradient(90deg, #7c3aed, #ec4899, #06b6d4);
    z-index: 2;
}
.gallery-card:hover {
    transform: translateY(-7px);
    box-shadow: 0 22px 50px rgba(76,29,149,.20);
    border-color: rgba(168,85,247,.45);
}
.gallery-image-link { overflow: hidden; }
.gallery-image-link img {
    transition: transform .35s ease, filter .35s ease;
}
.gallery-card:hover .gallery-image-link img {
    transform: scale(1.055);
    filter: saturate(1.08) contrast(1.03);
}
.gallery-caption {
    padding: 18px 18px 20px;
    background: linear-gradient(180deg, var(--card), rgba(124,58,237,.045));
}
.gallery-caption h3 { margin-bottom: 8px; }
.gallery-caption p { color: var(--muted); line-height: 1.65; }
.gallery-card {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 560px;
    min-height: 560px;
    box-sizing: border-box;
}
.gallery-card .gallery-image-link {
    height: 300px;
    min-height: 300px;
    flex: 0 0 300px;
}
.gallery-card .gallery-image-link img {
    width: 100%;
    height: 300px;
    min-height: 300px;
    object-fit: cover;
    display: block;
}
.gallery-card .gallery-image-link {
    width: 100%;
    flex: 0 0 auto;
}
.gallery-card .gallery-caption {
    width: 100%;
    flex: 1 1 auto;
    min-height: 100%;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    box-sizing: border-box;
    border-radius: 0 0 22px 22px;
}
.gallery-card.uploaded-gallery-card {
    overflow: hidden;
}
.gallery-card.uploaded-gallery-card .gallery-caption {
    min-height: 0;
}
.gallery-delete-form {
    margin-top: auto !important;
}
.gallery-card .gallery-caption h3,
.gallery-card .gallery-caption p {
    width: 100%;
    box-sizing: border-box;
}
.gallery-delete-form {
    width: 100%;
    margin-top: auto;
    padding-top: 16px;
}
.gallery-delete-button {
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 11px 16px;
    background: linear-gradient(135deg, #dc2626, #be123c);
    color: #fff;
    font-weight: 800;
    cursor: pointer;
    transition: transform .2s ease, box-shadow .2s ease, opacity .2s ease;
}
.gallery-delete-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(190,18,60,.25);
    opacity: .95;
}

@media (max-width: 900px) {
    .gallery-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 600px) {
    .gallery-grid { grid-template-columns: 1fr; }
}

/* =====================================================
   JHR ULTRA PREMIUM UI — VISUAL OVERRIDE
===================================================== */
:root{
  --jhr-bg:#f7f5ff;--jhr-surface:rgba(255,255,255,.78);--jhr-solid:#fff;
  --jhr-ink:#171225;--jhr-muted:#6d6680;--jhr-line:rgba(111,76,190,.16);
  --jhr-purple:#6d28d9;--jhr-violet:#8b5cf6;--jhr-pink:#db2777;--jhr-blue:#2563eb;
  --jhr-shadow:0 24px 70px rgba(53,28,104,.14);--jhr-soft-shadow:0 12px 35px rgba(53,28,104,.10);
}
html{scroll-padding-top:100px}
body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;background:radial-gradient(circle at 10% 0%,rgba(139,92,246,.16),transparent 28%),radial-gradient(circle at 90% 8%,rgba(219,39,119,.12),transparent 24%),linear-gradient(180deg,#fbfaff 0%,#f5f0ff 48%,#fff 100%);color:var(--jhr-ink);line-height:1.65}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:-1;background-image:radial-gradient(rgba(109,40,217,.07) 1px,transparent 1px);background-size:28px 28px;mask-image:linear-gradient(to bottom,#000,transparent 75%)}
body.dark{--jhr-bg:#0b0712;--jhr-surface:rgba(27,18,42,.82);--jhr-solid:#1b1228;--jhr-ink:#fff;--jhr-muted:#c7bdd4;--jhr-line:rgba(196,160,255,.17);background:radial-gradient(circle at 10% 0%,rgba(124,58,237,.2),transparent 28%),radial-gradient(circle at 90% 10%,rgba(236,72,153,.14),transparent 24%),linear-gradient(180deg,#09060f,#140b20 60%,#0c0713)}
body.dark:before{background-image:radial-gradient(rgba(196,160,255,.07) 1px,transparent 1px)}

/* Navigation */
nav{position:sticky!important;top:14px!important;z-index:1000!important;width:min(1380px,calc(100% - 32px));margin:14px auto 0!important;padding:12px 16px!important;border:1px solid var(--jhr-line)!important;border-radius:22px!important;background:rgba(255,255,255,.72)!important;backdrop-filter:blur(24px) saturate(160%)!important;box-shadow:0 14px 50px rgba(39,20,77,.13)!important;display:flex!important;align-items:center!important;gap:18px!important}
body.dark nav{background:rgba(20,12,31,.76)!important;border-color:rgba(196,160,255,.18)!important}
.logo{display:flex!important;align-items:center!important;gap:10px!important;padding:5px 12px 5px 5px!important;border-radius:16px!important;color:var(--jhr-ink)!important;text-decoration:none!important;font-weight:950!important;font-size:21px!important;letter-spacing:-.04em!important;white-space:nowrap}
.logo img{border-radius:13px!important;box-shadow:0 8px 20px rgba(109,40,217,.22)!important}
.logo:hover{background:rgba(139,92,246,.09)!important}
.nav-links{display:flex!important;align-items:center!important;justify-content:center!important;gap:3px!important;flex:1!important;min-width:0!important}
.nav-links a{padding:9px 11px!important;border-radius:11px!important;color:var(--jhr-muted)!important;text-decoration:none!important;font-size:13px!important;font-weight:800!important;transition:.2s ease!important;white-space:nowrap}
.nav-links a:hover{color:var(--jhr-purple)!important;background:rgba(139,92,246,.10)!important;transform:translateY(-1px)!important}
.nav-controls{display:flex!important;gap:7px!important;align-items:center!important}
.nav-btn{border:1px solid var(--jhr-line)!important;background:rgba(255,255,255,.66)!important;color:var(--jhr-ink)!important;border-radius:12px!important;padding:9px 12px!important;font-weight:850!important;box-shadow:none!important;transition:.2s ease!important}
.nav-btn:hover{transform:translateY(-2px)!important;border-color:rgba(109,40,217,.35)!important;background:rgba(139,92,246,.11)!important}
body.dark .nav-btn{background:rgba(255,255,255,.05)!important}

/* Hero */
.hero{position:relative!important;min-height:680px!important;margin:18px auto 0!important;width:min(1380px,calc(100% - 32px));border-radius:40px!important;overflow:hidden!important;display:grid!important;place-items:center!important;background:radial-gradient(circle at 50% 25%,rgba(255,255,255,.22),transparent 28%),linear-gradient(135deg,#32106f 0%,#6d28d9 42%,#a21caf 72%,#db2777 100%)!important;box-shadow:0 35px 90px rgba(76,29,149,.30)!important}
.hero:before,.hero:after{content:"";position:absolute;border-radius:999px;filter:blur(3px);opacity:.45;pointer-events:none}
.hero:before{width:430px;height:430px;right:-130px;top:-160px;background:radial-gradient(circle,#fff,transparent 65%)}
.hero:after{width:520px;height:520px;left:-220px;bottom:-300px;background:radial-gradient(circle,#06b6d4,transparent 65%)}
.hero-content{position:relative!important;z-index:2!important;width:min(920px,92%)!important;padding:70px 20px!important;text-align:center!important}
.hero .badge{display:inline-flex!important;padding:9px 15px!important;border:1px solid rgba(255,255,255,.28)!important;border-radius:999px!important;background:rgba(255,255,255,.13)!important;backdrop-filter:blur(10px)!important;color:#fff!important;font-size:11px!important;letter-spacing:.13em!important;box-shadow:0 10px 30px rgba(0,0,0,.12)!important}
.hero h1{font-size:clamp(72px,13vw,150px)!important;line-height:.88!important;letter-spacing:-.09em!important;color:#fff!important;text-shadow:0 16px 45px rgba(0,0,0,.22)!important;margin:26px 0 12px!important;font-weight:1000!important}
.hero-organization-title{display:block!important;width:100%!important;max-width:none!important;font-size:clamp(22px,2.45vw,38px)!important;line-height:1.08!important;color:#fff!important;letter-spacing:-.04em!important;margin:0 auto 20px!important;text-align:center!important;white-space:nowrap!important}
.hero-content .hero-message{font-size:clamp(16px,1.8vw,21px)!important;line-height:1.8!important;color:rgba(255,255,255,.9)!important;max-width:760px!important}

/* Sections */
.section,.color-section{width:min(1240px,calc(100% - 32px));margin:0 auto!important;padding:105px 0!important;position:relative}
.color-section{width:100%;padding-left:max(16px,calc((100% - 1240px)/2));padding-right:max(16px,calc((100% - 1240px)/2));background:linear-gradient(135deg,#21103e,#4c1d95 48%,#7e22ce);color:#fff;overflow:hidden}
.color-section:before{content:"";position:absolute;width:480px;height:480px;right:-180px;top:-220px;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.16),transparent 65%)}
.title{font-size:clamp(34px,5vw,58px)!important;line-height:1.05!important;letter-spacing:-.055em!important;color:var(--jhr-ink)!important;margin:0 0 18px!important;font-weight:950!important;text-align:center!important}
.color-section .title{color:#fff!important}.subtitle{font-size:18px!important;color:var(--jhr-muted)!important;text-align:center!important;max-width:760px;margin:0 auto 38px!important}.color-section .subtitle{color:rgba(255,255,255,.82)!important}

/* Generic cards */
.card,.mission-card,.service-card,.project-mini-card,.news-card,.owner-card{background:var(--jhr-surface)!important;border:1px solid var(--jhr-line)!important;box-shadow:var(--jhr-soft-shadow)!important;border-radius:26px!important;backdrop-filter:blur(16px)!important;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease!important}
.card:hover,.mission-card:hover,.service-card:hover,.project-mini-card:hover,.news-card:hover,.owner-card:hover{transform:translateY(-7px)!important;box-shadow:var(--jhr-shadow)!important;border-color:rgba(109,40,217,.28)!important}
.who-we-are-box{padding:38px!important;max-width:980px!important}
.who-we-are-box p{color:var(--jhr-muted)!important;font-size:17px!important;line-height:1.95!important}
.mission{position:relative;z-index:2;display:grid!important;grid-template-columns:repeat(4,1fr)!important;gap:18px!important}
.mission-card{padding:30px!important;background:rgba(255,255,255,.09)!important;border-color:rgba(255,255,255,.15)!important;color:#fff!important;text-align:left!important}
.mission-card h3{color:#fff!important;font-size:21px!important}.mission-card p{color:rgba(255,255,255,.72)!important}.mission-icon{font-size:38px!important;margin-bottom:18px!important}

/* Buttons */
button,.auth-submit,.upload-submit{font-family:inherit!important;box-shadow:0 10px 25px rgba(109,40,217,.18)!important;transition:transform .2s ease,box-shadow .2s ease,filter .2s ease!important}
button:hover,.auth-submit:hover,.upload-submit:hover{transform:translateY(-2px)!important;filter:brightness(1.04)!important;box-shadow:0 15px 32px rgba(109,40,217,.25)!important}

/* Gallery */
.gallery-grid{gap:24px!important;align-items:stretch!important}
.gallery-card{border-radius:26px!important;background:var(--jhr-solid)!important;border:1px solid var(--jhr-line)!important;box-shadow:var(--jhr-soft-shadow)!important;overflow:hidden!important;display:flex!important;flex-direction:column!important;min-height:100%!important}
.gallery-card:hover{transform:translateY(-8px)!important;box-shadow:0 28px 65px rgba(53,28,104,.18)!important}
.gallery-card .gallery-image-link{height:300px!important;background:linear-gradient(135deg,#ede9fe,#fce7f3)!important}
.gallery-card .gallery-image-link img{height:100%!important;width:100%!important;object-fit:cover!important}
.gallery-caption{flex:1 1 auto!important;width:100%!important;padding:24px!important;background:linear-gradient(180deg,var(--jhr-solid),rgba(139,92,246,.055))!important;display:flex!important;flex-direction:column!important;text-align:left!important}
.gallery-caption h3{font-size:20px!important;color:var(--jhr-ink)!important;letter-spacing:-.02em!important}.gallery-caption p{font-size:14px!important;color:var(--jhr-muted)!important;line-height:1.7!important}
.gallery-delete-form{margin-top:auto!important;padding-top:18px!important}.gallery-delete-button{border-radius:13px!important}
.gallery-upload{border-radius:28px!important;padding:30px!important;box-shadow:var(--jhr-shadow)!important;border:1px solid rgba(109,40,217,.18)!important}
.gallery-meta-row{border-radius:18px!important;padding:18px!important;background:rgba(255,255,255,.6)!important}
body.dark .gallery-meta-row{background:rgba(255,255,255,.035)!important}

/* News / project / services */
.news-grid{gap:22px!important}.news-card{padding:26px!important}.news-card h3{font-size:22px!important;letter-spacing:-.025em!important}.news-card p{line-height:1.75!important}
.project-mini-card,.service-center .service-card{padding:28px!important}

/* Stats */
.stats>*,.stat-card{border-radius:22px!important;border:1px solid var(--jhr-line)!important;background:var(--jhr-surface)!important;box-shadow:var(--jhr-soft-shadow)!important}

/* Forms */
.auth-box{border:1px solid var(--jhr-line)!important;border-top:0!important;border-radius:30px!important;background:rgba(255,255,255,.86)!important;backdrop-filter:blur(20px)!important;box-shadow:0 30px 90px rgba(53,28,104,.2)!important;padding:42px!important}
body.dark .auth-box{background:rgba(27,18,42,.88)!important}.auth-box input,.auth-box textarea,.gallery-meta-row input,.gallery-meta-row textarea{border:1px solid var(--jhr-line)!important;border-radius:14px!important;transition:.2s ease!important}.auth-box input:focus,.gallery-meta-row input:focus,.gallery-meta-row textarea:focus{outline:none!important;border-color:var(--jhr-violet)!important;box-shadow:0 0 0 4px rgba(139,92,246,.13)!important}

/* Footer */
/* Header brand + tagline */
.logo{display:flex!important;align-items:center!important;gap:10px!important}
.logo-name-wrap{display:flex!important;align-items:center!important;gap:9px!important;white-space:nowrap!important}
.logo-name-wrap strong{font-size:22px!important;line-height:1!important;color:var(--jhr-ink)!important}
.logo-name-wrap small{font-size:11px!important;font-weight:800!important;letter-spacing:.01em!important;color:var(--jhr-muted)!important;line-height:1.1!important}
body.dark .logo-name-wrap strong{color:#fff!important}
body.dark .logo-name-wrap small{color:#ddd3eb!important}

/* Footer: always readable in light and dark mode */
footer{margin-top:30px!important;border-top:1px solid var(--jhr-line)!important;background:#f7f4fb!important;color:#241632!important;backdrop-filter:blur(18px)!important;text-align:center!important}
footer .footer-logo{color:#5b21b6!important}
footer p{color:#3f3150!important}
body.dark footer{background:#120b1c!important;color:#f5effb!important}
body.dark footer .footer-logo{color:#d8b4fe!important}
body.dark footer p{color:#e9def2!important}

/* Scrollbar / selection */
::selection{background:#8b5cf6;color:#fff}::-webkit-scrollbar{width:10px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:linear-gradient(#7c3aed,#db2777);border-radius:999px;border:2px solid transparent;background-clip:padding-box}

/* Mobile */
@media(max-width:1050px){nav{flex-wrap:wrap}.nav-links{order:3;flex-basis:100%;overflow-x:auto;justify-content:flex-start;padding-top:3px}.mission{grid-template-columns:repeat(2,1fr)!important}.hero{min-height:600px!important}}
@media(max-width:700px){nav{top:7px!important;width:calc(100% - 16px)!important;margin-top:7px!important;border-radius:18px!important}.logo{margin-right:auto}.nav-controls{gap:4px}.nav-btn{padding:8px 9px!important}.nav-links a{font-size:12px!important}.hero,.section,.color-section{width:calc(100% - 16px)}.hero{min-height:570px!important;border-radius:28px!important}.hero-organization-title{font-size:clamp(25px,7vw,38px)!important;line-height:1.08!important;white-space:normal!important}.section{padding:72px 0!important}.color-section{width:100%;padding-left:16px;padding-right:16px}.mission{grid-template-columns:1fr!important}.gallery-grid{grid-template-columns:1fr!important}.gallery-card .gallery-image-link{height:270px!important}.who-we-are-box{padding:25px!important}.who-we-are-box p{font-size:15px!important}.title{font-size:39px!important}.auth-box{padding:28px!important;margin:20px 10px}}



/* =====================================================
   JHR ULTRA INTERACTIVE EXPERIENCE
===================================================== */
:root{--jhr-ease:cubic-bezier(.2,.8,.2,1)}
html{scroll-behavior:smooth}
body{overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:9998;background:radial-gradient(500px circle at var(--mx,50%) var(--my,20%),rgba(139,92,246,.09),transparent 55%);transition:opacity .25s;}
#jhr-progress{position:fixed;left:0;top:0;height:4px;width:0;z-index:10000;background:linear-gradient(90deg,#7c3aed,#ec4899,#06b6d4);box-shadow:0 0 18px rgba(168,85,247,.7);border-radius:0 99px 99px 0}
.nav-links a{position:relative;padding:9px 11px;border-radius:12px;transition:transform .25s var(--jhr-ease),background .25s,color .25s}
.nav-links a::after{content:"";position:absolute;left:12px;right:12px;bottom:4px;height:2px;border-radius:10px;background:linear-gradient(90deg,#8b5cf6,#ec4899);transform:scaleX(0);transform-origin:center;transition:transform .25s var(--jhr-ease)}
.nav-links a:hover{transform:translateY(-2px);background:rgba(139,92,246,.10)}
.nav-links a:hover::after{transform:scaleX(1)}
.button,.nav-btn,button{transition:transform .25s var(--jhr-ease),box-shadow .25s,filter .25s!important}
.button:hover,.nav-btn:hover,button:hover{box-shadow:0 14px 34px rgba(124,58,237,.25);filter:saturate(1.12)}
.hero{position:relative;overflow:hidden}
.hero::before,.hero::after{content:"";position:absolute;border-radius:50%;pointer-events:none;filter:blur(2px);opacity:.45}
.hero::before{width:420px;height:420px;left:-130px;top:-100px;background:radial-gradient(circle,rgba(236,72,153,.45),transparent 68%);animation:jhrFloat 9s ease-in-out infinite}
.hero::after{width:520px;height:520px;right:-180px;bottom:-180px;background:radial-gradient(circle,rgba(34,211,238,.25),transparent 68%);animation:jhrFloat 11s ease-in-out infinite reverse}
.hero-content{position:relative;z-index:2}
.badge{animation:jhrPulse 3s ease-in-out infinite}
.hero h1{background:linear-gradient(90deg,#fff,#e9d5ff,#fff,#fbcfe8);background-size:250% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:jhrGradient 7s linear infinite;text-shadow:none}
.card,.gallery-card,.owner-card,.project-mini-card,.service-card,.news-card,.mission-card{transition:transform .35s var(--jhr-ease),box-shadow .35s,border-color .35s,background .35s;will-change:transform}
.card:hover,.gallery-card:hover,.owner-card:hover,.project-mini-card:hover,.service-card:hover,.news-card:hover,.mission-card:hover{box-shadow:0 25px 70px rgba(31,15,52,.22);border-color:rgba(139,92,246,.35)}
.gallery-card{position:relative}
.gallery-card::before,.news-card::before,.service-card::before,.project-mini-card::before{content:"";position:absolute;inset:0;pointer-events:none;border-radius:inherit;background:linear-gradient(135deg,rgba(255,255,255,.12),transparent 35%,transparent 70%,rgba(139,92,246,.08));opacity:0;transition:opacity .35s}
.gallery-card:hover::before,.news-card:hover::before,.service-card:hover::before,.project-mini-card:hover::before{opacity:1}
.gallery-image-link{overflow:hidden}
.gallery-image-link img{transition:transform .65s var(--jhr-ease),filter .65s!important}
.gallery-card:hover .gallery-image-link img{transform:scale(1.075)!important;filter:saturate(1.12) contrast(1.03)}
.gallery-caption{position:relative}
.gallery-caption::before{content:"";position:absolute;left:0;top:0;width:54px;height:3px;background:linear-gradient(90deg,#7c3aed,#ec4899);border-radius:99px}
.reveal{opacity:0;transform:translateY(26px);transition:opacity .75s var(--jhr-ease),transform .75s var(--jhr-ease)}
.reveal.is-visible{opacity:1;transform:none}
.jhr-section-glow{position:relative}
.jhr-section-glow::before{content:"";position:absolute;left:50%;top:0;width:220px;height:2px;transform:translateX(-50%);background:linear-gradient(90deg,transparent,#8b5cf6,#ec4899,transparent);opacity:.8}
#jhr-lightbox{position:fixed;inset:0;z-index:10001;display:none;align-items:center;justify-content:center;padding:24px;background:rgba(5,3,12,.88);backdrop-filter:blur(16px)}
#jhr-lightbox.open{display:flex;animation:jhrFade .2s ease}
#jhr-lightbox img{max-width:min(1200px,94vw);max-height:88vh;object-fit:contain;border-radius:20px;box-shadow:0 30px 100px rgba(0,0,0,.55)}
#jhr-lightbox-close{position:absolute;top:20px;right:22px;width:48px;height:48px;border:0;border-radius:50%;background:rgba(255,255,255,.12);color:#fff;font-size:28px;cursor:pointer}
.jhr-ripple{position:relative;overflow:hidden}
.jhr-ripple-dot{position:absolute;border-radius:50%;background:rgba(255,255,255,.4);transform:scale(0);animation:jhrRipple .55s ease-out;pointer-events:none}
@keyframes jhrFloat{0%,100%{transform:translate3d(0,0,0)}50%{transform:translate3d(22px,18px,0)}}
@keyframes jhrPulse{0%,100%{box-shadow:0 0 0 0 rgba(167,139,250,0)}50%{box-shadow:0 0 0 9px rgba(167,139,250,.08)}}
@keyframes jhrGradient{to{background-position:250% center}}
@keyframes jhrFade{from{opacity:0}to{opacity:1}}
@keyframes jhrRipple{to{transform:scale(5);opacity:0}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation:none!important;transition:none!important}.reveal{opacity:1;transform:none}}
@media(max-width:700px){ #jhr-progress{height:3px}.hero h1{letter-spacing:2px}.button{min-height:44px}.nav-links a{min-height:40px;display:inline-flex;align-items:center}}



/* JHR CYBER-FUTURE VISUAL SYSTEM — deliberate sci-fi direction */
:root{--jhr-cyber-ink:#edfaff;--jhr-cyber-muted:#9cb6d0;--jhr-cyber-cyan:#54f4ff;--jhr-cyber-purple:#9b8cff;--jhr-cyber-pink:#ff52d9;--jhr-cyber-line:rgba(84,244,255,.2)}
html{background:#050713!important;scrollbar-color:#685cff #050713}
body{background-color:#050713!important;background-image:radial-gradient(ellipse at 12% 0%,rgba(79,48,190,.19),transparent 32%),radial-gradient(ellipse at 94% 20%,rgba(0,220,255,.09),transparent 27%),linear-gradient(rgba(84,244,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(84,244,255,.025) 1px,transparent 1px)!important;background-size:auto,auto,42px 42px,42px 42px!important;background-attachment:fixed!important;color:var(--jhr-cyber-ink)!important}
body:after{content:"";position:fixed;inset:0;z-index:9990;pointer-events:none;opacity:.11;background:repeating-linear-gradient(to bottom,transparent 0,transparent 3px,rgba(145,220,255,.1) 4px);mix-blend-mode:screen}
body:not(.dark){--jhr-ink:#edfaff!important;--jhr-muted:#9cb6d0!important;--jhr-line:rgba(84,244,255,.2)!important;--jhr-surface:rgba(10,17,36,.88)!important;--jhr-soft-shadow:0 18px 50px rgba(0,0,0,.25)!important;color:#edfaff!important}
nav{background:rgba(5,9,24,.82)!important;border:1px solid rgba(84,244,255,.19)!important;border-radius:18px!important;box-shadow:0 12px 55px rgba(0,0,0,.32),0 0 32px rgba(84,244,255,.035)!important;backdrop-filter:blur(24px) saturate(150%)!important}
.logo-name-wrap strong,.logo-name-wrap small{color:#edfaff!important}
.logo-name-wrap strong{letter-spacing:.13em!important;text-shadow:0 0 24px rgba(84,244,255,.18)}
.nav-links a{color:#adc5df!important;font-size:12px!important;font-weight:800!important;letter-spacing:.07em!important;text-transform:uppercase!important}
.nav-links a:hover{background:rgba(84,244,255,.08)!important;color:#fff!important}
.nav-btn{border:1px solid rgba(84,244,255,.2)!important;background:rgba(84,244,255,.06)!important;color:#c7fbff!important}
.hero{position:relative!important;isolation:isolate!important;min-height:min(790px,calc(100svh - 110px))!important;margin-top:24px!important;border:1px solid rgba(84,244,255,.27)!important;border-radius:28px!important;overflow:hidden!important;background:radial-gradient(ellipse at 50% 42%,rgba(72,48,178,.22),transparent 38%),radial-gradient(ellipse at 80% 20%,rgba(0,226,255,.12),transparent 30%),linear-gradient(135deg,#06091a 0%,#0b1026 48%,#140d2b 100%)!important;box-shadow:0 35px 100px rgba(0,0,0,.38),0 0 70px rgba(84,244,255,.045),inset 0 0 90px rgba(84,244,255,.025)!important}
.hero:before{content:""!important;position:absolute!important;inset:0!important;width:auto!important;height:auto!important;left:0!important;top:0!important;right:0!important;bottom:0!important;border-radius:0!important;filter:none!important;opacity:.65!important;pointer-events:none!important;background:linear-gradient(rgba(84,244,255,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(84,244,255,.07) 1px,transparent 1px),radial-gradient(circle at 50% 50%,transparent 0 150px,rgba(84,244,255,.1) 151px,transparent 153px,transparent 220px,rgba(155,140,255,.09) 221px,transparent 223px)!important;background-size:34px 34px,34px 34px,auto!important;mask-image:radial-gradient(ellipse at center,black,transparent 88%)!important;animation:none!important;z-index:-1!important}
.hero:after{content:""!important;position:absolute!important;inset:18px!important;width:auto!important;height:auto!important;left:18px!important;right:18px!important;top:18px!important;bottom:18px!important;border-radius:18px!important;filter:none!important;opacity:.65!important;background:linear-gradient(var(--jhr-cyber-cyan),var(--jhr-cyber-cyan)) left top/54px 2px no-repeat,linear-gradient(var(--jhr-cyber-cyan),var(--jhr-cyber-cyan)) left top/2px 54px no-repeat,linear-gradient(var(--jhr-cyber-purple),var(--jhr-cyber-purple)) right bottom/54px 2px no-repeat,linear-gradient(var(--jhr-cyber-purple),var(--jhr-cyber-purple)) right bottom/2px 54px no-repeat!important;pointer-events:none!important;animation:none!important;z-index:1!important}
.hero-content{width:min(1000px,94%)!important;padding:clamp(60px,9vw,130px) 20px!important}
.hero .badge{background:rgba(84,244,255,.07)!important;border:1px solid rgba(84,244,255,.34)!important;border-radius:5px!important;color:#8ff8ff!important;box-shadow:0 0 26px rgba(84,244,255,.08),inset 0 0 20px rgba(84,244,255,.035)!important;letter-spacing:.23em!important}
.hero h1{font-size:clamp(78px,15vw,174px)!important;line-height:.83!important;letter-spacing:-.085em!important;font-weight:1000!important;background:linear-gradient(115deg,#fff 4%,#9dfaff 35%,#a89cff 65%,#ff8be8 95%)!important;background-size:180% auto!important;-webkit-background-clip:text!important;background-clip:text!important;color:transparent!important;text-shadow:0 0 60px rgba(84,244,255,.08)!important;filter:drop-shadow(0 0 25px rgba(84,244,255,.12))!important}
.hero-organization-title{color:#d6eaff!important;letter-spacing:.015em!important;font-weight:750!important;text-shadow:0 0 25px rgba(84,244,255,.08)!important}
.hero-content .hero-message{color:#9bb7d4!important;max-width:700px!important;font-size:clamp(15px,1.6vw,19px)!important;line-height:1.9!important}
.button,.hero .button,.hero a.button{border:1px solid rgba(124,248,255,.42)!important;border-radius:8px!important;background:linear-gradient(105deg,#137d97,#5c50d6 58%,#a43d9e)!important;color:white!important;box-shadow:0 12px 38px rgba(33,166,209,.16),inset 0 1px rgba(255,255,255,.25)!important;text-transform:uppercase!important;letter-spacing:.08em!important;font-size:12px!important;font-weight:900!important}
.button:hover,.hero .button:hover{box-shadow:0 0 32px rgba(84,244,255,.2),0 18px 45px rgba(0,0,0,.25)!important;transform:translateY(-3px)!important}
.section,.color-section{position:relative!important}
.section>.title{color:#eafaff!important;letter-spacing:-.055em!important;text-shadow:0 0 32px rgba(84,244,255,.07)}
.section>.title:after{content:"";display:block;width:76px;height:3px;margin:18px auto 0;background:linear-gradient(90deg,#54f4ff,#8b7cff,#ff52d9);box-shadow:0 0 18px rgba(84,244,255,.28);border-radius:0!important}
.subtitle,.section p{color:#9cb6d0!important}
.card:not(.mission-card),.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card,.contact,.gallery-upload,.gallery-input-section,.stat-card,.stats>*{background:linear-gradient(145deg,rgba(12,19,40,.94),rgba(7,12,28,.94))!important;border:1px solid rgba(84,244,255,.16)!important;border-radius:18px!important;color:#eafaff!important;box-shadow:0 18px 55px rgba(0,0,0,.2),inset 0 1px rgba(255,255,255,.025)!important;backdrop-filter:blur(18px)!important}
.card h1,.card h2,.card h3,.news-card h3,.project-mini-card h3,.service-card h3,.owner-card h3,.gallery-card h3{color:#effcff!important}
.card p,.news-card p,.project-mini-card p,.service-card p,.owner-card p,.gallery-card p,.gallery-upload p{color:#9db7d0!important}
.gallery-image-link{border:1px solid rgba(84,244,255,.14)!important}
.gallery-card:hover,.news-card:hover,.project-mini-card:hover,.service-card:hover,.owner-card:hover,.mission-card:hover{border-color:rgba(84,244,255,.42)!important;box-shadow:0 22px 65px rgba(0,0,0,.28),0 0 30px rgba(84,244,255,.055)!important;transform:translateY(-5px)!important}
input,textarea,select{background:rgba(4,10,24,.95)!important;color:#effcff!important;border:1px solid rgba(84,244,255,.2)!important;border-radius:10px!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:#54f4ff!important;box-shadow:0 0 0 3px rgba(84,244,255,.09),0 0 24px rgba(84,244,255,.08)!important}
footer{background:#040711!important;color:#d8eaff!important;border-top:1px solid rgba(84,244,255,.2)!important}
footer p{color:#8ea9c7!important}footer .footer-logo{color:#54f4ff!important}
#jhr-progress{height:3px!important;background:linear-gradient(90deg,#54f4ff,#8977ff,#ff52d9)!important;box-shadow:0 0 18px rgba(84,244,255,.5)!important}
::selection{background:#54f4ff!important;color:#030712!important}
@keyframes cyberBreath{0%,100%{box-shadow:0 0 16px rgba(84,244,255,.06)}50%{box-shadow:0 0 35px rgba(84,244,255,.14)}}
.hero{animation:cyberBreath 7s ease-in-out infinite}
@media(max-width:700px){.hero{min-height:620px!important;border-radius:18px!important}.hero:after{inset:10px!important;left:10px!important;right:10px!important;top:10px!important;bottom:10px!important}.hero h1{font-size:clamp(70px,19vw,112px)!important;letter-spacing:-.07em!important}.hero-content{padding:70px 14px!important}.hero-organization-title{white-space:normal!important}.section>.title{font-size:clamp(34px,9vw,48px)!important}}
@media(prefers-reduced-motion:reduce){.hero{animation:none!important}}


/* JHR PURPLE NEBULA REDESIGN — vivid, layered, unmistakably purple */
/* ACCESSIBILITY FIX: calmer purple palette, comfortable contrast */
body{background-image:radial-gradient(ellipse at 15% 8%,rgba(124,58,237,.13),transparent 36%),radial-gradient(ellipse at 85% 18%,rgba(168,85,247,.09),transparent 32%),linear-gradient(180deg,#10091b 0%,#0b0712 55%,#08050d 100%)!important;background-color:#0b0712!important;color:#f4edff!important}
body:before{opacity:.055!important;background-size:64px 64px!important}
.join{background:linear-gradient(145deg,rgba(35,18,56,.98),rgba(19,10,32,.98))!important;color:#f4edff!important;border:1px solid rgba(192,132,252,.25)!important;box-shadow:0 18px 55px rgba(0,0,0,.28),0 0 28px rgba(124,58,237,.08)!important}
.join h2{color:#fff!important;text-shadow:0 2px 18px rgba(168,85,247,.22)!important}
.join p{color:#d7c9e8!important}
.join .viewer-counter{background:linear-gradient(110deg,#6d28d9,#8b5cf6)!important;color:#fff!important;border:1px solid rgba(233,213,255,.28)!important;box-shadow:0 6px 18px rgba(109,40,217,.2)!important}
.join .viewer-counter strong,.join .viewer-counter span{color:#fff!important}
footer{background:#090610!important;color:#e7ddf4!important}
footer p{color:#c5b7d8!important}
footer .footer-logo,footer h2,footer h3{color:#c4a1ff!important;text-shadow:none!important}
button,.btn,.button{box-shadow:0 5px 14px rgba(124,58,237,.16)!important}
@media(prefers-reduced-motion:reduce){body:before{display:none!important}}

:root{--jhr-purple:#a855f7;--jhr-violet:#7c3aed;--jhr-lilac:#e9d5ff;--jhr-pink:#f0abfc;--jhr-night:#090511;--jhr-panel:rgba(25,12,43,.82);--jhr-edge:rgba(192,132,252,.28);--jhr-glow:rgba(168,85,247,.28)}
html{scroll-behavior:smooth;scroll-padding-top:90px}
body{background-color:#090511!important;background-image:radial-gradient(ellipse at 12% 4%,rgba(147,51,234,.26),transparent 34%),radial-gradient(ellipse at 88% 16%,rgba(192,38,211,.17),transparent 29%),radial-gradient(ellipse at 52% 100%,rgba(109,40,217,.17),transparent 42%),linear-gradient(180deg,#090511 0%,#10071d 48%,#08040f 100%)!important;color:#fbf7ff!important}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.20;background-image:linear-gradient(rgba(192,132,252,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(192,132,252,.08) 1px,transparent 1px);background-size:46px 46px;mask-image:linear-gradient(to bottom,black,transparent 88%)}
body>*{position:relative;z-index:1}
nav{background:rgba(12,5,22,.82)!important;border:1px solid rgba(192,132,252,.2)!important;box-shadow:0 12px 50px rgba(0,0,0,.28),0 0 30px rgba(147,51,234,.08)!important;backdrop-filter:blur(22px)!important}
.logo strong,.logo-name-wrap strong,.footer-logo{color:#e9d5ff!important;text-shadow:0 0 22px rgba(168,85,247,.38)}
.nav-links a{transition:color .2s,background .2s,transform .2s!important;border-radius:999px}
.nav-links a:hover,.nav-links a.active-nav{color:#fff!important;background:rgba(168,85,247,.15)!important;box-shadow:inset 0 0 0 1px rgba(192,132,252,.2),0 0 22px rgba(168,85,247,.09)}
.hero{isolation:isolate!important;overflow:hidden!important;background:radial-gradient(ellipse at 50% 42%,rgba(124,58,237,.35),transparent 42%),linear-gradient(135deg,rgba(29,10,51,.97),rgba(10,5,21,.98) 56%,rgba(45,8,53,.9))!important;border:1px solid rgba(192,132,252,.35)!important;box-shadow:0 35px 100px rgba(0,0,0,.48),inset 0 0 80px rgba(124,58,237,.12),0 0 55px rgba(147,51,234,.13)!important}
.hero:before{content:""!important;position:absolute!important;inset:-20%!important;width:auto!important;height:auto!important;opacity:.75!important;pointer-events:none!important;background:radial-gradient(circle at 50% 45%,rgba(168,85,247,.22),transparent 28%),radial-gradient(circle at 18% 75%,rgba(236,72,153,.13),transparent 25%),radial-gradient(circle at 80% 22%,rgba(124,58,237,.22),transparent 28%)!important;filter:blur(18px)!important;animation:nebulaDrift 14s ease-in-out infinite alternate!important}
.hero:after{border-color:rgba(216,180,254,.48)!important;opacity:.72!important}
.hero h1{color:#fff!important;text-shadow:0 0 14px rgba(216,180,254,.4),0 0 55px rgba(168,85,247,.34)!important;letter-spacing:-.065em!important}
.hero p,.hero .subtitle,.hero-content p{color:#d8c7ed!important}
button,.btn,.button,.hero a[role=button],a.button{background:linear-gradient(115deg,#6d28d9,#a855f7 52%,#db2777)!important;border:1px solid rgba(233,213,255,.32)!important;color:white!important;box-shadow:0 10px 28px rgba(124,58,237,.25),inset 0 1px rgba(255,255,255,.18)!important;transition:transform .22s,filter .22s,box-shadow .22s!important}
button:hover,.btn:hover,.button:hover,.hero a[role=button]:hover,a.button:hover{transform:translateY(-2px)!important;filter:brightness(1.12)!important;box-shadow:0 15px 38px rgba(168,85,247,.34),0 0 24px rgba(217,70,239,.12)!important}
a{color:#d8b4fe}
.section>.title,.section h2,.section-title{color:#f5eaff!important;text-shadow:0 0 30px rgba(168,85,247,.16)}
.section>.title:after,.section-title:after{background:linear-gradient(90deg,#7c3aed,#d946ef,#f0abfc)!important;box-shadow:0 0 18px rgba(192,132,252,.32)!important}
.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card,.game,.contact,.mission-card{background:linear-gradient(145deg,rgba(34,17,54,.88),rgba(15,8,27,.91))!important;border:1px solid rgba(192,132,252,.19)!important;border-radius:22px!important;box-shadow:0 18px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)!important;backdrop-filter:blur(16px)!important;transition:transform .24s,border-color .24s,box-shadow .24s!important}
.news-card:hover,.project-mini-card:hover,.service-card:hover,.owner-card:hover,.gallery-card:hover,.game:hover,.contact:hover{border-color:rgba(216,180,254,.48)!important;box-shadow:0 24px 62px rgba(0,0,0,.32),0 0 32px rgba(147,51,234,.12)!important}
input,textarea,select{background:rgba(11,5,22,.9)!important;color:#fbf7ff!important;border:1px solid rgba(192,132,252,.28)!important;border-radius:13px!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 24px rgba(168,85,247,.12)!important}
footer{background:linear-gradient(180deg,#10071d,#07030d)!important;border-top:1px solid rgba(192,132,252,.22)!important;color:#e9d5ff!important}
footer p{color:#b8a4d2!important}
#jhr-progress{background:linear-gradient(90deg,#6d28d9,#a855f7,#e879f9,#f0abfc)!important;box-shadow:0 0 18px rgba(168,85,247,.6)!important}
::selection{background:#a855f7!important;color:#fff!important}
@keyframes nebulaDrift{from{transform:translate3d(-1.5%,1%,0) scale(1)}to{transform:translate3d(1.5%,-1%,0) scale(1.08)}}
/* Staff command center uses the same rich purple visual language */
.wrap{max-width:1360px!important}
.wrap>h1{color:#f5eaff!important;text-shadow:0 0 28px rgba(168,85,247,.2)!important}
.wrap>h1:before{color:#d8b4fe!important}
.staff-tab{color:#e9d5ff!important;border-color:rgba(192,132,252,.2)!important;background:rgba(38,18,61,.65)!important}
.staff-tab.active{background:linear-gradient(120deg,#6d28d9,#a855f7,#db2777)!important;box-shadow:0 10px 28px rgba(124,58,237,.3)!important}
.staff-tab:hover{background:rgba(168,85,247,.18)!important}
.viewer-table th{background:#241038!important;color:#e9d5ff!important}
.viewer-table td{background:rgba(18,8,32,.68)!important;color:#f5edff!important}
.viewer-table tbody tr:nth-child(even) td{background:rgba(38,17,60,.55)!important}
.viewer-table tbody tr:hover td{background:rgba(124,58,237,.22)!important}
input:focus,textarea:focus,select:focus{border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 22px rgba(168,85,247,.1)!important}
@media(max-width:700px){body{padding:16px!important}.hero{min-height:590px!important}.hero h1{font-size:clamp(62px,17vw,100px)!important}.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card{border-radius:17px!important}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;scroll-behavior:auto!important;transition:none!important}}

</style>

</head>


<body>

{% with messages = get_flashed_messages() %}
{% if messages %}
<div style="position:fixed;top:85px;right:20px;z-index:20000;max-width:360px;">
{% for message in messages %}<div class="auth-message">{{ message }}</div>{% endfor %}
</div>
{% endif %}
{% endwith %}


<!-- =====================================================
     NAVIGATION
===================================================== -->

<nav>


<a
    class="logo"
    href="#home"
>

    <img
        src="/media/OfficialLogo.png"
        alt="JHR Logo"
        width="48"
        height="48"
        fetchpriority="high"
        decoding="async"
    >

    <span class="logo-name-wrap">
        <strong>JHR</strong>
    </span>

</a>


<div class="nav-links">


<a
    href="#home"
    data-en="Home"
    data-fil="Home"
>
    Home
</a>


<a
    href="#about"
    data-en="About Us"
    data-fil="Tungkol sa Amin"
>
    About Us
</a>


<a
    href="#mission"
    data-en="Mission"
    data-fil="Misyon"
>
    Mission
</a>


<a
    href="#projects"
    data-en="Projects"
    data-fil="Mga Proyekto"
>
    Projects
</a>


<a
    href="#services"
    data-en="Services"
    data-fil="Serbisyo"
>
    Services
</a>


<a
    href="#gallery"
    data-en="Gallery"
    data-fil="Gallery"
>
    Gallery
</a>


<a
    href="#news"
    data-en="News"
    data-fil="Balita"
>
    News
</a>


<a
    href="#founders"
    data-en="Founders"
    data-fil="Mga Tagapagtatag"
>
    Founders
</a>


<a
    href="#games"
    data-en="Games"
    data-fil="Mga Laro"
>
    Games
</a>


<a
    href="#contact"
    data-en="Contact"
    data-fil="Kontak"
>
    Contact
</a>


</div>


<div class="nav-controls">


<button
    class="nav-btn"
    id="langBtn"
    onclick="toggleLanguage()"
>
    🇵🇭 FIL
</button>


<button
    class="nav-btn"
    id="themeBtn"
    onclick="toggleTheme()"
>
    🌙
</button>

{% if session.get("staff_id") %}
<a class="nav-btn" href="{{ url_for('staff_dashboard') }}" style="text-decoration:none;">👨‍💼 Staff</a>
<a class="nav-btn" href="{{ url_for('logout') }}" style="text-decoration:none;">🚪 Logout</a>
{% else %}
<a class="nav-btn" href="{{ url_for('login') }}" style="text-decoration:none;">🔐 Staff Login</a>
{% endif %}


</div>

</nav>



<!-- =====================================================
     HERO
===================================================== -->

<section
    class="hero"
    id="home"
>

<div class="hero-content">


<div
    class="badge"
    data-en="TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY"
    data-fil="TEKNOLOHIYA • EDUKASYON • INOBASYON • KOMUNIDAD"
>

    TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY

</div>


<h1>
    JHR
</h1>

<h2 class="hero-organization-title">
    Empowerment Through Technology
</h2>




<p class="hero-message" data-en="We are turning technology, creativity, and learning into opportunities
for people and communities." data-fil="Ginagawa naming mga oportunidad para sa mga tao at komunidad ang teknolohiya, pagkamalikhain, at pagkatuto.">
We are turning technology, creativity, and learning into opportunities
for people and communities.
</p>





</div>

</section>



<!-- =====================================================
     ABOUT
===================================================== -->

<section class="section" id="about">
<h2 class="title" data-en="Who Are We?" data-fil="Sino Kami?">Who Are We?</h2>
<div class="cards who-are-we-cards">
<div class="card who-we-are-box">
<p class="who-description" data-en="JHR: Empowerment Through Technology was founded and organized by Hugo and Julia, who are both passionate about robotics, artificial intelligence, coding, and community service. Having been exposed to the wonder of robotics at an early age and continuing their journey of creativity and innovation, they firmly believe that every child should have the opportunity to learn, explore, and experience the possibilities of robotics, coding, and technology." data-fil="Ang JHR: Empowerment Through Technology ay itinatag at inayos nina Hugo at Julia, na kapwa masigasig sa robotics, artificial intelligence, coding, at community service. Matapos maagang makilala ang kahanga-hangang mundo ng robotics at ipagpatuloy ang kanilang paglalakbay sa pagkamalikhain at inobasyon, naniniwala silang bawat bata ay dapat magkaroon ng pagkakataong matuto, magsaliksik, at maranasan ang mga posibilidad ng robotics, coding, at teknolohiya.">
JHR: Empowerment Through Technology was founded and organized by Hugo and Julia, who are both passionate about robotics, artificial intelligence, coding, and community service. Having been exposed to the wonder of robotics at an early age and continuing their journey of creativity and innovation, they firmly believe that every child should have the opportunity to learn, explore, and experience the possibilities of robotics, coding, and technology.
</p>
<p class="who-description" data-en="Through JHR, they hope to inspire children to harness their creativity and imagination and transform their ideas into meaningful innovations that address real-life problems. By empowering children with knowledge and technology, JHR envisions a generation of young innovators who can turn imagination into reality, use their skills to make a positive difference in the lives of others, and contribute to the well-being of their communities." data-fil="Sa pamamagitan ng JHR, nais nilang hikayatin ang mga bata na gamitin ang kanilang pagkamalikhain at imahinasyon at gawing makabuluhang inobasyon ang kanilang mga ideya upang matugunan ang mga tunay na problema sa buhay. Sa pagbibigay sa mga bata ng kaalaman at teknolohiya, hinahangad ng JHR ang isang henerasyon ng mga batang innovator na kayang gawing realidad ang imahinasyon, gamitin ang kanilang mga kasanayan upang magkaroon ng positibong pagbabago sa buhay ng iba, at makatulong sa kapakanan ng kanilang mga komunidad.">
Through JHR, they hope to inspire children to harness their creativity and imagination and transform their ideas into meaningful innovations that address real-life problems. By empowering children with knowledge and technology, JHR envisions a generation of young innovators who can turn imagination into reality, use their skills to make a positive difference in the lives of others, and contribute to the well-being of their communities.
</p>
</div>
</div>
</section>

<!-- =====================================================
     MISSION
===================================================== -->

<section class="color-section" id="mission">
<h2 class="title" data-en="Our Mission" data-fil="Aming Misyon">Our Mission</h2>
<p class="subtitle mission-subtitle mission-white" data-en="We are empowering through technology, creativity, and innovation." data-fil="Pinapalakas namin ang mga tao sa pamamagitan ng teknolohiya, pagkamalikhain, at inobasyon.">
We are empowering through technology, creativity, and innovation.
</p>
<div class="mission">
<div class="mission-card"><div class="mission-icon">💻</div><h3 data-en="Technology" data-fil="Teknolohiya">Technology</h3><p data-en="Promote creative and responsible technology use." data-fil="Itaguyod ang malikhain at responsableng paggamit ng teknolohiya.">Promote creative and responsible technology use.</p></div>
<div class="mission-card"><div class="mission-icon">🎓</div><h3 data-en="Education" data-fil="Edukasyon">Education</h3><p data-en="Encourage people, particularly children, to learn digital and technology skills." data-fil="Hikayatin ang mga tao, lalo na ang mga bata, na matuto ng mga kasanayang digital at teknolohiya.">Encourage people, particularly children, to learn digital and technology skills.</p></div>
<div class="mission-card"><div class="mission-icon">🌍</div><h3 data-en="Community" data-fil="Komunidad">Community</h3><p data-en="Explore ways technology can create positive community impact." data-fil="Tuklasin kung paano makalilikha ang teknolohiya ng positibong epekto sa komunidad.">Explore ways technology can create positive community impact.</p></div>
<div class="mission-card"><div class="mission-icon">🚀</div><h3 data-en="Innovation" data-fil="Inobasyon">Innovation</h3><p data-en="Turn creative ideas into useful projects and experiences." data-fil="Gawing kapaki-pakinabang na proyekto at karanasan ang mga malikhaing ideya.">Turn creative ideas into useful projects and experiences.</p></div>
</div>
</section>

<!-- =====================================================
     NUMBERS
===================================================== -->

<section class="section">

<h2
    class="title"
    data-en="JHR in Numbers"
    data-fil="JHR sa Bilang"
>

    JHR in Numbers

</h2>


<div class="stats">


<div class="stat">

<div class="stat-number">
    100+
</div>

<p
    data-en="Ideas"
    data-fil="Mga Ideya"
>
    Ideas
</p>

</div>


<div class="stat">

<div class="stat-number">
    25+
</div>

<p
    data-en="Activities"
    data-fil="Mga Aktibidad"
>
    Activities
</p>

</div>


<div class="stat">

<div class="stat-number">
    10+
</div>

<p
    data-en="Projects"
    data-fil="Mga Proyekto"
>
    Projects
</p>

</div>


<div class="stat">

<div class="stat-number">
    1
</div>

<p
    data-en="Big Mission"
    data-fil="Malaking Misyon"
>
    Big Mission
</p>

</div>


</div>

</section>



<!-- =====================================================
     PROJECTS
===================================================== -->

<section class="section" id="projects">
<h2 class="title" data-en="JHR Projects 🚀" data-fil="Mga Proyekto ng JHR 🚀">JHR Projects 🚀</h2>
<p class="subtitle" data-en="We are designing projects around learning and positive impact." data-fil="Nagdidisenyo kami ng mga proyekto para sa pagkatuto at positibong epekto.">We are designing projects around learning and positive impact.</p>
<div class="cards project-mini-grid">
<div class="card project-mini-card"><h3 data-en="💻 Technology Projects" data-fil="💻 Mga Proyektong Teknolohiya">💻 Technology Projects</h3><p data-en="websites, digital tools, programming, creative technology and experiments" data-fil="mga website, digital tool, programming, malikhaing teknolohiya at mga eksperimento">websites, digital tools, programming, creative technology and experiments</p></div>
<div class="card project-mini-card"><h3 data-en="🏫 Education" data-fil="🏫 Edukasyon">🏫 Education</h3><p data-en="technology-related learning activities and educational experiences" data-fil="mga aktibidad sa pagkatuto tungkol sa teknolohiya at mga karanasang pang-edukasyon">technology-related learning activities and educational experiences</p></div>
<div class="card project-mini-card"><h3 data-en="🌱 Community" data-fil="🌱 Komunidad">🌱 Community</h3><p data-en="exploring how technology can support communities and agricultural areas" data-fil="pagtuklas kung paano makatutulong ang teknolohiya sa mga komunidad at lugar na pang-agrikultura">exploring how technology can support communities and agricultural areas</p></div>
<div class="card project-mini-card"><h3 data-en="🚀 Future Projects" data-fil="🚀 Mga Proyektong Hinaharap">🚀 Future Projects</h3><p data-en="more JHR projects will be added as new initiatives are completed" data-fil="mas marami pang proyekto ng JHR ang idaragdag habang natatapos ang mga bagong inisyatiba">more JHR projects will be added as new initiatives are completed</p></div>
</div>
</section>

<!-- =====================================================
     SERVICES
===================================================== -->

<section class="section" id="services">
<h2 class="title" data-en="JHR Services 💻🎓" data-fil="Mga Serbisyo ng JHR 💻🎓">JHR Services 💻🎓</h2>
<p class="subtitle" data-en="We provide learning opportunities that help people discover technology and build useful projects." data-fil="Nagbibigay kami ng mga oportunidad sa pagkatuto upang matuklasan ng mga tao ang teknolohiya at makabuo ng mga kapaki-pakinabang na proyekto.">We provide learning opportunities that help people discover technology and build useful projects.</p>
<div class="services service-center">
<div class="service-card"><div class="service-icon">💻</div><h3 data-en="Free Coding Classes" data-fil="Libreng Coding Classes">Free Coding Classes</h3><p data-en="We provide free coding classes for beginners and learners who want to start programming." data-fil="Nagbibigay kami ng libreng coding classes para sa mga baguhan at mga nais magsimulang mag-program.">We provide free coding classes for beginners and learners who want to start programming.</p><span class="free" data-en="FREE" data-fil="LIBRE">FREE</span></div>
<div class="service-card"><div class="service-icon">🌐</div><h3 data-en="Web Development" data-fil="Web Development">Web Development</h3><p data-en="We build and develop websites using HTML, CSS, and JavaScript." data-fil="Gumagawa at nagde-develop kami ng mga website gamit ang HTML, CSS, at JavaScript">We build and develop websites using HTML, CSS, and JavaScript.</p></div>
<div class="service-card"><div class="service-icon">🚀</div><h3 data-en="Learn by Building" data-fil="Matuto sa Pamamagitan ng Pagbuo">Learn by Building</h3><p data-en="We organize and conduct community outreach for children to learn\nrobotics and coding." data-fil="Nag-oorganisa at nagsasagawa kami ng community outreach para sa mga batang matuto ng robotics at coding.">We organize and conduct community outreach for children to learn<br>robotics and coding.</p></div>
</div>
<div class="auth-box" id="coding-classes">
<h3>📨 Message Staff About Free Coding Classes</h3>
<p style="color:var(--muted); margin:8px 0 15px;">Send your question or request directly to the JHR staff. You do not need a staff account to send a message.</p>
<form method="POST" action="{{ url_for('coding_class_message') }}">
<label for="class-name">Name</label><input id="class-name" type="text" name="name" maxlength="120" placeholder="Your name" required>
<label for="class-email">Email</label><input id="class-email" type="email" name="email" maxlength="200" placeholder="you@example.com" required>
<label for="class-message">Message</label><textarea id="class-message" name="message" maxlength="5000" placeholder="Write your message about the free coding classes..." required style="width:100%;min-height:140px;padding:13px;margin:8px 0 14px;border:1px solid var(--border);border-radius:12px;background:var(--background);color:var(--text);font:inherit;resize:vertical;"></textarea>
<button class="upload-submit" type="submit">📨 Send Message to Staff</button>
</form>
</div>
</section>

<!-- =====================================================
GALLERY
     
     EXACT GALLERY FILES:
     
     IMG_0884
     IMG_5798
     IMG_12345
===================================================== -->

<section
    class="section"
    id="gallery"
>

<h2
    class="title"
    data-en="JHR Gallery 📸"
    data-fil="JHR Gallery 📸"
>

    JHR Gallery 📸

</h2>


<p
    class="subtitle"
    data-en="We empower ourselves; we empower others."
    data-fil="Pinalalakas natin ang ating sarili; pinalalakas natin ang iba."
>
    We empower ourselves; we empower others.
</p>


{% if session.get("staff_id") %}
<div class="auth-box gallery-upload">
    <div class="gallery-upload-header">
        <div class="gallery-upload-icon">📸</div>
        <div>
            <h3>Add Photos</h3>
            <p>Same event = same title + description.</p>
        </div>
    </div>

    <form method="POST" action="{{ url_for('upload_gallery') }}" enctype="multipart/form-data" id="galleryUploadForm">
        <div class="gallery-input-section">
            <div class="gallery-input-heading">
                <span class="gallery-input-number">1</span>
                <div><strong>Photos</strong><small>Choose event photos.</small></div>
            </div>
            <label for="galleryFiles" class="gallery-dropzone" id="galleryDropzone">
                <span class="gallery-drop-icon">☁️</span>
                <strong>Choose photos</strong>
                <span>or drag & drop</span>
                <small>JPG, PNG, WEBP, GIF • Multiple allowed</small>
                <input type="file" name="images" id="galleryFiles" accept="image/jpeg,image/png,image/webp,image/gif" multiple required>
            </label>
            <div id="gallerySelection" class="gallery-selection" aria-live="polite"></div>
        </div>

        <div class="gallery-input-section">
            <div class="gallery-input-heading">
                <span class="gallery-input-number">2</span>
                <div><strong>Title</strong><small>Used for every photo.</small></div>
            </div>
            <label class="sr-only" for="galleryTitle">Event / Gallery Title</label>
            <input type="text" name="gallery_title" id="galleryTitle" maxlength="160" placeholder="Example: Outreach Day" required>
        </div>

        <div class="gallery-input-section">
            <div class="gallery-input-heading">
                <span class="gallery-input-number">3</span>
                <div><strong>Description</strong><small>Used for every photo.</small></div>
            </div>
            <label class="sr-only" for="galleryDescription">Event / Gallery Description</label>
            <textarea name="gallery_description" id="galleryDescription" maxlength="2000" rows="5" placeholder="Example: Our team helped the community." required></textarea>
        </div>

        <div class="gallery-upload-summary" id="galleryUploadSummary">
            <span>📋</span>
            <div><strong>Ready?</strong><small>Check photos, title, and description.</small></div>
        </div>

        <button class="upload-submit gallery-main-submit" type="submit">⬆️ Upload Photos</button>
    </form>
</div>
{% endif %}

<div class="gallery-grid">

{% for image in uploaded_images %}
<div class="gallery-card uploaded-gallery-card">
    <a href="{{ url_for('uploaded_gallery_image', filename=image['filename']) }}" target="_blank" rel="noopener" class="gallery-image-link">
        <img src="{{ url_for('uploaded_gallery_image', filename=image['filename']) }}" alt="{{ image['title']|e }}" loading="lazy" decoding="async" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
        <span class="gallery-image-error">Photo could not be loaded.</span>
    </a>
    <div class="gallery-caption">
        <h3>📷 {{ image["title"] }}</h3>
        <p>{{ image["description"] }}</p>
        {% if session.get("staff_id") %}
        <form method="POST" action="{{ url_for('delete_gallery_image', image_id=image['id']) }}" class="gallery-delete-form" onsubmit="return confirm('Delete this gallery photo? This cannot be undone.');">
            <button type="submit" class="gallery-delete-button">🗑️ Delete Photo</button>
        </form>
        {% endif %}
    </div>
</div>
{% endfor %}


</div>

</section>



<!-- =====================================================
     NEWS & ANNOUNCEMENTS
===================================================== -->

<section class="section" id="news">
<h2 class="title" data-en="News & Announcements 📰" data-fil="Balita at Mga Anunsyo 📰">News & Announcements 📰</h2>
<p class="subtitle" data-en="Stay updated with JHR news, activities, and announcements." data-fil="Manatiling updated sa mga balita, gawain, at anunsyo ng JHR.">Stay updated with JHR news, activities, and announcements.</p>
<div class="news-grid">
{% if news_items %}
    {% for item in news_items %}
    <article class="news-card">
        <div class="news-kind">{{ item["kind"] }}</div>
        <h3>{{ item["title"] }}</h3>
        <div class="news-meta">{{ item["created_at"] }}{% if item["author"] %} · Posted by {{ item["author"] }}{% endif %}</div>
        {% if item["images"] %}
        <div class="news-images">
            {% for image in item["images"] %}
            <img src="{{ url_for('news_image', filename=image) }}" alt="{{ item['title'] }}" loading="lazy" decoding="async">
            {% endfor %}
        </div>
        {% endif %}
        <p>{{ item["content"] }}</p>
    </article>
    {% endfor %}
{% else %}
    <article class="news-card">
        <div class="news-kind">JHR</div>
        <h3>News & Announcements</h3>
        <p>New JHR news and announcements will appear here.</p>
    </article>
{% endif %}
</div>
</section>


<!-- =====================================================
     FOUNDERS
===================================================== -->

<section
    class="section"
    id="founders"
>

<h2
    class="title"
    data-en="JHR Team 👥"
    data-fil="JHR Team 👥"
>

    JHR Team 👥

</h2>


<p
    class="subtitle"
    data-en="Meet the hearts and minds behind the vision."
    data-fil="Kilalanin ang puso at isip sa likod ng pananaw."
>

    Meet the hearts and minds behind the vision.

</p>


<div class="owners">


<!-- =====================================================
     JOSE
===================================================== -->

<div class="owner-card">


<img
    class="owner-photo"
    src="/media/Owner1.jpg"
    alt="Jose Hugo Rafael T. Tan"
    loading="lazy"
    decoding="async"
>


<div class="owner-info">

<h3>
    Jose Hugo Rafael T. Tan
</h3>


<div
    class="owner-role"
    data-en="Founder"
    data-fil="Tagapagtatag"
>

    Founder

</div>


<p
    data-en="Hugo helps guide JHR's vision, projects, and technology-focused activities."
    data-fil="Tumutulong sa paggabay sa pananaw, mga proyekto at mga aktibidad ng JHR na nakatuon sa teknolohiya."
>

    Hugo helps guide JHR's vision, projects,
    and technology-focused activities.

</p>

</div>

</div>


<!-- =====================================================
     JULIA
===================================================== -->

<div class="owner-card">


<img
    class="owner-photo"
    src="/media/Owner2.png"
    alt="Julia Helga Raquel T. Tan"
    loading="lazy"
    decoding="async"
>


<div class="owner-info">

<h3>
    Julia Helga Raquel T. Tan
</h3>


<div
    class="owner-role"
    data-en="Founder"
    data-fil="Tagapagtatag"
>

    Founder

</div>


<p
    data-en="Julia supports JHR's creativity, projects, and community-focused activities."
    data-fil="Sinusuportahan ang pagkamalikhain, mga proyekto at mga aktibidad ng JHR para sa komunidad."
>

    Julia supports JHR's creativity, projects,
    and community-focused activities.

</p>

</div>

</div>


</div>



<div class="coordinator-section">

<h3
    class="coordinator-section-title"
    data-en="Coordinators"
    data-fil="Mga Coordinator"
>
    Coordinators
</h3>

<p
    class="subtitle"
    data-en="Meet the local and national coordinators supporting JHR's work."
    data-fil="Kilalanin ang mga lokal at pambansang coordinator na sumusuporta sa gawain ng JHR."
>
    Meet the local and national coordinators supporting JHR's work.
</p>

<div class="coordinator-grid">

<div class="coordinator-card">

<img
    class="coordinator-photo"
    src="/media/Loveth"
    alt="Loveth D. Cagud"
    loading="lazy"
    decoding="async"
    onerror="imageError(this)"
>

<div class="coordinator-info">

<h3>
    Loveth D. Cagud
</h3>

<div
    class="coordinator-role"
    data-en="Local Coordinator"
    data-fil="Lokal na Coordinator"
>
    Local Coordinator
</div>

<p
    class="coordinator-location"
    data-en="Misamis Occidental"
    data-fil="Misamis Occidental"
>
    Misamis Occidental
</p>

</div>

</div>


<div class="coordinator-card">

<img
    class="coordinator-photo"
    src="/media/Tagupa"
    alt="May Hazel M. Tagupa"
    loading="lazy"
    decoding="async"
    onerror="imageError(this)"
>

<div class="coordinator-info">

<h3>
    May Hazel M. Tagupa
</h3>

<div
    class="coordinator-role"
    data-en="National Coordinator"
    data-fil="Pambansang Coordinator"
>
    National Coordinator
</div>

<p
    class="coordinator-location"
    data-en="Philippines"
    data-fil="Pilipinas"
>
    Philippines
</p>

</div>

</div>

</div>

</div>
</section>



<!-- =====================================================
     GAME ZONE
===================================================== -->

<section
    class="games"
    id="games"
>

<h2
    class="title"
    data-en="JHR GAME ZONE 🎮"
    data-fil="JHR GAME ZONE 🎮"
>

    JHR GAME ZONE 🎮

</h2>


<p
    class="subtitle"
    data-en="12 games to learn, think and have fun!"
    data-fil="12 laro para matuto, mag-isip at magsaya!"
>

    12 games to learn,
    think and have fun!

</p>


<div class="game-grid">


<!-- =====================================================
     GAME 1
===================================================== -->

<div class="game">

<h3
    data-en="⚡ Speed Math"
    data-fil="⚡ Mabilis na Math"
>
    ⚡ Speed Math
</h3>

<p
    data-en="What is 12 × 8?"
    data-fil="Magkano ang 12 × 8?"
>
    What is 12 × 8?
</p>

<button onclick="answer('g1',true)">
96
</button>

<button onclick="answer('g1',false)">
88
</button>

<button onclick="answer('g1',false)">
108
</button>

<div id="g1" class="result"></div>

</div>


<!-- GAME 2 -->

<div class="game">

<h3
    data-en="🧠 Tech Quiz"
    data-fil="🧠 Tech Quiz"
>
    🧠 Tech Quiz
</h3>

<p
    data-en="What does CPU mean?"
    data-fil="Ano ang ibig sabihin ng CPU?"
>

    What does CPU mean?

</p>

<button
    data-en="Central Processing Unit"
    data-fil="Central Processing Unit"
    onclick="answer('g2',true)"
>
    Central Processing Unit
</button>

<button
    data-en="Computer Power Unit"
    data-fil="Computer Power Unit"
    onclick="answer('g2',false)"
>
    Computer Power Unit
</button>

<div id="g2" class="result"></div>

</div>


<!-- GAME 3 -->

<div class="game">

<h3
    data-en="🔐 Online Safety"
    data-fil="🔐 Kaligtasan Online"
>
    🔐 Online Safety
</h3>

<p
    data-en="Should you share your password?"
    data-fil="Dapat mo bang ibahagi ang iyong password?"
>

    Should you share your password?

</p>

<button
    data-en="Yes"
    data-fil="Oo"
    onclick="answer('g3',false)"
>
    Yes
</button>

<button
    data-en="No"
    data-fil="Hindi"
    onclick="answer('g3',true)"
>
    No
</button>

<div id="g3" class="result"></div>

</div>


<!-- GAME 4 -->

<div class="game">

<h3
    data-en="🤝 JHR Values"
    data-fil="🤝 Mga Halaga ng JHR"
>

    🤝 JHR Values

</h3>

<p
    data-en="What helps a team succeed?"
    data-fil="Ano ang tumutulong sa isang koponan upang magtagumpay?"
>

    What helps a team succeed?

</p>

<button
    data-en="Cooperation"
    data-fil="Pagtutulungan"
    onclick="answer('g4',true)"
>
    Cooperation
</button>

<button
    data-en="Giving up"
    data-fil="Pagsuko"
    onclick="answer('g4',false)"
>
    Giving up
</button>

<div id="g4" class="result"></div>

</div>


<!-- GAME 5 -->

<div class="game">

<h3
    data-en="🌐 HTML Quiz"
    data-fil="🌐 HTML Quiz"
>

    🌐 HTML Quiz

</h3>

<p
    data-en="What does HTML help create?"
    data-fil="Ano ang tinutulungan ng HTML na gawin?"
>

    What does HTML help create?

</p>

<button
    data-en="Web pages"
    data-fil="Web pages"
    onclick="answer('g5',true)"
>
    Web pages
</button>

<button
    data-en="Batteries"
    data-fil="Baterya"
    onclick="answer('g5',false)"
>
    Batteries
</button>

<div id="g5" class="result"></div>

</div>


<!-- GAME 6 -->

<div class="game">

<h3
    data-en="🔢 Binary"
    data-fil="🔢 Binary"
>

    🔢 Binary

</h3>

<p
    data-en="What numbers are used in binary?"
    data-fil="Anong mga numero ang ginagamit sa binary?"
>

    What numbers are used in binary?

</p>

<button
    data-en="0 and 1"
    data-fil="0 at 1"
    onclick="answer('g6',true)"
>
    0 and 1
</button>

<button
    data-en="1 and 9"
    data-fil="1 at 9"
    onclick="answer('g6',false)"
>
    1 and 9
</button>

<div id="g6" class="result"></div>

</div>


<!-- GAME 7 -->

<div class="game">

<h3
    data-en="➕ Quick Addition"
    data-fil="➕ Mabilis na Addition"
>

    ➕ Quick Addition

</h3>

<p>
    27 + 15 = ?
</p>

<button onclick="answer('g7',true)">
42
</button>

<button onclick="answer('g7',false)">
41
</button>

<button onclick="answer('g7',false)">
52
</button>

<div id="g7" class="result"></div>

</div>


<!-- GAME 8 -->

<div class="game">

<h3
    data-en="✖️ Multiplication"
    data-fil="✖️ Multiplication"
>

    ✖️ Multiplication

</h3>

<p>
    7 × 6 = ?
</p>

<button onclick="answer('g8',true)">
42
</button>

<button onclick="answer('g8',false)">
48
</button>

<button onclick="answer('g8',false)">
36
</button>

<div id="g8" class="result"></div>

</div>


<!-- GAME 9 -->

<div class="game">

<h3
    data-en="🧩 Logic Puzzle"
    data-fil="🧩 Logic Puzzle"
>

    🧩 Logic Puzzle

</h3>

<p
    data-en="What comes next? 2, 4, 6, 8, ?"
    data-fil="Ano ang kasunod? 2, 4, 6, 8, ?"
>

    What comes next?
    2, 4, 6, 8, ?

</p>

<button onclick="answer('g9',true)">
10
</button>

<button onclick="answer('g9',false)">
12
</button>

<button onclick="answer('g9',false)">
9
</button>

<div id="g9" class="result"></div>

</div>


<!-- GAME 10 -->

<div class="game">

<h3
    data-en="🔤 Word Scramble"
    data-fil="🔤 Ayusin ang Salita"
>

    🔤 Word Scramble

</h3>

<p
    data-en="Unscramble: GOCIDN"
    data-fil="Ayusin: GOCIDN"
>

    Unscramble:
    GOCIDN

</p>

<button
    data-en="CODING"
    data-fil="CODING"
    onclick="answer('g10',true)"
>
    CODING
</button>

<button
    data-en="CLOUD"
    data-fil="CLOUD"
    onclick="answer('g10',false)"
>
    CLOUD
</button>

<button
    data-en="GARDEN"
    data-fil="GARDEN"
    onclick="answer('g10',false)"
>
    GARDEN
</button>

<div id="g10" class="result"></div>

</div>


<!-- GAME 11 -->

<div class="game">

<h3
    data-en="🌟 Innovation Quiz"
    data-fil="🌟 Innovation Quiz"
>

    🌟 Innovation Quiz

</h3>

<p
    data-en="What is a good first step for a new idea?"
    data-fil="Ano ang magandang unang hakbang para sa bagong ideya?"
>

    What is a good first step for a new idea?

</p>

<button
    data-en="Plan and test it"
    data-fil="Planuhin at subukan ito"
    onclick="answer('g11',true)"
>
    Plan and test it
</button>

<button
    data-en="Ignore it"
    data-fil="Huwag pansinin"
    onclick="answer('g11',false)"
>
    Ignore it
</button>

<button
    data-en="Give up"
    data-fil="Sumuko"
    onclick="answer('g11',false)"
>
    Give up
</button>

<div id="g11" class="result"></div>

</div>


<!-- GAME 12 -->

<div class="game">

<h3
    data-en="🌍 Digital Citizenship"
    data-fil="🌍 Digital Citizenship"
>

    🌍 Digital Citizenship

</h3>

<p
    data-en="Which is responsible technology use?"
    data-fil="Alin ang responsableng paggamit ng teknolohiya?"
>

    Which is responsible technology use?

</p>

<button
    data-en="Learning"
    data-fil="Pag-aaral"
    onclick="answer('g12',true)"
>
    Learning
</button>

<button
    data-en="Cyberbullying"
    data-fil="Cyberbullying"
    onclick="answer('g12',false)"
>
    Cyberbullying
</button>

<button
    data-en="Sharing passwords"
    data-fil="Pagbabahagi ng password"
    onclick="answer('g12',false)"
>
    Sharing passwords
</button>

<div id="g12" class="result"></div>

</div>


</div>

</section>



<!-- =====================================================
     CONTACT
===================================================== -->

<section
    class="section"
    id="contact"
>

<div class="contact">


<h2
    data-en="Contact JHR"
    data-fil="Kontakin ang JHR"
>

    Contact JHR

</h2>


<p
    data-en="Join us in this journey of technology, education, innovation and community."
    data-fil="Sumama sa aming paglalakbay sa teknolohiya, edukasyon, inobasyon at komunidad."
>

    Join us in this journey of technology,
    education, innovation and community.

</p>


<p>
    📧
    <a
        href="mailto:josehr.tan@gmail.com"
    >
        josehr.tan@gmail.com
    </a>
</p>


<p>
    📱
    <a
        href="tel:09096585708"
    >
        0909 658 5708
    </a>
</p>


</div>


<!-- =====================================================
     JHR JOURNEY
===================================================== -->

<div class="join">


<h2
    data-en="Join the JHR Journey 🚀"
    data-fil="Sumama sa JHR Journey 🚀"
>

    Join the JHR Journey 🚀

</h2>


<p
    data-en="Technology • Education • Innovation • Community"
    data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad"
>

    Technology • Education • Innovation • Community

</p>


<p
    data-en="Learn. Create. Share. Empower."
    data-fil="Matuto. Lumikha. Magbahagi. Magbigay-lakas."
>

    Learn. Create. Share. Empower.

</p>


<!-- =====================================================
     VIEWER COUNTER
===================================================== -->

<div class="viewer-counter">

    👀

    <strong>
        {{ viewer_count }}
    </strong>

    <span
        id="visitorWord"
    >
        Visitors
    </span>

</div>


</div>

</section>



<!-- =====================================================
     FOOTER
===================================================== -->

<footer>

<div class="footer-logo">
    JHR
</div>


<p
    data-en="Empowerment Through Technology"
    data-fil="Pagpapalakas sa Pamamagitan ng Teknolohiya"
>

    Empowerment Through Technology

</p>


<p
    data-en="Technology • Education • Innovation • Community"
    data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad"
>

    Technology • Education • Innovation • Community

</p>


<p
    data-en="© 2026 JHR Team"
    data-fil="© 2026 JHR Team"
>

    © 2026 JHR Team

</p>

</footer>



<!-- =====================================================
     TOP BUTTON
===================================================== -->

<button
    class="top"
    id="topButton"
    onclick="window.scrollTo({
        top:0,
        behavior:'smooth'
    })"
>

    ↑

</button>



<script>

/* =====================================================
   LANGUAGE
===================================================== */

let currentLanguage =
    localStorage.getItem(
        "jhrLanguage"
    ) || "en";


function applyLanguage() {

    document
        .querySelectorAll(
            "[data-en]"
        )
        .forEach(function(element) {

            const english =
                element.getAttribute(
                    "data-en"
                );

            const filipino =
                element.getAttribute(
                    "data-fil"
                );

            const translated =
                currentLanguage === "en"
                    ? english
                    : (filipino || english);

            if (translated !== null && translated !== undefined) {
                element.textContent = translated;
            }

        });


    document.getElementById(
        "langBtn"
    ).textContent =
        currentLanguage === "en"
            ? "🇵🇭 FIL"
            : "🇬🇧 ENG";


    const visitor =
        document.getElementById(
            "visitorWord"
        );

    if (visitor) {

        visitor.textContent =
            currentLanguage === "en"
                ? "Visitors"
                : "Mga Bisita";

    }


    document.documentElement.lang =
        currentLanguage === "en"
            ? "en"
            : "fil";
}


function toggleLanguage() {

    currentLanguage =
        currentLanguage === "en"
            ? "fil"
            : "en";


    localStorage.setItem(
        "jhrLanguage",
        currentLanguage
    );


    applyLanguage();

}


/* =====================================================
   DARK / LIGHT MODE
===================================================== */

function applyTheme() {

    const saved =
        localStorage.getItem(
            "jhrTheme"
        );


    if (
        saved === "dark"
    ) {

        document.body.classList.add(
            "dark"
        );

        document.getElementById(
            "themeBtn"
        ).textContent = "☀️";

    } else {

        document.body.classList.remove(
            "dark"
        );

        document.getElementById(
            "themeBtn"
        ).textContent = "🌙";

    }

}


function toggleTheme() {

    const dark =
        document.body.classList.toggle(
            "dark"
        );


    localStorage.setItem(
        "jhrTheme",
        dark
            ? "dark"
            : "light"
    );


    document.getElementById(
        "themeBtn"
    ).textContent =
        dark
            ? "☀️"
            : "🌙";

}


/* =====================================================
   GAME ANSWERS
===================================================== */

function answer(
    id,
    correct
) {

    const result =
        document.getElementById(id);


    if (correct) {

        result.textContent =
            currentLanguage === "en"
                ? "🎉 Correct! Great job!"
                : "🎉 Tama! Mahusay!";

    } else {

        result.textContent =
            currentLanguage === "en"
                ? "❌ Try again!"
                : "❌ Subukan muli!";

    }

}


/* =====================================================
   VIEWER COUNTER
===================================================== */

const viewerKey =
    "jhr_local_viewers";


let visitors =
    Number(
        localStorage.getItem(
            viewerKey
        )
    ) || 0;


if (
    !sessionStorage.getItem(
        "jhr_counted"
    )
) {

    visitors++;

    localStorage.setItem(
        viewerKey,
        visitors
    );

    sessionStorage.setItem(
        "jhr_counted",
        "1"
    );

}


/* =====================================================
   STAFF SESSION AUTO-LOGOUT
===================================================== */

{% if session.get("staff_id") %}
(function () {
    const timeoutMs = 5 * 60 * 1000;
    let lastActivity = Date.now();
    let heartbeatTimer = null;

    function markActivity() {
        lastActivity = Date.now();
    }

    ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach(function (eventName) {
        window.addEventListener(eventName, markActivity, { passive: true });
    });

    function heartbeat() {
        fetch("{{ url_for('staff_heartbeat') }}", {
            method: "POST",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            credentials: "same-origin"
        }).then(function (response) {
            if (response.status === 401 || response.redirected) {
                window.location.href = "{{ url_for('login') }}";
            }
        }).catch(function () {});
    }

    heartbeatTimer = setInterval(function () {
        if (Date.now() - lastActivity >= timeoutMs) {
            clearInterval(heartbeatTimer);
            window.location.href = "{{ url_for('logout') }}";
            return;
        }
        heartbeat();
    }, 60 * 1000);

    window.addEventListener("beforeunload", function () {
        clearInterval(heartbeatTimer);
    });
})();
{% endif %}


/* =====================================================
   GALLERY SHARED EVENT FIELDS
===================================================== */

(function () {
    const fileInput = document.getElementById("galleryFiles");
    const selection = document.getElementById("gallerySelection");
    const dropzone = document.getElementById("galleryDropzone");
    const summary = document.getElementById("galleryUploadSummary");
    const form = document.getElementById("galleryUploadForm");
    if (!fileInput || !selection) return;

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (character) {
            return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[character];
        });
    }

    function formatSize(bytes) {
        if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
        return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    }

    function renderSelection() {
        const files = Array.from(fileInput.files || []);
        if (!files.length) {
            selection.innerHTML = '';
            if (summary) summary.innerHTML = '<span>📋</span><div><strong>Ready?</strong><small>Check photos, title, and description.</small></div>';
            return;
        }
        selection.innerHTML = '<div class="gallery-selection-top"><strong>📸 ' + files.length + ' photo' + (files.length === 1 ? '' : 's') + ' selected</strong><span>All will use the same event title and description.</span></div>' +
            '<div class="gallery-selection-list">' + files.map(function (file) {
                return '<div class="gallery-selection-item"><span>🖼️</span><div><strong>' + escapeHtml(file.name) + '</strong><small>' + formatSize(file.size) + '</small></div></div>';
            }).join('') + '</div>';
        if (summary) summary.innerHTML = '<span>✅</span><div><strong>' + files.length + ' photo' + (files.length === 1 ? '' : 's') + ' ready</strong><small>Finish the title and description below, then upload the event.</small></div>';
    }

    fileInput.addEventListener("change", renderSelection);

    if (dropzone) {
        ["dragenter", "dragover"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                dropzone.classList.add("is-dragging");
            });
        });
        ["dragleave", "drop"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                dropzone.classList.remove("is-dragging");
            });
        });
        dropzone.addEventListener("drop", function (event) {
            const dropped = event.dataTransfer && event.dataTransfer.files;
            if (!dropped || !dropped.length) return;
            try { fileInput.files = dropped; } catch (error) {}
            renderSelection();
        });
    }

    if (form) {
        form.addEventListener("submit", function (event) {
            if (!fileInput.files.length) {
                event.preventDefault();
                alert("Please choose at least one photo first.");
                return;
            }
            const title = document.getElementById("galleryTitle");
            const description = document.getElementById("galleryDescription");
            if (!title.value.trim() || !description.value.trim()) {
                event.preventDefault();
                alert("Please add the event title and description before uploading.");
            }
        });
    }

    renderSelection();
})();

/* =====================================================
   IMAGE ERROR HANDLER
===================================================== */

function imageError(image) {

    image.style.background =
        "linear-gradient(135deg,#4c1d95,#7c3aed)";

    image.alt =
        "JHR image";

}


/* =====================================================
   BACK TO TOP
===================================================== */

window.addEventListener(
    "scroll",
    function() {

        const button =
            document.getElementById(
                "topButton"
            );


        if (
            window.scrollY > 500
        ) {

            button.style.display =
                "block";

        } else {

            button.style.display =
                "none";

        }

    }
);


/* =====================================================
   START
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        applyTheme();

        applyLanguage();

    }
);



/* =====================================================
   JHR INTERACTION ENGINE
===================================================== */
(function(){
    function initJHRInteractions(){
        if(window.__jhrUltraReady)return;
        window.__jhrUltraReady=true;
        const root=document.body;
        if(!root)return;

        const progress=document.createElement('div');
        progress.id='jhr-progress';
        root.appendChild(progress);
        const updateProgress=()=>{
            const max=document.documentElement.scrollHeight-window.innerHeight;
            progress.style.width=(max>0?Math.min(100,Math.max(0,window.scrollY/max*100)):0)+'%';
        };
        window.addEventListener('scroll',updateProgress,{passive:true}); updateProgress();

        let raf=0;
        window.addEventListener('pointermove',e=>{
            if(raf)return;
            raf=requestAnimationFrame(()=>{root.style.setProperty('--mx',e.clientX+'px');root.style.setProperty('--my',e.clientY+'px');raf=0;});
        },{passive:true});

        const revealables=root.querySelectorAll('section,.card,.gallery-card,.owner-card,.project-mini-card,.service-card,.news-card,.mission-card');
        revealables.forEach((el,i)=>{el.classList.add('reveal');el.style.transitionDelay=Math.min(i%6,5)*45+'ms';});
        if('IntersectionObserver' in window){
            const io=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');io.unobserve(entry.target);}}),{threshold:.08});
            revealables.forEach(el=>io.observe(el));
        }else revealables.forEach(el=>el.classList.add('is-visible'));

        const lightbox=document.createElement('div');
        lightbox.id='jhr-lightbox';
        lightbox.innerHTML='<button id="jhr-lightbox-close" type="button" aria-label="Close image">×</button><img alt="Gallery preview">';
        root.appendChild(lightbox);
        const lightImg=lightbox.querySelector('img');
        const close=()=>lightbox.classList.remove('open');
        lightbox.addEventListener('click',e=>{if(e.target===lightbox)close();});
        lightbox.querySelector('#jhr-lightbox-close').addEventListener('click',close);
        document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
        root.querySelectorAll('.gallery-image-link').forEach(link=>{
            link.addEventListener('click',e=>{
                const img=link.querySelector('img'); if(!img)return;
                e.preventDefault(); lightImg.src=img.currentSrc||img.src; lightImg.alt=img.alt||'Gallery preview'; lightbox.classList.add('open');
            });
        });

        root.querySelectorAll('.button,.nav-btn,button').forEach(btn=>{
            btn.classList.add('jhr-ripple');
            btn.addEventListener('click',e=>{
                const rect=btn.getBoundingClientRect(), dot=document.createElement('span');
                const size=Math.max(rect.width,rect.height); dot.className='jhr-ripple-dot'; dot.style.width=dot.style.height=size+'px';
                dot.style.left=(e.clientX-rect.left-size/2)+'px'; dot.style.top=(e.clientY-rect.top-size/2)+'px'; btn.appendChild(dot);
                setTimeout(()=>dot.remove(),600);
            });
        });

        if(window.matchMedia('(hover:hover) and (pointer:fine)').matches){
            root.querySelectorAll('.gallery-card,.owner-card,.service-card,.project-mini-card,.news-card').forEach(card=>{
                card.addEventListener('pointermove',e=>{
                    const r=card.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
                    card.style.transform='perspective(900px) rotateX('+(-y*2.5)+'deg) rotateY('+(x*2.5)+'deg) translateY(-4px)';
                });
                card.addEventListener('pointerleave',()=>card.style.transform='');
            });
        }

        const links=[...root.querySelectorAll('.nav-links a[href^="#"]')];
        const sections=links.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
        if('IntersectionObserver' in window && sections.length){
            const navIO=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){links.forEach(a=>a.classList.toggle('active-nav',a.getAttribute('href')==='#'+entry.target.id));}}),{rootMargin:'-35% 0px -55% 0px',threshold:0});
            sections.forEach(s=>navIO.observe(s));
        }
    }
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initJHRInteractions,{once:true});else initJHRInteractions();
})();

</script>


</body>
</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    from flask import make_response

    viewer_id, _ = track_viewer("/")

    # Count only valid tracked browser IDs, not legacy/empty MongoDB records.
    viewer_count = viewers_collection.count_documents({
        "viewer_id": {"$type": "string", "$ne": ""}
    })

    response = make_response(render_template_string(
        HTML,
        viewer_count=viewer_count,
        uploaded_images=gallery_images(),
        news_items=news_items()
    ))
    response.set_cookie(
        "jhr_viewer_id",
        viewer_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=bool(request.is_secure),
        samesite="Lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


AUTH_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JHR | {{ title }}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#2e1065,#7c3aed,#c026d3);padding:20px}.box{width:min(440px,100%);background:white;border-radius:24px;padding:35px;box-shadow:0 20px 60px rgba(0,0,0,.25)}h1{color:#4c1d95;margin-top:0}p{color:#6b5b82}.box input{width:100%;padding:14px;margin:7px 0 15px;border:1px solid #ded0ff;border-radius:12px}.box button{width:100%;padding:14px;border:0;border-radius:12px;background:linear-gradient(135deg,#7c3aed,#c026d3);color:white;font-weight:800;cursor:pointer}.box a{display:block;text-align:center;margin-top:18px;color:#7c3aed;text-decoration:none;font-weight:700}.note{background:#ede9fe;padding:12px;border-radius:12px;margin-bottom:15px;color:#4c1d95;font-weight:700}


/* JHR CYBER AUTH */
body{background:radial-gradient(ellipse at 18% 10%,rgba(79,70,229,.28),transparent 35%),radial-gradient(ellipse at 88% 85%,rgba(34,211,238,.13),transparent 30%),linear-gradient(rgba(84,244,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(84,244,255,.035) 1px,transparent 1px),#050713!important;background-size:auto,auto,34px 34px,34px 34px,auto!important;color:#eefaff!important}
.box{background:linear-gradient(145deg,rgba(12,19,40,.96),rgba(7,12,28,.96))!important;border:1px solid rgba(84,244,255,.24)!important;border-radius:20px!important;box-shadow:0 30px 100px rgba(0,0,0,.45),0 0 50px rgba(84,244,255,.07)!important;backdrop-filter:blur(24px)!important}
.box h1{color:#eefaff!important;letter-spacing:-.045em}.box p{color:#9cb6d0!important}.box label{color:#bdebf2!important}.box input{background:#050b1b!important;color:#fff!important;border:1px solid rgba(84,244,255,.2)!important}.box input:focus{outline:none;border-color:#54f4ff;box-shadow:0 0 0 3px rgba(84,244,255,.1)}.box button{background:linear-gradient(105deg,#137d97,#5c50d6 58%,#a43d9e)!important;border:1px solid rgba(84,244,255,.3)!important;text-transform:uppercase;letter-spacing:.08em}.box a{color:#65efff!important}.note{background:rgba(84,244,255,.08)!important;border:1px solid rgba(84,244,255,.2)!important;color:#c8faff!important}


/* JHR PURPLE NEBULA REDESIGN — vivid, layered, unmistakably purple */
/* ACCESSIBILITY FIX: calmer purple palette, comfortable contrast */
body{background-image:radial-gradient(ellipse at 15% 8%,rgba(124,58,237,.13),transparent 36%),radial-gradient(ellipse at 85% 18%,rgba(168,85,247,.09),transparent 32%),linear-gradient(180deg,#10091b 0%,#0b0712 55%,#08050d 100%)!important;background-color:#0b0712!important;color:#f4edff!important}
body:before{opacity:.055!important;background-size:64px 64px!important}
.join{background:linear-gradient(145deg,rgba(35,18,56,.98),rgba(19,10,32,.98))!important;color:#f4edff!important;border:1px solid rgba(192,132,252,.25)!important;box-shadow:0 18px 55px rgba(0,0,0,.28),0 0 28px rgba(124,58,237,.08)!important}
.join h2{color:#fff!important;text-shadow:0 2px 18px rgba(168,85,247,.22)!important}
.join p{color:#d7c9e8!important}
.join .viewer-counter{background:linear-gradient(110deg,#6d28d9,#8b5cf6)!important;color:#fff!important;border:1px solid rgba(233,213,255,.28)!important;box-shadow:0 6px 18px rgba(109,40,217,.2)!important}
.join .viewer-counter strong,.join .viewer-counter span{color:#fff!important}
footer{background:#090610!important;color:#e7ddf4!important}
footer p{color:#c5b7d8!important}
footer .footer-logo,footer h2,footer h3{color:#c4a1ff!important;text-shadow:none!important}
button,.btn,.button{box-shadow:0 5px 14px rgba(124,58,237,.16)!important}
@media(prefers-reduced-motion:reduce){body:before{display:none!important}}

:root{--jhr-purple:#a855f7;--jhr-violet:#7c3aed;--jhr-lilac:#e9d5ff;--jhr-pink:#f0abfc;--jhr-night:#090511;--jhr-panel:rgba(25,12,43,.82);--jhr-edge:rgba(192,132,252,.28);--jhr-glow:rgba(168,85,247,.28)}
html{scroll-behavior:smooth;scroll-padding-top:90px}
body{background-color:#090511!important;background-image:radial-gradient(ellipse at 12% 4%,rgba(147,51,234,.26),transparent 34%),radial-gradient(ellipse at 88% 16%,rgba(192,38,211,.17),transparent 29%),radial-gradient(ellipse at 52% 100%,rgba(109,40,217,.17),transparent 42%),linear-gradient(180deg,#090511 0%,#10071d 48%,#08040f 100%)!important;color:#fbf7ff!important}
body:before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.20;background-image:linear-gradient(rgba(192,132,252,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(192,132,252,.08) 1px,transparent 1px);background-size:46px 46px;mask-image:linear-gradient(to bottom,black,transparent 88%)}
body>*{position:relative;z-index:1}
nav{background:rgba(12,5,22,.82)!important;border:1px solid rgba(192,132,252,.2)!important;box-shadow:0 12px 50px rgba(0,0,0,.28),0 0 30px rgba(147,51,234,.08)!important;backdrop-filter:blur(22px)!important}
.logo strong,.logo-name-wrap strong,.footer-logo{color:#e9d5ff!important;text-shadow:0 0 22px rgba(168,85,247,.38)}
.nav-links a{transition:color .2s,background .2s,transform .2s!important;border-radius:999px}
.nav-links a:hover,.nav-links a.active-nav{color:#fff!important;background:rgba(168,85,247,.15)!important;box-shadow:inset 0 0 0 1px rgba(192,132,252,.2),0 0 22px rgba(168,85,247,.09)}
.hero{isolation:isolate!important;overflow:hidden!important;background:radial-gradient(ellipse at 50% 42%,rgba(124,58,237,.35),transparent 42%),linear-gradient(135deg,rgba(29,10,51,.97),rgba(10,5,21,.98) 56%,rgba(45,8,53,.9))!important;border:1px solid rgba(192,132,252,.35)!important;box-shadow:0 35px 100px rgba(0,0,0,.48),inset 0 0 80px rgba(124,58,237,.12),0 0 55px rgba(147,51,234,.13)!important}
.hero:before{content:""!important;position:absolute!important;inset:-20%!important;width:auto!important;height:auto!important;opacity:.75!important;pointer-events:none!important;background:radial-gradient(circle at 50% 45%,rgba(168,85,247,.22),transparent 28%),radial-gradient(circle at 18% 75%,rgba(236,72,153,.13),transparent 25%),radial-gradient(circle at 80% 22%,rgba(124,58,237,.22),transparent 28%)!important;filter:blur(18px)!important;animation:nebulaDrift 14s ease-in-out infinite alternate!important}
.hero:after{border-color:rgba(216,180,254,.48)!important;opacity:.72!important}
.hero h1{color:#fff!important;text-shadow:0 0 14px rgba(216,180,254,.4),0 0 55px rgba(168,85,247,.34)!important;letter-spacing:-.065em!important}
.hero p,.hero .subtitle,.hero-content p{color:#d8c7ed!important}
button,.btn,.button,.hero a[role=button],a.button{background:linear-gradient(115deg,#6d28d9,#a855f7 52%,#db2777)!important;border:1px solid rgba(233,213,255,.32)!important;color:white!important;box-shadow:0 10px 28px rgba(124,58,237,.25),inset 0 1px rgba(255,255,255,.18)!important;transition:transform .22s,filter .22s,box-shadow .22s!important}
button:hover,.btn:hover,.button:hover,.hero a[role=button]:hover,a.button:hover{transform:translateY(-2px)!important;filter:brightness(1.12)!important;box-shadow:0 15px 38px rgba(168,85,247,.34),0 0 24px rgba(217,70,239,.12)!important}
a{color:#d8b4fe}
.section>.title,.section h2,.section-title{color:#f5eaff!important;text-shadow:0 0 30px rgba(168,85,247,.16)}
.section>.title:after,.section-title:after{background:linear-gradient(90deg,#7c3aed,#d946ef,#f0abfc)!important;box-shadow:0 0 18px rgba(192,132,252,.32)!important}
.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card,.game,.contact,.mission-card{background:linear-gradient(145deg,rgba(34,17,54,.88),rgba(15,8,27,.91))!important;border:1px solid rgba(192,132,252,.19)!important;border-radius:22px!important;box-shadow:0 18px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)!important;backdrop-filter:blur(16px)!important;transition:transform .24s,border-color .24s,box-shadow .24s!important}
.news-card:hover,.project-mini-card:hover,.service-card:hover,.owner-card:hover,.gallery-card:hover,.game:hover,.contact:hover{border-color:rgba(216,180,254,.48)!important;box-shadow:0 24px 62px rgba(0,0,0,.32),0 0 32px rgba(147,51,234,.12)!important}
input,textarea,select{background:rgba(11,5,22,.9)!important;color:#fbf7ff!important;border:1px solid rgba(192,132,252,.28)!important;border-radius:13px!important}
input:focus,textarea:focus,select:focus{outline:none!important;border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 24px rgba(168,85,247,.12)!important}
footer{background:linear-gradient(180deg,#10071d,#07030d)!important;border-top:1px solid rgba(192,132,252,.22)!important;color:#e9d5ff!important}
footer p{color:#b8a4d2!important}
#jhr-progress{background:linear-gradient(90deg,#6d28d9,#a855f7,#e879f9,#f0abfc)!important;box-shadow:0 0 18px rgba(168,85,247,.6)!important}
::selection{background:#a855f7!important;color:#fff!important}
@keyframes nebulaDrift{from{transform:translate3d(-1.5%,1%,0) scale(1)}to{transform:translate3d(1.5%,-1%,0) scale(1.08)}}
/* Staff command center uses the same rich purple visual language */
.wrap{max-width:1360px!important}
.wrap>h1{color:#f5eaff!important;text-shadow:0 0 28px rgba(168,85,247,.2)!important}
.wrap>h1:before{color:#d8b4fe!important}
.staff-tab{color:#e9d5ff!important;border-color:rgba(192,132,252,.2)!important;background:rgba(38,18,61,.65)!important}
.staff-tab.active{background:linear-gradient(120deg,#6d28d9,#a855f7,#db2777)!important;box-shadow:0 10px 28px rgba(124,58,237,.3)!important}
.staff-tab:hover{background:rgba(168,85,247,.18)!important}
.viewer-table th{background:#241038!important;color:#e9d5ff!important}
.viewer-table td{background:rgba(18,8,32,.68)!important;color:#f5edff!important}
.viewer-table tbody tr:nth-child(even) td{background:rgba(38,17,60,.55)!important}
.viewer-table tbody tr:hover td{background:rgba(124,58,237,.22)!important}
input:focus,textarea:focus,select:focus{border-color:#c084fc!important;box-shadow:0 0 0 3px rgba(168,85,247,.15),0 0 22px rgba(168,85,247,.1)!important}
@media(max-width:700px){body{padding:16px!important}.hero{min-height:590px!important}.hero h1{font-size:clamp(62px,17vw,100px)!important}.card,.news-card,.project-mini-card,.service-card,.owner-card,.gallery-card{border-radius:17px!important}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;scroll-behavior:auto!important;transition:none!important}}

</style>
</head>
<body>
<div class="box">
<h1>JHR {{ title }}</h1>
<p>{{ message }}</p>
{% with messages = get_flashed_messages() %}{% for msg in messages %}<div class="note">{{ msg }}</div>{% endfor %}{% endwith %}
<form method="POST">
<label>Username</label><input type="text" name="username" required autocomplete="username">
<label>Password</label><input type="password" name="password" required autocomplete="current-password">
<button type="submit">{{ action }}</button>
</form>
<a href="{{ url_for('home') }}">← Back to JHR</a>
</div>
</body>
</html>
"""

# =========================================================
# STAFF LOGIN
# =========================================================

def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_id"):
            return redirect(url_for("login"))

        last_activity = session.get("staff_last_activity")
        if not last_activity or time.time() - float(last_activity) > STAFF_SESSION_TIMEOUT.total_seconds():
            session.clear()
            flash("Your staff session expired after 5 minutes of inactivity. Please log in again.")
            return redirect(url_for("login"))

        session.permanent = True
        session["staff_last_activity"] = time.time()
        return view(*args, **kwargs)
    return wrapped


def superadmin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("staff_id") or session.get("staff_role") != "superadmin":
            flash("Superadmin access required.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.before_request
def expire_staff_session():
    """Expire staff sessions even when the requested route is public."""
    if not session.get("staff_id"):
        return

    last_activity = session.get("staff_last_activity")
    if not last_activity:
        session.clear()
        return

    if time.time() - float(last_activity) > STAFF_SESSION_TIMEOUT.total_seconds():
        session.clear()
        if request.endpoint not in {"login", "logout"}:
            flash("Your staff session expired after 5 minutes of inactivity. Please log in again.")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        staff = staff_accounts_collection.find_one({"username": username})

        if staff and check_password_hash(staff.get("password", ""), password):
            session.clear()
            session.permanent = True
            session["staff_id"] = str(staff["_id"])
            session["staff_username"] = staff.get("username", username)
            session["staff_role"] = staff.get("role", "staff")
            session["staff_last_activity"] = time.time()
            flash("Welcome, " + staff.get("username", username) + "!")
            return redirect(url_for("home"))

        flash("Invalid staff username or password.")

    return render_template_string(
        AUTH_HTML,
        title="Staff Login",
        action="Login",
        message="Log in to manage gallery pictures, messages, and news."
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


@app.route("/staff/heartbeat", methods=["POST"])
@staff_required
def staff_heartbeat():
    return ("", 204)


# =========================================================
# GALLERY UPLOAD
# =========================================================

@app.route("/gallery/upload", methods=["POST"])
@staff_required
def upload_gallery():
    """Upload gallery images and save their metadata safely."""
    files = request.files.getlist("images")

    if not files:
        flash("No picture was selected.")
        return redirect(url_for("home") + "#gallery")

    # Make sure the upload directory exists on every request. This is
    # especially useful on fresh Render instances.
    os.makedirs(GALLERY_FOLDER, exist_ok=True)

    title = request.form.get("gallery_title", "").strip()[:160]
    description = request.form.get("gallery_description", "").strip()[:2000]
    if not title or not description:
        flash("Add a title and description first.")
        return redirect(url_for("home") + "#gallery")

    added = 0
    skipped = []

    for index, image in enumerate(files):
        gridfs_id = None
        original_name = (image.filename or "").strip()

        if not original_name:
            skipped.append("an unnamed file")
            continue

        if not allowed_file(original_name):
            skipped.append(original_name)
            continue

        filename = secure_filename(original_name)
        if not filename:
            skipped.append(original_name)
            continue

        base, ext = os.path.splitext(filename)
        ext = ext.lower()

        # Always create a unique server-side filename. This prevents an
        # existing upload from overwriting another picture.
        candidate = f"{base}_{uuid4().hex[:10]}{ext}"
        filepath = os.path.join(GALLERY_FOLDER, candidate)

        # All photos selected in one upload represent the same event/group,
        # so they share one title and one description.

        try:
            # Persist the image in MongoDB GridFS. Render's local filesystem
            # is ephemeral, so this is what makes gallery uploads survive
            # restarts, redeploys, and new Render instances.
            image.stream.seek(0)
            gridfs_id = gallery_fs.put(
                image.stream,
                filename=candidate,
                content_type=image.mimetype or mimetypes.guess_type(candidate)[0] or "application/octet-stream",
                metadata={"original_filename": original_name}
            )

            gallery_collection.insert_one({
                "filename": candidate,
                "original_filename": original_name,
                "title": title,
                "description": description,
                "created_at": now_string(),
                "author_id": session.get("staff_id"),
                "gridfs_id": gridfs_id
            })

            # Keep a temporary local copy for fast serving during the current
            # Render instance. The persistent copy is the GridFS version.
            try:
                image.stream.seek(0)
                image.save(filepath)
            except Exception:
                app.logger.warning("Could not create local gallery cache for %s", candidate)

            added += 1

        except Exception as exc:
            try:
                if 'gridfs_id' in locals() and gridfs_id:
                    gallery_fs.delete(gridfs_id)
            except Exception:
                pass
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
            except OSError:
                pass
            skipped.append(original_name)
            app.logger.exception("Gallery upload failed for %s: %s", original_name, exc)

    if added:
        message = f"{added} picture(s) imported into the gallery successfully."
        if skipped:
            message += f" {len(skipped)} file(s) were skipped."
        flash(message)
    else:
        flash("No pictures were uploaded. Please select JPG, JPEG, PNG, WEBP, or GIF files and try again.")

    return redirect(url_for("home") + "#gallery")


# =========================================================
# NEWS / ANNOUNCEMENT IMAGE UPLOAD
# =========================================================

@app.route("/news-image/<path:filename>")
def news_image(filename):
    return uploaded_image_response(NEWS_FOLDER, filename)

# =========================================================
# FREE CODING CLASS MESSAGES
# =========================================================


# =========================================================
# FREE CODING CLASS MESSAGES
# =========================================================

@app.route("/coding-class-message", methods=["POST"])
def coding_class_message():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        flash("Please fill in your name, email, and message.")
        return redirect(url_for("home") + "#coding-classes")

    if len(name) > 120 or len(email) > 200 or len(message) > 5000:
        flash("Please keep your name, email, and message within the allowed length.")
        return redirect(url_for("home") + "#coding-classes")

    class_messages_collection.insert_one({
        "name": name,
        "email": email,
        "message": message,
        "created_at": now_string()
    })

    flash("Your message was sent to the JHR staff.")
    return redirect(url_for("home") + "#coding-classes")


def _db_ping_ok():
    try:
        mongo_db.command("ping")
        return True
    except Exception:
        return False


# =========================================================
# STAFF DASHBOARD
# =========================================================

@app.route("/staff")
@staff_required
def staff_dashboard():
    messages = [
        normalize_message(doc)
        for doc in class_messages_collection.find().sort("created_at", -1)
    ]

    staff_accounts = [
        normalize_staff(doc)
        for doc in staff_accounts_collection.find().sort("username", 1)
    ]
    viewers = detailed_viewers()

    return render_template_string(
        STAFF_DASHBOARD_HTML,
        messages=messages,
        staff_accounts=staff_accounts,
        news_items=news_items(),
        viewers=viewers,
        viewer_total=len(viewers),
        viewer_views=sum(item["total_views"] for item in viewers),
        staff_username=session.get("staff_username"),
        staff_role=session.get("staff_role", "staff"),
        superadmin_audit=[normalize_audit(d) for d in audit_collection.find().sort("_id", -1).limit(30)],
        superadmin_stats={"accounts": staff_accounts_collection.count_documents({}), "gallery": gallery_collection.count_documents({}), "news": news_collection.count_documents({}), "messages": class_messages_collection.count_documents({}), "viewers": viewers_collection.count_documents({}), "gridfs": mongo_db["gallery_files.files"].count_documents({}), "audit": audit_collection.count_documents({}), "storage_mb": round(mongo_db["gallery_files.files"].aggregate([{ "$group": {"_id": None, "bytes": {"$sum": "$length"}}}]).next().get("bytes", 0) / 1048576, 2) if mongo_db["gallery_files.files"].count_documents({}) else 0, "db": "Online" if _db_ping_ok() else "Check"}
    )


@app.route("/staff/change-password", methods=["POST"])
@staff_required
def change_staff_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(new_password) < 6:
        flash("New password must be at least 6 characters.")
        return redirect(url_for("staff_dashboard"))

    if new_password != confirm_password:
        flash("New passwords do not match.")
        return redirect(url_for("staff_dashboard"))

    try:
        staff = staff_accounts_collection.find_one({"_id": ObjectId(session["staff_id"])})
    except (InvalidId, TypeError):
        staff = None

    if not staff or not check_password_hash(staff.get("password", ""), current_password):
        flash("Current password is incorrect.")
        return redirect(url_for("staff_dashboard"))

    staff_accounts_collection.update_one(
        {"_id": staff["_id"]},
        {"$set": {"password": generate_password_hash(new_password)}}
    )

    flash("Your staff password has been changed.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/add-account", methods=["POST"])
@staff_required
def add_staff_account():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if len(username) < 3:
        flash("Staff username must be at least 3 characters.")
        return redirect(url_for("staff_dashboard"))
    if len(username) > 80:
        flash("Staff username is too long.")
        return redirect(url_for("staff_dashboard"))
    if len(password) < 6:
        flash("Staff password must be at least 6 characters.")
        return redirect(url_for("staff_dashboard"))
    if password != confirm_password:
        flash("New staff passwords do not match.")
        return redirect(url_for("staff_dashboard"))

    try:
        staff_accounts_collection.insert_one({
            "username": username,
            "password": generate_password_hash(password),
            "created_at": now_string()
        })
    except DuplicateKeyError:
        flash("That staff username already exists.")
        return redirect(url_for("staff_dashboard"))

    flash("New staff account created.")
    return redirect(url_for("staff_dashboard"))


@app.route("/superadmin/toggle-role/<account_id>", methods=["POST"])
@superadmin_required
def superadmin_toggle_role(account_id):
    try:
        target = staff_accounts_collection.find_one({"_id": ObjectId(account_id)})
    except (InvalidId, TypeError):
        target = None
    if not target or str(target.get("_id")) == session.get("staff_id"):
        flash("That account cannot be changed here.")
        return redirect(url_for("staff_dashboard") + "#control")
    new_role = "staff" if target.get("role") == "superadmin" else "superadmin"
    staff_accounts_collection.update_one({"_id": target["_id"]}, {"$set": {"role": new_role}})
    audit_superadmin("Role changed", f"{target.get('username')} → {new_role}")
    flash(f"{target.get('username')} is now {new_role}.")
    return redirect(url_for("staff_dashboard") + "#control")

@app.route("/superadmin/export-viewers")
@superadmin_required
def superadmin_export_viewers():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Viewer ID", "IP", "Location", "Device", "Browser", "OS", "Views", "Last Seen", "Last Page"])
    for item in detailed_viewers():
        writer.writerow([item.get("viewer_id",""), item.get("ip",""), item.get("location",""), item.get("device",""), item.get("browser",""), item.get("os",""), item.get("total_views",0), item.get("last_seen",""), item.get("last_page","")])
    audit_superadmin("Viewer export", "Downloaded viewer analytics CSV")
    response = app.response_class(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=jhr_viewers.csv"
    return response

@app.route("/superadmin/export-gallery")
@superadmin_required
def superadmin_export_gallery():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Filename", "Title", "Description", "Uploaded At"])
    for item in gallery_collection.find().sort("_id", -1):
        writer.writerow([item.get("filename", ""), item.get("title", ""), item.get("description", ""), item.get("uploaded_at", "")])
    audit_superadmin("Gallery export", "Downloaded gallery metadata CSV")
    response = app.response_class(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=jhr_gallery.csv"
    return response

@app.route("/superadmin/clear-gallery", methods=["POST"])
@superadmin_required
def superadmin_clear_gallery():
    removed_files = 0
    for item in gallery_collection.find({}, {"gridfs_id": 1}):
        gid = item.get("gridfs_id")
        if gid:
            try:
                gallery_fs.delete(ObjectId(str(gid)))
                removed_files += 1
            except Exception:
                pass
    result = gallery_collection.delete_many({})
    audit_superadmin("Entire gallery deleted", f"Removed {result.deleted_count} gallery records and {removed_files} stored files")
    flash(f"Gallery cleared: {result.deleted_count} photos removed.")
    return redirect(url_for("staff_dashboard") + "#control")

@app.route("/superadmin/clear-audit", methods=["POST"])
@superadmin_required
def superadmin_clear_audit():
    result = audit_collection.delete_many({})
    flash(f"Cleared {result.deleted_count} audit logs.")
    return redirect(url_for("staff_dashboard") + "#control")

@app.route("/superadmin/delete-account/<account_id>", methods=["POST"])
@superadmin_required
def superadmin_delete_account(account_id):
    try: target=staff_accounts_collection.find_one({"_id":ObjectId(account_id)})
    except (InvalidId,TypeError): target=None
    if not target or target.get("role") == "superadmin" or str(target.get("_id")) == session.get("staff_id"):
        flash("That account cannot be deleted.")
        return redirect(url_for("staff_dashboard")+"#accounts")
    staff_accounts_collection.delete_one({"_id":target["_id"]})
    audit_superadmin("Account deleted", target.get("username", ""))
    flash("Staff account deleted.")
    return redirect(url_for("staff_dashboard")+"#accounts")

@app.route("/superadmin/reset-admin", methods=["POST"])
@superadmin_required
def superadmin_reset_admin():
    staff_accounts_collection.update_one({"username":"admin"},{"$set":{"password":generate_password_hash("ChangeMe123!"),"role":"staff"}},upsert=True)
    audit_superadmin("Admin reset", "Admin password reset to the default")
    flash("Admin password reset.")
    return redirect(url_for("staff_dashboard")+"#control")

@app.route("/superadmin/clear-viewers", methods=["POST"])
@superadmin_required
def superadmin_clear_viewers():
    result=viewers_collection.delete_many({})
    audit_superadmin("Viewer analytics cleared", str(result.deleted_count))
    flash(f"Cleared {result.deleted_count} viewer records.")
    return redirect(url_for("staff_dashboard")+"#control")

@app.route("/superadmin/cleanup-gridfs", methods=["POST"])
@superadmin_required
def superadmin_cleanup_gridfs():
    referenced={str(d.get("gridfs_id")) for d in gallery_collection.find({}, {"gridfs_id":1}) if d.get("gridfs_id")}
    removed=0
    for f in mongo_db["gallery_files.files"].find({}, {"_id":1}):
        if str(f["_id"]) not in referenced:
            try: gallery_fs.delete(f["_id"]); removed+=1
            except Exception: pass
    audit_superadmin("Storage cleanup", f"Removed {removed} orphaned files")
    flash(f"Removed {removed} orphaned stored photos.")
    return redirect(url_for("staff_dashboard")+"#control")

@app.route("/staff/delete-message/<message_id>", methods=["POST"])
@staff_required
def delete_staff_message(message_id):
    try:
        result = class_messages_collection.delete_one({"_id": ObjectId(message_id)})
    except (InvalidId, TypeError):
        result = None

    if result and result.deleted_count:
        flash("Message deleted successfully.")
    else:
        flash("Message not found.")

    return redirect(url_for("staff_dashboard"))


@app.route("/staff/add-news", methods=["POST"])
@staff_required
def add_news_item():
    kind = request.form.get("kind", "Announcement").strip()
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    uploaded_files = request.files.getlist("news_images")

    if kind not in {"News", "Announcement"}:
        kind = "Announcement"

    if not title or not content:
        flash("Please enter a title and message.")
        return redirect(url_for("staff_dashboard"))

    if len(title) > 160 or len(content) > 10000:
        flash("The news title or content is too long.")
        return redirect(url_for("staff_dashboard"))

    try:
        author_id = ObjectId(session["staff_id"])
    except (InvalidId, TypeError):
        flash("Your staff session is invalid. Please log in again.")
        session.clear()
        return redirect(url_for("login"))

    image_names = []

    for image in uploaded_files:
        if not image or not image.filename or not allowed_file(image.filename):
            continue

        filename = secure_filename(image.filename)
        if not filename:
            continue

        base, ext = os.path.splitext(filename)
        candidate = filename
        counter = 1

        while os.path.exists(os.path.join(NEWS_FOLDER, candidate)):
            candidate = f"{base}_{counter}{ext}"
            counter += 1

        image.save(os.path.join(NEWS_FOLDER, candidate))
        image_names.append(candidate)

    news_collection.insert_one({
        "kind": kind,
        "title": title,
        "content": content,
        "images": image_names,
        "created_at": now_string(),
        "author_id": str(author_id)
    })

    flash(f"{kind} published successfully.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/delete-news/<news_id>", methods=["POST"])
@staff_required
def delete_news_item(news_id):
    try:
        object_id = ObjectId(news_id)
        document = news_collection.find_one({"_id": object_id})
    except (InvalidId, TypeError):
        document = None

    if not document:
        flash("News/announcement not found.")
        return redirect(url_for("staff_dashboard"))

    for filename in document.get("images", []):
        safe_name = os.path.basename(filename)
        filepath = os.path.join(NEWS_FOLDER, safe_name)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass

    result = news_collection.delete_one({"_id": document["_id"]})

    if result.deleted_count:
        flash("News/announcement deleted.")
    else:
        flash("News/announcement could not be deleted.")

    return redirect(url_for("staff_dashboard"))


@app.route("/staff/delete-gallery/<image_id>", methods=["POST"])
@staff_required
def delete_gallery_image(image_id):
    """Delete an imported gallery image and its MongoDB metadata."""
    try:
        document = gallery_collection.find_one({"_id": ObjectId(image_id)})
    except (InvalidId, TypeError):
        document = None

    if not document:
        flash("Gallery photo not found.")
        return redirect(url_for("home") + "#gallery")

    filename = os.path.basename(document.get("filename", ""))

    # Delete the persistent MongoDB GridFS copy first.
    gridfs_id = document.get("gridfs_id")
    if gridfs_id:
        try:
            gallery_fs.delete(ObjectId(str(gridfs_id)))
        except Exception as exc:
            app.logger.warning("Could not remove GridFS gallery file %s: %s", gridfs_id, exc)

    # Also remove the temporary local cache if it exists.
    if filename:
        filepath = os.path.join(GALLERY_FOLDER, filename)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
            except OSError as exc:
                app.logger.warning("Could not remove gallery file %s: %s", filepath, exc)

    result = gallery_collection.delete_one({"_id": document["_id"]})
    if result.deleted_count:
        flash("Gallery photo deleted successfully.")
    else:
        flash("Gallery photo could not be deleted.")

    return redirect(url_for("home") + "#gallery")


@app.route("/gallery-image/<path:filename>")
def uploaded_gallery_image(filename):
    """Serve gallery photos from persistent GridFS, with local-cache fallback."""
    safe_filename = os.path.basename(filename)
    document = gallery_collection.find_one({"filename": safe_filename})

    if document and document.get("gridfs_id"):
        try:
            grid_id = ObjectId(str(document["gridfs_id"]))
            grid_file = gallery_fs.get(grid_id)
            return send_file(
                grid_file,
                mimetype=grid_file.content_type or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream",
                download_name=safe_filename,
                conditional=True
            )
        except Exception as exc:
            app.logger.warning("GridFS gallery read failed for %s: %s", safe_filename, exc)

    # Backward-compatible fallback for older local gallery files.
    return uploaded_image_response(GALLERY_FOLDER, safe_filename)

# =========================================================
# HEALTH
# =========================================================

@app.route("/health")
def health():
    try:
        mongo_client.admin.command("ping")
        return "JHR is running! MongoDB is connected.", 200
    except PyMongoError:
        return "JHR is running, but MongoDB is unavailable.", 503


# =========================================================
# PHOTO CHECK
# =========================================================

@app.route("/photo-check")
def photo_check():

    files = [

        "OfficialLogo.png",

        "Owner1.jpg",

        "Owner2.png",

        "IMG_0884.jpg",

        "IMG_0884.jpeg",

        "IMG_0884.png",

        "IMG_5798.jpg",

        "IMG_5798.jpeg",

        "IMG_5798.png",

        "IMG_12345.jpg",

        "IMG_12345.jpeg",

        "IMG_12345.png",

        "IMG_12345.webp",

    ]

    output = [
        "<h1>JHR Photo Check</h1>"
    ]


    found_bases = set()


    for filename in files:

        path = os.path.join(
            app.static_folder,
            filename
        )


        if os.path.isfile(path):

            output.append(
                f"✅ {filename} — FOUND"
            )

            found_bases.add(
                os.path.splitext(filename)[0]
            )


    expected = [
        "OfficialLogo",
        "Owner1",
        "Owner2",
        "IMG_0884",
        "IMG_5798",
        "IMG_12345",
    ]


    for base in expected:

        if base not in found_bases:

            output.append(
                f"❌ {base} — NOT FOUND"
            )


    return "<br>".join(output)


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
