const API_BASE = "http://localhost:8000/api";

// Elements
const cvInput = document.getElementById("cvInput");
const saveCvBtn = document.getElementById("saveCvBtn");
const saveStatus = document.getElementById("saveStatus");
const roleSelect = document.getElementById("roleSelect");
const customRoleInput = document.getElementById("customRoleInput");
const experienceSelect = document.getElementById("experienceSelect");
const additionalFilters = document.getElementById("additionalFilters");
const boardSelect = document.getElementById("boardSelect");
const executeBtn = document.getElementById("executeBtn");
const executeStatus = document.getElementById("executeStatus");

const refreshBtn = document.getElementById("refreshBtn");
const resultsContainer = document.getElementById("resultsContainer");

const tabDashboard = document.getElementById("tabDashboard");
const tabMatches = document.getElementById("tabMatches");
const viewDashboard = document.getElementById("view-dashboard");
const viewMatches = document.getElementById("view-matches");
const viewDetail = document.getElementById("view-detail");

const backBtn = document.getElementById("backBtn");
const detailTitle = document.getElementById("detailTitle");
const detailContent = document.getElementById("detailContent");

let allMatches = [];

// Navigation Logic
function switchView(viewId) {
    viewDashboard.classList.add("hidden");
    viewMatches.classList.add("hidden");
    viewDetail.classList.add("hidden");

    if (viewId === "dashboard") {
        viewDashboard.classList.remove("hidden");
        tabDashboard.classList.add("active");
        tabMatches.classList.remove("active");
    } else if (viewId === "matches") {
        viewMatches.classList.remove("hidden");
        tabDashboard.classList.remove("active");
        tabMatches.classList.add("active");
    } else if (viewId === "detail") {
        viewDetail.classList.remove("hidden");
        // keep Matches tab active
    }
}

tabDashboard.addEventListener("click", () => switchView("dashboard"));
tabMatches.addEventListener("click", () => {
    switchView("matches");
    if (allMatches.length === 0) loadOutputs();
});
backBtn.addEventListener("click", () => switchView("matches"));

