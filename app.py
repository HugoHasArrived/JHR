from flask import Flask, render_template_string
import os

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static"
)

viewer_count = 0


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="description"
    content="JHR - Empowerment Through Technology"
>

<title>JHR | Empowerment Through Technology</title>

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
   VARIABLES
========================================================= */

:root {

    --purple-dark: #2e1065;
    --purple-deep: #4c1d95;
    --purple: #6d28d9;
    --purple-light: #7c3aed;
    --purple-soft: #ede9fe;

    --white: #ffffff;

    --text: #24113f;
    --muted: #6b5b82;

    --shadow:
        0 15px 40px rgba(46, 16, 101, 0.18);
}


/* =========================================================
   BODY
========================================================= */

body {

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: var(--purple);

    color: var(--text);

    line-height: 1.6;
}


/* =========================================================
   NAVIGATION
========================================================= */

nav {

    position: sticky;

    top: 0;

    z-index: 1000;

    width: 100%;

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;

    padding: 10px 25px;

    background: white;

    box-shadow:
        0 5px 25px rgba(0,0,0,0.15);
}


.logo {

    display: flex;

    align-items: center;

    gap: 10px;

    font-size: 25px;

    font-weight: 900;

    color: var(--purple);
}


.logo img {

    width: 50px;

    height: 50px;

    object-fit: contain;
}


.nav-links {

    display: flex;

    align-items: center;

    justify-content: center;

    gap: 15px;

    flex-wrap: wrap;
}


.nav-links a {

    color: var(--text);

    text-decoration: none;

    font-size: 13px;

    font-weight: 700;

    transition: 0.2s;
}


.nav-links a:hover {

    color: var(--purple-light);
}


/* =========================================================
   HERO
========================================================= */

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
            var(--purple-dark),
            var(--purple-light),
            var(--purple-deep)
        );
}


.hero-content {

    width: 100%;

    max-width: 1050px;

    position: relative;

    z-index: 2;
}


.badge {

    display: inline-block;

    padding: 11px 20px;

    border:
        1px solid
        rgba(255,255,255,0.4);

    border-radius: 30px;

    background:
        rgba(255,255,255,0.12);

    font-weight: 800;

    color: white;

    margin-bottom: 25px;
}


.hero h1 {

    font-size:
        clamp(75px, 14vw, 160px);

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
        13px 23px;

    border-radius: 30px;

    background: white;

    color: var(--purple);

    text-decoration: none;

    font-weight: 900;

    transition: 0.2s;
}


.button:hover {

    transform: translateY(-3px);
}


.button.purple {

    background:
        #a78bfa;

    color: white;
}


/* =========================================================
   SECTIONS
========================================================= */

