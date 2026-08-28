from flask import Flask, render_template_string

app = Flask(__name__)

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>JHR - Empowerment Through Technology</title>

<style>
:root {
    --purple: #6d28d9;
    --purple-dark: #4c1d95;
    --purple-light: #a855f7;
    --purple-soft: #ede9fe;
    --bg: #faf7ff;
    --card: #ffffff;
    --text: #24113d;
    --muted: #6b5a7a;
    --border: #ddd6fe;
    --shadow: 0 12px 35px rgba(76, 29, 149, 0.16);
}

body.dark {
    --bg: #160d24;
    --card: #241337;
    --text: #f7f2ff;
    --muted: #d0c4dd;
    --border: #573780;
    --purple-soft: #33204c;
    --shadow: 0 12px 35px rgba(0, 0, 0, 0.35);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    scroll-behavior: smooth;
}

body {
    font-family: Arial, Helvetica, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    transition: background 0.3s, color 0.3s;
}

/* NAVIGATION */

nav {
    width: 100%;
    position: sticky;
    top: 0;
    z-index: 1000;
    background: rgba(109, 40, 217, 0.97);
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(76, 29, 149, 0.25);
}

.nav-container {
    width: min(1150px, 92%);
    margin: auto;
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    color: white;
    font-weight: 900;
    font-size: 1.3rem;
    text-decoration: none;
}

.brand-badge {
    width: 42px;
    height: 42px;
    background: white;
    color: var(--purple);
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-weight: 900;
}

.nav-links {
    display: flex;
    gap: 18px;
    align-items: center;
}

.nav-links a {
    color: white;
    text-decoration: none;
    font-weight: 700;
    font-size: 0.95rem;
}

.nav-links a:hover {
    text-decoration: underline;
}

.controls {
    display: flex;
    align-items: center;
    gap: 8px;
}

.control-btn,
.lang-select {
    border: 2px solid rgba(255,255,255,0.6);
    background: white;
    color: var(--purple-dark);
    border-radius: 10px;
    padding: 8px 11px;
    font-weight: 800;
    cursor: pointer;
}

.lang-select {
    outline: none;
}

/* HERO */

.hero {
    min-height: 650px;
    padding: 80px 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    background:
        radial-gradient(circle at top left, rgba(168, 85, 247, 0.30), transparent 35%),
        radial-gradient(circle at bottom right, rgba(109, 40, 217, 0.22), transparent 35%),
        var(--bg);
}

.hero-content {
    width: min(950px, 100%);
}

.logo-box {
    width: 150px;
    height: 150px;
    margin: 0 auto 25px;
    border-radius: 50%;
    overflow: hidden;
    background: white;
    box-shadow: var(--shadow);
    border: 5px solid var(--purple);
}

.logo-box img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.hero h1 {
    font-size: clamp(2.4rem, 7vw, 5.5rem);
    line-height: 1;
    color: var(--purple);
    margin-bottom: 18px;
}

.hero .tagline {
    color: var(--purple-dark);
    font-weight: 900;
    letter-spacing: 1px;
    font-size: clamp(0.9rem, 2vw, 1.2rem);
    margin-bottom: 24px;
}

body.dark .hero .tagline {
    color: #d8b4fe;
}

.hero-description {
    font-size: clamp(1rem, 2.5vw, 1.3rem);
    max-width: 750px;
    margin: auto;
    color: var(--muted);
}

.journey {
    margin-top: 30px;
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--text);
}

.journey-title {
    font-size: 1.35rem;
    color: var(--purple);
    margin-bottom: 8px;
}

.viewer-counter {
    margin: 16px auto 0;
    width: fit-content;
    background: var(--card);
    color: var(--purple);
    border: 2px solid var(--purple-light);
    border-radius: 999px;
    padding: 10px 20px;
    font-weight: 900;
    box-shadow: var(--shadow);
}

.hero-buttons {
    margin-top: 30px;
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
}

.btn {
    display: inline-block;
    padding: 13px 22px;
    border-radius: 10px;
    text-decoration: none;
    font-weight: 900;
    transition: transform 0.2s, opacity 0.2s;
}

.btn:hover {
    transform: translateY(-3px);
}

