// ─────────────────────────────────────────────────────────────────────────────
// Config — update API_BASE for production (uses relative path, works with Nginx)
// ─────────────────────────────────────────────────────────────────────────────
const API_BASE = "/api";   // relative — Nginx proxies /api/ to FastAPI

// ─────────────────────────────────────────────────────────────────────────────
// Auth state
// ─────────────────────────────────────────────────────────────────────────────
let currentUser = null;    // { id, email, role } or null
let authToken = null;

function loadAuthFromStorage() {
    authToken = localStorage.getItem("jwtToken");
    const stored = localStorage.getItem("currentUser");
    if (stored) {
        try { currentUser = JSON.parse(stored); } catch (_) { currentUser = null; }
    }
}

function saveAuth(token, user) {
    authToken = token;
    currentUser = user;
    localStorage.setItem("jwtToken", token);
    localStorage.setItem("currentUser", JSON.stringify(user));
}

function clearAuth() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem("jwtToken");
    localStorage.removeItem("currentUser");
}

function authHeaders() {
    return authToken ? { "Authorization": `Bearer ${authToken}` } : {};
}

// ─────────────────────────────────────────────────────────────────────────────
// DOM refs
// ─────────────────────────────────────────────────────────────────────────────
const authModal       = document.getElementById("authModal");
const closeAuthModal  = document.getElementById("closeAuthModal");
const authTabLogin    = document.getElementById("authTabLogin");
const authTabRegister = document.getElementById("authTabRegister");
const loginForm       = document.getElementById("loginForm");
const registerForm    = document.getElementById("registerForm");
const loginError      = document.getElementById("loginError");
const registerError   = document.getElementById("registerError");

const userBar    = document.getElementById("userBar");
const userEmail  = document.getElementById("userEmail");
const userRole   = document.getElementById("userRole");
const usageMeter = document.getElementById("usageMeter");
const usageLabel = document.getElementById("usageLabel");
const usageBarFill = document.getElementById("usageBarFill");
const logoutBtn  = document.getElementById("logoutBtn");
const guestBanner = document.getElementById("guestBanner");
const openAuthBtn = document.getElementById("openAuthBtn");

const cvInput          = document.getElementById("cvInput");
const saveCvBtn        = document.getElementById("saveCvBtn");
const saveStatus       = document.getElementById("saveStatus");
const fillExampleBtn   = document.getElementById("fillExampleBtn");
const roleSelect       = document.getElementById("roleSelect");
const customRoleInput  = document.getElementById("customRoleInput");
const experienceSelect = document.getElementById("experienceSelect");
const additionalFilters = document.getElementById("additionalFilters");
const boardSelect      = document.getElementById("boardSelect");
const executeBtn       = document.getElementById("executeBtn");
const executeStatus    = document.getElementById("executeStatus");

const tabDashboard  = document.getElementById("tabDashboard");
const tabMatches    = document.getElementById("tabMatches");
const tabHistory    = document.getElementById("tabHistory");
const viewDashboard = document.getElementById("view-dashboard");
const viewMatches   = document.getElementById("view-matches");
const viewDetail    = document.getElementById("view-detail");
const viewHistory   = document.getElementById("view-history");

const refreshBtn       = document.getElementById("refreshBtn");
const resultsContainer = document.getElementById("resultsContainer");
const toggleNonMatches = document.getElementById("toggleNonMatches");
const nonMatchesPanel  = document.getElementById("nonMatchesPanel");
const nonMatchesContainer = document.getElementById("nonMatchesContainer");
const historyContainer = document.getElementById("historyContainer");

const backBtn      = document.getElementById("backBtn");
const detailTitle  = document.getElementById("detailTitle");
const detailContent = document.getElementById("detailContent");

let allMatches = [];
let nonMatchesVisible = false;

