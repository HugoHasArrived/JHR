from flask import Flask, render_template_string
import os

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

viewer_count = 0

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<meta name="theme-color" content="#7c3aed">

<title>JHR | Empowerment Through Technology</title>

<style>

/* =========================
   RESET
========================= */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    scroll-behavior: smooth;
}

:root {
    --purple: #7c3aed;
    --purple-dark: #4c1d95;
    --purple-deep: #2e1065;
    --purple-light: #ede9fe;
    --purple-soft: #f5f3ff;

    --white: #ffffff;
    --text: #24113f;
    --muted: #6b5b82;

    --card: #ffffff;

    --shadow:
        0 12px 35px rgba(76, 29, 149, 0.16);
}

/* =========================
   BODY
========================= */

body {
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: var(--purple);
    color: var(--text);
    line-height: 1.6;

    transition:
        background 0.25s ease,
        color 0.25s ease;
}

/* =========================
   DARK MODE
========================= */

body.dark {
    --text: #ffffff;
    --muted: #ddd0f0;
    --card: #24103d;

    background: #16052d;
    color: #ffffff;
}

body.dark nav {
    background: #19072f;
}

body.dark .card,
body.dark .service-card,
body.dark .stat,
body.dark .owner-card,
body.dark .gallery-card,
body.dark .game {
    background: #24103d;
    color: white;
}

body.dark .games {
    background: #24103d;
}

body.dark .title {
    color: white;
}

body.dark .subtitle,
body.dark .card p,
body.dark .service-card p,
body.dark .gallery-caption p,
body.dark .owner-info p,
body.dark .game p {
    color: #ddd0f0;
}

/* =========================
   NAVIGATION
========================= */

nav {
    position: sticky;
    top: 0;
    z-index: 9999;

    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 15px;

    padding: 10px 22px;

    background: white;

    box-shadow:
        0 5px 25px rgba(0, 0, 0, 0.15);
}

.logo {
    display: flex;
    align-items: center;
    gap: 9px;

    font-size: 25px;
    font-weight: 900;

    color: var(--purple);

    text-decoration: none;
}

.logo img {
    width: 48px;
    height: 48px;

    object-fit: contain;

    display: block;
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
    font-weight: 800;

    transition: 0.2s;
}

.nav-links a:hover {
    color: var(--purple);
}

.nav-controls {
    display: flex;
    align-items: center;
    gap: 7px;
}

.nav-btn {
    border: none;

    border-radius: 20px;

    padding: 8px 12px;

    background: var(--purple);
    color: white;

    cursor: pointer;

    font-weight: 800;

    transition: 0.2s;
}

.nav-btn:hover {
    transform: translateY(-2px);
    background: var(--purple-dark);
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

    color: white;

    padding: 80px 20px;

    position: relative;
    overflow: hidden;

    background:
        linear-gradient(
            135deg,
            #2e1065,
            #7c3aed 52%,
            #581c87
        );
}

.hero-content {
    max-width: 1050px;

    position: relative;
    z-index: 2;
}

.badge {
    display: inline-block;

    padding: 10px 20px;

    border:
        1px solid
        rgba(255,255,255,0.4);

    border-radius: 30px;

    background:
        rgba(255,255,255,0.12);

    font-weight: 800;

    margin-bottom: 20px;
}

.hero h1 {
    font-size:
        clamp(76px, 14vw, 155px);

    line-height: 0.85;

    letter-spacing: 8px;

    font-weight: 1000;
}

.hero h2 {
    font-size:
        clamp(22px, 4vw, 42px);

    margin:
        25px 0 15px;
}

.hero p {
    max-width: 780px;

    margin: auto;

    font-size: 19px;

    color: #f4edff;
}

.button {
    display: inline-block;

    margin:
        25px 7px 0;

    padding:
        13px 22px;

    border-radius: 28px;

    background: white;

    color: var(--purple);

    text-decoration: none;

    font-weight: 900;
}

.button.purple {
    background: #a78bfa;
    color: white;
}

