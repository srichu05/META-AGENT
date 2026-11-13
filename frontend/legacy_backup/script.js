// Meta-Agent Math Debate System - Frontend B+ (Backend v2+ compatible)
// Path: /frontend/script.js

class MathDebateSystem {
    constructor() {
        this.baseUrl = "http://127.0.0.1:5000/api";
        this.sampleProblems = [];
        this.agentColorCache = new Map();
        this.materialPalette = this.getMaterialPalette();
        this.fixedRoleColors = {
            judge: "#43A047",
            meta: "#5E35B1",
        };
        this.init();
    }

    init() {
        this.setupTabs();
        this.setupEventListeners();
        this.createLoadingOverlay();
        this.loadSampleProblems();
        this.attachKeyboardShortcuts();
        console.log("✅ Frontend B+ ready (backend v2+ compatible)");
    }

    async makeRequest(endpoint, method = "GET", data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const opts = {
            method,
            headers: { "Content-Type": "application/json" },
            body: data ? JSON.stringify(data) : undefined,
        };

        let res, json;
        try {
            res = await fetch(url, opts);
            json = await res.json();
        } catch (e) {
            throw new Error("Network error. Check if backend is running at 127.0.0.1:5000");
        }

        if (!json || json.success === false || !res.ok) {
            const msg = (json && (json.error || json.message)) || `HTTP ${res?.status || 500} error`;
            throw new Error(msg);
        }

        return "data" in json && json.data ? json.data : json;
    }

    createLoadingOverlay() {
        if (document.getElementById("loading-overlay")) return;
        const overlay = document.createElement("div");
        overlay.id = "loading-overlay";
        overlay.innerHTML = `
          <div class="loading-spinner-container">
            <div class="loading-spinner"></div>
            <div class="loading-text">Processing...</div>
          </div>
        `;
        document.body.appendChild(overlay);
    }

    showLoading(show = true, text = "Processing...") {
        const overlay = document.getElementById("loading-overlay");
        if (!overlay) return;
        overlay.style.display = show ? "flex" : "none";
        const t = overlay.querySelector(".loading-text");
        if (t) t.textContent = text;
    }

