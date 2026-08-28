from flask import Flask, render_template_string

app = Flask(__name__)

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
    --purple: #7b2cbf;
    --purple-dark: #3c096c;
    --purple-light: #c77dff;
    --pink: #e85dff;
    --white: #ffffff;
    --text: #241033;
    --muted: #6b5b73;
    --background: #f7efff;
    --card: #ffffff;
}

html {
    scroll-behavior: smooth;
}

body {
    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        linear-gradient(
            180deg,
            #f7efff 0%,
            #ffffff 45%,
            #f3e5ff 100%
        );

    color: var(--text);
    line-height: 1.6;
    overflow-x: hidden;
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

    gap: 20px;

    padding: 12px 25px;

    background: rgba(255,255,255,0.97);

    border-bottom:
        2px solid
        rgba(123,44,191,0.12);

    box-shadow:
        0 5px 25px
        rgba(75,20,110,0.12);
}

.logo {
    display: flex;
    align-items: center;

    gap: 10px;

    color: var(--purple);

    font-size: 26px;
    font-weight: 900;

    letter-spacing: 2px;
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

    gap: 15px;

    flex-wrap: wrap;
}

.nav-links a {
    color: var(--text);

    text-decoration: none;

    font-size: 14px;
    font-weight: 700;

    transition: 0.2s;
}

.nav-links a:hover {
    color: var(--purple);
}

/* =========================
   HERO
========================= */

.hero {
    min-height: 720px;

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
            rgba(199,125,255,0.35),
            transparent 25%
        ),
        radial-gradient(
            circle at 80% 20%,
            rgba(232,93,255,0.28),
            transparent 25%
        ),
        linear-gradient(
            135deg,
            #240046,
            #5a189a,
            #7b2cbf,
            #9d4edd
        );
}

.hero-content {
    position: relative;

    z-index: 2;

    width: 100%;
    max-width: 1000px;

    padding: 40px 25px;
}

.badge {
    display: inline-block;

    padding: 12px 22px;

    margin-bottom: 25px;

    border-radius: 30px;

    background:
        rgba(255,255,255,0.13);

    border:
        1px solid
        rgba(255,255,255,0.3);

    font-weight: 800;

    color: white;
}

.hero h1 {
    font-size:
        clamp(
            75px,
            15vw,
            160px
        );

    line-height: 0.9;

    font-weight: 1000;

    letter-spacing: 8px;

    color: white;

    text-shadow:
        0 10px 35px
        rgba(0,0,0,0.25);
}

.hero h2 {
    margin: 30px 0 20px;

    font-size:
        clamp(
            22px,
            4vw,
            40px
        );

    color: #ffffff;
}

.hero p {
    max-width: 800px;

    margin: auto;

    font-size: 20px;

    color: #f8edff;
}

.hero-buttons {
    margin-top: 30px;
}

/* =========================
   BUTTONS
========================= */

.button {
    display: inline-block;

    margin: 8px;

    padding:
        14px 25px;

    border-radius: 35px;

    background:
        linear-gradient(
            135deg,
            #ffffff,
            #ead7ff
        );

    color:
        var(--purple-dark);

    text-decoration: none;

    font-weight: 900;

    transition: 0.25s;
}

.button:hover {
    transform:
        translateY(-4px);

    box-shadow:
        0 12px 25px
        rgba(0,0,0,0.15);
}

.button.purple {
    color: white;

    background:
        linear-gradient(
            135deg,
            #7b2cbf,
            #9d4edd
        );
}

/* =========================
   SECTION
========================= */

.section {
    max-width: 1200px;

    margin: auto;

    padding:
        90px 25px;
}

.title {
    text-align: center;

    font-size:
        clamp(
            32px,
            5vw,
            50px
        );

    margin-bottom: 15px;

    color: var(--purple-dark);
}

.subtitle {
    max-width: 850px;

    margin:
        0 auto 45px;

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

    padding: 30px;

    border-radius: 22px;

    box-shadow:
        0 10px 30px
        rgba(75,20,110,0.12);

    border-top:
        5px solid
        var(--purple);

    transition: 0.25s;
}

