from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)


HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>JHR | Empowerment Through Technology</title>

<style>

/* =========================
   RESET
========================= */

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    scroll-behavior: smooth;
}


/* =========================
   COLORS
========================= */

:root {
    --purple: #6d28d9;
    --purple-dark: #4c1d95;
    --purple-light: #a855f7;
    --violet: #8b5cf6;
    --pink: #ec4899;
    --yellow: #fbbf24;

    --background: #f7f2ff;
    --card: #ffffff;
    --text: #24103d;
    --muted: #6b5b78;

    --shadow: rgba(76, 29, 149, 0.15);
}


body.dark {
    --background: #12091f;
    --card: #211130;
    --text: #ffffff;
    --muted: #d6c8e5;

    --shadow: rgba(0, 0, 0, 0.35);
}


body {
    font-family: Arial, Helvetica, sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.7;
    overflow-x: hidden;
    transition: background 0.3s, color 0.3s;
}


/* =========================
   NAVIGATION
========================= */

nav {
    position: sticky;
    top: 0;
    z-index: 9999;

    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 20px;

    padding: 12px 25px;

    background: rgba(255, 255, 255, 0.96);

    backdrop-filter: blur(15px);

    box-shadow:
        0 5px 25px var(--shadow);

    transition: 0.3s;
}


body.dark nav {
    background: rgba(25, 10, 40, 0.96);
}


.logo {
    display: flex;
    align-items: center;
    gap: 10px;

    font-size: 26px;
    font-weight: 1000;
    letter-spacing: 2px;

    color: var(--purple);
}


.logo img {
    width: 48px;
    height: 48px;

    object-fit: contain;
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

    transition: 0.2s;
}


.nav-links a:hover {
    color: var(--purple-light);
}


.nav-button,
.language-button {
    border: none;

    padding: 9px 14px;

    border-radius: 25px;

    cursor: pointer;

    background:
        linear-gradient(
            135deg,
            var(--purple),
            var(--purple-light)
        );

    color: white;

    font-weight: bold;

    transition: 0.2s;
}


.nav-button:hover,
.language-button:hover {
    transform: translateY(-2px);
}


/* =========================
   HERO
========================= */

.hero {
    min-height: 700px;

    display: flex;
    align-items: center;
    justify-content: center;

    text-align: center;

    position: relative;

    overflow: hidden;

    color: white;

    background:
        radial-gradient(
            circle at 15% 20%,
            rgba(168, 85, 247, 0.45),
            transparent 28%
        ),
        radial-gradient(
            circle at 85% 25%,
            rgba(236, 72, 153, 0.35),
            transparent 25%
        ),
        radial-gradient(
            circle at 50% 90%,
            rgba(139, 92, 246, 0.35),
            transparent 35%
        ),
        linear-gradient(
            135deg,
            #24063d,
            #5b21b6,
            #3b0764
        );
}


.hero-content {
    position: relative;

    z-index: 2;

    max-width: 1000px;

    padding: 40px 25px;
}


.badge {
    display: inline-block;

    padding: 10px 20px;

    border-radius: 30px;

    border: 1px solid rgba(255, 255, 255, 0.4);

    background: rgba(255, 255, 255, 0.12);

    margin-bottom: 20px;

    font-weight: bold;
}


.hero h1 {
    font-size: clamp(70px, 13vw, 150px);

    line-height: 0.9;

    font-weight: 1000;

    letter-spacing: 8px;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #d8b4fe,
            #f0abfc,
            #ffffff
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
    font-size: clamp(19px, 4vw, 36px);

    color: #fde68a;

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
            var(--purple-light),
            var(--pink)
        );

    color: white;

    text-decoration: none;

    font-weight: 900;

    transition: 0.25s;
}


.button:hover {
    transform: translateY(-5px) scale(1.04);
}


/* =========================
   VIEWER COUNTER
========================= */

.viewer-counter {
    margin: 22px auto 0;

    display: inline-flex;

    align-items: center;

    gap: 10px;

    padding: 10px 20px;

    border-radius: 30px;

    background: rgba(255, 255, 255, 0.16);

    border: 1px solid rgba(255, 255, 255, 0.35);

    font-weight: bold;

    color: white;
}


/* =========================
   HERO BLOBS
========================= */

.blob {
    position: absolute;

    border-radius: 50%;

    filter: blur(8px);

    opacity: 0.3;

    animation: blobMove 10s infinite alternate ease-in-out;
}


