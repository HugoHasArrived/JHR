from flask import Flask, render_template_string, send_from_directory, abort, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from bson import ObjectId
from bson.errors import InvalidId

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

viewer_count = 0

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
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://josehugorafaeltan_db_user:CG4Gvfq2rOjelCHx@jhrwebsite.xaryu3e.mongodb.net/?retryWrites=true&w=majority"
)

MONGO_DB_NAME = os.environ.get(
    "MONGO_DB_NAME",
    "jhr_database"
)

GALLERY_FOLDER = os.path.join(app.static_folder, "gallery")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
os.makedirs(GALLERY_FOLDER, exist_ok=True)


# =========================================================
# MONGODB CONNECTION
# =========================================================

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    mongo_client.admin.command("ping")
    mongo_db = mongo_client[MONGO_DB_NAME]

    staff_accounts_collection = mongo_db["staff_accounts"]
    class_messages_collection = mongo_db["class_messages"]
    news_collection = mongo_db["news_items"]

    staff_accounts_collection.create_index("username", unique=True)

except PyMongoError as exc:
    raise RuntimeError(
        "Could not connect to MongoDB. Set MONGO_URI to your MongoDB Atlas "
        "connection string or make sure local MongoDB is running."
    ) from exc


def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_mongodb():
    # Default staff login:
    # username = admin
    # password = admin123
    if not staff_accounts_collection.find_one({"username": "admin"}):
        try:
            staff_accounts_collection.insert_one({
                "username": "admin",
                "password": generate_password_hash("admin123"),
                "created_at": now_string()
            })
        except DuplicateKeyError:
            pass


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_staff(doc):
    return {
        "id": str(doc["_id"]),
        "username": doc.get("username", ""),
        "created_at": doc.get("created_at", "")
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
        items.append({
            "id": str(doc["_id"]),
            "kind": doc.get("kind", "Announcement"),
            "title": doc.get("title", ""),
            "content": doc.get("content", ""),
            "created_at": doc.get("created_at", ""),
            "author": author
        })
    return items


def gallery_images():
    images = []
    if os.path.isdir(GALLERY_FOLDER):
        for filename in sorted(os.listdir(GALLERY_FOLDER)):
            if allowed_file(filename):
                images.append(filename)
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
input,textarea{width:100%;padding:13px;border:1px solid #3c4658;border-radius:11px;background:#0f131a;color:#fff;margin:7px 0 12px;font:inherit}
textarea{min-height:130px;resize:vertical}
button{border:0;border-radius:11px;padding:12px 17px;background:linear-gradient(135deg,#7c3aed,#c026d3);color:#fff;cursor:pointer;font-weight:800}
a{color:#b894ff}
.message{border-top:1px solid #303746;padding:16px 0}
.message:first-child{border-top:0}
.meta{color:#aab4c2;font-size:14px}
.notice{padding:12px;border-radius:10px;background:#241d3c;margin-bottom:8px}

.who-are-we-cards{display:flex;justify-content:center;align-items:center}
.who-we-are-box{width:min(950px,100%);margin:0 auto;text-align:center}
.who-we-are-box p{margin:0;text-align:center;font-weight:700;text-indent:2em;line-height:1.9}
.who-we-are-box p + p{margin-top:32px}

</style>
</head>
<body>
<div class="wrap">
<p><a href="{{ url_for('home') }}">← Back to JHR website</a></p>
<h1>👨‍💼 JHR Staff Dashboard</h1>
<p>You are logged in as <strong>{{ staff_username }}</strong>.</p>

{% with notices = get_flashed_messages() %}
{% for notice in notices %}
<div class="notice">{{ notice }}</div>
{% endfor %}
{% endwith %}

<div class="card">
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

<div class="card">
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

<div class="card">
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

<div class="card">
<h2>📰 Add News / Announcement</h2>
<form method="POST" action="{{ url_for('add_news_item') }}">
<label>Type</label>
<select name="kind" required style="width:100%;padding:13px;border:1px solid #3c4658;border-radius:11px;background:#0f131a;color:#fff;margin:7px 0 12px;font:inherit;">
<option value="Announcement">Announcement</option>
<option value="News">News</option>
</select>
<label>Title</label>
<input type="text" name="title" maxlength="160" required placeholder="News or announcement title">
<label>Content</label>
<textarea name="content" maxlength="10000" required placeholder="Write the news or announcement..."></textarea>
<button type="submit">📢 Publish</button>
</form>
</div>

<div class="card">
<h2>🗞️ Published News & Announcements</h2>
{% if news_items %}
    {% for item in news_items %}
    <div class="message">
        <strong>{{ item["kind"] }} — {{ item["title"] }}</strong><br>
        <span class="meta">{{ item["created_at"] }}{% if item["author"] %} · Posted by {{ item["author"] }}{% endif %}</span>
        <p style="white-space:pre-wrap;">{{ item["content"] }}</p>
        <form method="POST" action="{{ url_for('delete_news_item', news_id=item['id']) }}" onsubmit="return confirm('Delete this news or announcement permanently?');">
            <button type="submit" style="background:#b42318;color:#fff;padding:9px 14px;border:0;border-radius:9px;cursor:pointer;font-weight:800;">🗑️ Delete</button>
        </form>
    </div>
    {% endfor %}
{% else %}
    <p>No news or announcements published yet.</p>
{% endif %}
</div>

<div class="card">
<h2>👤 Current Staff Accounts</h2>
{% for staff in staff_accounts %}
<p><strong>{{ staff["username"] }}</strong><br><span class="meta">Created {{ staff["created_at"] }}</span></p>
{% endfor %}
</div>
</div>
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

    display:
        grid;

    grid-template-columns:
        repeat(
            3,
            minmax(0,1fr)
        );

    gap:
        24px;
}


.gallery-card {

    overflow:
        hidden;

    background:
        var(--card);

    border-radius:
        22px;

    box-shadow:
        var(--shadow);

    border:
        1px solid
        var(--border);
}


.gallery-card img {

    display:
        block;

    width:
        100%;

    height:
        300px;

    object-fit:
        cover;

    background:
        var(--purple-soft);

    /*
       Faster image loading.
    */
    content-visibility:
        auto;
}


.gallery-caption {

    padding:
        20px;
}


.gallery-caption h3 {

    color:
        var(--purple);

    margin-bottom:
        6px;
}


.gallery-caption p {

    color:
        var(--muted);
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

    <span>
        JHR
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
    <h3>📸 Import Pictures</h3>
    <p style="color:var(--muted); margin:8px 0 15px;">Choose pictures from your computer and add them to the JHR Gallery.</p>
    <form method="POST" action="{{ url_for('upload_gallery') }}" enctype="multipart/form-data">
        <input type="file" name="images" accept="image/jpeg,image/png,image/webp,image/gif" multiple required>
        <button class="upload-submit" type="submit">⬆️ Import Pictures</button>
    </form>
    <small>Supported: JPG, JPEG, PNG, WEBP, GIF</small>
</div>
{% endif %}

{% for image in uploaded_images %}
<div class="gallery-card">
    <img src="{{ url_for('uploaded_gallery_image', filename=image) }}" alt="JHR uploaded gallery image" loading="lazy" decoding="async">
    <div class="gallery-caption"><h3>📷 JHR Gallery</h3><p>Imported picture</p></div>
</div>
{% endfor %}

<div class="gallery-grid">


<!-- =====================================================
     IMG_0884
===================================================== -->

<div class="gallery-card">


<img
    src="/media/IMG_0884"
    alt="JHR technology activity"
    loading="lazy"
    decoding="async"
    onerror="imageError(this)"
>


<div class="gallery-caption">

<h3
    data-en="It's Building Time!"
    data-fil="💻 Aktibidad sa Teknolohiya ng JHR"
>

    It's Building Time!

</h3>


<p
    data-en="We introduced children to basic robotics concepts through LEGO blocks."
    data-fil="Pag-aaral ng teknolohiya, coding at digital skills."
>

    We introduced children to basic robotics concepts through LEGO blocks.

</p>

</div>

</div>



<!-- =====================================================
     IMG_5798
===================================================== -->

<div class="gallery-card">


<img
    src="/media/IMG_5798"
    alt="JHR community learning activity"
    loading="lazy"
    decoding="async"
    onerror="imageError(this)"
>


<div class="gallery-caption">

<h3
    data-en="Community Time"
    data-fil="🤝 Pagkatuto sa Komunidad"
>

    Community Time

</h3>


<p
    data-en="We introduced children to basic robotics concepts through LEGO SPIKE Prime."
    data-fil="Sama-samang pag-aaral at pagtutulungan sa komunidad."
>

    We introduced children to basic robotics concepts through LEGO SPIKE Prime.

</p>

</div>

</div>



<!-- =====================================================
     IMG_12345
===================================================== -->

<div class="gallery-card">


<img
    src="/media/IMG_12345"
    alt="Ozamiz Elementary School JHR activity"
    loading="lazy"
    decoding="async"
    onerror="imageError(this)"
>


<div class="gallery-caption">

<h3
    data-en="It's Scratch Time!"
    data-fil="It's Scratch Time!"
>

    It's Scratch Time!

</h3>


<p
    data-en="We introduced children to basic coding skills."
    data-fil="Isang espesyal na sandali ng JHR kasama ang paaralan at komunidad."
>

    We introduced children to basic coding skills.

</p>

</div>

</div>


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

            element.textContent =
                currentLanguage === "en"
                    ? english
                    : filipino;

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

</script>


</body>
</html>
"""


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    global viewer_count

    viewer_count += 1

    return render_template_string(
        HTML,
        viewer_count=viewer_count,
        uploaded_images=gallery_images(),
        news_items=news_items()
    )


AUTH_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JHR | {{ title }}</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#2e1065,#7c3aed,#c026d3);padding:20px}.box{width:min(440px,100%);background:white;border-radius:24px;padding:35px;box-shadow:0 20px 60px rgba(0,0,0,.25)}h1{color:#4c1d95;margin-top:0}p{color:#6b5b82}.box input{width:100%;padding:14px;margin:7px 0 15px;border:1px solid #ded0ff;border-radius:12px}.box button{width:100%;padding:14px;border:0;border-radius:12px;background:linear-gradient(135deg,#7c3aed,#c026d3);color:white;font-weight:800;cursor:pointer}.box a{display:block;text-align:center;margin-top:18px;color:#7c3aed;text-decoration:none;font-weight:700}.note{background:#ede9fe;padding:12px;border-radius:12px;margin-bottom:15px;color:#4c1d95;font-weight:700}
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
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        staff = staff_accounts_collection.find_one({"username": username})

        if staff and check_password_hash(staff.get("password", ""), password):
            session.clear()
            session["staff_id"] = str(staff["_id"])
            session["staff_username"] = staff.get("username", username)
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


# =========================================================
# GALLERY UPLOAD
# =========================================================

@app.route("/gallery/upload", methods=["POST"])
@staff_required
def upload_gallery():
    files = request.files.getlist("images")
    added = 0

    for image in files:
        if not image or not image.filename or not allowed_file(image.filename):
            continue

        filename = secure_filename(image.filename)
        if not filename:
            continue

        base, ext = os.path.splitext(filename)
        candidate = filename
        counter = 1

        while os.path.exists(os.path.join(GALLERY_FOLDER, candidate)):
            candidate = f"{base}_{counter}{ext}"
            counter += 1

        image.save(os.path.join(GALLERY_FOLDER, candidate))
        added += 1

    flash(f"{added} picture(s) imported into the gallery.")
    return redirect(url_for("home") + "#gallery")


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

    return render_template_string(
        STAFF_DASHBOARD_HTML,
        messages=messages,
        staff_accounts=staff_accounts,
        news_items=news_items(),
        staff_username=session.get("staff_username")
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

    news_collection.insert_one({
        "kind": kind,
        "title": title,
        "content": content,
        "created_at": now_string(),
        "author_id": str(author_id)
    })

    flash(f"{kind} published successfully.")
    return redirect(url_for("staff_dashboard"))


@app.route("/staff/delete-news/<news_id>", methods=["POST"])
@staff_required
def delete_news_item(news_id):
    try:
        result = news_collection.delete_one({"_id": ObjectId(news_id)})
    except (InvalidId, TypeError):
        result = None

    if result and result.deleted_count:
        flash("News/announcement deleted.")
    else:
        flash("News/announcement not found.")

    return redirect(url_for("staff_dashboard"))


@app.route("/gallery-image/<path:filename>")
def uploaded_gallery_image(filename):
    filename = os.path.basename(filename)
    if not allowed_file(filename):
        abort(404)
    return send_from_directory(GALLERY_FOLDER, filename)


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
