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
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>JHR | Empowerment Through Technology</title>

<style>

*{
    box-sizing:border-box;
    margin:0;
    padding:0;
    scroll-behavior:smooth;
}

:root{
    --purple:#7c3aed;
    --dark-purple:#4c1d95;
    --deep-purple:#2e1065;
    --light-purple:#ede9fe;
    --background:#faf7ff;
    --card:#ffffff;
    --text:#24113f;
    --muted:#6b5b82;
}

body{
    font-family:Arial,Helvetica,sans-serif;
    background:var(--background);
    color:var(--text);
    line-height:1.6;
}

/* ================= NAVIGATION ================= */

nav{
    position:sticky;
    top:0;
    z-index:1000;

    display:flex;
    align-items:center;
    justify-content:space-between;

    gap:15px;
    padding:10px 24px;

    background:#ffffff;

    box-shadow:0 5px 25px rgba(0,0,0,.15);
}

.logo{
    display:flex;
    align-items:center;
    gap:9px;

    font-size:25px;
    font-weight:900;

    color:var(--purple);
}

.logo img{
    width:48px;
    height:48px;

    object-fit:contain;
}

.nav-links{
    display:flex;
    align-items:center;
    justify-content:center;

    gap:12px;
    flex-wrap:wrap;
}

.nav-links a{
    color:var(--text);
    text-decoration:none;

    font-size:13px;
    font-weight:700;
}

.nav-links a:hover{
    color:var(--purple);
}

.nav-btn{
    border:0;
    border-radius:20px;

    padding:8px 12px;

    color:white;
    background:var(--purple);

    cursor:pointer;
    font-weight:700;
}

.lang-btn{
    min-width:42px;
}

/* ================= HERO ================= */

.hero{
    min-height:690px;

    display:flex;
    align-items:center;
    justify-content:center;

    text-align:center;

    color:white;

    padding:70px 20px;

    background:
        linear-gradient(
            135deg,
            #4c1d95,
            #7c3aed 55%,
            #581c87
        );
}

.hero-content{
    max-width:1050px;
}

.badge{
    display:inline-block;

    padding:10px 19px;

    border:1px solid rgba(255,255,255,.4);
    border-radius:30px;

    background:rgba(255,255,255,.12);

    font-weight:800;

    margin-bottom:20px;
}

.hero h1{
    font-size:clamp(76px,14vw,155px);

    line-height:.85;

    letter-spacing:8px;

    font-weight:1000;
}

.hero h2{
    font-size:clamp(22px,4vw,42px);

    margin:25px 0 15px;
}

.hero p{
    max-width:780px;

    margin:auto;

    font-size:19px;

    color:#f4edff;
}

.button{
    display:inline-block;

    margin:25px 7px 0;

    padding:13px 22px;

    border-radius:28px;

    background:white;
    color:var(--purple);

    text-decoration:none;

    font-weight:900;
}

.button.purple{
    background:#a78bfa;
    color:white;
}

/* ================= SECTIONS ================= */

.section{
    max-width:1180px;

    margin:0 auto;

    padding:85px 22px;
}

.title{
    text-align:center;

    font-size:42px;

    margin-bottom:12px;
}

.subtitle{
    text-align:center;

    max-width:780px;

    margin:0 auto 42px;

    color:var(--muted);

    font-size:18px;
}

/* ================= CARDS ================= */

.cards{
    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:20px;
}