.blob.one {
    width: 250px;
    height: 250px;

    background: var(--purple-light);

    top: 10%;
    left: 4%;
}


.blob.two {
    width: 320px;
    height: 320px;

    background: var(--pink);

    top: 20%;
    right: 5%;
}


.blob.three {
    width: 220px;
    height: 220px;

    background: var(--violet);

    bottom: 4%;
    left: 35%;
}


@keyframes blobMove {

    0% {
        transform: translate(0, 0) scale(1);
    }

    50% {
        transform: translate(60px, -40px) scale(1.15);
    }

    100% {
        transform: translate(-40px, 50px) scale(0.9);
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


.title {
    text-align: center;

    font-size: clamp(32px, 5vw, 48px);

    margin-bottom: 15px;

    background:
        linear-gradient(
            90deg,
            var(--purple),
            var(--purple-light),
            var(--pink)
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
            minmax(240px, 1fr)
        );

    gap: 25px;
}


.card {
    background: var(--card);

    padding: 32px;

    border-radius: 22px;

    box-shadow:
        0 10px 30px var(--shadow);

    border-top:
        5px solid var(--purple);

    transition: 0.3s;
}


.card:hover {
    transform: translateY(-10px);

    box-shadow:
        0 20px 45px var(--shadow);
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
            #2e1065,
            #6d28d9,
            #7e22ce
        );
}


.mission {
    max-width: 1200px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(220px, 1fr)
        );

    gap: 25px;
}


.mission-card {
    padding: 35px;

    text-align: center;

    border-radius: 25px;

    background:
        rgba(255, 255, 255, 0.1);

    border:
        1px solid rgba(255, 255, 255, 0.2);

    backdrop-filter: blur(10px);

    transition: 0.3s;
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
            minmax(180px, 1fr)
        );

    gap: 20px;
}


.stat {
    text-align: center;

    padding: 25px;

    background: var(--card);

    border-radius: 20px;

    box-shadow:
        0 8px 25px var(--shadow);
}


.stat-number {
    font-size: 45px;

    font-weight: 1000;

    color: var(--purple);
}


/* =========================
   FOUNDERS
========================= */

.owners {
    max-width: 1100px;

    margin: 40px auto 0;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(300px, 1fr)
        );

    gap: 30px;
}


.owner-card {
    background: var(--card);

    border-radius: 25px;

    overflow: hidden;

    box-shadow:
        0 12px 35px var(--shadow);

    border-top:
        5px solid var(--purple-light);

    transition: 0.3s;
}


.owner-card:hover {
    transform: translateY(-8px);
}


.owner-photo {
    width: 100%;

    height: 400px;

    object-fit: cover;

    display: block;

    background: #ddd;
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
   GALLERY
========================= */

.gallery-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(300px, 1fr)
        );

    gap: 30px;
}


.gallery-card {
    background: var(--card);

    border-radius: 25px;

    overflow: hidden;

    box-shadow:
        0 12px 35px var(--shadow);

    transition: 0.3s;
}


.gallery-card:hover {
    transform: translateY(-8px);
}


.gallery-card img {
    width: 100%;

    height: 330px;

    object-fit: cover;

    display: block;

    background: #ddd;
}


.gallery-caption {
    padding: 22px;
}


.gallery-caption h3 {
    color: var(--purple);

    margin-bottom: 8px;
}


/* =========================
   GAMES
========================= */

.games {
    padding: 90px 25px;

    background:
        linear-gradient(
            135deg,
            #ede9fe,
            #f5f3ff,
            #fae8ff
        );
}


body.dark .games {
    background:
        linear-gradient(
            135deg,
            #1e1030,
            #160c25,
            #281036
        );
}


.game-grid {
    max-width: 1200px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(280px, 1fr)
        );

    gap: 25px;
}


.game {
    background: var(--card);

    padding: 30px;

    text-align: center;

    border-radius: 25px;

    box-shadow:
        0 10px 30px var(--shadow);
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
            var(--purple-light)
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
        0 10px 35px var(--shadow);
}


.contact h2 {
    color: var(--purple);

    font-size: 35px;
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
            #1e0935,
            #3b0764,
            #581c87
        );
}


.footer-logo {
    font-size: 35px;

    font-weight: 1000;

    color: #e9d5ff;
}


/* =========================
   BACK TO TOP
========================= */