.card:hover {
    transform:
        translateY(-7px);

    box-shadow:
        0 18px 40px
        rgba(75,20,110,0.18);
}

.card h3 {
    color:
        var(--purple);

    margin-bottom: 10px;

    font-size: 23px;
}

/* =========================
   MISSION
========================= */

.color-section {
    padding:
        90px 25px;

    color: white;

    background:
        linear-gradient(
            135deg,
            #240046,
            #5a189a,
            #7b2cbf
        );
}

.color-section .title {
    color: white;
}

.color-section .subtitle {
    color: #eadcff;
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
        rgba(255,255,255,0.10);

    border:
        1px solid
        rgba(255,255,255,0.2);
}

.mission-icon {
    font-size: 50px;

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

    padding: 30px;

    background: white;

    border-radius: 20px;

    box-shadow:
        0 8px 25px
        rgba(75,20,110,0.12);
}

.stat-number {
    font-size: 45px;

    font-weight: 1000;

    color: var(--purple);
}

/* =========================
   FOUNDERS
========================= */

.founders {
    max-width: 1100px;

    margin:
        40px auto 0;

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(300px,1fr)
        );

    gap: 30px;
}

.founder-card {
    overflow: hidden;

    background: white;

    border-radius: 25px;

    box-shadow:
        0 12px 35px
        rgba(75,20,110,0.16);

    border-top:
        5px solid
        var(--purple);

    transition: 0.25s;
}

.founder-card:hover {
    transform:
        translateY(-8px);
}

.founder-photo {
    display: block;

    width: 100%;

    height: 430px;

    object-fit: cover;

    background:
        #eee;

    /*
       Important:
       The photos are loaded directly from
       GitHub instead of relying on Flask's
       static path.
    */
}

.founder-info {
    padding: 28px;
}

.founder-info h3 {
    color: var(--purple);

    font-size: 25px;

    margin-bottom: 5px;
}

.founder-role {
    color:
        #8e44ad;

    font-weight: 800;

    margin-bottom: 15px;
}

/* =========================
   SERVICE
========================= */

.service {
    max-width: 1000px;

    margin: auto;

    padding: 50px 30px;

    text-align: center;

    border-radius: 30px;

    color: white;

    background:
        linear-gradient(
            135deg,
            #5a189a,
            #7b2cbf,
            #9d4edd
        );

    box-shadow:
        0 15px 40px
        rgba(75,20,110,0.2);
}

.service h2 {
    font-size:
        clamp(
            30px,
            5vw,
            45px
        );

    margin-bottom: 15px;
}

.service p {
    font-size: 20px;

    max-width: 750px;

    margin: auto;
}

/* =========================
   GALLERY
========================= */

.gallery {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(260px,1fr)
        );

    gap: 20px;

    margin-top: 35px;
}

.gallery-item {
    overflow: hidden;

    border-radius: 20px;

    background: white;

    box-shadow:
        0 10px 30px
        rgba(75,20,110,0.15);
}

.gallery-item img {
    display: block;

    width: 100%;

    height: 280px;

    object-fit: cover;

    transition:
        transform 0.3s;
}

.gallery-item:hover img {
    transform:
        scale(1.04);
}

.gallery-caption {
    padding: 15px;

    text-align: center;

    font-weight: 800;

    color: var(--purple);
}

/* =========================
   GAMES
========================= */

.games {
    padding:
        90px 25px;

    background:
        #f0e2ff;
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
    background: white;

    padding: 30px;

    text-align: center;

    border-radius: 25px;

    box-shadow:
        0 10px 30px
        rgba(75,20,110,0.14);
}

.game h3 {
    color: var(--purple);

    margin-bottom: 12px;
}

.game button {
    border: none;

    padding:
        12px 18px;

    margin: 5px;

    border-radius: 25px;

    cursor: pointer;

    background:
        linear-gradient(
            135deg,
            #7b2cbf,
            #9d4edd
        );

    color: white;

    font-weight: 800;
}

