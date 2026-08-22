from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JHR | Empowerment Through Technology</title>

<style>
*{box-sizing:border-box;margin:0;padding:0;scroll-behavior:smooth}

:root{
 --blue:#1264ff;
 --cyan:#18c9ff;
 --navy:#102a63;
 --yellow:#ffc928;
 --green:#159447;
 --bg:#f5f9ff;
 --card:#fff;
 --text:#102044;
 --muted:#61708c;
 --shadow:0 14px 45px rgba(16,42,99,.13)
}

body.dark{
 --bg:#071326;
 --card:#0e1e38;
 --text:#f4f8ff;
 --muted:#bdc8da
}

body{
 font-family:Arial,Helvetica,sans-serif;
 background:var(--bg);
 color:var(--text);
 line-height:1.6
}

nav{
 position:sticky;
 top:0;
 z-index:1000;
 display:flex;
 align-items:center;
 justify-content:space-between;
 gap:18px;
 padding:10px 24px;
 background:rgba(255,255,255,.96);
 box-shadow:0 5px 25px rgba(0,0,0,.12);
 backdrop-filter:blur(14px)
}

body.dark nav{
 background:rgba(8,21,40,.96)
}

.logo{
 display:flex;
 align-items:center;
 gap:9px;
 font-size:25px;
 font-weight:900;
 color:var(--blue)
}

.logo img{
 width:48px;
 height:48px;
 object-fit:contain
}

.nav-links{
 display:flex;
 align-items:center;
 justify-content:center;
 gap:13px;
 flex-wrap:wrap
}

.nav-links a{
 color:var(--text);
 text-decoration:none;
 font-size:13px;
 font-weight:700
}

.nav-links a:hover{
 color:var(--blue)
}

.nav-btn{
 border:0;
 border-radius:20px;
 padding:8px 12px;
 color:#fff;
 background:var(--blue);
 cursor:pointer;
 font-weight:700
}

.hero{
 min-height:690px;
 display:flex;
 align-items:center;
 justify-content:center;
 text-align:center;
 color:#fff;
 padding:70px 20px;
 position:relative;
 overflow:hidden;
 background:
 radial-gradient(
  circle at 15% 20%,
  rgba(24,201,255,.35),
  transparent 25%
 ),
 radial-gradient(
  circle at 85% 25%,
  rgba(255,201,40,.28),
  transparent 25%
 ),
 linear-gradient(
  135deg,
  #061c52,
  #1264ff 52%,
  #08275f
 )
}

.hero:before,
.hero:after{
 content:"";
 position:absolute;
 border-radius:50%;
 filter:blur(2px);
 opacity:.25
}

.hero:before{
 width:420px;
 height:420px;
 background:#18c9ff;
 left:-180px;
 bottom:-180px
}

.hero:after{
 width:420px;
 height:420px;
 background:#ffc928;
 right:-180px;
 top:-180px
}

.hero-content{
 max-width:1050px;
 position:relative;
 z-index:2
}

.badge{
 display:inline-block;
 padding:10px 19px;
 border:1px solid rgba(255,255,255,.4);
 border-radius:30px;
 background:rgba(255,255,255,.12);
 font-weight:800;
 color:#fff;
 margin-bottom:20px
}

.hero h1{
 font-size:clamp(76px,14vw,155px);
 line-height:.85;
 letter-spacing:8px;
 font-weight:1000
}

.hero h2{
 font-size:clamp(22px,4vw,42px);
 margin:25px 0 15px
}

.hero p{
 max-width:780px;
 margin:auto;
 font-size:19px;
 color:#eaf4ff
}

.button{
 display:inline-block;
 margin:25px 7px 0;
 padding:13px 22px;
 border-radius:28px;
 background:#fff;
 color:#1264ff;
 text-decoration:none;
 font-weight:900
}

.button.yellow{
 background:var(--yellow);
 color:#102044
}

.section{
 max-width:1180px;
 margin:auto;
 padding:85px 22px
}

