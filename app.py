from flask import Flask, render_template_string
import webbrowser
import threading

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
<a href="#owners">Owners</a>
<a href="#games">Games</a>
<a href="#contact">Contact</a>

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


<!-- =========================
     OWNERS
========================= -->

<section class="section" id="owners">

<h2 class="title">
Meet the JHR Owners 👥
</h2>

<p class="subtitle">
The people behind JHR and its mission of
empowerment through technology.
</p>

<div class="owners">

<!-- OWNER 1 -->

<div class="owner-card">

<img
class="owner-photo"
src="{{ url_for('static', filename='Owner1.jpg') }}"
alt="JHR Owner 1"
>

<div class="owner-info">

<h3
data-en="JHR Owner 1"
data-fil="May-ari ng JHR 1"
>
JHR Owner 1
</h3>

<div
class="owner-role"
data-en="Founder / Owner"
data-fil="Tagapagtatag / May-ari"
>
Founder / Owner
</div>

<p
data-en="The founder helps guide JHR's vision, projects and technology-focused activities. Through creativity, learning and service, the goal is to help people discover opportunities through technology."
data-fil="Tumutulong ang tagapagtatag na gabayan ang pananaw, mga proyekto at mga aktibidad ng JHR na nakatuon sa teknolohiya. Sa pamamagitan ng pagkamalikhain, pagkatuto at paglilingkod, layunin nitong makatulong sa mga tao na makahanap ng mga oportunidad gamit ang teknolohiya."
>
The founder helps guide JHR's vision, projects and technology-focused activities. Through creativity, learning and service, the goal is to help people discover opportunities through technology.
</p>

</div>

</div>


<!-- OWNER 2 -->

<div class="owner-card">

<img
class="owner-photo"
src="{{ url_for('static', filename='Owner2.png') }}"
alt="JHR Owner 2"
>

<div class="owner-info">

<h3
data-en="JHR Owner 2"
data-fil="May-ari ng JHR 2"
>
JHR Owner 2
</h3>

<div
class="owner-role"
data-en="Co-Founder / Owner"
data-fil="Co-Founder / May-ari"
>
Co-Founder / Owner
</div>

<p
data-en="The co-founder supports JHR's projects, creativity and technology activities. Together, the owners work to develop ideas that can inspire learning, innovation and positive community impact."
data-fil="Sinusuportahan ng co-founder ang mga proyekto, pagkamalikhain at mga aktibidad sa teknolohiya ng JHR. Sama-sama, nagsisikap ang mga may-ari na bumuo ng mga ideyang makapagbibigay-inspirasyon sa pagkatuto, inobasyon at positibong epekto sa komunidad."
>
The co-founder supports JHR's projects, creativity and technology activities. Together, the owners work to develop ideas that can inspire learning, innovation and positive community impact.
</p>

</div>

</div>

</div>

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
    return render_template_string(HTML)


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


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
        host="127.0.0.1",
        port=5000,
        debug=False
    )