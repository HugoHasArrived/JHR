from flask import Flask, render_template_string, request, redirect, url_for, session, abort, send_file, flash
import webbrowser
import threading
import sqlite3
import uuid
import re
import json

try:
    from pymongo import MongoClient, DESCENDING
    import gridfs
except ImportError:
    MongoClient = None
    DESCENDING = -1
    gridfs = None

try:
    import requests
except ImportError:
    requests = None
import os
import secrets
from io import BytesIO
from datetime import datetime


app = Flask(__name__)

# ============================================================
# JHR CONTENT STORAGE
# ============================================================

app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("JHR_DATABASE", os.path.join(BASE_DIR, "jhr.db"))
_db_dir = os.path.dirname(os.path.abspath(DATABASE))
os.makedirs(_db_dir, exist_ok=True)
STAFF_USERNAME = os.environ.get("STAFF_USERNAME", "admin")
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "ChangeMe123!")
MAX_IMAGE_MB = 10
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# MongoDB is used in production so uploads survive Render redeploys.
MONGO_URI = os.environ.get("MONGO_URI", "").strip()
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "jhr").strip() or "jhr"
mongo_client = None
mongo_db = None
mongo_fs = None

if MONGO_URI and MongoClient is not None and gridfs is not None:
    # Never let a bad Render environment variable prevent Flask/Gunicorn from
    # starting. PyMongo requires mongodb:// or mongodb+srv://.
    if MONGO_URI.startswith(("mongodb://", "mongodb+srv://")):
        try:
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
            mongo_db = mongo_client[MONGO_DB_NAME]
            mongo_fs = gridfs.GridFS(mongo_db)
            # Force a connection check so an invalid/unreachable Atlas setup is
            # detected here and the app can safely fall back to SQLite.
            mongo_client.admin.command("ping")
        except Exception as mongo_error:
            print(f"MongoDB disabled: {mongo_error}")
            mongo_client = None
            mongo_db = None
            mongo_fs = None
    else:
        print("MongoDB disabled: MONGO_URI must begin with mongodb:// or mongodb+srv://")

def using_mongo():
    return mongo_db is not None and mongo_fs is not None


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT NOT NULL CHECK(section IN ('gallery','news','announcement')),
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            image_data BLOB,
            image_mime TEXT,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS viewers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            device TEXT NOT NULL DEFAULT 'Unknown',
            browser TEXT NOT NULL DEFAULT 'Unknown',
            user_agent TEXT NOT NULL DEFAULT '',
            country TEXT NOT NULL DEFAULT 'Unknown',
            city TEXT NOT NULL DEFAULT 'Unknown',
            region TEXT NOT NULL DEFAULT '',
            referrer TEXT NOT NULL DEFAULT 'Direct',
            path TEXT NOT NULL DEFAULT '/',
            viewed_at TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()


def staff_required():
    return session.get("staff_logged_in") is True


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def read_uploaded_image(required=False):
    image = request.files.get("image")
    if not image or not image.filename:
        if required:
            raise ValueError("Please select an image.")
        return None, None

    if not allowed_file(image.filename):
        raise ValueError("Only PNG, JPG, JPEG, GIF and WEBP images are allowed.")

    data = image.read()
    if not data:
        raise ValueError("The selected image is empty.")

    if len(data) > MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(f"Image must be smaller than {MAX_IMAGE_MB} MB.")

    mime = image.mimetype or "application/octet-stream"
    if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        raise ValueError("Invalid image type.")

    return data, mime


def get_posts(section):
    if using_mongo():
        rows = list(mongo_db.posts.find({"section": section}).sort("created_at_sort", DESCENDING))
        for row in rows:
            row["id"] = str(row["_id"])
            row["image_mime"] = row.get("image_mime")
        return rows
    db = get_db()
    rows = db.execute(
        "SELECT id, section, title, description, image_mime, created_at FROM posts WHERE section=? ORDER BY id DESC",
        (section,)
    ).fetchall()
    db.close()
    return rows


def get_news_updates():
    """News and announcements are displayed and managed as one combined feed."""
    if using_mongo():
        rows = list(mongo_db.posts.find({"section": {"$in": ["news", "announcement"]}}).sort("created_at_sort", DESCENDING))
        for row in rows:
            row["id"] = str(row["_id"])
            row["image_mime"] = row.get("image_mime")
        return rows
    db = get_db()
    rows = db.execute(
        "SELECT id, section, title, description, image_mime, created_at "
        "FROM posts WHERE section IN ('news','announcement') ORDER BY id DESC"
    ).fetchall()
    db.close()
    return rows


def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "Unknown"


def parse_user_agent(ua):
    ua = ua or ""
    if re.search(r"iPhone", ua, re.I):
        device = "iPhone"
    elif re.search(r"iPad", ua, re.I):
        device = "iPad"
    elif re.search(r"Android", ua, re.I):
        device = "Android device"
    elif re.search(r"Windows", ua, re.I):
        device = "Windows PC"
    elif re.search(r"Macintosh|Mac OS", ua, re.I):
        device = "Mac"
    elif re.search(r"Linux", ua, re.I):
        device = "Linux PC"
    else:
        device = "Unknown device"
    if re.search(r"Edg/", ua): browser = "Microsoft Edge"
    elif re.search(r"Chrome/", ua) and not re.search(r"Edg/", ua): browser = "Google Chrome"
    elif re.search(r"Firefox/", ua): browser = "Mozilla Firefox"
    elif re.search(r"Safari/", ua) and not re.search(r"Chrome/", ua): browser = "Safari"
    else: browser = "Other / Unknown"
    return device, browser


def lookup_ip_location(ip):
    if not requests or not ip or ip in {"Unknown", "127.0.0.1", "::1"} or ip.startswith(("10.", "192.168.", "172.16.")):
        return {"country": "Local/Unknown", "city": "Local/Unknown", "region": ""}
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2.5)
        if r.ok:
            data = r.json()
            return {"country": data.get("country_name", "Unknown"), "city": data.get("city", "Unknown"), "region": data.get("region", "")}
    except Exception:
        pass
    return {"country": "Unknown", "city": "Unknown", "region": ""}