.card{
    background:var(--card);

    border-radius:22px;

    padding:27px;

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.card h3{
    margin-bottom:10px;

    color:var(--purple);
}

.card p{
    color:var(--muted);
}

/* ================= MISSION ================= */

.color-section{
    padding:85px 22px;

    background:
        linear-gradient(
            135deg,
            #4c1d95,
            #7c3aed
        );

    color:white;
}

.color-section .title{
    color:white;
}

.mission{
    max-width:1180px;

    margin:auto;

    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:20px;
}

.mission-card{
    padding:27px;

    border-radius:22px;

    background:
        rgba(255,255,255,.1);

    border:
        1px solid
        rgba(255,255,255,.2);
}

.mission-card p{
    color:#eee7ff;
}

.mission-icon{
    font-size:40px;

    margin-bottom:10px;
}

/* ================= STATS ================= */

.stats{
    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:20px;
}

.stat{
    padding:30px;

    text-align:center;

    background:white;

    border-radius:22px;

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.stat-number{
    font-size:48px;

    font-weight:1000;

    color:var(--purple);
}

/* ================= SERVICES ================= */

.services{
    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:20px;
}

.service-card{
    padding:30px;

    background:white;

    border-radius:22px;

    border-top:
        5px solid
        var(--purple);

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.service-icon{
    font-size:42px;

    margin-bottom:12px;
}

.service-card h3{
    color:var(--purple);

    margin-bottom:10px;
}

.service-card p{
    color:var(--muted);
}

.free{
    display:inline-block;

    margin-top:16px;

    padding:6px 11px;

    border-radius:20px;

    background:var(--light-purple);

    color:var(--purple);

    font-weight:900;

    font-size:12px;
}

/* ================= GALLERY ================= */

.gallery-grid{
    display:grid;

    grid-template-columns:
        repeat(2,1fr);

    gap:24px;
}

.gallery-card{
    background:white;

    border-radius:22px;

    overflow:hidden;

    border:
        1px solid
        #ddd0ff;

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.gallery-card img{
    display:block;

    width:100%;

    height:330px;

    object-fit:cover;

    background:#ede9fe;
}

.gallery-caption{
    padding:20px;
}

.gallery-caption p{
    color:var(--muted);
}

/* ================= FOUNDERS ================= */

.owners{
    display:grid;

    grid-template-columns:
        repeat(2,1fr);

    gap:28px;
}

.owner-card{
    display:grid;

    grid-template-columns:
        180px 1fr;

    background:white;

    border-radius:22px;

    overflow:hidden;

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.owner-photo{
    width:180px;

    height:100%;

    min-height:310px;

    object-fit:cover;

    background:#ede9fe;
}

.owner-info{
    padding:25px;
}

.owner-info h3{
    font-size:22px;

    margin-bottom:5px;
}

.owner-role{
    display:inline-block;

    padding:5px 12px;

    border-radius:20px;

    background:#ede9fe;

    color:var(--purple);

    font-weight:900;

    margin-bottom:15px;
}

.owner-info p{
    color:var(--muted);
}

/* ================= GAMES ================= */

.games{
    padding:85px 22px;

    background:#ede9fe;
}

.game-grid{
    max-width:1100px;

    margin:auto;

    display:grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:20px;
}

.game{
    padding:25px;

    background:white;

    border-radius:22px;

    box-shadow:
        0 14px 40px
        rgba(76,29,149,.16);
}

.game h3{
    color:var(--purple);

    margin-bottom:10px;
}

.game p{
    color:var(--muted);
}

.game button{
    margin:6px 3px;

    padding:9px 13px;

    border:0;

    border-radius:12px;

    background:var(--purple);

    color:white;

    cursor:pointer;

    font-weight:800;
}

.game-result{
    margin-top:10px;

    font-weight:800;
}

/* ================= CONTACT ================= */

.contact{
    text-align:center;

    background:var(--dark-purple);

    color:white;

    padding:75px 22px;
}

.contact p{
    color:#eee7ff;

    margin:10px 0;
}

/* ================= VIEWER ================= */

.viewer-counter{
    text-align:center;

    padding:18px 20px 30px;

    background:var(--deep-purple);

    color:white;

    font-size:16px;

    font-weight:700;
}

/* ================= FOOTER ================= */

footer{
    text-align:center;

    padding:25px;

    background:var(--deep-purple);

    color:#eee7ff;
}

/* ================= DARK MODE ================= */

body.dark{
    background:#16052d;

    --card:#21103b;
    --text:#faf7ff;
    --muted:#d5c9e8;
}

body.dark nav{
    background:#17062d;
}

body.dark .nav-links a{
    color:#faf7ff;
}

body.dark .games{
    background:#21103b;
}

body.dark .card,
body.dark .stat,
body.dark .service-card,
body.dark .owner-card,
body.dark .game,
body.dark .gallery-card{
    background:#21103b;
}

/* ================= MOBILE ================= */

@media(max-width:950px){

    .cards,
    .mission,
    .services,
    .game-grid{
        grid-template-columns:
            repeat(2,1fr);
    }

    .owners{
        grid-template-columns:1fr;
    }
}

@media(max-width:700px){

    nav{
        flex-direction:column;

        padding:12px;
    }

    .nav-links{
        gap:8px;
    }

    .nav-links a{
        font-size:11px;
    }

    .hero{
        min-height:620px;
    }

    .gallery-grid,
    .cards,
    .mission,
    .services,
    .game-grid,
    .stats{
        grid-template-columns:1fr;
    }

    .owner-card{
        grid-template-columns:1fr;
    }

    .owner-photo{
        width:100%;

        height:330px;
    }

    .title{
        font-size:34px;
    }
}

</style>
</head>

<body>

<nav>

<div class="logo">

<img
    src="/static/OfficialLogo.png"
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

<button
    class="nav-btn"
    id="themeBtn"
    onclick="toggleTheme()"
>
🌙
</button>

<button
    class="nav-btn lang-btn"
    id="langBtn"
    onclick="toggleLanguage()"
>
EN
</button>

</div>

</nav>


<section class="hero" id="home">

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

<a class="button" href="#about">
✨ Explore JHR
</a>

<a class="button purple" href="#services">
💻 Free Coding Classes
</a>

</div>

</section>


<section class="section" id="about">

<h2 class="title">
What is JHR?
</h2>

<p class="subtitle">
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
<h3>📚 Education</h3>
<p>
We encourage people to learn useful digital
and technology skills.
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
<h3>💡 Innovation</h3>
<p>
Every big project starts with an idea and
the courage to try.
</p>
</div>

</div>

</section>


<section class="color-section" id="mission">

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
Encourage people to learn digital
and technology skills.
</p>
</div>

<div class="mission-card">
<div class="mission-icon">🌍</div>
<h3>Community</h3>
<p>
Explore ways technology can create
positive community impact.
</p>
</div>

<div class="mission-card">
<div class="mission-icon">🚀</div>
<h3>Innovation</h3>
<p>
Turn creative ideas into useful projects
and experiences.
</p>
</div>

</div>

</section>


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


<section class="section" id="projects">

<h2 class="title">
JHR Projects 🚀
</h2>

<p class="subtitle">
Technology, education and community projects
designed around learning and positive impact.
</p>

<div class="cards">

<div class="card">
<h3>💻 Technology Projects</h3>
<p>
Websites, digital tools, programming,
creative technology and experiments.
</p>
</div>

<div class="card">
<h3>🏫 Education</h3>
<p>
Technology-related learning activities
and educational experiences.
</p>
</div>

<div class="card">
<h3>🌾 Community & Agriculture</h3>
<p>
Exploring how technology can support
communities and agricultural areas.
</p>
</div>

<div class="card">
<h3>🚀 Future Projects</h3>
<p>
More JHR projects will be added as new
initiatives are completed.
</p>
</div>

</div>

</section>


<section class="section" id="services">

<h2 class="title">
JHR Services 💻🎓
</h2>

<p class="subtitle">
We provide learning opportunities that help
people discover technology and build useful skills.
</p>

<div class="services">

<div class="service-card">

<div class="service-icon">💻</div>

<h3>
Free Coding Classes
</h3>

<p>
We provide <strong>free coding classes</strong>
for beginners and learners who want to
start programming.
</p>

<span class="free">
FREE
</span>

</div>

<div class="service-card">

<div class="service-icon">🌐</div>

<h3>
Web Development
</h3>

<p>
Learn the basics of building websites
using HTML, CSS and JavaScript.
</p>

</div>

<div class="service-card">

<div class="service-icon">🚀</div>

<h3>
Learn by Building
</h3>

<p>
Practice technology by creating simple
projects and turning ideas into working experiences.
</p>

</div>

<div class="service-card">

<div class="service-icon">🌱</div>

<h3>
Technology Skills
</h3>

<p>
Develop practical digital skills that can
support school, projects and future opportunities.
</p>

</div>

</div>

</section>


<section class="section" id="gallery">

<h2 class="title">
JHR Gallery 📸
</h2>

<p class="subtitle">
Moments of learning, teamwork, technology and community.
</p>

<div class="gallery-grid">

<div class="gallery-card">

<img
    src="/static/gallery_classroom.png"
    alt="JHR classroom technology activity"
>

<div class="gallery-caption">

<h3>
💻 Technology in Action
</h3>

<p>
Learning, collaboration and technology
in a classroom environment.
</p>

</div>

</div>


<div class="gallery-card">

<img
    src="/static/gallery_children_learning.jpeg"
    alt="JHR learning activity with children"
>

<div class="gallery-caption">

<h3>
🤝 Learning Together
</h3>

<p>
A community learning activity focused
on teamwork and education.
</p>

</div>

</div>


<div class="gallery-card">

<img
    src="/static/gallery_school.jpeg"
    alt="JHR school community"
>

<div class="gallery-caption">

<h3>
🏫 School Community
</h3>

<p>
Connecting learning, education and young people.
</p>

</div>

</div>


<div class="gallery-card">

<img
    src="/static/gallery_community.jpeg"
    alt="JHR community activity"
>

<div class="gallery-caption">

<h3>
🌱 Community Activity
</h3>

<p>
A community moment centered on learning,
participation and service.
</p>

</div>

</div>

</div>

</section>


<section class="section" id="founders">

<h2 class="title">
JHR Team 👥
</h2>

<p class="subtitle">
The founders behind JHR and its mission
of empowerment through technology.
</p>

<div class="owners">

<div class="owner-card">

<img
    class="owner-photo"
    src="/static/Jose_Hugo_Rafael_T_Tan.jpg"
    alt="Jose Hugo Rafael T. Tan"
>

<div class="owner-info">

<h3>
Jose Hugo Rafael T. Tan
</h3>

<div class="owner-role">
Founder
</div>

<p>
Helps guide JHR's vision, projects and
technology-focused activities through
creativity, learning and service.
</p>

</div>

</div>


<div class="owner-card">

<img
    class="owner-photo"
    src="/static/Julia_Helga_Raquel_T_Tan.png"
    alt="Julia Helga Raquel T. Tan"
>

<div class="owner-info">

<h3>
Julia Helga Raquel T. Tan
</h3>

<div class="owner-role">
Founder
</div>

<p>
Supports JHR's projects, creativity and
technology activities while helping develop
ideas for learning and community impact.
</p>

</div>

</div>

</div>

</section>


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

<p>
What is 12 × 8?
</p>

<button onclick="mathGame(96)">
96
</button>

<button onclick="mathGame(88)">
88
</button>

<button onclick="mathGame(108)">
108
</button>

<div id="mathResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🧠 Tech Quiz</h3>

<p>
What does CPU mean?
</p>

<button onclick="techGame(true)">
Central Processing Unit
</button>

<button onclick="techGame(false)">
Computer Power Utility
</button>

<div id="techResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🔐 Online Safety</h3>

<p>
Should you share your password?
</p>

<button onclick="safetyGame(false)">
Yes
</button>

<button onclick="safetyGame(true)">
No
</button>

<div id="safetyResult" class="game-result">
Choose an answer!
</div>

</div>


<div class="game">

<h3>🤝 JHR Values</h3>

<p>
What helps a team succeed?
</p>

<button onclick="valuesGame(true)">
Cooperation
</button>

<button onclick="valuesGame(false)">
Giving up
</button>

<div id="valuesResult" class="game-result">
Choose an answer!
</div>

</div>

</div>

</section>


<section class="contact" id="contact">

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


<div class="viewer-counter">

👀 <strong>{{ viewer_count }}</strong> viewers

</div>


<footer>

<p>
© 2026 JHR — Empowerment Through Technology
</p>

<p>
Technology • Education • Innovation • Community
</p>

</footer>


<script>

const translations = {

    en:{
        home:"Home",
        about:"About",
        mission:"Mission",
        projects:"Projects",
        services:"Services",
        gallery:"Gallery",
        founders:"Founders",
        games:"Games",
        contact:"Contact",
        free:"💻 Free Coding Classes"
    },

    tl:{
        home:"Home",
        about:"Tungkol",
        mission:"Misyon",
        projects:"Mga Proyekto",
        services:"Serbisyo",
        gallery:"Gallery",
        founders:"Mga Founder",
        games:"Mga Laro",
        contact:"Kontak",
        free:"💻 Libreng Coding Classes"
    }

};


let currentLanguage =
    localStorage.getItem("jhrLanguage") || "en";


function toggleTheme(){

    document.body.classList.toggle("dark");

    const dark =
        document.body.classList.contains("dark");

    localStorage.setItem(
        "jhrTheme",
        dark ? "dark" : "light"
    );

    document.getElementById("themeBtn").textContent =
        dark ? "☀️" : "🌙";
}


function applySavedTheme(){

    const saved =
        localStorage.getItem("jhrTheme");

    if(saved === "dark"){

        document.body.classList.add("dark");

        document.getElementById("themeBtn").textContent =
            "☀️";
    }
}


function toggleLanguage(){

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


function applyLanguage(){

    const t =
        translations[currentLanguage];

    const ids=[
        "home",
        "about",
        "mission",
        "projects",
        "services",
        "gallery",
        "founders",
        "games",
        "contact"
    ];

    ids.forEach(function(id){

        const link =
            document.querySelector(
                '.nav-links a[href="#' +
                id +
                '"]'
            );

        if(link){
            link.textContent=t[id];
        }

    });


    const freeButton =
        document.querySelector(
            ".hero .button.purple"
        );

    if(freeButton){
        freeButton.textContent=t.free;
    }


    document.getElementById("langBtn").textContent =
        currentLanguage === "en"
            ? "EN"
            : "TL";
}


function mathGame(answer){

    document.getElementById(
        "mathResult"
    ).textContent =
        answer === 96
            ? "🎉 Correct!"
            : "❌ Try again!";
}


function techGame(correct){

    document.getElementById(
        "techResult"
    ).textContent =
        correct
            ? "💡 Correct!"
            : "❌ Try again!";
}


function safetyGame(correct){

    document.getElementById(
        "safetyResult"
    ).textContent =
        correct
            ? "🔐 Correct! Keep passwords private."
            : "❌ Never share your password!";
}


function valuesGame(correct){

    document.getElementById(
        "valuesResult"
    ).textContent =
        correct
            ? "🤝 Correct! Cooperation matters!"
            : "❌ Try again!";
}


document.addEventListener(
    "DOMContentLoaded",
    function(){

        applySavedTheme();

        applyLanguage();

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
        "gallery_school.jpeg",
        "gallery_community.jpeg"
    ]

    result=[]

    for name in files:

        path=os.path.join(
            app.static_folder,
            name
        )

        result.append(
            f"{name}: "
            f"{'OK' if os.path.isfile(path) else 'MISSING'}"
        )

    return "<br>".join(result)


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