.section {

    max-width: 1180px;

    margin: auto;

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


/* =========================================================
   CARDS
========================================================= */

.cards {

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}


.card {

    background: white;

    border-radius: 22px;

    padding: 28px;

    box-shadow: var(--shadow);

    overflow: hidden;

    transition: 0.25s;
}


.card:hover {

    transform:
        translateY(-5px);
}


.card h3 {

    margin-bottom: 10px;

    color: var(--purple-light);
}


.card p {

    color: var(--muted);
}


/* =========================================================
   MISSION
========================================================= */

.color-section {

    padding:
        85px 22px;

    background:
        linear-gradient(
            135deg,
            var(--purple-deep),
            var(--purple-light)
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

    padding: 28px;

    background:
        rgba(255,255,255,0.1);

    color: white;

    border:
        1px solid
        rgba(255,255,255,0.2);

    border-radius: 22px;
}


.mission-card h3 {

    margin-bottom: 8px;
}


.mission-card p {

    color: #eee7ff;
}


.mission-icon {

    font-size: 40px;

    margin-bottom: 10px;
}


/* =========================================================
   STATS
========================================================= */

.stats {

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}


.stat {

    background: white;

    padding: 30px;

    text-align: center;

    border-radius: 22px;

    box-shadow: var(--shadow);
}


.stat-number {

    font-size: 48px;

    font-weight: 1000;

    color: var(--purple-light);
}


/* =========================================================
   SERVICES
========================================================= */

.services {

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}


.service-card {

    background: white;

    padding: 30px;

    border-radius: 22px;

    box-shadow: var(--shadow);

    border-top:
        5px solid
        var(--purple-light);

    transition: 0.25s;
}


.service-card:hover {

    transform:
        translateY(-5px);
}


.service-icon {

    font-size: 42px;

    margin-bottom: 12px;
}


.service-card h3 {

    margin-bottom: 10px;

    color: var(--purple-light);
}


.service-card p {

    color: var(--muted);
}


.free {

    display: inline-block;

    margin-top: 16px;

    padding:
        6px 12px;

    border-radius: 20px;

    background:
        var(--purple-soft);

    color:
        var(--purple-light);

    font-weight: 900;

    font-size: 12px;
}


/* =========================================================
   GALLERY
========================================================= */

.gallery-grid {

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 25px;
}


.gallery-card {

    background: white;

    border-radius: 22px;

    overflow: hidden;

    box-shadow: var(--shadow);

    border:
        1px solid
        #ddd0ff;

    transition: 0.25s;
}


.gallery-card:hover {

    transform:
        translateY(-5px);
}


/*
   IMPORTANT:
   These are the ONLY gallery images.
*/

.gallery-card img {

    display: block;

    width: 100%;

    height: 400px;

    object-fit: cover;

    background:
        var(--purple-soft);
}


.gallery-caption {

    padding: 22px;
}


.gallery-caption h3 {

    color:
        var(--purple-light);

    margin-bottom: 7px;
}


.gallery-caption p {

    color:
        var(--muted);
}


/* =========================================================
   FOUNDERS / JHR TEAM
========================================================= */

.team {

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 28px;
}


.team-card {

    display: grid;

    grid-template-columns:
        190px 1fr;

    background: white;

    border-radius: 22px;

    overflow: hidden;

    box-shadow: var(--shadow);
}


.team-photo {

    width: 190px;

    height: 100%;

    min-height: 330px;

    object-fit: cover;

    background:
        var(--purple-soft);
}


.team-info {

    padding: 27px;
}


.team-info h3 {

    font-size: 22px;

    margin-bottom: 7px;

    color: var(--text);
}


.team-role {

    display: inline-block;

    padding:
        5px 13px;

    border-radius: 20px;

    background:
        var(--purple-soft);

    color:
        var(--purple-light);

    font-weight: 900;

    margin-bottom: 15px;
}


.team-info p {

    color:
        var(--muted);
}


/* =========================================================
   GAME ZONE
========================================================= */

.games {

    padding:
        85px 22px;

    background:
        var(--purple-soft);
}


.game-grid {

    max-width: 1100px;

    margin: auto;

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 20px;
}


.game {

    background: white;

    padding: 25px;

    border-radius: 22px;

    box-shadow: var(--shadow);
}


.game h3 {

    color:
        var(--purple-light);

    margin-bottom: 10px;
}


.game p {

    color:
        var(--muted);

    margin-bottom: 10px;
}


.game button {

    margin:
        5px 3px;

    padding:
        9px 13px;

    border: 0;

    border-radius: 12px;

    background:
        var(--purple-light);

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


/* =========================================================
   CONTACT
========================================================= */

.contact {

    text-align: center;

    background:
        var(--purple-deep);

    color: white;

    padding:
        75px 22px;
}


.contact h2 {

    font-size:
        clamp(30px, 5vw, 48px);

    margin-bottom: 10px;
}


.contact p {

    color:
        #eee7ff;

    margin:
        8px 0;
}


/* =========================================================
   VIEWER COUNTER
   EXACTLY BELOW JOIN THE JHR JOURNEY
========================================================= */

.viewer-counter {

    width: 100%;

    text-align: center;

    padding:
        22px 20px;

    background:
        var(--purple-dark);

    color: white;

    font-size: 17px;

    font-weight: 700;
}


.viewer-counter strong {

    color:
        #c4b5fd;

    font-size: 22px;
}


/* =========================================================
   FOOTER
========================================================= */

footer {

    text-align: center;

    padding:
        28px 20px;

    background:
        #1e0a44;

    color:
        #eee7ff;
}


footer p {

    margin:
        4px 0;
}


/* =========================================================
   TOP BUTTON
========================================================= */

.top {

    position: fixed;

    right: 20px;

    bottom: 20px;

    display: none;

    border: 0;

    border-radius: 50%;

    width: 48px;

    height: 48px;

    background:
        var(--purple-light);

    color: white;

    font-size: 20px;

    cursor: pointer;

    z-index: 900;
}


/* =========================================================
   MOBILE
========================================================= */

@media(max-width: 950px) {

    .cards,
    .mission,
    .services,
    .game-grid {

        grid-template-columns:
            repeat(2, 1fr);
    }

    .team {

        grid-template-columns:
            1fr;
    }
}


@media(max-width: 700px) {

    nav {

        flex-direction: column;

        padding: 12px;
    }

    .nav-links {

        gap: 9px;
    }

    .nav-links a {

        font-size: 11px;
    }

    .hero {

        min-height: 620px;
    }

    .cards,
    .mission,
    .services,
    .game-grid,
    .stats,
    .gallery-grid {

        grid-template-columns:
            1fr;
    }

    .team-card {

        grid-template-columns:
            1fr;
    }

    .team-photo {

        width: 100%;

        height: 350px;

        min-height: 0;
    }

    .gallery-card img {

        height: 300px;
    }

    .title {

        font-size: 34px;
    }
}

</style>

</head>


<body>


<!-- =====================================================
     NAVIGATION
===================================================== -->

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

        <a href="#services">Services</a>

        <a href="#gallery">Gallery</a>

        <a href="#founders">Founders</a>

        <a href="#games">Games</a>

        <a href="#contact">Contact</a>

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


<!-- =====================================================
     ABOUT
===================================================== -->

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

                We encourage people to learn useful
                digital and technology skills.

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


<!-- =====================================================
     MISSION
===================================================== -->

<section
    class="color-section"
    id="mission"
>

    <h2 class="title">

        Our Mission

    </h2>


    <p
        class="subtitle"
        style="color:#eee7ff;"
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


<!-- =====================================================
     STATS
===================================================== -->

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


<!-- =====================================================
     PROJECTS
===================================================== -->

<section
    class="section"
    id="projects"
>

    <h2 class="title">

        JHR Projects 🚀

    </h2>


    <p class="subtitle">

        Technology, education and community projects
        designed around learning and positive impact.

    </p>


    <div class="cards">


        <div class="card">

            <h3>
                💻 Technology Projects
            </h3>

            <p>

                Websites, digital tools, programming,
                creative technology and experiments.

            </p>

        </div>


        <div class="card">

            <h3>
                🏫 Education
            </h3>

            <p>

                Technology-related learning activities
                and educational experiences.

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

    <h2 class="title">

        JHR Services 💻🎓

    </h2>


    <p class="subtitle">

        We provide learning opportunities that help
        people discover technology and build useful skills.

    </p>


    <div class="services">


        <!-- FREE CODING -->

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
                for beginners and learners who want
                to start programming.

            </p>

            <span class="free">
                FREE
            </span>

        </div>


        <!-- WEB DEVELOPMENT -->

        <div class="service-card">

            <div class="service-icon">
                🌐
            </div>

            <h3>
                Web Development
            </h3>

            <p>

                Learn the basics of building websites
                using HTML, CSS and JavaScript.

            </p>

        </div>


        <!-- LEARN BY BUILDING -->

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


        <!-- TECHNOLOGY SKILLS -->

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


<!-- =====================================================
     GALLERY
     
     ONLY THE TWO CORRECT PHOTOS ARE HERE.
===================================================== -->

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


        <!-- PHOTO 1 -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_ozamiz.jpg') }}"
                alt="JHR at Ozamiz Elementary School"
                loading="eager"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
            >

            <div
                class="gallery-caption"
                style="display:none;"
            >

                <h3>
                    Photo could not load
                </h3>

                <p>
                    Make sure gallery_ozamiz.jpg
                    is inside the static folder.
                </p>

            </div>


            <div class="gallery-caption">

                <h3>
                    🏫 Ozamiz Elementary School
                </h3>

                <p>

                    A JHR community moment
                    with children and learners.

                </p>

            </div>

        </div>


        <!-- PHOTO 2 -->

        <div class="gallery-card">

            <img
                src="{{ url_for('static', filename='gallery_community.jpg') }}"
                alt="JHR community learning activity"
                loading="eager"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
            >

            <div
                class="gallery-caption"
                style="display:none;"
            >

                <h3>
                    Photo could not load
                </h3>

                <p>
                    Make sure gallery_community.jpg
                    is inside the static folder.
                </p>

            </div>


            <div class="gallery-caption">

                <h3>
                    💻 Community Learning
                </h3>

                <p>

                    Learning, teamwork and
                    technology in the community.

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

    <h2 class="title">

        JHR Team 👥

    </h2>


    <p class="subtitle">

        The founders behind JHR and its mission
        of empowerment through technology.

    </p>


    <div class="team">


        <!-- JOSE -->

        <div class="team-card">

            <img
                class="team-photo"
                src="{{ url_for('static', filename='Jose_Hugo_Rafael_T_Tan.jpg') }}"
                alt="Jose Hugo Rafael T. Tan"
                loading="lazy"
            >


            <div class="team-info">

                <h3>

                    Jose Hugo Rafael T. Tan

                </h3>


                <div class="team-role">

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


        <!-- JULIA -->

        <div class="team-card">

            <img
                class="team-photo"
                src="{{ url_for('static', filename='Julia_Helga_Raquel_T_Tan.png') }}"
                alt="Julia Helga Raquel T. Tan"
                loading="lazy"
            >


            <div class="team-info">

                <h3>

                    Julia Helga Raquel T. Tan

                </h3>


                <div class="team-role">

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


<!-- =====================================================
     GAME ZONE
===================================================== -->

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


        <!-- MATH -->

        <div class="game">

            <h3>
                ⚡ Speed Math
            </h3>

            <p>
                What is 12 × 8?
            </p>


            <button
                onclick="mathGame(96)"
            >
                96
            </button>


            <button
                onclick="mathGame(88)"
            >
                88
            </button>


            <button
                onclick="mathGame(108)"
            >
                108
            </button>


            <div
                id="mathResult"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- TECH QUIZ -->

        <div class="game">

            <h3>
                🧠 Tech Quiz
            </h3>

            <p>
                What does CPU mean?
            </p>


            <button
                onclick="techGame(true)"
            >
                Central Processing Unit
            </button>


            <button
                onclick="techGame(false)"
            >
                Computer Power Utility
            </button>


            <div
                id="techResult"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- SAFETY -->

        <div class="game">

            <h3>
                🔐 Online Safety
            </h3>

            <p>
                Should you share your password?
            </p>


            <button
                onclick="safetyGame(false)"
            >
                Yes
            </button>


            <button
                onclick="safetyGame(true)"
            >
                No
            </button>


            <div
                id="safetyResult"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


        <!-- VALUES -->

        <div class="game">

            <h3>
                🤝 JHR Values
            </h3>

            <p>
                What helps a team succeed?
            </p>


            <button
                onclick="valuesGame(true)"
            >
                Cooperation
            </button>


            <button
                onclick="valuesGame(false)"
            >
                Giving up
            </button>


            <div
                id="valuesResult"
                class="game-result"
            >
                Choose an answer!
            </div>

        </div>


    </div>

</section>


<!-- =====================================================
     CONTACT / JOURNEY
===================================================== -->

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


<!-- =====================================================
     VIEWER COUNTER
     
     EXACTLY BELOW:
     
     Join the JHR Journey 🚀
     Technology • Education • Innovation • Community
     Learn. Create. Share. Empower.
===================================================== -->

<div class="viewer-counter">

    👀

    <strong>
        {{ viewer_count }}
    </strong>

    viewers

</div>


<!-- =====================================================
     FOOTER
===================================================== -->

<footer>

    <p>

        © 2026 JHR — Empowerment Through Technology

    </p>


    <p>

        Technology • Education • Innovation • Community

    </p>

</footer>


<!-- =====================================================
     BACK TO TOP
===================================================== -->

<button
    class="top"
    id="topButton"
    onclick="window.scrollTo({top:0,behavior:'smooth'})"
>

    ↑

</button>


<!-- =====================================================
     JAVASCRIPT
===================================================== -->

<script>


/* SPEED MATH */

function mathGame(answer) {

    const result =
        document.getElementById("mathResult");

    if (answer === 96) {

        result.textContent =
            "🎉 Correct! 12 × 8 = 96.";

    } else {

        result.textContent =
            "❌ Try again!";

    }

}


/* TECH QUIZ */

function techGame(correct) {

    const result =
        document.getElementById("techResult");

    if (correct) {

        result.textContent =
            "💡 Correct! CPU means Central Processing Unit.";

    } else {

        result.textContent =
            "❌ Try again!";

    }

}


/* ONLINE SAFETY */

function safetyGame(correct) {

    const result =
        document.getElementById("safetyResult");

    if (correct) {

        result.textContent =
            "🔐 Correct! Keep passwords private.";

    } else {

        result.textContent =
            "❌ Never share your password!";

    }

}


/* JHR VALUES */

function valuesGame(correct) {

    const result =
        document.getElementById("valuesResult");

    if (correct) {

        result.textContent =
            "🤝 Correct! Cooperation matters!";

    } else {

        result.textContent =
            "❌ Try again!";

    }

}


/* BACK TO TOP */

window.addEventListener(
    "scroll",
    function() {

        const button =
            document.getElementById("topButton");

        if (window.scrollY > 500) {

            button.style.display = "block";

        } else {

            button.style.display = "none";

        }

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
        port=port
    )
