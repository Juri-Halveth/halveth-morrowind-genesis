"use strict";

(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const state = { status: null, entities: [], activeEntity: null, filter: "all", pending: false, historyRequest: 0, loreRequest: 0, entitiesLoaded: false, actionViews: new Map() };
  const kindNames = { companion: "Begleiter", assistant: "Begleiter", npc: "NPC", creature: "Wesen", animal: "Tier", entity: "Entität", archetype: "Archetyp", character: "Charakter", agent: "Agent", persona: "Persönlichkeit" };
  const kindName = kind => kindNames[String(kind || "entity").toLowerCase()] || String(kind || "Entität");
  const asList = (data, field) => Array.isArray(data) ? data : Array.isArray(data?.[field]) ? data[field] : [];
  const stringify = value => typeof value === "string" ? value : value == null ? "" : typeof value === "object" ? Object.values(value).filter(v => typeof v === "string").join(" · ") : String(value);
  const node = (tag, className, content) => { const el = document.createElement(tag); if (className) el.className = className; if (content != null) el.textContent = String(content); return el; };
  const text = (selector, value) => { $(selector).textContent = value; };
  const initials = name => String(name || "✧").trim().split(/\s+/).map(s => Array.from(s)[0]).slice(0, 2).join("").toUpperCase();

  async function api(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.method === "POST" ? 180000 : 15000);
    try {
      const response = await fetch(path, { credentials: "same-origin", ...options, signal: controller.signal });
      let data;
      try { data = await response.json(); } catch { throw new Error("Der lokale Dienst hat keine lesbare Antwort geliefert."); }
      if (!response.ok) throw new Error(stringify(data.error || data.message) || `Lokaler Dienst: Fehler ${response.status}.`);
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("Die Antwort dauert zu lange. Der lokale Dienst kann noch beschäftigt sein.");
      if (error instanceof TypeError) throw new Error("Der lokale Dienst ist nicht erreichbar. Starte den HALVETH-Server und lade die Seite erneut.");
      throw error;
    } finally { clearTimeout(timeout); }
  }

  async function post(path, payload) {
    if (!state.status?.csrfToken) await loadStatus();
    if (!state.status?.csrfToken) throw new Error("Die lokale Sitzung ist noch nicht bereit. Bitte lade die Seite erneut.");
    return api(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Halveth-Token": state.status.csrfToken }, body: JSON.stringify(payload) });
  }

  function notice(message) { const box = $("#service-notice"); box.textContent = message; box.hidden = !message; }
  let toastTimer;
  function toast(message) { clearTimeout(toastTimer); const el = $("#toast"); el.textContent = message; el.hidden = false; toastTimer = setTimeout(() => { el.hidden = true; }, 5500); }
  function number(value) { return value != null && Number.isFinite(Number(value)) ? new Intl.NumberFormat("de-DE").format(Number(value)) : "—"; }
  function showMode(mode) {
    const el = $("#response-mode");
    const live = mode === "MODEL_LIVE" || mode === "live" || mode === "model";
    el.textContent = live ? "MODEL_LIVE" : mode ? String(mode).toUpperCase() : "BEREIT";
    el.classList.toggle("offline", Boolean(mode) && !live);
    el.title = live ? "Diese Antwort wurde vom Sprachmodell erzeugt." : mode ? "Der Antwortmodus stammt aus der lokalen Dienstantwort." : "Noch keine Antwort erzeugt.";
  }

  async function loadStatus() {
    try {
      const data = await api("/api/status");
      state.status = data;
      const model = data.model || {};
      const game = data.game || {};
      text("#version", data.version ? `v${data.version}` : "GENESIS");
      text("#footer-version", data.version ? `v${data.version}` : "BUILD");
      text("#model-status", model.available ? "Sprachmodell verbunden" : "Offline-Modus");
      text("#model-detail", model.available ? (model.name || "Lokales Modell") : "Grundfunktionen verfügbar");
      $("#model-dot").className = `status-dot ${model.available ? "" : "offline"}`;
      text("#chat-model-caption", model.available ? (model.name || "Lokales Modell") : "Offline · lokale Antworten");
      text("#game-status", game.connected ? "Spielbrücke verbunden" : "Wartet auf Morrowind");
      text("#game-detail", game.connected ? (stringify(game.cell) || "Weltzustand verfügbar") : "Lokale Gespräche sind möglich");
      $("#game-dot").className = `status-dot ${game.connected ? "" : "offline"}`;
      text("#entities-count", number(data.counts?.entities));
      text("#memories-count", number(data.counts?.memories));
      text("#lore-count", number(data.counts?.lore));
      text("#current-cell", game.connected ? (stringify(game.cell) || "Ort nicht übermittelt") : "Noch nicht verbunden");
      text("#current-player", game.connected ? (stringify(game.player?.name || game.player) || "—") : "—");
      text("#nearby-npcs", game.connected ? number(Array.isArray(game.npcs) ? game.npcs.length : game.npcs) : "—");
      text("#world-note", game.connected ? "Dieser Kontext stammt aus dem zuletzt gelieferten Spielzustand." : "Die Spielbrücke ergänzt den tatsächlichen Weltzustand, sobald sie verbunden ist.");
      renderGraphics(data.graphicsProfiles, data.graphics);
      for (const receipt of asList(data.actions, "actions")) {
        const view = state.actionViews.get(receipt.id);
        if (view) renderActionResult(receipt, view.button, view.result, true);
      }
      if (state.entitiesLoaded && Number(data.counts?.entities) !== state.entities.length) loadEntities();
      notice("");
      return data;
    } catch (error) {
      text("#model-status", "Dienst nicht erreichbar");
      text("#model-detail", "Verbindung wird erneut geprüft");
      text("#game-status", "Status nicht verfügbar");
      text("#game-detail", "Keine aktuelle Verbindung");
      $("#model-dot").className = "status-dot offline";
      $("#game-dot").className = "status-dot offline";
      notice(error.message);
      throw error;
    }
  }

  function renderFilters() {
    const root = $("#entity-filters"); root.replaceChildren();
    const kinds = ["all", ...new Set(state.entities.map(e => String(e.kind || "entity")))];
    for (const kind of kinds) {
      const button = node("button", `filter-button${state.filter === kind ? " active" : ""}`, kind === "all" ? "Alle" : kindName(kind));
      button.type = "button"; button.setAttribute("aria-pressed", String(state.filter === kind));
      button.addEventListener("click", () => { state.filter = kind; renderFilters(); renderEntities(); });
      root.append(button);
    }
  }

  function renderEntities() {
    const root = $("#entity-list"); root.replaceChildren();
    const query = $("#entity-search").value.toLocaleLowerCase("de").trim();
    const entities = state.entities.filter(entity => (state.filter === "all" || String(entity.kind || "entity") === state.filter) && `${entity.name || ""} ${entity.kind || ""} ${entity.description || ""}`.toLocaleLowerCase("de").includes(query));
    text("#entity-total", state.entities.length);
    if (!entities.length) { root.append(node("p", "empty-state", state.entities.length ? "Keine passenden Profile gefunden." : "Noch keine Profile verfügbar.")); return; }
    for (const entity of entities) {
      const selected = state.activeEntity?.id === entity.id;
      const button = node("button", `entity-card${selected ? " active" : ""}`);
      button.type = "button"; button.setAttribute("aria-pressed", String(selected)); button.setAttribute("aria-label", `Mit ${entity.name} sprechen`);
      const avatar = node("span", "avatar", entity.kind === "companion" || entity.id === "jarvis" ? "✧" : initials(entity.name)); avatar.setAttribute("aria-hidden", "true");
      const content = node("span", "entity-card-text"); content.append(node("span", "entity-name", entity.name || entity.id), node("span", "entity-kind", kindName(entity.kind)));
      button.append(avatar, content);
      if (selected) { const mark = node("span", "entity-selection", "↗"); mark.setAttribute("aria-hidden", "true"); button.append(mark); }
      button.addEventListener("click", () => selectEntity(entity));
      root.append(button);
    }
  }

  function emptyConversation() {
    const root = $("#messages"); root.replaceChildren();
    const empty = node("div", "conversation-empty");
    const glyph = node("span", "", "✧"); glyph.setAttribute("aria-hidden", "true");
    empty.append(glyph, node("h4", "", "Jede Geschichte beginnt mit einer Frage."), node("p", "", "Sprich frei. Erkunde Hintergründe. Oder finde einen friedlichen nächsten Schritt.")); root.append(empty);
  }

  async function selectEntity(entity) {
    if (state.pending) { toast("Dein aktuelles Gespräch wird noch beantwortet."); return; }
    state.activeEntity = entity;
    renderEntities();
    text("#conversation-title", entity.name || entity.id);
    text("#active-kind", kindName(entity.kind).toUpperCase());
    text("#active-description", entity.description || "Eine neue Begegnung wartet.");
    text("#active-avatar", entity.kind === "companion" || entity.id === "jarvis" ? "✧" : initials(entity.name));
    $("#chat-input").placeholder = `${entity.name || "Jarvis"}, was wäre, wenn wir …`;
    showMode(null); emptyConversation();
    const request = ++state.historyRequest;
    try {
      const data = await api(`/api/history?entity=${encodeURIComponent(entity.id)}`);
      if (request !== state.historyRequest) return;
      const history = asList(data, "history");
      if (history.length) {
        $("#messages").replaceChildren();
        for (const message of history) appendMessage(message.role === "user" ? "user" : "assistant", stringify(message.content || message.reply), { mode: message.mode, historical: true });
        scrollMessages();
      }
    } catch (error) { if (request === state.historyRequest) toast(`Gesprächsverlauf: ${error.message}`); }
  }

  function appendMessage(role, content, meta = {}) {
    $(".conversation-empty", $("#messages"))?.remove();
    const article = node("article", `message ${role}`);
    const label = node("div", "message-label", role === "user" ? "DU" : (state.activeEntity?.name || "HALVETH"));
    article.append(label, node("div", "message-content", content));
    if (role === "assistant") {
      const info = node("div", "message-meta");
      if (meta.mode) info.append(node("span", "", String(meta.mode)));
      if (meta.historical) info.append(node("span", "", "Erinnerter Dialog"));
      if ("speechSynthesis" in window && content) {
        const voice = node("button", "voice-button", "▷ Vorlesen"); voice.type = "button"; voice.title = "Mit einer lokal installierten Systemstimme vorlesen; startet nur durch diesen Klick.";
        voice.addEventListener("click", () => {
          if (voice.dataset.speaking === "yes") { window.speechSynthesis.cancel(); return; }
          window.speechSynthesis.cancel();
          const localVoices = window.speechSynthesis.getVoices().filter(item => item.localService);
          const localVoice = localVoices.find(item => item.lang.startsWith("de")) || localVoices[0];
          if (!localVoice) { voice.textContent = "Keine lokale Stimme verfügbar"; return; }
          const utterance = new SpeechSynthesisUtterance(content); utterance.lang = "de-DE";
          utterance.voice = localVoice;
          voice.dataset.speaking = "yes"; voice.textContent = "□ Stoppen";
          const finish = () => { voice.dataset.speaking = "no"; voice.textContent = "▷ Vorlesen"; };
          utterance.onend = finish; utterance.onerror = finish;
          window.speechSynthesis.speak(utterance);
        }); info.append(voice);
      }
      if (info.childElementCount) article.append(info);
      if (Array.isArray(meta.sources) && meta.sources.length) {
        const details = node("details", "message-source"); details.append(node("summary", "", `${meta.sources.length} Quelle${meta.sources.length === 1 ? "" : "n"}`));
        const list = node("ul");
        for (const source of meta.sources) list.append(node("li", "", typeof source === "string" ? source : [source.title || source.id, source.source || source.url].filter(Boolean).join(" · ")));
        details.append(list); article.append(details);
      }
      if (Array.isArray(meta.projectSources) && meta.projectSources.length) {
        const details = node("details", "message-source");
        details.append(node("summary", "", `${meta.projectSources.length} HALVETH-Designreferenzen im Modellkontext`));
        const list = node("ul");
        for (const source of meta.projectSources) {
          const item = node("li", "", source.title || source.id);
          try {
            const url = new URL(source.url);
            if (url.protocol === "https:" && !url.username && !url.password) {
              const anchor = node("a", "atelier-link", "Quellstand ↗");
              anchor.href = url.href; anchor.target = "_blank"; anchor.rel = "noopener noreferrer";
              item.append(document.createTextNode(" · "), anchor);
            }
          } catch { /* The title still identifies the reference if no link is available. */ }
          list.append(item);
        }
        details.append(list); article.append(details);
      }
      if (Array.isArray(meta.actions) && meta.actions.length) {
        const actions = node("div", "message-actions");
        for (const action of meta.actions) {
          if (!action.id) continue;
          const button = node("button", "action-button", action.label || action.kind || "Aktion ansehen"); button.type = "button";
          button.addEventListener("click", () => runAction(action, button, article)); actions.append(button);
        }
        article.append(actions);
      }
    }
    $("#messages").append(article); return article;
  }

  function scrollMessages() { const messages = $("#messages"); messages.scrollTop = messages.scrollHeight; }

  function renderActionResult(data, button, result, fromGame = false) {
    const status = String(data.status || "UNKNOWN").toUpperCase();
    const queued = /QUEUED|PENDING|WAITING/.test(status);
    const executed = /^(EXECUTED|APPLIED|COMPLETED|SUCCESS)$/.test(status);
    const failed = /FAILED|TIMEOUT|EXPIRED/.test(status);
    const label = queued ? "IN DER WARTESCHLANGE · Noch nicht im Spiel ausgeführt" : executed ? `AUSGEFÜHRT · ${fromGame ? "vom Spiel zurückgemeldet" : "vom Dienst gemeldet"}` : status === "FAILED" ? "FEHLGESCHLAGEN · vom Spiel zurückgemeldet" : status === "TIMEOUT" ? "KEINE SPIELBESTÄTIGUNG · Zeitfenster abgelaufen" : status === "EXPIRED" ? "ANGEBOT ABGELAUFEN" : status;
    result.classList.toggle("pending", queued || failed);
    result.textContent = `${label}\n${data.message || "Der lokale Dienst hat den Aktionsstatus zurückgegeben."}`;
    button.textContent = queued ? "✓ In Warteschlange" : executed ? "✓ Ausgeführt" : failed ? "Status prüfen" : "Status empfangen";
  }

  async function runAction(action, button, article) {
    if (button.disabled) return;
    button.disabled = true;
    let result = state.actionViews.get(action.id)?.result; if (!result) { result = node("div", "action-result"); result.setAttribute("role", "status"); article.append(result); }
    state.actionViews.set(action.id, { result, button });
    result.textContent = "Aktion wird an den lokalen Dienst übergeben …";
    scrollMessages();
    try {
      const data = await post("/api/action", { id: action.id });
      renderActionResult(data, button, result);
      loadStatus().catch(() => {});
    } catch (error) { result.classList.add("pending"); result.textContent = `Aktion nicht bestätigt: ${error.message}`; button.disabled = false; }
    scrollMessages();
  }

  async function sendMessage(event) {
    event?.preventDefault();
    if (state.pending) return;
    const input = $("#chat-input"); const message = input.value.trim(); if (!message) return;
    if (!state.activeEntity) { toast("Wähle zuerst einen verfügbaren Gesprächspartner."); return; }
    ++state.historyRequest;
    state.pending = true; $("#send-button").disabled = true; $("#chat-error").hidden = true;
    appendMessage("user", message); input.value = ""; input.style.height = "auto";
    const pending = node("div", "typing-indicator", `${state.activeEntity.name || "Dein Gegenüber"} denkt nach …`); $("#messages").append(pending); scrollMessages();
    try {
      const data = await post("/api/chat", { message, entityId: state.activeEntity.id });
      pending.remove(); appendMessage("assistant", stringify(data.reply), data); showMode(data.mode || "UNKNOWN"); scrollMessages();
      loadStatus().catch(() => {});
    } catch (error) {
      pending.remove(); const box = $("#chat-error"); box.textContent = error.message; box.hidden = false;
      if (!input.value) input.value = message;
    } finally { state.pending = false; $("#send-button").disabled = false; input.focus(); }
  }

  function selectTab(name, focus = false) {
    for (const tab of $$("[data-tab]")) { const active = tab.dataset.tab === name; tab.classList.toggle("active", active); tab.setAttribute("aria-selected", String(active)); tab.tabIndex = active ? 0 : -1; if (active && focus) tab.focus(); }
    for (const panel of $$(".tab-panel")) panel.hidden = panel.id !== `panel-${name}`;
    if (name === "workshop") loadProjects();
  }

  async function searchLore(event) {
    event?.preventDefault(); const request = ++state.loreRequest;
    const query = $("#lore-input").value.trim();
    text("#lore-search-status", "Das lokale Archiv wird durchsucht …");
    try {
      const data = await api(`/api/lore?q=${encodeURIComponent(query)}`); if (request !== state.loreRequest) return;
      const items = asList(data, "results"); const root = $("#lore-results"); root.replaceChildren();
      text("#lore-search-status", `${items.length} Fragment${items.length === 1 ? "" : "e"} im verfügbaren Bestand gefunden.`);
      if (!items.length) { root.append(node("p", "empty-state", "Für diese Suche ist im lokalen Bestand noch kein Fragment vorhanden.")); return; }
      for (const item of items) {
        const card = node("article", "lore-card"); card.append(node("span", "eyebrow", "WISSENSFRAGMENT"), node("h4", "", item.title || item.id || "Ohne Titel"), node("p", "", stringify(item.text || item.content)), node("span", "source", `QUELLE · ${stringify(item.source) || "Nicht angegeben"}`)); root.append(card);
      }
    } catch (error) { if (request === state.loreRequest) text("#lore-search-status", error.message); }
  }

  async function loadProjects() {
    try {
      const data = await api("/api/projects"); const projects = asList(data, "projects");
      const columns = { new: [], active: [], done: [] };
      for (const project of projects) {
        const status = String(project.status || "new").toLowerCase();
        const group = /^(done|complete|completed|erledigt|finished|closed)$/.test(status) ? "done" : /progress|active|running|arbeit|started|doing/.test(status) ? "active" : "new";
        columns[group].push(project);
      }
      for (const [name, items] of Object.entries(columns)) {
        const column = $(`[data-board="${name}"]`); $(".board-count", column).textContent = String(items.length);
        const root = $(".board-cards", column); root.replaceChildren();
        if (!items.length) root.append(node("p", "board-empty", "Hier ist gerade kein Auftrag eingetragen."));
        for (const item of items) {
          const card = node("article", "board-card"); card.append(node("h5", "", item.title || item.name || item.id));
          if (item.description) card.append(node("p", "", stringify(item.description)));
          card.append(node("small", "", `${item.id || "AUFTRAG"} · ${item.status || "neu"}`)); root.append(card);
        }
      }
    } catch (error) {
      for (const column of $$(".board-column")) { const root = $(".board-cards", column); root.replaceChildren(node("p", "board-empty", "Auftragsboard gerade nicht erreichbar.")); }
    }
  }

  let graphicsSelection = "beauty";
  let graphicsSignature = "";
  function formatBytes(value) {
    if (!Number.isFinite(Number(value)) || value == null || Number(value) < 0) return "Größe offen";
    let amount = Number(value); const units = ["B", "KiB", "MiB", "GiB"];
    let unit = 0; while (amount >= 1024 && unit < units.length - 1) { amount /= 1024; unit++; }
    return `${new Intl.NumberFormat("de-DE", { maximumFractionDigits: unit ? 1 : 0 }).format(amount)} ${units[unit]}`;
  }

  function renderGraphics(profiles, graphics = {}, force = false) {
    graphics = graphics || {};
    const signature = JSON.stringify([profiles, graphics]);
    if (!force && graphicsSignature === signature) return;
    graphicsSignature = signature;
    const items = Array.isArray(profiles) ? profiles : profiles && typeof profiles === "object" ? Object.entries(profiles).map(([id, profile]) => typeof profile === "object" ? { id, ...profile } : { id, name: id, description: String(profile) }) : [];
    const normalized = items.map(raw => typeof raw === "string" ? { id: raw, name: raw } : raw);
    if (!normalized.some(profile => profile.id === graphicsSelection)) graphicsSelection = normalized[0]?.id;
    const root = $("#graphics-profiles"); root.replaceChildren();
    if (!normalized.length) root.append(node("p", "quiet", "Noch keine Grafikprofile vom lokalen Dienst bereitgestellt."));
    for (const profile of normalized) {
      const selected = profile.id === graphicsSelection;
      const card = node("article", `graphics-profile${selected ? " selected" : ""}`);
      if (["original", "beauty", "cinematic"].includes(profile.id)) card.classList.add(`profile-${profile.id}`);
      const glyph = node("span", "profile-glyph", profile.id === "cinematic" ? "✺" : profile.id === "beauty" ? "✧" : "◇"); glyph.setAttribute("aria-hidden", "true");
      card.append(glyph, node("span", "profile-status", profile.status || "PROFIL · EMPFEHLUNG"), node("h4", "", profile.name || profile.title || profile.id || "Grafikprofil"));
      if (profile.description || profile.summary) card.append(node("p", "", stringify(profile.description || profile.summary)));
      const details = profile.features || profile.mods || profile.notes || [];
      if (Array.isArray(details)) { const list = node("ul"); for (const detail of details) list.append(node("li", "", stringify(detail))); if (list.childElementCount) card.append(list); }
      else if (details) card.append(node("p", "", stringify(details)));
      const button = node("button", "profile-inspect-button", selected ? "✓ Einstellungen geöffnet" : "Einstellungen ansehen ↗");
      button.type = "button"; button.setAttribute("aria-pressed", String(selected));
      button.setAttribute("aria-label", `${profile.name || profile.id}: Einstellungen ansehen`);
      button.addEventListener("click", () => {
        graphicsSelection = profile.id; renderGraphics(profiles, graphics, true);
        $$(".profile-inspect-button").find(item => item.getAttribute("aria-pressed") === "true")?.focus({ preventScroll: true });
      });
      card.append(button);
      root.append(card);
    }
    const selected = normalized.find(profile => profile.id === graphicsSelection);
    $("#graphics-inspector").hidden = !selected;
    if (selected) {
      text("#graphics-selected-title", selected.name || selected.id);
      text("#graphics-launch-profile", selected.name || selected.id);
      text("#graphics-selected-status", selected.status || "Status nicht angegeben");
      const settings = $("#graphics-settings"); settings.replaceChildren();
      const entries = selected.settings && typeof selected.settings === "object" ? Object.entries(selected.settings) : [];
      for (const [label, value] of entries) {
        const item = node("div", "graphics-setting"); item.append(node("dt", "", label), node("dd", "", stringify(value) || "—")); settings.append(item);
      }
      if (!entries.length) settings.append(node("p", "quiet", "Der Dienst hat für dieses Profil noch keine gespeicherten Einzelwerte geliefert."));
      text("#graphics-config-note", selected.prepared === false ? "Dieses Profil wird im nativen Launcher vorbereitet. Die Auswahl hier öffnet nur die Übersicht." : "Gespeicherte Einstellungen · Änderungen und Spielstart erfolgen im nativen Launcher. Eine Bildrate wird hier nicht gemessen.");
    }
    const packages = asList(graphics.installedPackages || graphics.packages, "packages");
    text("#graphics-package-count", String(packages.length));
    text("#graphics-package-bytes", packages.length ? formatBytes(graphics.installedBytes) : "Noch kein Paketbeleg");
    text("#graphics-character-style", graphics.characterStyle || "Für die Charaktergrafik liegt noch keine gesonderte Installationsangabe vor.");
    text("#graphics-install-count", packages.length ? `(${packages.length})` : "");
    const installs = $("#graphics-installations"); installs.replaceChildren();
    if (!packages.length) installs.append(node("p", "quiet", "Noch keine zusätzlichen Inhaltspakete im lokalen Installationsbeleg. Vorhandene Spielgrafik bleibt davon getrennt."));
    const packageStatus = { installed: "Installiert laut Beleg", downloaded: "Heruntergeladen", verified: "Dateien geprüft", pending: "Ausstehend", planned: "Geplant", failed: "Installation fehlgeschlagen" };
    for (const item of packages) {
      const card = node("article", "graphics-install-card");
      const heading = node("div", "graphics-install-heading");
      heading.append(node("h5", "", item.name || "Inhaltspaket"), node("span", "install-state", packageStatus[String(item.status).toLowerCase()] || item.status || "Status nicht angegeben"));
      card.append(heading);
      const info = [item.version ? `Version ${item.version}` : null, formatBytes(item.bytes), item.fileCount != null ? `${number(item.fileCount)} Dateien` : null].filter(Boolean).join(" · ");
      card.append(node("p", "", info));
      if (item.license) card.append(node("p", "package-license", `Lizenz: ${stringify(item.license)}`));
      if (typeof item.source === "string") {
        try {
          const url = new URL(item.source);
          if (["https:", "http:"].includes(url.protocol) && !url.username && !url.password) {
            const link = node("a", "package-source", `Quelle · ${url.hostname} ↗`); link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer"; card.append(link);
          }
        } catch { /* Keep non-URL source labels as plain text. */ }
      }
      installs.append(card);
    }
  }

  async function loadEntities() {
    try {
      const data = await api("/api/entities"); state.entities = asList(data, "entities").filter(entity => entity && entity.id); state.entitiesLoaded = true;
      renderFilters(); renderEntities();
      if (state.entities.length && !state.activeEntity) await selectEntity(state.entities.find(entity => entity.id === "jarvis" || entity.id === "halveth") || state.entities[0]);
    } catch (error) { $("#entity-list").replaceChildren(node("p", "empty-state", error.message)); }
  }

  $("#entity-search").addEventListener("input", renderEntities);
  $("#chat-form").addEventListener("submit", sendMessage);
  $("#chat-input").addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendMessage(); } });
  $("#chat-input").addEventListener("input", event => { event.target.style.height = "auto"; event.target.style.height = `${Math.min(event.target.scrollHeight, 150)}px`; });
  for (const button of $$("[data-prompt]")) button.addEventListener("click", () => { $("#chat-input").value = button.dataset.prompt; $("#chat-input").focus(); });
  for (const tab of $$("[data-tab]")) {
    tab.addEventListener("click", () => selectTab(tab.dataset.tab));
    tab.addEventListener("keydown", event => {
      const tabs = $$("[data-tab]"); let index = tabs.indexOf(tab);
      if (event.key === "ArrowRight") index = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") index = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") index = 0;
      else if (event.key === "End") index = tabs.length - 1;
      else return;
      event.preventDefault(); selectTab(tabs[index].dataset.tab, true);
    });
  }
  $("#lore-form").addEventListener("submit", searchLore);
  const initialTab = location.hash.slice(1);
  if (["dialogue", "lore", "workshop", "atelier"].includes(initialTab)) selectTab(initialTab);
  window.addEventListener("beforeunload", () => { if ("speechSynthesis" in window) window.speechSynthesis.cancel(); });
  Promise.allSettled([loadStatus(), loadEntities(), loadProjects()]);
  setInterval(() => { if (!document.hidden) loadStatus().catch(() => {}); }, 15000);
})();
