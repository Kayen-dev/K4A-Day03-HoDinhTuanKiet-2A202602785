const STORAGE_KEY = "travel-agent-browser-state-v3";

const defaultProfile = {
  name: "", home_city: "", travel_style: "balanced", budget_level: "mid-range",
  interests: [], dietary_notes: "", mobility_notes: "", preferred_language: "vi",
};
const defaultSettings = {
  provider: "auto", gemini_model: "gemini-2.5-flash", openai_model: "gpt-4o-mini",
  gemini_api_key: "", openai_api_key: "",
};
const state = {
  sessions: [], activeSessionId: null, profile: { ...defaultProfile }, memories: [], serverSettings: {},
};
const $ = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : { error: await response.text() };
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function nowIso() { return new Date().toISOString(); }
function newId(prefix) {
  const value = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  return `${prefix}-${value.replaceAll("-", "").slice(0, 12)}`;
}
function createSession(title = "New trip") {
  const now = nowIso();
  return { id: newId("chat"), title, created_at: now, updated_at: now, messages: [], settings: { ...defaultSettings } };
}
function activeSession() {
  return state.sessions.find((session) => session.id === state.activeSessionId) || null;
}
function saveBrowserState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    sessions: state.sessions, activeSessionId: state.activeSessionId,
    profile: state.profile, memories: state.memories.slice(0, 50),
  }));
}
function loadBrowserState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!saved) return;
    state.profile = { ...defaultProfile, ...(saved.profile || {}) };
    state.memories = Array.isArray(saved.memories) ? saved.memories : [];
    state.sessions = Array.isArray(saved.sessions) ? saved.sessions.map((session) => ({
      ...session,
      messages: Array.isArray(session.messages) ? session.messages : [],
      settings: { ...defaultSettings, ...(session.settings || {}) },
    })) : [];
    state.activeSessionId = saved.activeSessionId;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("vi-VN", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}
function hasKey(settings, keyName, serverFlag) {
  return Boolean(settings?.[keyName] || state.serverSettings?.[serverFlag]);
}
function escapeHtml(value = "") {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function renderProfile() {
  const profile = state.profile;
  const settings = activeSession()?.settings || defaultSettings;
  const items = [
    profile.name && `User: ${profile.name}`,
    profile.home_city && `From: ${profile.home_city}`,
    profile.travel_style && `Style: ${profile.travel_style}`,
    profile.budget_level && `Budget: ${profile.budget_level}`,
    profile.interests?.length && `Interests: ${profile.interests.join(", ")}`,
    hasKey(settings, "gemini_api_key", "has_gemini_key") ? "Gemini: connected" : "Gemini: key needed",
    hasKey(settings, "openai_api_key", "has_openai_key") ? "GPT: connected" : "GPT: fallback key needed",
  ].filter(Boolean);
  $("#profileStrip").innerHTML = items.map((item) => `<span class="profile-pill">${escapeHtml(item)}</span>`).join("");
}
function renderSessions() {
  $("#sessionCount").textContent = state.sessions.length;
  $("#sessionList").innerHTML = state.sessions.map((session) => `
    <div class="session-row ${session.id === state.activeSessionId ? "active" : ""}">
      <button class="session-item" data-session="${session.id}" type="button">
        <strong>${escapeHtml(session.title || "New trip")}</strong>
        <small>${session.messages?.length || 0} messages - ${formatDate(session.updated_at)}</small>
      </button>
      <button class="delete-session" data-delete-session="${session.id}" type="button"
        title="Xóa cuộc trò chuyện" aria-label="Xóa cuộc trò chuyện ${escapeHtml(session.title || "New trip")}">×</button>
    </div>`).join("");
  document.querySelectorAll("[data-session]").forEach((button) => {
    button.addEventListener("click", () => loadSession(button.dataset.session));
  });
  document.querySelectorAll("[data-delete-session]").forEach((button) => {
    button.addEventListener("click", () => deleteSession(button.dataset.deleteSession));
  });
}
function renderMemories() {
  $("#memoryList").innerHTML = state.memories.length ? state.memories.slice(0, 8).map((memory) => `
    <div class="memory-item"><strong>${escapeHtml(memory.content)}</strong><small>${formatDate(memory.created_at)}</small></div>`).join("")
    : `<div class="memory-item"><strong>Chưa có hành trình đã lưu</strong><small>Kế hoạch sẽ xuất hiện sau khi agent trả lời</small></div>`;
}
function renderMessages(session) {
  $("#activeTitle").textContent = session?.title || "Personalized itinerary builder";
  const messages = session?.messages || [];
  $("#messages").innerHTML = messages.length
    ? messages.map((msg, index) => renderMessage(msg, index)).join("")
    : `<div class="message assistant">Chào bạn! Hãy cho mình biết điểm đến, thời gian, ngân sách và sở thích. Agent sẽ kiểm tra dữ liệu thực tế trước khi lập kế hoạch.</div>`;
  
  document.querySelectorAll("[data-delete-msg]").forEach((button) => {
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteMessage(Number(button.dataset.deleteMsg));
    });
  });

  $("#messages").scrollTop = $("#messages").scrollHeight;
}
function renderMessage(message, index) {
  const trace = message.trace ? `<details class="trace"><summary>Xem từng bước Agent</summary><pre>${escapeHtml(JSON.stringify(message.trace, null, 2))}</pre></details>` : "";
  const isUser = message.role === "user";
  return `<div class="message-row ${isUser ? "user-row" : "assistant-row"}">
    <article class="message ${message.role}">${escapeHtml(message.content)}${trace}</article>
    <button class="delete-msg-btn" data-delete-msg="${index}" type="button" title="Xóa dòng chat này" aria-label="Xóa dòng chat">×</button>
  </div>`;
}