.top {
    position: fixed;

    bottom: 25px;
    right: 25px;

    width: 48px;
    height: 48px;

    border: none;

    border-radius: 50%;

    background: var(--purple);

    color: white;

    font-size: 20px;

    cursor: pointer;

    display: none;

    z-index: 999;
}


/* =========================
   MOBILE
========================= */

@media (max-width: 850px) {

    nav {
        flex-direction: column;

        padding: 15px;
    }

    .nav-links {
        gap: 8px;
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
        height: 330px;
    }

}

</style>

</head>


<body>


<!-- =========================
     NAVIGATION
========================= -->

<nav>

    <div class="logo">

        <img
            src="{{ url_for('static', filename='logo.png') }}"
            alt="JHR Logo"
            onerror="this.style.display='none'"
        >

        <span>JHR</span>

    </div>


    <div class="nav-links">

        <a href="#home" data-en="Home" data-fil="Home">Home</a>

        <a href="#about" data-en="About" data-fil="Tungkol">About</a>

        <a href="#mission" data-en="Mission" data-fil="Misyon">Mission</a>

        <a href="#projects" data-en="Projects" data-fil="Mga Proyekto">Projects</a>

        <a href="#gallery" data-en="Gallery" data-fil="Gallery">Gallery</a>

        <a href="#services" data-en="Services" data-fil="Serbisyo">Services</a>

        <a href="#founders" data-en="Founders" data-fil="Mga Tagapagtatag">Founders</a>

        <a href="#games" data-en="Games" data-fil="Mga Laro">Games</a>

        <a href="#contact" data-en="Contact" data-fil="Makipag-ugnayan">Contact</a>


        <!-- LANGUAGE BUTTON -->

        <button
            class="language-button"
            onclick="toggleLanguage()"
            id="languageButton"
        >
            🇵🇭 FIL
        </button>


        <!-- LIGHT / DARK MODE BUTTON -->

        <button
            class="nav-button"
            onclick="toggleDarkMode()"
            id="themeButton"
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
            data-en="EMPOWERMENT THROUGH TECHNOLOGY"
            data-fil="PAGPAPALAKAS SA PAMAMAGITAN NG TEKNOLOHIYA"
        >
            EMPOWERMENT THROUGH TECHNOLOGY
        </div>


        <h1>JHR</h1>


        <h2
            data-en="TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY"
            data-fil="TEKNOLOHIYA • EDUKASYON • INOBASYON • KOMUNIDAD"
        >
            TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY
        </h2>


        <p
            data-en="Join the JHR Journey 🚀"
            data-fil="Samahan ang JHR Journey 🚀"
        >
            Join the JHR Journey 🚀
        </p>


        <p
            data-en="Technology • Education • Innovation • Community"
            data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad"
        >
            Technology • Education • Innovation • Community
        </p>


        <p
            data-en="Learn. Create. Share. Empower."
            data-fil="Matuto. Lumikha. Magbahagi. Magbigay-kakayahan."
        >
            Learn. Create. Share. Empower.
        </p>


        <!-- VIEWER COUNTER EXACTLY BELOW HERO TEXT -->

        <div class="viewer-counter">

            👁️

            <span
                id="viewerCount"
            >
                1
            </span>

            <span
                data-en="Visitors"
                data-fil="Mga Bisita"
            >
                Visitors
            </span>

        </div>


        <a
            href="#about"
            class="button"
            data-en="Discover JHR"
            data-fil="Tuklasin ang JHR"
        >
            Discover JHR
        </a>


        <a
            href="#services"
            class="button"
            data-en="Free Coding Classes"
            data-fil="Libreng Coding Classes"
        >
            Free Coding Classes
        </a>

    </div>

</section>


<!-- =========================
     ABOUT
========================= -->

