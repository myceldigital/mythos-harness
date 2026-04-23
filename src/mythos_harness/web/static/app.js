(function () {
  "use strict";

  const SESSION_KEY = "mythos.console.sessions.v1";
  const SETTINGS_KEY = "mythos.console.settings.v1";
  const MAX_ACTIVITY = 80;

  const dom = {
    newSessionBtn: document.getElementById("newSessionBtn"),
    sessionsList: document.getElementById("sessionsList"),
    sessionCountBadge: document.getElementById("sessionCountBadge"),
    statusBadge: document.getElementById("statusBadge"),
    statusText: document.getElementById("statusText"),
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
    payloadPanel: document.getElementById("payloadPanel"),
    activityList: document.getElementById("activityList"),
    tabs: Array.from(document.querySelectorAll(".tab")),
    tabPanels: Array.from(document.querySelectorAll(".tab-panel")),
    saveConfigBtn: document.getElementById("saveConfigBtn"),
    testConnectionBtn: document.getElementById("testConnectionBtn"),
    apiBaseUrlInput: document.getElementById("apiBaseUrlInput"),
    apiKeyInput: document.getElementById("apiKeyInput"),
    executionModeInput: document.getElementById("executionModeInput"),
    constraintsInput: document.getElementById("constraintsInput"),
    messageTemplate: document.getElementById("messageTemplate"),
  };

  const state = {
    sessions: [],
    activeSessionId: null,
    settings: {
      apiBaseUrl: window.location.origin,
      apiKey: "",
      executionMode: "",
      constraintsRaw: "",
    },
    activity: [],
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
    dom.executionModeInput.value = state.settings.executionMode || "";
    dom.constraintsInput.value = state.settings.constraintsRaw || "";
  }

  function bindEvents() {
    dom.newSessionBtn.addEventListener("click", () => {
      const session = createSession("New Conversation");
      state.sessions.unshift(session);
      state.activeSessionId = session.id;
      persistSessions();
      logActivity("ok", "session", "Created new conversation");
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
    dom.saveConfigBtn.addEventListener("click", saveSettingsFromInputs);
    dom.testConnectionBtn.addEventListener("click", testConnection);
    dom.apiBaseUrlInput.addEventListener("blur", () => {
      const updated = normalizeBaseUrl(dom.apiBaseUrlInput.value);
      dom.apiBaseUrlInput.value = updated;
      if (state.settings.apiBaseUrl !== updated) {
        state.settings.apiBaseUrl = updated;
        persistSettings();
        logActivity("ok", "config", `API base URL set to ${updated}`);
      }
      probeHealth();
    });
    dom.apiKeyInput.addEventListener("blur", syncAndPersistSettings);
    dom.executionModeInput.addEventListener("change", syncAndPersistSettings);
    dom.constraintsInput.addEventListener("blur", syncAndPersistSettings);

    dom.tabs.forEach((tab) => {
      tab.addEventListener("click", () => activateTab(tab.dataset.tab || "overview"));
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
            "Welcome to Mythos Console. Ask a question to run Mythos orchestration.",
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
    renderActivity();
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
        logActivity("ok", "session", `Switched to "${session.title}"`);
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
      ["Loops", result ? String(result.loops ?? "-") : "-"],
      ["Halt Reason", result ? String(result.halt_reason ?? "-") : "-"],
      ["Overall Confidence", result ? formatConfidence(result.confidence_summary) : "-"],
      ["Trajectory ID", result ? String(result.trajectory_id ?? "-") : "-"],
      ["Task Type", result ? String(result.triage?.task_type ?? "-") : "-"],
      ["Citations", result && Array.isArray(result.citations) ? String(result.citations.length) : "0"],
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
    renderPayloadPreview(result ? result.request_payload || {} : {});
  }

  async function submitPrompt() {
    syncSettingsFromInputs();
    const session = getActiveSession();
    const prompt = dom.composerInput.value.trim();
    if (!session || !prompt || state.pending) {
      return;
    }
    state.pending = true;
    dom.sendBtn.disabled = true;
    setRunStatus("running", "Running");
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
      const constraints = parseConstraints();
      const payload = {
        query: prompt,
        thread_id: session.thread_id,
        constraints,
      };
      payload.constraints = applyExecutionModeConstraint(
        payload.constraints,
        state.settings.executionMode
      );
      renderPayloadPreview(payload);
      logActivity("ok", "request", `POST /v1/mythos/stream for ${session.thread_id}`);

      const result = await streamCompletion(payload, session, placeholder);
      result.request_payload = payload;
      session.thread_id = result.thread_id || session.thread_id;
      session.last_result = result;
      placeholder.content = result.final_answer || "No answer returned.";
      placeholder.error = false;
      if (session.title === "New Conversation") {
        session.title = truncate(prompt, 42);
      }
      session.updated_at = new Date().toISOString();
      persistSessions();
      setRunStatus("online", "Ready");
      logActivity(
        "ok",
        "response",
        `Run complete · loops=${result.loops ?? "-"} · halt=${result.halt_reason ?? "-"}`
      );
      render();
    } catch (error) {
      placeholder.content =
        `Request failed.\n\n${error instanceof Error ? error.message : String(error)}`;
      placeholder.error = true;
      session.updated_at = new Date().toISOString();
      persistSessions();
      setRunStatus("error", "Error");
      logActivity(
        "error",
        "request",
        error instanceof Error ? error.message : String(error)
      );
      render();
    } finally {
      state.pending = false;
      dom.sendBtn.disabled = false;
    }
  }

  async function streamCompletion(payload, session, placeholder) {
    const response = await fetch(
      `${state.settings.apiBaseUrl}/v1/mythos/stream`,
      {
        method: "POST",
        headers: {
          ...buildHeaders(),
          Accept: "text/event-stream",
        },
        body: JSON.stringify(payload),
      }
    );
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status} - ${truncate(errorText, 240)}`);
    }
    if (!response.body) {
      throw new Error("Streaming unavailable: empty response body.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload = null;
    let streamError = null;
    let renderQueued = false;
    let tokenStarted = false;

    const scheduleRender = () => {
      if (renderQueued) {
        return;
      }
      renderQueued = true;
      window.setTimeout(() => {
        renderQueued = false;
        render();
      }, 24);
    };

    const onEvent = (eventName, payloadObj) => {
      if (eventName === "token") {
        if (!tokenStarted) {
          placeholder.content = "";
          tokenStarted = true;
        }
        placeholder.content += payloadObj.text || "";
        scheduleRender();
        return;
      }
      if (eventName === "replace") {
        placeholder.content = payloadObj.text || placeholder.content;
        scheduleRender();
        return;
      }
      if (eventName === "status") {
        if (payloadObj.stage === "loop_start") {
          logActivity(
            "ok",
            "loop",
            `Loop ${payloadObj.loop ?? "?"} · phase=${payloadObj.phase ?? "unknown"}`
          );
        }
        if (payloadObj.stage === "feedback_done" && payloadObj.trajectory_id) {
          logActivity("ok", "trajectory", `Recorded ${payloadObj.trajectory_id}`);
        }
        return;
      }
      if (eventName === "final") {
        finalPayload = payloadObj;
        return;
      }
      if (eventName === "error") {
        streamError = payloadObj.message || "Unknown stream error.";
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replaceAll("\r\n", "\n");
      buffer = processSseBuffer(buffer, onEvent);
    }
    buffer += decoder.decode();
    buffer = buffer.replaceAll("\r\n", "\n");
    processSseBuffer(buffer, onEvent);

    if (streamError) {
      throw new Error(streamError);
    }
    if (!finalPayload) {
      throw new Error("Stream ended without final payload.");
    }
    return finalPayload;
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
    logActivity("warn", "session", `Cleared conversation "${session.title}"`);
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
      logActivity("ok", "clipboard", "Transcript copied");
      window.setTimeout(() => {
        dom.copyTranscriptBtn.textContent = "Copy Transcript";
      }, 1200);
    } catch {
      dom.copyTranscriptBtn.textContent = "Copy Failed";
      logActivity("error", "clipboard", "Clipboard write failed");
      window.setTimeout(() => {
        dom.copyTranscriptBtn.textContent = "Copy Transcript";
      }, 1200);
    }
  }

  async function probeHealth() {
    try {
      const response = await fetch(`${state.settings.apiBaseUrl}/readyz`);
      const ok = response.ok;
      dom.healthTag.textContent = ok ? "health: online" : "health: degraded";
      dom.healthTag.classList.toggle("chip-muted", !ok);
      if (ok) {
        setRunStatus(state.pending ? "running" : "online", state.pending ? "Running" : "Ready");
      } else {
        setRunStatus("warn", "Degraded");
      }
    } catch {
      dom.healthTag.textContent = "health: offline";
      dom.healthTag.classList.add("chip-muted");
      setRunStatus("error", "Offline");
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

  async function testConnection() {
    syncSettingsFromInputs();
    persistSettings();
    const base = state.settings.apiBaseUrl;
    logActivity("ok", "connection", `Testing ${base}`);
    try {
      const health = await fetch(`${base}/healthz`);
      const ready = await fetch(`${base}/readyz`);
      const details = `healthz=${health.status} readyz=${ready.status}`;
      if (health.ok && ready.ok) {
        logActivity("ok", "connection", `Connection passed · ${details}`);
        setRunStatus(state.pending ? "running" : "online", state.pending ? "Running" : "Ready");
      } else {
        logActivity("warn", "connection", `Connection degraded · ${details}`);
        setRunStatus("warn", "Degraded");
      }
      probeHealth();
    } catch (error) {
      logActivity(
        "error",
        "connection",
        `Connection failed: ${error instanceof Error ? error.message : String(error)}`
      );
      setRunStatus("error", "Offline");
    }
  }

  function saveSettingsFromInputs() {
    syncSettingsFromInputs();
    persistSettings();
    logActivity("ok", "config", "Configuration saved");
    probeHealth();
  }

  function syncSettingsFromInputs() {
    const nextBase = normalizeBaseUrl(dom.apiBaseUrlInput.value);
    state.settings = {
      apiBaseUrl: nextBase,
      apiKey: dom.apiKeyInput.value.trim(),
      executionMode: (dom.executionModeInput.value || "").trim(),
      constraintsRaw: dom.constraintsInput.value.trim(),
    };
    dom.apiBaseUrlInput.value = nextBase;
  }

  function syncAndPersistSettings() {
    syncSettingsFromInputs();
    persistSettings();
  }

  function activateTab(tabName) {
    dom.tabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.tab === tabName);
    });
    dom.tabPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `tab-${tabName}`);
    });
  }

  function renderPayloadPreview(payload) {
    dom.payloadPanel.textContent = JSON.stringify(payload || {}, null, 2);
  }

  function logActivity(level, kind, message) {
    const entry = {
      id: `a-${Math.random().toString(36).slice(2, 9)}`,
      at: new Date().toISOString(),
      level,
      kind,
      message,
    };
    state.activity.unshift(entry);
    if (state.activity.length > MAX_ACTIVITY) {
      state.activity.length = MAX_ACTIVITY;
    }
    renderActivity();
  }

  function renderActivity() {
    if (!dom.activityList) {
      return;
    }
    if (state.activity.length === 0) {
      dom.activityList.innerHTML = `<div class="activity-entry"><div class="activity-msg">No activity yet.</div></div>`;
      return;
    }
    dom.activityList.innerHTML = state.activity
      .map((entry) => {
        const safeMessage = escapeHtml(entry.message);
        const safeKind = escapeHtml(entry.kind);
        const safeTime = escapeHtml(formatTime(entry.at));
        return `
          <article class="activity-entry ${entry.level}">
            <div class="activity-head">
              <span class="activity-kind">${safeKind}</span>
              <span class="activity-time">${safeTime}</span>
            </div>
            <div class="activity-msg">${safeMessage}</div>
          </article>
        `;
      })
      .join("");
  }

  function setRunStatus(level, text) {
    dom.statusBadge.classList.remove("online", "running", "warn", "error");
    if (level === "online") {
      dom.statusBadge.classList.add("online");
    } else if (level === "running") {
      dom.statusBadge.classList.add("running");
    } else if (level === "warn") {
      dom.statusBadge.classList.add("warn");
    } else if (level === "error") {
      dom.statusBadge.classList.add("error");
    }
    dom.statusText.textContent = text;
  }

  function parseConstraints() {
    const raw = state.settings.constraintsRaw.trim();
    if (!raw) {
      return {};
    }
    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        logActivity("warn", "config", "Constraints ignored: expected JSON object");
        return {};
      }
      return parsed;
    } catch {
      logActivity("warn", "config", "Constraints ignored: invalid JSON");
      return {};
    }
  }

  function applyExecutionModeConstraint(constraints, mode) {
    if (!mode) {
      return constraints;
    }
    return {
      ...constraints,
      execution_mode_hint: mode,
    };
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

  function formatTime(value) {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleTimeString();
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
        const isOrderedList = lines.every((line) => /^\d+\.\s+/.test(line.trim()));
        if (isList) {
          const items = lines
            .map((line) => line.trim().replace(/^[-*]\s+/, ""))
            .map((line) => `<li>${line}</li>`)
            .join("");
          return `<ul>${items}</ul>`;
        }
        if (isOrderedList) {
          const items = lines
            .map((line) => line.trim().replace(/^\d+\.\s+/, ""))
            .map((line) => `<li>${line}</li>`)
            .join("");
          return `<ol>${items}</ol>`;
        }
        return `<p>${lines.join("<br/>")}</p>`;
      })
      .join("");
  }

  function processSseBuffer(buffer, onEvent) {
    let working = buffer;
    while (true) {
      const delimiterIndex = working.indexOf("\n\n");
      if (delimiterIndex === -1) {
        break;
      }
      const eventBlock = working.slice(0, delimiterIndex).trim();
      working = working.slice(delimiterIndex + 2);
      if (!eventBlock) {
        continue;
      }
      const parsed = parseSseEvent(eventBlock);
      if (!parsed) {
        continue;
      }
      onEvent(parsed.event, parsed.payload);
    }
    return working;
  }

  function parseSseEvent(eventBlock) {
    const lines = eventBlock.split(/\r?\n/);
    let eventName = "message";
    const dataLines = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length === 0) {
      return null;
    }
    const rawPayload = dataLines.join("\n");
    try {
      return {
        event: eventName,
        payload: JSON.parse(rawPayload),
      };
    } catch {
      return {
        event: eventName,
        payload: { value: rawPayload },
      };
    }
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

  logActivity("ok", "system", "Mythos Console ready");
  setRunStatus("online", "Ready");
})();
