from flask import Flask, render_template_string, send_from_directory, abort
import os

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

viewer_count = 0


# =========================================================
# IMAGE ROUTE
# =========================================================
# This checks several possible extensions automatically.
# Example:
# /media/IMG_0884
# will try:
# IMG_0884.jpg
# IMG_0884.jpeg
# IMG_0884.png
#
# This makes image loading much more reliable.
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

    # Protect against directory traversal.
    image_name = os.path.basename(image_name)

    for extension in IMAGE_EXTENSIONS:

        filename = image_name

        # Don't add another extension if one was already supplied.
        if not os.path.splitext(filename)[1]:
            filename += extension

        filepath = os.path.join(
            app.static_folder,
            filename
        )

        if os.path.isfile(filepath):

            return send_from_directory(
                app.static_folder,
                filename
            )

    abort(404)


# =========================================================
# WEBSITE
# =========================================================

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

<title>
JHR | Empowerment Through Technology
</title>


<style>

/* =========================================================
   RESET
========================================================= */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    scroll-behavior: smooth;
}


/* =========================================================
   COLORS
========================================================= */

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


/* =========================================================
   BODY
========================================================= */

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


/* =========================================================
   DARK MODE
========================================================= */

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
        #ffffff;

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


/* =========================================================
   NAVIGATION
========================================================= */

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

    object-fit:
        contain;

    display:
        block;
}


.nav-links {

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    gap:
        10px;

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


/* =========================================================
   HERO
========================================================= */

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
}


.button.alt {

    background:
        var(--purple-light);

    color:
        white;
}


/* =========================================================
   SECTIONS
========================================================= */

