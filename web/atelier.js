"use strict";

(() => {
  const $ = selector => document.querySelector(selector);
  const el = (tag, className, text) => {
    const item = document.createElement(tag);
    item.className = className || "";
    if (text != null) item.textContent = text;
    return item;
  };
  const link = (label, raw) => {
    const item = el("a", "atelier-link", label);
    try {
      const url = new URL(raw);
      if (url.protocol !== "https:" || url.username || url.password) return el("span", "quiet", label);
      item.href = url.href; item.target = "_blank"; item.rel = "noopener noreferrer";
    } catch { return el("span", "quiet", label); }
    return item;
  };
  let briefs = [];
  let loaded = false;

  function showBrief() {
    const brief = briefs.find(item => item.id === $("#atelier-brief").value);
    $("#atelier-prompt").value = brief?.prompt || "";
    $("#atelier-target").textContent = brief?.target || "";
    $("#atelier-acceptance").replaceChildren(...(brief?.acceptance || []).map(text => el("li", "", text)));
    $("#atelier-copy").disabled = !brief;
    $("#atelier-copy-status").textContent = "";
  }

  async function readJson(url) {
    const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`Lokaler Dienst: ${response.status}`);
    return response.json();
  }

  async function load() {
    if (loaded) return;
    const results = await Promise.allSettled([readJson("/api/generation-providers"), readJson("/api/project-knowledge")]);
    const [production, knowledge] = results;
    if (production.status === "fulfilled") {
      const data = production.value;
      const providers = $("#atelier-providers"); providers.replaceChildren();
      const kinds = { image_texture_source: "BILDER & TEXTUREN", cinematic_and_frame_sequence: "FILM & EFFEKTSEQUENZEN", mesh_texture_rig_animation: "3D-MODELLE & ANIMATION", cinematic_video: "FILM & BEWEGUNGSREFERENZ", local_mesh_material_authoring_and_conversion: "MODELLBAU & SPIELIMPORT" };
      for (const provider of data.providers || []) {
        const card = el("article", "atelier-provider");
        card.append(el("p", "eyebrow", kinds[provider.outputKind] || "PRODUKTIONSWERKZEUG"), el("h4", "", provider.name), el("p", "", provider.gameUse));
        card.append(el("p", "atelier-formats", (provider.formats || []).join(" · ")));
        card.append(el("p", "atelier-access", provider.accessNote));
        card.append(link("Offizielle Quelle ↗", provider.officialUrl));
        providers.append(card);
      }
      briefs = data.assetBriefs || [];
      $("#atelier-brief").replaceChildren(...briefs.map(brief => {
        const option = el("option", "", brief.title); option.value = brief.id; return option;
      }));
      showBrief();
      $("#atelier-status").textContent = `Produktionswege geprüft am ${String(data.checkedAt).slice(0, 10)}. Ein Brief startet noch keinen kostenpflichtigen Auftrag.`;
    } else {
      $("#atelier-status").textContent = `Produktionswege gerade nicht erreichbar: ${production.reason.message}. Beim nächsten Öffnen wird erneut geladen.`;
    }
    if (knowledge.status === "fulfilled") {
      const cards = Array.isArray(knowledge.value) ? knowledge.value : knowledge.value.cards || [];
      const root = $("#atelier-knowledge"); root.replaceChildren();
      $("#atelier-source-count").textContent = `${cards.length} Quellenkarten für neue Ideen`;
      for (const card of cards) {
        const detail = el("details", "atelier-source");
        detail.append(el("summary", "", card.title), el("p", "", card.summary),
          el("p", "eyebrow", "GESTALTUNGSIDEE FÜR DEN AUSBAU"), el("p", "quiet", card.designUse));
        detail.append(link("Gebundenen GitHub-Quellstand lesen ↗", card.url));
        root.append(detail);
      }
    } else {
      $("#atelier-source-count").textContent = "Projektquellen gerade nicht erreichbar";
    }
    loaded = results.every(result => result.status === "fulfilled");
  }

  $("#tab-atelier").addEventListener("click", load);
  // Keyboard tab navigation updates aria-selected without a click.
  new MutationObserver(() => { if ($("#tab-atelier").getAttribute("aria-selected") === "true") load(); })
    .observe($("#tab-atelier"), { attributes: true, attributeFilter: ["aria-selected"] });
  $("#atelier-brief").addEventListener("change", showBrief);
  $("#atelier-copy").addEventListener("click", async () => {
    const brief = briefs.find(item => item.id === $("#atelier-brief").value);
    if (!brief) return;
    const packet = `${brief.title}\n\n${brief.prompt}\n\nAcceptance:\n${(brief.acceptance || []).map(item => `- ${item}`).join("\n")}`;
    try {
      await navigator.clipboard.writeText(packet);
      $("#atelier-copy-status").textContent = "Produktionsbrief mit Abnahmekriterien kopiert.";
    } catch {
      $("#atelier-prompt").focus(); $("#atelier-prompt").select();
      $("#atelier-copy-status").textContent = "Automatisches Kopieren nicht verfügbar. Der Prompt ist zum manuellen Kopieren markiert.";
    }
  });
  $("#atelier-art").addEventListener("error", () => {
    $("#atelier-art").hidden = true;
    $("#atelier-art-status").textContent = "Das lokale Bild konnte nicht geladen werden.";
  });
  if ($("#tab-atelier").getAttribute("aria-selected") === "true") load();
})();