.title{
 text-align:center;
 font-size:42px;
 margin-bottom:12px;
 color:var(--text)
}

.subtitle{
 text-align:center;
 max-width:780px;
 margin:0 auto 42px;
 color:var(--muted);
 font-size:18px
}

.cards{
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:20px
}

.card,
.service-card,
.mission-card,
.game,
.owner-card,
.gallery-card{
 background:var(--card);
 border-radius:22px;
 box-shadow:var(--shadow);
 overflow:hidden
}

.card{
 padding:27px
}

.card h3{
 margin-bottom:10px;
 color:var(--blue)
}

.card p,
.service-card p,
.mission-card p,
.game p,
.owner-info p{
 color:var(--muted)
}

.color-section{
 padding:85px 22px;
 background:linear-gradient(135deg,#08255e,#1264ff);
 color:#fff
}

.color-section .title{
 color:#fff
}

.mission{
 max-width:1180px;
 margin:auto;
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:20px
}

.mission-card{
 padding:27px;
 background:rgba(255,255,255,.1);
 color:#fff;
 border:1px solid rgba(255,255,255,.2)
}

.mission-card p{
 color:#e7efff
}

.mission-icon{
 font-size:40px;
 margin-bottom:10px
}

.stats{
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:20px
}

.stat{
 background:var(--card);
 padding:30px;
 text-align:center;
 border-radius:20px;
 box-shadow:var(--shadow)
}

.stat-number{
 font-size:48px;
 font-weight:1000;
 color:var(--blue)
}

.services{
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:20px
}

.service-card{
 padding:30px;
 border-top:5px solid var(--blue)
}

.service-icon{
 font-size:42px;
 margin-bottom:12px
}

.service-card h3{
 margin-bottom:10px
}

.free{
 display:inline-block;
 margin-top:16px;
 padding:6px 11px;
 border-radius:20px;
 background:#e5f8ec;
 color:var(--green);
 font-weight:900;
 font-size:12px
}

.gallery-grid{
 display:grid;
 grid-template-columns:repeat(2,1fr);
 gap:24px
}

.gallery-card{
 border:1px solid rgba(18,100,255,.1)
}

.gallery-card img{
 display:block;
 width:100%;
 height:330px;
 object-fit:cover
}

.gallery-caption{
 padding:20px
}

.gallery-caption h3{
 margin-bottom:6px
}

.gallery-caption p{
 color:var(--muted)
}

.owners{
 display:grid;
 grid-template-columns:repeat(2,1fr);
 gap:28px
}

.owner-card{
 display:grid;
 grid-template-columns:180px 1fr
}

.owner-photo{
 width:180px;
 height:100%;
 min-height:310px;
 object-fit:cover
}

.owner-info{
 padding:25px
}

.owner-info h3{
 font-size:22px;
 margin-bottom:5px
}

.owner-role{
 display:inline-block;
 padding:5px 12px;
 border-radius:20px;
 background:#e9f1ff;
 color:var(--blue);
 font-weight:900;
 margin-bottom:15px
}

.games{
 padding:85px 22px;
 background:#eef5ff
}

.game-grid{
 max-width:1100px;
 margin:auto;
 display:grid;
 grid-template-columns:repeat(4,1fr);
 gap:20px
}

.game{
 padding:25px
}

.game h3{
 margin-bottom:12px;
 color:var(--blue)
}

.game button{
 margin:6px 3px;
 padding:9px 13px;
 border:0;
 border-radius:12px;
 background:var(--blue);
 color:#fff;
 cursor:pointer;
 font-weight:800
}

.game-result{
 margin-top:10px;
 font-weight:800
}

.contact{
 text-align:center;
 background:var(--navy);
 color:#fff;
 padding:75px 22px
}

.contact p{
 color:#dce8ff;
 margin:10px 0
}

footer{
 text-align:center;
 padding:25px;
 background:#061633;
 color:#cddcff
}

.top{
 position:fixed;
 right:20px;
 bottom:20px;
 display:none;
 border:0;
 border-radius:50%;
 width:48px;
 height:48px;
 background:var(--blue);
 color:#fff;
 font-size:20px;
 cursor:pointer;
 z-index:900
}

@media(max-width:950px){
 .cards,
 .mission,
 .services,
 .game-grid{
  grid-template-columns:repeat(2,1fr)
 }

 .owners{
  grid-template-columns:1fr
 }
}

@media(max-width:700px){
 nav{
  flex-direction:column;
  padding:12px
 }

 .nav-links{
  gap:8px
 }

 .nav-links a{
  font-size:11px
 }

 .hero{
  min-height:620px
 }

 .gallery-grid,
 .cards,
 .mission,
 .services,
 .game-grid,
 .stats{
  grid-template-columns:1fr
 }

 .owner-card{
  grid-template-columns:1fr
 }

 .owner-photo{
  width:100%;
  height:330px
 }

 .title{
  font-size:34px
 }
}
</style>
</head>

<body>

<nav>

<div class="logo">

<img
src="{{ url_for('static_files', filename='OfficialLogo.png') }}"
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
onclick="toggleDark()"
>
🌙
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

<a class="button yellow" href="#services">
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
Every big project starts with an idea
and the courage to try.
</p>
</div>

</div>

</section>


<section class="color-section" id="mission">

<h2 class="title">
Our Mission
</h2>

<p class="subtitle" style="color:#dce8ff">
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
for beginners and learners who want to start programming.
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
Learn the basics of building websites using
HTML, CSS and JavaScript.
</p>

</div>


<div class="service-card">

<div class="service-icon">🚀</div>

<h3>
Learn by Building
</h3>

<p>
Practice technology by creating simple projects
and turning ideas into working experiences.
</p>

</div>


<div class="service-card">

<div class="service-icon">🌱</div>

<h3>
Technology Skills
</h3>

<p>
Develop practical digital skills that can support
school, projects and future opportunities.
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
src="{{ url_for('static_files', filename='gallery_classroom.png') }}"
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
src="{{ url_for('static_files', filename='gallery_children_learning.jpeg') }}"
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
src="{{ url_for('static_files', filename='gallery_school.jpeg') }}"
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
src="{{ url_for('static_files', filename='gallery_community.jpeg') }}"
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
src="{{ url_for('static_files', filename='Jose_Hugo_Rafael_T_Tan.jpg') }}"
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
src="{{ url_for('static_files', filename='Julia_Helga_Raquel_T_Tan.png') }}"
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

<h3>
⚡ Speed Math
</h3>

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

<h3>
🧠 Tech Quiz
</h3>

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

<h3>
🔐 Online Safety
</h3>

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

<h3>
🤝 JHR Values
</h3>

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


<footer>

<p>
© 2026 JHR — Empowerment Through Technology
</p>

<p>
Technology • Education • Innovation • Community
</p>

</footer>


<button
class="top"
id="topButton"
onclick="window.scrollTo({top:0,behavior:'smooth'})"
>
↑
</button>


<script>

function toggleDark(){

    document.body.classList.toggle("dark");

}


function mathGame(answer){

    document.getElementById("mathResult").textContent =
        answer === 96
        ? "🎉 Correct!"
        : "❌ Try again!";

}


function techGame(correct){

    document.getElementById("techResult").textContent =
        correct
        ? "💡 Correct!"
        : "❌ Try again!";

}


function safetyGame(correct){

    document.getElementById("safetyResult").textContent =
        correct
        ? "🔐 Correct! Keep passwords private."
        : "❌ Never share your password!";

}


function valuesGame(correct){

    document.getElementById("valuesResult").textContent =
        correct
        ? "🤝 Correct! Cooperation matters!"
        : "❌ Try again!";

}


window.addEventListener("scroll",function(){

    document.getElementById("topButton").style.display =
        window.scrollY > 500
        ? "block"
        : "none";

});

</script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/health")
def health():
    return "JHR is running!", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