/* =========================
   SECTIONS
========================= */

.section {
    max-width: 1180px;

    margin: 0 auto;

    padding:
        85px 22px;
}

.title {
    text-align: center;

    font-size: 42px;

    margin-bottom: 12px;

    color: var(--text);
}

.subtitle {
    text-align: center;

    max-width: 780px;

    margin:
        0 auto 42px;

    color: var(--muted);

    font-size: 18px;
}

/* =========================
   CARDS
========================= */

.cards {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}

.card {
    background: var(--card);

    border-radius: 22px;

    box-shadow: var(--shadow);

    padding: 27px;

    overflow: hidden;
}

.card h3 {
    color: var(--purple);

    margin-bottom: 10px;
}

.card p {
    color: var(--muted);
}

/* =========================
   MISSION
========================= */

.color-section {
    padding:
        85px 22px;

    background:
        linear-gradient(
            135deg,
            #4c1d95,
            #7c3aed
        );

    color: white;
}

.color-section .title {
    color: white;
}

.mission {
    max-width: 1180px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}

.mission-card {
    padding: 27px;

    background:
        rgba(255,255,255,0.1);

    color: white;

    border-radius: 22px;

    border:
        1px solid
        rgba(255,255,255,0.2);
}

.mission-icon {
    font-size: 40px;

    margin-bottom: 10px;
}

.mission-card p {
    color: #eee7ff;
}

/* =========================
   STATS
========================= */

.stats {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}

.stat {
    background: var(--card);

    border-radius: 22px;

    box-shadow: var(--shadow);

    padding: 30px;

    text-align: center;
}

.stat-number {
    font-size: 48px;

    font-weight: 1000;

    color: var(--purple);
}

/* =========================
   SERVICES
========================= */

.services {
    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}

.service-card {
    background: var(--card);

    border-radius: 22px;

    box-shadow: var(--shadow);

    padding: 30px;

    border-top:
        5px solid
        var(--purple);
}

.service-icon {
    font-size: 42px;

    margin-bottom: 12px;
}

.service-card h3 {
    color: var(--purple);

    margin-bottom: 10px;
}

.service-card p {
    color: var(--muted);
}

.free {
    display: inline-block;

    margin-top: 16px;

    padding:
        6px 11px;

    border-radius: 20px;

    background:
        #ede9fe;

    color:
        var(--purple);

    font-weight: 900;

    font-size: 12px;
}

/* =========================
   GALLERY
========================= */

.gallery-grid {
    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 24px;
}

.gallery-card {
    background: var(--card);

    border-radius: 22px;

    box-shadow: var(--shadow);

    overflow: hidden;

    border:
        1px solid
        #ddd0ff;
}

.gallery-card img {
    display: block;

    width: 100%;

    height: 330px;

    object-fit: cover;

    background:
        #ede9fe;

    /* Faster rendering */
    loading: lazy;
}

.gallery-caption {
    padding: 20px;
}

.gallery-caption h3 {
    margin-bottom: 6px;
}

.gallery-caption p {
    color: var(--muted);
}

/* =========================
   FOUNDERS
========================= */

.owners {
    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 28px;
}

.owner-card {
    display: grid;

    grid-template-columns:
        180px 1fr;

    background: var(--card);

    border-radius: 22px;

    box-shadow: var(--shadow);

    overflow: hidden;
}

.owner-photo {
    width: 180px;

    height: 100%;

    min-height: 310px;

    object-fit: cover;

    background:
        #ede9fe;

    display: block;
}

.owner-info {
    padding: 25px;
}

.owner-info h3 {
    font-size: 22px;

    margin-bottom: 5px;
}

.owner-role {
    display: inline-block;

    padding:
        5px 12px;

    border-radius: 20px;

    background:
        #ede9fe;

    color:
        var(--purple);

    font-weight: 900;

    margin-bottom: 15px;
}

.owner-info p {
    color: var(--muted);
}

/* =========================
   GAMES
========================= */

.games {
    padding:
        85px 22px;

    background:
        #ede9fe;
}