// ─────────────────────────────────────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────────────────────────────────────
function switchView(viewId) {
    [viewDashboard, viewMatches, viewDetail, viewHistory].forEach(v => {
        v.classList.add("hidden");
        v.classList.remove("active");
    });
    [tabDashboard, tabMatches, tabHistory].forEach(t => t.classList.remove("active"));

    if (viewId === "dashboard") {
        viewDashboard.classList.remove("hidden");
        viewDashboard.classList.add("active");
        tabDashboard.classList.add("active");
    } else if (viewId === "matches") {
        viewMatches.classList.remove("hidden");
        viewMatches.classList.add("active");
        tabMatches.classList.add("active");
    } else if (viewId === "detail") {
        viewDetail.classList.remove("hidden");
        viewDetail.classList.add("active");
        tabMatches.classList.add("active");
    } else if (viewId === "history") {
        viewHistory.classList.remove("hidden");
        viewHistory.classList.add("active");
        tabHistory.classList.add("active");
    }
}

tabDashboard.addEventListener("click", () => switchView("dashboard"));
tabMatches.addEventListener("click", () => {
    switchView("matches");
    if (allMatches.length === 0) loadOutputs();
});
tabHistory.addEventListener("click", () => {
    switchView("history");
    loadHistory();
});
backBtn.addEventListener("click", () => switchView("matches"));

// ─────────────────────────────────────────────────────────────────────────────
// Auth modal
// ─────────────────────────────────────────────────────────────────────────────
function openAuthModal(tab = "login") {
    authModal.classList.remove("hidden");
    if (tab === "register") switchAuthTab("register");
    else switchAuthTab("login");
}

function closeModal() {
    authModal.classList.add("hidden");
    loginError.classList.add("hidden");
    registerError.classList.add("hidden");
    loginForm.reset();
    registerForm.reset();
}

function switchAuthTab(tab) {
    if (tab === "login") {
        authTabLogin.classList.add("active");
        authTabRegister.classList.remove("active");
        loginForm.classList.remove("hidden");
        registerForm.classList.add("hidden");
    } else {
        authTabRegister.classList.add("active");
        authTabLogin.classList.remove("active");
        registerForm.classList.remove("hidden");
        loginForm.classList.add("hidden");
    }
}

closeAuthModal.addEventListener("click", closeModal);
authModal.addEventListener("click", e => { if (e.target === authModal) closeModal(); });
authTabLogin.addEventListener("click", () => switchAuthTab("login"));
authTabRegister.addEventListener("click", () => switchAuthTab("register"));
openAuthBtn.addEventListener("click", () => openAuthModal("register"));

// Login submit
loginForm.addEventListener("submit", async e => {
    e.preventDefault();
    loginError.classList.add("hidden");
    const btn = loginForm.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "Logging in...";
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: document.getElementById("loginEmail").value, password: document.getElementById("loginPassword").value })
        });
        const data = await res.json();
        if (!res.ok) { loginError.textContent = data.detail || "Login failed."; loginError.classList.remove("hidden"); return; }
        saveAuth(data.token, data.user);
        closeModal();
        onAuthChange();
    } catch (_) {
        loginError.textContent = "Network error. Please try again.";
        loginError.classList.remove("hidden");
    } finally {
        btn.disabled = false; btn.textContent = "Log In";
    }
});

// Register submit
registerForm.addEventListener("submit", async e => {
    e.preventDefault();
    registerError.classList.add("hidden");
    const btn = registerForm.querySelector("button[type=submit]");
    btn.disabled = true; btn.textContent = "Creating account...";
    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: document.getElementById("regEmail").value, password: document.getElementById("regPassword").value })
        });
        const data = await res.json();
        if (!res.ok) { registerError.textContent = data.detail || "Registration failed."; registerError.classList.remove("hidden"); return; }

        if (data.status === "pending_verification") {
            // Account created but email not yet verified — show inbox message
            registerForm.classList.add("hidden");
            const msg = document.createElement("div");
            msg.className = "verify-notice";
            msg.innerHTML = `
                <div class="verify-icon">📬</div>
                <h3>Check your inbox!</h3>
                <p>We've sent a verification link to <strong>${document.getElementById("regEmail").value}</strong>.<br>
                Click the link in the email to activate your account.</p>
            `;
            registerForm.parentNode.insertBefore(msg, registerForm);
            return;
        }

        // Admin email: immediately verified and logged in
        saveAuth(data.token, data.user);
        closeModal();
        onAuthChange();
    } catch (_) {
        registerError.textContent = "Network error. Please try again.";
        registerError.classList.remove("hidden");
    } finally {
        btn.disabled = false; btn.textContent = "Create Account";
    }
});

