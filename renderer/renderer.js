const apiBaseUrl = window.youGetAMeme?.backendUrl ?? "http://127.0.0.1:8765";

const form = document.querySelector("#search-form");
const situationInput = document.querySelector("#situation");
const statusPill = document.querySelector("#status-pill");
const resultsTitle = document.querySelector("#results-title");
const resultsGrid = document.querySelector("#results-grid");
const candidateTemplate = document.querySelector("#candidate-template");

function setStatus(label, state = "neutral") {
  statusPill.textContent = label;
  statusPill.dataset.state = state;
}

function emptyResults(message) {
  resultsGrid.replaceChildren();
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = message;
  resultsGrid.append(empty);
}

function renderCandidates(candidates) {
  resultsGrid.replaceChildren();

  for (const candidate of candidates) {
    const node = candidateTemplate.content.firstElementChild.cloneNode(true);
    node.querySelector(".candidate-score").textContent = `${Math.round(candidate.confidence * 100)}%`;
    node.querySelector("h3").textContent = candidate.name;
    node.querySelector(".fit").textContent = candidate.fit;
    node.querySelector(".caption").textContent = candidate.caption_idea;
    resultsGrid.append(node);
  }
}

async function checkHealth() {
  try {
    const response = await fetch(`${apiBaseUrl}/api/health`);
    if (!response.ok) {
      throw new Error("Backend did not return OK");
    }
    setStatus("Local API", "ok");
    emptyResults("Type a situation to find a matching meme format.");
  } catch {
    setStatus("Offline", "error");
    emptyResults("The local Python API is not responding.");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const situation = situationInput.value.trim();

  if (situation.length < 3) {
    emptyResults("Give the situation a little more shape.");
    return;
  }

  setStatus("Searching", "busy");
  resultsTitle.textContent = "Searching";

  try {
    const response = await fetch(`${apiBaseUrl}/api/memes/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ situation })
    });

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`);
    }

    const payload = await response.json();
    resultsTitle.textContent = "Best fits";
    renderCandidates(payload.candidates);
    setStatus("Local API", "ok");
  } catch {
    resultsTitle.textContent = "Unavailable";
    emptyResults("Could not reach the local Python API.");
    setStatus("Offline", "error");
  }
});

checkHealth();