.game-result {
    margin-top: 15px;

    min-height: 30px;

    color: var(--purple);

    font-weight: 800;
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

    background: white;

    box-shadow:
        0 10px 35px
        rgba(75,20,110,0.15);
}

.contact h2 {
    color:
        var(--purple);

    font-size: 35px;
}

.contact a {
    color:
        var(--purple);

    font-weight: bold;
}

/* =========================
   FOOTER
========================= */

footer {
    padding:
        60px 20px;

    text-align: center;

    color: white;

    background:
        linear-gradient(
            135deg,
            #240046,
            #3c096c,
            #5a189a
        );
}

.footer-logo {
    font-size: 40px;

    font-weight: 1000;

    margin-bottom: 10px;
}

/* =========================
   VIEWER COUNTER
   EXACTLY AT BOTTOM
========================= */

.viewer-counter {
    margin-top: 20px;

    padding:
        15px 25px;

    display: inline-block;

    border-radius: 30px;

    background:
        rgba(255,255,255,0.14);

    border:
        1px solid
        rgba(255,255,255,0.25);

    color: white;

    font-weight: 800;

    font-size: 16px;
}

.viewer-counter span {
    color:
        #e0aaff;

    font-size: 20px;
}

/* =========================
   TOP BUTTON
========================= */