.btn-primary {
    background: var(--purple);
    color: white;
}

.btn-secondary {
    background: var(--card);
    color: var(--purple);
    border: 2px solid var(--purple);
}

/* SECTIONS */

section {
    padding: 80px 20px;
}

.container {
    width: min(1150px, 100%);
    margin: auto;
}

.section-title {
    text-align: center;
    font-size: clamp(2rem, 5vw, 3rem);
    color: var(--purple);
    margin-bottom: 12px;
}

.section-subtitle {
    text-align: center;
    max-width: 750px;
    margin: 0 auto 45px;
    color: var(--muted);
}

/* CARDS */

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(235px, 1fr));
    gap: 22px;
}

.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 28px;
    box-shadow: var(--shadow);
}

.card-icon {
    font-size: 2.5rem;
    margin-bottom: 12px;
}

.card h3 {
    color: var(--purple);
    margin-bottom: 10px;
}

/* SERVICE */

.service {
    background: linear-gradient(135deg, var(--purple-dark), var(--purple));
    color: white;
}

.service .section-title,
.service .section-subtitle {
    color: white;
}

.service-box {
    width: min(850px, 100%);
    margin: auto;
    text-align: center;
    padding: 35px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.35);
    border-radius: 20px;
}

.service-box h3 {
    font-size: 1.7rem;
    margin-bottom: 10px;
}

/* FOUNDERS */

.founders {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 28px;
}

.founder-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: var(--shadow);
    text-align: center;
}

.founder-photo {
    width: 100%;
    height: 420px;
    display: block;
    object-fit: cover;
    background: var(--purple-soft);
}

.founder-info {
    padding: 24px;
}

.founder-info h3 {
    color: var(--purple);
    font-size: 1.35rem;
}

.founder-info p {
    color: var(--muted);
    margin-top: 8px;
}

/* GALLERY */

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 25px;
}