<section class="section" id="about">

    <h2
        class="title"
        data-en="About JHR"
        data-fil="Tungkol sa JHR"
    >
        About JHR
    </h2>


    <p
        class="subtitle"
        data-en="JHR is focused on technology, education, innovation and community. We believe that learning and creativity can help people discover new opportunities and build a better future."
        data-fil="Ang JHR ay nakatuon sa teknolohiya, edukasyon, inobasyon at komunidad. Naniniwala kami na ang pagkatuto at pagkamalikhain ay makatutulong sa mga tao na makatuklas ng mga bagong oportunidad at makabuo ng mas magandang kinabukasan."
    >
        JHR is focused on technology, education, innovation and community. We believe that learning and creativity can help people discover new opportunities and build a better future.
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
                data-en="Exploring programming, websites, digital tools and creative technology."
                data-fil="Paggalugad sa programming, websites, digital tools at malikhaing teknolohiya."
            >
                Exploring programming, websites, digital tools and creative technology.
            </p>

        </div>


        <div class="card">

            <h3
                data-en="🎓 Education"
                data-fil="🎓 Edukasyon"
            >
                🎓 Education
            </h3>

            <p
                data-en="Helping people discover opportunities to learn useful technology skills."
                data-fil="Pagtulong sa mga tao na makatuklas ng mga oportunidad upang matuto ng kapaki-pakinabang na technology skills."
            >
                Helping people discover opportunities to learn useful technology skills.
            </p>

        </div>


        <div class="card">

            <h3
                data-en="🚀 Innovation"
                data-fil="🚀 Inobasyon"
            >
                🚀 Innovation
            </h3>

            <p
                data-en="Turning creative ideas into projects, experiences and useful solutions."
                data-fil="Pagbabago ng malikhaing ideya tungo sa mga proyekto, karanasan at kapaki-pakinabang na solusyon."
            >
                Turning creative ideas into projects, experiences and useful solutions.
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
        data-en="Our Mission"
        data-fil="Ang Aming Misyon"
    >
        Our Mission
    </h2>


    <p
        class="subtitle"
        style="color:#f3e8ff"
        data-en="Empowerment through technology, knowledge, creativity and community."
        data-fil="Pagpapalakas sa pamamagitan ng teknolohiya, kaalaman, pagkamalikhain at komunidad."
    >
        Empowerment through technology, knowledge, creativity and community.
    </p>


    <div class="mission">

        <div class="mission-card">

            <div class="mission-icon">💻</div>

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
                Promote creative and responsible technology use.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">🎓</div>

            <h3
                data-en="Education"
                data-fil="Edukasyon"
            >
                Education
            </h3>

            <p
                data-en="Encourage people to learn digital and technology skills."
                data-fil="Hikayatin ang mga tao na matuto ng digital at technology skills."
            >
                Encourage people to learn digital and technology skills.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">🌍</div>

            <h3
                data-en="Community"
                data-fil="Komunidad"
            >
                Community
            </h3>

            <p
                data-en="Explore ways technology can create positive community impact."
                data-fil="Maghanap ng mga paraan kung paano makapagbibigay ng positibong epekto ang teknolohiya sa komunidad."
            >
                Explore ways technology can create positive community impact.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">🚀</div>

            <h3
                data-en="Innovation"
                data-fil="Inobasyon"
            >
                Innovation
            </h3>

            <p
                data-en="Turn creative ideas into useful projects and experiences."
                data-fil="Gawing kapaki-pakinabang na mga proyekto at karanasan ang malikhaing mga ideya."
            >
                Turn creative ideas into useful projects and experiences.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     JHR IN NUMBERS
========================= -->

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
            <div class="stat-number">100+</div>
            <p data-en="Ideas" data-fil="Mga Ideya">Ideas</p>
        </div>

        <div class="stat">
            <div class="stat-number">25+</div>
            <p data-en="Activities" data-fil="Mga Aktibidad">Activities</p>
        </div>

        <div class="stat">
            <div class="stat-number">10+</div>
            <p data-en="Projects" data-fil="Mga Proyekto">Projects</p>
        </div>

        <div class="stat">
            <div class="stat-number">1</div>
            <p data-en="Big Mission" data-fil="Malaking Misyon">Big Mission</p>
        </div>

    </div>

</section>


<!-- =========================
     PROJECTS
========================= -->

<section class="section" id="projects">

    <h2
        class="title"
        data-en="JHR Projects 🚀"
        data-fil="Mga Proyekto ng JHR 🚀"
    >
        JHR Projects 🚀
    </h2>


    <p
        class="subtitle"
        data-en="Our project showcase can grow as new JHR activities and initiatives are completed."
        data-fil="Patuloy na lalago ang aming project showcase habang nadaragdagan ang mga aktibidad at proyekto ng JHR."
    >
        Our project showcase can grow as new JHR activities and initiatives are completed.
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
                data-fil="Mga website, digital tools, programming, malikhaing teknolohiya at mga eksperimento."
            >
                Websites, digital tools, programming, creative technology and experiments.
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
                data-fil="Mga aktibidad sa pagkatuto at educational experiences na may kaugnayan sa teknolohiya."
            >
                Technology-related learning activities and educational experiences.
            </p>

        </div>


        <div class="card">

            <h3
                data-en="🌾 Community"
                data-fil="🌾 Komunidad"
            >
                🌾 Community
            </h3>

            <p
                data-en="Exploring how technology can support communities and create useful opportunities."
                data-fil="Pagsasaliksik kung paano makatutulong ang teknolohiya sa mga komunidad at makalilikha ng kapaki-pakinabang na oportunidad."
            >
                Exploring how technology can support communities and create useful opportunities.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     GALLERY
     ONLY THE TWO CORRECT PHOTOS