.top {
    position: fixed;

    bottom: 25px;

    right: 25px;

    width: 48px;

    height: 48px;

    border: none;

    border-radius: 50%;

    background:
        var(--purple);

    color: white;

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
        gap: 10px;
    }

    .nav-links a {
        font-size: 12px;
    }

    .hero {
        min-height: 650px;
    }

    .hero p {
        font-size: 17px;
    }

    .founder-photo {
        height: 380px;
    }

    .contact {
        padding: 30px 20px;
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

        <!-- DIRECT GITHUB IMAGE -->
        <img
            src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/OfficialLogo.png"
            alt="JHR Logo"
            width="48"
            height="48"
            loading="eager"
            decoding="async"
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
        <a href="#services">Services</a>
        <a href="#gallery">Gallery</a>
        <a href="#games">Games</a>
        <a href="#contact">Contact</a>

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

        <h1>JHR</h1>

        <h2>
            EMPOWERMENT THROUGH TECHNOLOGY
        </h2>

        <p>
            Turning technology, creativity and learning
            into opportunities for people and communities.
        </p>

        <div class="hero-buttons">

            <a
                class="button"
                href="#about"
            >
                ✨ Explore JHR
            </a>

            <a
                class="button"
                href="#services"
            >
                💻 Free Coding Classes
            </a>

        </div>

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
                We explore technology as a tool for
                creativity, learning and opportunity.
            </p>

        </div>


        <div class="card">

            <h3>
                📚 Education
            </h3>

            <p>
                Learning new skills helps young people
                turn ideas into real projects.
            </p>

        </div>


        <div class="card">

            <h3>
                🌱 Community
            </h3>

            <p>
                Technology can help communities connect,
                learn and grow.
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

    <p class="subtitle">
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
        Technology, education and community projects
        that turn ideas into action.
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
                🌱 Community
            </h3>

            <p>
                Activities designed to help communities
                learn, connect and grow.
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


<!-- =========================
     EXPERIENCE
========================= -->

<section
    class="section"
    id="experience"
>

    <h2 class="title">
        JHR Experience
    </h2>

    <p class="subtitle">
        Learning through technology, education
        and community activities.
    </p>

    <div class="cards">

        <div class="card">

            <h3>
                🌱 Community Experiences
            </h3>

            <p>
                Learning from communities and exploring
                how technology can be useful in everyday life.
            </p>

        </div>


        <div class="card">

            <h3>
                🏫 School Experiences
            </h3>

            <p>
                Exploring educational environments
                and learning about technology.
            </p>

        </div>


        <div class="card">

            <h3>
                💻 Technology Experiences
            </h3>

            <p>
                Building projects, experimenting with code
                and learning new technology skills.
            </p>

        </div>

    </div>

</section>


<!-- =========================
     FOUNDERS
========================= -->

<section
    class="section"
    id="founders"
>

    <h2 class="title">
        Meet the JHR Founders 👥
    </h2>

    <p class="subtitle">
        The founders behind JHR and its mission
        of empowerment through technology.
    </p>


    <div class="founders">


        <!-- =====================
             JOSE
        ====================== -->

        <div class="founder-card">

            <img
                class="founder-photo"
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner1.jpg"
                alt="Jose Hugo Rafael T. Tan"
                width="736"
                height="1000"
                loading="eager"
                decoding="async"
                fetchpriority="high"
            >

            <div class="founder-info">

                <h3>
                    Jose Hugo Rafael T. Tan
                </h3>

                <div class="founder-role">
                    Founder
                </div>

                <p>
                    Jose Hugo Rafael T. Tan helps guide
                    JHR's vision, projects and technology
                    activities through creativity,
                    learning and service.
                </p>

            </div>

        </div>


        <!-- =====================
             JULIA
        ====================== -->

        <div class="founder-card">

            <img
                class="founder-photo"
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner2.png"
                alt="Julia Helga Raquel T. Tan"
                width="736"
                height="1000"
                loading="eager"
                decoding="async"
            >

            <div class="founder-info">

                <h3>
                    Julia Helga Raquel T. Tan
                </h3>

                <div class="founder-role">
                    Founder
                </div>

                <p>
                    Julia Helga Raquel T. Tan supports
                    JHR's creativity, learning and
                    technology activities and helps
                    inspire positive community impact.
                </p>

            </div>

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

    <div class="service">

        <h2>
            💻 Our Service Offer
        </h2>

        <p>
            <strong>
                We provide free coding classes.
            </strong>
        </p>

        <br>

        <p>
            JHR provides free opportunities for people
            to learn coding, technology and digital
            skills in a friendly and creative environment.
        </p>

    </div>

</section>


<!-- =========================
     GALLERY
========================= -->

<section
    class="section"
    id="gallery"
>

    <h2 class="title">
        JHR Gallery 📸
    </h2>

    <p class="subtitle">
        Moments from JHR's technology,
        education and community activities.
    </p>


    <div class="gallery">


        <!-- FOUNDER PHOTO -->

        <div class="gallery-item">

            <img
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner1.jpg"
                alt="JHR Founder"
                width="736"
                height="1000"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">
                JHR Founder
            </div>

        </div>


        <!-- FOUNDER PHOTO -->

        <div class="gallery-item">

            <img
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner2.png"
                alt="JHR Founder"
                width="736"
                height="1000"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">
                JHR Founder
            </div>

        </div>


        <!-- COMMUNITY -->

        <div class="gallery-item">

            <img
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner1.jpg"
                alt="JHR Community"
                width="736"
                height="1000"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">
                Technology & Community
            </div>

        </div>


        <!-- EDUCATION -->

        <div class="gallery-item">

            <img
                src="https://raw.githubusercontent.com/HugoHasArrived/JHR-Website/main/static/Owner2.png"
                alt="JHR Education"
                width="736"
                height="1000"
                loading="lazy"
                decoding="async"
            >

            <div class="gallery-caption">
                Education & Learning
            </div>

        </div>


    </div>

</section>


<!-- =========================
     GAMES
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
                Choose!
            </div>

        </div>


        <div class="game">

            <h3>
                💻 Technology
            </h3>

            <p>
                Is coding a technology skill?
            </p>

            <button
                onclick="techGame(true)"
            >
                Yes
            </button>

            <button
                onclick="techGame(false)"
            >
                No
            </button>

            <div
                id="techResult"
                class="game-result"
            >
                Choose!
            </div>

        </div>


        <div class="game">

            <h3>
                🔢 Guess the Number
            </h3>

            <p>
                Guess a number from 1 to 5.
            </p>

            <button onclick="guessGame(1)">
                1
            </button>

            <button onclick="guessGame(2)">
                2
            </button>

            <button onclick="guessGame(3)">
                3
            </button>

            <button onclick="guessGame(4)">
                4
            </button>

            <button onclick="guessGame(5)">
                5
            </button>

            <div
                id="guessResult"
                class="game-result"
            >
                Choose!
            </div>

        </div>


        <div class="game">

            <h3>
                🌱 Community
            </h3>

            <p>
                Does helping your community matter?
            </p>

            <button
                onclick="communityGame(true)"
            >
                Yes
            </button>

            <button
                onclick="communityGame(false)"
            >
                No
            </button>

            <div
                id="communityResult"
                class="game-result"
            >
                Choose!
            </div>

        </div>


    </div>

</section>


<!-- =========================
     CONTACT
========================= -->

<section
    class="section"
    id="contact"
>

    <div class="contact">

        <h2>
            JHR
        </h2>

        <br>

        <p>
            <strong>
                Join us in this journey!
            </strong>
        </p>

        <br>

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

    <br>

    <p>
        Technology • Education • Innovation • Community
    </p>

    <br>

    <p>
        Join the JHR Journey 🚀
    </p>

    <p>
        Technology • Education • Innovation • Community
    </p>

    <p>
        Learn. Create. Share. Empower.
    </p>


    <!-- =========================
         VIEWER COUNTER
         EXACTLY BELOW THE TEXT
    ========================== -->

    <div
        class="viewer-counter"
        id="viewerCounter"
    >
        👁️ Visitors:
        <span id="visitorNumber">
            0
        </span>
    </div>


    <br>
    <br>

    <p>
        © 2026 JHR
    </p>

</footer>


<!-- =========================
     TOP BUTTON
========================= -->

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

/* =========================
   VIEWER COUNTER
========================= */

(function() {

    const key = "jhr_viewer_count";

    let count =
        Number(
            localStorage.getItem(key)
        ) || 0;

    count++;

    localStorage.setItem(
        key,
        count
    );

    const element =
        document.getElementById(
            "visitorNumber"
        );

    if (element) {

        element.textContent =
            count.toLocaleString();

    }

})();


/* =========================
   MATH GAME
========================= */

function mathGame(answer) {

    const result =
        document.getElementById(
            "mathResult"
        );

    if (answer === 96) {

        result.textContent =
            "🎉 CORRECT!";

    } else {

        result.textContent =
            "❌ Try again!";

    }

}


/* =========================
   TECHNOLOGY GAME
========================= */

function techGame(correct) {

    const result =
        document.getElementById(
            "techResult"
        );

    result.textContent =
        correct
        ? "🚀 Correct!"
        : "❌ Try again!";

}


/* =========================
   COMMUNITY GAME
========================= */

function communityGame(correct) {

    const result =
        document.getElementById(
            "communityResult"
        );

    result.textContent =
        correct
        ? "🌟 Correct! Community matters!"
        : "❌ Try again!";

}


/* =========================
   GUESS GAME
========================= */

let secretNumber =
    Math.floor(
        Math.random() * 5
    ) + 1;


function guessGame(number) {

    const result =
        document.getElementById(
            "guessResult"
        );

    if (number === secretNumber) {

        result.textContent =
            "🏆 AMAZING! You guessed it!";

        secretNumber =
            Math.floor(
                Math.random() * 5
            ) + 1;

    } else {

        result.textContent =
            "❌ Nope! Try again.";

    }

}


/* =========================
   TOP BUTTON
========================= */

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


/* =========================
   IMAGE ERROR PROTECTION
========================= */

document
    .querySelectorAll("img")
    .forEach(function(image) {

        image.addEventListener(
            "error",
            function() {

                console.log(
                    "JHR image failed:",
                    image.src
                );

            }
        );

    });

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
        port=5000,
        debug=False
    )