    showToast(message, type = "success") {
        const container = document.getElementById("toast-container") || document.body;
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `
          <span class="toast-icon">${type === "success" ? "✅" : "❌"}</span>
          <span class="toast-message">${this.escapeHtml(message)}</span>
          <button class="toast-close" aria-label="Close" onclick="this.parentElement.remove()">×</button>
        `;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    autoScrollIntoView(el) {
        if (!el) return;
        el.style.display = "block";
        el.classList.add("fade-in");
        el.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    setupTabs() {
        const tabButtons = Array.from(document.querySelectorAll(".tab-btn"));
        const tabContents = Array.from(document.querySelectorAll(".tab-content"));

        const activate = (name) => {
            tabButtons.forEach(b => b.classList.toggle("active", b.dataset.tab === name));
            tabContents.forEach(c => c.classList.toggle("active", c.id === `${name}-tab`));

            if (name === "stats") {
                this.loadSystemStats();
            } else if (name === "evaluation") {
                this.loadEvaluationMetrics();
            } else if (name === "corpus") {
                this.loadCorpusPreview();
            }
        };

        tabButtons.forEach(btn => {
            btn.addEventListener("click", () => activate(btn.dataset.tab));
        });

        const activeBtn = tabButtons.find(b => b.classList.contains("active")) || tabButtons[0];
        if (activeBtn) activate(activeBtn.dataset.tab);
    }

    attachKeyboardShortcuts() {
        const solveInput = document.getElementById("problem-input");
        const debateInput = document.getElementById("debate-problem-input");
        solveInput?.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.key === "Enter") this.solveProblem();
        });
        debateInput?.addEventListener("keydown", (e) => {
            if (e.ctrlKey && e.key === "Enter") this.startDebate();
        });
    }

    setupEventListeners() {
        document.getElementById("solve-btn")?.addEventListener("click", () => this.solveProblem());
        document.getElementById("load-sample-btn")?.addEventListener("click", () => this.loadRandomSample());
        document.getElementById("start-debate-btn")?.addEventListener("click", () => this.startDebate());
        document.getElementById("analyze-btn")?.addEventListener("click", () => this.analyzeProblem());
        document.getElementById("refresh-stats-btn")?.addEventListener("click", () => this.loadSystemStats());
        document.getElementById("upload-corpus-btn")?.addEventListener("click", () => this.uploadCorpus());
    }

    /* ------------------------------- SOLVE FLOW ------------------------------ */
    async solveProblem() {
        const input = document.getElementById("problem-input");
        const problem = (input?.value || "").trim();
        if (!problem) return this.showToast("Please enter a math problem", "error");

        try {
            this.showLoading(true, "Solving problem...");
            const data = await this.makeRequest("/solve", "POST", { problem });
            this.displaySolutionResult(data);
            this.showToast("Problem solved successfully!", "success");
        } catch (err) {
            this.displaySolutionError(err.message);
            this.showToast(err.message, "error");
        } finally {
            this.showLoading(false);
        }
    }

    displaySolutionResult(data) {
        const resultContainer = document.getElementById("solution-result");
        const bestAgent = document.getElementById("best-agent");
        const finalAnswer = document.getElementById("final-answer");
        const confidenceScore = document.getElementById("confidence-score");
        const solveTime = document.getElementById("solve-time");
        const solutionText = document.getElementById("solution-text");
        const similarProblemsList = document.getElementById("similar-problems-list");

        const {
            best_agent,
            solver_used,
            answer,
            confidence,
            total_time,
            solution,
            rag_used,
            rag_context_count,
            api_used,
            api_latency_ms,
        } = data;

        if (bestAgent) bestAgent.textContent = solver_used || best_agent || "Unknown Agent";
        if (finalAnswer) finalAnswer.textContent = answer ?? "No answer";
        if (confidenceScore) confidenceScore.textContent = `${((confidence || 0) * 100).toFixed(1)}%`;
        if (solveTime) solveTime.textContent = `${(total_time || 0).toFixed(2)}s`;
        if (solutionText) {
            // Clean up raw LLM answer – remove special tokens like [*] or <...> that are not HTML
            const cleanSolution = this.sanitizeAnswer(solution);
            solutionText.innerHTML = this.formatSolutionText(cleanSolution);
        }

        if (similarProblemsList) {
            const used = !!rag_used;
            const count = rag_context_count || 0;
            similarProblemsList.innerHTML = used
                ? `<div class="similar-problems-info"><strong>${count}</strong> similar problems used <span class="context-badge">RAG Enhanced</span></div>`
                : `<div class="similar-problems-info">No similar problems used <span class="context-badge">Direct Solve</span></div>`;
        }

        const provider = api_used || "—";
        const latency = api_latency_ms != null ? `${api_latency_ms} ms` : "—";

        const footer = document.getElementById("solution-provider-footer")
            || document.createElement("div");
        footer.id = "solution-provider-footer";
        footer.className = "provider-footer";
        footer.innerHTML = `⚡ Provider: <strong>${provider}</strong> • ${latency}`;

        if (resultContainer && !resultContainer.contains(footer)) {
            resultContainer.appendChild(footer);
        }

        this.autoScrollIntoView(resultContainer);
    }

    displaySolutionError(errorMessage) {
        const resultContainer = document.getElementById("solution-result");
        const bestAgent = document.getElementById("best-agent");
        const finalAnswer = document.getElementById("final-answer");
        const solutionText = document.getElementById("solution-text");

        if (bestAgent) bestAgent.textContent = "Error";
        if (finalAnswer) finalAnswer.textContent = "Failed to solve";
        if (solutionText) solutionText.innerHTML = `<div class="error-message">❌ ${this.escapeHtml(errorMessage)}</div>`;

        const footer = document.getElementById("solution-provider-footer");
        if (footer) footer.remove();

        this.autoScrollIntoView(resultContainer);
    }

    /* ------------------------------ DEBATE FLOW ------------------------------ */
    async startDebate() {
        const input = document.getElementById("debate-problem-input");
        const roundsInput = document.getElementById("debate-rounds");
        const problem = (input?.value || "").trim();
        const rounds = parseInt(roundsInput?.value || "3", 10);

        if (!problem) return this.showToast("Please enter a problem for debate", "error");

        try {
            this.showLoading(true, `Running ${rounds} rounds of debate...`);
            const data = await this.makeRequest("/debate", "POST", { problem, rounds });
            this.displayDebateResult(data);
            this.showToast("Debate completed successfully!", "success");
        } catch (err) {
            this.displayDebateError(err.message);
            this.showToast(err.message, "error");
        } finally {
            this.showLoading(false);
        }
    }

    displayDebateResult(data) {
        const { debate_winner, final_solution, debate_rounds, debate_history } = data;

        const winner = document.getElementById("debate-winner");
        const solution = document.getElementById("debate-solution");
        const roundsCount = document.getElementById("debate-rounds-count");
        const timeline = document.getElementById("debate-timeline");
        const container = document.getElementById("debate-result");

        if (winner) {
            winner.textContent = debate_winner || "Unknown";
            winner.style.fontWeight = "bold";
            winner.classList.remove("error-text");
        }

        if (solution) {
            solution.innerHTML = this.formatSolutionText(final_solution || "No solution");
        }

        if (roundsCount) {
            roundsCount.textContent = debate_rounds || 0;
        }

        if (timeline) {
            timeline.innerHTML = this.buildDebateTimeline(debate_history);
        }

        if (debate_winner && container) {
            container.style.setProperty("--winner-color", this.getAgentColor(debate_winner));
            container.setAttribute("data-winner", `Winner: ${debate_winner}`);
        }

        this.autoScrollIntoView(container);
    }

    displayDebateError(errorMessage) {
        const container = document.getElementById("debate-result");
        const winner = document.getElementById("debate-winner");
        const solution = document.getElementById("debate-solution");
        const roundsCount = document.getElementById("debate-rounds-count");
        const timeline = document.getElementById("debate-timeline");

        if (winner) {
            winner.textContent = "Error";
            winner.classList.add("error-text");
        }
        if (solution) {
            solution.innerHTML = `<div class="error-message">❌ Debate failed: ${this.escapeHtml(errorMessage)}</div>`;
        }
        if (roundsCount) roundsCount.textContent = "0";
        if (timeline) {
            timeline.innerHTML = `
                <div class="error-timeline">
                  <div class="error-icon">❌</div>
                  <div class="error-title">Debate System Error</div>
                  <div class="error-details">${this.escapeHtml(errorMessage)}</div>
                  <div class="error-suggestion">Please try again with a different problem.</div>
                </div>
            `;
        }
        this.autoScrollIntoView(container);
    }

    buildDebateTimeline(history) {
        if (!history || !Array.isArray(history.rounds) || history.rounds.length === 0) {
            return `<div class="no-timeline">No debate timeline available.</div>`;
        }

        const rounds = history.rounds || [];
        let html = `<div class="debate-timeline">`;

        rounds.forEach((round, idx) => {
            const roundIdx = round.round || idx + 1;
            const ts = round.timestamp ? new Date(round.timestamp) : null;
            const tsStr = ts ? ts.toLocaleTimeString() : "—";

            html += `
                <div class="debate-round card">
                  <div class="round-header">
                    <h4>🎪 Round ${roundIdx}</h4>
                    <span class="round-time">${tsStr}</span>
                  </div>
                  <div class="round-content">
                    ${this.renderRoundCritiques(round.critiques)}
                  </div>
                </div>
            `;
        });

        const final = history.final_decision || {};
        html += `
            <div class="final-decision card">
              <div class="decision-header"><h4>⚖️ Final Judgment</h4></div>
              <div class="decision-content">
                <div class="winner-announcement">
                  <strong>🏅 Winner:</strong> ${this.escapeHtml(final.best_agent || "Unknown")}
                </div>
                <div class="decision-reasoning">
                  <strong>📝 Reasoning:</strong> ${this.escapeHtml(final.evaluation_reasoning || "No reasoning provided")}
                </div>
                ${typeof final.confidence === "number"
                ? `<div class="decision-confidence"><strong>🎯 Confidence:</strong> ${(final.confidence * 100).toFixed(1)}%</div>`
                : ""
            }
              </div>
            </div>
        `;

        html += `</div>`;
        return html;
    }

    renderRoundCritiques(critiques) {
        if (!critiques || typeof critiques !== "object") {
            return `<div class="no-content">No agent contributions in this round.</div>`;
        }

        let html = "";
        Object.entries(critiques).forEach(([agentName, content]) => {
            const color = this.getAgentColor(agentName);
            const isError = typeof content === "string" && content.toLowerCase().includes("error");
            const badge = isError
                ? `<span class="badge badge-error">Error</span>`
                : `<span class="badge badge-active">Active</span>`;

            html += `
                <div class="agent-contribution" style="--agent-color:${color}">
                  <div class="agent-header">
                    <span class="agent-dot" style="background:${color}"></span>
                    <strong class="agent-name" title="${this.escapeHtml(agentName)}">${this.escapeHtml(agentName)}</strong>
                    ${badge}
                  </div>
                  <div class="agent-content">
                    ${this.formatAgentContent(content)}
                  </div>
                </div>
            `;
        });

        return html;
    }

    /* ------------------------------ ANALYZE FLOW ----------------------------- */
    async analyzeProblem() {
        const input = document.getElementById("analyze-input");
        const problem = (input?.value || "").trim();
        if (!problem) return this.showToast("Please enter a problem to analyze", "error");

        try {
            this.showLoading(true, "Analyzing problem...");
            const data = await this.makeRequest("/analyze", "POST", { problem });
            this.displayAnalysisResult(data);
            this.showToast("Problem analyzed successfully!", "success");
        } catch (err) {
            this.showToast(err.message, "error");
        } finally {
            this.showLoading(false);
        }
    }

    displayAnalysisResult(data) {
        const resultContainer = document.getElementById("analysis-result");
        const problemType = document.getElementById("problem-type");
        const keyConcepts = document.getElementById("key-concepts");
        const difficultyLevel = document.getElementById("difficulty-level");
        const solutionApproaches = document.getElementById("solution-approaches");
        const hintsList = document.getElementById("hints-list");

        if (problemType) problemType.textContent = data.problem_type || "Unknown";
        if (keyConcepts) keyConcepts.textContent = data.concepts || "Not identified";
        if (difficultyLevel) difficultyLevel.textContent = data.difficulty || "Medium";
        if (solutionApproaches) solutionApproaches.textContent = data.approaches || "Standard approach";

        const hints = data.hints || [];
        if (hintsList) {
            hintsList.innerHTML = hints.length
                ? hints.map((h, i) => `<li><span class="hint-number">${i + 1}.</span> ${this.escapeHtml(h)}</li>`).join("")
                : `<li>No specific hints available for this problem.</li>`;
        }

        this.autoScrollIntoView(resultContainer);
    }

    /* --------------------------------- STATS --------------------------------- */
    async loadSystemStats() {
        try {
            this.showLoading(true, "Loading system statistics...");
            const data = await this.makeRequest("/stats");
            this.displaySystemStats(data.stats || data);
        } catch (err) {
            this.showToast(`Error loading stats: ${err.message}`, "error");
        } finally {
            this.showLoading(false);
        }
    }

    displaySystemStats(stats) {
        const totalProblemsEl = document.getElementById("total-problems");
        const activeAgentsEl = document.getElementById("active-agents");
        const memoryUsageEl = document.getElementById("memory-usage");
        const vectorDimensionEl = document.getElementById("vector-dimension");

        if (totalProblemsEl) totalProblemsEl.textContent = stats?.vector_store_stats?.total_documents ?? 0;
        if (activeAgentsEl) activeAgentsEl.textContent = stats?.agent_count ?? 0;
        if (memoryUsageEl) memoryUsageEl.textContent = `${(stats?.vector_store_stats?.memory_usage_mb ?? 0).toFixed(1)} MB`;
        if (vectorDimensionEl) vectorDimensionEl.textContent = stats?.vector_store_stats?.dimension ?? 384;
    }

    /* ---------------------------- SAMPLE PROBLEMS ---------------------------- */
    async loadSampleProblems() {
        try {
            const data = await this.makeRequest("/problems");
            const arr = data.problems || data || [];
            if (Array.isArray(arr) && arr.length) {
                this.sampleProblems = arr
                    .map(p => (typeof p === "string" ? p : (p?.problem || "")))
                    .filter(Boolean);
            }
        } catch {
            this.sampleProblems = [
                "A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes and pays with a $50 bill, how much change will she receive?",
                "A rectangular garden is 12 meters long and 8 meters wide. What is the perimeter of the garden?",
                "Tom has 24 marbles. He gives 1/3 of them to his friend and 1/4 of the remaining marbles to his sister. How many marbles does Tom have left?",
                "A car travels at 60 mph for 2.5 hours. How far does the car travel?",
                "The sum of two consecutive even numbers is 46. What are the two numbers?",
            ];
        }
    }

    loadRandomSample() {
        if (!this.sampleProblems.length) {
            return this.showToast("No sample problems loaded yet.", "error");
        }
        const idx = Math.floor(Math.random() * this.sampleProblems.length);
        const problemInput = document.getElementById("problem-input");
        if (problemInput) {
            problemInput.value = this.sampleProblems[idx];
            this.showToast("Sample problem loaded!", "success");
        }
    }

    /* ----------------------------- RENDER HELPERS ---------------------------- */
    formatSolutionText(text) {
        if (!text) return "No solution provided";
        // Split the raw text into separate lines
        const lines = text.split('\n');
        // Process each line individually and wrap it in its own div
        const formattedLines = lines.map(line => {
            let formatted = this.escapeHtml(line);
            // Highlight numbers
            formatted = formatted.replace(/(\d+\.?\d*)/g, `<span class="number">$1</span>`);
            // Highlight operators
            formatted = formatted.replace(/(=|×|÷|\+|-)/g, `<span class="operator">$1</span>`);
            // Highlight step markers
            formatted = formatted.replace(/(Step \d+:|First,|Then,|Next,|Finally,)/gi, `<strong class="step-marker">$1</strong>`);
            return `<div class="solution-line">${formatted}</div>`;
        });
        // Join all line divs together – no extra <br> needed
        return formattedLines.join('');
    }

    sanitizeAnswer(text) {
        if (!text) return '';
        let cleaned = text;
        // 1. Remove token markers like [*] or (*)
        cleaned = cleaned.replace(/[\[\*\]]|\(\*\)/g, '');
        // 2. Strip HTML tags that may be present
        cleaned = cleaned.replace(/<[^>]*>/g, '');
        // 3. Remove escaped HTML fragments like ="number"> or ="operator">
        cleaned = cleaned.replace(/=\s*"[^"]*"\s*>/g, '');
        // 4. Remove HTML entities (e.g., &#039;)
        cleaned = cleaned.replace(/&#\d+;|&#[A-Za-z]+;/g, '');
        // 5. Remove markdown bold (**text**) and other asterisks
        cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '$1');
        cleaned = cleaned.replace(/\*(.*?)\*/g, '$1');
        // 6. Remove markdown list bullets or leading dashes
        cleaned = cleaned.replace(/^\s*[\*-]\s+/gm, '');
        // 7. Collapse multiple spaces (excluding newlines) into a single space
        cleaned = cleaned.replace(/[ \t]+/g, ' ');
        return cleaned.trim();
    }

    formatAgentContent(content) {
        if (content == null) return "No content provided";
        if (typeof content !== "string") content = String(content);
        const lower = content.toLowerCase();
        if (lower.includes("error:")) {
            return `<div class="error-content">${this.escapeHtml(content)}</div>`;
        }
        return `<div class="agent-text">${this.escapeHtml(content)}</div>`;
    }

    escapeHtml(str) {
        return String(str)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    getMaterialPalette() {
        return [
            "#1E88E5", "#00897B", "#8E24AA", "#F4511E",
            "#3949AB", "#00ACC1", "#7CB342", "#FB8C00",
            "#5C6BC0", "#26A69A", "#AB47BC", "#42A5F5",
        ];
    }

    colorFromName(name) {
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = (hash << 5) - hash + name.charCodeAt(i);
            hash |= 0;
        }
        const idx = Math.abs(hash) % this.materialPalette.length;
        return this.materialPalette[idx];
    }

    getAgentColor(agentName = "") {
        if (!agentName) return "#9E9E9E";
        const lower = agentName.toLowerCase();
        if (lower.includes("judge")) return this.fixedRoleColors.judge;
        if (lower.includes("meta")) return this.fixedRoleColors.meta;

        if (this.agentColorCache.has(agentName)) {
            return this.agentColorCache.get(agentName);
        }
        const color = this.colorFromName(agentName);
        this.agentColorCache.set(agentName, color);
        return color;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.mathDebateSystem = new MathDebateSystem();
});