========================= -->

<section class="section" id="gallery">

    <h2
        class="title"
        data-en="JHR Gallery 📸"
        data-fil="JHR Gallery 📸"
    >
        JHR Gallery 📸
    </h2>


    <p
        class="subtitle"
        data-en="Real moments of learning, teamwork, coding and community."
        data-fil="Mga tunay na sandali ng pagkatuto, pagtutulungan, coding at komunidad."
    >
        Real moments of learning, teamwork, coding and community.
    </p>


    <div class="gallery-grid">


        <!-- CORRECT PHOTO 1:
             OZAMIZ ELEMENTARY SCHOOL GROUP PHOTO -->

        <div class="gallery-card">

            <img
                src="{{ url_for('serve_static', filename='gallery_ozamiz.jpg') }}"
                alt="JHR activity at Ozamiz Elementary School"
                loading="eager"
                onerror="this.onerror=null; this.src='/static/gallery_ozamiz.jpg';"
            >

            <div class="gallery-caption">

                <h3
                    data-en="🏫 Learning Together"
                    data-fil="🏫 Sama-samang Pagkatuto"
                >
                    🏫 Learning Together
                </h3>

                <p
                    data-en="A memorable learning and community activity with students at Ozamiz Elementary School."
                    data-fil="Isang makabuluhang aktibidad sa pagkatuto at komunidad kasama ang mga mag-aaral sa Ozamiz Elementary School."
                >
                    A memorable learning and community activity with students at Ozamiz Elementary School.
                </p>

            </div>

        </div>


        <!-- CORRECT PHOTO 2:
             OUTDOOR COMMUNITY / CODING ACTIVITY -->

        <div class="gallery-card">

            <img
                src="{{ url_for('serve_static', filename='gallery_community.jpg') }}"
                alt="JHR outdoor community coding activity"
                loading="eager"
                onerror="this.onerror=null; this.src='/static/gallery_community.jpg';"
            >

            <div class="gallery-caption">

                <h3
                    data-en="💻 Community Coding Activity"
                    data-fil="💻 Community Coding Activity"
                >
                    💻 Community Coding Activity
                </h3>

                <p
                    data-en="Sharing knowledge, learning together and bringing technology closer to the community."
                    data-fil="Pagbabahagi ng kaalaman, sama-samang pagkatuto at paglapit ng teknolohiya sa komunidad."
                >
                    Sharing knowledge, learning together and bringing technology closer to the community.
                </p>

            </div>

        </div>


    </div>

</section>


<!-- =========================
     SERVICES
========================= -->

