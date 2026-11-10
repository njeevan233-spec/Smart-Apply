
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer
import fitz
import numpy as np
import os
import re
import tempfile

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_JOB_ROLES = 20

# -------------------------------
# AI MODEL
# -------------------------------

print("Loading AI model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("AI model loaded successfully!")


# -------------------------------
# JOB DATABASE
# -------------------------------

JOB_DATABASE = [
    {
        "title": "Python Developer",
        "description": "Develop Python applications using Python, Flask, Django, APIs, SQL, Git and software development.",
        "skills": ["python", "flask", "django", "sql", "rest api", "git"]
    },
    {
        "title": "Java Developer",
        "description": "Develop Java software using Java, OOP, Spring Boot, SQL, REST APIs and Git.",
        "skills": ["java", "spring boot", "sql", "rest api", "git"]
    },
    {
        "title": "Frontend Developer",
        "description": "Build responsive websites using HTML, CSS, JavaScript and React.",
        "skills": ["html", "css", "javascript", "react"]
    },
    {
        "title": "Full Stack Developer",
        "description": "Build frontend and backend applications using HTML, CSS, JavaScript, React, Node.js and databases.",
        "skills": ["html", "css", "javascript", "react", "node.js", "sql", "mongodb"]
    },
    {
        "title": "Data Analyst",
        "description": "Analyze data using Python, SQL, Excel, Pandas, NumPy, statistics and data visualization.",
        "skills": ["python", "sql", "excel", "pandas", "numpy", "statistics"]
    },
    {
        "title": "Machine Learning Engineer",
        "description": "Build machine learning models using Python, Pandas, NumPy, Scikit-learn and TensorFlow.",
        "skills": ["python", "pandas", "numpy", "scikit-learn", "machine learning", "tensorflow"]
    },
    {
        "title": "AI Developer",
        "description": "Develop artificial intelligence applications using Python, machine learning, deep learning and PyTorch.",
        "skills": ["python", "artificial intelligence", "machine learning", "deep learning", "pytorch"]
    },
    {
        "title": "Backend Developer",
        "description": "Develop backend applications using Python, Flask, Django, Node.js, SQL, MongoDB and REST APIs.",
        "skills": ["python", "flask", "django", "node.js", "sql", "mongodb", "rest api"]
    },
    {
        "title": "Database Developer",
        "description": "Design and manage databases using SQL, MySQL and MongoDB.",
        "skills": ["sql", "mysql", "mongodb"]
    },
    {
        "title": "DevOps Engineer",
        "description": "Manage software deployment, Docker, Git, automation and cloud infrastructure.",
        "skills": ["docker", "git", "github", "linux"]
    },
    {
        "title": "Mobile App Developer",
        "description": "Develop mobile applications using Java, Flutter, Dart, APIs and databases.",
        "skills": ["java", "flutter", "dart", "rest api", "sql"]
    },
    {
        "title": "Software Developer",
        "description": "Design and develop software using Python, Java, C, SQL, Git and problem solving.",
        "skills": ["python", "java", "c", "sql", "git", "problem solving"]
    },
    {
        "title": "Cybersecurity Analyst",
        "description": "Protect systems and networks using cybersecurity, networking, Linux, security analysis and ethical hacking.",
        "skills": ["cybersecurity", "networking", "linux", "ethical hacking"]
    },
    {
        "title": "Cloud Engineer",
        "description": "Build and manage cloud infrastructure using AWS, Azure, Docker and Linux.",
        "skills": ["aws", "azure", "docker", "linux"]
    },
    {
        "title": "UI UX Designer",
        "description": "Design user interfaces using Figma, wireframes, prototyping and user experience principles.",
        "skills": ["figma", "ui design", "ux design"]
    }
]


ALL_SKILLS = sorted({
    skill
    for job in JOB_DATABASE
    for skill in job["skills"]
} | {
    "c++", "communication", "leadership",
    "github", "excel", "aws", "azure",
    "figma", "linux", "statistics",
    "problem solving", "ethical hacking",
    "artificial intelligence", "deep learning"
})


# -------------------------------
# PREPARE JOB EMBEDDINGS
# -------------------------------

print("Preparing job profiles...")

PROFILE_TEXTS = [
    job["title"] + ". " + job["description"]
    for job in JOB_DATABASE
]

PROFILE_EMBEDDINGS = model.encode(
    PROFILE_TEXTS,
    normalize_embeddings=True
)

print("Job profiles ready!")


# -------------------------------
# PDF TEXT EXTRACTION
# -------------------------------

def extract_pdf_text(file_path):

    with fitz.open(file_path) as pdf:
        return "\n".join(
            page.get_text() for page in pdf
        ).strip()


# -------------------------------
# TEXT CLEANING
# -------------------------------

def clean_text(text):

    return re.sub(r"\s+", " ", text).strip()


# -------------------------------
# SKILL EXTRACTION
# -------------------------------

def extract_skills(text):

    text = text.lower()
    found = []

    for skill in ALL_SKILLS:

        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"

        if re.search(pattern, text):
            found.append(skill)

    return found


# -------------------------------
# FIND CLOSEST JOB PROFILE
# -------------------------------

def find_job_profile(job_title):

    title_embedding = model.encode(
        [job_title],
        normalize_embeddings=True
    )[0]

    similarities = np.dot(
        PROFILE_EMBEDDINGS,
        title_embedding
    )

    index = int(np.argmax(similarities))

    return JOB_DATABASE[index]


# -------------------------------
# ANALYSE ALL JOBS
# -------------------------------

def analyse_jobs(resume_text, job_titles):

    resume_skills = extract_skills(resume_text)

    resume_embedding = model.encode(
        [resume_text],
        normalize_embeddings=True
    )[0]

    recommendations = []

    for requested_title in job_titles:

        profile = find_job_profile(requested_title)

        matching_skills = [
            skill for skill in profile["skills"]
            if skill in resume_skills
        ]

        missing_skills = [
            skill for skill in profile["skills"]
            if skill not in resume_skills
        ]

        profile_index = JOB_DATABASE.index(profile)

        similarity = float(
            np.dot(
                resume_embedding,
                PROFILE_EMBEDDINGS[profile_index]
            )
        )

        score = round(
            max(0, min(1, similarity)) * 100,
            2
        )

        recommendations.append({
            "title": requested_title,
            "matched_profile": profile["title"],
            "match_percentage": score,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "required_skills": profile["skills"]
        })

    recommendations.sort(
        key=lambda item: item["match_percentage"],
        reverse=True
    )

    return recommendations, resume_skills


# -------------------------------
# HOME PAGE
# -------------------------------

@app.route("/")
def home():

    return render_template("index.html")


# -------------------------------
# ANALYSE RESUME API
# -------------------------------

@app.route("/analyze", methods=["POST"])
def analyze():

    if "resume" not in request.files:
        return jsonify({
            "error": "Please upload your PDF resume."
        }), 400

    file = request.files["resume"]

    raw_titles = request.form.get(
        "job_title", ""
    ).strip()

    if not file.filename:
        return jsonify({
            "error": "Please select your resume."
        }), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files are supported."
        }), 400

    job_titles = [
        title.strip()
        for title in re.split(r"[,;\r\n]+", raw_titles)
        if title.strip()
    ]

    # Remove duplicate job titles
    job_titles = list(dict.fromkeys(
        title.lower() for title in job_titles
    ))

    # Preserve user-entered capitalization
    original_titles = [
        title.strip()
        for title in re.split(r"[,;\r\n]+", raw_titles)
        if title.strip()
    ]

    unique_titles = []
    seen = set()

    for title in original_titles:
        if title.lower() not in seen:
            unique_titles.append(title)
            seen.add(title.lower())

    job_titles = unique_titles

    if not job_titles:
        return jsonify({
            "error": "Please enter at least one job role."
        }), 400

    if len(job_titles) > MAX_JOB_ROLES:
        return jsonify({
            "error": "Maximum 20 job roles allowed."
        }), 400

    if any(len(title) > 80 for title in job_titles):
        return jsonify({
            "error": "Each job role must be 80 characters or less."
        }), 400

    file_path = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=UPLOAD_FOLDER,
            delete=False
        ) as temp:

            file_path = temp.name
            file.save(file_path)

        resume_text = clean_text(
            extract_pdf_text(file_path)
        )

        if len(resume_text) < 30:
            return jsonify({
                "error": "No readable text found. Please upload a text-based PDF, not a scanned image."
            }), 400

        recommendations, resume_skills = analyse_jobs(
            resume_text,
            job_titles
        )

        best_job = recommendations[0]

        suggestions = []

        if best_job["missing_skills"]:
            suggestions.append(
                "Consider learning: "
                + ", ".join(best_job["missing_skills"])
            )

        if not resume_skills:
            suggestions.append(
                "Add a technical skills section to your resume."
            )

        if len(resume_text.split()) < 100:
            suggestions.append(
                "Add more project details, education and experience."
            )

        if not suggestions:
            suggestions.append(
                "Add measurable achievements to your projects and experience."
            )

        return jsonify({

            "success": True,
            "job_titles": job_titles,
            "score": best_job["match_percentage"],
            "best_match": best_job["title"],
            "resume_skills": resume_skills,
            "job_skills": best_job["required_skills"],
            "matching_skills": best_job["matching_skills"],
            "missing_skills": best_job["missing_skills"],
            "suggestions": suggestions,
            "word_count": len(resume_text.split()),
            "recommended_jobs": recommendations

        })

    except Exception as error:

        app.logger.exception("Resume analysis failed")

        return jsonify({
            "error": "Analysis failed: " + str(error)
        }), 500

    finally:

        if file_path and os.path.exists(file_path):
            os.remove(file_path)


# -------------------------------
# FILE SIZE ERROR
# -------------------------------

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "Your PDF must be smaller than 5 MB."
    }), 413


# -------------------------------
# START SERVER
# -------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
