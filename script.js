const form = document.getElementById("analysisForm");
const resumeInput = document.getElementById("resume");
const message = document.getElementById("message");
const button = document.getElementById("analyzeButton");


// -------------------------------
// SELECTED FILE NAME
// -------------------------------

resumeInput.addEventListener("change", () => {

    const file = resumeInput.files[0];

    document.getElementById("fileName").textContent =
        file ? file.name : "Choose your PDF resume";

});


// -------------------------------
// SAFE HTML
// -------------------------------

function escapeHTML(value) {

    return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[char]));

}


// -------------------------------
// DISPLAY SKILLS
// -------------------------------

function showSkills(elementId, skills) {

    const element = document.getElementById(elementId);

    if (!skills || skills.length === 0) {
        element.innerHTML =
            '<p class="empty">No skills detected.</p>';
        return;
    }

    element.innerHTML = skills.map(skill =>
        `<span class="skill">${escapeHTML(skill)}</span>`
    ).join("");

}


// -------------------------------
// DISPLAY JOB RECOMMENDATIONS
// -------------------------------

function displayRecommendedJobs(jobs) {

    const container =
        document.getElementById("recommendedJobs");

    if (!jobs || jobs.length === 0) {
        container.innerHTML = "<p>No matching jobs found.</p>";
        return;
    }

    container.innerHTML = jobs.map((job, index) => {

                const score = Math.max(
                    0,
                    Math.min(100, Number(job.match_percentage) || 0)
                );

                const matching = job.matching_skills || [];
                const missing = job.missing_skills || [];

                return `

        <div class="result-card job-recommendation">

            <div class="job-header">

                <h3>
                    ${index + 1}. ${escapeHTML(job.title)}
                </h3>

                <span class="job-match">
                    ${score.toFixed(1)}% Match
                </span>

            </div>

            <p class="note">
                Closest job profile:
                ${escapeHTML(job.matched_profile)}
            </p>

            <div class="progress-container">
                <div class="progress-bar"
                     style="width: ${score}%">
                </div>
            </div>

            <h4>Matching Skills (${matching.length})</h4>

            <div class="job-skills">

                ${
                    matching.length
                    ? matching.map(skill =>
                        `<span class="skill">${escapeHTML(skill)}</span>`
                    ).join("")
                    : '<p class="empty">No matching skills found.</p>'
                }

            </div>

            <h4>Skills to Improve (${missing.length})</h4>

            <div class="job-skills">

                ${
                    missing.length
                    ? missing.map(skill =>
                        `<span class="skill missing">${escapeHTML(skill)}</span>`
                    ).join("")
                    : '<p class="empty">All listed skills detected!</p>'
                }

            </div>

        </div>

        `;

    }).join("");

}


// -------------------------------
// FORM SUBMISSION
// -------------------------------

form.addEventListener("submit", async (event) => {

    event.preventDefault();

    message.textContent = "";
    message.style.color = "#b42318";

    const file = resumeInput.files[0];

    const rawRoles =
        document.getElementById("job_title").value.trim();


    // Check resume

    if (!file) {
        message.textContent = "Please upload your resume.";
        return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
        message.textContent = "Please upload a PDF file.";
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        message.textContent = "Maximum PDF size is 5 MB.";
        return;
    }


    // Read job roles

    const roles = [...new Set(
        rawRoles
            .split(/[,\n;]+/)
            .map(role => role.trim())
            .filter(Boolean)
    )];


    if (roles.length === 0) {
        message.textContent = "Enter at least one job role.";
        return;
    }

    if (roles.length > 20) {
        message.textContent = "Maximum 20 job roles allowed.";
        return;
    }

    if (roles.some(role => role.length > 80)) {
        message.textContent =
            "Each job title must be 80 characters or less.";
        return;
    }


    // Prepare request

    const formData = new FormData();

    formData.append("resume", file);
    formData.append("job_title", roles.join("\n"));

    button.disabled = true;
    button.textContent = "AI is analysing your resume...";

    document.getElementById("results").hidden = true;


    try {

        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Analysis failed.");
        }


        // Show results

        document.getElementById("results").hidden = false;

        document.getElementById("score").textContent =
            Number(data.score).toFixed(1) + "%";

        document.getElementById("bestMatch").textContent =
            data.best_match || "Not available";

        document.getElementById("wordCount").textContent =
            "Resume word count: " + data.word_count;


        // Skills

        showSkills("resumeSkills", data.resume_skills);

        showSkills("matchingSkills", data.matching_skills);

        showSkills("missingSkills", data.missing_skills);


        // Suggestions

        document.getElementById("suggestions").innerHTML =
            (data.suggestions || []).map(item =>
                `<li>${escapeHTML(item)}</li>`
            ).join("");


        // All jobs

        displayRecommendedJobs(data.recommended_jobs);


        message.textContent =
            `Successfully analysed ${data.recommended_jobs.length} job roles!`;

        message.style.color = "green";

        document.getElementById("results").scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }

    catch (error) {

        message.textContent = error.message;
        message.style.color = "#b42318";

    }

    finally {

        button.disabled = false;
        button.textContent = "Find Matching Jobs";

    }

});