.game-grid {
    max-width: 1150px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}

.game {
    background: white;

    border-radius: 22px;

    box-shadow: var(--shadow);

    padding: 25px;
}

.game h3 {
    color: var(--purple);

    margin-bottom: 8px;
}

.game p {
    color: var(--muted);

    margin-bottom: 8px;
}

.game button {
    margin:
        6px 3px;

    padding:
        9px 13px;

    border: none;

    border-radius: 12px;

    background:
        var(--purple);

    color: white;

    cursor: pointer;

    font-weight: 800;
}

.game button:hover {
    background:
        var(--purple-dark);
}

.game-result {
    margin-top: 10px;

    font-weight: 800;
}

/* =========================
   CONTACT
========================= */

.contact {
    text-align: center;

    background:
        var(--purple-dark);

    color: white;

    padding:
        75px 22px;
}

.contact h2 {
    font-size: 38px;
}

.contact p {
    color: #eee7ff;

    margin: 10px 0;
}

/* =========================
   VIEWER COUNTER
   VERY BOTTOM
========================= */

.viewer-counter {
    text-align: center;

    padding:
        22px 20px;

    background:
        #2e1065;

    color: white;

    font-size: 17px;

    font-weight: 800;
}

.viewer-number {
    color: #c4b5fd;

    font-size: 25px;
}

/* =========================
   FOOTER
========================= */

footer {
    text-align: center;

    padding: 25px;

    background:
        #1e0a42;

    color:
        #eee7ff;
}

/* =========================
   BACK TO TOP
========================= */

.top {
    position: fixed;

    right: 20px;

    bottom: 20px;

    display: none;

    border: none;

    border-radius: 50%;

    width: 48px;

    height: 48px;

    background:
        var(--purple);

    color: white;

    font-size: 20px;

    cursor: pointer;

    z-index: 9000;
}

/* =========================
   RESPONSIVE
========================= */

@media(max-width: 1050px) {

    .cards,
    .mission,
    .services,
    .game-grid {
        grid-template-columns:
            repeat(2, 1fr);
    }

}

@media(max-width: 850px) {

    nav {
        flex-direction: column;
    }

    .owners {
        grid-template-columns: 1fr;
    }

}

@media(max-width: 700px) {

    .nav-links {
        gap: 8px;
    }

    .nav-links a {
        font-size: 11px;
    }

    .hero {
        min-height: 620px;
    }

    .gallery-grid,
    .cards,
    .mission,
    .services,
    .game-grid,
    .stats {
        grid-template-columns: 1fr;
    }

    .owner-card {
        grid-template-columns: 1fr;
    }

    .owner-photo {
        width: 100%;

        height: 360px;

        min-height: 0;
    }

    .title {
        font-size: 34px;
    }

}

</style>

</head>

<body>

<!-- =========================
     NAVIGATION
========================= -->

<nav>

    <a class="logo" href="#home">

        <img
            src="{{ url_for('static', filename='OfficialLogo.png') }}"
            alt="JHR Logo"
            width="48"
            height="48"
            decoding="async"
        >

        <span>JHR</span>

    </a>

    <div class="nav-links">

        <a href="#home" data-en="Home" data-tl="Home">
            Home
        </a>

        <a href="#about" data-en="About" data-tl="Tungkol">
            About
        </a>

        <a href="#mission" data-en="Mission" data-tl="Misyon">
            Mission
        </a>

        <a href="#projects" data-en="Projects" data-tl="Mga Proyekto">
            Projects
        </a>

        <a href="#services" data-en="Services" data-tl="Serbisyo">
            Services
        </a>

        <a href="#gallery" data-en="Gallery" data-tl="Gallery">
            Gallery
        </a>

        <a href="#founders" data-en="Founders" data-tl="Mga Founder">
            Founders
        </a>

        <a href="#games" data-en="Games" data-tl="Mga Laro">
            Games
        </a>

        <a href="#contact" data-en="Contact" data-tl="Kontak">
            Contact
        </a>

    </div>

    <div class="nav-controls">

        <button
            class="nav-btn"
            id="themeBtn"
            onclick="toggleTheme()"
            aria-label="Toggle light and dark mode"
        >
            🌙
        </button>

        <button
            class="nav-btn"
            id="langBtn"
            onclick="toggleLanguage()"
            aria-label="Change language"
        >
            EN
        </button>

    </div>

