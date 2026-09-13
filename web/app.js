const state = {
  sessions: [],
  activeSessionId: null,
  profile: {},
  settings: {},
};

const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Request failed");
  return payload;
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function renderProfile() {
  const profile = state.profile || {};
  const items = [
    profile.name && `User: ${profile.name}`,
    profile.home_city && `From: ${profile.home_city}`,
    profile.travel_style && `Style: ${profile.travel_style}`,
    profile.budget_level && `Budget: ${profile.budget_level}`,
    profile.interests?.length && `Interests: ${profile.interests.join(", ")}`,
    state.settings?.has_gemini_key ? "Gemini: connected" : "Gemini: key needed",
    state.settings?.has_openai_key ? "GPT: connected" : "GPT: fallback key needed",
  ].filter(Boolean);
  $("#profileStrip").innerHTML = items.map((item) => `<span class="profile-pill">${escapeHtml(item)}</span>`).join("");
}

function renderSessions() {
  $("#sessionCount").textContent = state.sessions.length;
  $("#sessionList").innerHTML = state.sessions
    .map(
      (session) => `
        <button class="session-item ${session.id === state.activeSessionId ? "active" : ""}" data-session="${session.id}" type="button">
          <strong>${escapeHtml(session.title || "New trip")}</strong>
          <small>${session.message_count ?? session.messages?.length ?? 0} messages - ${formatDate(session.updated_at)}</small>
        </button>
      `,
    )
    .join("");
  document.querySelectorAll("[data-session]").forEach((button) => {
    button.addEventListener("click", () => loadSession(button.dataset.session));
  });
}

function renderMemories(memories = []) {
  $("#memoryList").innerHTML = memories.length
    ? memories
        .map(
          (memory) => `
            <div class="memory-item">
              <strong>${escapeHtml(memory.content)}</strong>
              <small>${formatDate(memory.created_at)}</small>
            </div>
          `,
        )
        .join("")
    : `<div class="memory-item"><strong>No saved travel memory yet</strong><small>Plans appear after each answer</small></div>`;
}

function renderMessages(session) {
  $("#activeTitle").textContent = session?.title || "Personalized itinerary builder";
  const messages = session?.messages || [];
  $("#messages").innerHTML = messages.length
    ? messages.map(renderMessage).join("")
    : `<div class="message assistant">ChÃ o báº¡n. HÃ£y Ä‘iá»n profile cÆ¡ báº£n, sau Ä‘Ã³ há»i mÃ¬nh vá» má»™t chuyáº¿n Ä‘i. MÃ¬nh sáº½ gá»i MCP tools Ä‘á»ƒ kiá»ƒm tra thá»i tiáº¿t, Ä‘á»‹a Ä‘iá»ƒm vÃ  khoáº£ng cÃ¡ch trÆ°á»›c khi láº­p lá»‹ch trÃ¬nh.</div>`;
  $("#messages").scrollTop = $("#messages").scrollHeight;
}

function renderMessage(message) {
  const trace = message.trace
    ? `<details class="trace"><summary>View MCP trace</summary><pre>${escapeHtml(JSON.stringify(message.trace, null, 2))}</pre></details>`
    : "";
  return `<article class="message ${message.role}">${escapeHtml(message.content)}${trace}</article>`;
}

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function boot() {
  const payload = await api("/api/state");
  state.profile = payload.profile;
  state.settings = payload.settings;
  state.sessions = payload.sessions;
  renderProfile();
  renderMemories(payload.memories);
  if (!state.profile?.name && HTMLDialogElement.prototype.showModal) {
    $("#profileDialog").showModal();
  }
  if (state.sessions.length) {
    await loadSession(state.sessions[0].id);
  } else {
    const created = await api("/api/sessions", { method: "POST", body: JSON.stringify({ title: "New trip" }) });
    state.sessions.unshift(created.session);
    state.activeSessionId = created.session.id;
    renderSessions();
    renderMessages(created.session);
  }
}

async function refreshSessions() {
  const payload = await api("/api/sessions");
  state.sessions = payload.sessions;
  renderSessions();
}

async function loadSession(sessionId) {
  state.activeSessionId = sessionId;
  const payload = await api(`/api/sessions/${sessionId}`);
  renderSessions();
  renderMessages(payload.session);
}

$("#newSessionBtn").addEventListener("click", async () => {
  const payload = await api("/api/sessions", { method: "POST", body: JSON.stringify({ title: "New trip" }) });
  state.sessions.unshift(payload.session);
  state.activeSessionId = payload.session.id;
  renderSessions();
  renderMessages(payload.session);
});

$("#chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#messageInput");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  $("#sendBtn").disabled = true;
  const temp = { role: "user", content: message };
  $("#messages").insertAdjacentHTML("beforeend", renderMessage(temp));
  $("#messages").insertAdjacentHTML("beforeend", `<article class="message assistant" id="thinking">Checking live APIs and building your itinerary...</article>`);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  try {
    const payload = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: state.activeSessionId, message }),
    });
    state.activeSessionId = payload.session.id;
    await refreshSessions();
    renderMessages(payload.session);
    const fresh = await api("/api/state");
    state.profile = fresh.profile;
    state.settings = fresh.settings;
    renderProfile();
    renderMemories(fresh.memories);
  } catch (error) {
    $("#thinking").textContent = error.message;
  } finally {
    $("#sendBtn").disabled = false;
  }
});

$("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.interests = payload.interests.split(",").map((item) => item.trim()).filter(Boolean);
  const result = await api("/api/profile", { method: "POST", body: JSON.stringify(payload) });
  state.profile = result.profile;
  renderProfile();
  $("#profileDialog").close();
});

$("#skipProfileBtn").addEventListener("click", () => $("#profileDialog").close());
$("#settingsBtn").addEventListener("click", () => $("#settingsDialog").showModal());
$("#closeSettingsBtn").addEventListener("click", () => $("#settingsDialog").close());

$("#settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  payload.provider = "auto";
  const result = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
  state.settings = result.settings;
  renderProfile();
  $("#settingsDialog").close();
});

boot().catch((error) => {
  $("#messages").innerHTML = `<article class="message assistant">${escapeHtml(error.message)}</article>`;
});