def record_viewer():
    """Record every homepage visit. MongoDB is preferred; SQLite is a reliable fallback."""
    try:
        ip = get_client_ip()
        device, browser = parse_user_agent(request.headers.get("User-Agent", ""))
        now = datetime.utcnow()
        location = lookup_ip_location(ip)
        data = {
            "ip": ip,
            "device": device,
            "browser": browser,
            "user_agent": request.headers.get("User-Agent", ""),
            "country": location["country"],
            "city": location["city"],
            "region": location["region"],
            "referrer": request.referrer or "Direct",
            "path": request.path,
            "viewed_at": now,
        }
        if using_mongo():
            mongo_db.viewers.insert_one(data)
        else:
            db = get_db()
            db.execute(
                """INSERT INTO viewers
                (ip,device,browser,user_agent,country,city,region,referrer,path,viewed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (ip, device, browser, data["user_agent"], location["country"],
                 location["city"], location["region"], data["referrer"],
                 data["path"], now.isoformat(timespec="seconds"))
            )
            db.commit()
            db.close()
    except Exception as e:
        # Viewer tracking must never break the public website.
        print(f"Viewer tracking error: {e}")


init_db()

def migrate_sqlite_to_mongo():
    """Copy existing local SQLite posts into MongoDB once, preserving old uploads."""
    if not using_mongo():
        return
    try:
        if mongo_db.posts.count_documents({}) > 0:
            return
        db = get_db()
        rows = db.execute("SELECT * FROM posts ORDER BY id ASC").fetchall()
        db.close()
        for row in rows:
            doc = {
                "legacy_id": row["id"],
                "section": row["section"],
                "title": row["title"],
                "description": row["description"],
                "created_at": row["created_at"],
            }
            if row["image_data"]:
                doc["image_id"] = mongo_fs.put(row["image_data"], contentType=row["image_mime"] or "application/octet-stream", filename=f"legacy-{row['id']}")
                doc["image_mime"] = row["image_mime"]
            mongo_db.posts.insert_one(doc)
    except Exception:
        # Do not prevent the website from starting if migration is unavailable.
        pass

migrate_sqlite_to_mongo()

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>JHR | Empowerment Through Technology</title>

<style>

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    scroll-behavior: smooth;
}

:root {
    --purple: #7628d9;
    --violet: #a83cff;
    --pink: #ff4fcf;
    --cyan: #24e7ff;
    --green: #62ff8a;
    --yellow: #ffe45e;

    --background: #f7f1ff;
    --card: #ffffff;
    --text: #261533;
    --muted: #6d6277;
}

body.dark {
    --background: #120a1c;
    --card: #21112e;
    --text: #ffffff;
    --muted: #d2c7db;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.7;
    overflow-x: hidden;

    text-align: center;
}

/* =========================
   HEADER
========================= */

nav {
    position: sticky;
    top: 0;
    z-index: 9999;

    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 20px;
    padding: 10px 25px;

    background: rgba(255,255,255,.96);
    backdrop-filter: blur(15px);

    box-shadow: 0 5px 30px rgba(60,20,100,.18);
}

body.dark nav {
    background: rgba(25,12,35,.96);
}

.logo {
    display: flex;
    align-items: center;
    gap: 10px;

    font-size: 25px;
    font-weight: 1000;
    letter-spacing: 2px;

    color: var(--purple);
}

.logo img {
    width: 48px;
    height: 48px;

    object-fit: contain;

    display: block;

    /* Makes white background of logo less noticeable */
    mix-blend-mode: multiply;
}

body.dark .logo img {
    mix-blend-mode: screen;
}

.nav-links {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
}

.nav-links a {
    color: var(--text);
    text-decoration: none;
    font-size: 13px;
    font-weight: bold;
}

.nav-links a:hover {
    color: var(--pink);
}

.nav-button,
.language-button {
    border: none;
    padding: 8px 12px;
    border-radius: 20px;
    cursor: pointer;

    background: linear-gradient(
        135deg,
        var(--purple),
        var(--pink)
    );

    color: white;
    font-weight: bold;
}

/* =========================
   HERO
========================= */

.hero {
    min-height: 680px;

    display: flex;
    align-items: center;
    justify-content: center;

    text-align: center;

    position: relative;
    overflow: hidden;

    color: white;

    background:
        radial-gradient(
            circle at 20% 20%,
            rgba(36,231,255,.35),
            transparent 25%
        ),
        radial-gradient(
            circle at 80% 20%,
            rgba(255,79,207,.35),
            transparent 25%
        ),
        radial-gradient(
            circle at 50% 90%,
            rgba(98,255,138,.25),
            transparent 30%
        ),
        linear-gradient(
            135deg,
            #26083f,
            #7027d9,
            #42136e
        );
}

.hero-content {
    position: relative;
    z-index: 2;
    max-width: 1000px;
    padding: 30px;
}

/* No logo inside hero.
   The logo is ONLY in the header. */

.badge {
    display: inline-block;

    padding: 10px 20px;
    border-radius: 30px;

    border: 1px solid rgba(255,255,255,.4);

    background: rgba(255,255,255,.12);

    margin-bottom: 20px;
    font-weight: bold;

    color: var(--green);
}

.hero h1 {
    font-size: clamp(70px, 13vw, 150px);

    line-height: .9;
    font-weight: 1000;
    letter-spacing: 8px;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            var(--cyan),
            var(--green),
            #ffffff,
            var(--pink)
        );

    background-size: 300%;

    -webkit-background-clip: text;
    color: transparent;

    animation: gradientMove 5s infinite linear;
}

@keyframes gradientMove {
    0% {
        background-position: 0%;
    }

    100% {
        background-position: 300%;
    }
}

.hero h2 {
    font-size: clamp(20px, 4vw, 38px);
    color: var(--yellow);
    margin: 25px 0;
}

.hero p {
    max-width: 800px;
    margin: auto;
    font-size: 20px;
}

.button {
    display: inline-block;

    margin: 25px 5px 0;

    padding: 14px 25px;

    border-radius: 35px;

    background:
        linear-gradient(
            135deg,
            var(--green),
            var(--cyan)
        );

    color: #182035;

    text-decoration: none;

    font-weight: 900;

    transition: .25s;
}

.button:hover {
    transform: translateY(-5px) scale(1.04);
}

.button.pink {
    background:
        linear-gradient(
            135deg,
            var(--pink),
            var(--violet)
        );

    color: white;
}

/* =========================
   BLOBS
========================= */

.blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(5px);
    opacity: .35;

    animation:
        blobMove 10s infinite alternate ease-in-out;
}

.blob.one {
    width: 220px;
    height: 220px;
    background: var(--cyan);
    top: 10%;
    left: 5%;
}

.blob.two {
    width: 300px;
    height: 300px;
    background: var(--pink);
    right: 4%;
    top: 25%;
}

.blob.three {
    width: 180px;
    height: 180px;
    background: var(--green);
    bottom: 5%;
    left: 30%;
}

@keyframes blobMove {

    0% {
        transform: translate(0,0) scale(1);
    }

    50% {
        transform: translate(70px,-40px) scale(1.2);
    }

    100% {
        transform: translate(-40px,60px) scale(.9);
    }
}

/* =========================
   SECTIONS
========================= */

.section {
    max-width: 1200px;
    margin: auto;
    padding: 90px 25px;
}

/* Center-align the JHR website content */
.section, .color-section, .games, footer, header {
    text-align: center;
}
.cards, .mission, .post-grid {
    justify-items: center;
}
.post-card {
    text-align: center;
}
.post-body {
    width: 100%;
}
.post-type {
    display: inline-block;
    margin-bottom: 8px;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1.2px;
    color: var(--purple);
}


.title {
    text-align: center;

    font-size: clamp(32px,5vw,48px);

    margin-bottom: 15px;

    background:
        linear-gradient(
            90deg,
            var(--purple),
            var(--pink),
            #00a9c7
        );

    -webkit-background-clip: text;
    color: transparent;
}

.subtitle {
    max-width: 850px;

    margin: 0 auto 45px;

    text-align: center;

    color: var(--muted);

    font-size: 18px;
}

/* =========================
   CARDS
========================= */

.cards {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(240px,1fr)
        );

    gap: 25px;
}

.card {
    background: var(--card);

    padding: 32px;

    border-radius: 22px;

    box-shadow:
        0 10px 30px rgba(60,20,90,.12);

    border-top:
        5px solid var(--purple);

    transition: .3s;
}

.card:hover {
    transform: translateY(-10px);

    box-shadow:
        0 20px 45px rgba(100,30,160,.2);
}

.card h3 {
    color: var(--purple);
    margin-bottom: 10px;
}

/* =========================
   MISSION
========================= */

.color-section {
    padding: 90px 25px;
    color: white;

    background:
        linear-gradient(
            135deg,
            #28093e,
            #7027d9,
            #a52b92
        );
}

.mission {
    max-width: 1200px;
    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px,1fr)
        );

    gap: 25px;
}

.mission-card {
    padding: 35px;
    text-align: center;

    border-radius: 25px;

    background:
        rgba(255,255,255,.1);

    border:
        1px solid rgba(255,255,255,.2);

    backdrop-filter: blur(10px);

    transition: .3s;
}

.mission-card:hover {
    transform:
        translateY(-10px)
        scale(1.03);
}

.mission-icon {
    font-size: 55px;
    margin-bottom: 15px;
}

/* =========================
   STATS
========================= */

.stats {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px,1fr)
        );

    gap: 20px;
}

.stat {
    text-align: center;

    padding: 25px;

    background: var(--card);

    border-radius: 20px;

    box-shadow:
        0 8px 25px rgba(50,20,80,.12);
}

.stat-number {
    font-size: 45px;
    font-weight: 1000;
    color: var(--purple);
}

/* =========================
   OWNERS
========================= */

.owners {
    max-width: 1100px;
    margin: 40px auto 0;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(300px,1fr)
        );

    gap: 30px;
}

.owner-card {
    background: var(--card);

    border-radius: 25px;

    overflow: hidden;

    box-shadow:
        0 12px 35px rgba(60,20,90,.15);

    border-top: 5px solid var(--pink);

    transition: .3s;
}

.owner-card:hover {
    transform: translateY(-8px);
}

.owner-photo {
    width: 100%;
    height: 350px;

    object-fit: cover;

    display: block;

    background: #eee;
}

.owner-info {
    padding: 28px;
}

.owner-info h3 {
    color: var(--purple);
    font-size: 27px;
    margin-bottom: 5px;
}

.owner-role {
    color: var(--pink);
    font-weight: bold;
    margin-bottom: 15px;
}

/* =========================
   JHR POSTS / GALLERY / NEWS
========================= */

.post-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 25px;
}

.post-card {
    background: var(--card);
    border-radius: 25px;
    overflow: hidden;
    box-shadow: 0 12px 35px rgba(60,20,90,.14);
    border-top: 5px solid var(--purple);
    transition: .3s;
}

.post-card:hover {
    transform: translateY(-7px);
}

.post-image {
    width: 100%;
    height: 260px;
    object-fit: cover;
    display: block;
    background: #eee;
}

.post-no-image {
    height: 260px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 60px;
    background: linear-gradient(135deg,#ead7ff,#d9faff);
}

.post-body {
    padding: 25px;
}

.post-body h3 {
    color: var(--purple);
    margin-bottom: 7px;
    font-size: 25px;
}

.post-date {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 12px;
}

.empty-posts {
    text-align: center;
    padding: 30px;
    background: var(--card);
    border-radius: 20px;
    color: var(--muted);
}

/* =========================
   GAMES
========================= */

.games {
    padding: 90px 25px;

    background:
        radial-gradient(
            circle at top left,
            #d7b5ff,
            transparent 35%
        ),
        radial-gradient(
            circle at bottom right,
            #8df7ff,
            transparent 30%
        ),
        #eee1f9;
}

.game-grid {
    max-width: 1200px;
    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px,1fr)
        );

    gap: 25px;
}

.game {
    background: var(--card);

    padding: 30px;

    text-align: center;

    border-radius: 25px;

    box-shadow:
        0 10px 30px rgba(60,20,90,.15);
}

.game h3 {
    color: var(--purple);
    margin-bottom: 12px;
}

.game button {
    border: none;

    padding: 12px 16px;

    margin: 5px;

    border-radius: 25px;

    cursor: pointer;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--pink)
        );

    color: white;

    font-weight: bold;
}

.game-result {
    margin-top: 15px;
    min-height: 30px;

    color: var(--purple);
    font-weight: bold;
}

/* =========================
   CONTACT
========================= */

.contact {
    max-width: 850px;
    margin: auto;

    padding: 45px;

    text-align: center;

    border-radius: 30px;

    background: var(--card);

    box-shadow:
        0 10px 35px rgba(60,20,90,.15);
}

.contact h2 {
    color: var(--purple);
    font-size: 35px;
}

.contact a {
    color: var(--purple);
    font-weight: bold;
}

/* =========================
   FOOTER
========================= */

footer {
    padding: 55px 20px;

    text-align: center;

    color: white;

    background:
        linear-gradient(
            135deg,
            #1c0829,
            #3c1258
        );
}

.footer-logo {
    font-size: 35px;
    font-weight: 1000;
    color: var(--green);
}

.social {
    display: inline-block;

    margin-top: 20px;

    padding: 12px 22px;

    border-radius: 30px;

    background: #1877f2;

    color: white;

    text-decoration: none;

    font-weight: bold;
}

/* =========================
   MUSIC
========================= */

.music-control {
    position: fixed;

    right: 20px;
    bottom: 20px;

    z-index: 99999;

    width: 58px;
    height: 58px;

    border: none;

    border-radius: 50%;

    cursor: pointer;

    font-size: 23px;

    color: white;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--pink)
        );
}

/* =========================
   TOP
========================= */

.top {
    position: fixed;

    bottom: 90px;
    right: 25px;

    width: 45px;
    height: 45px;

    border: none;

    border-radius: 50%;

    background: var(--cyan);

    color: #17203a;

    font-size: 20px;

    cursor: pointer;

    display: none;

    z-index: 999;
}

/* =========================
   MOBILE
========================= */

@media(max-width:800px) {

    nav {
        flex-direction: column;
        padding: 15px;
    }

    .nav-links {
        gap: 9px;
    }

    .nav-links a {
        font-size: 11px;
    }

    .hero {
        min-height: 650px;
    }

    .hero p {
        font-size: 17px;
    }

    .owner-photo {
        height: 300px;
    }
}

</style>
</head>

<body>

<!-- =========================
     HEADER
========================= -->

<nav>

<div class="logo">

<img
src="{{ url_for('static', filename='OfficialLogo.png') }}"
alt="JHR Logo"
>

<span>JHR</span>

</div>

<div class="nav-links">

<a href="#home">Home</a>
<a href="#about">About</a>
<a href="#mission">Mission</a>
<a href="#projects">Projects</a>
<a href="#experience">Experience</a>
<a href="#founders">Founders</a>
<a href="#gallery">Gallery</a>
<a href="#news">News & Announcements</a>
<a href="#games">Games</a>
<a href="#contact">Contact</a>
<a href="{{ url_for('staff_login') }}">Staff</a>

<button
class="language-button"
onclick="toggleLanguage()"
id="languageButton"
>
🇵🇭 FIL
</button>

<button
class="nav-button"
onclick="toggleDarkMode()"
>
🌙
</button>

</div>

</nav>


<!-- =========================
     HERO
========================= -->

<section class="hero" id="home">

<div class="blob one"></div>
<div class="blob two"></div>
<div class="blob three"></div>

<div class="hero-content">

<div
class="badge"
data-en="TECHNOLOGY • EDUCATION • INNOVATION"
data-fil="TEKNOLOHIYA • EDUKASYON • INOBASYON"
>
TECHNOLOGY • EDUCATION • INNOVATION
</div>

<h1>JHR</h1>

<h2
data-en="EMPOWERMENT THROUGH TECHNOLOGY"
data-fil="PAGPAPALAKAS SA PAMAMAGITAN NG TEKNOLOHIYA"
>
EMPOWERMENT THROUGH TECHNOLOGY
</h2>

<p
data-en="Turning technology, creativity and learning into opportunities for people and communities."
data-fil="Ginagamit namin ang teknolohiya, pagkamalikhain at pagkatuto upang lumikha ng mga oportunidad para sa mga tao at komunidad."
>
Turning technology, creativity and learning into opportunities for people and communities.
</p>

<a class="button" href="#about">
✨ Explore JHR
</a>

<a class="button pink" href="#games">
🎮 Play Games
</a>

</div>

</section>


<!-- =========================
     ABOUT
========================= -->

<section class="section" id="about">

<h2
class="title"
data-en="What is JHR?"
data-fil="Ano ang JHR?"
>
What is JHR?
</h2>

<p
class="subtitle"
data-en="JHR — Empowerment Through Technology."
data-fil="JHR — Pagpapalakas sa Pamamagitan ng Teknolohiya."
>
JHR — Empowerment Through Technology.
</p>

<div class="cards">

<div class="card">

<h3>💻 Technology</h3>

<p>
We explore technology as a tool for creativity,
learning and opportunity.
</p>

</div>

<div class="card">

<h3>📚 Learning</h3>

<p>
Learning new skills helps young people turn ideas
into real projects.
</p>

</div>

<div class="card">

<h3>🌱 Community</h3>

<p>
Technology can help communities connect,
learn and grow.
</p>

</div>

<div class="card">

<h3>💡 Ideas</h3>

<p>
Every big project starts with an idea and the
courage to try.
</p>

</div>

</div>

</section>


<!-- =========================
     MISSION
========================= -->

<section class="color-section" id="mission">

<h2
class="title"
style="color:white"
>
Our Mission
</h2>

<p
class="subtitle"
style="color:#eadcff"
>
Empowerment through technology, knowledge and creativity.
</p>

<div class="mission">

<div class="mission-card">

<div class="mission-icon">💻</div>

<h3>Technology</h3>

<p>
Promote creative and responsible technology use.
</p>

</div>

<div class="mission-card">

<div class="mission-icon">🎓</div>

<h3>Education</h3>

<p>
Encourage people to learn digital and technology skills.
</p>

</div>

<div class="mission-card">

<div class="mission-icon">🌍</div>

<h3>Community</h3>

<p>
Explore ways technology can create positive community impact.
</p>

</div>

<div class="mission-card">

<div class="mission-icon">🚀</div>

<h3>Innovation</h3>

<p>
Turn creative ideas into useful projects and experiences.
</p>

</div>

</div>

</section>


<!-- =========================
     STATS
========================= -->

<section class="section">

<h2 class="title">
JHR in Numbers
</h2>

<div class="stats">

<div class="stat">
<div class="stat-number">100+</div>
<p>Ideas</p>
</div>

<div class="stat">
<div class="stat-number">25+</div>
<p>Activities</p>
</div>

<div class="stat">
<div class="stat-number">10+</div>
<p>Projects</p>
</div>

<div class="stat">
<div class="stat-number">1</div>
<p>Big Mission</p>
</div>

</div>

</section>


<!-- =========================
     PROJECTS
========================= -->

<section class="section" id="projects">

<h2 class="title">
JHR Projects 🚀
</h2>

<p class="subtitle">
Our project showcase can grow as new JHR activities
and initiatives are completed.
</p>

<div class="cards">

<div class="card">
<h3>💻 Technology Projects</h3>
<p>
Websites, digital tools, programming, creative
technology and experiments.
</p>
</div>

<div class="card">
<h3>🏫 Education</h3>
<p>
Technology-related learning activities and
educational experiences.
</p>
</div>

<div class="card">
<h3>🌾 Community & Agriculture</h3>
<p>
Exploring how technology can support communities
and agricultural areas.
</p>
</div>

<div class="card">
<h3>🚀 Future Projects</h3>
<p>
More JHR projects will be added here as they
are officially completed.
</p>
</div>

</div>

</section>


<!-- =========================
     EXPERIENCE
========================= -->

<section class="section" id="experience">

<h2 class="title">
JHR Experience
</h2>

<p class="subtitle">
A timeline for documenting JHR activities,
events and experiences.
</p>

<div class="cards">

<div class="card">

<h3>🌱 Community Experiences</h3>

<p>
Learning from communities and exploring how
technology can be useful in everyday life.
</p>

</div>

<div class="card">

<h3>🏫 School Experiences</h3>

<p>
Exploring educational environments and learning
about technology and education.
</p>

</div>

<div class="card">

<h3>💻 Technology Experiences</h3>

<p>
Building projects, experimenting with code and
learning new technology skills.
</p>

</div>

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

<div class="owner-card">
<img
    class="owner-photo"
    src="{{ url_for('static', filename='Owner1.jpg') }}"
    alt="Jose Hugo Rafael T. Tan"
    loading="lazy"
    decoding="async"
>

<div class="owner-info">
<h3>Jose Hugo Rafael T. Tan</h3>

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
    Hugo helps guide JHR's vision, projects, and technology-focused activities.
</p>
</div>
</div>

<div class="owner-card">
<img
    class="owner-photo"
    src="{{ url_for('static', filename='Owner2.png') }}"
    alt="Julia Helga Raquel T. Tan"
    loading="lazy"
    decoding="async"
>

<div class="owner-info">
<h3>Julia Helga Raquel T. Tan</h3>

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
    Julia supports JHR's creativity, projects, and community-focused activities.
</p>
</div>
</div>

</div>

</section>


<!-- =========================
     GALLERY
========================= -->

<section class="section" id="gallery">

<h2 class="title">JHR Gallery 📸</h2>
<p class="subtitle">Photos and memories from JHR.</p>

{% if gallery %}
<div class="post-grid">
{% for post in gallery %}
<article class="post-card">
{% if post["image_mime"] %}
<img class="post-image" src="{{ url_for('post_image', post_id=post['id']) }}" alt="{{ post['title'] }}">
{% else %}
<div class="post-no-image">📷</div>
{% endif %}
<div class="post-body">
<h3>{{ post["title"] }}</h3>
<div class="post-date">{{ post["created_at"] }}</div>
<p>{{ post["description"] }}</p>
</div>
</article>
{% endfor %}
</div>
{% else %}
<div class="empty-posts">No gallery photos have been posted yet.</div>
{% endif %}

</section>


<!-- =========================
     NEWS & ANNOUNCEMENTS
========================= -->

<section class="section" id="news">

<h2 class="title">JHR News & Announcements 📰📢</h2>
<p class="subtitle">Latest JHR news, updates, and important announcements.</p>

{% if news %}
<div class="post-grid">
{% for post in news %}
<article class="post-card">
{% if post["image_mime"] %}
<img class="post-image" src="{{ url_for('post_image', post_id=post['id']) }}" alt="{{ post['title'] }}">
{% else %}
<div class="post-no-image">{% if post["section"] == "announcement" %}📢{% else %}📰{% endif %}</div>
{% endif %}
<div class="post-body">
<div class="post-type">{% if post["section"] == "announcement" %}ANNOUNCEMENT{% else %}NEWS{% endif %}</div>
<h3>{{ post["title"] }}</h3>
<div class="post-date">{{ post["created_at"] }}</div>
<p>{{ post["description"] }}</p>
</div>
</article>
{% endfor %}
</div>
{% else %}
<div class="empty-posts">No news or announcements have been posted yet.</div>
{% endif %}

</section>


<!-- =========================
     GAMES
========================= -->

<section class="games" id="games">

<h2 class="title">
JHR GAME ZONE 🎮
</h2>

<p class="subtitle">
Learn, think and have fun!
</p>

<div class="game-grid">

<div class="game">

<h3>⚡ Speed Math</h3>

<p>What is 12 × 8?</p>

<button onclick="mathGame(96)">96</button>
<button onclick="mathGame(88)">88</button>
<button onclick="mathGame(108)">108</button>

<div id="mathResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🧠 Tech Quiz</h3>

<p>What does CPU mean?</p>

<button onclick="techGame(false)">
Computer Personal Unit
</button>

<button onclick="techGame(true)">
Central Processing Unit
</button>

<button onclick="techGame(false)">
Central Program Utility
</button>

<div id="techResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🔢 Number Guess</h3>

<p>Guess the secret number: 1–5</p>

<button onclick="guessGame(1)">1</button>
<button onclick="guessGame(2)">2</button>
<button onclick="guessGame(3)">3</button>
<button onclick="guessGame(4)">4</button>
<button onclick="guessGame(5)">5</button>

<div id="guessResult" class="game-result">
Good luck!
</div>

</div>


<div class="game">

<h3>🌍 Digital Citizenship</h3>

<p>Which is responsible technology use?</p>

<button onclick="citizenGame(true)">
Learning 📚
</button>

<button onclick="citizenGame(false)">
Cyberbullying 😈
</button>

<button onclick="citizenGame(false)">
Fake News ❌
</button>

<div id="citizenResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🚀 JHR Challenge</h3>

<p>
What should you do when learning something difficult?
</p>

<button onclick="challengeGame(true)">
Keep practicing 💪
</button>

<button onclick="challengeGame(false)">
Give up 😴
</button>

<button onclick="challengeGame(false)">
Never try again ❌
</button>

<div id="challengeResult" class="game-result">
Your challenge awaits!
</div>

</div>


<div class="game">

<h3>➕ Quick Addition</h3>

<p>
<strong>27 + 15 = ?</strong>
</p>

<button onclick="additionGame(42)">42</button>
<button onclick="additionGame(41)">41</button>
<button onclick="additionGame(52)">52</button>

<div id="additionResult" class="game-result">
Choose!
</div>

</div>


<div class="game">

<h3>💡 Technology True or False</h3>

<p>
A strong password helps protect an account.
</p>

<button onclick="trueFalseGame(true)">
TRUE
</button>

<button onclick="trueFalseGame(false)">
FALSE
</button>

<div id="trueFalseResult" class="game-result">
Choose!
</div>

</div>


<div class="game">

<h3>🌟 JHR Values</h3>

<p>
Which value helps a community grow?
</p>

<button onclick="valuesGame(true)">
Cooperation 🤝
</button>

<button onclick="valuesGame(false)">
Bullying ❌
</button>

<button onclick="valuesGame(false)">
Dishonesty ❌
</button>

<div id="valuesResult" class="game-result">
Choose!
</div>

</div>

</div>

</section>


<!-- =========================
     CONTACT
========================= -->

<section class="section" id="contact">

<div class="contact">

<h2>JHR</h2>

<p>
<strong>
Join us in this journey!
</strong>
</p>

<br>

<p>
📧
<a href="mailto:josehr.tan@gmail.com">
josehr.tan@gmail.com
</a>
</p>

<p>
📱
<a href="tel:09096585708">
0909 658 5708
</a>
</p>

<br>

<a
class="button"
href="https://www.facebook.com/jhrtan"
target="_blank"
rel="noopener noreferrer"
>
📘 JHR Facebook
</a>

</div>

</section>


<!-- =========================
     FOOTER
========================= -->

<footer>

<div class="footer-logo">
JHR
</div>

<div>
EMPOWERMENT THROUGH TECHNOLOGY
</div>

<p>
Technology • Education • Innovation • Community
</p>

<a
class="social"
href="https://www.facebook.com/jhrtan"
target="_blank"
rel="noopener noreferrer"
>
📘 JHR Facebook
</a>

<br><br>

<p>
© 2026 JHR
</p>

</footer>


<!-- MUSIC BUTTON -->

<button
class="music-control"
onclick="toggleMusic()"
id="musicButton"
>
🎵
</button>


<!-- TOP BUTTON -->

<button
class="top"
id="topButton"
onclick="window.scrollTo({top:0,behavior:'smooth'})"
>
↑
</button>


<script>

/* =========================
   LANGUAGE
========================= */

let currentLanguage =
localStorage.getItem("jhr-language") || "en";

function translatePage() {

    document.querySelectorAll("[data-en]").forEach(element => {

        const text =
        currentLanguage === "en"
        ? element.getAttribute("data-en")
        : element.getAttribute("data-fil");

        if (text) {
            element.textContent = text;
        }

    });

    document.getElementById("languageButton").textContent =
    currentLanguage === "en"
    ? "🇵🇭 FIL"
    : "🇬🇧 ENG";
}

function toggleLanguage() {

    currentLanguage =
    currentLanguage === "en"
    ? "fil"
    : "en";

    localStorage.setItem(
        "jhr-language",
        currentLanguage
    );

    translatePage();
}

translatePage();


/* =========================
   DARK MODE
========================= */

function toggleDarkMode() {

    document.body.classList.toggle("dark");

    localStorage.setItem(
        "jhr-dark-mode",
        document.body.classList.contains("dark")
    );
}

if (
    localStorage.getItem("jhr-dark-mode")
    === "true"
) {
    document.body.classList.add("dark");
}


/* =========================
   GAMES
========================= */

function mathGame(answer) {

    document.getElementById("mathResult").textContent =
    answer === 96
    ? "🎉 CORRECT!"
    : "❌ Try again!";
}


function techGame(correct) {

    document.getElementById("techResult").textContent =
    correct
    ? "🚀 Correct!"
    : "❌ Try again!";
}


let secretNumber =
Math.floor(Math.random() * 5) + 1;

function guessGame(number) {

    if (number === secretNumber) {

        document.getElementById("guessResult").textContent =
        "🏆 AMAZING!";

        secretNumber =
        Math.floor(Math.random() * 5) + 1;

    } else {

        document.getElementById("guessResult").textContent =
        "❌ Nope! Try again.";

    }
}


function citizenGame(correct) {

    document.getElementById("citizenResult").textContent =
    correct
    ? "🌟 Correct!"
    : "❌ Try again!";
}


function challengeGame(correct) {

    document.getElementById("challengeResult").textContent =
    correct
    ? "💪 That's the JHR spirit!"
    : "😂 Keep going!";
}


function additionGame(answer) {

    document.getElementById("additionResult").textContent =
    answer === 42
    ? "🎉 Correct!"
    : "❌ Try again!";
}


function trueFalseGame(correct) {

    document.getElementById("trueFalseResult").textContent =
    correct
    ? "🔐 Correct! Stay safe online!"
    : "❌ Try again!";
}


function valuesGame(correct) {

    document.getElementById("valuesResult").textContent =
    correct
    ? "🤝 Correct! Cooperation matters!"
    : "❌ Try again!";
}


/* =========================
   TOP BUTTON
========================= */

window.addEventListener("scroll", function() {

    document.getElementById("topButton").style.display =
    window.scrollY > 500
    ? "block"
    : "none";

});


/* =========================
   SIMPLE MUSIC
========================= */

let audioContext = null;
let musicPlaying = false;
let musicTimer = null;

const melody = [
    261.63,
    329.63,
    392.00,
    523.25,
    392.00,
    329.63
];

let noteIndex = 0;

function playNote() {

    if (!audioContext) {

        audioContext =
        new (
            window.AudioContext ||
            window.webkitAudioContext
        )();

    }

    const oscillator =
    audioContext.createOscillator();

    const gain =
    audioContext.createGain();

    oscillator.type = "sine";

    oscillator.frequency.value =
    melody[noteIndex];

    gain.gain.setValueAtTime(
        0.0001,
        audioContext.currentTime
    );

    gain.gain.exponentialRampToValueAtTime(
        0.05,
        audioContext.currentTime + .03
    );

    gain.gain.exponentialRampToValueAtTime(
        0.0001,
        audioContext.currentTime + .4
    );

    oscillator.connect(gain);
    gain.connect(audioContext.destination);

    oscillator.start();

    oscillator.stop(
        audioContext.currentTime + .45
    );

    noteIndex =
    (noteIndex + 1) % melody.length;
}


function toggleMusic() {

    const button =
    document.getElementById("musicButton");

    if (!audioContext) {

        audioContext =
        new (
            window.AudioContext ||
            window.webkitAudioContext
        )();

    }

    if (audioContext.state === "suspended") {
        audioContext.resume();
    }

    musicPlaying = !musicPlaying;

    if (musicPlaying) {

        playNote();

        musicTimer =
        setInterval(playNote, 500);

        button.textContent = "🔊";

    } else {

        clearInterval(musicTimer);

        button.textContent = "🎵";
    }
}

</script>

</body>
</html>
"""


@app.route("/")
def home():
    record_viewer()
    return render_template_string(
        HTML,
        gallery=get_posts("gallery"),
        news=get_news_updates()
    )


@app.route("/image/<post_id>")
def post_image(post_id):
    if using_mongo():
        from bson import ObjectId
        try:
            post = mongo_db.posts.find_one({"_id": ObjectId(post_id)})
        except Exception:
            post = None
        if not post or not post.get("image_id"):
            abort(404)
        try:
            blob = mongo_fs.get(post["image_id"])
            return send_file(BytesIO(blob.read()), mimetype=post.get("image_mime") or "application/octet-stream", max_age=3600)
        except Exception:
            abort(404)

    try:
        legacy_id = int(post_id)
    except ValueError:
        abort(404)
    db = get_db()
    post = db.execute("SELECT image_data, image_mime FROM posts WHERE id=?", (legacy_id,)).fetchone()
    db.close()
    if not post or not post["image_data"]:
        abort(404)
    return send_file(BytesIO(post["image_data"]), mimetype=post["image_mime"], max_age=0)


@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if staff_required():
        return redirect(url_for("staff_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (secrets.compare_digest(username, STAFF_USERNAME) and
                secrets.compare_digest(password, STAFF_PASSWORD)):
            session.clear()
            session["staff_logged_in"] = True
            return redirect(url_for("staff_dashboard"))

        flash("Incorrect username or password.")

    return render_template_string(STAFF_LOGIN_HTML)


@app.route("/staff/logout")
def staff_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/staff")
def staff_dashboard():
    if not staff_required():
        return redirect(url_for("staff_login"))

    return render_template_string(
        STAFF_DASHBOARD_HTML,
        gallery=get_posts("gallery"),
        news=get_news_updates()
    )


@app.route("/staff/add/<section>", methods=["POST"])
def add_post(section):
    if not staff_required(): return redirect(url_for("staff_login"))
    if section not in {"gallery", "news", "announcement"}: abort(404)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if not title or not description:
        flash("Title and description are required.")
        return redirect(url_for("staff_dashboard"))
    try:
        image_data, image_mime = read_uploaded_image(required=(section == "gallery"))
    except ValueError as exc:
        flash(str(exc)); return redirect(url_for("staff_dashboard"))
    created_text = datetime.now().strftime("%B %d, %Y %I:%M %p")
    created_sort = datetime.utcnow()
    if using_mongo():
        doc = {"section": section, "title": title, "description": description, "created_at": created_text, "created_at_sort": created_sort}
        if image_data is not None:
            doc["image_id"] = mongo_fs.put(image_data, contentType=image_mime, filename=secrets.token_hex(8))
            doc["image_mime"] = image_mime
        mongo_db.posts.insert_one(doc)
    else:
        db = get_db(); db.execute("INSERT INTO posts (section,title,description,image_data,image_mime,created_at) VALUES (?,?,?,?,?,?)", (section,title,description,image_data,image_mime,created_text)); db.commit(); db.close()
    flash("Post published successfully and saved permanently.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/edit/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if not staff_required(): return redirect(url_for("staff_login"))
    if using_mongo():
        from bson import ObjectId
        try: post = mongo_db.posts.find_one({"_id": ObjectId(post_id)})
        except Exception: post = None
        if post is None: abort(404)
        post["id"] = str(post["_id"]); post["image_mime"] = post.get("image_mime")
    else:
        try: legacy_id=int(post_id)
        except ValueError: abort(404)
        db=get_db(); post=db.execute("SELECT * FROM posts WHERE id=?",(legacy_id,)).fetchone(); db.close()
        if post is None: abort(404)
    if request.method == "POST":
        title=request.form.get("title","").strip(); description=request.form.get("description","").strip()
        if not title or not description:
            flash("Title and description are required."); return redirect(url_for("edit_post",post_id=post_id))
        try: image_data,image_mime=read_uploaded_image(required=False)
        except ValueError as exc: flash(str(exc)); return redirect(url_for("edit_post",post_id=post_id))
        if using_mongo():
            from bson import ObjectId
            update={"title":title,"description":description}
            if image_data is not None:
                if post.get("image_id"):
                    try: mongo_fs.delete(post["image_id"])
                    except Exception: pass
                update["image_id"]=mongo_fs.put(image_data,contentType=image_mime,filename=secrets.token_hex(8)); update["image_mime"]=image_mime
            mongo_db.posts.update_one({"_id":ObjectId(post_id)},{"$set":update})
        else:
            db=get_db()
            if image_data is not None: db.execute("UPDATE posts SET title=?,description=?,image_data=?,image_mime=? WHERE id=?",(title,description,image_data,image_mime,int(post_id)))
            else: db.execute("UPDATE posts SET title=?,description=? WHERE id=?",(title,description,int(post_id)))
            db.commit(); db.close()
        flash("Post updated successfully. Your changes are now saved."); return redirect(url_for("staff_dashboard"))
    return render_template_string(EDIT_POST_HTML, post=post)


@app.route("/staff/delete/<post_id>", methods=["POST"])
def delete_post(post_id):
    if not staff_required(): return redirect(url_for("staff_login"))
    if using_mongo():
        from bson import ObjectId
        try: post=mongo_db.posts.find_one({"_id":ObjectId(post_id)})
        except Exception: post=None
        if post:
            if post.get("image_id"):
                try: mongo_fs.delete(post["image_id"])
                except Exception: pass
            mongo_db.posts.delete_one({"_id":post["_id"]})
    else:
        db=get_db(); db.execute("DELETE FROM posts WHERE id=?",(int(post_id),)); db.commit(); db.close()
    flash("Post and its photo were deleted."); return redirect(url_for("staff_dashboard"))


@app.route("/staff/viewers")
def viewer_details():
    if not staff_required():
        return redirect(url_for("staff_login"))
    viewers = []
    total_views = 0
    storage = "SQLite fallback"
    if using_mongo():
        viewers = list(mongo_db.viewers.find().sort("viewed_at", DESCENDING).limit(500))
        total_views = mongo_db.viewers.count_documents({})
        storage = "MongoDB"
    else:
        db = get_db()
        rows = db.execute("SELECT * FROM viewers ORDER BY id DESC LIMIT 500").fetchall()
        total_views = db.execute("SELECT COUNT(*) FROM viewers").fetchone()[0]
        db.close()
        viewers = [dict(row) for row in rows]
    return render_template_string(
        VIEWER_DETAILS_HTML, viewers=viewers, total_views=total_views,
        mongo_enabled=using_mongo(), storage=storage
    )


STAFF_LOGIN_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JHR Staff Login</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:Arial;background:linear-gradient(135deg,#26083f,#7628d9,#ff4fcf)}
.box{width:min(420px,90%);background:#fff;padding:35px;border-radius:25px;box-shadow:0 20px 60px #0005}
h1{color:#7628d9} input,button{width:100%;padding:13px;margin:8px 0;box-sizing:border-box;border-radius:10px;border:1px solid #ddd} button{border:0;color:#fff;background:linear-gradient(135deg,#7628d9,#ff4fcf);font-weight:bold;cursor:pointer}.error{padding:10px;background:#ffe8ed;color:#a00;border-radius:10px}a{color:#7628d9}
</style>
</head>
<body><div class="box"><h1>JHR Staff</h1><p>Manage Gallery, News and Announcements.</p>
{% with messages=get_flashed_messages() %}{% for message in messages %}<div class="error">{{ message }}</div>{% endfor %}{% endwith %}
<form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Sign In</button></form>
<p><a href="{{ url_for('home') }}">← Back to website</a></p></div></body></html>
"""


EDIT_POST_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Edit JHR Post</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#f7f1ff;color:#261533;text-align:center}.box{max-width:760px;margin:40px auto;padding:30px;background:#fff;border-radius:22px;box-shadow:0 10px 30px #3c145c1f}h1{color:#7628d9}label{display:block;font-weight:bold;margin-top:15px}label{display:block;text-align:center;font-weight:bold}input,textarea{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;margin:7px 0 14px;font:inherit}textarea{min-height:160px;resize:vertical}button{padding:12px 20px;border:0;border-radius:20px;background:#7628d9;color:#fff;font-weight:bold;cursor:pointer}.cancel{display:inline-block;margin-left:10px;padding:12px 20px;border-radius:20px;background:#eee;color:#333;text-decoration:none}.current{margin:15px 0}.current img{max-width:320px;max-height:220px;object-fit:cover;border-radius:12px;display:block;margin-top:8px}.hint{color:#777;font-size:14px}.type{display:inline-block;background:#eee0ff;color:#7628d9;border-radius:20px;padding:7px 12px}
</style>
</head>
<body>
<div class="box">
<span class="type">{{ post['section']|title }}</span>
<h1>Edit Post</h1>
<p class="hint">Fix the title or description below. You can also replace the current photo. Leave the photo field empty to keep the existing photo.</p>
<form method="POST" enctype="multipart/form-data">
<label>Title</label>
<input name="title" maxlength="200" value="{{ post['title'] }}" required>
<label>Description</label>
<textarea name="description" maxlength="5000" required>{{ post['description'] }}</textarea>
{% if post['image_mime'] %}
<div class="current"><strong>Current photo:</strong><img src="{{ url_for('post_image', post_id=post['id']) }}" alt="Current photo"></div>
{% endif %}
<label>Replace Photo (optional)</label>
<input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp">
<button type="submit">Save Changes</button>
<a class="cancel" href="{{ url_for('staff_dashboard') }}">Cancel</a>
</form>
</div>
</body>
</html>
"""


STAFF_DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JHR Staff Dashboard</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial;background:#f7f1ff;color:#261533;text-align:center}header{padding:25px 5%;color:#fff;background:linear-gradient(135deg,#26083f,#7628d9,#ff4fcf)}header a{color:#fff;text-decoration:none;margin-right:20px}main{max-width:1200px;margin:auto;padding:30px 20px;text-align:center}.panel{background:#fff;border-radius:22px;padding:25px;margin-bottom:25px;box-shadow:0 10px 30px #3c145c1f}.tabs{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:25px}.tabs a{padding:11px 17px;background:#7628d9;color:#fff;text-decoration:none;border-radius:20px}label{display:block;text-align:center;font-weight:bold}input,textarea{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;margin:6px 0 14px;font:inherit}textarea{min-height:120px;resize:vertical}button{padding:11px 18px;border:0;border-radius:20px;background:#7628d9;color:#fff;font-weight:bold;cursor:pointer}.delete{background:#c62828}.edit{display:inline-block;padding:11px 18px;border-radius:20px;background:#7628d9;color:#fff;text-decoration:none;font-weight:bold;margin-right:6px}.actions{white-space:nowrap}.editbox{display:none;grid-column:1/-1;background:#faf7ff;border:1px solid #e5d5ff;border-radius:16px;padding:18px;margin-top:8px}.editbox:target{display:block}.editbox h4{margin-top:0;color:#7628d9}.editbox img{max-width:220px;max-height:150px;object-fit:cover;border-radius:10px;margin:8px 0}.editbox .save{background:#16834b}.editbox .cancel-edit{background:#777;text-decoration:none;color:#fff;display:inline-block;padding:11px 18px;border-radius:20px;margin-left:6px}.post{display:grid;grid-template-columns:180px 1fr auto;gap:20px;align-items:center;text-align:center;border-top:1px solid #eee;padding:18px 0}.post img{width:180px;height:120px;object-fit:cover;border-radius:12px}.post h3{color:#7628d9;margin:0}.muted{color:#777}.flash{padding:12px;background:#e8fff0;color:#146b35;border-radius:10px;margin-bottom:15px}@media(max-width:700px){.post{grid-template-columns:1fr}.post img{width:100%;height:220px}}
</style>
</head>
<body>
<header><h1>JHR Staff Dashboard</h1><p>Upload and manage website content.</p><a href="{{ url_for('home') }}">View Website</a><a href="{{ url_for('viewer_details') }}">👁️ Detailed Viewers</a><a href="{{ url_for('staff_logout') }}">Logout</a></header>
<main>
{% with messages=get_flashed_messages() %}{% for message in messages %}<div class="flash">{{ message }}</div>{% endfor %}{% endwith %}
<div class="tabs"><a href="#gallery">📸 Gallery</a><a href="#news">📰 News</a></div>

<section class="panel" id="gallery"><h2>📸 Gallery</h2><p>Gallery requires an image, title and description. You can permanently delete old photos below.</p>
<form method="POST" action="{{ url_for('add_post', section='gallery') }}" enctype="multipart/form-data"><label>Title</label><input name="title" maxlength="200" required><label>Description</label><textarea name="description" maxlength="5000" required></textarea><label>Photo</label><input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp" required><button>Upload Gallery Photo</button></form>
{% for post in gallery %}<div class="post">{% if post['image_mime'] %}<img src="{{ url_for('post_image',post_id=post['id']) }}" alt="{{ post['title'] }}">{% endif %}<div><h3>{{ post['title'] }}</h3><p class="muted">{{ post['created_at'] }}</p><p>{{ post['description'] }}</p></div><div class="actions"><a class="edit" href="{{ url_for('edit_post', post_id=post['id']) }}">✏️ Edit</a><form method="POST" action="{{ url_for('delete_post',post_id=post['id']) }}" style="display:inline"><button class="delete" type="submit" onclick="return confirm('Are you sure you want to permanently delete this post? This cannot be undone.')">🗑️ Delete</button></form></div><div class="editbox" id="edit-{{ post['id'] }}"><h4>✏️ Edit this post</h4><form method="POST" action="{{ url_for('edit_post',post_id=post['id']) }}" enctype="multipart/form-data"><label>Title</label><input name="title" maxlength="200" value="{{ post['title'] }}" required><label>Description</label><textarea name="description" maxlength="5000" required>{{ post['description'] }}</textarea>{% if post['image_mime'] %}<strong>Current photo:</strong><br><img src="{{ url_for('post_image',post_id=post['id']) }}" alt="Current photo"><br>{% endif %}<label>Replace Photo (optional)</label><input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp"><button class="save" type="submit">💾 Save Changes</button><a class="cancel-edit" href="#">Cancel</a></form></div></div>{% else %}<p class="muted">No gallery posts yet.</p>{% endfor %}
</section>

<section class="panel" id="news"><h2>📰📢 News & Announcements</h2>
<p>News and announcements are managed together here. You can upload, edit, replace photos, or delete posts.</p>
<form method="POST" action="{{ url_for('add_post', section='news') }}" enctype="multipart/form-data"><label>Title</label><input name="title" maxlength="200" required><label>Description</label><textarea name="description" maxlength="5000" required></textarea><label>Photo (optional)</label><input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp"><button>Publish News / Announcement</button></form>
{% for post in news %}<div class="post">{% if post['image_mime'] %}<img src="{{ url_for('post_image',post_id=post['id']) }}" alt="{{ post['title'] }}">{% endif %}<div><div class="post-type">{% if post['section'] == 'announcement' %}ANNOUNCEMENT{% else %}NEWS{% endif %}</div><h3>{{ post['title'] }}</h3><p class="muted">{{ post['created_at'] }}</p><p>{{ post['description'] }}</p></div><div class="actions"><a class="edit" href="{{ url_for('edit_post', post_id=post['id']) }}">✏️ Edit</a><form method="POST" action="{{ url_for('delete_post',post_id=post['id']) }}" style="display:inline"><button class="delete" type="submit" onclick="return confirm('Are you sure you want to permanently delete this post? This cannot be undone.')">🗑️ Delete</button></form></div></div>{% else %}<p class="muted">No news or announcements yet.</p>{% endfor %}
</section>
</main></body></html>
"""


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


VIEWER_DETAILS_HTML = r"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JHR Detailed Viewers</title><style>body{font-family:Arial;margin:0;background:#f6f1fb;color:#24152f}header{background:linear-gradient(135deg,#26083f,#7628d9);color:white;padding:28px;text-align:center}main{max-width:1400px;margin:25px auto;padding:0 15px}.back{display:inline-block;margin:10px 0 20px;padding:12px 20px;background:#7628d9;color:white;text-decoration:none;border-radius:12px}table{width:100%;border-collapse:collapse;background:white;border-radius:16px;overflow:hidden;box-shadow:0 8px 25px #0001}th,td{padding:12px;border-bottom:1px solid #eee;text-align:center;vertical-align:top}th{background:#eee6f7}small{color:#666}.empty{text-align:center;padding:50px;background:white;border-radius:16px}</style></head><body><header><h1>👁️ Detailed Viewer Information</h1><p>Recent website visits recorded by JHR.</p></header><main><a class="back" href="{{ url_for('staff_dashboard') }}">← Back to Staff Dashboard</a><div style="background:white;border-radius:16px;padding:24px;margin:10px 0 22px;text-align:center;box-shadow:0 8px 25px #0001"><div style="font-size:18px">👁️ Total Page Views</div><div style="font-size:46px;font-weight:800;color:#7628d9">{{ total_views }}</div><small>Storage: {{ storage }}</small></div>{% if viewers %}<div style="overflow-x:auto"><table><tr><th>Date / Time</th><th>IP Address</th><th>Device</th><th>Browser</th><th>Location</th><th>Page</th><th>Referrer</th></tr>{% for v in viewers %}<tr><td>{{ v.get('viewed_at','') }}</td><td>{{ v.get('ip','Unknown') }}</td><td>{{ v.get('device','Unknown') }}</td><td>{{ v.get('browser','Unknown') }}</td><td>{{ v.get('city','Unknown') }}, {{ v.get('region','') }}<br>{{ v.get('country','Unknown') }}</td><td>{{ v.get('path','/') }}</td><td>{{ v.get('referrer','Direct') }}</td></tr>{% endfor %}</table></div>{% else %}<div class="empty"><h2>No viewers recorded yet.</h2><p>Visits will appear here as people visit the website.</p></div>{% endif %}</main></body></html>
"""


if __name__ == "__main__":

    print("=" * 60)
    print("                    JHR")
    print("       EMPOWERMENT THROUGH TECHNOLOGY")
    print("=" * 60)

    print()
    print("Website is starting...")
    print()
    print("Open:")
    print("http://127.0.0.1:5000")
    print()
    print("Press CTRL+C to stop.")
    print()

    threading.Timer(
        1.5,
        open_browser
    ).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