.section {

    max-width:
        1180px;

    margin:
        auto;

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


/* =========================================================
   CARDS
========================================================= */

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


/* =========================================================
   MISSION
========================================================= */

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

    border:
        1px solid
        rgba(255,255,255,.2);

    border-radius:
        22px;

    background:
        rgba(255,255,255,.1);

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


/* =========================================================
   STATS
========================================================= */

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


/* =========================================================
   SERVICES
========================================================= */

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


/* =========================================================
   GALLERY
========================================================= */

.gallery-grid {

    display:
        grid;

    grid-template-columns:
        repeat(
            2,
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

    border:
        1px solid
        var(--border);

    border-radius:
        22px;

    box-shadow:
        var(--shadow);
}


.gallery-card img {

    display:
        block;

    width:
        100%;

    height:
        390px;

    object-fit:
        cover;

    background:
        var(--purple-soft);
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


/* =========================================================
   FOUNDERS
========================================================= */

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


/* =========================================================
   GAMES
========================================================= */

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


/* =========================================================
   CONTACT
========================================================= */

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


/* =========================================================
   JOURNEY
========================================================= */

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


/* =========================================================
   VIEWER COUNTER
========================================================= */

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


/* =========================================================
   FOOTER
========================================================= */

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


/* =========================================================
   TOP BUTTON
========================================================= */

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


/* =========================================================
   MOBILE
========================================================= */

@media(max-width:1000px) {

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


@media(max-width:700px) {

    .nav-links {

        gap:
            7px;
    }

    .nav-links a {

        font-size:
            10px;
    }

    .gallery-grid {

        grid-template-columns:
            1fr;
    }

    .gallery-card img {

        height:
            300px;
    }

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
            350px;
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

</style>

</head>


<body>


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
    data-en="About"
    data-fil="Tungkol"
>
    About
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


<h2
    data-en="EMPOWERMENT THROUGH TECHNOLOGY"
    data-fil="PAGPAPALAKAS SA PAMAMAGITAN NG TEKNOLOHIYA"
>

    EMPOWERMENT THROUGH TECHNOLOGY

</h2>


<p
    data-en="Turning technology, creativity and learning into opportunities for people and communities."
    data-fil="Ginagamit ang teknolohiya, pagkamalikhain at pagkatuto upang lumikha ng mga oportunidad para sa mga tao at komunidad."
>

    Turning technology, creativity and learning
    into opportunities for people and communities.

</p>


<a
    class="button"
    href="#about"
    data-en="✨ Explore JHR"
    data-fil="✨ Tuklasin ang JHR"
>

    ✨ Explore JHR

</a>


<a
    class="button alt"
    href="#services"
    data-en="💻 Free Coding Classes"
    data-fil="💻 Libreng Coding Classes"
>

    💻 Free Coding Classes

</a>


</div>

</section>



<!-- =====================================================
     ABOUT
===================================================== -->

<section
    class="section"
    id="about"
>

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

<h3
    data-en="💻 Technology"
    data-fil="💻 Teknolohiya"
>
    💻 Technology
</h3>

<p
    data-en="We explore technology as a tool for creativity, learning and opportunity."
    data-fil="Sinasaliksik namin ang teknolohiya bilang kasangkapan sa pagkamalikhain, pagkatuto at oportunidad."
>

    We explore technology as a tool for
    creativity, learning and opportunity.

</p>

</div>


<div class="card">

<h3
    data-en="📚 Education"
    data-fil="📚 Edukasyon"
>
    📚 Education
</h3>

<p
    data-en="We encourage people to learn useful digital and technology skills."
    data-fil="Hinihikayat namin ang mga tao na matuto ng kapaki-pakinabang na digital at teknolohikal na kasanayan."
>

    We encourage people to learn useful
    digital and technology skills.

</p>

</div>


<div class="card">

<h3
    data-en="🌱 Community"
    data-fil="🌱 Komunidad"
>
    🌱 Community
</h3>

<p
    data-en="Technology can help communities connect, learn and grow."
    data-fil="Makakatulong ang teknolohiya sa mga komunidad na kumonekta, matuto at umunlad."
>

    Technology can help communities connect,
    learn and grow.

</p>

</div>


<div class="card">

<h3
    data-en="💡 Innovation"
    data-fil="💡 Inobasyon"
>
    💡 Innovation
</h3>

<p
    data-en="Every big project starts with an idea and the courage to try."
    data-fil="Ang bawat malaking proyekto ay nagsisimula sa isang ideya at lakas ng loob na sumubok."
>

    Every big project starts with an idea
    and the courage to try.

</p>

</div>


</div>

</section>



<!-- =====================================================
     MISSION
===================================================== -->

<section
    class="color-section"
    id="mission"
>

<h2
    class="title"
    data-en="Our Mission"
    data-fil="Aming Misyon"
>

    Our Mission

</h2>


<p
    class="subtitle"
    data-en="Empowerment through technology, knowledge and creativity."
    data-fil="Pagpapalakas sa pamamagitan ng teknolohiya, kaalaman at pagkamalikhain."
>

    Empowerment through technology,
    knowledge and creativity.

</p>


<div class="mission">


<div class="mission-card">

<div class="mission-icon">
    💻
</div>

<h3
    data-en="Technology"
    data-fil="Teknolohiya"
>
    Technology
</h3>

<p
    data-en="Promote creative and responsible technology use."
    data-fil="Itaguyod ang malikhain at responsableng paggamit ng teknolohiya."
>

    Promote creative and responsible
    technology use.

</p>

</div>


<div class="mission-card">

<div class="mission-icon">
    🎓
</div>

<h3
    data-en="Education"
    data-fil="Edukasyon"
>
    Education
</h3>

<p
    data-en="Encourage people to learn digital and technology skills."
    data-fil="Hikayatin ang mga tao na matuto ng digital at teknolohikal na kasanayan."
>

    Encourage people to learn digital
    and technology skills.

</p>

</div>


<div class="mission-card">

<div class="mission-icon">
    🌍
</div>

<h3
    data-en="Community"
    data-fil="Komunidad"
>
    Community
</h3>

<p
    data-en="Explore ways technology can create positive community impact."
    data-fil="Tuklasin kung paano makalilikha ang teknolohiya ng positibong epekto sa komunidad."
>

    Explore ways technology can create
    positive community impact.

</p>

</div>


<div class="mission-card">

<div class="mission-icon">
    🚀
</div>

<h3
    data-en="Innovation"
    data-fil="Inobasyon"
>
    Innovation
</h3>

<p
    data-en="Turn creative ideas into useful projects and experiences."
    data-fil="Gawing kapaki-pakinabang na proyekto at karanasan ang mga malikhaing ideya."
>

    Turn creative ideas into useful
    projects and experiences.

</p>

</div>


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

<section
    class="section"
    id="projects"
>

<h2
    class="title"
    data-en="JHR Projects 🚀"
    data-fil="Mga Proyekto ng JHR 🚀"
>

    JHR Projects 🚀

</h2>


<p
    class="subtitle"
    data-en="Technology, education and community projects designed around learning and positive impact."
    data-fil="Mga proyekto sa teknolohiya, edukasyon at komunidad na nakatuon sa pagkatuto at positibong epekto."
>

    Technology, education and community projects
    designed around learning and positive impact.

</p>


<div class="cards">


<div class="card">

<h3
    data-en="💻 Technology Projects"
    data-fil="💻 Mga Proyektong Teknolohiya"
>
    💻 Technology Projects
</h3>

<p
    data-en="Websites, digital tools, programming, creative technology and experiments."
    data-fil="Mga website, digital tool, programming, malikhaing teknolohiya at mga eksperimento."
>

    Websites, digital tools, programming,
    creative technology and experiments.

</p>

</div>


<div class="card">

<h3
    data-en="🏫 Education"
    data-fil="🏫 Edukasyon"
>
    🏫 Education
</h3>

<p
    data-en="Technology-related learning activities and educational experiences."
    data-fil="Mga aktibidad sa pagkatuto tungkol sa teknolohiya at mga karanasang pang-edukasyon."
>

    Technology-related learning activities
    and educational experiences.

</p>

</div>


<div class="card">

<h3
    data-en="🌱 Community"
    data-fil="🌱 Komunidad"
>
    🌱 Community
</h3>

<p
    data-en="Exploring how technology can support communities and agricultural areas."
    data-fil="Tinutuklas kung paano makatutulong ang teknolohiya sa mga komunidad at lugar na pang-agrikultura."
>

    Exploring how technology can support
    communities and agricultural areas.

</p>

</div>


<div class="card">

<h3
    data-en="🚀 Future Projects"
    data-fil="🚀 Mga Proyektong Hinaharap"
>
    🚀 Future Projects
</h3>

<p
    data-en="More JHR projects will be added as new initiatives are completed."
    data-fil="Mas marami pang proyekto ng JHR ang idaragdag habang natatapos ang mga bagong inisyatiba."
>

    More JHR projects will be added as
    new initiatives are completed.

</p>

</div>


</div>

</section>



<!-- =====================================================
     SERVICES
===================================================== -->

<section
    class="section"
    id="services"
>

<h2
    class="title"
    data-en="JHR Services 💻🎓"
    data-fil="Mga Serbisyo ng JHR 💻🎓"
>

    JHR Services 💻🎓

</h2>


<p
    class="subtitle"
    data-en="We provide learning opportunities that help people discover technology and build useful skills."
    data-fil="Nagbibigay kami ng mga oportunidad sa pagkatuto upang matuklasan ng mga tao ang teknolohiya at makabuo ng kapaki-pakinabang na kasanayan."
>

    We provide learning opportunities that help
    people discover technology and build useful skills.

</p>


<div class="services">


<div class="service-card">

<div class="service-icon">
    💻
</div>

<h3
    data-en="Free Coding Classes"
    data-fil="Libreng Coding Classes"
>
    Free Coding Classes
</h3>

<p
    data-en="We provide free coding classes for beginners and learners who want to start programming."
    data-fil="Nagbibigay kami ng libreng coding classes para sa mga baguhan at nais magsimulang mag-program."
>

    We provide free coding classes for beginners
    and learners who want to start programming.

</p>

<span
    class="free"
    data-en="FREE"
    data-fil="LIBRE"
>
    FREE
</span>

</div>


<div class="service-card">

<div class="service-icon">
    🌐
</div>

<h3
    data-en="Web Development"
    data-fil="Web Development"
>
    Web Development
</h3>

<p
    data-en="Learn the basics of building websites using HTML, CSS and JavaScript."
    data-fil="Matutunan ang mga pangunahing kaalaman sa paggawa ng website gamit ang HTML, CSS at JavaScript."
>

    Learn the basics of building websites
    using HTML, CSS and JavaScript.

</p>

</div>


<div class="service-card">

<div class="service-icon">
    🚀
</div>

<h3
    data-en="Learn by Building"
    data-fil="Matuto sa Pamamagitan ng Pagbuo"
>
    Learn by Building
</h3>

<p
    data-en="Practice technology by creating simple projects and turning ideas into working experiences."
    data-fil="Magsanay sa teknolohiya sa pamamagitan ng paggawa ng simpleng proyekto at gawing aktuwal na karanasan ang mga ideya."
>

    Practice technology by creating simple
    projects and turning ideas into working experiences.

</p>

</div>


<div class="service-card">

<div class="service-icon">
    🌱
</div>

<h3
    data-en="Technology Skills"
    data-fil="Mga Kasanayang Teknolohiya"
>
    Technology Skills
</h3>

<p
    data-en="Develop practical digital skills that can support school, projects and future opportunities."
    data-fil="Bumuo ng praktikal na digital skills para makatulong sa paaralan, proyekto at mga oportunidad sa hinaharap."
>

    Develop practical digital skills that can
    support school, projects and future opportunities.

</p>

</div>


</div>

</section>



<!-- =====================================================
     GALLERY
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
    data-en="Moments of learning, teamwork, technology and community."
    data-fil="Mga sandali ng pagkatuto, pagtutulungan, teknolohiya at komunidad."
>

    Moments of learning, teamwork,
    technology and community.

</p>


<div class="gallery-grid">


<!-- =====================================================
     IMG_0884
===================================================== -->

<div class="gallery-card">

<img
    src="/media/IMG_0884"
    alt="JHR technology and community activity"
    loading="lazy"
    decoding="async"
>


<div class="gallery-caption">

<h3
    data-en="💻 JHR Technology Activity"
    data-fil="💻 Aktibidad sa Teknolohiya ng JHR"
>

    💻 JHR Technology Activity

</h3>


<p
    data-en="Learning, coding and technology together."
    data-fil="Sama-samang pag-aaral, coding at teknolohiya."
>

    Learning, coding and technology together.

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
>


<div class="gallery-caption">

<h3
    data-en="🤝 Community Learning"
    data-fil="🤝 Pagkatuto sa Komunidad"
>

    🤝 Community Learning

</h3>


<p
    data-en="A JHR community learning and technology activity."
    data-fil="Isang aktibidad ng JHR sa komunidad tungkol sa pagkatuto at teknolohiya."
>

    A JHR community learning and technology activity.

</p>

</div>

</div>



<!-- =====================================================
     OZAMIZ ELEMENTARY SCHOOL
===================================================== -->

<div class="gallery-card">

<img
    src="/media/Untitled11_20260822092717"
    alt="Ozamiz Elementary School JHR activity"
    loading="lazy"
    decoding="async"
>


<div class="gallery-caption">

<h3
    data-en="🏫 Ozamiz Elementary School"
    data-fil="🏫 Ozamiz Elementary School"
>

    🏫 Ozamiz Elementary School

</h3>


<p
    data-en="A special JHR school and community moment."
    data-fil="Isang espesyal na sandali ng JHR kasama ang paaralan at komunidad."
>

    A special JHR school and community moment.

</p>

</div>

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
    data-en="The founders behind JHR and its mission of empowerment through technology."
    data-fil="Ang mga tagapagtatag sa likod ng JHR at ng misyon nitong pagpapalakas sa pamamagitan ng teknolohiya."
>

    The founders behind JHR and its mission
    of empowerment through technology.

</p>


<div class="owners">


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
    data-en="Helps guide JHR's vision, projects and technology-focused activities."
    data-fil="Tumutulong sa paggabay sa pananaw, mga proyekto at mga aktibidad ng JHR na nakatuon sa teknolohiya."
>

    Helps guide JHR's vision,
    projects and technology-focused activities.

</p>

</div>

</div>



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
    data-en="Supports JHR's creativity, projects and community-focused activities."
    data-fil="Sinusuportahan ang pagkamalikhain, mga proyekto at mga aktibidad ng JHR para sa komunidad."
>

    Supports JHR's creativity,
    projects and community-focused activities.

</p>

</div>

</div>


</div>

</section>



<!-- =====================================================
     GAMES
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

    12 games to learn, think and have fun!

</p>


<div class="game-grid">


<!-- GAME 1 -->

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

<div
    id="g1"
    class="result"
>
</div>

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

<button onclick="answer('g2',true)">
Central Processing Unit
</button>

<button onclick="answer('g2',false)">
Computer Power Unit
</button>

<div
    id="g2"
    class="result"
>
</div>

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
    data-fil="Dapat mo bang ibahagi ang password mo?"
>

    Should you share your password?

</p>

<button onclick="answer('g3',false)">
Yes
</button>

<button onclick="answer('g3',true)">
No
</button>

<div
    id="g3"
    class="result"
>
</div>

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

<button onclick="answer('g4',true)">
Cooperation
</button>

<button onclick="answer('g4',false)">
Giving up
</button>

<div
    id="g4"
    class="result"
>
</div>

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

<button onclick="answer('g5',true)">
Web pages
</button>

<button onclick="answer('g5',false)">
Batteries
</button>

<div
    id="g5"
    class="result"
>
</div>

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

<button onclick="answer('g6',true)">
0 and 1
</button>

<button onclick="answer('g6',false)">
1 and 9
</button>

<div
    id="g6"
    class="result"
>
</div>

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

<div
    id="g7"
    class="result"
>
</div>

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

<div
    id="g8"
    class="result"
>
</div>

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

<div
    id="g9"
    class="result"
>
</div>

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

<button onclick="answer('g10',true)">
CODING
</button>

<button onclick="answer('g10',false)">
CLOUD
</button>

<button onclick="answer('g10',false)">
GARDEN
</button>

<div
    id="g10"
    class="result"
>
</div>

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

<button onclick="answer('g11',true)">
Plan and test it
</button>

<button onclick="answer('g11',false)">
Ignore it
</button>

<button onclick="answer('g11',false)">
Give up
</button>

<div
    id="g11"
    class="result"
>
</div>

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

<button onclick="answer('g12',true)">
Learning
</button>

<button onclick="answer('g12',false)">
Cyberbullying
</button>

<button onclick="answer('g12',false)">
Sharing passwords
</button>

<div
    id="g12"
    class="result"
>
</div>

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
    data-en="Join JHR"
    data-fil="Sumali sa JHR"
>

    Join JHR

</h2>


<p
    data-en="We believe technology can help people learn, create and empower others."
    data-fil="Naniniwala kami na makatutulong ang teknolohiya sa mga tao na matuto, lumikha at magbigay-lakas sa iba."
>

    We believe technology can help people
    learn, create and empower others.

</p>


</div>


<!-- =====================================================
     JOURNEY
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
     THIS IS BELOW THE JOURNEY TEXT
===================================================== -->

<div class="viewer-counter">

    👀

    <strong>
        {{ viewer_count }}
    </strong>

    <span id="visitorWord">
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


<p>
    © 2026 JHR Team
</p>

</footer>



<!-- =====================================================
     JAVASCRIPT
===================================================== -->

<script>

/* =========================================================
   LANGUAGE
========================================================= */

let currentLanguage =
    localStorage.getItem(
        "jhrLanguage"
    ) || "en";


function applyLanguage() {

    document
        .querySelectorAll("[data-en]")
        .forEach(function(element) {

            if (
                currentLanguage === "en"
            ) {

                element.textContent =
                    element.getAttribute(
                        "data-en"
                    );

            } else {

                element.textContent =
                    element.getAttribute(
                        "data-fil"
                    );

            }

        });


    document.getElementById(
        "langBtn"
    ).textContent =
        currentLanguage === "en"
            ? "🇵🇭 FIL"
            : "🇬🇧 ENG";


    document.getElementById(
        "visitorWord"
    ).textContent =
        currentLanguage === "en"
            ? "Visitors"
            : "Mga Bisita";

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


/* =========================================================
   LIGHT / DARK MODE
========================================================= */

function applyTheme() {

    const savedTheme =
        localStorage.getItem(
            "jhrTheme"
        );


    if (
        savedTheme === "dark"
    ) {

        document.body.classList.add(
            "dark"
        );

        document.getElementById(
            "themeBtn"
        ).textContent =
            "☀️";

    } else {

        document.body.classList.remove(
            "dark"
        );

        document.getElementById(
            "themeBtn"
        ).textContent =
            "🌙";

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


/* =========================================================
   GAME ANSWERS
========================================================= */

function answer(id, correct) {

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


/* =========================================================
   VIEWER COUNTER
========================================================= */

const visitorKey =
    "jhr_local_visitors";


let localVisitors =
    Number(
        localStorage.getItem(
            visitorKey
        )
    ) || 0;


if (
    !sessionStorage.getItem(
        "jhr_counted_this_session"
    )
) {

    localVisitors++;

    localStorage.setItem(
        visitorKey,
        localVisitors
    );

    sessionStorage.setItem(
        "jhr_counted_this_session",
        "1"
    );

}


/* =========================================================
   TOP BUTTON
========================================================= */

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


/* =========================================================
   INITIALIZE
========================================================= */

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
        viewer_count=viewer_count
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return "JHR is running!", 200


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

        "Untitled11_20260822092717.png",

    ]

    output = [
        "<h1>JHR Photo Check</h1>"
    ]


    for filename in files:

        path = os.path.join(
            app.static_folder,
            filename
        )


        if os.path.isfile(path):

            output.append(
                f"✅ {filename} — FOUND"
            )

        else:

            output.append(
                f"❌ {filename} — MISSING"
            )


    return "<br>".join(output)


# =========================================================
# START
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