function deleteMessage(messageIndex) {
  const session = activeSession();
  if (!session || messageIndex < 0 || messageIndex >= session.messages.length) return;
  session.messages.splice(messageIndex, 1);
  session.updated_at = nowIso();
  saveBrowserState();
  renderSessions();
  renderMessages(session);
}

function loadSession(sessionId) {
  if (!state.sessions.some((session) => session.id === sessionId)) return;
  state.activeSessionId = sessionId;
  saveBrowserState(); renderSessions(); renderProfile(); renderMessages(activeSession());
}
function addSession() {
  const session = createSession();
  state.sessions.unshift(session); state.activeSessionId = session.id;
  saveBrowserState(); renderSessions(); renderProfile(); renderMessages(session);
}
function deleteSession(sessionId) {
  const session = state.sessions.find((item) => item.id === sessionId);
  if (!session || !window.confirm(`Xóa cuộc trò chuyện "${session.title || "New trip"}"?`)) return;
  state.sessions = state.sessions.filter((item) => item.id !== sessionId);
  state.memories = state.memories.filter((memory) => memory.session_id !== sessionId);
  if (!state.sessions.length) state.sessions.push(createSession());
  if (state.activeSessionId === sessionId) state.activeSessionId = state.sessions[0].id;
  saveBrowserState(); renderSessions(); renderProfile(); renderMessages(activeSession()); renderMemories();
}

async function boot() {
  loadBrowserState();
  if (!state.sessions.length) state.sessions.push(createSession());
  if (!state.sessions.some((session) => session.id === state.activeSessionId)) state.activeSessionId = state.sessions[0].id;
  try {
    const serverState = await api("/api/state");
    state.serverSettings = serverState.settings || {};
  } catch { state.serverSettings = {}; }
  saveBrowserState(); renderSessions(); renderProfile(); renderMessages(activeSession()); renderMemories();
  if (!state.profile.name && HTMLDialogElement.prototype.showModal) $("#profileDialog").showModal();
}

$("#newSessionBtn").addEventListener("click", addSession);
$("#deleteActiveSessionBtn")?.addEventListener("click", () => {
  if (state.activeSessionId) deleteSession(state.activeSessionId);
});

$("#chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("#messageInput");
  const message = input.value.trim();
  const session = activeSession();
  if (!message || !session) return;
  const priorMessages = session.messages.slice(-10);
  input.value = ""; $("#sendBtn").disabled = true;
  session.messages.push({ id: newId("msg"), role: "user", content: message, created_at: nowIso() });
  session.updated_at = nowIso();
  if (["New trip", ""].includes(session.title)) session.title = message.slice(0, 46);
  saveBrowserState(); renderSessions(); renderMessages(session);
  $("#messages").insertAdjacentHTML("beforeend", `<article class="message assistant" id="thinking">Mình đang đối chiếu dữ liệu trực tiếp và nhờ mô hình phân tích để tạo kế hoạch phù hợp...</article>`);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  try {
    const payload = await api("/api/chat", { method: "POST", body: JSON.stringify({
      session_id: session.id, message, profile: state.profile, settings: session.settings,
      memories: state.memories.slice(0, 8), conversation_history: priorMessages,
    }) });
    session.messages.push({ id: newId("msg"), role: "assistant", content: payload.answer, trace: payload.trace, created_at: nowIso() });
    if (payload.memory) state.memories.unshift(payload.memory);
  } catch (error) {
    session.messages.push({ id: newId("msg"), role: "assistant", content: `Không thể xử lý yêu cầu: ${error.message}`, created_at: nowIso() });
  } finally {
    session.updated_at = nowIso(); saveBrowserState(); renderSessions(); renderMessages(session); renderMemories();
    $("#sendBtn").disabled = false;
  }
});

$("#profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const profile = Object.fromEntries(new FormData(event.currentTarget).entries());
  profile.interests = profile.interests.split(",").map((item) => item.trim()).filter(Boolean);
  try {
    const result = await api("/api/profile", { method: "POST", body: JSON.stringify(profile) });
    state.profile = { ...defaultProfile, ...result.profile };
    saveBrowserState(); renderProfile(); $("#profileDialog").close();
  } catch (error) { window.alert(`Không thể lưu hồ sơ: ${error.message}`); }
});
$("#skipProfileBtn").addEventListener("click", () => $("#profileDialog").close());
$("#settingsBtn").addEventListener("click", () => {
  const form = $("#settingsForm");
  const settings = activeSession()?.settings || defaultSettings;
  form.elements.gemini_model.value = settings.gemini_model;
  form.elements.openai_model.value = settings.openai_model;
  form.elements.gemini_api_key.value = ""; form.elements.openai_api_key.value = "";
  $("#settingsDialog").showModal();
});
$("#closeSettingsBtn").addEventListener("click", () => $("#settingsDialog").close());
$("#settingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const session = activeSession();
  if (!session) return;
  const incoming = Object.fromEntries(new FormData(event.currentTarget).entries());
  const merged = { ...session.settings, ...incoming, provider: "auto" };
  if (!incoming.gemini_api_key) merged.gemini_api_key = session.settings.gemini_api_key;
  if (!incoming.openai_api_key) merged.openai_api_key = session.settings.openai_api_key;
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify(merged) });
    session.settings = merged; saveBrowserState(); renderProfile(); $("#settingsDialog").close();
  } catch (error) { window.alert(`Không thể lưu API key: ${error.message}`); }
});

boot().catch((error) => {
  $("#messages").innerHTML = `<article class="message assistant">${escapeHtml(error.message)}</article>`;
});