</nav>


<!-- =========================
     HERO
========================= -->

<section
    class="hero"
    id="home"
>

    <div class="hero-content">

        <div class="badge">
            TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY
        </div>

        <h1>
            JHR
        </h1>

        <h2>
            EMPOWERMENT THROUGH TECHNOLOGY
        </h2>

        <p>
            Turning technology, creativity and learning
            into opportunities for people and communities.
        </p>

        <a
            class="button"
            href="#about"
        >
            ✨ Explore JHR
        </a>

        <a
            class="button purple"
            href="#services"
        >
            💻 Free Coding Classes
        </a>

    </div>

</section>


<!-- =========================
     ABOUT
========================= -->

<section
    class="section"
    id="about"
>

    <h2 class="title">
        What is JHR?
    </h2>

    <p class="subtitle">
        JHR — Empowerment Through Technology.
    </p>

    <div class="cards">

        <div class="card">

            <h3>
                💻 Technology
            </h3>

            <p>
                We explore technology as a tool
                for creativity, learning and opportunity.
            </p>

        </div>


        <div class="card">

            <h3>
                📚 Education
            </h3>

            <p>
                We encourage people to learn
                useful digital and technology skills.
            </p>

        </div>


        <div class="card">

            <h3>
                🌱 Community
            </h3>

            <p>
                Technology can help communities
                connect, learn and grow.
            </p>

        </div>


        <div class="card">

            <h3>
                💡 Innovation
            </h3>

            <p>
                Every big project starts with an idea
                and the courage to try.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     MISSION
========================= -->

<section
    class="color-section"
    id="mission"
>

    <h2 class="title">
        Our Mission
    </h2>

    <p
        class="subtitle"
        style="color:#eee7ff"
    >
        Empowerment through technology,
        knowledge and creativity.
    </p>

    <div class="mission">

        <div class="mission-card">

            <div class="mission-icon">
                💻
            </div>

            <h3>
                Technology
            </h3>

            <p>
                Promote creative and responsible
                technology use.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">
                🎓
            </div>

            <h3>
                Education
            </h3>

            <p>
                Encourage people to learn digital
                and technology skills.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">
                🌍
            </div>

            <h3>
                Community
            </h3>

            <p>
                Explore ways technology can create
                positive community impact.
            </p>

        </div>


        <div class="mission-card">

            <div class="mission-icon">
                🚀
            </div>

            <h3>
                Innovation
            </h3>

            <p>
                Turn creative ideas into useful
                projects and experiences.
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
            <div class="stat-number">
                100+
            </div>
            <p>
                Ideas
            </p>
        </div>

        <div class="stat">
            <div class="stat-number">
                25+
            </div>
            <p>
                Activities
            </p>
        </div>

        <div class="stat">
            <div class="stat-number">
                10+
            </div>
            <p>
                Projects
            </p>
        </div>

        <div class="stat">
            <div class="stat-number">
                1
            </div>
            <p>
                Big Mission
            </p>
        </div>

    </div>

</section>


<!-- =========================
     PROJECTS
========================= -->

<section
    class="section"
    id="projects"
>

    <h2 class="title">
        JHR Projects 🚀
    </h2>

    <p class="subtitle">
        Technology, education and community
        projects designed around learning
        and positive impact.
    </p>

    <div class="cards">

        <div class="card">

            <h3>
                💻 Technology Projects
            </h3>

            <p>
                Websites, digital tools,
                programming, creative technology
                and experiments.
            </p>

        </div>


        <div class="card">

            <h3>
                🏫 Education
            </h3>

            <p>
                Technology-related learning
                activities and educational experiences.
            </p>

        </div>


        <div class="card">

            <h3>
                🌾 Community & Agriculture
            </h3>

            <p>
                Exploring how technology can support
                communities and agricultural areas.
            </p>

        </div>


        <div class="card">

            <h3>
                🚀 Future Projects
            </h3>

            <p>
                More JHR projects will be added
                as new initiatives are completed.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     SERVICES