// Logout
logoutBtn.addEventListener("click", () => {
    clearAuth();
    // Clear matches so the tab doesn't auto-load and show stale/other-user data
    allMatches = [];
    resultsContainer.innerHTML = `<p class="status-msg">Log in to view your saved matches.</p>`;
    nonMatchesPanel.classList.add("hidden");
    nonMatchesVisible = false;
    toggleNonMatches.textContent = "Show Rejected";
    switchView("dashboard");
    onAuthChange();
});

// ─────────────────────────────────────────────────────────────────────────────
// Auth state → UI update
// ─────────────────────────────────────────────────────────────────────────────
async function onAuthChange() {
    if (currentUser) {
        // Show user bar, hide guest banner
        userBar.classList.remove("hidden");
        guestBanner.classList.add("hidden");
        userEmail.textContent = currentUser.email;

        if (currentUser.role === "admin") {
            userRole.textContent = "Admin";
            userRole.className = "role-badge badge-admin";
            usageMeter.classList.add("hidden");
        } else {
            userRole.textContent = "Free";
            userRole.className = "role-badge badge-free";
            await refreshUsageMeter();
        }

        // Show History tab for authenticated users
        tabHistory.classList.remove("hidden");
    } else {
        userBar.classList.add("hidden");
        guestBanner.classList.remove("hidden");
        tabHistory.classList.add("hidden");
        if (document.getElementById("view-history").classList.contains("active")) {
            switchView("dashboard");
        }
    }

    // Reload config (CV might change between auth states)
    loadConfig();

    // Reset matches container on every auth change
    allMatches = [];
    if (currentUser) {
        // Pre-load matches in background so the Matches tab is ready immediately
        resultsContainer.innerHTML = `<p class="status-msg">Loading your matches...</p>`;
        loadOutputs();
    } else {
        resultsContainer.innerHTML = `<p class="status-msg">Log in to view your saved matches.</p>`;
    }
}

async function refreshUsageMeter() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const usage = data.usage;
        const limit = 5; // free tier
        const runs = usage.scout_runs || 0;
        usageLabel.textContent = `${runs} / ${limit} scans used this month`;
        const pct = Math.min((runs / limit) * 100, 100);
        usageBarFill.style.width = `${pct}%`;
        usageBarFill.className = `usage-bar-fill ${pct >= 100 ? "bar-full" : pct >= 60 ? "bar-warn" : ""}`;
        usageMeter.classList.remove("hidden");
    } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Config / CV
// ─────────────────────────────────────────────────────────────────────────────
async function loadConfig() {
    try {
        const res = await fetch(`${API_BASE}/config`, { headers: authHeaders() });
        const data = await res.json();
        if (data.my_cv) cvInput.value = data.my_cv;
        if (data.boards && data.boards.length > 0) {
            boardSelect.innerHTML = "";
            data.boards.forEach(board => {
                const opt = document.createElement("option");
                opt.value = board;
                opt.textContent = board;
                opt.selected = true;
                boardSelect.appendChild(opt);
            });
        }
    } catch (e) { console.error("Failed to load config:", e); }
}

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
        }
    } catch (e) { console.error(e); } finally {
        fillExampleBtn.disabled = false;
        fillExampleBtn.textContent = "Fill with Example";
        setTimeout(() => saveStatus.textContent = "", 3000);
    }
});

saveCvBtn.addEventListener("click", async () => {
    saveCvBtn.disabled = true;
    saveStatus.textContent = "Saving...";
    try {
        const res = await fetch(`${API_BASE}/save-cv`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...authHeaders() },
            body: JSON.stringify({ cv_text: cvInput.value })
        });
        if (res.ok) {
            saveStatus.textContent = "CV saved!";
            saveStatus.style.color = "var(--primary-color)";
        } else throw new Error();
    } catch (_) {
        saveStatus.textContent = "Failed to save.";
        saveStatus.style.color = "#ba1a1a";
    } finally {
        saveCvBtn.disabled = false;
        setTimeout(() => saveStatus.textContent = "", 3000);
    }
});

// ─────────────────────────────────────────────────────────────────────────────
// Role select toggle
// ─────────────────────────────────────────────────────────────────────────────
roleSelect.addEventListener("change", () => {
    customRoleInput.classList.toggle("hidden", roleSelect.value !== "Other");
});

