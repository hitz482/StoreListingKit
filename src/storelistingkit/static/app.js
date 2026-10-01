"use strict";
// Store Listing Kit UI. Vanilla JS, no build step. All server data is rendered via textContent.

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const state = { token: "", status: null, project: null, job: null, activeStore: null };

function readToken() {
  const m = location.hash.match(/token=([A-Za-z0-9_-]+)/);
  if (m) {
    try { sessionStorage.setItem("slk-token", m[1]); } catch (e) { /* storage may be blocked */ }
    history.replaceState(null, "", location.pathname);
    return m[1];
  }
  try { return sessionStorage.getItem("slk-token") || ""; } catch (e) { return ""; }
}

async function api(path, opts = {}) {
  const headers = Object.assign({ "X-SLK-Token": state.token }, opts.headers || {});
  let body = opts.body;
  if (body && !(body instanceof FormData)) { headers["Content-Type"] = "application/json"; body = JSON.stringify(body); }
  const res = await fetch(path, { method: opts.method || "GET", headers, body });
  let data = null;
  try { data = await res.json(); } catch (e) { /* non-JSON */ }
  if (!res.ok) {
    const msg = data && data.detail ? (typeof data.detail === "string" ? data.detail : "Invalid input.") : `Request failed (${res.status}).`;
    throw new Error(msg);
  }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

function banner(msg, kind = "error") {
  const b = $("#banner");
  if (!msg) { b.classList.add("hidden"); return; }
  b.textContent = msg;
  b.className = "banner" + (kind === "info" ? " info" : "");
}

function busy(btn, on) { if (btn) btn.disabled = on; }

function showStep(n) {
  for (let i = 1; i <= 6; i++) $(`#step-${i}`).classList.toggle("hidden", i > n);
  $$("#stepper li").forEach((li) => {
    const s = Number(li.dataset.step);
    li.classList.toggle("current", s === n);
    li.classList.toggle("done", s < n);
  });
  $(`#step-${n}`).scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------------------------------------------------------------- status / key

async function refreshStatus() {
  state.status = await api("/api/status");
  const src = state.status.key_source;
  $("#key-dot").className = "dot " + (src === "none" ? "off" : "on");
  $("#key-label").textContent = src === "none" ? "No API key (offline mode)" : `Claude ready (${src === "env" ? "env" : "session"})`;
  $("#key-status").textContent = src === "none" ? "No key set." : `Using key from ${src === "env" ? "environment" : "this session"}. Model: ${state.status.model}`;
}

function setupKeyDialog() {
  const dlg = $("#dlg-key");
  $("#btn-key").addEventListener("click", () => dlg.showModal());
  $("#key-save").addEventListener("click", async () => {
    try { await api("/api/key", { method: "POST", body: { key: $("#key-input").value } }); $("#key-input").value = ""; await refreshStatus(); dlg.close(); }
    catch (e) { $("#key-status").textContent = e.message; }
  });
  $("#key-clear").addEventListener("click", async () => { await api("/api/key", { method: "DELETE" }); await refreshStatus(); });
}

function setupEnginesDialog() {
  const dlg = $("#dlg-engines");
  $("#btn-engines").addEventListener("click", async () => {
    dlg.showModal();
    const list = $("#engine-list");
    list.replaceChildren(el("li", { text: "Scanning…" }));
    try {
      const data = await api("/api/engines");
      list.replaceChildren();
      if (!data.installs.length) list.append(el("li", { class: "muted", text: "No Unreal Engine or Unity installs found (that's fine; you can still use zips, URLs and folders)." }));
      for (const e of data.installs) list.append(el("li", { text: `${e.engine === "unreal" ? "Unreal Engine" : "Unity"} ${e.version} (${e.source}): ${e.path}` }));
    } catch (e) { list.replaceChildren(el("li", { class: "err", text: e.message })); }
  });
  $("#bridge-go").addEventListener("click", async (ev) => {
    busy(ev.target, true);
    try {
      const r = await api("/api/engines/bridge", { method: "POST", body: { project_dir: $("#bridge-path").value } });
      $("#bridge-status").className = "small ok";
      $("#bridge-status").textContent = `Installed ${r.engine} bridge to ${r.installed_to}. Restart the editor, then use Tools → Store Listing Kit.`;
    } catch (e) { $("#bridge-status").className = "small err"; $("#bridge-status").textContent = e.message; }
    busy(ev.target, false);
  });
}

// ---------------------------------------------------------------- step 1: source

function setupTabs(container) {
  $$(".tab", container).forEach((t) => t.addEventListener("click", () => {
    $$(".tab", container).forEach((x) => x.classList.toggle("active", x === t));
    $$(".tabpane", container.parentElement).forEach((p) => p.classList.toggle("hidden", p.dataset.pane !== t.dataset.tab));
  }));
}

function setupDrop(label, input, onFiles) {
  input.addEventListener("change", () => { if (input.files.length) onFiles(Array.from(input.files)); input.value = ""; });
  label.addEventListener("dragover", (e) => { e.preventDefault(); label.classList.add("over"); });
  label.addEventListener("dragleave", () => label.classList.remove("over"));
  label.addEventListener("drop", (e) => { e.preventDefault(); label.classList.remove("over"); onFiles(Array.from(e.dataTransfer.files)); });
}

async function loadSource(fn) {
  banner(null);
  $("#source-loading").classList.remove("hidden");
  try { state.project = await fn(); renderProfile(); showStep(2); }
  catch (e) { banner(e.message); }
  finally { $("#source-loading").classList.add("hidden"); }
}

function setupSource() {
  setupTabs($("#step-1 .tabs"));
  setupDrop($("#zip-drop"), $("#zip-input"), (files) => {
    const fd = new FormData(); fd.append("file", files[0]);
    loadSource(() => api("/api/projects/upload", { method: "POST", body: fd }));
  });
  $("#url-go").addEventListener("click", () => loadSource(() => api("/api/projects/source", { method: "POST", body: { url: $("#url-input").value } })));
  $("#folder-go").addEventListener("click", () => loadSource(() => api("/api/projects/source", { method: "POST", body: { path: $("#folder-input").value } })));
}

// ---------------------------------------------------------------- step 2: profile

const PROFILE_FIELDS = [
  ["display_name", "Display name", "text"], ["name", "Internal name", "text"],
  ["engine", "Engine", "engine"], ["version", "Plugin version", "text"],
  ["author", "Author / publisher", "text"], ["category", "Category", "text"],
  ["engine_versions", "Supported engine versions (comma separated)", "csv"],
  ["platforms", "Platforms (comma separated)", "csv"],
  ["description", "Description", "area", true],
  ["features", "Features (one per line)", "lines", true],
  ["modules", "Modules / assemblies (one per line: Name | kind | platforms)", "modules", true],
  ["dependencies", "Dependencies (comma separated)", "csv", true],
  ["keywords", "Keywords (comma separated)", "csv"], ["license", "License", "text"],
  ["docs_url", "Documentation URL", "text"], ["support_url", "Support URL", "text"],
];

function renderProfile() {
  const p = state.project.profile;
  const warn = $("#profile-warnings");
  warn.replaceChildren(...p.warnings.map((w) => el("div", { class: "notice", text: w })));
  if (state.project.engine_confidence > 0 && state.project.engine_confidence < 0.9)
    warn.append(el("div", { class: "notice", text: "Engine detection is not certain. Check the Engine field." }));
  const form = $("#profile-form");
  form.replaceChildren();
  for (const [key, label, kind, wide] of PROFILE_FIELDS) {
    const src = p.sources[key];
    const lab = el("label", { for: `pf-${key}` }, label, src ? el("span", { class: "src" + (src === "edited by user" ? " edited" : ""), text: `from ${src}` }) : null);
    let input;
    const v = p[key];
    if (kind === "engine") {
      input = el("select", { id: `pf-${key}` }, ...["unreal", "unity", "unknown"].map((o) => el("option", { value: o, text: o === "unreal" ? "Unreal Engine (Fab)" : o === "unity" ? "Unity (Asset Store)" : "Unknown (both stores)", selected: o === v })));
    } else if (kind === "area") input = el("textarea", { id: `pf-${key}` }), input.value = v;
    else if (kind === "lines") input = el("textarea", { id: `pf-${key}` }), input.value = v.join("\n");
    else if (kind === "modules") input = el("textarea", { id: `pf-${key}` }), input.value = v.map((m) => [m.name, m.kind, m.platforms.join(", ")].join(" | ")).join("\n");
    else if (kind === "csv") input = el("input", { id: `pf-${key}`, type: "text" }), input.value = v.join(", ");
    else input = el("input", { id: `pf-${key}`, type: "text" }), input.value = v;
    form.append(el("div", { class: wide ? "wide" : "" }, lab, input));
  }
}

function collectProfile() {
  const p = structuredClone(state.project.profile);
  const val = (k) => $(`#pf-${k}`).value;
  const csv = (k) => val(k).split(",").map((s) => s.trim()).filter(Boolean);
  for (const [key, , kind] of PROFILE_FIELDS) {
    if (kind === "csv") p[key] = csv(key);
    else if (kind === "lines") p[key] = val(key).split("\n").map((s) => s.trim()).filter(Boolean);
    else if (kind === "modules") p[key] = val(key).split("\n").map((l) => l.trim()).filter(Boolean).map((l) => {
      const [name, kindv = "", plats = ""] = l.split("|").map((s) => s.trim());
      return { name, kind: kindv, platforms: plats.split(",").map((s) => s.trim()).filter(Boolean) };
    }).filter((m) => m.name);
    else p[key] = val(key).trim();
  }
  return p;
}

function setupProfile() {
  $("#profile-save").addEventListener("click", async (ev) => {
    banner(null); busy(ev.target, true);
    try {
      state.project = await api(`/api/projects/${state.project.id}/profile`, { method: "PUT", body: collectProfile() });
      if (!state.project.profile.name && !state.project.profile.display_name) throw new Error("Give the plugin a display name first.");
      renderShots(); showStep(3);
    } catch (e) { banner(e.message); }
    busy(ev.target, false);
  });
}

// ---------------------------------------------------------------- step 3: screenshots

function shotUrl(name) { return `/api/projects/${state.project.id}/screenshots/${encodeURIComponent(name)}?t=${encodeURIComponent(state.token)}`; }

function renderShots() {
  const names = state.project.screenshots;
  $("#shots-empty").classList.toggle("hidden", names.length > 0);
  $("#shots").replaceChildren(...names.map((n, i) => el("div", { class: "shot" },
    el("img", { src: shotUrl(n), alt: `Screenshot ${i + 1}` }),
    el("div", { class: "bar" },
      el("span", { class: "small muted", text: i === 0 ? "1 (cover)" : String(i + 1) }),
      el("span", {},
        el("button", { type: "button", class: "ghost small-btn", text: "←", title: "Move left", disabled: i === 0, onclick: () => moveShot(i, -1) }),
        el("button", { type: "button", class: "ghost small-btn", text: "→", title: "Move right", disabled: i === names.length - 1, onclick: () => moveShot(i, 1) }),
        el("button", { type: "button", class: "ghost small-btn", text: "✕", title: "Remove", onclick: () => removeShot(n) }))))));
}

async function moveShot(i, d) {
  const names = state.project.screenshots.slice();
  [names[i], names[i + d]] = [names[i + d], names[i]];
  state.project = await api(`/api/projects/${state.project.id}/screenshots/order`, { method: "POST", body: names });
  renderShots();
}

async function removeShot(n) {
  state.project = await api(`/api/projects/${state.project.id}/screenshots/${encodeURIComponent(n)}`, { method: "DELETE" });
  renderShots();
}

function setupShots() {
  setupDrop($("#shot-drop"), $("#shot-input"), async (files) => {
    banner(null);
    const fd = new FormData(); files.forEach((f) => fd.append("files", f));
    try {
      const r = await api(`/api/projects/${state.project.id}/screenshots`, { method: "POST", body: fd });
      state.project = r; renderShots();
      if (r.errors && r.errors.length) banner(r.errors.join(" "));
    } catch (e) { banner(e.message); }
  });
  $("#shots-next").addEventListener("click", () => showStep(4));
}

// ---------------------------------------------------------------- step 4: generate

const STEP_LABEL = { pending: "Waiting", running: "Writing copy and composing images…", done: "Done", error: "Failed" };

function storeName(id) { return (state.status.specs[id] || {}).display_name || id; }

function renderProgress(job) {
  const ul = $("#gen-progress");
  ul.replaceChildren(...Object.entries(job.steps).map(([store, st]) => el("li", {},
    st === "running" ? el("span", { class: "spinner" }) : el("span", { class: st === "done" ? "ok" : st === "error" ? "err" : "muted", text: st === "done" ? "✓" : st === "error" ? "✕" : "•" }),
    el("strong", { text: storeName(store) }), el("span", { class: "muted", text: STEP_LABEL[st] }),
    ...(job.errors[store] || []).map((m) => el("div", { class: "err small wide", text: m })))));
  if (job.state === "running") ul.append(el("li", { class: "muted small", text: `${job.elapsed}s elapsed. Claude can take a minute per store; partial results appear below as each store finishes.` }));
}

function setupGenerate() {
  $("#gen-go").addEventListener("click", async (ev) => {
    banner(null); busy(ev.target, true);
    try {
      const r = await api(`/api/projects/${state.project.id}/generate`, { method: "POST", body: { mode: $("#gen-mode").value } });
      if (r.generator === "template") banner("Using the offline template (no AI). Add an API key for Claude-written copy.", "info");
      await pollJob(r.job_id);
    } catch (e) { banner(e.message); }
    busy(ev.target, false);
  });
}

async function pollJob(id) {
  for (;;) {
    const job = await api(`/api/jobs/${id}`);
    renderProgress(job);
    if (job.kit && Object.keys(job.kit.copies).length) {
      state.project.kit = job.kit;
      renderReview(); $("#step-5").classList.remove("hidden");
    }
    if (job.state !== "running") {
      if (job.kit && Object.keys(job.kit.copies).length) { renderExport(); showStep(6); $("#step-5").scrollIntoView({ behavior: "smooth" }); }
      return;
    }
    await new Promise((r) => setTimeout(r, 900));
  }
}

// ---------------------------------------------------------------- step 5: review

function limitsFor(store) { return state.status.specs[store].fields; }

function counter(value, lim) {
  if (!lim || !lim.max_chars) return el("span", { class: "counter muted", text: `${value.length}` });
  const n = value.length, over = n > lim.max_chars, low = lim.min_chars && n < lim.min_chars;
  return el("span", { class: "counter " + (over ? "err" : low ? "warn" : "muted"), text: `${n} / ${lim.max_chars}` });
}

function renderReview() {
  const kit = state.project.kit;
  const stores = Object.keys(kit.copies);
  if (!state.activeStore || !stores.includes(state.activeStore)) state.activeStore = stores[0];
  $("#store-tabs").replaceChildren(...stores.map((s) => el("button", { type: "button", class: "tab" + (s === state.activeStore ? " active" : ""), text: storeName(s), onclick: () => { state.activeStore = s; renderReview(); } })));
  const s = state.activeStore, copy = kit.copies[s], lim = limitsFor(s);
  const issues = kit.issues.filter((i) => i.store === s);
  const ed = $("#store-editor");
  ed.replaceChildren();
  ed.append(el("p", { class: "small muted", text: `Written by ${copy.generated_by}. Limits from store_specs.json${state.status.specs[s].verified ? "" : " (not yet re-verified against the live store guidelines)"}.` }));
  ed.append(issues.length ? el("ul", { class: "issues" }, ...issues.map((i) => el("li", { class: i.severity === "error" ? "err" : "warn", text: `${i.severity === "error" ? "✕" : "!"} ${i.field}: ${i.message}` }))) : el("p", { class: "ok small", text: "✓ Within all store limits." }));

  const field = (key, label, multiline, listMode) => {
    const raw = listMode ? copy[key].join("\n") : copy[key];
    const input = multiline ? el("textarea", { id: `cf-${key}`, rows: key === "long_description" ? 10 : 4 }) : el("input", { id: `cf-${key}`, type: "text" });
    input.value = raw;
    const itemCount = (v) => el("span", { class: "counter " + (v.length > lim[key].max_items ? "err" : "muted"), text: `${v.length} / ${lim[key].max_items} items` });
    const lines = () => input.value.split("\n").map((x) => x.trim()).filter(Boolean);
    const lab = el("label", { for: `cf-${key}` }, label, listMode ? itemCount(copy[key]) : counter(raw, lim[key]));
    input.addEventListener("input", () => lab.replaceChild(listMode ? itemCount(lines()) : counter(input.value, lim[key]), lab.lastChild));
    input.addEventListener("change", () => saveCopy(s));
    return el("div", { class: "field" }, lab, input);
  };
  ed.append(field("title", "Title"), field("short_description", "Short description", true),
    field("long_description", "Long description", true),
    field("features", `Features (one per line, max ${lim.features.max_items})`, true, true),
    field("tags", `Tags (one per line, max ${lim.tags.max_items})`, true, true));
  ed.append(el("label", { text: "Technical details (from the profile; appended to the long description)" }), el("pre", { class: "tech", text: copy.technical_details || "(empty)" }));
  const imgs = kit.images.filter((i) => i.store === s);
  ed.append(el("h3", { text: "Images" }));
  ed.append(imgs.length ? el("div", { class: "images" }, ...imgs.map((i) => el("figure", {},
    el("img", { src: `/api/projects/${state.project.id}/images/${s}/${encodeURIComponent(i.filename)}?t=${encodeURIComponent(state.token)}&v=${Date.now()}`, alt: i.slot }),
    el("figcaption", { text: `${i.filename}: ${i.width}×${i.height}, from ${i.source}` })))) : el("p", { class: "empty", text: "No images: add screenshots in step 3 and generate again." }));
}

async function saveCopy(store) {
  const body = {
    title: $("#cf-title").value, short_description: $("#cf-short_description").value,
    long_description: $("#cf-long_description").value,
    features: $("#cf-features").value.split("\n").map((x) => x.trim()).filter(Boolean),
    tags: $("#cf-tags").value.split("\n").map((x) => x.trim()).filter(Boolean),
  };
  try { state.project = await api(`/api/projects/${state.project.id}/copies/${store}`, { method: "PUT", body }); renderReview(); renderExport(); }
  catch (e) { banner(e.message); }
}

// ---------------------------------------------------------------- step 6: export

function renderExport() {
  const kit = state.project.kit;
  const errors = kit.issues.filter((i) => i.severity === "error").length;
  const warnings = kit.issues.length - errors;
  $("#export-summary").className = errors ? "warn" : "ok";
  $("#export-summary").textContent = errors ? `${errors} error(s) and ${warnings} warning(s) remain. You can still export, but fix them before submitting.` : `Ready: no errors${warnings ? `, ${warnings} warning(s)` : ""}.`;
  $("#export-link").href = `/api/projects/${state.project.id}/export?t=${encodeURIComponent(state.token)}`;
}

// ---------------------------------------------------------------- boot

async function boot() {
  state.token = readToken();
  if (!state.token) { banner("Missing session token. Open the link printed in the Store Listing Kit window."); return; }
  setupKeyDialog(); setupEnginesDialog(); setupSource(); setupProfile(); setupShots(); setupGenerate();
  try { await refreshStatus(); } catch (e) { banner(e.message); return; }
  if (state.status.startup_project) {
    state.project = await api(`/api/projects/${state.status.startup_project}`);
    renderProfile(); renderShots(); showStep(2);
    banner(`Opened from the editor: ${state.project.origin.replace(/^folder:/, "")}`, "info");
  } else showStep(1);
}

document.addEventListener("DOMContentLoaded", boot);