========================= -->

<section
    class="section"
    id="services"
>

    <h2 class="title">
        JHR Services 💻🎓
    </h2>

    <p class="subtitle">
        We provide learning opportunities that
        help people discover technology and
        build useful skills.
    </p>

    <div class="services">

        <div class="service-card">

            <div class="service-icon">
                💻
            </div>

            <h3>
                Free Coding Classes
            </h3>

            <p>
                We provide
                <strong>free coding classes</strong>
                for beginners and learners
                who want to start programming.
            </p>

            <span class="free">
                FREE
            </span>

        </div>


        <div class="service-card">

            <div class="service-icon">
                🌐
            </div>

            <h3>
                Web Development
            </h3>

            <p>
                Learn the basics of building
                websites using HTML, CSS
                and JavaScript.
            </p>

        </div>


        <div class="service-card">

            <div class="service-icon">
                🚀
            </div>

            <h3>
                Learn by Building
            </h3>

            <p>
                Practice technology by creating
                simple projects and turning ideas
                into working experiences.
            </p>

        </div>


        <div class="service-card">

            <div class="service-icon">
                🌱
            </div>

            <h3>
                Technology Skills
            </h3>

            <p>
                Develop practical digital skills
                that can support school, projects
                and future opportunities.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     CORRECT JHR GALLERY
========================= -->

<section
    class="section"
    id="gallery"
>

    <h2 class="title">
        JHR Gallery 📸
    </h2>

    <p class="subtitle">
        Moments of learning, teamwork,
        technology and community.
    </p>

    <div class="gallery-grid">


        <!-- PHOTO 1:
             CLASSROOM / LAPTOP
        -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_classroom.png') }}"
                alt="JHR technology classroom activity"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">

                <h3>
                    💻 Technology in Action
                </h3>

                <p>
                    Learning and technology
                    in a classroom environment.
                </p>

            </div>

        </div>


        <!-- PHOTO 2:
             COMMUNITY LEARNING
        -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_children_learning.jpeg') }}"
                alt="JHR community learning activity"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">

                <h3>
                    🤝 Learning Together
                </h3>

                <p>
                    A community learning activity
                    focused on teamwork and education.
                </p>

            </div>

        </div>


        <!-- PHOTO 3:
             SCHOOL
        -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_community.jpeg') }}"
                alt="JHR Ozamiz Elementary School activity"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">

                <h3>
                    🏫 School Community
                </h3>

                <p>
                    Connecting learning,
                    education and young people.
                </p>

            </div>

        </div>


        <!-- PHOTO 4:
             COMMUNITY ACTIVITY
        -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_school.jpeg') }}"
                alt="JHR community school activity"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">

                <h3>
                    🌱 Community Activity
                </h3>

                <p>
                    A community moment centered
                    on learning and participation.
                </p>

            </div>

        </div>

    </div>

</section>


<!-- =========================
     FOUNDERS / JHR TEAM
========================= -->

<section
    class="section"
    id="founders"