<section class="section" id="services">

    <h2
        class="title"
        data-en="JHR Services 💻🎓"
        data-fil="Mga Serbisyo ng JHR 💻🎓"
    >
        JHR Services 💻🎓
    </h2>


    <p
        class="subtitle"
        data-en="We provide free coding classes to help students and beginners learn programming, build projects and develop useful technology skills."
        data-fil="Nagbibigay kami ng libreng coding classes upang matulungan ang mga estudyante at beginners na matuto ng programming, gumawa ng mga proyekto at magkaroon ng kapaki-pakinabang na technology skills."
    >
        We provide free coding classes to help students and beginners learn programming, build projects and develop useful technology skills.
    </p>


    <div class="cards">

        <div class="card">

            <h3
                data-en="💻 Free Coding Classes"
                data-fil="💻 Libreng Coding Classes"
            >
                💻 Free Coding Classes
            </h3>

            <p
                data-en="JHR provides free coding classes for beginners in a friendly and hands-on learning environment."
                data-fil="Nagbibigay ang JHR ng libreng coding classes para sa beginners sa isang magiliw at hands-on na learning environment."
            >
                JHR provides free coding classes for beginners in a friendly and hands-on learning environment.
            </p>

        </div>


        <div class="card">

            <h3
                data-en="🚀 Learn by Building"
                data-fil="🚀 Matuto sa Pamamagitan ng Pagbuo"
            >
                🚀 Learn by Building
            </h3>

            <p
                data-en="Practice coding by creating simple websites, projects and digital ideas step by step."
                data-fil="Magsanay sa coding sa pamamagitan ng paggawa ng simpleng websites, projects at digital ideas nang paunti-unti."
            >
                Practice coding by creating simple websites, projects and digital ideas step by step.
            </p>

        </div>


        <div class="card">

            <h3
                data-en="🌱 Skills for the Future"
                data-fil="🌱 Skills para sa Kinabukasan"
            >
                🌱 Skills for the Future
            </h3>

            <p
                data-en="Develop creativity, problem-solving and technology skills useful for school, projects and future opportunities."
                data-fil="Linangin ang creativity, problem-solving at technology skills na magagamit sa paaralan, mga proyekto at mga oportunidad sa hinaharap."
            >
                Develop creativity, problem-solving and technology skills useful for school, projects and future opportunities.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     FOUNDERS
========================= -->

<section class="section" id="founders">

    <h2
        class="title"
        data-en="Meet the JHR Team 👥"
        data-fil="Kilalanin ang JHR Team 👥"
    >
        Meet the JHR Team 👥
    </h2>


    <p
        class="subtitle"
        data-en="The founders behind JHR and its mission of empowerment through technology."
        data-fil="Ang mga tagapagtatag sa likod ng JHR at ng misyon nitong magbigay-kakayahan sa pamamagitan ng teknolohiya."
    >
        The founders behind JHR and its mission of empowerment through technology.
    </p>


    <div class="owners">


        <!-- JOSE -->

        <div class="owner-card">

            <img
                class="owner-photo"
                src="{{ url_for('serve_static', filename='Jose_Hugo_Rafael_T_Tan.jpg') }}"
                alt="Jose Hugo Rafael T. Tan"
                loading="eager"
                onerror="this.onerror=null; this.src='/static/Jose_Hugo_Rafael_T_Tan.jpg';"
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
                    data-en="A founder helping guide JHR's vision, projects and technology-focused activities through creativity, learning and service."
                    data-fil="Isang tagapagtatag na tumutulong gumabay sa pananaw, mga proyekto at technology-focused activities ng JHR sa pamamagitan ng pagkamalikhain, pagkatuto at paglilingkod."
                >
                    A founder helping guide JHR's vision, projects and technology-focused activities through creativity, learning and service.
                </p>

            </div>

        </div>


        <!-- JULIA -->

        <div class="owner-card">

            <img
                class="owner-photo"
                src="{{ url_for('serve_static', filename='Julia_Helga_Raquel_T_Tan.png') }}"
                alt="Julia Helga Raquel T. Tan"
                loading="eager"
                onerror="this.onerror=null; this.src='/static/Julia_Helga_Raquel_T_Tan.png';"
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
                    data-en="A founder supporting JHR's projects, creativity, education and technology activities."
                    data-fil="Isang tagapagtatag na sumusuporta sa mga proyekto, pagkamalikhain, edukasyon at technology activities ng JHR."
                >
                    A founder supporting JHR's projects, creativity, education and technology activities.
                </p>

            </div>

        </div>

    </div>

</section>


<!-- =========================
     GAMES
========================= -->

<section class="games" id="games">

    <h2
        class="title"
        data-en="JHR GAME ZONE 🎮"
        data-fil="JHR GAME ZONE 🎮"
    >
        JHR GAME ZONE 🎮
    </h2>


    <p
        class="subtitle"
        data-en="Learn, think and have fun!"
        data-fil="Matuto, mag-isip at magsaya!"
    >
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

            <h3>🧠 Quick Question</h3>

            <p>Which one is used to build websites?</p>

            <button onclick="webGame(false)">Python</button>

            <button onclick="webGame(true)">HTML</button>

            <button onclick="webGame(false)">Photoshop</button>


            <div id="webResult" class="game-result">
                Choose an answer!
            </div>

        </div>

    </div>

</section>


<!-- =========================
     CONTACT
========================= -->

