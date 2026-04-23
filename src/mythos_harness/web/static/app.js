(function () {
  "use strict";

  const SESSION_KEY = "mythos.console.sessions.v1";
  const SETTINGS_KEY = "mythos.console.settings.v1";

  const dom = {
    newSessionBtn: document.getElementById("newSessionBtn"),
    sessionsList: document.getElementById("sessionsList"),
    sessionCountBadge: document.getElementById("sessionCountBadge"),
    activeTitle: document.getElementById("activeTitle"),
    threadIdTag: document.getElementById("threadIdTag"),
    healthTag: document.getElementById("healthTag"),
    copyTranscriptBtn: document.getElementById("copyTranscriptBtn"),
    clearSessionBtn: document.getElementById("clearSessionBtn"),
    timeline: document.getElementById("messageTimeline"),
    composerInput: document.getElementById("composerInput"),
    sendBtn: document.getElementById("sendBtn"),
    runMetaCards: document.getElementById("runMetaCards"),
    triagePanel: document.getElementById("triagePanel"),
    apiBaseUrlInput: document.getElementById("apiBaseUrlInput"),
    apiKeyInput: document.getElementById("apiKeyInput"),
    messageTemplate: document.getElementById("messageTemplate"),
  };

  const state = {
    sessions: [],
    activeSessionId: null,
    settings: {
      apiBaseUrl: window.location.origin,
      apiKey: "",
    },
    pending: false,
  };

  init();

  function init() {
    loadState();
    bindEvents();
    render();
    scheduleHealthProbe();
  }

  function loadState() {
    const savedSessions = safeParse(localStorage.getItem(SESSION_KEY), []);
    const savedSettings = safeParse(localStorage.getItem(SETTINGS_KEY), {});
    if (Array.isArray(savedSessions) && savedSessions.length > 0) {
      state.sessions = savedSessions;
      state.activeSessionId = savedSessions[0].id;
    } else {
      const session = createSession("New Conversation");
      state.sessions = [session];
      state.activeSessionId = session.id;
    }
    state.settings = {
      ...state.settings,
      ...(typeof savedSettings === "object" && savedSettings ? savedSettings : {}),
    };
    dom.apiBaseUrlInput.value = state.settings.apiBaseUrl;
    dom.apiKeyInput.value = state.settings.apiKey;
  }

  function bindEvents() {
    dom.newSessionBtn.addEventListener("click", () => {
      const session = createSession("New Conversation");
      state.sessions.unshift(session);
      state.activeSessionId = session.id;
      persistSessions();
      render();
    });

    dom.sendBtn.addEventListener("click", submitPrompt);
    dom.composerInput.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        submitPrompt();
      }
    });
    dom.composerInput.addEventListener("input", autoSizeComposer);
    dom.copyTranscriptBtn.addEventListener("click", copyTranscript);
    dom.clearSessionBtn.addEventListener("click", clearActiveSession);
    dom.apiBaseUrlInput.addEventListener("blur", () => {
      state.settings.apiBaseUrl = normalizeBaseUrl(dom.apiBaseUrlInput.value);
      dom.apiBaseUrlInput.value = state.settings.apiBaseUrl;
      persistSettings();
      probeHealth();
    });
    dom.apiKeyInput.addEventListener("blur", () => {
      state.settings.apiKey = dom.apiKeyInput.value.trim();
      persistSettings();
    });
  }

  function createSession(title) {
    const now = new Date().toISOString();
    return {
      id: `s-${Math.random().toString(36).slice(2, 10)}`,
      title,
      thread_id: `thread-${Math.random().toString(36).slice(2, 10)}`,
      messages: [
        {
          role: "assistant",
          content:
            "Welcome to Mythos Console. Ask a question to run the orchestration loop.",
          created_at: now,
        },
      ],
      last_result: null,
      created_at: now,
      updated_at: now,
    };
  }

  function render() {
    renderSessions();
    renderActiveSession();
    autoSizeComposer();
  }

  function renderSessions() {
    dom.sessionsList.innerHTML = "";
    state.sessions.forEach((session) => {
      const item = document.createElement("button");
      item.className =
        "session-item" +
        (session.id === state.activeSessionId ? " active" : "");
      item.type = "button";
      item.innerHTML = `
        <div class="session-title">${escapeHtml(session.title)}</div>
        <div class="session-meta">${formatDate(session.updated_at)}</div>
      `;
      item.addEventListener("click", () => {
        state.activeSessionId = session.id;
        render();
      });
      dom.sessionsList.appendChild(item);
    });
    dom.sessionCountBadge.textContent = String(state.sessions.length);
  }

  function renderActiveSession() {
    const session = getActiveSession();
    if (!session) {
      return;
    }
    dom.activeTitle.textContent = session.title;
    dom.threadIdTag.textContent = `thread: ${session.thread_id}`;

    dom.timeline.innerHTML = "";
    session.messages.forEach((message) => {
      const fragment = dom.messageTemplate.content.cloneNode(true);
      const root = fragment.querySelector(".msg");
      root.classList.add(message.role);
      if (message.error) {
        root.classList.add("error");
      }
      fragment.querySelector(".msg-role").textContent = message.role;
      fragment.querySelector(".msg-time").textContent = formatDate(
        message.created_at
      );
      fragment.querySelector(".msg-body").innerHTML = markdownToHtml(
        message.content || ""
      );
      dom.timeline.appendChild(fragment);
    });

    renderMeta(session.last_result);
    dom.timeline.scrollTop = dom.timeline.scrollHeight;
  }

  function renderMeta(result) {
    const items = [
      ["loops", result ? String(result.loops ?? "-") : "-"],
      ["halt_reason", result ? String(result.halt_reason ?? "-") : "-"],
      ["overall_conf", result ? formatConfidence(result.confidence_summary) : "-"],
      ["trajectory_id", result ? String(result.trajectory_id ?? "-") : "-"],
    ];
    dom.runMetaCards.innerHTML = "";
    items.forEach(([label, value]) => {
      const card = document.createElement("article");
      card.className = "meta-card";
      card.innerHTML = `<div class="meta-label">${escapeHtml(
        label
      )}</div><div class="meta-value">${escapeHtml(value)}</div>`;
      dom.runMetaCards.appendChild(card);
    });
    dom.triagePanel.textContent = JSON.stringify(
      result ? result.triage || {} : {},
      null,
      2
    );
  }

  async function submitPrompt() {
    const session = getActiveSession();
    const prompt = dom.composerInput.value.trim();
    if (!session || !prompt || state.pending) {
      return;
    }
    state.pending = true;
    dom.sendBtn.disabled = true;
    appendMessage(session, {
      role: "user",
      content: prompt,
      created_at: new Date().toISOString(),
    });
    dom.composerInput.value = "";
    autoSizeComposer();

    const placeholder = {
      role: "assistant",
      content: "Running Mythos orchestration...",
      created_at: new Date().toISOString(),
    };
    appendMessage(session, placeholder);
    render();

    try {
      const payload = {
        query: prompt,
        thread_id: session.thread_id,
        constraints: {},
      };
      const response = await fetch(
        `${state.settings.apiBaseUrl}/v1/mythos/complete`,
        {
          method: "POST",
          headers: buildHeaders(),
          body: JSON.stringify(payload),
        }
      );
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status} - ${truncate(errorText, 240)}`);
      }
      const result = await response.json();
      session.thread_id = result.thread_id || session.thread_id;
      session.last_result = result;
      placeholder.content = result.final_answer || "No answer returned.";
      placeholder.error = false;
      if (session.title === "New Conversation") {
        session.title = truncate(prompt, 42);
      }
      session.updated_at = new Date().toISOString();
      persistSessions();
      render();
    } catch (error) {
      placeholder.content =
        `Request failed.\n\n${error instanceof Error ? error.message : String(error)}`;
      placeholder.error = true;
      session.updated_at = new Date().toISOString();
      persistSessions();
      render();
    } finally {
      state.pending = false;
      dom.sendBtn.disabled = false;
    }
  }

  function buildHeaders() {
    const headers = { "content-type": "application/json" };
    const key = state.settings.apiKey.trim();
    if (key) {
      headers["x-api-key"] = key;
    }
    return headers;
  }

  function appendMessage(session, message) {
    session.messages.push(message);
    session.updated_at = new Date().toISOString();
    persistSessions();
  }

  function clearActiveSession() {
    const session = getActiveSession();
    if (!session) {
      return;
    }
    if (!window.confirm("Clear the current conversation?")) {
      return;
    }
    session.messages = [];
    session.last_result = null;
    session.updated_at = new Date().toISOString();
    persistSessions();
    render();
  }

  async function copyTranscript() {
    const session = getActiveSession();
    if (!session) {
      return;
    }
    const lines = session.messages.map(
      (message) => `[${message.role}] ${message.content}`
    );
    try {
      await navigator.clipboard.writeText(lines.join("\n\n"));
      dom.copyTranscriptBtn.textContent = "Copied";
      window.setTimeout(() => {
        dom.copyTranscriptBtn.textContent = "Copy Transcript";
      }, 1200);
    } catch {
      dom.copyTranscriptBtn.textContent = "Copy Failed";
      window.setTimeout(() => {
        dom.copyTranscriptBtn.textContent = "Copy Transcript";
      }, 1200);
    }
  }

  async function probeHealth() {
    try {
      const response = await fetch(`${state.settings.apiBaseUrl}/healthz`);
      const ok = response.ok;
      dom.healthTag.textContent = ok ? "health: online" : "health: degraded";
      dom.healthTag.classList.toggle("chip-muted", !ok);
    } catch {
      dom.healthTag.textContent = "health: offline";
      dom.healthTag.classList.add("chip-muted");
    }
  }

  function scheduleHealthProbe() {
    probeHealth();
    window.setInterval(probeHealth, 30000);
  }

  function autoSizeComposer() {
    dom.composerInput.style.height = "auto";
    dom.composerInput.style.height = `${Math.min(
      dom.composerInput.scrollHeight,
      220
    )}px`;
  }

  function getActiveSession() {
    return state.sessions.find((session) => session.id === state.activeSessionId);
  }

  function persistSessions() {
    localStorage.setItem(SESSION_KEY, JSON.stringify(state.sessions));
  }

  function persistSettings() {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(state.settings));
  }

  function normalizeBaseUrl(value) {
    const trimmed = value.trim();
    if (!trimmed) {
      return window.location.origin;
    }
    return trimmed.replace(/\/+$/, "");
  }

  function formatDate(value) {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString();
  }

  function formatConfidence(map) {
    if (!map || typeof map !== "object") {
      return "-";
    }
    const overall = map.overall;
    if (typeof overall !== "number") {
      return "-";
    }
    return `${(overall * 100).toFixed(1)}%`;
  }

  function markdownToHtml(input) {
    const escaped = escapeHtml(input);
    const fenced = escaped.replace(
      /```([\s\S]*?)```/g,
      (_match, code) => `<pre><code>${code.trim()}</code></pre>`
    );
    const inlineCode = fenced.replace(/`([^`]+)`/g, "<code>$1</code>");
    const bold = inlineCode.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    const italic = bold.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    const links = italic.replace(
      /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noreferrer">$1</a>'
    );

    return links
      .split(/\n{2,}/)
      .map((block) => {
        const lines = block.split("\n");
        const isList = lines.every((line) => /^[-*]\s+/.test(line.trim()));
        if (isList) {
          const items = lines
            .map((line) => line.trim().replace(/^[-*]\s+/, ""))
            .map((line) => `<li>${line}</li>`)
            .join("");
          return `<ul>${items}</ul>`;
        }
        return `<p>${lines.join("<br/>")}</p>`;
      })
      .join("");
  }

  function truncate(value, maxLen) {
    if (value.length <= maxLen) {
      return value;
    }
    return `${value.slice(0, maxLen - 1)}...`;
  }

  function escapeHtml(input) {
    return String(input)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function safeParse(raw, fallback) {
    if (!raw) {
      return fallback;
    }
    try {
      return JSON.parse(raw);
    } catch {
      return fallback;
    }
  }
})();