>

    <h2 class="title">
        JHR Team 👥
    </h2>

    <p class="subtitle">
        The founders behind JHR and its mission
        of empowerment through technology.
    </p>

    <div class="owners">


        <!-- BOY FOUNDER -->

        <div class="owner-card">

            <img
                class="owner-photo"
                src="{{ url_for('static', filename='Jose_Hugo_Rafael_T_Tan.jpg') }}"
                alt="Jose Hugo Rafael T. Tan"
                loading="eager"
                decoding="async"
            >

            <div class="owner-info">

                <h3>
                    Jose Hugo Rafael T. Tan
                </h3>

                <div class="owner-role">
                    Founder
                </div>

                <p>
                    Helps guide JHR's vision,
                    projects and technology-focused
                    activities through creativity,
                    learning and service.
                </p>

            </div>

        </div>


        <!-- GIRL FOUNDER -->

        <div class="owner-card">

            <img
                class="owner-photo"
                src="{{ url_for('static', filename='Julia_Helga_Raquel_T_Tan.png') }}"
                alt="Julia Helga Raquel T. Tan"
                loading="eager"
                decoding="async"
            >

            <div class="owner-info">

                <h3>
                    Julia Helga Raquel T. Tan
                </h3>

                <div class="owner-role">
                    Founder
                </div>

                <p>
                    Supports JHR's projects,
                    creativity and technology
                    activities while helping develop
                    ideas for learning and community impact.
                </p>

            </div>

        </div>

    </div>

</section>


<!-- =========================
     GAME ZONE
========================= -->

<section
    class="games"
    id="games"
>

    <h2 class="title">
        JHR GAME ZONE 🎮
    </h2>

    <p class="subtitle">
        Learn, think and have fun!
    </p>

    <div class="game-grid">


        <!-- GAME 1 -->

        <div class="game">

            <h3>
                ⚡ Speed Math
            </h3>

            <p>
                What is 12 × 8?
            </p>

            <button onclick="answer('math1', true)">
                96
            </button>

            <button onclick="answer('math1', false)">
                88
            </button>

            <button onclick="answer('math1', false)">
                108
            </button>

            <div
                id="math1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 2 -->

        <div class="game">

            <h3>
                🧠 Tech Quiz
            </h3>

            <p>
                What does CPU mean?
            </p>

            <button onclick="answer('tech1', true)">
                Central Processing Unit
            </button>

            <button onclick="answer('tech1', false)">
                Computer Power Utility
            </button>

            <div
                id="tech1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 3 -->

        <div class="game">

            <h3>
                🔐 Online Safety
            </h3>

            <p>
                Should you share your password?
            </p>

            <button onclick="answer('safe1', false)">
                Yes
            </button>

            <button onclick="answer('safe1', true)">
                No
            </button>

            <div
                id="safe1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 4 -->

        <div class="game">

            <h3>
                🤝 JHR Values
            </h3>

            <p>
                What helps a team succeed?
            </p>

            <button onclick="answer('value1', true)">
                Cooperation
            </button>

            <button onclick="answer('value1', false)">
                Giving up
            </button>

            <div
                id="value1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 5 -->

        <div class="game">

            <h3>
                💻 HTML Quiz
            </h3>

            <p>
                What does HTML create?
            </p>

            <button onclick="answer('html1', true)">
                Web pages
            </button>

            <button onclick="answer('html1', false)">
                Batteries
            </button>

            <div
                id="html1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 6 -->

        <div class="game">

            <h3>
                🔢 Binary
            </h3>

            <p>
                What is binary based on?
            </p>

            <button onclick="answer('binary1', true)">
                0 and 1
            </button>

            <button onclick="answer('binary1', false)">
                1 and 9
            </button>

            <div
                id="binary1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 7 -->

        <div class="game">

            <h3>
                🧩 Logic Challenge
            </h3>

            <p>
                Which one is a programming language?
            </p>

            <button onclick="answer('logic1', true)">
                Python
            </button>

            <button onclick="answer('logic1', false)">
                Banana
            </button>

            <div
                id="logic1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- GAME 8 -->

        <div class="game">

            <h3>
                🚀 JHR Challenge
            </h3>

            <p>
                What does JHR promote?
            </p>

            <button onclick="answer('jhr1', true)">
                Technology & Education
            </button>

            <button onclick="answer('jhr1', false)">
                Giving up
            </button>

            <div
                id="jhr1"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>

    </div>

</section>


<!-- =========================
     CONTACT
========================= -->

<section
    class="contact"
    id="contact"
>

    <h2>
        Join the JHR Journey 🚀
    </h2>

    <p>
        Technology • Education • Innovation • Community
    </p>

    <p>
        Learn. Create. Share. Empower.
    </p>