.gallery-item {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

.gallery-image {
    width: 100%;
    height: 380px;
    display: block;
    object-fit: cover;
    background: var(--purple-soft);
}

.gallery-caption {
    padding: 18px;
}

.gallery-caption h3 {
    color: var(--purple);
    margin-bottom: 5px;
}

.gallery-caption p {
    color: var(--muted);
}

/* CONTACT */

.contact-box {
    max-width: 700px;
    margin: auto;
    background: var(--card);
    border: 1px solid var(--border);
    padding: 35px;
    border-radius: 20px;
    box-shadow: var(--shadow);
    text-align: center;
}

/* FOOTER */

footer {
    background: var(--purple-dark);
    color: white;
    padding: 35px 20px;
    text-align: center;
}

footer p {
    opacity: 0.9;
}

@media (max-width: 800px) {
    .nav-container {
        flex-wrap: wrap;
        justify-content: center;
        padding: 12px 0;
    }

    .nav-links {
        justify-content: center;
        flex-wrap: wrap;
        gap: 12px;
    }

    .gallery-grid {
        grid-template-columns: 1fr;
    }

    .gallery-image {
        height: 300px;
    }
}

@media (max-width: 500px) {
    .founder-photo {
        height: 360px;
    }

    .hero {
        min-height: 600px;
        padding-top: 50px;
    }

    .nav-links a {
        font-size: 0.85rem;
    }
}
</style>
</head>

<body>

<nav>
    <div class="nav-container">

        <a href="#home" class="brand">
            <span class="brand-badge">JHR</span>
            <span>JHR</span>
        </a>

        <div class="nav-links">
            <a href="#home" data-en="Home" data-fil="Tahanan">Home</a>
            <a href="#about" data-en="About" data-fil="Tungkol">About</a>
            <a href="#services" data-en="Services" data-fil="Serbisyo">Services</a>
            <a href="#founders" data-en="Founders" data-fil="Mga Tagapagtatag">Founders</a>
            <a href="#gallery" data-en="Gallery" data-fil="Gallery">Gallery</a>
        </div>

        <div class="controls">
            <select class="lang-select" id="languageSelect" onchange="changeLanguage()">
                <option value="en">EN</option>
                <option value="fil">FIL</option>
            </select>

            <button class="control-btn" id="themeButton" onclick="toggleTheme()">
                🌙 Dark
            </button>
        </div>

    </div>
</nav>


<section class="hero" id="home">
    <div class="hero-content">

        <!-- Put your JHR logo here -->
        <div class="logo-box">
            <img
                src="{{ url_for('static', filename='logo.jpg') }}"
                alt="JHR Logo"
                onerror="this.style.display='none'; this.parentElement.innerHTML='JHR'; this.parentElement.style.display='grid'; this.parentElement.style.placeItems='center'; this.parentElement.style.fontSize='2.3rem'; this.parentElement.style.fontWeight='900'; this.parentElement.style.color='#6d28d9';"
            >
        </div>

        <h1>JHR</h1>

        <div class="tagline"
             data-en="TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY"
             data-fil="TEKNOLOHIYA • EDUKASYON • INOBASYON • KOMUNIDAD">
            TECHNOLOGY • EDUCATION • INNOVATION • COMMUNITY
        </div>

        <p class="hero-description"
           data-en="Empowering young people and communities through learning, creativity, technology, and innovation."
           data-fil="Pagbibigay-kakayahan sa kabataan at komunidad sa pamamagitan ng pag-aaral, pagkamalikhain, teknolohiya, at inobasyon.">
            Empowering young people and communities through learning, creativity, technology, and innovation.
        </p>

        <div class="journey">
            <div class="journey-title"
                 data-en="Join the JHR Journey 🚀"
                 data-fil="Sumali sa JHR Journey 🚀">
                Join the JHR Journey 🚀
            </div>

            <div
                data-en="Technology • Education • Innovation • Community"
                data-fil="Teknolohiya • Edukasyon • Inobasyon • Komunidad">
                Technology • Education • Innovation • Community
            </div>

            <div
                data-en="Learn. Create. Share. Empower."
                data-fil="Matuto. Lumikha. Magbahagi. Magbigay-kakayahan.">
                Learn. Create. Share. Empower.
            </div>

            <!-- VIEWER COUNTER EXACTLY BELOW THE JHR JOURNEY TEXT -->
            <div class="viewer-counter">
                👁 Visitors: <span id="viewerCount">1</span>
            </div>
        </div>

        <div class="hero-buttons">
            <a href="#services"
               class="btn btn-primary"
               data-en="Explore Our Services"
               data-fil="Tingnan ang Aming Serbisyo">
                Explore Our Services
            </a>

            <a href="#gallery"
               class="btn btn-secondary"
               data-en="View Gallery"
               data-fil="Tingnan ang Gallery">
                View Gallery
            </a>
        </div>

    </div>
</section>


<section id="about">
    <div class="container">

        <h2 class="section-title"
            data-en="About JHR"
            data-fil="Tungkol sa JHR">
            About JHR
        </h2>

        <p class="section-subtitle"
           data-en="JHR is focused on technology, education, innovation, and community. We believe that young people can learn, create, share knowledge, and make a positive difference."
           data-fil="Ang JHR ay nakatuon sa teknolohiya, edukasyon, inobasyon, at komunidad. Naniniwala kami na ang kabataan ay maaaring matuto, lumikha, magbahagi ng kaalaman, at gumawa ng positibong pagbabago.">
            JHR is focused on technology, education, innovation, and community. We believe that young people can learn, create, share knowledge, and make a positive difference.
        </p>

        <div class="cards">

            <div class="card">
                <div class="card-icon">💻</div>
                <h3 data-en="Technology" data-fil="Teknolohiya">Technology</h3>
                <p data-en="Learning and exploring useful technology and digital skills."
                   data-fil="Pag-aaral at pagtuklas ng kapaki-pakinabang na teknolohiya at digital na kasanayan.">
                    Learning and exploring useful technology and digital skills.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">📚</div>
                <h3 data-en="Education" data-fil="Edukasyon">Education</h3>
                <p data-en="Sharing knowledge and helping others learn."
                   data-fil="Pagbabahagi ng kaalaman at pagtulong sa iba na matuto.">
                    Sharing knowledge and helping others learn.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">💡</div>
                <h3 data-en="Innovation" data-fil="Inobasyon">Innovation</h3>
                <p data-en="Creating ideas and projects that solve problems."
                   data-fil="Paglikha ng mga ideya at proyekto na tumutulong sa paglutas ng problema.">
                    Creating ideas and projects that solve problems.
                </p>
            </div>

            <div class="card">
                <div class="card-icon">🤝</div>
                <h3 data-en="Community" data-fil="Komunidad">Community</h3>
                <p data-en="Working with communities and encouraging young learners."
                   data-fil="Pakikipagtulungan sa komunidad at paghikayat sa mga batang mag-aaral.">
                    Working with communities and encouraging young learners.
                </p>
            </div>

        </div>
    </div>
</section>


<section class="service" id="services">
    <div class="container">

        <h2 class="section-title"
            data-en="Our Services"
            data-fil="Aming Serbisyo">
            Our Services
        </h2>

        <p class="section-subtitle"
           data-en="Learning opportunities for young people and communities."
           data-fil="Mga oportunidad sa pag-aaral para sa kabataan at komunidad.">
            Learning opportunities for young people and communities.
        </p>

        <div class="service-box">
            <h3 data-en="💻 We Provide Free Coding Classes!"
                data-fil="💻 Nagbibigay Kami ng Libreng Coding Classes!">
                💻 We Provide Free Coding Classes!
            </h3>

            <p data-en="JHR provides free coding classes to help children and young learners explore programming, technology, creativity, and digital skills."
               data-fil="Nagbibigay ang JHR ng libreng coding classes upang matulungan ang mga bata at batang mag-aaral na matuklasan ang programming, teknolohiya, pagkamalikhain, at digital na kasanayan.">
                JHR provides free coding classes to help children and young learners explore programming, technology, creativity, and digital skills.
            </p>
        </div>

    </div>
</section>


<section id="founders">
    <div class="container">

        <h2 class="section-title"
            data-en="Founders"
            data-fil="Mga Tagapagtatag">
            Founders
        </h2>

        <p class="section-subtitle"
           data-en="Meet the young founders behind JHR."
           data-fil="Kilalanin ang mga batang tagapagtatag ng JHR.">
            Meet the young founders behind JHR.
        </p>

        <div class="founders">

            <div class="founder-card">
                <img
                    class="founder-photo"
                    src="{{ url_for('static', filename='jose.jpg') }}"
                    alt="Jose Hugo Rafael T. Tan"
                    onerror="this.onerror=null; this.src='{{ url_for('static', filename='founder_boy.jpg') }}';"
                >

                <div class="founder-info">
                    <h3>Jose Hugo Rafael T. Tan</h3>
                    <p data-en="Founder"
                       data-fil="Tagapagtatag">
                        Founder
                    </p>
                </div>
            </div>

            <div class="founder-card">
                <img
                    class="founder-photo"
                    src="{{ url_for('static', filename='julia.jpg') }}"
                    alt="Julia Helga Raquel T. Tan"
                    onerror="this.onerror=null; this.src='{{ url_for('static', filename='founder_girl.jpg') }}';"
                >

                <div class="founder-info">
                    <h3>Julia Helga Raquel T. Tan</h3>
                    <p data-en="Founder"
                       data-fil="Tagapagtatag">
                        Founder
                    </p>
                </div>
            </div>

        </div>

    </div>
</section>


<section id="gallery">
    <div class="container">

        <h2 class="section-title"
            data-en="JHR Gallery"
            data-fil="JHR Gallery">
            JHR Gallery
        </h2>

        <p class="section-subtitle"
           data-en="Moments from our learning activities and community outreach."
           data-fil="Mga sandali mula sa aming mga aktibidad sa pag-aaral at pagtulong sa komunidad.">
            Moments from our learning activities and community outreach.
        </p>


        <!--
        IMPORTANT:
        ONLY THE TWO CORRECT GALLERY PHOTOS ARE HERE.

        1. gallery_ozamiz.jpg
           = Group photo at Ozamiz Elementary School

        2. gallery_community.jpg
           = Outdoor coding/community class photo
        -->

        <div class="gallery-grid">

            <!-- CORRECT PHOTO 1: OZAMIZ ELEMENTARY SCHOOL GROUP PHOTO -->
            <div class="gallery-item">
                <img
                    class="gallery-image"
                    src="{{ url_for('static', filename='gallery_ozamiz.jpg') }}"
                    alt="JHR activity at Ozamiz Elementary School"
                >

                <div class="gallery-caption">
                    <h3 data-en="Learning Together"
                        data-fil="Sama-samang Pag-aaral">
                        Learning Together
                    </h3>

                    <p data-en="A special learning moment with children at Ozamiz Elementary School."
                       data-fil="Isang espesyal na sandali ng pag-aaral kasama ang mga bata sa Ozamiz Elementary School.">
                        A special learning moment with children at Ozamiz Elementary School.
                    </p>
                </div>
            </div>


            <!-- CORRECT PHOTO 2: OUTDOOR COMMUNITY CODING CLASS -->
            <div class="gallery-item">
                <img
                    class="gallery-image"
                    src="{{ url_for('static', filename='gallery_community.jpg') }}"
                    alt="JHR community coding class"
                >

                <div class="gallery-caption">
                    <h3 data-en="Community Coding Class"
                        data-fil="Coding Class sa Komunidad">
                        Community Coding Class
                    </h3>

                    <p data-en="Sharing technology and learning with children in the community."
                       data-fil="Pagbabahagi ng teknolohiya at pag-aaral kasama ang mga bata sa komunidad.">
                        Sharing technology and learning with children in the community.
                    </p>
                </div>
            </div>

        </div>

    </div>
</section>


<section id="contact">
    <div class="container">

        <h2 class="section-title"
            data-en="Join the JHR Journey"
            data-fil="Sumali sa JHR Journey">
            Join the JHR Journey
        </h2>

        <div class="contact-box">
            <h3 data-en="Learn. Create. Share. Empower."
                data-fil="Matuto. Lumikha. Magbahagi. Magbigay-kakayahan.">
                Learn. Create. Share. Empower.
            </h3>

            <p style="margin-top: 15px; color: var(--muted);"
               data-en="Together, we can use technology and education to create positive change."
               data-fil="Sama-sama nating magagamit ang teknolohiya at edukasyon upang lumikha ng positibong pagbabago.">
                Together, we can use technology and education to create positive change.
            </p>
        </div>

    </div>
</section>


<footer>
    <h3>JHR Team</h3>
    <p>Technology • Education • Innovation • Community</p>
    <p style="margin-top: 8px;">© <span id="year"></span> JHR. All Rights Reserved.</p>
</footer>


<script>

/* =========================
   LIGHT / DARK MODE
========================= */

function updateThemeButton() {
    const button = document.getElementById("themeButton");

    if (document.body.classList.contains("dark")) {
        button.textContent = "☀️ Light";
    } else {
        button.textContent = "🌙 Dark";
    }
}

function toggleTheme() {
    document.body.classList.toggle("dark");

    const theme = document.body.classList.contains("dark")
        ? "dark"
        : "light";

    localStorage.setItem("jhr-theme", theme);

    updateThemeButton();
}

function loadTheme() {
    const savedTheme = localStorage.getItem("jhr-theme");

    if (savedTheme === "dark") {
        document.body.classList.add("dark");
    }

    updateThemeButton();
}


/* =========================
   LANGUAGE
========================= */

function changeLanguage() {
    const language = document.getElementById("languageSelect").value;

    document.querySelectorAll("[data-en]").forEach(function(element) {
        if (language === "fil") {
            element.textContent = element.getAttribute("data-fil");
        } else {
            element.textContent = element.getAttribute("data-en");
        }
    });

    localStorage.setItem("jhr-language", language);
}

function loadLanguage() {
    const savedLanguage = localStorage.getItem("jhr-language") || "en";

    document.getElementById("languageSelect").value = savedLanguage;

    changeLanguage();
}


/* =========================
   VIEWER COUNTER
========================= */

function updateViewerCounter() {
    let count = localStorage.getItem("jhr-viewer-count");

    if (count === null) {
        count = 1;
    } else {
        count = parseInt(count) + 1;
    }

    localStorage.setItem("jhr-viewer-count", count);

    document.getElementById("viewerCount").textContent = count;
}


/* =========================
   START WEBSITE
========================= */

document.getElementById("year").textContent =
    new Date().getFullYear();

loadTheme();
loadLanguage();
updateViewerCounter();

</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