<section class="section" id="contact">

    <div class="contact">

        <h2
            data-en="Join the JHR Journey 🚀"
            data-fil="Samahan ang JHR Journey 🚀"
        >
            Join the JHR Journey 🚀
        </h2>


        <p
            data-en="Technology • Education • Innovation • Community"
            data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad"
        >
            Technology • Education • Innovation • Community
        </p>


        <br>


        <p
            data-en="Learn. Create. Share. Empower."
            data-fil="Matuto. Lumikha. Magbahagi. Magbigay-kakayahan."
        >
            Learn. Create. Share. Empower.
        </p>

    </div>

</section>


<!-- =========================
     FOOTER
========================= -->

<footer>

    <div class="footer-logo">JHR</div>

    <p
        data-en="Technology • Education • Innovation • Community"
        data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad"
    >
        Technology • Education • Innovation • Community
    </p>


    <br>


    <p>
        © 2026 JHR. All rights reserved.
    </p>

</footer>


<!-- BACK TO TOP -->

<button
    class="top"
    id="topButton"
    onclick="scrollToTop()"
>
    ↑
</button>


<script>


/* =========================
   DARK MODE
========================= */

function toggleDarkMode() {

    document.body.classList.toggle("dark");

    const button =
        document.getElementById("themeButton");

    if (document.body.classList.contains("dark")) {

        button.innerHTML = "☀️";

        localStorage.setItem(
            "jhrTheme",
            "dark"
        );

    } else {

        button.innerHTML = "🌙";

        localStorage.setItem(
            "jhrTheme",
            "light"
        );

    }

}


function loadTheme() {

    const savedTheme =
        localStorage.getItem("jhrTheme");

    if (savedTheme === "dark") {

        document.body.classList.add("dark");

        document.getElementById(
            "themeButton"
        ).innerHTML = "☀️";

    }

}


/* =========================
   LANGUAGE
========================= */

let currentLanguage = "en";


function toggleLanguage() {

    const elements =
        document.querySelectorAll(
            "[data-en][data-fil]"
        );

    const button =
        document.getElementById(
            "languageButton"
        );


    if (currentLanguage === "en") {

        elements.forEach(function(element) {

            element.innerHTML =
                element.getAttribute(
                    "data-fil"
                );

        });

        currentLanguage = "fil";

        button.innerHTML = "🇬🇧 EN";

        localStorage.setItem(
            "jhrLanguage",
            "fil"
        );

    } else {

        elements.forEach(function(element) {

            element.innerHTML =
                element.getAttribute(
                    "data-en"
                );

        });

        currentLanguage = "en";

        button.innerHTML = "🇵🇭 FIL";

        localStorage.setItem(
            "jhrLanguage",
            "en"
        );

    }

}


function loadLanguage() {

    const savedLanguage =
        localStorage.getItem(
            "jhrLanguage"
        );

    if (savedLanguage === "fil") {

        toggleLanguage();

    }

}


/* =========================
   VIEWER COUNTER
========================= */

function updateViewerCounter() {

    let count =
        localStorage.getItem(
            "jhrViewerCount"
        );

    if (!count) {

        count = 0;

    }

    count =
        parseInt(count) + 1;

    localStorage.setItem(
        "jhrViewerCount",
        count
    );

    document.getElementById(
        "viewerCount"
    ).innerHTML = count;

}


/* =========================
   MATH GAME
========================= */

function mathGame(answer) {

    const result =
        document.getElementById(
            "mathResult"
        );

    if (answer === 96) {

        result.innerHTML =
            "🎉 Correct! Great job!";

    } else {

        result.innerHTML =
            "❌ Try again!";

    }

}


/* =========================
   WEBSITE GAME
========================= */

function webGame(correct) {

    const result =
        document.getElementById(
            "webResult"
        );

    if (correct) {

        result.innerHTML =
            "🎉 Correct! HTML is used to structure web pages.";

    } else {

        result.innerHTML =
            "❌ Not this one. Try again!";

    }

}


/* =========================
   BACK TO TOP
========================= */

window.addEventListener(
    "scroll",
    function() {

        const button =
            document.getElementById(
                "topButton"
            );

        if (window.scrollY > 500) {

            button.style.display = "block";

        } else {

            button.style.display = "none";

        }

    }
);


function scrollToTop() {

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


/* =========================
   STARTUP
========================= */

window.addEventListener(
    "DOMContentLoaded",
    function() {

        loadTheme();

        loadLanguage();

        updateViewerCounter();

    }
);


</script>


</body>

</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