</section>


<!-- =========================
     VIEWER COUNTER
     EXACTLY AT THE BOTTOM
========================= -->

<div class="viewer-counter">

    👀

    <span class="viewer-number">
        {{ viewer_count }}
    </span>

    visitors

</div>


<!-- =========================
     FOOTER
========================= -->

<footer>

    <p>
        © 2026 JHR — Empowerment Through Technology
    </p>

    <p>
        Technology • Education • Innovation • Community
    </p>

</footer>


<!-- =========================
     BACK TO TOP
========================= -->

<button
    class="top"
    id="topButton"
    onclick="window.scrollTo({top:0,behavior:'smooth'})"
>
    ↑
</button>


<script>

/* =========================
   THEME
========================= */

function toggleTheme() {

    document.body.classList.toggle("dark");

    const isDark =
        document.body.classList.contains("dark");

    localStorage.setItem(
        "jhrTheme",
        isDark ? "dark" : "light"
    );

    document.getElementById("themeBtn").textContent =
        isDark ? "☀️" : "🌙";
}


/* =========================
   LANGUAGE
========================= */

let currentLanguage =
    localStorage.getItem("jhrLanguage") || "en";


function toggleLanguage() {

    currentLanguage =
        currentLanguage === "en"
            ? "tl"
            : "en";

    localStorage.setItem(
        "jhrLanguage",
        currentLanguage
    );

    applyLanguage();
}


function applyLanguage() {

    document
        .querySelectorAll("[data-en]")
        .forEach(function(element) {

            element.textContent =
                currentLanguage === "en"
                    ? element.dataset.en
                    : element.dataset.tl;

        });


    document.getElementById("langBtn").textContent =
        currentLanguage === "en"
            ? "EN"
            : "TL";
}


/* =========================
   LOAD SAVED SETTINGS
========================= */

function loadSettings() {

    const savedTheme =
        localStorage.getItem("jhrTheme");

    if (savedTheme === "dark") {

        document.body.classList.add("dark");

        document.getElementById(
            "themeBtn"
        ).textContent = "☀️";

    } else {

        document.getElementById(
            "themeBtn"
        ).textContent = "🌙";

    }

    applyLanguage();
}


/* =========================
   GAMES
========================= */

function answer(id, correct) {

    const element =
        document.getElementById(id);

    if (correct) {

        element.textContent =
            "🎉 Correct! Great job!";

    } else {

        element.textContent =
            "❌ Try again!";

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

            button.style.display =
                "block";

        } else {

            button.style.display =
                "none";

        }

    }
);


/* =========================
   IMAGE ERROR HANDLING
========================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadSettings();

        document
            .querySelectorAll("img")
            .forEach(function(img) {

                img.addEventListener(
                    "error",
                    function() {

                        this.style.background =
                            "linear-gradient(135deg,#4c1d95,#7c3aed)";

                        this.alt =
                            "JHR photo could not be loaded";

                    }
                );

            });

    }
);

</script>

</body>
</html>
"""


@app.route("/")
def home():

    global viewer_count

    viewer_count += 1

    return render_template_string(
        HTML,
        viewer_count=viewer_count
    )


@app.route("/health")
def health():

    return "JHR is running!", 200


@app.route("/photo-check")
def photo_check():

    files = [

        "OfficialLogo.png",

        "Jose_Hugo_Rafael_T_Tan.jpg",

        "Julia_Helga_Raquel_T_Tan.png",

        "gallery_classroom.png",

        "gallery_children_learning.jpeg",

        "gallery_community.jpeg",

        "gallery_school.jpeg",

    ]

    result = [
        "<h1>JHR Photo Check</h1>"
    ]

    for filename in files:

        path = os.path.join(
            app.static_folder,
            filename
        )

        if os.path.isfile(path):

            result.append(
                f"✅ {filename} — LOADED"
            )

        else:

            result.append(
                f"❌ {filename} — MISSING"
            )

    return "<br>".join(result)


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