// ─────────────────────────────────────────────────────────────────────────────
// Run Scout
// ─────────────────────────────────────────────────────────────────────────────
executeBtn.addEventListener("click", async () => {
    let targetRole = roleSelect.value;
    if (targetRole === "Other") targetRole = customRoleInput.value.trim();
    if (!targetRole) { alert("Please specify a target role."); return; }

    const selectedBoards = Array.from(boardSelect.selectedOptions).map(opt => opt.value);

    executeBtn.disabled = true;
    executeBtn.textContent = "Starting Scout...";
    executeStatus.textContent = "";
    executeStatus.style.color = "var(--text-color)";

    try {
        const res = await fetch(`${API_BASE}/run-scout`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...authHeaders() },
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

        if (res.status === 429) {
            executeStatus.textContent = data.detail || "Monthly limit reached.";
            executeStatus.style.color = "#ba1a1a";
            if (!currentUser) openAuthModal("register");
            executeBtn.disabled = false;
            executeBtn.textContent = "Start Scouting";
            return;
        }

        executeStatus.textContent = "Scouting in progress... (This may take a few minutes)";
        executeBtn.textContent = "Scouting...";

        const pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetch(`${API_BASE}/status`);
                const statusData = await statusRes.json();

                if (!statusData.is_running) {
                    clearInterval(pollInterval);
                    executeBtn.disabled = false;
                    executeBtn.textContent = "Start Scouting";

                    const skipped = statusData.skipped > 0 ? ` (${statusData.skipped} already-rejected skipped)` : "";
                    if (statusData.matches_found > 0) {
                        executeStatus.textContent = `Finished! Found ${statusData.matches_found} matches${skipped}.`;
                        executeStatus.style.color = "var(--primary-color)";
                        tabMatches.click();
                    } else {
                        executeStatus.textContent = `Finished! No new matches${skipped}.`;
                        executeStatus.style.color = "var(--text-color)";
                    }

                    if (currentUser && currentUser.role !== "admin") refreshUsageMeter();
                } else {
                    executeStatus.textContent = statusData.message || "Scouting in progress...";
                }
            } catch (_) {}
        }, 3000);

    } catch (e) {
        console.error(e);
        executeStatus.textContent = "Failed to start scouting.";
        executeStatus.style.color = "#ba1a1a";
        executeBtn.disabled = false;
        executeBtn.textContent = "Start Scouting";
    }
});

// ─────────────────────────────────────────────────────────────────────────────
// Load Matches + Non-matches
// ─────────────────────────────────────────────────────────────────────────────
async function loadOutputs() {
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Loading...";
    try {
        const res = await fetch(`${API_BASE}/outputs`, { headers: authHeaders() });
        const data = await res.json();
        resultsContainer.innerHTML = "";
        allMatches = data.outputs || [];

        if (allMatches.length > 0) {
            allMatches.forEach((job, index) => {
                const card = document.createElement("div");
                card.className = "match-card";
                card.onclick = () => openMatchDetail(index);
                card.innerHTML = `
                    <h3>${escapeHtml(job.title)}</h3>
                    <p class="card-snippet">${escapeHtml(job.content.substring(0, 160))}...</p>
                `;
                resultsContainer.appendChild(card);
            });
        } else {
            resultsContainer.innerHTML = `<p class="status-msg">No matches found yet. Keep scouting!</p>`;
        }

        // Load non-matches if user is authenticated
        if (currentUser) await loadNonMatches();
    } catch (e) {
        console.error(e);
        resultsContainer.innerHTML = `<p class="status-msg error-msg">Failed to load results.</p>`;
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.textContent = "Refresh";
    }
}