// Load config on start
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/config`);
        const data = await res.json();
        
        if (data.my_cv) {
            cvInput.value = data.my_cv;
        }
        
        if (data.boards && data.boards.length > 0) {
            boardSelect.innerHTML = "";
            data.boards.forEach(board => {
                const opt = document.createElement("option");
                opt.value = board;
                opt.textContent = board;
                opt.selected = true; // Select all by default
                boardSelect.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load config:", e);
    }
}

// Load Example CV
const fillExampleBtn = document.getElementById("fillExampleBtn");
fillExampleBtn.addEventListener("click", async () => {
    fillExampleBtn.disabled = true;
    fillExampleBtn.textContent = "Loading...";
    
    try {
        const res = await fetch(`${API_BASE}/example-cv`);
        const data = await res.json();
        
        if (data.example_cv) {
            cvInput.value = data.example_cv;
            saveStatus.textContent = "Example loaded! Don't forget to save.";
            saveStatus.style.color = "var(--primary-color)";
        } else {
            saveStatus.textContent = "No example found.";
            saveStatus.style.color = "#ba1a1a";
        }
    } catch (e) {
        console.error("Failed to load example:", e);
    } finally {
        fillExampleBtn.disabled = false;
        fillExampleBtn.textContent = "Fill with Example";
        setTimeout(() => saveStatus.textContent = "", 3000);
    }
});

// Save CV
saveCvBtn.addEventListener("click", async () => {
    saveCvBtn.disabled = true;
    saveStatus.textContent = "Saving...";
    
    try {
        const res = await fetch(`${API_BASE}/save-cv`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cv_text: cvInput.value })
        });
        
        if (res.ok) {
            saveStatus.textContent = "CV saved successfully!";
            saveStatus.style.color = "var(--primary-color)";
        } else {
            throw new Error("Server error");
        }
    } catch (e) {
        saveStatus.textContent = "Failed to save.";
        saveStatus.style.color = "#ba1a1a";
    } finally {
        saveCvBtn.disabled = false;
        setTimeout(() => saveStatus.textContent = "", 3000);
    }
});

// Toggle custom role input visibility
roleSelect.addEventListener("change", () => {
    if (roleSelect.value === "Other") {
        customRoleInput.classList.remove("hidden");
    } else {
        customRoleInput.classList.add("hidden");
    }
});

// Run Scout
executeBtn.addEventListener("click", async () => {
    let targetRole = roleSelect.value;
    if (targetRole === "Other") {
        targetRole = customRoleInput.value.trim();
    }
    
    const selectedBoards = Array.from(boardSelect.selectedOptions).map(opt => opt.value);
    
    if (!targetRole) {
        alert("Please specify a target role.");
        return;
    }
    
    try {
        executeBtn.disabled = true;
        executeBtn.textContent = "Starting Scout...";
        executeStatus.textContent = "";
        executeStatus.style.color = "var(--text-color)";
        
        const res = await fetch(`${API_BASE}/run-scout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target_role: targetRole,
                boards: selectedBoards,
                experience_level: experienceSelect.value,
                additional_filters: additionalFilters.value.trim()
            })
        });
        
        const data = await res.json();
        
        if (data.status === "error") {
            executeStatus.textContent = data.message;
            executeStatus.style.color = "#ba1a1a";
            executeBtn.disabled = false;
            executeBtn.textContent = "Start Scouting";
            return;
        }

        executeStatus.textContent = "Scouting in progress... (This may take a few minutes)";
        executeBtn.textContent = "Scouting...";
        
        // Start polling status
        const pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetch(`${API_BASE}/status`);
                const statusData = await statusRes.json();
                
                if (!statusData.is_running) {
                    clearInterval(pollInterval);
                    executeBtn.disabled = false;
                    executeBtn.textContent = "Start Scouting";
                    
                    if (statusData.matches_found > 0) {
                        executeStatus.textContent = `Finished! Found ${statusData.matches_found} matches.`;
                        executeStatus.style.color = "var(--primary-color)";
                        // Auto-switch to Matches tab
                        document.getElementById("tabMatches").click();
                    } else {
                        executeStatus.textContent = "Finished! No matches found this time.";
                        executeStatus.style.color = "var(--text-color)";
                    }
                } else {
                    // Still running
                    executeStatus.textContent = statusData.message || "Scouting in progress...";
                }
            } catch (err) {
                console.error("Error checking status:", err);
            }
        }, 3000); // Check every 3 seconds
        
    } catch (e) {
        console.error("Failed to run scout:", e);
        executeStatus.textContent = "Failed to start scouting.";
        executeStatus.style.color = "#ba1a1a";
        executeBtn.disabled = false;
        executeBtn.textContent = "Start Scouting";
    }
});

// Load Matches
async function loadOutputs() {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Loading...";
    
    try {
        const res = await fetch(`${API_BASE}/outputs`);
        const data = await res.json();
        
        resultsContainer.innerHTML = "";
        allMatches = data.outputs || [];
        
        if (allMatches.length > 0) {
            allMatches.forEach((job, index) => {
                const card = document.createElement("div");
                card.className = "match-card";
                card.onclick = () => openMatchDetail(index);
                
                const title = document.createElement("h3");
                title.textContent = job.title;
                card.appendChild(title);
                
                const snippet = document.createElement("p");
                snippet.textContent = job.content.substring(0, 150) + "...";
                snippet.style.color = "var(--text-muted)";
                snippet.style.margin = "0";
                card.appendChild(snippet);
                
                resultsContainer.appendChild(card);
            });
        } else {
            resultsContainer.innerHTML = `<p class="status-msg">No matches found yet. Keep scouting!</p>`;
        }
    } catch (e) {
        console.error("Failed to load outputs:", e);
        resultsContainer.innerHTML = `<p class="status-msg" style="color: #ba1a1a;">Failed to load results.</p>`;
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh";
    }
}

refreshBtn.addEventListener("click", loadOutputs);

function openMatchDetail(index) {
    const job = allMatches[index];
    if (!job) return;
    
    detailTitle.textContent = job.title;
    detailContent.innerHTML = marked.parse(job.content);
    
    switchView("detail");
}

loadConfig();