async function loadNonMatches() {
    if (!currentUser) { toggleNonMatches.classList.add("hidden"); return; }
    toggleNonMatches.classList.remove("hidden");
    try {
        const res = await fetch(`${API_BASE}/history/non-matches`, { headers: authHeaders() });
        const data = await res.json();
        const list = data.non_matches || [];
        nonMatchesContainer.innerHTML = "";
        if (list.length === 0) {
            nonMatchesContainer.innerHTML = `<p class="status-msg">No rejected jobs yet.</p>`;
            return;
        }
        list.forEach(nm => {
            const card = document.createElement("div");
            card.className = "non-match-card";
            card.innerHTML = `
                <div class="nm-title">${escapeHtml(nm.job_title || "Unknown")} <span class="nm-company">@ ${escapeHtml(nm.company || "")}</span></div>
                <div class="nm-reason">${escapeHtml(nm.rejection_reason || "")}</div>
                <a href="${escapeHtml(nm.job_url || "#")}" class="nm-url" target="_blank" rel="noopener">${escapeHtml(nm.job_url || "")}</a>
            `;
            nonMatchesContainer.appendChild(card);
        });
    } catch (e) { console.error("Failed to load non-matches:", e); }
}

toggleNonMatches.addEventListener("click", () => {
    nonMatchesVisible = !nonMatchesVisible;
    nonMatchesPanel.classList.toggle("hidden", !nonMatchesVisible);
    toggleNonMatches.textContent = nonMatchesVisible ? "Hide Rejected" : "Show Rejected";
});

refreshBtn.addEventListener("click", loadOutputs);

function openMatchDetail(index) {
    const job = allMatches[index];
    if (!job) return;
    detailTitle.textContent = job.title;
    detailContent.innerHTML = marked.parse(job.content);
    switchView("detail");
}

// ─────────────────────────────────────────────────────────────────────────────
// History view
// ─────────────────────────────────────────────────────────────────────────────
async function loadHistory() {
    if (!currentUser) return;
    historyContainer.innerHTML = `<p class="status-msg">Loading...</p>`;
    try {
        const res = await fetch(`${API_BASE}/history/runs`, { headers: authHeaders() });
        const data = await res.json();
        const runs = data.runs || [];
        historyContainer.innerHTML = "";
        if (runs.length === 0) {
            historyContainer.innerHTML = `<p class="status-msg">No scout runs yet. Go to Dashboard and Start Scouting!</p>`;
            return;
        }
        runs.forEach(run => {
            const date = new Date(run.started_at * 1000).toLocaleString();
            const statusClass = run.status === "done" ? "status-done" : run.status === "error" ? "status-error" : "status-running";
            const card = document.createElement("div");
            card.className = "history-card";
            card.innerHTML = `
                <div class="history-row">
                    <span class="history-role">${escapeHtml(run.target_role)}</span>
                    <span class="run-status ${statusClass}">${run.status}</span>
                </div>
                <div class="history-meta">
                    ${date} · ${run.match_count} match${run.match_count !== 1 ? "es" : ""}
                    ${run.skip_count > 0 ? ` · ${run.skip_count} skipped` : ""}
                    ${run.experience ? ` · ${escapeHtml(run.experience)}` : ""}
                </div>
                <div class="history-boards">${(run.boards || []).map(b => `<span class="board-chip">${escapeHtml(b)}</span>`).join("")}</div>
            `;
            historyContainer.appendChild(card);
        });
    } catch (e) {
        historyContainer.innerHTML = `<p class="status-msg error-msg">Failed to load history.</p>`;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ─────────────────────────────────────────────────────────────────────────────
// Email verification — handle ?token= links from inbox
// ─────────────────────────────────────────────────────────────────────────────
async function checkVerificationToken() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (!token) return;

    // Clean the token from the URL so a refresh doesn't re-send it
    window.history.replaceState({}, document.title, window.location.pathname);

    try {
        const res = await fetch(`${API_BASE}/auth/verify?token=${encodeURIComponent(token)}`);
        const data = await res.json();
        if (res.ok && data.token) {
            saveAuth(data.token, data.user);
            onAuthChange();
            // Show a brief success banner
            const banner = document.createElement("div");
            banner.className = "verify-success-banner";
            banner.textContent = `✅ Email verified! Welcome, ${data.user.email}.`;
            document.body.prepend(banner);
            setTimeout(() => banner.remove(), 5000);
        } else {
            const banner = document.createElement("div");
            banner.className = "verify-error-banner";
            banner.textContent = `⚠️ ${data.detail || "Verification link is invalid or already used."}`;
            document.body.prepend(banner);
            setTimeout(() => banner.remove(), 7000);
        }
    } catch (_) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────────────────────────────────────
loadAuthFromStorage();
onAuthChange();
checkVerificationToken();
