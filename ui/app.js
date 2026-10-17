"use strict";

/* ============================== basics ============================== */

/** @type {Record<string, string>} */
const ICONS = {
  volume: '<path d="M4.5 9.5h3l4.5-4v13l-4.5-4h-3z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
  mute: '<path d="M4.5 9.5h3l4.5-4v13l-4.5-4h-3z"/><path d="m16 9.5 5 5m0-5-5 5"/>',
  loop: '<path d="M17 3.5 19.5 6 17 8.5"/><path d="M19.5 6H8a3.5 3.5 0 0 0-3.5 3.5V11M7 20.5 4.5 18 7 15.5"/><path d="M4.5 18H16a3.5 3.5 0 0 0 3.5-3.5V13"/>',
  captions: '<rect x="3.5" y="5.5" width="17" height="13" rx="2"/><path d="M10.5 10.3a2 2 0 1 0 0 3.4M16.5 10.3a2 2 0 1 0 0 3.4"/>',
  camera: '<path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2.3l1.5-2h5.4l1.5 2h2.3A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5z"/><circle cx="12" cy="12.5" r="3.5"/>',
  pip: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><rect x="12" y="11.5" width="6" height="5" rx="1"/>',
  expand: '<path d="M4.5 9V4.5H9M15 4.5h4.5V9M19.5 15v4.5H15M9 19.5H4.5V15"/>',
  shrink: '<path d="M9 4.5V9H4.5M19.5 9H15V4.5M15 19.5V15h4.5M4.5 15H9v4.5"/>',
  back: '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4.5v3.7h3.7"/>',
  forward: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v3.7h-3.7"/>',
  skip: '<path d="M6 6.5v11l8-5.5z"/><path d="M18 6.5v11"/>',
  download: '<path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 19.5h14"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  clock: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l2.5 2.5"/>',
  sliders: '<path d="M4 7h10m4 0h2M4 17h4m4 0h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v4h-4"/>',
  eye: '<path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.6"/>',
  pause: '<path d="M9 6.5v11M15 6.5v11"/>',
  play: '<path d="M8 5.8v12.4a.6.6 0 0 0 .9.5l9.4-6.2a.6.6 0 0 0 0-1L8.9 5.3a.6.6 0 0 0-.9.5z"/>',
  x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  folder: '<path d="M3.5 7.5A1.5 1.5 0 0 1 5 6h4l2 2h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z"/>',
  external: '<path d="M14 4.5h5.5V10M19.5 4.5 11 13M17.5 14v4.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1v-11a1 1 0 0 1 1-1H10"/>',
  log: '<path d="M5 7h14M5 12h14M5 17h9"/>',
  trash: '<path d="M4.5 7h15M10 7V4.8h4V7M6.8 7l.9 12.2h8.6L17.2 7"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  aperture: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5l3.3 8.5M20.5 12l-8.5 3.3M12 20.5l-3.3-8.5M3.5 12l8.5-3.3"/>',
  film: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M7.5 5v14M16.5 5v14M3.5 9.5h4M3.5 14.5h4M16.5 9.5h4M16.5 14.5h4"/>',
  music: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
  image: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4.5 3.5"/>',
  text: '<path d="M5 6h14M5 10h14M5 14h10M5 18h7"/>',
  search: '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.5-4.5"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  clipboard: '<rect x="8" y="3.5" width="8" height="4" rx="1"/><path d="M8 5.5H6.5A1.5 1.5 0 0 0 5 7v12a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19V7a1.5 1.5 0 0 0-1.5-1.5H16"/>',
  file: '<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  left: '<path d="M15 5.5 8.5 12l6.5 6.5"/>',
  right: '<path d="M9 5.5 15.5 12 9 18.5"/>',
  up: '<path d="M6 14.5 12 8.5l6 6"/>',
  top: '<path d="M6 17.5 12 11.5l6 6M6 6.5h12"/>',
  bell: '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  wrench: '<path d="M14.5 5.5a4 4 0 0 0-5 5L4.5 15.5a1.4 1.4 0 0 0 2 2l5-5a4 4 0 0 0 5-5l-2.4 2.4-2-2z"/>',
  scissors: '<circle cx="6.5" cy="7" r="2.5"/><circle cx="6.5" cy="17" r="2.5"/><path d="M8.6 8.5 19.5 17M8.6 15.5 19.5 7"/>',
  eraser: '<path d="M8 19.5 4.6 16.1a1.5 1.5 0 0 1 0-2.1l9-9a1.5 1.5 0 0 1 2.1 0l3.4 3.4a1.5 1.5 0 0 1 0 2.1l-8.9 9zM9.3 9.3l5.4 5.4M11 19.5h8.5"/>',
  minimize: '<path d="M4.5 12h15"/>',
  maximize: '<rect x="4.5" y="4.5" width="15" height="15" rx="2"/>',
  restore: '<rect x="4.5" y="7.5" width="12" height="12" rx="2"/><path d="M7.5 7.5v-1a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-1"/>',
  close: '<path d="m4.5 4.5 15 15m0-15-15 15"/>',
};

/** @param {string} name */
function icon(name) {
  return `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] ?? ""}</svg>`;
}

/**
 * The one element a selector names; a missing one is a bug in this file.
 * @template {Element} [T=HTMLElement]
 * @param {string} selector
 * @param {ParentNode} [root]
 * @returns {T}
 */
function $(selector, root = document) {
  const found = root.querySelector(selector);
  if (!found) {
    throw new Error(`The window has no ${selector}`);
  }
  return /** @type {T} */ (found);
}

/**
 * @template {Element} [T=HTMLElement]
 * @param {string} selector
 * @param {ParentNode} [root]
 * @returns {T[]}
 */
function $$(selector, root = document) {
  return /** @type {T[]} */ ([...root.querySelectorAll(selector)]);
}

/** Titles, uploaders and file names come from websites: every one goes through here. */
const ESCAPES = /** @type {Record<string, string>} */ ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
});

/** @param {string | number | null | undefined} value */
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/gu, (c) => ESCAPES[c] ?? c);
}

/** @param {string} url */
function safeSrc(url) {
  return /^(?:https?|file):\/\//iu.test(url) ? url : "";
}

/** @param {number | null | undefined} n */
function bytes(n) {
  if (n === null || n === undefined || Number.isNaN(n)) {
    return "";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = n;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const digits = unit === 0 || value >= 10 ? 0 : 1;
  const shown = new Intl.NumberFormat(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value);
  return `${shown}\u00a0${units[unit] ?? ""}`;
}

/** @param {number | null | undefined} seconds */
function dur(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return "";
  }
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const pad = (/** @type {number} */ v) => String(v).padStart(2, "0");
  return h ? `${String(h)}:${pad(m)}:${pad(s % 60)}` : `${String(m)}:${pad(s % 60)}`;
}

/** @param {number | null | undefined} stamp */
function ago(stamp) {
  if (!stamp) {
    return "";
  }
  const d = Date.now() / 1000 - stamp;
  if (d < 60) {
    return "just now";
  }
  if (d < 3600) {
    return `${String(Math.floor(d / 60))}m ago`;
  }
  if (d < 86400) {
    return `${String(Math.floor(d / 3600))}h ago`;
  }
  if (d < 86400 * 7) {
    return `${String(Math.floor(d / 86400))}d ago`;
  }
  return new Date(stamp * 1000).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** yt-dlp's upload_date, 20140514, as the reader's own calendar writes it. @param {string} date */
function uploaded(date) {
  const day = new Date(Date.UTC(Number(date.slice(0, 4)), Number(date.slice(4, 6)) - 1, Number(date.slice(6, 8))));
  return day.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

const PERCENT = new Intl.NumberFormat(undefined, { style: "percent", maximumFractionDigits: 0 });

/** @type {number | undefined} */
let toastTimer;

/** @param {string} text */
/** @param {string} text @param {{ label: string, run: () => unknown }} [action] */
function toast(text, action) {
  const box = $("#toast");
  box.textContent = text;
  if (action) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn ghost small";
    button.textContent = action.label;
    on(button, "click", () => {
      box.classList.remove("on");
      return action.run();
    });
    box.append(button);
  }
  box.classList.add("on");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    box.classList.remove("on");
  }, action ? 7000 : 2400);
}

/** @param {unknown} problem */
function report(problem) {
  console.error(problem);
  toast(`Something went wrong: ${problem instanceof Error ? problem.message : String(problem)}`);
}

/**
 * Listen, and never let a failed promise vanish without a word.
 * @template {keyof HTMLElementEventMap} K
 * @param {EventTarget} target
 * @param {K} type
 * @param {(event: HTMLElementEventMap[K]) => unknown} handler
 */
function on(target, type, handler) {
  target.addEventListener(type, (event) => {
    const result = handler(/** @type {HTMLElementEventMap[K]} */ (event));
    if (result instanceof Promise) {
      result.catch(report);
    }
  });
}

/** @param {string} text */
async function copyText(text) {
  await navigator.clipboard.writeText(text);
  toast("Copied");
}

function api() {
  return window.pywebview.api;
}

/** @param {ParentNode} [root] */
function paintIcons(root = document) {
  for (const holder of $$("[data-i]", root)) {
    holder.outerHTML = icon(holder.dataset["i"] ?? "");
  }
}

/* ============================== state ============================== */

const S = {
  settings: /** @type {Settings} */ ({}),
  defaults: /** @type {Settings} */ ({}),
  browsers: /** @type {string[]} */ ([]),
  afterimage: false,
  textRemoval: /** @type {TextRemoval | null} */ (null),
  presets: /** @type {string[]} */ ([]),
  builtin: /** @type {string[]} */ ([]),
  version: "",
  state: /** @type {State | null} */ (null),
  tab: "downloads",
  lib: /** @type {LibFile[]} */ ([]),
  libFilter: "all",
  /** Files picked in the library, by path, and whether a click picks rather than opens. */
  libPicked: /** @type {Set<string>} */ (new Set()),
  libPicking: false,
  libLast: -1,
  libShown: 240,
  hist: /** @type {HistoryData | null} */ (null),
  preview: /** @type {PreviewState | null} */ (null),
  logs: new Set(/** @type {string[]} */ ([])),
  picked: new Set(/** @type {string[]} */ ([])),
  clipSeen: new Set(/** @type {string[]} */ ([])),
  offer: /** @type {string[]} */ ([]),
  results: /** @type {SearchResult[]} */ ([]),
  resultPicks: new Set(/** @type {number[]} */ ([])),
  editingSub: "",
};

/**
 * @typedef {object} PreviewState
 * @property {string} url
 * @property {boolean} loading
 * @property {Probe | null} probe
 * @property {string} spec
 * @property {Set<number> | null} picked
 * @property {Set<string>} chapters
 * @property {string} rename
 * @property {string} folder
 * @property {{ start: number, end: number }} span the part to download, both 0 for all of it
 * @property {boolean} formats whether the formats table is unfolded
 * @property {{ watch: HTMLElement | null, bar: HTMLElement } | null} clip the player and clip bar, made once and kept across redraws
 */

/** The four download folders, which All in One Place sets together. */
const FOLDER_KEYS = /** @type {SettingKey[]} */ (["folder", "audio_folder", "picture_folder", "text_folder"]);

const DRAWER = /** @type {SettingKey[]} */ ([
  "container", "codec", "always_plays", "prefer_sdr", "subs", "sub_langs", "auto_subs", "audio_lang", "strip_metadata",
  "audio_quality", "music", "square_cover", "playlist", "items", "playlist_reverse", "section", "precise_cuts",
  "skip_shorts", "skip_live", "skip_members", "min_duration", "max_duration", "date_after",
  "date_before", "title_match", "title_skip", "max_items", "live_from_start", "wait_for_live",
  "embed_thumbnail", "embed_metadata", "embed_chapters", "split_chapters", "write_thumbnail",
  "write_description", "write_info_json", "write_comments", "sponsorblock", "sponsor_categories",
  "range", "ugoira", "gallery_filter", "write_metadata", "zip", "remove_text", "archive",
]);

const FOLDS = "keepsake.drawer";

/** Folds each group of options to its name, remembering which are open. */
function bindDrawerFolds() {
  /** @type {string[]} */
  let open = [];
  try {
    const kept = /** @type {unknown} */ (JSON.parse(localStorage.getItem(FOLDS) ?? "[]"));
    open = Array.isArray(kept) ? kept.filter((name) => typeof name === "string") : [];
  } catch {
    // Storage can be missing or blocked; every group starts folded.
  }
  for (const group of $$("#drawer .group")) {
    const legend = $("legend", group);
    const name = legend.textContent.trim();
    group.dataset["fold"] = name;
    legend.innerHTML = `<button type="button" class="fold" aria-expanded="false"><span class="chev">${icon("right")}</span><span>${esc(name)}</span><span class="set"></span></button>`;
    const fold = $(".fold", legend);
    const setOpen = (/** @type {boolean} */ shown) => {
      group.classList.toggle("open", shown);
      fold.setAttribute("aria-expanded", String(shown));
    };
    setOpen(open.includes(name));
    on(fold, "click", () => {
      setOpen(!group.classList.contains("open"));
      open = $$("#drawer .group.open").map((each) => each.dataset["fold"] ?? "");
      try {
        localStorage.setItem(FOLDS, JSON.stringify(open));
      } catch {
        // Nowhere to keep it: the drawer just forgets.
      }
    });
  }
}

/** Says beside each group of options how many of its settings differ from the defaults. */
function paintFolds() {
  for (const group of $$("#drawer .group")) {
    const keys = $$("[data-set]", group).map((el) => el.dataset["set"] ?? "").filter(isSetting);
    const changed = keys.filter((key) => S.settings[key] !== S.defaults[key]).length;
    const set = group.querySelector(".fold .set");
    if (set) {
      set.textContent = changed ? `${String(changed)} changed` : "";
    }
  }
}

/* ============================== settings ============================== */

/** @param {string} key @returns {key is SettingKey} */
function isSetting(key) {
  return key in S.settings;
}

/** @param {HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement} el */
function readControl(el) {
  if (el instanceof HTMLInputElement && el.type === "checkbox") {
    return el.checked;
  }
  return el.value;
}

function paintSettings() {
  for (const el of $$("[data-set]")) {
    const key = el.dataset["set"] ?? "";
    if (!isSetting(key)) {
      continue;
    }
    const value = S.settings[key];
    if (el instanceof HTMLInputElement && el.type === "checkbox") {
      el.checked = Boolean(value);
    } else if (
      (el instanceof HTMLInputElement || el instanceof HTMLSelectElement) &&
      document.activeElement !== el
    ) {
      el.value = String(value);
    }
  }
  document.body.dataset["mode"] = S.settings.mode;
  // Removing metadata overrides what would put it back, so those switches show
  // off and grey while it is on, and their own values again once it is not.
  for (const el of $$("[data-meta]")) {
    if (el instanceof HTMLInputElement) {
      const key = el.dataset["set"] ?? "";
      el.disabled = S.settings.strip_metadata;
      el.checked = !el.disabled && isSetting(key) && S.settings[key] === true;
    }
  }
  // Best quality never re-encodes: the switches that would show off and grey,
  // and a lossy Pixiv conversion shows as the untouched MKV it becomes.
  const best = S.settings.quality === "best";
  for (const el of $$("[data-lossy]")) {
    if (el instanceof HTMLInputElement) {
      const key = el.dataset["set"] ?? "";
      el.disabled = best;
      el.checked = !best && isSetting(key) && S.settings[key] === true;
    }
  }
  for (const hint of $$("[data-best-hint]")) {
    hint.hidden = !best;
  }
  const ugoira = $("#ugoira");
  if (ugoira instanceof HTMLSelectElement) {
    for (const option of ugoira.options) {
      option.disabled = best && option.hasAttribute("data-lossy");
    }
    if (best && ugoira.selectedOptions[0]?.hasAttribute("data-lossy")) {
      ugoira.value = "copy";
    }
  }
  paintFolds();
  const changed = DRAWER.filter((key) => S.settings[key] !== S.defaults[key]).length;
  const badge = $("#optcount");
  badge.hidden = changed === 0;
  badge.textContent = String(changed);
  for (const el of $$("[data-folder-show]")) {
    const key = el.dataset["folderShow"] ?? "";
    const folder = isSetting(key) ? String(S.settings[key]) || S.settings.folder : "";
    // Isolated, or the right-to-left box that trims a long path carries a leading slash to its end.
    el.replaceChildren(Object.assign(document.createElement("bdi"), { textContent: folder }));
    el.title = folder;
  }
  const preset = $("#template-preset", document);
  if (preset instanceof HTMLSelectElement) {
    preset.value = [...preset.options].some((o) => o.value === S.settings.template) ? S.settings.template : "";
    $("#template-row").hidden = Boolean(preset.value);
  }
  const spots = FOLDER_KEYS.map((key) => S.settings[key]);
  const where = spots.every((spot) => spot === spots[0]) ? "downloads" : FOLDER_KEYS.every((key) => S.settings[key] === S.defaults[key]) ? "own" : "";
  for (const button of $$("[data-folders]")) {
    button.classList.toggle("on", button.dataset["folders"] === where);
    button.setAttribute("aria-pressed", String(button.dataset["folders"] === where));
  }
  $("#cookie-file-row").hidden = S.settings.cookies !== "file";
  $("#cookie-file-show").textContent = S.settings.cookie_file || "None chosen";
  paintTextRemoval();
}

/* ============================== text removal ============================== */

const DETEXT_TYPES = /\.(?:jpe?g|jfif|png|webp)$/iu;

function textRemovalReady() {
  return Boolean(S.textRemoval && (S.textRemoval.quick || S.textRemoval.best));
}

function settingUpTextRemoval() {
  return S.state?.jobs.some((j) => j.job_kind === "setup" && j.url.startsWith("text-removal") && (j.status === "queued" || j.status === "running")) ?? false;
}

/** Text removal is optional: until it is set up, Settings is the only place that mentions it. */
function paintTextRemoval() {
  const t = S.textRemoval;
  if (!t) {
    return;
  }
  const ready = textRemovalReady();
  const busy = settingUpTextRemoval();
  const offerBest = t.best_possible && !t.best;
  let about = "Saves a copy of a picture with its captions, stickers and watermarks taken off.";
  if (busy) {
    about += " It is being set up: follow it in the queue.";
  } else if (ready) {
    about += ` ${t.best ? "Best" : "Quick"} is set up, so press T on a picture in the library.`;
  } else {
    about += ` Optional. Quick works on any computer and is about ${bytes(t.quick_size)}.`;
  }
  if (offerBest && !busy) {
    about += ` Best needs the ${t.card} and is about ${bytes(t.best_size)}.`;
  }
  $("#detext-about").textContent = about;
  $("#detext-quick").hidden = busy || ready;
  $("#detext-best").hidden = busy || !offerBest;
  $("#detext-forget").hidden = busy || !ready;
  $("#remove-text-row").hidden = !ready;
  $("#remove-text-hint").hidden = !ready || S.settings.remove_text === "off";
  for (const option of /** @type {HTMLSelectElement} */ ($("#remove-text")).options) {
    option.disabled = option.value !== "off" && !t[/** @type {"quick" | "best"} */ (option.value)];
  }
  const f = current();
  $("#lb-detext").hidden = !ready || f?.kind !== "image" || !DETEXT_TYPES.test(f.name);
}

async function refreshTextRemoval() {
  S.textRemoval = await api().text_removal();
  paintTextRemoval();
  paintPicks();
}

/** @type {number | undefined} */
let forgetTimer;

function disarmForget() {
  const button = $("#detext-forget");
  button.classList.remove("confirming");
  button.textContent = "Uninstall";
  window.clearTimeout(forgetTimer);
}

/** @param {string} tier */
async function setUpTextRemoval(tier) {
  if (await api().set_up_text_removal(tier)) {
    toast("Setting it up: follow it in the queue");
    await poll();
    paintTextRemoval();
  }
}

function bindTextRemoval() {
  on($("#show-keys"), "click", () => {
    /** @type {HTMLDialogElement} */ ($("#help")).showModal();
  });
  on($("#detext-quick"), "click", () => setUpTextRemoval("quick"));
  on($("#detext-best"), "click", () => setUpTextRemoval("best"));
  on($("#detext-forget"), "click", async () => {
    const button = $("#detext-forget");
    if (!button.classList.contains("confirming")) {
      button.classList.add("confirming");
      button.textContent = "Delete it and its models?";
      forgetTimer = window.setTimeout(disarmForget, 3500);
      return;
    }
    disarmForget();
    S.textRemoval = await api().forget_text_removal();
    paintTextRemoval();
    toast(textRemovalReady() ? "It is being set up: try again when that is done" : "Uninstalled");
  });
  on($("#lb-detext"), "click", removeTextHere);
  on($("#lib-detext"), "click", removeTextFromPicked);
}

async function removeTextHere() {
  const f = current();
  if (f?.kind !== "image" || !DETEXT_TYPES.test(f.name)) {
    return;
  }
  if (!textRemovalReady()) {
    toast("Removing added text is an optional download", {
      label: "Set It Up",
      run: () => {
        closeBox();
        show("settings");
        $("#text-removal").scrollIntoView({ block: "center" });
      },
    });
    return;
  }
  await startSaving($("#lb-detext"), f, "detext");
}

/** @returns {string[]} the picked files text removal can clean */
function pickedPictures() {
  return S.lib.filter((f) => S.libPicked.has(f.path) && f.kind === "image" && DETEXT_TYPES.test(f.name)).map((f) => f.path);
}

async function removeTextFromPicked() {
  const pictures = pickedPictures();
  if (!pictures.length || !textRemovalReady()) {
    return;
  }
  const id = await api().remove_text(pictures);
  toast(id ? `Saving ${String(pictures.length)} picture${pictures.length === 1 ? "" : "s"} without added text: follow it in the queue` : "Could not start removing the text");
}

/** @type {Partial<Settings>} */
let pending = {};
/** @type {number | undefined} */
let saveTimer;

/**
 * @param {SettingKey} key
 * @param {SettingValue} value
 */
function save(key, value) {
  S.settings = { ...S.settings, [key]: value };
  pending = { ...pending, [key]: value };
  paintSettings();
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => {
    const changes = pending;
    pending = {};
    api().save_settings(changes).then((saved) => {
      S.settings = saved;
      paintSettings();
    }).catch(report);
  }, 300);
}

function bindSettings() {
  for (const el of $$("[data-set]")) {
    if (!(el instanceof HTMLInputElement || el instanceof HTMLSelectElement)) {
      continue;
    }
    const typing = el instanceof HTMLInputElement && el.type !== "checkbox";
    on(el, typing ? "input" : "change", () => {
      const key = el.dataset["set"] ?? "";
      if (isSetting(key)) {
        const numeric = typeof S.defaults[key] === "number";
        const value = readControl(el);
        save(key, numeric && typeof value === "string" ? Number(value) : value);
      }
    });
  }
  const preset = $("#template-preset");
  on(preset, "change", () => {
    if (preset instanceof HTMLSelectElement && preset.value) {
      save("template", preset.value);
    } else {
      $("#template-row").hidden = false;
      $("#template").focus();
    }
  });
}

function fillCookies() {
  /** @type {Record<string, string>} */
  const names = {
    firefox: "Firefox", chrome: "Chrome", edge: "Edge", brave: "Brave", vivaldi: "Vivaldi",
    opera: "Opera", chromium: "Chromium",
  };
  const found = S.browsers.map((b) => `<option value="${esc(b)}">From ${esc(names[b] ?? b)}</option>`).join("");
  $("#cookies").innerHTML = `<option value="auto">Automatic</option><option value="none">Never</option>${found}<option value="file">From a cookies.txt file</option>`;
}

function fillPresets() {
  const select = $("#preset");
  const mine = S.presets.filter((name) => !S.builtin.includes(name));
  select.innerHTML = `<option value="">Preset…</option>${S.builtin.map((n) => `<option>${esc(n)}</option>`).join("")}${
    mine.length ? `<optgroup label="Yours">${mine.map((n) => `<option>${esc(n)}</option>`).join("")}</optgroup>` : ""
  }<option value="+save">Save these options as a preset…</option>`;
  $("#preset-list").innerHTML = mine.length
    ? mine.map((n) => `<span class="chip">${esc(n)}<button type="button" class="icon-btn" data-preset-del="${esc(n)}" title="Delete" aria-label="Delete ${esc(n)}">${icon("x")}</button></span>`).join("")
    : '<span class="dim">Presets you save from the Preset menu on the Downloads page appear here.</span>';
}

/**
 * Ask for one line of text in the window's own dialog, never the browser's.
 * @param {string} title
 * @param {string} [value]
 * @returns {Promise<string | null>}
 */
function ask(title, value = "") {
  const dialog = /** @type {HTMLDialogElement} */ ($("#ask"));
  const input = /** @type {HTMLInputElement} */ ($("#ask-input"));
  $("#ask-title").textContent = title;
  input.value = value;
  dialog.showModal();
  input.select();
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => {
      resolve(dialog.returnValue === "ok" && input.value.trim() ? input.value.trim() : null);
    }, { once: true });
  });
}

/* ============================== pages ============================== */

const PAGES = ["downloads", "search", "subscriptions", "library", "history", "settings"];

/** @param {string} tab */
function show(tab) {
  S.tab = tab;
  for (const button of $$("nav button")) {
    button.classList.toggle("on", button.dataset["tab"] === tab);
  }
  for (const page of $$("main > .page")) {
    page.hidden = page.id !== tab;
  }
  if (tab === "library") {
    void loadLibrary();
  } else if (tab === "history") {
    void loadHistory();
  } else if (tab === "settings") {
    void loadSettingsExtras();
    $("#settings").dispatchEvent(new Event("scroll"));
  } else if (tab === "downloads") {
    urls().focus();
  } else if (tab === "search") {
    $("#search-q").focus();
  }
}

/* ============================== composer ============================== */

function urls() {
  return /** @type {HTMLTextAreaElement} */ ($("#urls"));
}

function grow() {
  const box = urls();
  box.style.height = "auto";
  box.style.height = `${String(Math.min(box.scrollHeight, 190))}px`;
}

async function download() {
  const text = urls().value.trim();
  if (!text) {
    urls().focus();
    return;
  }
  const { found, added, before } = await api().add(text, S.settings.mode, null);
  if (!found) {
    toast("No links in that");
    return;
  }
  urls().value = "";
  grow();
  if (!added) {
    toast(found === 1 ? "Already in the queue" : "All of those are already in the queue");
  } else if (before) {
    toast(S.settings.archive
      ? `${before === found ? "Downloaded before" : `${String(before)} of these were downloaded before`}, so Skip anything already downloaded passes over it. Download Again on its row fetches it anyway.`
      : `${before === found ? "Downloaded before" : `${String(before)} of these were downloaded before`}. Fetching again.`);
  } else {
    toast(added === 1 ? "Added to the queue" : `Added ${String(added)} downloads`);
  }
  await poll();
}

/** @param {string} [given] @param {boolean} [clip] open with the clip bar in hand */
async function preview(given, clip = false) {
  const url = given ?? urls().value.split("\n").map((line) => line.trim()).find(Boolean) ?? "";
  if (!url) {
    urls().focus();
    toast("Paste a link first");
    return;
  }
  show("downloads");
  S.preview = { url, loading: true, probe: null, spec: "", picked: null, chapters: new Set(), rename: "", folder: "", span: { start: 0, end: 0 }, formats: false, clip: null };
  renderPreview();
  const probe = await api().probe(url, S.settings.mode);
  const still = openPreview();
  if (still?.url !== url) {
    return;
  }
  S.preview = { ...still, loading: false, probe };
  if (!failed(probe) && probe.kind === "video" && probe.duration && probe.live !== "is_live") {
    S.preview.clip = previewClip(S.preview, probe);
  }
  renderPreview();
  if (clip) {
    handClip();
  }
}

/** Brings the preview's clip bar into view with the keyboard on it, or says why there is none. */
function handClip() {
  const bar = S.preview?.clip?.bar;
  if (!bar) {
    toast("There is no single video here to clip, so this is a plain preview");
    return;
  }
  bar.scrollIntoView({ block: "nearest", behavior: "smooth" });
  /** @type {HTMLElement | null} */ (bar.querySelector("[tabindex]"))?.focus({ preventScroll: true });
}

/**
 * The preview as it is now, which the user may have closed or replaced during an await.
 * @returns {PreviewState | null}
 */
function openPreview() {
  return S.preview;
}

/** @param {Probe} probe @returns {probe is ProbeFailure} */
function failed(probe) {
  return "error" in probe;
}

function renderPreview() {
  const box = $("#preview");
  const p = S.preview;
  box.hidden = !p;
  // The preview carries its own Download, so the red block moves there.
  $("#download-btn").classList.toggle("primary", !p);
  if (!p) {
    box.replaceChildren();
    return;
  }
  if (p.loading || !p.probe) {
    box.innerHTML = `<div class="loading"><span class="spinner"></span><span>Reading <span class="mono dim">${esc(p.url)}</span>…</span><span class="grow"></span><button type="button" class="icon-btn" data-pv="close" title="Close" aria-label="Close">${icon("x")}</button></div>`;
    return;
  }
  const probe = p.probe;
  if (failed(probe)) {
    box.innerHTML = `<div class="top bare"><div><h2 class="error">${esc(probe.error)}</h2><p class="dim">${esc(probe.advice)}</p>
      <div class="actions"><button type="button" class="btn primary" data-pv="download">${icon("download")}Try downloading anyway</button><button type="button" class="btn ghost" data-pv="close">Close</button></div></div></div>`;
    return;
  }
  box.innerHTML = previewTop(p, probe) + previewBody(p, probe);
  if (p.clip) {
    if (p.clip.watch) {
      box.querySelector(".poster.watch")?.append(p.clip.watch);
    }
    box.querySelector(".pv-clip-slot")?.replaceWith(p.clip.bar);
  }
  for (const img of $$(".shots img", box)) {
    on(img, "error", () => {
      img.remove();
    });
  }
}

/**
 * @param {PreviewState} p
 * @param {VideoProbe | GalleryProbe} probe
 */
function previewTop(p, probe) {
  const video = probe.kind === "gallery" ? null : probe;
  const facts = [
    probe.site, probe.uploader,
    video?.kind === "video" ? dur(video.duration) : "",
    video?.kind === "playlist" ? `${String(video.count)} items` : "",
    probe.kind === "gallery" ? `${String(probe.count)}${probe.more ? "+" : ""} file${probe.count === 1 && !probe.more ? "" : "s"}` : "",
    video?.date ? uploaded(video.date) : "",
    video?.views ? `${video.views.toLocaleString()} views` : "",
    video?.live === "is_live" ? "live now" : video?.live === "is_upcoming" ? "not started yet" : "",
  ].filter(Boolean);
  const thumb = probe.kind === "gallery" ? "" : safeSrc(probe.thumb);
  const picked = p.picked ? p.picked.size : probe.count;
  const label = probe.kind === "playlist"
    ? `Download ${picked === probe.count ? `all ${String(probe.count)}` : `${String(picked)} of ${String(probe.count)}`}`
    : probe.kind === "gallery" ? "Download gallery" : previewLabel(p);
  const before = probe.before
    ? `<p class="before">${icon("check")} You downloaded this ${esc(ago(probe.before))}. <button type="button" class="btn ghost small" data-pv="again">Download it again anyway</button></p>`
    : "";
  const fine = video?.kind === "video"
    ? `<div class="fine"><label for="pv-rename">Name</label><input class="field" id="pv-rename" data-pv-field="rename" placeholder="${esc(probe.title)}" value="${esc(p.rename)}">
      <span>Folder</span><span class="c"><button type="button" class="btn small path" data-pv="open-folder" title="Open ${esc(p.folder || video.folder)}">${icon("folder")}<span class="where"><bdi>${esc(p.folder || video.folder)}</bdi></span></button><button type="button" class="btn ghost small" data-pv="folder">Change</button></span>
      <span>Saves as</span><span class="file" title="${esc(video.file)}">${esc(video.file)}</span></div>`
    : "";
  const poster = p.clip?.watch
    ? '<div class="poster watch"></div>'
    : thumb ? `<div class="poster"><img src="${esc(thumb)}" width="256" height="144" referrerpolicy="no-referrer" alt=""></div>` : "";
  return `<div class="top ${poster ? "" : "bare"} ${p.clip?.watch ? "watching" : ""}">${poster}
    <div><h2>${esc(probe.title)}</h2><div class="facts">${facts.map((f) => `<span>${esc(f)}</span>`).join("")}</div>${before}${fine}
    <div class="actions"><button type="button" class="btn primary" data-pv="download" ${probe.kind === "playlist" && !picked ? "disabled" : ""}>${icon("download")}<span class="pv-label">${esc(label)}</span></button>
    ${probe.kind === "playlist" ? '<button type="button" class="btn" data-pv="all">Select all</button><button type="button" class="btn" data-pv="none">None</button>' : ""}
    <button type="button" class="btn ghost" data-pv="subscribe">${icon("bell")}Subscribe</button>
    <button type="button" class="btn ghost" data-pv="open">${icon("external")}Open page</button><button type="button" class="btn ghost" data-pv="close">Close</button></div></div></div>`;
}

/**
 * @param {PreviewState} p
 * @param {VideoProbe | GalleryProbe} probe
 */
function previewBody(p, probe) {
  if (probe.kind === "gallery") {
    return probe.previews.length
      ? `<div class="shots">${probe.previews.map((u) => (safeSrc(u) ? `<img src="${esc(u)}" width="92" height="92" loading="lazy" referrerpolicy="no-referrer" alt="">` : "")).join("")}</div>`
      : "";
  }
  if (probe.kind === "playlist") {
    return `<div class="section-title">Items</div><div class="entries">${probe.entries.map((e, i) => `<label><input type="checkbox" data-idx="${String(i + 1)}" ${!p.picked || p.picked.has(i + 1) ? "checked" : ""}>
      <span class="n">${String(i + 1)}</span><span class="d">${esc(dur(e.duration))}</span><span class="t">${esc(e.title)}</span></label>`).join("")}</div>`;
  }
  let body = p.clip ? '<div class="section-title">Clip<span class="hint">Download only part of it</span></div><div class="pv-clip-slot"></div>' : "";
  if (probe.chapters.length) {
    body += `<div class="section-title">Chapters<span class="hint">Tick to download only those</span></div><div class="entries">${probe.chapters.map((c, i) => `<label><input type="checkbox" data-chapter="${esc(c.title)}" ${p.chapters.has(c.title) ? "checked" : ""}>
      <span class="n">${String(i + 1)}</span><span class="d">${esc(dur(c.start))}</span><span class="t">${esc(c.title)}</span></label>`).join("")}</div>`;
  }
  if (probe.formats.length) {
    body += `<button type="button" class="section-title fold" data-pv="formats" aria-expanded="${String(p.formats)}"><span class="chev">${icon("right")}</span><span>Formats</span><span class="hint">${p.spec ? "One picked" : `${String(probe.formats.length)} to pick from, or let the options above decide`}</span></button>`;
  }
  if (probe.formats.length && p.formats) {
    const automatic = S.settings.mode === "audio" ? "best audio" : S.settings.quality === "best" ? "best quality" : `${S.settings.quality}p at most`;
    body += `<div class="table-wrap"><table class="formats"><thead><tr><th>ID</th><th>Ext</th><th>Resolution</th><th>FPS</th><th>Video</th><th>Audio</th><th>Lang</th><th class="r">Size</th><th class="r">Bitrate</th><th>Note</th></tr></thead><tbody>
      <tr data-spec="" class="${p.spec ? "" : "on"}"><td colspan="10" class="auto">Automatic: the options above decide (${esc(automatic)})</td></tr>
      ${probe.formats.map((f) => `<tr data-spec="${esc(f.spec)}" class="${p.spec === f.spec ? "on" : ""}"><td>${esc(f.id)}</td><td>${esc(f.ext)}</td><td>${esc(f.res)}</td><td>${esc(f.fps ?? "")}</td>
        <td>${esc(f.vcodec)}</td><td>${esc(f.acodec)}</td><td>${esc(f.lang)}</td><td class="r">${esc(bytes(f.size))}</td><td class="r">${f.tbr ? `${String(Math.round(f.tbr))}k` : ""}</td><td>${esc(f.note)}</td></tr>`).join("")}
      </tbody></table></div>`;
  }
  return body;
}

/** What the preview's download button does, in its own words. @param {PreviewState} p */
function previewLabel(p) {
  if (p.span.end > p.span.start) {
    return `Download ${(p.span.end - p.span.start).toFixed(1)} seconds`;
  }
  if (p.spec) {
    return "Download this format";
  }
  return p.chapters.size ? `Download ${String(p.chapters.size)} chapter${p.chapters.size === 1 ? "" : "s"}` : "Download";
}

/**
 * The link's own video, in the thumbnail's place, to watch while choosing a part with the clip bar.
 * Pictures only and small: it is there to find the moments, and the download decides the quality.
 * @param {PreviewState} p @param {VideoProbe} probe
 */
function previewClip(p, probe) {
  const zone = document.createElement("div");
  const poster = safeSrc(probe.thumb);
  zone.innerHTML = `${probe.watch ? miniPlayer(probe.watch, poster) : ""}<div class="tools-bar pv-clip">${clipMarkup()}</div>`;
  const video = zone.querySelector("video");
  const watch = /** @type {HTMLElement | null} */ (zone.querySelector(".player"));
  const strip = /** @type {HTMLElement} */ (zone.querySelector(".pv-clip"));
  const repaint = video && watch ? bindMiniPlayer(watch, video, p.span) : () => undefined;
  if (video && probe.listen) {
    follow(video, new Audio(probe.listen));
  }
  if (video) {
    keepToSpan(video, p.span, () => false);
  }
  const media = () => (video && Number.isFinite(video.duration) ? video : null);
  const length = () => media()?.duration ?? probe.duration ?? 0;
  const bar = clipBar(strip, media, length, p.span, () => {
    bar.paint();
    repaint();
    const label = document.querySelector("#preview .pv-label");
    if (label) {
      label.textContent = previewLabel(p);
    }
  });
  if (video) {
    for (const type of /** @type {const} */ (["loadedmetadata", "timeupdate", "seeked"])) {
      on(video, type, () => {
        bar.paint();
      });
    }
  }
  window.requestAnimationFrame(() => {
    bar.paint();
  });
  return { watch, bar: strip };
}

/** The preview's small player, drawn like the viewer's. @param {string} src @param {string} poster */
function miniPlayer(src, poster) {
  /** @param {string} act @param {string} name @param {string} label */
  const pb = (act, name, label) => `<button type="button" class="icon-btn" data-p="${act}" title="${esc(label)}" aria-label="${esc(label)}">${icon(name)}</button>`;
  return `<div class="player video mini">
      <video src="${esc(src)}" preload="metadata" playsinline ${poster ? `poster="${esc(poster)}"` : ""}></video>
      <div class="controls">
        <div class="timeline" role="slider" tabindex="0" aria-label="Position" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0">
          <div class="groove"><div class="buffered"></div><div class="marked" hidden></div><div class="played"></div><div class="knob"></div></div>
        </div>
        <div class="deck-bar">${pb("play", "play", "Play")}${pb("mute", "volume", "Mute")}<span class="time">0:00 / 0:00</span><span class="grow"></span>${pb("full", "expand", "Full screen")}</div>
      </div>
    </div>`;
}

/**
 * Wires the preview's player: play, a timeline that shows the marked part and seeks where
 * it is pressed or dragged, mute and full screen. Returns its repaint.
 * @param {HTMLElement} root @param {HTMLVideoElement} video @param {{ start: number, end: number }} span
 */
function bindMiniPlayer(root, video, span) {
  const total = () => (Number.isFinite(video.duration) ? video.duration : 0);
  const share = (/** @type {number} */ time) => `${String(total() ? Math.min(100, (time / total()) * 100) : 0)}%`;
  const paint = () => {
    $(".played", root).style.width = share(video.currentTime);
    $(".knob", root).style.left = share(video.currentTime);
    $(".buffered", root).style.width = share(video.buffered.length ? video.buffered.end(video.buffered.length - 1) : 0);
    const stretch = $(".marked", root);
    stretch.hidden = span.end <= span.start;
    stretch.style.left = share(span.start);
    stretch.style.width = share(span.end - span.start);
    $(".time", root).textContent = `${dur(video.currentTime)} / ${dur(total())}`;
    const line = $(".timeline", root);
    line.setAttribute("aria-valuemax", String(Math.round(total())));
    line.setAttribute("aria-valuenow", String(Math.round(video.currentTime)));
    paintButton(root, "play", video.paused ? "play" : "pause", video.paused ? "Play" : "Pause");
    paintButton(root, "mute", video.muted ? "mute" : "volume", video.muted ? "Sound on" : "Mute");
  };
  for (const type of /** @type {const} */ (["timeupdate", "progress", "play", "pause", "volumechange", "loadedmetadata", "durationchange"])) {
    on(video, type, paint);
  }
  on(root, "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest("[data-p]");
    const act = button instanceof HTMLElement ? button.dataset["p"] : target === video ? "play" : "";
    if (act === "play") {
      await togglePlay(video);
    } else if (act === "mute") {
      video.muted = !video.muted;
    } else if (act === "full") {
      await (document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen());
    }
  });
  const line = $(".timeline", root);
  const seekTo = (/** @type {PointerEvent} */ event) => {
    const edges = line.getBoundingClientRect();
    video.currentTime = Math.min(1, Math.max(0, (event.clientX - edges.left) / edges.width)) * total();
  };
  on(line, "pointerdown", (event) => {
    line.setPointerCapture(event.pointerId);
    seekTo(event);
  });
  on(line, "pointermove", (event) => {
    if (line.hasPointerCapture(event.pointerId)) {
      seekTo(event);
    }
  });
  on(line, "keydown", (event) => {
    const step = { ArrowLeft: -5, ArrowRight: 5 }[event.key];
    if (step) {
      event.preventDefault();
      video.currentTime = Math.min(total(), Math.max(0, video.currentTime + step));
    }
  });
  paint();
  return paint;
}

/**
 * Plays a sound stream along with a picture that has none, as if it were the picture's own.
 * @param {HTMLVideoElement} video @param {HTMLAudioElement} sound
 */
function follow(video, sound) {
  const align = () => {
    if (Math.abs(sound.currentTime - video.currentTime) > 0.25) {
      sound.currentTime = video.currentTime;
    }
  };
  on(video, "play", () => {
    align();
    // A pause before it starts rejects this, and the picture plays on without sound either way.
    sound.play().catch(() => undefined);
  });
  on(video, "pause", () => {
    sound.pause();
  });
  on(video, "seeked", align);
  on(video, "timeupdate", align);
  on(video, "ratechange", () => {
    sound.playbackRate = video.playbackRate;
  });
  on(video, "volumechange", () => {
    sound.volume = video.volume;
    sound.muted = video.muted;
  });
}

/**
 * Plays a marked clip as if it were the whole file: it stops at the clip's end, or goes round
 * when `loops` says so, and play from outside the clip starts it from the top. Checked every
 * frame, since timeupdate comes only four times a second and would run a quarter second over.
 * @param {HTMLMediaElement} media @param {{ start: number, end: number }} span @param {() => boolean} loops
 */
function keepToSpan(media, span, loops) {
  let frame = 0;
  const clipped = () => span.end > span.start;
  const watch = () => {
    frame = 0;
    if (media.paused || !clipped()) {
      return;
    }
    if (media.currentTime >= span.end) {
      if (!loops()) {
        media.pause();
        media.currentTime = span.end;
        return;
      }
      media.currentTime = span.start;
    }
    frame = window.requestAnimationFrame(watch);
  };
  on(media, "play", () => {
    if (clipped() && (media.currentTime < span.start || media.currentTime >= span.end - 0.05)) {
      media.currentTime = span.start;
    }
    if (!frame) {
      frame = window.requestAnimationFrame(watch);
    }
  });
}

/** @param {PreviewState} p @param {VideoProbe | GalleryProbe} probe */
function previewExtra(p, probe) {
  /** @type {Partial<Settings>} */
  const extra = {};
  if (p.spec) {
    extra.format = p.spec;
  }
  if (p.rename.trim()) {
    extra.rename = p.rename.trim();
  }
  if (p.folder) {
    extra.folder = p.folder;
  }
  if (p.chapters.size) {
    extra.chapters = [...p.chapters].join("\n");
  }
  if (p.span.end > p.span.start) {
    extra.section = `${String(p.span.start)}-${String(p.span.end)}`;
  }
  if (probe.kind === "playlist") {
    extra.playlist = true;
    if (p.picked && p.picked.size < probe.count) {
      extra.items = [...p.picked].sort((a, b) => a - b).join(",");
    }
  }
  return extra;
}

/** @param {string} act */
async function previewAction(act) {
  const p = S.preview;
  if (!p) {
    return;
  }
  const probe = p.probe;
  if (act === "close") {
    S.preview = null;
    renderPreview();
    return;
  }
  if (act === "formats") {
    p.formats = !p.formats;
    renderPreview();
    return;
  }
  if (act === "open") {
    await api().open_url(p.url);
    return;
  }
  if (act === "subscribe") {
    openSubForm({ url: p.url, name: probe && !failed(probe) ? probe.title : "" });
    return;
  }
  if (act === "open-folder" && probe && !failed(probe) && probe.kind !== "gallery") {
    if (!(await api().open_directory(p.folder || probe.folder))) {
      toast("That folder is not there any more");
    }
    return;
  }
  if (act === "folder") {
    const folder = await api().pick_folder(p.folder || (probe && !failed(probe) && probe.kind !== "gallery" ? probe.folder : ""));
    if (folder) {
      p.folder = folder;
      renderPreview();
    }
    return;
  }
  if (act === "all" || act === "none") {
    p.picked = act === "all" ? null : new Set();
    renderPreview();
    return;
  }
  const extra = probe && !failed(probe) ? previewExtra(p, probe) : {};
  if (act === "again") {
    extra.ignore_archive = true;
  }
  await api().add(p.url, S.settings.mode, extra);
  S.preview = null;
  renderPreview();
  if (urls().value.trim().split("\n").filter(Boolean).length <= 1) {
    urls().value = "";
    grow();
  }
  toast("Added to the queue");
  await poll();
}

function bindPreview() {
  const box = $("#preview");
  on(box, "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const p = S.preview;
    const row = target?.closest("tr[data-spec]");
    if (p && row instanceof HTMLElement) {
      p.spec = row.dataset["spec"] ?? "";
      renderPreview();
      return;
    }
    const button = target?.closest("[data-pv]");
    if (button instanceof HTMLElement) {
      await previewAction(button.dataset["pv"] ?? "");
    }
  });
  on(box, "input", (event) => {
    const p = S.preview;
    if (p && event.target instanceof HTMLInputElement && event.target.dataset["pvField"] === "rename") {
      p.rename = event.target.value;
    }
  });
  on(box, "change", (event) => {
    const p = S.preview;
    const input = event.target;
    if (!p || !(input instanceof HTMLInputElement) || !p.probe || failed(p.probe)) {
      return;
    }
    const probe = p.probe;
    if (input.dataset["chapter"] !== undefined) {
      const title = input.dataset["chapter"];
      if (input.checked) {
        p.chapters.add(title);
      } else {
        p.chapters.delete(title);
      }
    } else if (input.dataset["idx"] !== undefined && probe.kind === "playlist") {
      p.picked ??= new Set(probe.entries.map((_, i) => i + 1));
      const index = Number(input.dataset["idx"]);
      if (input.checked) {
        p.picked.add(index);
      } else {
        p.picked.delete(index);
      }
    } else {
      return;
    }
    const list = $$(".entries", box)[0];
    const scroll = list?.scrollTop ?? 0;
    renderPreview();
    const again = $$(".entries", box)[0];
    if (again) {
      again.scrollTop = scroll;
    }
  });
}

/* ============================== queue ============================== */

/** @typedef {HTMLElement & { sig?: string, status?: string }} Card */
/** @type {Map<string, Card>} */
const cards = new Map();
/** @type {Record<string, string>} */
const MODE_ICON = { audio: "music", images: "image", video: "film", auto: "link", transcript: "text" };
/** What each colour code stands for, said aloud. @type {Record<string, string>} */
const CODE_NAME = { "c-video": "Video", "c-audio": "Audio", "c-images": "Pictures", "c-text": "Transcript" };
/** Where each kind of file goes, as its colour code. @type {Record<string, string>} */
const CODE = {
  video: "c-video", compatible: "c-video", trim: "c-video", exact: "c-video", gif: "c-video",
  audio: "c-audio", mp3: "c-audio", images: "c-images", image: "c-images", detext: "c-images", transcript: "c-text",
};
/** Samples of each running entry's speed, newest last, for its signal line. */
const signals = {
  /** @type {Map<string, number[]>} */
  speeds: new Map(),
  /** The fastest sample on screen, so every line is drawn to one scale. */
  top: 1,
};
/** How many samples a signal line holds: a sample a poll, about half a minute. */
const SIGNAL_SAMPLES = 60;

/** The colour code of where an entry's files go, or grey while that is not known yet. @param {{ mode: string, tool: string }} j */
function codeOf(j) {
  if (j.mode === "auto") {
    return { "gallery-dl": "c-images", "yt-dlp": "c-video" }[j.tool] ?? "c-wait";
  }
  return CODE[j.mode] ?? "c-wait";
}

/** Adds this poll's speeds, and forgets entries that are gone. @param {JobView[]} jobs */
function sampleSignals(jobs) {
  for (const j of jobs) {
    if (j.status === "running") {
      const line = signals.speeds.get(j.id) ?? [];
      line.push(j.speed ?? 0);
      signals.speeds.set(j.id, line.slice(-SIGNAL_SAMPLES));
    }
  }
  const live = new Set(jobs.map((j) => j.id));
  for (const id of signals.speeds.keys()) {
    if (!live.has(id)) {
      signals.speeds.delete(id);
    }
  }
  signals.top = Math.max(256 * 1024, ...[...signals.speeds.values()].flat());
}

/** The signal line's points: the speed history once it has run, flat otherwise. @param {JobView} j */
function signalPoints(j) {
  const line = j.status === "running" || j.status === "done" ? signals.speeds.get(j.id) ?? [] : [];
  if (line.length < 2) {
    return "0,24 120,24";
  }
  const step = 120 / (SIGNAL_SAMPLES - 1);
  const first = 120 - (line.length - 1) * step;
  return [`0,24`, `${first.toFixed(1)},24`, ...line.map((v, i) => `${(first + i * step).toFixed(1)},${(24 - (v / signals.top) * 22).toFixed(1)}`)].join(" ");
}
/** @type {Record<string, string>} */
const MODE_WORDS = { auto: "videos or pictures", video: "videos", audio: "audio only", images: "pictures" };
const ORDER = { running: 0, queued: 1, paused: 2, failed: 3, cancelled: 4, done: 5 };

/** @param {JobView} j */
function stateText(j) {
  if (j.status === "running") {
    return j.pct !== null && j.stage.startsWith("Downloading") ? PERCENT.format(j.pct / 100) : j.stage || "Starting";
  }
  if (j.status === "queued" && j.retry_at * 1000 > Date.now()) {
    return `Retrying in ${dur(j.retry_at - Date.now() / 1000)}`;
  }
  if (j.status === "done" && j.repeat) {
    return "Already downloaded";
  }
  if (j.status === "done" && j.errors) {
    return `Done, ${String(j.errors)} failed`;
  }
  return { queued: "Waiting", done: "Done", failed: "Failed", paused: "Paused", cancelled: "Cancelled" }[j.status];
}

/** @param {JobView} j */
function metaParts(j) {
  /** @type {string[]} */
  const parts = [];
  if (j.status === "done" && j.repeat) {
    return [j.repeat > 1 ? `You downloaded it ${ago(j.repeat)}` : "The archive says it was downloaded before", j.site].filter(Boolean);
  }
  const where = [j.sub ? "subscription" : "", j.site, j.status === "running" ? "" : j.tool].filter(Boolean);
  if (j.status !== "running") {
    parts.push(...where);
  }
  if (j.status === "running") {
    if (j.count && j.count > 1 && j.index) {
      parts.push(`${String(j.index)} of ${String(j.count)}`);
    }
    if (j.pct !== null && j.stage.startsWith("Downloading") && j.size) {
      parts.push(bytes(j.size));
    }
    if (j.speed) {
      parts.push(`${bytes(j.speed)}/s`);
    }
    if (j.eta !== null && j.pct !== null && j.pct < 100) {
      parts.push(`${dur(j.eta)} left`);
    }
  } else if (j.status === "done") {
    parts.push(j.stage || `${String(j.nfiles)} file${j.nfiles === 1 ? "" : "s"}`);
    parts.push(ago(j.finished));
  } else if (j.status === "paused" && j.stage) {
    parts.push(j.stage);
  }
  if (j.status === "running") {
    parts.push(...where);
  }
  return parts;
}

/**
 * @param {string} act
 * @param {string} name
 * @param {string} title
 * @param {string} [cls]
 */
function actButton(act, name, title, cls = "") {
  return `<button type="button" class="icon-btn ${cls}" data-act="${act}" title="${esc(title)}" aria-label="${esc(title)}">${icon(name)}</button>`;
}

/** @param {JobView} j */
function actions(j) {
  const log = actButton("log", "log", "Show the log");
  switch (j.status) {
    case "running":
      return actButton("pause", "pause", "Pause (carries on from where it stopped)") + actButton("cancel", "x", "Cancel", "warn") + log;
    case "queued":
      return actButton("top", "top", "Move to the top") + actButton("up", "up", "Move up") + actButton("pause", "pause", "Hold") + actButton("remove", "x", "Remove", "warn");
    case "paused":
      return actButton("retry", "play", "Resume", "accent") + actButton("remove", "x", "Remove", "warn") + log;
    case "failed":
      return `${j.repairable ? '<button type="button" class="btn small" data-act="repair">Repair</button>' : ""}<button type="button" class="btn small" data-act="retry">Try Again</button>${
        actButton("copy", "copy", "Copy link")}${log}${actButton("remove", "x", "Remove", "warn")}`;
    case "cancelled":
      return actButton("retry", "refresh", "Start again") + actButton("remove", "x", "Remove", "warn");
    case "done":
      return (j.repeat ? '<button type="button" class="btn small" data-act="again" title="Fetch it anyway, past the archive">Download Again</button>' : "") +
        (j.errors ? '<button type="button" class="btn small" data-act="retry">Try Again</button>' : "") +
        (j.first ? actButton("open", "external", "Open") + actButton("reveal", "folder", "Show in folder") : "") +
        (j.video && S.afterimage ? actButton("afterimage", "aperture", "Open in Afterimage") : "") +
        (j.job_kind === "download" ? actButton("page", "link", "Open the page") : "") + log + actButton("remove", "x", "Remove from the list");
  }
}

/** @param {JobView} j */
function card(j) {
  let el = cards.get(j.id);
  if (!el) {
    el = /** @type {Card} */ (document.createElement("article"));
    el.className = "job";
    el.dataset["id"] = j.id;
    el.innerHTML = `<input type="checkbox" class="pick" aria-label="Select"><span class="no"></span><i class="code" role="img"></i><svg class="signal" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"><polyline points="0,24 120,24"/></svg>
      <div class="body"><div class="title"></div><div class="item"></div><div class="meta"></div><div class="why" hidden></div></div><div class="acts"></div><pre class="log" hidden></pre><div class="bar"><i></i></div>`;
    cards.set(j.id, el);
  }
  const sig = JSON.stringify(j) + String(S.picked.has(j.id)) + (signals.speeds.has(j.id) ? String(signals.top) : "");
  if (el.sig === sig) {
    return el;
  }
  el.sig = sig;
  const partial = j.status === "done" && j.errors > 0;
  el.className = `job ${j.status}${partial ? " partial" : ""}${S.picked.has(j.id) ? " picked" : ""}`;
  const pick = /** @type {HTMLInputElement} */ ($(".pick", el));
  pick.checked = S.picked.has(j.id);
  pick.setAttribute("aria-label", `Select ${j.title || j.url}`);
  $(".no", el).textContent = j.serial ? String(j.serial).padStart(4, "0") : "";
  const code = $(".code", el);
  code.className = `code ${codeOf(j)}`;
  code.title = CODE_NAME[codeOf(j)] ?? "Not known yet";
  code.setAttribute("aria-label", code.title);
  $(".signal polyline", el).setAttribute("points", signalPoints(j));
  const title = $(".title", el);
  title.textContent = j.title || j.url;
  title.title = j.url;
  const item = j.item && j.item !== j.title ? j.item : "";
  const itemEl = $(".item", el);
  itemEl.textContent = item;
  itemEl.hidden = !item;
  $(".meta", el).innerHTML = [`<span class="state">${esc(stateText(j))}</span>`, ...metaParts(j).map((m) => `<span>${esc(m)}</span>`)].join("");
  const why = $(".why", el);
  why.hidden = j.status !== "failed" && !partial;
  if (j.status === "failed") {
    why.innerHTML = `<b>${esc(j.advice)}</b>${j.said ? `<span class="said">The site said: ${esc(j.said)}</span>` : ""}`;
  } else if (partial) {
    const what = j.errors === 1 ? "One of them" : `${String(j.errors)} of them`;
    why.innerHTML = `<b>${what} did not download, and what did arrive is kept.</b><span class="said">${j.said ? `The site said: ${esc(j.said)}` : "The log says which."}</span>`;
  }
  const key = j.status + String(j.repairable) + String(partial);
  if (el.status !== key) {
    el.status = key;
    $(".acts", el).innerHTML = actions(j);
  }
  const bar = $(".bar", el);
  bar.classList.toggle("busy", j.status === "running" && j.pct === null);
  $("i", bar).style.transform = `scaleX(${String((j.pct ?? 0) / 100)})`;
  return el;
}

/** @param {JobView[]} jobs */
function sortJobs(jobs) {
  return jobs
    .map((j, i) => ({ j, i }))
    .sort((a, b) => {
      const rank = ORDER[a.j.status] - ORDER[b.j.status];
      if (rank) {
        return rank;
      }
      return a.j.status === "done" || a.j.status === "failed" ? (b.j.finished ?? 0) - (a.j.finished ?? 0) : a.i - b.i;
    })
    .map((pair) => pair.j);
}

function renderJobs() {
  const state = S.state;
  if (!state) {
    return;
  }
  const list = $("#queue");
  const live = new Set(state.jobs.map((j) => j.id));
  /** @type {Element | null} */
  let previous = null;
  for (const j of sortJobs(state.jobs)) {
    const el = card(j);
    /** @type {Element | null} */
    const wanted = previous ? previous.nextElementSibling : list.firstElementChild;
    if (wanted !== el) {
      if (previous) {
        previous.after(el);
      } else {
        list.prepend(el);
      }
    }
    previous = el;
  }
  for (const [id, el] of cards) {
    if (!live.has(id)) {
      el.remove();
      cards.delete(id);
      S.logs.delete(id);
      S.picked.delete(id);
    }
  }
  renderQueueHead(state);
  void refreshLogs();
}

/** @param {State} state */
function renderQueueHead(state) {
  const count = (/** @type {Status} */ s) => state.jobs.filter((j) => j.status === s).length;
  const running = state.jobs.filter((j) => j.status === "running");
  const active = running.length;
  const waiting = count("queued");
  $("#empty").hidden = state.jobs.length > 0;
  $("#qhead").hidden = state.jobs.length === 0;
  $("#next-no").textContent = String(state.next).padStart(4, "0");
  const partial = state.jobs.filter((j) => j.status === "done" && j.errors > 0).length;
  $("#qsummary").textContent = [
    active ? `${String(active)} downloading` : "", waiting ? `${String(waiting)} waiting` : "",
    count("paused") ? `${String(count("paused"))} paused` : "", count("failed") ? `${String(count("failed"))} failed` : "",
    count("done") ? `${String(count("done"))} done` : "", partial ? `${String(partial)} with failures` : "",
  ].filter(Boolean).join(", ");
  // Each control shows only when there is something for it to act on.
  $("#hold-btn").hidden = !active && !waiting && state.held !== Infinity;
  $("[data-all=retry]").hidden = !count("failed") && !partial;
  $("[data-all=clear]").hidden = !count("done") && !count("failed") && !count("cancelled");
  $("[data-all=cancel]").hidden = !active && !waiting && !count("paused");
  const speed = running.reduce((total, j) => total + (j.speed ?? 0), 0);
  const known = running.filter((j) => j.pct !== null);
  const overall = known.length ? known.reduce((total, j) => total + (j.pct ?? 0), 0) / known.length : null;
  $("#qtotal").textContent = active ? [speed ? `${bytes(speed)}/s` : "", overall !== null ? `${String(Math.round(overall))}% overall` : ""].filter(Boolean).join(", ") : "";
  const nav = $("#nav-count");
  nav.textContent = active + waiting ? String(active + waiting) : "";
  nav.classList.toggle("live", active > 0);
  const held = state.held === Infinity || state.held > Date.now() / 1000;
  $("#hold-btn").innerHTML = held && state.held === Infinity ? `${icon("play")}<span class="label">Resume queue</span>` : `${icon("pause")}<span class="label">Pause queue</span>`;
  $("#reason").hidden = !state.reason || !waiting;
  $("#reason-text").textContent = state.reason;
  const afterAll = /** @type {HTMLSelectElement} */ ($("#after-all"));
  if (document.activeElement !== afterAll) {
    afterAll.value = state.after_all;
  }
  const bulk = $("#bulk");
  bulk.hidden = S.picked.size === 0;
  $("#bulk-count").textContent = `${String(S.picked.size)} selected`;
  void api().set_title(active ? `Keepsake (${String(active)} downloading${overall !== null ? `, ${PERCENT.format(overall / 100)}` : ""})` : "Keepsake");
}

async function refreshLogs() {
  for (const id of S.logs) {
    const el = cards.get(id);
    if (!el) {
      continue;
    }
    const pre = $("pre.log", el);
    const lines = await api().log(id);
    const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 8;
    const text = lines.join("\n") || "(nothing yet)";
    if (pre.textContent !== text) {
      pre.textContent = text;
      if (stick) {
        pre.scrollTop = pre.scrollHeight;
      }
    }
  }
}

/**
 * @param {string} act
 * @param {JobView} j
 */
async function jobAction(act, j) {
  switch (act) {
    case "log": {
      const el = cards.get(j.id);
      if (!el) {
        return;
      }
      const pre = $("pre.log", el);
      pre.hidden = !pre.hidden;
      if (pre.hidden) {
        S.logs.delete(j.id);
      } else {
        S.logs.add(j.id);
        await refreshLogs();
        pre.scrollTop = pre.scrollHeight;
      }
      return;
    }
    case "open":
      await api().open_path(j.first);
      return;
    case "reveal":
      await revealFile(j.first);
      return;
    case "afterimage":
      await api().afterimage(j.video);
      toast("Opening in Afterimage");
      return;
    case "copy":
      await copyText(j.url);
      return;
    case "again":
      await api().add(j.url, j.mode, { ignore_archive: true });
      toast("Downloading it again");
      return;
    case "page":
      await api().open_url(j.url);
      return;
    case "repair":
      await api().repair(j.id);
      toast("Trying the fixes");
      return;
    default:
      await api().act(act, [j.id]);
  }
}

function bindQueue() {
  const list = $("#queue");
  on(list, "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const jobEl = target?.closest(".job");
    if (!(jobEl instanceof HTMLElement)) {
      return;
    }
    const id = jobEl.dataset["id"] ?? "";
    if (target instanceof HTMLInputElement && target.classList.contains("pick")) {
      if (target.checked) {
        S.picked.add(id);
      } else {
        S.picked.delete(id);
      }
      renderJobs();
      return;
    }
    const button = target?.closest("[data-act]");
    const j = S.state?.jobs.find((x) => x.id === id);
    if (button instanceof HTMLElement && j) {
      await jobAction(button.dataset["act"] ?? "", j);
      await poll();
    }
  });
  for (const button of $$("[data-all]")) {
    on(button, "click", async () => {
      if (button.dataset["all"] === "cancel" && !armed(button, "Cancel every download?")) {
        return;
      }
      await api().everything(button.dataset["all"] ?? "");
      await poll();
    });
  }
  for (const button of $$("[data-bulk]")) {
    on(button, "click", async () => {
      await api().act(button.dataset["bulk"] ?? "", [...S.picked]);
      if (button.dataset["bulk"] === "remove") {
        S.picked.clear();
      }
      await poll();
    });
  }
  on($("#bulk-none"), "click", () => {
    S.picked.clear();
    renderJobs();
  });
  on($("#hold-btn"), "click", async () => {
    const held = S.state?.held === Infinity;
    await api().everything(held ? "release" : "hold");
    await poll();
  });
  on($("#reason-go"), "click", async () => {
    await api().schedule("");
    await api().everything("release");
    await poll();
  });
  on($("#schedule-btn"), "click", async () => {
    const when = await ask("Start the queue at (e.g. 02:00)", "02:00");
    if (when) {
      await api().schedule(when);
      toast(`New downloads start at ${when}`);
      await poll();
    }
  });
  const afterAll = /** @type {HTMLSelectElement} */ ($("#after-all"));
  on(afterAll, "change", async () => {
    const chosen = await api().after_all(afterAll.value);
    toast(chosen === "shutdown" ? "The PC shuts down a minute after the last download" : "Noted");
  });
}

/* ============================== tools and updates ============================== */

/** @param {State} state */
function renderTools(state) {
  const t = state.tools;
  const known = Object.keys(t).length > 0;
  /** @param {string} label @param {string | null | undefined} value */
  const row = (label, value) => `<dt>${esc(label)}</dt><dd class="${value ? "" : "missing"}" title="${esc(value ?? "not found")}">${esc(value ?? (known ? "missing" : "…"))}</dd>`;
  const html = row("yt-dlp", t["yt-dlp"]) + row("gallery-dl", t["gallery-dl"]) + row("ffmpeg", t.ffmpeg) + row("JS runtime", t.js) +
    row("encoder", t.encoder === undefined ? undefined : t.encoder.replace("h264_", "").replace("lib", ""));
  const box = $("#tools");
  if (box.innerHTML !== html) {
    box.innerHTML = html;
  }
  const button = /** @type {HTMLButtonElement} */ ($("#update"));
  button.disabled = state.updating;
  button.innerHTML = state.updating ? '<span class="spinner"></span>Updating…' : `${icon("refresh")}Update tools`;
  $("#note").textContent = state.note;
  const app = state.app;
  $("#app-ready").hidden = app.state !== "ready";
  $("#app-restart-2").hidden = app.state !== "ready";
  $("#app-ready-text").textContent = `Keepsake ${app.latest ?? ""} is ready`;
  $("#app-version").textContent = app.version;
  /** @type {Record<string, string>} */
  const said = {
    dev: "This copy is a development checkout, so it does not update itself.",
    idle: "Checks every six hours.", checking: "Looking for a new version…",
    current: `Up to date. Checked ${ago(app.checked)}.`, available: `${app.latest ?? ""} is available.`,
    downloading: "Installing the new version…", ready: `${app.latest ?? ""} is installed: restart to use it.`,
    failed: `Could not update: ${app.error}`,
  };
  $("#app-state").textContent = said[app.state] ?? app.state;
  const notes = $("#app-notes");
  notes.hidden = !app.notes.length || app.state === "current";
  notes.innerHTML = app.notes.map((n) => `<li>${esc(n)}</li>`).join("");
  const rollback = /** @type {HTMLSelectElement} */ ($("#rollback"));
  const seen = (t.seen ?? []).slice().reverse();
  const options = seen.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("") || '<option value="">None yet</option>';
  if (rollback.innerHTML !== options) {
    rollback.innerHTML = options;
  }
  /** @type {HTMLButtonElement} */ ($("#rollback-go")).disabled = !seen.length;
  $("#nav-subs").textContent = state.subs.length ? String(state.subs.length) : "";
}

/** Builds the jump list over the settings page and keeps the section in view marked. */
function bindSettingsIndex() {
  const page = $("#settings");
  // A section the platform has no use for is not displayed, and gets no place in the index either.
  const sheets = $$(".sheet", page).filter((sheet) => getComputedStyle(sheet).display !== "none");
  const nav = $("#settings-index");
  const topOf = (/** @type {HTMLElement} */ sheet) => sheet.getBoundingClientRect().top - page.getBoundingClientRect().top + page.scrollTop;
  nav.innerHTML = sheets.map((sheet, i) => `<button type="button" data-sheet="${String(i)}">${esc($("h2", sheet).textContent)}</button>`).join("");
  let chosen = -1;
  for (const type of /** @type {const} */ (["wheel", "keydown", "pointerdown", "touchstart"])) {
    on(page, type, () => {
      chosen = -1;
    });
  }
  on(nav, "click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("[data-sheet]") : null;
    if (button instanceof HTMLElement) {
      chosen = Number(button.dataset["sheet"]);
      const sheet = sheets[chosen];
      page.scrollTo({ top: (sheet ? topOf(sheet) : 0) - nav.offsetHeight - 8, behavior: "smooth" });
    }
  });
  const markCurrent = () => {
    const line = page.scrollTop + nav.offsetHeight + 24;
    let at = 0;
    sheets.forEach((sheet, i) => {
      if (topOf(sheet) <= line) {
        at = i;
      }
    });
    // The last sections are too short to reach the line, so the bottom of the page is the last one.
    if (page.scrollTop + page.clientHeight >= page.scrollHeight - 2) {
      at = chosen < 0 ? sheets.length - 1 : chosen;
    }
    $$("[data-sheet]", nav).forEach((button, i) => {
      button.setAttribute("aria-current", String(i === at));
      // On a phone the index scrolls sideways, so the marked section is kept in sight.
      if (i === at) {
        nav.scrollLeft = button.offsetLeft - (nav.clientWidth - button.offsetWidth) / 2;
      }
    });
  };
  on(page, "scroll", markCurrent);
  markCurrent();
}

/* ============================== poll ============================== */

/** @type {number | undefined} */
let pollTimer;

// A window brought back from the tray catches up at once rather than at the next slow poll.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    void poll();
  }
});

async function poll() {
  window.clearTimeout(pollTimer);
  try {
    const was = new Map(S.state?.jobs.map((j) => [j.id, j.status]));
    const before = new Set(S.state?.jobs.filter((j) => j.status === "done").map((j) => j.id));
    S.state = await api().state();
    const news = was.size ? S.state.jobs.filter((j) => (j.status === "done" || j.status === "failed") && was.get(j.id) !== j.status) : [];
    if (news.length) {
      $("#announce").textContent = news.map((j) => `${j.title || j.url}: ${stateText(j)}`).join(". ");
    }
    sampleSignals(S.state.jobs);
    const ended = S.state.jobs.filter((j) => j.status === "done" && !before.has(j.id));
    if (ended.some((j) => j.job_kind === "setup")) {
      void refreshTextRemoval();
    } else if (S.tab === "settings") {
      paintTextRemoval();
    }
    const landed = ended.some((j) => j.nfiles);
    if (landed && before.size + S.state.jobs.length && S.tab === "library") {
      void loadLibrary();
    }
    renderJobs();
    renderTools(S.state);
    paintSaving();
    if (S.tab === "subscriptions") {
      renderSubs();
    }
  } catch (problem) {
    console.error(problem);
  }
  const busy = S.state?.jobs.some((j) => j.status === "running" || j.status === "queued") ?? false;
  pollTimer = window.setTimeout(() => {
    void poll();
  }, document.hidden ? 5000 : busy ? 400 : 1500);
}

/* ============================== clipboard ============================== */

async function watchClipboard() {
  try {
    if (S.settings.clipboard !== "off") {
      const got = await api().clipboard();
      const jobs = S.state?.jobs ?? [];
      const fresh = got.filter((u) => !S.clipSeen.has(u) && !jobs.some((j) => j.url === u));
      for (const u of fresh) {
        S.clipSeen.add(u);
      }
      if (fresh.length && S.settings.clipboard === "auto") {
        await api().add(fresh.join("\n"), S.settings.mode, null);
        toast(fresh.length === 1 ? "Copied link added" : `${String(fresh.length)} copied links added`);
      } else if (fresh.length) {
        S.offer = fresh;
        renderOffer();
      }
    }
  } catch (problem) {
    console.error(problem);
  }
  window.setTimeout(() => {
    void watchClipboard();
  }, 1200);
}

function renderOffer() {
  $("#offer").hidden = !S.offer.length;
  $("#offer-url").textContent = S.offer.length > 1 ? `${String(S.offer.length)} copied links: ${S.offer.join("  ")}` : S.offer[0] ?? "";
}

function bindOffer() {
  on($("#offer-add"), "click", async () => {
    await api().add(S.offer.join("\n"), S.settings.mode, null);
    S.offer = [];
    renderOffer();
    toast("Added to the queue");
  });
  on($("#offer-preview"), "click", async () => {
    const first = S.offer[0];
    S.offer = [];
    renderOffer();
    if (first) {
      await preview(first);
    }
  });
  on($("#offer-x"), "click", () => {
    S.offer = [];
    renderOffer();
  });
}

/* ============================== search ============================== */

async function runSearch() {
  const query = /** @type {HTMLInputElement} */ ($("#search-q")).value.trim();
  if (!query) {
    return;
  }
  const source = /** @type {HTMLSelectElement} */ ($("#search-source")).value;
  const count = Number(/** @type {HTMLSelectElement} */ ($("#search-n")).value);
  $("#results").innerHTML = '<div class="loading"><span class="spinner"></span>Searching…</div>';
  $("#search-empty").hidden = true;
  const found = await api().search(query, source, count);
  S.results = found.results;
  S.resultPicks.clear();
  renderResults();
  if (found.error) {
    toast(found.error);
  }
}

function renderResults() {
  $("#search-empty").hidden = S.results.length > 0;
  $("#search-count").textContent = S.results.length ? `${String(S.results.length)} results` : "";
  $("#results").innerHTML = S.results.map((r, i) => {
    const thumb = safeSrc(r.thumb);
    const by = [r.channel, r.views !== null ? `${r.views.toLocaleString()} views` : ""].filter(Boolean).join(", ");
    return `<article class="result${S.resultPicks.has(i) ? " picked" : ""}" data-r="${String(i)}">
      <button type="button" class="pick" aria-pressed="${S.resultPicks.has(i) ? "true" : "false"}" aria-label="Pick ${esc(r.title)}"><span class="poster">${thumb ? `<img src="${esc(thumb)}" width="320" height="180" loading="lazy" referrerpolicy="no-referrer" alt="">` : ""}
        <span class="tick" aria-hidden="true">${S.resultPicks.has(i) ? icon("check") : ""}</span>
        ${r.duration ? `<span class="length">${esc(dur(r.duration))}</span>` : ""}</span></button>
        <span class="quick"><button type="button" class="icon-btn" data-r-act="preview" title="Preview" aria-label="Preview">${icon("eye")}</button><button type="button" class="icon-btn" data-r-act="get" title="Download" aria-label="Download">${icon("download")}</button></span>
      <h3>${esc(r.title)}</h3><div class="by">${esc(by)}</div></article>`;
  }).join("");
  $("#search-bulk").hidden = S.resultPicks.size === 0;
  $("#search-picked").textContent = `${String(S.resultPicks.size)} selected`;
}

function bindSearch() {
  on($("#search-form"), "submit", async (event) => {
    event.preventDefault();
    await runSearch();
  });
  on($("#results"), "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const holder = target?.closest("[data-r]");
    if (!(holder instanceof HTMLElement)) {
      return;
    }
    const index = Number(holder.dataset["r"]);
    const result = S.results[index];
    if (!result) {
      return;
    }
    const button = target?.closest("[data-r-act]");
    if (button instanceof HTMLElement) {
      if (button.dataset["rAct"] === "preview") {
        await preview(result.url);
      } else {
        await api().add(result.url, S.settings.mode, null);
        toast("Added to the queue");
      }
      return;
    }
    if (S.resultPicks.has(index)) {
      S.resultPicks.delete(index);
    } else {
      S.resultPicks.add(index);
    }
    renderResults();
  });
  on($("#search-get"), "click", async () => {
    const chosen = [...S.resultPicks].map((i) => S.results[i]?.url ?? "").filter(Boolean);
    const { added } = await api().add(chosen.join("\n"), S.settings.mode, null);
    toast(added ? `Added ${String(added)} to the queue` : "Already in the queue");
    S.resultPicks.clear();
    renderResults();
  });
  on($("#search-all"), "click", () => {
    S.results.forEach((_, i) => S.resultPicks.add(i));
    renderResults();
  });
  on($("#search-none"), "click", () => {
    S.resultPicks.clear();
    renderResults();
  });
}

/* ============================== subscriptions ============================== */

/** @param {{ url?: string; name?: string }} [start] */
function openSubForm(start = {}) {
  show("subscriptions");
  S.editingSub = "";
  const form = /** @type {HTMLFormElement} */ ($("#sub-form"));
  form.reset();
  const fields = form.elements;
  /** @type {HTMLInputElement} */ (fields.namedItem("url")).value = start.url ?? "";
  /** @type {HTMLInputElement} */ (fields.namedItem("name")).value = start.name ?? "";
  $("#sub-form-title").textContent = "Subscribe to a channel, playlist or profile";
  $("#sub-save").textContent = "Subscribe";
  form.hidden = false;
  /** @type {HTMLInputElement} */ (fields.namedItem("url")).focus();
}

/** @param {Subscription} sub */
function editSub(sub) {
  openSubForm({ url: sub.url, name: sub.name });
  S.editingSub = sub.id;
  const fields = /** @type {HTMLFormElement} */ ($("#sub-form")).elements;
  /** @type {HTMLSelectElement} */ (fields.namedItem("mode")).value = sub.mode;
  /** @type {HTMLSelectElement} */ (fields.namedItem("every")).value = String(sub.every);
  /** @type {HTMLSelectElement} */ (fields.namedItem("start")).value = sub.start;
  for (const [key, value] of Object.entries(sub.overrides)) {
    const field = fields.namedItem(key);
    if (field instanceof HTMLInputElement && field.type === "checkbox") {
      field.checked = key === "sponsorblock" ? value === "remove" : Boolean(value);
    } else if (field instanceof HTMLInputElement || field instanceof HTMLSelectElement) {
      field.value = String(value);
    }
  }
  $("#sub-form-title").textContent = `Change ${sub.name}`;
  $("#sub-save").textContent = "Save";
}

/** @returns {SubForm} */
function readSubForm() {
  const form = /** @type {HTMLFormElement} */ ($("#sub-form"));
  const data = new FormData(form);
  /** @param {string} name */
  const text = (name) => {
    const value = data.get(name);
    return typeof value === "string" ? value.trim() : "";
  };
  /** @param {string} name */
  const ticked = (name) => data.get(name) !== null;
  /** @type {Record<string, string | boolean>} */
  const overrides = {
    skip_shorts: ticked("skip_shorts"), skip_live: ticked("skip_live"), skip_members: ticked("skip_members"),
    sponsorblock: ticked("sponsorblock") ? "remove" : "off", min_duration: text("min_duration"),
    title_match: text("title_match"), title_skip: text("title_skip"),
  };
  if (text("quality")) {
    overrides["quality"] = text("quality");
  }
  return { url: text("url"), name: text("name"), mode: text("mode") || "auto", every: Number(text("every") || "6"), start: text("start") || "new", overrides };
}

function renderSubs() {
  const subs = S.state?.subs ?? [];
  $("#subs-empty").hidden = subs.length > 0;
  $("#subs-check").hidden = subs.length === 0;
  $("#subs-count").textContent = subs.length ? `${String(subs.length)} watched` : "";
  const running = new Set((S.state?.jobs ?? []).filter((j) => j.sub && (j.status === "running" || j.status === "queued")).map((j) => j.sub));
  /** @param {number} hours */
  const every = (hours) => (hours >= 168 ? "Weekly" : hours >= 24 ? "Daily" : hours === 1 ? "Hourly" : `Every ${String(hours)} hours`);
  const html = subs.map((s) => `<div class="sub-row${s.enabled ? "" : " off"}" data-sub="${esc(s.id)}">
    <div><div class="name">${esc(s.name)}</div><div class="link">${esc(s.url)}</div>
      <div class="plan">${esc([every(s.every), s.start === "new" ? "only what is new" : "everything there is", MODE_WORDS[s.mode] ?? s.mode].join(", "))}</div>
      ${s.last_error ? `<div class="why"><b>${esc(s.last_error)}</b></div>` : ""}</div>
    <div class="numbers"><span>checked</span><span>new</span><span>in all</span>
      <b>${running.has(s.id) ? "now" : esc(s.checked ? ago(s.checked) : "never")}</b><b>${String(s.last_new)}</b><b>${String(s.found)}</b></div>
    <div class="acts"><input type="checkbox" class="switch" data-sub-act="toggle" ${s.enabled ? "checked" : ""} aria-label="Watching">
      ${actButton("check", "refresh", "Check now").replace("data-act", "data-sub-act")}${actButton("edit", "sliders", "Change").replace("data-act", "data-sub-act")}
      <button type="button" class="icon-btn warn" data-sub-act="remove" title="Stop watching" aria-label="Stop watching">${icon("x")}</button></div></div>`).join("");
  const box = $("#subs");
  if (box.innerHTML !== html) {
    box.innerHTML = html;
  }
}

function bindSubs() {
  on($("#subs-new"), "click", () => {
    openSubForm();
  });
  on($("#sub-cancel"), "click", () => {
    $("#sub-form").hidden = true;
  });
  on($("#subs-check"), "click", async () => {
    await api().check_subscription("all");
    toast("Checking every subscription");
    await poll();
  });
  on($("#sub-form"), "submit", async (event) => {
    event.preventDefault();
    const form = readSubForm();
    if (S.editingSub) {
      await api().update_subscription(S.editingSub, { name: form.name, url: form.url, mode: form.mode, every: form.every, start: form.start, overrides: form.overrides });
      toast("Saved");
    } else if (await api().add_subscription(form)) {
      toast("Subscribed: looking now");
    } else {
      toast("That link does not look right");
      return;
    }
    $("#sub-form").hidden = true;
    await poll();
    renderSubs();
  });
  on($("#subs"), "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const row = target?.closest("[data-sub]");
    const button = target?.closest("[data-sub-act]");
    if (!(row instanceof HTMLElement) || !(button instanceof HTMLElement)) {
      return;
    }
    const id = row.dataset["sub"] ?? "";
    const sub = S.state?.subs.find((s) => s.id === id);
    switch (button.dataset["subAct"]) {
      case "toggle":
        await api().update_subscription(id, { enabled: button instanceof HTMLInputElement && button.checked });
        break;
      case "check":
        await api().check_subscription(id);
        toast("Checking");
        break;
      case "edit":
        if (sub) {
          editSub(sub);
        }
        return;
      case "remove":
        if (!armed(button, "Stop watching?")) {
          return;
        }
        await api().remove_subscription(id);
        toast("No longer watching. Files already fetched stay put.");
        break;
      default:
        return;
    }
    await poll();
    renderSubs();
  });
}

/* ============================== library ============================== */

/** @type {IntersectionObserver | null} */
let observer = null;

async function loadLibrary() {
  S.lib = await api().library();
  renderLibrary();
}

function libItems() {
  const query = /** @type {HTMLInputElement} */ ($("#libq")).value.trim().toLowerCase();
  const sort = /** @type {HTMLSelectElement} */ ($("#libsort")).value;
  const items = S.lib.filter((f) => (S.libFilter === "all" || f.kind === S.libFilter) &&
    (!query || f.name.toLowerCase().includes(query) || f.folder.toLowerCase().includes(query)));
  /** @type {Record<string, (a: LibFile, b: LibFile) => number>} */
  const orders = {
    new: (a, b) => b.time - a.time, old: (a, b) => a.time - b.time,
    name: (a, b) => a.name.localeCompare(b.name), size: (a, b) => b.size - a.size,
  };
  return items.sort(orders[sort] ?? orders["new"]);
}

function renderLibrary() {
  const items = libItems();
  const shown = items.slice(0, S.libShown);
  const total = S.lib.reduce((sum, f) => sum + f.size, 0);
  $("#libcount").textContent = S.lib.length ? `${String(S.lib.length)} file${S.lib.length === 1 ? "" : "s"}, ${bytes(total)}` : "";
  $("#grid").innerHTML = shown.map((f, i) => {
    const ext = f.name.split(".").pop() ?? "";
    const thumb = `<img data-path="${esc(f.path)}" data-uri="${esc(f.uri)}" width="176" height="176" decoding="async" alt=""`;
    const media = f.kind === "image"
      ? `${thumb}>`
      : f.kind === "video" ? `${thumb} data-video>${icon("film")}` : `<span class="wave" data-path="${esc(f.path)}"></span>${icon("music")}`;
    const where = f.folder === "." ? f.name : `${f.folder}\\${f.name}`;
    const picked = S.libPicked.has(f.path);
    return `<button type="button" class="tile${picked ? " picked" : ""}" data-i="${String(i)}" aria-label="${S.libPicking ? "Pick" : "View"} ${esc(f.name)}"${S.libPicking ? ` aria-pressed="${String(picked)}"` : ""}><span class="ph">${media}<span class="tick">${icon("check")}</span><span class="kind"><i class="code ${CODE[f.kind] ?? "c-wait"}"></i>${f.serial ? `${String(f.serial).padStart(4, "0")} ` : ""}${esc(ext)}</span></span>
      <span class="cap"><span class="n" title="${esc(where)}">${esc(f.name)}</span><span class="m">${esc(bytes(f.size))}, ${esc(ago(f.time))}</span></span></button>`;
  }).join("");
  $("#libempty").hidden = items.length > 0;
  paintPicks();
  $("#libmore").hidden = items.length <= S.libShown;
  observer?.disconnect();
  observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      const seen = entry.target;
      if (!entry.isIntersecting || !(seen instanceof HTMLElement)) {
        continue;
      }
      observer?.unobserve(seen);
      if (seen instanceof HTMLImageElement) {
        drawThumb(seen);
      } else {
        drawWave(seen);
      }
    }
  }, { root: $("#library"), rootMargin: "400px" });
  for (const waiting of $$("#grid img[data-path], #grid .wave[data-path]")) {
    observer.observe(waiting);
  }
}

/**
 * Puts a tile's small picture in, which Keepsake makes once and keeps, or the file itself when
 * it cannot. A video it cannot make one of shows its own frame instead, or turns out to be sound.
 * @param {HTMLImageElement} img
 */
function drawThumb(img) {
  const video = "video" in img.dataset;
  api().thumbnail(img.dataset["path"] ?? "").then((url) => {
    if (url || !video) {
      if (video) {
        img.addEventListener("load", () => img.nextElementSibling?.remove(), { once: true });
      }
      img.src = url || (img.dataset["uri"] ?? "");
      return;
    }
    const own = document.createElement("video");
    own.muted = true;
    own.preload = "metadata";
    own.dataset["path"] = img.dataset["path"] ?? "";
    own.addEventListener("loadeddata", () => {
      if (own.videoWidth) {
        own.nextElementSibling?.remove();
      } else {
        soundOnly(own);
      }
    }, { once: true });
    img.replaceWith(own);
    own.src = `${img.dataset["uri"] ?? ""}#t=1`;
  }).catch(report);
}

/** Puts a sound's waveform in its tile, behind the note until it is drawn. @param {HTMLElement} wave */
function drawWave(wave) {
  api().waveform(wave.dataset["path"] ?? "").then((url) => {
    if (url) {
      wave.style.setProperty("--wave", `url("${url}")`);
      wave.classList.add("drawn");
      wave.nextElementSibling?.remove();
    }
  }).catch(report);
}

/**
 * A video file with no picture is sound, as a WebM straight from YouTube often is: the
 * library files it as sound from then on.
 * @param {HTMLVideoElement} video
 */
function soundOnly(video) {
  const f = S.lib.find((each) => each.path === video.dataset["path"]);
  if (f) {
    f.kind = "audio";
  }
  const tile = video.closest(".tile");
  tile?.querySelector(".kind .code")?.setAttribute("class", `code ${CODE["audio"] ?? "c-wait"}`);
  const wave = document.createElement("span");
  wave.className = "wave";
  wave.dataset["path"] = video.dataset["path"] ?? "";
  video.nextElementSibling?.replaceWith(document.createRange().createContextualFragment(icon("music")));
  video.replaceWith(wave);
  drawWave(wave);
}

function bindLibrary() {
  on($("#libfilter"), "click", (event) => {
    const button = event.target instanceof Element ? event.target.closest("button") : null;
    if (!button) {
      return;
    }
    S.libFilter = button.dataset["v"] ?? "all";
    S.libShown = 240;
    for (const other of $$("#libfilter button")) {
      other.classList.toggle("on", other === button);
    }
    renderLibrary();
  });
  on($("#libq"), "input", () => {
    S.libShown = 240;
    renderLibrary();
  });
  on($("#libsort"), "change", () => {
    renderLibrary();
  });
  on($("#libmore"), "click", () => {
    S.libShown += 240;
    renderLibrary();
  });
  on($("#lib-refresh"), "click", loadLibrary);
  // The folder for what is being looked at; everything at once means the latest download.
  const libraryFolders = /** @type {Record<string, string>} */ ({ video: "videos", audio: "music", image: "pictures" });
  on($("#lib-folder"), "click", () => api().open_folder(libraryFolders[S.libFilter] ?? "downloads"));
  on($("#grid"), "click", (event) => {
    const tile = event.target instanceof Element ? event.target.closest(".tile") : null;
    if (!(tile instanceof HTMLElement)) {
      return;
    }
    const index = Number(tile.dataset["i"]);
    if (S.libPicking || event.ctrlKey || event.shiftKey) {
      pickFiles(index, event.shiftKey);
    } else {
      openBox(index);
    }
  });
  on($("#lib-select"), "click", () => {
    S.libPicking = !S.libPicking;
    if (!S.libPicking) {
      S.libPicked.clear();
    }
    renderLibrary();
  });
  on($("#lib-all"), "click", () => {
    for (const f of libItems().slice(0, S.libShown)) {
      S.libPicked.add(f.path);
    }
    renderLibrary();
  });
  on($("#lib-none"), "click", () => {
    S.libPicked.clear();
    S.libPicking = false;
    renderLibrary();
  });
  on($("#lib-delete"), "click", deletePicked);
}

/** Picks or unpicks one file, or with Shift everything from the last one picked. @param {number} index @param {boolean} range */
function pickFiles(index, range) {
  const items = libItems();
  const span = range && S.libLast >= 0 ? items.slice(Math.min(S.libLast, index), Math.max(S.libLast, index) + 1) : [items[index]];
  const target = items[index];
  const picking = target ? !S.libPicked.has(target.path) || range : false;
  for (const f of span) {
    if (f && picking) {
      S.libPicked.add(f.path);
    } else if (f) {
      S.libPicked.delete(f.path);
    }
  }
  S.libLast = index;
  S.libPicking = true;
  renderLibrary();
}

/** @type {number | undefined} */
let pickArmTimer;

function paintPicks() {
  const count = S.libPicked.size;
  $("#lib-bulk").hidden = !S.libPicking && !count;
  $("#lib-bulk-count").textContent = count ? `${String(count)} selected` : "None selected";
  /** @type {HTMLButtonElement} */ ($("#lib-none")).disabled = !count;
  $("#lib-select").setAttribute("aria-pressed", String(S.libPicking));
  $("#grid").classList.toggle("picking", S.libPicking);
  const pictures = pickedPictures().length;
  $("#lib-detext").hidden = !pictures || !textRemovalReady();
  $(".label", $("#lib-detext")).textContent = pictures > 1 ? `Remove Added Text from ${String(pictures)}` : "Remove Added Text";
  const button = $("#lib-delete");
  /** @type {HTMLButtonElement} */ (button).disabled = !count;
  if (!button.classList.contains("confirming")) {
    $(".label", button).textContent = count ? `Move ${String(count)} to Recycle Bin` : "Move to Recycle Bin";
  }
}

/** The first click asks, the second moves every picked file to the Recycle Bin. */
async function deletePicked() {
  const button = $("#lib-delete");
  const paths = [...S.libPicked];
  if (!paths.length) {
    return;
  }
  if (!button.classList.contains("confirming")) {
    button.classList.add("confirming");
    $(".label", button).textContent = `Move ${String(paths.length)} file${paths.length === 1 ? "" : "s"} to the Recycle Bin?`;
    window.clearTimeout(pickArmTimer);
    pickArmTimer = window.setTimeout(() => {
      button.classList.remove("confirming");
      paintPicks();
    }, 3500);
    return;
  }
  window.clearTimeout(pickArmTimer);
  button.classList.remove("confirming");
  let moved = 0;
  for (const path of paths) {
    if (await api().delete(path)) {
      moved += 1;
      S.lib = S.lib.filter((f) => f.path !== path);
      S.libPicked.delete(path);
    }
  }
  const stuck = paths.length - moved;
  S.libPicking = S.libPicked.size > 0;
  renderLibrary();
  toast(`Moved ${String(moved)} file${moved === 1 ? "" : "s"} to the Recycle Bin${stuck ? `. ${String(stuck)} could not be moved` : ""}`);
}

/* ============================== viewer ============================== */

const box = { i: -1, list: /** @type {LibFile[]} */ ([]), start: 0, end: 0 };

/** @param {number} index */
function openBox(index) {
  box.i = index;
  box.list = libItems();
  box.start = 0;
  box.end = 0;
  paintBox();
  $("#lightbox").hidden = false;
}

function closeBox() {
  leavePlayer();
  $("#lightbox").hidden = true;
  $("#lb-stage").innerHTML = "";
}

function current() {
  return box.list[box.i];
}

function paintBox() {
  const f = current();
  viewerClip?.reset();
  if (!f) {
    closeBox();
    return;
  }
  $("#lb-name").textContent = f.name;
  $("#lb-no").textContent = f.serial ? String(f.serial).padStart(4, "0") : "";
  $("#lb-code").className = `code ${CODE[f.kind] ?? "c-wait"}`;
  $("#lb-meta").textContent = [f.folder === "." ? "" : f.folder, bytes(f.size), ago(f.time), `${String(box.i + 1)} of ${String(box.list.length)}`].filter(Boolean).join(", ");
  const media = f.kind === "image" ? `<img src="${esc(f.uri)}" alt="">` : playerMarkup(f);
  $("#lb-stage").innerHTML = `${media}<button type="button" class="icon-btn nav prev" title="Previous (Left)" aria-label="Previous" ${box.i ? "" : "hidden"}>${icon("left")}</button><button type="button" class="icon-btn nav next" title="Next (Right)" aria-label="Next" ${box.i < box.list.length - 1 ? "" : "hidden"}>${icon("right")}</button>`;
  if (f.kind !== "image") {
    setupPlayer(f);
  }
  $("#lb-after").hidden = !(S.afterimage && f.kind === "video");
  $("#lb-playable").hidden = true;
  if (f.kind === "video") {
    api().plays_everywhere(f.path).then((fine) => {
      if (current() === f) {
        $("#lb-playable").hidden = fine;
      }
    }).catch(report);
  }
  paintTextRemoval();
  $("#lb-frame").hidden = f.kind !== "video";
  $("#lb-tools").hidden = f.kind === "image";
  // Sound cuts exactly either way, and a GIF needs pictures.
  $("#lb-clip .opener").hidden = f.kind !== "video";
  $("[data-convert='gif']").hidden = f.kind !== "video";
  const clip = $("#lb-clip [data-convert]");
  if (f.kind !== "video") {
    clip.dataset["convert"] = "trim";
  }
  for (const split of $$(".split")) {
    unfold(split, false);
  }
  showWave(f);
  if (f.kind === "image") {
    const picture = $("#lb-stage > img");
    on(picture, "load", () => {
      if (current() === f && picture instanceof HTMLImageElement) {
        $("#lb-meta").textContent += `, ${String(picture.naturalWidth)} x ${String(picture.naturalHeight)}`;
      }
    });
  }
  paintSpan();
  paintSaving();
  disarm();
}

/** Says on each save button what it will do now: which clip, which format. */
function paintSplits() {
  const sound = $("#lb-sound [data-convert]");
  // As wide as its longest wording from the start, so marking a clip moves nothing.
  if (!sound.style.minWidth && sound.offsetWidth) {
    sound.textContent = "Save clip as FLAC";
    sound.style.minWidth = `${String(sound.offsetWidth)}px`;
  }
  const format = $(`#lb-formats [data-pick="${sound.dataset["convert"] ?? "mp3"}"]`).textContent;
  sound.textContent = `Save ${marked() ? "clip " : ""}as ${format}`;
  const clip = $("#lb-clip [data-convert]");
  clip.textContent = clip.dataset["convert"] === "exact" ? "Save Exact Clip" : "Save Clip";
}

/** @param {HTMLElement} split @param {boolean} open */
function unfold(split, open) {
  split.classList.toggle("open", open);
  $(".opener", split).setAttribute("aria-expanded", String(open));
}

/**
 * A button with versions: its arrow unrolls them upward, and picking one does it at once and
 * stays on the button for next time.
 * @param {HTMLElement} split
 */
function bindSplit(split) {
  const opener = $(".opener", split);
  const primary = /** @type {HTMLButtonElement} */ ($("[data-convert]", split));
  const choices = () => $$("[data-pick]", split);
  on(opener, "click", () => {
    const opening = !split.classList.contains("open");
    unfold(split, opening);
    if (opening) {
      const list = choices();
      (list.find((item) => item.dataset["pick"] === primary.dataset["convert"]) ?? list.at(-1))?.focus();
    }
  });
  // While it is open, keys stay in the menu: Delete and Escape mean something else to the viewer.
  on(split, "keydown", (event) => {
    if (!split.classList.contains("open")) {
      return;
    }
    event.stopPropagation();
    const list = choices();
    const n = list.length;
    const at = list.indexOf(/** @type {HTMLElement} */ (document.activeElement));
    /** @type {Record<string, number>} */
    const moves = { ArrowUp: at < 0 ? n - 1 : at - 1, ArrowDown: at + 1, Home: 0, End: n - 1 };
    const to = moves[event.key];
    if (to !== undefined && n) {
      event.preventDefault();
      list[(to + n) % n]?.focus();
    } else if (event.key === "Escape") {
      unfold(split, false);
      opener.focus();
    }
  });
  on(split, "focusout", (event) => {
    if (!(event.relatedTarget instanceof Node && split.contains(event.relatedTarget))) {
      unfold(split, false);
    }
  });
  for (const item of choices()) {
    on(item, "click", () => {
      primary.dataset["convert"] = item.dataset["pick"] ?? "";
      paintSplits();
      unfold(split, false);
      opener.focus();
      return convertWith(primary);
    });
  }
}

function paintSpan() {
  const media = player();
  if (media) {
    media.loop = deck.loop && !marked();
  }
  paintControls();
  paintSplits();
  paintSaving();
}

/** The waveform of a sound in view, for the stage and under the clip bar. @param {LibFile} f */
function showWave(f) {
  const art = document.querySelector("#lb-stage .art");
  viewerClip?.wave("");
  if (f.kind !== "audio") {
    return;
  }
  api().waveform(f.path).then((url) => {
    if (current() !== f || !url) {
      return;
    }
    viewerClip?.wave(url);
    if (art instanceof HTMLElement) {
      art.innerHTML = `<button type="button" class="sound" aria-label="Play from here" style="--wave: url('${esc(url)}')"><span class="heard"></span></button>`;
      paintControls();
    }
  }).catch(report);
}

/** @param {number} step */
function stepBox(step) {
  const next = box.i + step;
  if (next >= 0 && next < box.list.length) {
    leavePlayer();
    box.i = next;
    box.start = 0;
    box.end = 0;
    paintBox();
  }
}

function player() {
  const found = $$("#lb-stage video, #lb-stage audio")[0];
  return found instanceof HTMLMediaElement ? found : null;
}

/* ============================== clip bar ============================== */

/** The shortest clip the bar keeps, in seconds. */
const SHORTEST = 0.5;
/** A short clip out of a long file still gets this many seconds either side of it, so it can be cut to a tenth. */
const CUT_ROOM = 5;
/** How long the bar takes to zoom to a new stretch, in milliseconds. */
const CUT_ZOOM = 250;

/** A time to a tenth of a second, as 1:02.5. @param {number} seconds */
function tenths(seconds) {
  const whole = Math.floor(seconds);
  return `${dur(whole)}.${String(Math.floor((seconds - whole) * 10 + 0.05) % 10)}`;
}

/** Reads 83.4, 1:23.4 or 1:01:23 as seconds, or null. @param {string} text */
function readClock(text) {
  const parts = text.trim().split(":");
  if (!text.trim() || parts.length > 3 || parts.some((p) => !/^\d+(\.\d+)?$/u.test(p))) {
    return null;
  }
  return parts.reduce((total, part) => total * 60 + Number(part), 0);
}

/** The bar, then the boxes and buttons that set its ends. */
function clipMarkup() {
  const grip = (/** @type {string} */ which, /** @type {string} */ label) =>
    `<div class="cut-grip" data-grip="${which}" role="slider" tabindex="0" aria-label="${label}" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0"></div>`;
  return `<div class="cut whole">
      <span class="cut-label">Clip</span>
      <div class="cut-body">
        <div class="cut-map" hidden><span>0:00</span><div class="cut-line"><div class="cut-shown"></div><div class="cut-map-kept"></div></div><span class="cut-total"></span></div>
        <div class="cut-track"><div class="cut-kept"></div><div class="cut-hint">Drag across the bar to choose the part to keep</div><div class="cut-head"></div>${grip("start", "Clip start")}${grip("end", "Clip end")}</div>
        <div class="cut-scale"><span class="cut-lo"></span><span class="cut-said"></span><span class="cut-hi"></span></div>
      </div>
    </div>
    <div class="cut-marks">
      <label class="cut-time">Start <input type="text" class="field cut-from" autocomplete="off" spellcheck="false" placeholder="0:00.0"></label>
      <button type="button" class="btn small cut-in" title="Start the clip where it is playing now (I)" aria-label="Mark the start where it is playing (I)">Mark</button>
      <label class="cut-time">End <input type="text" class="field cut-to" autocomplete="off" spellcheck="false" placeholder="0:00.0"></label>
      <button type="button" class="btn small cut-out" title="End the clip where it is playing now (O)" aria-label="Mark the end where it is playing (O)">Mark</button>
      <button type="button" class="btn small cut-clear off" title="Keep the whole file again">Clear Clip</button>
    </div>`;
}

/**
 * A clip bar over one media element, keeping its ends in `span`, both 0 for the whole file.
 * @param {HTMLElement} root holds clipMarkup()
 * @param {() => HTMLMediaElement | null} media what plays, or null while nothing can
 * @param {() => number} length seconds, 0 while unknown
 * @param {{ start: number, end: number }} span
 * @param {() => void} changed after either end moves
 */
function clipBar(root, media, length, span, changed) {
  const bar = $(".cut", root);
  const track = $(".cut-track", bar);
  const isMarked = () => span.end > span.start;
  const zoom = {
    /** The stretch the bar shows, easing from `from` to `to` since `since`. */
    from: /** @type {[number, number]} */ ([0, 0]),
    to: /** @type {[number, number]} */ ([0, 0]),
    since: 0,
    /** Held still while a handle is dragged, so the scale doesn't shift under it. */
    held: /** @type {[number, number] | null} */ (null),
    /** The time a dragged handle last asked the video to show. */
    seek: /** @type {number | null} */ (null),
    frame: 0,
  };

  /** Both ends at the file's ends is the whole file, which is no clip at all. @param {number} start @param {number} end */
  const keep = (start, end) => {
    const total = length();
    [span.start, span.end] = start <= 0 && end >= total - 0.05 ? [0, 0] : [start, end];
    changed();
  };

  /** Moves one end, keeping the clip at least SHORTEST long and inside the file. @param {"start" | "end"} which @param {number} at */
  const set = (which, at) => {
    const total = length();
    if (!total) {
      return;
    }
    let [start, end] = isMarked() ? [span.start, span.end] : [0, total];
    const time = Math.round(Math.min(total, Math.max(0, at)) * 10) / 10;
    if (which === "start") {
      start = Math.max(0, Math.min(time, end - SHORTEST));
    } else {
      end = Math.min(total, Math.max(time, start + SHORTEST));
    }
    keep(start, end);
  };

  /** Marks a whole stretch at once. @param {number} from @param {number} to */
  const sweepTo = (from, to) => {
    const total = length();
    if (!total) {
      return;
    }
    const start = Math.round(Math.max(0, from) * 10) / 10;
    keep(start, Math.round(Math.min(total, Math.max(to, start + SHORTEST)) * 10) / 10);
  };

  /** The clip with as much again either side, or the whole file. @param {number} total */
  const reach = (total) => {
    if (!isMarked()) {
      return /** @type {[number, number]} */ ([0, total]);
    }
    const room = Math.max(span.end - span.start, CUT_ROOM);
    return /** @type {[number, number]} */ ([Math.max(0, span.start - room), Math.min(total, span.end + room)]);
  };

  /** The stretch the bar shows now, easing toward where it should be. @param {number} total */
  const shown = (total) => {
    if (zoom.held) {
      return zoom.held;
    }
    const goal = reach(total);
    const now = performance.now();
    const share = Math.min(1, (now - zoom.since) / CUT_ZOOM);
    const eased = 1 - (1 - share) ** 3;
    const ease = (/** @type {number} */ from, /** @type {number} */ to) => from + (to - from) * eased;
    /** @type {[number, number]} */
    const now2 = [ease(zoom.from[0], zoom.to[0]), ease(zoom.from[1], zoom.to[1])];
    if (goal[0] !== zoom.to[0] || goal[1] !== zoom.to[1]) {
      const still = matchMedia("(prefers-reduced-motion: reduce)").matches || zoom.to[1] === 0;
      zoom.from = still ? goal : now2;
      zoom.to = goal;
      zoom.since = now;
      window.cancelAnimationFrame(zoom.frame);
      zoom.frame = window.requestAnimationFrame(paint);
      return zoom.from;
    }
    if (share < 1) {
      window.cancelAnimationFrame(zoom.frame);
      zoom.frame = window.requestAnimationFrame(paint);
    }
    return now2;
  };

  let wave = "";

  function paint() {
    const total = length();
    bar.classList.toggle("empty", !total);
    bar.classList.toggle("whole", !isMarked());
    bar.classList.toggle("waved", Boolean(wave));
    $(".cut-clear", root).classList.toggle("off", !isMarked());
    if (!total) {
      return;
    }
    const [lo, hi] = shown(total);
    const [start, end] = isMarked() ? [span.start, span.end] : [0, total];
    const at = (/** @type {number} */ time) => `${String(Math.min(100, Math.max(0, ((time - lo) / (hi - lo)) * 100)))}%`;
    const kept = $(".cut-kept", bar);
    kept.style.left = at(start);
    kept.style.right = `calc(100% - ${at(end)})`;
    for (const grip of $$(".cut-grip", bar)) {
      const value = grip.dataset["grip"] === "start" ? start : end;
      grip.style.left = at(value);
      grip.setAttribute("aria-valuemax", String(Math.round(total * 10) / 10));
      grip.setAttribute("aria-valuenow", String(value));
      grip.setAttribute("aria-valuetext", tenths(value));
    }
    const playing = media();
    const head = $(".cut-head", bar);
    head.hidden = !playing || playing.currentTime < lo || playing.currentTime > hi;
    head.style.left = at(playing?.currentTime ?? 0);
    const map = $(".cut-map", bar);
    map.hidden = hi - lo >= total - 0.05;
    const whole = (/** @type {number} */ time) => `${String((time / total) * 100)}%`;
    Object.assign($(".cut-shown", map).style, { left: whole(lo), width: whole(hi - lo) });
    Object.assign($(".cut-map-kept", map).style, { left: whole(start), width: whole(end - start) });
    $(".cut-total", bar).textContent = dur(total);
    $(".cut-lo", bar).textContent = tenths(lo);
    $(".cut-hi", bar).textContent = tenths(hi);
    $(".cut-said", bar).textContent = isMarked() ? `Keeps ${(end - start).toFixed(1)} seconds` : "";
    for (const [name, value] of /** @type {const} */ ([[".cut-from", start], [".cut-to", end]])) {
      const field = /** @type {HTMLInputElement} */ ($(name, root));
      if (document.activeElement !== field) {
        field.value = isMarked() ? tenths(value) : "";
      }
    }
    // Empty fields mean the whole file, so they show where it starts and ends.
    /** @type {HTMLInputElement} */ ($(".cut-to", root)).placeholder = tenths(total);
    const lane = $(".cut-track", bar);
    lane.style.setProperty("--wave", wave ? `url("${wave}")` : "none");
    lane.style.setProperty("--wave-size", `${String((total / (hi - lo)) * 100)}%`);
    lane.style.setProperty("--wave-x", `${String((lo / Math.max(total - (hi - lo), 0.001)) * 100)}%`);
  }

  /** Shows a frame while a handle is dragged, one seek at a time. @param {number} time */
  const showFrame = (time) => {
    const playing = media();
    if (!playing) {
      return;
    }
    const busy = zoom.seek !== null;
    zoom.seek = time;
    if (busy) {
      return;
    }
    const next = () => {
      if (zoom.seek === null) {
        return;
      }
      playing.currentTime = zoom.seek;
      zoom.seek = null;
    };
    next();
    playing.addEventListener("seeked", next, { once: true });
  };

  /** The end a handle or a box just moved, to show its frame. @param {"start" | "end"} which */
  const endOf = (which) => (which === "start" ? span.start : span.end || length());

  /** @param {PointerEvent} event */
  const timeAt = (event) => {
    const rect = track.getBoundingClientRect();
    const [lo, hi] = shown(length());
    const share = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    return lo + share * (hi - lo);
  };

  for (const grip of $$(".cut-grip", bar)) {
    const which = grip.dataset["grip"] === "start" ? "start" : "end";
    on(grip, "pointerdown", (event) => {
      event.stopPropagation();
      grip.setPointerCapture(event.pointerId);
      zoom.held = shown(length());
      media()?.pause();
      bar.classList.add("dragging");
    });
    on(grip, "pointermove", (event) => {
      if (grip.hasPointerCapture(event.pointerId)) {
        set(which, timeAt(event));
        showFrame(endOf(which));
      }
    });
    on(grip, "pointerup", (event) => {
      grip.releasePointerCapture(event.pointerId);
      zoom.held = null;
      bar.classList.remove("dragging");
      paint();
    });
    on(grip, "keydown", (event) => {
      const step = event.shiftKey ? 1 : 0.1;
      const value = Number(grip.getAttribute("aria-valuenow"));
      const to = new Map([["ArrowLeft", value - step], ["ArrowRight", value + step], ["Home", 0], ["End", length()]]).get(event.key);
      if (to !== undefined) {
        event.preventDefault();
        event.stopPropagation();
        media()?.pause();
        set(which, to);
        showFrame(endOf(which));
      }
    });
  }
  // Pressing on the bar and dragging across it marks that stretch. A press that
  // doesn't move just plays from there.
  /** @type {{ at: number, x: number, moved: boolean } | null} */
  let sweep = null;
  on(track, "pointerdown", (event) => {
    track.setPointerCapture(event.pointerId);
    sweep = { at: timeAt(event), x: event.clientX, moved: false };
    zoom.held = shown(length());
  });
  on(track, "pointermove", (event) => {
    if (!sweep || !track.hasPointerCapture(event.pointerId)) {
      return;
    }
    if (!sweep.moved && Math.abs(event.clientX - sweep.x) < 4) {
      return;
    }
    if (!sweep.moved) {
      sweep.moved = true;
      media()?.pause();
      bar.classList.add("dragging");
    }
    const now = timeAt(event);
    sweepTo(Math.min(sweep.at, now), Math.max(sweep.at, now));
    showFrame(now);
  });
  on(track, "pointerup", (event) => {
    track.releasePointerCapture(event.pointerId);
    const playing = media();
    if (sweep && !sweep.moved && playing) {
      playing.currentTime = sweep.at;
    }
    sweep = null;
    zoom.held = null;
    bar.classList.remove("dragging");
    paint();
  });
  /** @param {"in" | "out"} which */
  const markHere = (which) => {
    const playing = media();
    if (playing) {
      set(which === "in" ? "start" : "end", playing.currentTime);
    }
  };
  on($(".cut-in", root), "click", () => {
    markHere("in");
  });
  on($(".cut-out", root), "click", () => {
    markHere("out");
  });
  on($(".cut-clear", root), "click", () => {
    keep(0, 0);
  });
  for (const [name, which] of /** @type {const} */ ([[".cut-from", "start"], [".cut-to", "end"]])) {
    const field = /** @type {HTMLInputElement} */ ($(name, root));
    on(field, "change", () => {
      const time = readClock(field.value);
      if (time !== null) {
        set(which, time);
        media()?.pause();
        showFrame(endOf(which));
      }
      field.blur();
      paint();
    });
    on(field, "keydown", (event) => {
      event.stopPropagation();
      if (event.key === "Escape") {
        field.blur();
        paint();
      }
    });
  }
  return {
    paint,
    mark: markHere,
    /** Forgets the zoom, for a new file. */
    reset() {
      zoom.to = [0, 0];
    },
    /** Points at the bar when an action needs a part chosen first. */
    ask() {
      bar.classList.remove("ask");
      window.requestAnimationFrame(() => {
        bar.classList.add("ask");
      });
    },
    /** Draws a sound's waveform behind the track, or nothing. @param {string} url */
    wave(url) {
      wave = url;
      paint();
    },
  };
}

/** The viewer's clip bar, made once its footer exists. @type {ReturnType<typeof clipBar> | null} */
let viewerClip = null;

/** @param {"in" | "out"} which */
function mark(which) {
  viewerClip?.mark(which);
}

function fileLength() {
  const media = player();
  return media && Number.isFinite(media.duration) ? media.duration : 0;
}

/* ============================== player ============================== */

const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3];
const PLAYER_PREFS = "keepsake.player";
const deck = {
  loop: false,
  next: false,
  remaining: false,
  fps: 30,
  track: -1,
  /** @type {{ label: string, vtt: string }[]} */
  tracks: [],
  /** @type {string[]} */
  urls: [],
  /** @type {number | undefined} */
  idle: undefined,
};

/**
 * @typedef {object} PlayerPrefs
 * @property {number} volume
 * @property {boolean} muted
 * @property {number} speed
 * @property {boolean} next
 * @property {Record<string, number>} at where each file was left off
 */

/** @returns {PlayerPrefs} what the player remembers, if this window may keep anything */
function playerPrefs() {
  /** @type {PlayerPrefs} */
  const prefs = { volume: 1, muted: false, speed: 1, next: false, at: {} };
  try {
    // Saved under the app's old name until 1.14, and kept so the volume and speed carry over.
    const kept = localStorage.getItem(PLAYER_PREFS) ?? localStorage.getItem("siphon.player");
    const saved = /** @type {unknown} */ (JSON.parse(kept ?? "{}"));
    const s = saved && typeof saved === "object" ? /** @type {Record<string, unknown>} */ (saved) : {};
    const volume = s["volume"];
    const speed = s["speed"];
    if (typeof volume === "number") {
      prefs.volume = Math.min(1, Math.max(0, volume));
    }
    if (typeof speed === "number" && SPEEDS.includes(speed)) {
      prefs.speed = speed;
    }
    prefs.muted = s["muted"] === true;
    prefs.next = s["next"] === true;
    const at = s["at"];
    if (at && typeof at === "object") {
      for (const [path, time] of Object.entries(at)) {
        if (typeof time === "number") {
          prefs.at[path] = time;
        }
      }
    }
  } catch {
    // Storage can be missing or blocked; the defaults do.
  }
  return prefs;
}

/** @param {Partial<PlayerPrefs>} changes */
function savePlayerPrefs(changes) {
  try {
    localStorage.setItem(PLAYER_PREFS, JSON.stringify({ ...playerPrefs(), ...changes }));
  } catch {
    // Nowhere to keep it: the player still works, it just forgets.
  }
}

function marked() {
  return box.end > box.start;
}

/** @param {LibFile} f */
function playerMarkup(f) {
  const video = f.kind === "video";
  /** @param {string} act @param {string} name @param {string} label @param {string} [extra] */
  const pb = (act, name, label, extra = "") => `<button type="button" class="icon-btn" data-p="${act}" title="${esc(label)}" aria-label="${esc(label)}" ${extra}>${icon(name)}</button>`;
  const media = video
    ? `<video src="${esc(f.uri)}" autoplay playsinline></video>`
    : `<audio src="${esc(f.uri)}" autoplay></audio><div class="art">${icon("music")}<span>${esc(f.name)}</span></div>`;
  const pictureOnly = video ? pb("frame", "camera", "Save this frame as a picture (S)") + pb("pip", "pip", "Picture in picture (P)") + pb("full", "expand", "Full screen (F)") : "";
  return `<div class="player ${video ? "video" : "audio"}">${media}
    <div class="captions" aria-live="polite" hidden></div>
    <div class="big-state" aria-hidden="true"></div><div class="spinner" hidden></div>
    <div class="controls">
      <div class="timeline" role="slider" tabindex="0" aria-label="Position" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0">
        <div class="groove"><div class="buffered"></div><div class="marked" hidden></div><div class="played"></div><div class="knob"></div></div>
        <div class="hover-time" hidden></div>
      </div>
      <div class="deck-bar">
        ${pb("play", "pause", "Pause (Space)")}${pb("back", "back", "Back 10 seconds (J)")}${pb("forward", "forward", "Forward 10 seconds (L)")}
        ${pb("mute", "volume", "Mute (M)")}<input type="range" class="volume" min="0" max="1" step="0.05" aria-label="Volume">
        <button type="button" class="time" data-p="time" title="Show the time left">0:00 / 0:00</button>
        <span class="grow"></span>
        ${pb("subs", "captions", "Subtitles (C)", "hidden")}
        <button type="button" class="speed" data-p="speed" title="Speed (&lt; and &gt;)" aria-label="Speed">1×</button>
        ${pb("loop", "loop", "Loop (R): the marked part, or all of it", 'aria-pressed="false"')}
        ${pb("next", "skip", "Play the next one when this ends", 'aria-pressed="false"')}
        ${pictureOnly}
      </div>
    </div></div>`;
}

/** @param {LibFile} f */
function setupPlayer(f) {
  const media = player();
  const root = document.querySelector("#lb-stage .player");
  if (!media || !(root instanceof HTMLElement)) {
    return;
  }
  const prefs = playerPrefs();
  media.volume = prefs.volume;
  media.muted = prefs.muted;
  media.playbackRate = prefs.speed;
  media.loop = deck.loop && !marked();
  Object.assign(deck, { next: prefs.next, tracks: [], track: -1, fps: 30 });
  on(media, "loadedmetadata", () => {
    const left = prefs.at[f.path];
    if (left !== undefined && left < media.duration - 5) {
      media.currentTime = left;
      toast(`Carrying on from ${dur(left)}`);
    }
    paintControls();
  });
  for (const type of /** @type {const} */ (["timeupdate", "progress", "durationchange"])) {
    on(media, type, paintControls);
  }
  on(media, "play", () => {
    paintControls();
    flash("play");
    wake(root, media);
  });
  on(media, "pause", () => {
    paintControls();
    flash("pause");
    root.classList.remove("idle");
    rememberPosition();
  });
  on(media, "waiting", () => {
    spin(root, true);
  });
  for (const type of /** @type {const} */ (["playing", "canplay"])) {
    on(media, type, () => {
      spin(root, false);
    });
  }
  keepToSpan(media, box, () => deck.loop);
  on(media, "ended", () => {
    rememberPosition();
    if (deck.next) {
      playNext();
    }
  });
  on(media, "volumechange", () => {
    paintControls();
    savePlayerPrefs({ volume: media.volume, muted: media.muted });
  });
  on(media, "ratechange", () => {
    paintControls();
    savePlayerPrefs({ speed: media.playbackRate });
  });
  on(media, "error", () => {
    cantPlay(root);
  });
  on(root, "click", (event) => controlClick(event, root, media, f));
  on(root, "dblclick", async (event) => {
    if (event.target === media) {
      await toggleFullscreen(root);
    }
  });
  on(root, "pointermove", () => {
    wake(root, media);
  });
  on($(".volume", root), "input", (event) => {
    if (event.target instanceof HTMLInputElement) {
      media.volume = Number(event.target.value);
      media.muted = media.volume === 0;
    }
  });
  bindTimeline(root, media);
  if (media instanceof HTMLVideoElement) {
    measureFps(media);
    loadSubtitles(f, media).catch(report);
  }
  paintControls();
}

/**
 * @param {MouseEvent} event
 * @param {HTMLElement} root
 * @param {HTMLMediaElement} media
 * @param {LibFile} f
 */
async function controlClick(event, root, media, f) {
  const target = event.target instanceof Element ? event.target : null;
  if (target === media) {
    // A finger cannot hover, so the first tap on a playing video brings its controls back rather than pausing it.
    if (root.classList.contains("idle") && matchMedia("(hover: none)").matches) {
      wake(root, media);
    } else {
      await togglePlay(media);
    }
    return;
  }
  const wave = target?.closest(".art .sound");
  if (wave && Number.isFinite(media.duration)) {
    const edges = wave.getBoundingClientRect();
    media.currentTime = ((event.clientX - edges.left) / edges.width) * media.duration;
    if (media.paused) {
      await media.play();
    }
    return;
  }
  const button = target?.closest("[data-p]");
  if (!(button instanceof HTMLElement)) {
    return;
  }
  switch (button.dataset["p"]) {
    case "play":
      await togglePlay(media);
      break;
    case "back":
      seek(media, -10);
      break;
    case "forward":
      seek(media, 10);
      break;
    case "mute":
      toggleMute(media);
      break;
    case "time":
      deck.remaining = !deck.remaining;
      paintControls();
      break;
    case "subs":
      cycleSubtitles(media);
      break;
    case "speed":
      changeSpeed(media, 1, true);
      break;
    case "loop":
      toggleLoop(media);
      break;
    case "next":
      deck.next = !deck.next;
      savePlayerPrefs({ next: deck.next });
      paintControls();
      toast(deck.next ? "The next one plays when this ends" : "Stops at the end");
      break;
    case "frame":
      await saveFrame(f, media);
      break;
    case "pip":
      await togglePip(media);
      break;
    case "full":
      await toggleFullscreen(root);
      break;
    default:
      break;
  }
}

/** @param {HTMLMediaElement} media */
async function togglePlay(media) {
  if (media.paused) {
    await media.play();
  } else {
    media.pause();
  }
}

/** @param {HTMLMediaElement} media @param {number} by seconds */
function seek(media, by) {
  const end = Number.isFinite(media.duration) ? media.duration : media.currentTime + Math.max(0, by);
  media.currentTime = Math.min(Math.max(0, media.currentTime + by), end);
}

/** @param {HTMLMediaElement} media @param {number} frames */
function stepFrame(media, frames) {
  media.pause();
  seek(media, frames / deck.fps);
}

/** @param {HTMLMediaElement} media */
function toggleMute(media) {
  if (media.muted || media.volume === 0) {
    media.muted = false;
    media.volume = media.volume || 0.5;
  } else {
    media.muted = true;
  }
}

/** @param {HTMLMediaElement} media @param {number} by */
function nudgeVolume(media, by) {
  media.muted = false;
  media.volume = Math.min(1, Math.max(0, Math.round((media.volume + by) * 100) / 100));
  toast(`Volume ${PERCENT.format(media.volume)}`);
}

/** @param {HTMLMediaElement} media @param {number} step @param {boolean} wrap */
function changeSpeed(media, step, wrap) {
  const here = SPEEDS.findIndex((speed) => speed >= media.playbackRate);
  const at = (here < 0 ? SPEEDS.length - 1 : here) + step;
  const next = wrap ? (at + SPEEDS.length) % SPEEDS.length : Math.min(SPEEDS.length - 1, Math.max(0, at));
  media.playbackRate = SPEEDS[next] ?? 1;
  toast(`Speed ${String(media.playbackRate)}×`);
}

/** @param {HTMLMediaElement} media */
function toggleLoop(media) {
  deck.loop = !deck.loop;
  media.loop = deck.loop && !marked();
  paintControls();
  toast(deck.loop ? (marked() ? "Looping the marked part" : "Looping") : "Loop off");
}

/** @param {HTMLMediaElement} media */
function cycleSubtitles(media) {
  if (!deck.tracks.length) {
    toast("No subtitles for this one");
    return;
  }
  deck.track = deck.track + 1 >= deck.tracks.length ? -1 : deck.track + 1;
  // "hidden", not "showing": the browser keeps the cues current and the player draws them,
  // above its own controls, where the browser would put them underneath.
  [...media.textTracks].forEach((track, index) => {
    track.mode = index === deck.track ? "hidden" : "disabled";
  });
  paintCaptions();
  paintControls();
  toast(deck.track < 0 ? "Subtitles off" : `Subtitles: ${deck.tracks[deck.track]?.label ?? ""}`);
}

/** @param {LibFile} f @param {HTMLVideoElement} video */
async function loadSubtitles(f, video) {
  const tracks = await api().subtitles(f.path);
  if (player() !== video || !tracks.length) {
    return;
  }
  deck.tracks = tracks;
  for (const found of tracks) {
    const url = URL.createObjectURL(new Blob([found.vtt], { type: "text/vtt" }));
    deck.urls.push(url);
    const track = document.createElement("track");
    track.kind = "subtitles";
    track.label = found.label;
    track.src = url;
    track.addEventListener("cuechange", paintCaptions);
    video.append(track);
  }
  for (const track of video.textTracks) {
    track.mode = "disabled";
  }
  paintControls();
}

function paintCaptions() {
  const media = player();
  const shown = document.querySelector("#lb-stage .captions");
  if (!media || !(shown instanceof HTMLElement)) {
    return;
  }
  const cues = deck.track >= 0 ? media.textTracks[deck.track]?.activeCues : null;
  const text = [...(cues ?? [])]
    .map((cue) => (cue instanceof VTTCue ? cue.text.replace(/<[^>]*>/gu, "") : ""))
    .join("\n");
  shown.textContent = text;
  shown.hidden = !text;
}

/** Shows a file in Explorer, and says so when it has been moved or deleted. @param {string} path */
async function revealFile(path) {
  const how = await api().reveal(path);
  if (how === "folder") {
    toast("That file is not there any more, so this is the folder it was in");
  } else if (how === "gone") {
    toast("That file and its folder are not there any more");
  }
}

/** @param {LibFile} f @param {HTMLMediaElement} media */
async function saveFrame(f, media) {
  const made = await api().save_frame(f.path, media.currentTime);
  if (!made) {
    toast("Could not save that frame");
    return;
  }
  toast(`Saved ${made.split("\\").pop() ?? made}`, { label: "Show in Folder", run: () => revealFile(made) });
  await loadLibrary();
}

/** @param {HTMLMediaElement} media */
async function togglePip(media) {
  if (document.pictureInPictureElement) {
    await document.exitPictureInPicture();
  } else if (media instanceof HTMLVideoElement && document.pictureInPictureEnabled) {
    await media.requestPictureInPicture();
  }
}

/** @param {HTMLElement} root */
async function toggleFullscreen(root) {
  if (document.fullscreenElement) {
    await document.exitFullscreen();
  } else {
    await root.requestFullscreen();
  }
}

/** A video's controls fade while it plays and nobody moves the mouse; a song's stay. @param {HTMLElement} root @param {HTMLMediaElement} media */
function wake(root, media) {
  root.classList.remove("idle");
  window.clearTimeout(deck.idle);
  deck.idle = window.setTimeout(() => {
    if (!media.paused && media instanceof HTMLVideoElement) {
      root.classList.add("idle");
    }
  }, 2500);
}

/** @param {HTMLElement} root @param {boolean} busy */
function spin(root, busy) {
  $(".spinner", root).hidden = !busy;
}

/** @param {string} name */
function flash(name) {
  const badge = document.querySelector("#lb-stage .big-state");
  if (!(badge instanceof HTMLElement) || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  badge.innerHTML = icon(name);
  badge.animate([{ opacity: 1, transform: "scale(0.9)" }, { opacity: 0, transform: "scale(1.2)" }], { duration: 450, easing: "ease-out" });
}

/** The real frame rate, from the frames themselves, for stepping one at a time. @param {HTMLVideoElement} video */
function measureFps(video) {
  let last = -1;
  let shortest = Infinity;
  let seen = 0;
  /** @type {VideoFrameRequestCallback} */
  const tick = (_now, meta) => {
    if (last >= 0 && meta.mediaTime > last) {
      shortest = Math.min(shortest, meta.mediaTime - last);
    }
    last = meta.mediaTime;
    seen += 1;
    if (seen < 24 && player() === video) {
      video.requestVideoFrameCallback(tick);
    } else if (Number.isFinite(shortest)) {
      deck.fps = Math.min(240, Math.max(1, Math.round(1 / shortest)));
    }
  };
  video.requestVideoFrameCallback(tick);
}

/** @param {HTMLElement} root @param {HTMLMediaElement} media */
function bindTimeline(root, media) {
  const line = $(".timeline", root);
  const hover = $(".hover-time", root);
  /** @param {PointerEvent} event */
  const where = (event) => {
    const rect = line.getBoundingClientRect();
    const share = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    return { x: share * rect.width, time: share * (Number.isFinite(media.duration) ? media.duration : 0) };
  };
  on(line, "pointerdown", (event) => {
    line.setPointerCapture(event.pointerId);
    line.classList.add("dragging");
    media.currentTime = where(event).time;
  });
  on(line, "pointermove", (event) => {
    const at = where(event);
    hover.hidden = false;
    hover.textContent = dur(at.time);
    hover.style.left = `${String(at.x)}px`;
    if (line.classList.contains("dragging")) {
      media.currentTime = at.time;
    }
  });
  on(line, "pointerup", (event) => {
    line.releasePointerCapture(event.pointerId);
    line.classList.remove("dragging");
  });
  on(line, "pointerleave", () => {
    hover.hidden = true;
  });
}

/** @param {HTMLElement} root @param {string} act @param {string} name @param {string} label */
function paintButton(root, act, name, label) {
  const button = root.querySelector(`[data-p='${act}']`);
  if (!(button instanceof HTMLElement)) {
    return;
  }
  if (button.dataset["icon"] !== name) {
    button.innerHTML = icon(name);
    button.dataset["icon"] = name;
  }
  button.title = label;
  button.setAttribute("aria-label", label);
}

function paintControls() {
  const media = player();
  const root = document.querySelector("#lb-stage .player");
  if (!media || !(root instanceof HTMLElement)) {
    return;
  }
  const total = Number.isFinite(media.duration) ? media.duration : 0;
  const now = media.currentTime;
  const share = (/** @type {number} */ time) => `${String(total ? Math.min(100, (time / total) * 100) : 0)}%`;
  const loaded = media.buffered.length ? media.buffered.end(media.buffered.length - 1) : 0;
  $(".buffered", root).style.width = share(loaded);
  $(".played", root).style.width = share(now);
  $(".knob", root).style.left = share(now);
  const heard = root.querySelector(".art .sound");
  if (heard instanceof HTMLElement) {
    heard.style.setProperty("--heard", share(now));
  }
  const span = $(".marked", root);
  span.hidden = !marked();
  span.style.left = share(box.start);
  span.style.width = share(box.end - box.start);
  const line = $(".timeline", root);
  line.setAttribute("aria-valuemax", String(Math.round(total)));
  line.setAttribute("aria-valuenow", String(Math.round(now)));
  line.setAttribute("aria-valuetext", dur(now));
  $(".time", root).textContent = deck.remaining ? `-${dur(total - now)} / ${dur(total)}` : `${dur(now)} / ${dur(total)}`;
  paintButton(root, "play", media.paused ? "play" : "pause", media.paused ? "Play (Space)" : "Pause (Space)");
  const silent = media.muted || media.volume === 0;
  paintButton(root, "mute", silent ? "mute" : "volume", silent ? "Unmute (M)" : "Mute (M)");
  /** @type {HTMLInputElement} */ ($(".volume", root)).value = String(silent ? 0 : media.volume);
  $("[data-p='speed']", root).textContent = `${String(media.playbackRate)}×`;
  $("[data-p='loop']", root).setAttribute("aria-pressed", String(deck.loop));
  $("[data-p='next']", root).setAttribute("aria-pressed", String(deck.next));
  const subs = $("[data-p='subs']", root);
  subs.hidden = !deck.tracks.length;
  subs.setAttribute("aria-pressed", String(deck.track >= 0));
  const full = Boolean(document.fullscreenElement);
  paintButton(root, "full", full ? "shrink" : "expand", full ? "Leave full screen (F)" : "Full screen (F)");
  viewerClip?.paint();
}

/** @param {HTMLElement} root */
function cantPlay(root) {
  root.outerHTML = `<div class="cant"><p>This file does not play inside the window.</p><div class="actions">
    <button type="button" class="btn" data-cant="open">${icon("external")}Open it in your usual player</button>
    <button type="button" class="btn" data-cant="playable">${icon("film")}Make a copy that plays here</button></div></div>`;
}

/** Remember where a file was left, so it carries on from there next time. */
function rememberPosition() {
  const f = current();
  const media = player();
  if (!f || !media || !Number.isFinite(media.duration)) {
    return;
  }
  const time = media.currentTime;
  const kept = Object.entries(playerPrefs().at).filter(([path]) => path !== f.path);
  if (time > 30 && time < media.duration - 20) {
    kept.push([f.path, time]);
  }
  savePlayerPrefs({ at: Object.fromEntries(kept.slice(-200)) });
}

/** Let go of a file's player: its place remembered, full screen and its subtitles let go. */
function leavePlayer() {
  rememberPosition();
  window.clearTimeout(deck.idle);
  if (document.pictureInPictureElement) {
    document.exitPictureInPicture().catch(report);
  }
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(report);
  }
  for (const url of deck.urls) {
    URL.revokeObjectURL(url);
  }
  deck.urls = [];
}

function playNext() {
  const kind = current()?.kind;
  const next = box.list.findIndex((f, index) => index > box.i && f.kind === kind);
  if (next >= 0) {
    stepBox(next - box.i);
  }
}

/** @type {number | undefined} */
let armTimer;

function disarm() {
  const button = $("#lb-delete");
  button.classList.remove("confirming");
  $(".label", button).textContent = "Delete";
  window.clearTimeout(armTimer);
}

async function deleteCurrent() {
  const button = $("#lb-delete");
  if (!button.classList.contains("confirming")) {
    button.classList.add("confirming");
    $(".label", button).textContent = "Move to Recycle Bin?";
    armTimer = window.setTimeout(disarm, 3500);
    return;
  }
  const f = current();
  if (!f) {
    return;
  }
  $("#lb-stage").innerHTML = "";
  if (await api().delete(f.path)) {
    toast("Moved to the Recycle Bin");
    S.lib = S.lib.filter((x) => x.path !== f.path);
    box.list.splice(box.i, 1);
    box.i = Math.min(box.i, box.list.length - 1);
    renderLibrary();
    if (box.list.length) {
      paintBox();
    } else {
      closeBox();
    }
  } else {
    toast("Could not delete that");
    paintBox();
  }
}

function bindViewer() {
  on(document, "fullscreenchange", paintControls);
  on($("#lb-stage"), "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const cant = target?.closest("[data-cant]");
    const f = current();
    if (cant instanceof HTMLElement && f) {
      if (cant.dataset["cant"] === "open") {
        await api().open_path(f.path);
      } else if (cant instanceof HTMLButtonElement) {
        await startSaving(cant, f, "compatible");
      }
    } else if (target?.closest(".prev")) {
      stepBox(-1);
    } else if (target?.closest(".next")) {
      stepBox(1);
    } else if (target === event.currentTarget) {
      closeBox();
    }
  });
  on($("#lb-close"), "click", closeBox);
  on($("#lb-open"), "click", () => api().open_path(current()?.path ?? ""));
  on($("#lb-reveal"), "click", () => revealFile(current()?.path ?? ""));
  on($("#lb-copy"), "click", async () => {
    if (await api().copy_path(current()?.path ?? "")) {
      toast("Path copied");
    }
  });
  on($("#lb-after"), "click", async () => {
    await api().afterimage(current()?.path ?? "");
    toast("Opening in Afterimage");
  });
  on($("#lb-frame"), "click", async () => {
    const f = current();
    const media = player();
    if (f && media instanceof HTMLVideoElement) {
      await saveFrame(f, media);
    }
  });
  on($("#lb-delete"), "click", deleteCurrent);
  const tools = $("#lb-tools");
  tools.insertAdjacentHTML("afterbegin", clipMarkup());
  viewerClip = clipBar(tools, player, fileLength, box, paintSpan);
  for (const split of $$(".split", tools)) {
    bindSplit(split);
  }
  for (const button of $$("#lightbox [data-convert]")) {
    on(button, "click", () => convertWith(/** @type {HTMLButtonElement} */ (button)));
  }
}

/** Runs what a viewer button stands for on the file in view. @param {HTMLButtonElement} button */
async function convertWith(button) {
  const f = current();
  if (!f) {
    return;
  }
  const how = button.dataset["convert"] ?? "";
  if ((how === "trim" || how === "exact") && !marked()) {
    toast("Choose the part to keep first: drag across the clip bar, or use Mark Start and Mark End as it plays");
    viewerClip?.ask();
    return;
  }
  await startSaving(button, f, how, box.start, box.end);
}

/**
 * @typedef {object} Saving a conversion started in the viewer, shown on the button that started it
 * @property {string} id its job
 * @property {string} path the file it was made from
 * @property {HTMLButtonElement} button
 * @property {boolean} seen whether a poll has had its job yet
 * @property {Status} [result] how it ended
 * @property {number} [ended] when
 */

/** @type {Saving[]} */
let saving = [];
/** Buttons drawn as working last time, to put back to their labels. @type {Set<HTMLButtonElement>} */
const showing = new Set();
/** How long a button says Saved or Failed before it is itself again, in milliseconds. */
const SAID_FOR = 4000;

/**
 * Queues a conversion and turns its button into the progress of it, so it cannot be pressed twice.
 * @param {HTMLButtonElement} button @param {LibFile} f @param {string} how
 */
async function startSaving(button, f, how, start = 0, end = 0) {
  button.disabled = true;
  const id = await api().convert(f.path, how, start, end);
  button.disabled = false;
  if (!id) {
    toast("That cannot be converted");
    return;
  }
  saving.push({ id, path: f.path, button, seen: false });
  paintSaving();
  void poll();
}

/** Draws each conversion of the file in view on its button: how far along, then Saved or Failed. */
function paintSaving() {
  const now = Date.now();
  const jobs = new Map((S.state?.jobs ?? []).map((j) => [j.id, j]));
  for (const run of saving) {
    const job = jobs.get(run.id);
    run.seen ||= Boolean(job);
    if (run.ended === undefined && job && ["done", "failed", "cancelled"].includes(job.status)) {
      run.result = job.status;
      run.ended = now;
      const made = job.first;
      if (job.status === "done" && made) {
        toast(`Saved ${made.split("\\").pop() ?? made}`, { label: "Show in Folder", run: () => revealFile(made) });
      } else if (job.status === "done" && job.mode === "detext") {
        toast(job.stage || "Done");
      } else if (job.status === "failed") {
        toast(job.error || "That could not be saved");
      }
    }
  }
  // A job cleared from the queue before it ended has nothing left to show.
  saving = saving.filter((run) => (run.ended === undefined ? !run.seen || jobs.has(run.id) : now - run.ended < SAID_FOR));
  for (const button of showing) {
    delete button.dataset["state"];
    button.style.removeProperty("--pct");
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
  showing.clear();
  const path = current()?.path;
  for (const run of saving.filter((each) => each.path === path)) {
    const button = run.button;
    const job = jobs.get(run.id);
    const pct = job?.pct;
    const [working, worked] = job?.mode === "detext" ? ["Removing", job.nfiles ? "Saved" : "None found"] : ["Saving", "Saved"];
    showing.add(button);
    button.disabled = true;
    if (run.ended === undefined) {
      button.setAttribute("aria-busy", "true");
      button.dataset["state"] = pct === null || pct === undefined ? working : `${String(Math.floor(pct))}%`;
      button.style.setProperty("--pct", `${String(pct ?? 0)}%`);
    } else {
      button.dataset["state"] = run.result === "done" ? worked : "Failed";
      button.style.setProperty("--pct", run.result === "done" ? "100%" : "0%");
    }
  }
  // Nothing to cut until a part is marked; the clip bar says how.
  const clip = /** @type {HTMLButtonElement} */ ($("#lb-clip [data-convert]"));
  if (!showing.has(clip)) {
    clip.disabled = !marked();
    clip.title = marked() ? "" : "Mark a part on the clip bar first";
    /** @type {HTMLButtonElement} */ ($("#lb-clip .opener")).disabled = !marked();
  }
}

/* ============================== history ============================== */

async function loadHistory() {
  S.hist = await api().history();
  renderHistory();
}

function renderHistory() {
  const data = S.hist;
  if (!data) {
    return;
  }
  const query = /** @type {HTMLInputElement} */ ($("#histq")).value.trim().toLowerCase();
  const rows = data.entries.filter((h) => !query || h.title.toLowerCase().includes(query) || h.url.toLowerCase().includes(query));
  const s = data.stats;
  $("#histcount").textContent = data.entries.length
    ? [`${String(data.entries.length)} download${data.entries.length === 1 ? "" : "s"}`, bytes(s.bytes), s.failed ? `${String(s.failed)} failed` : ""].filter(Boolean).join(", ")
    : "";
  $("#histempty").hidden = rows.length > 0;
  $("#hist").hidden = rows.length === 0;
  // Where they came from, worth a strip only once there is more than one site.
  const strip = $("#stats");
  strip.hidden = s.sites.length < 2;
  strip.innerHTML = s.sites.slice(0, 5)
    .map(([site, n]) => `<div class="stat"><strong>${esc(String(n))}</strong><span>${esc(site)}</span></div>`).join("");
  /** @param {string} act @param {string} name @param {string} title */
  const hb = (act, name, title) => `<button type="button" class="icon-btn" data-h="${act}" title="${esc(title)}" aria-label="${esc(title)}">${icon(name)}</button>`;
  $("#hist").innerHTML = rows.slice(0, 600).map((h) => {
    const th = safeSrc(h.thumb);
    const files = [h.nfiles ? `${String(h.nfiles)} file${h.nfiles === 1 ? "" : "s"}` : "", h.errors ? `${String(h.errors)} failed` : ""].filter(Boolean).join(", ");
    return `<div class="hist-row ${esc(h.status)}" data-id="${esc(h.id)}" title="${esc(h.status === "failed" ? "Failed" : h.errors ? "Downloaded, some failed" : "Downloaded")}"><span class="no">${h.serial ? String(h.serial).padStart(4, "0") : ""}</span><i class="code ${codeOf(h)}" role="img" aria-label="${CODE_NAME[codeOf(h)] ?? "Not known yet"}"></i>
      <div class="thumb">${th ? `<img src="${esc(th)}" width="64" height="36" loading="lazy" referrerpolicy="no-referrer" alt="">` : icon(MODE_ICON[h.mode] ?? "link")}</div>
      <div class="body"><div class="t">${esc(h.title || h.url)}</div><div class="u">${esc([h.title && h.title !== h.url ? h.url : "", h.said].filter(Boolean).join(", "))}</div></div>
      <div class="w"><span>${esc(h.site)}</span><span>${esc([files, ago(h.finished), h.bytes ? bytes(h.bytes) : ""].filter(Boolean).join(", "))}</span></div>
      <div class="acts">${hb("again", "download", "Download again")}${h.files.length ? hb("reveal", "folder", "Show in folder") : '<span class="icon-btn gap"></span>'}${hb("copy", "copy", "Copy link")}${hb("forget", "x", "Forget")}</div></div>`;
  }).join("");
  for (const img of $$("#hist img")) {
    on(img, "error", () => {
      img.outerHTML = icon("link");
    });
  }
}

/**
 * Ask for a second click before something that cannot be undone.
 * @param {HTMLElement} button
 * @param {string} question
 * @returns {boolean} whether this click is the confirming one
 */
function armed(button, question) {
  if (button.classList.contains("confirming")) {
    button.classList.remove("confirming");
    return true;
  }
  const before = button.innerHTML;
  button.classList.add("confirming");
  button.textContent = question;
  window.setTimeout(() => {
    if (button.classList.contains("confirming")) {
      button.classList.remove("confirming");
      button.innerHTML = before;
    }
  }, 3500);
  return false;
}

/** @type {number | undefined} */
let clearTimer;

function bindHistory() {
  on($("#histq"), "input", renderHistory);
  on($("#hist"), "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest("[data-h]");
    const row = target?.closest(".hist-row");
    if (!(button instanceof HTMLElement) || !(row instanceof HTMLElement)) {
      return;
    }
    const h = S.hist?.entries.find((x) => x.id === row.dataset["id"]);
    if (!h) {
      return;
    }
    switch (button.dataset["h"]) {
      case "again":
        await api().add(h.url, h.mode, { ignore_archive: true });
        toast("Added to the queue");
        break;
      case "reveal":
        await revealFile(h.files[0] ?? "");
        break;
      case "copy":
        await copyText(h.url);
        break;
      case "forget":
        await api().forget(h.id);
        await loadHistory();
        break;
      default:
        break;
    }
  });
  on($("#hist-export"), "click", async () => {
    if (await api().export_history()) {
      toast("History saved");
    }
  });
  on($("#hist-clear"), "click", async () => {
    const button = $("#hist-clear");
    if (!button.classList.contains("confirming")) {
      button.classList.add("confirming");
      $(".label", button).textContent = "Clear all history?";
      clearTimer = window.setTimeout(() => {
        button.classList.remove("confirming");
        $(".label", button).textContent = "Clear";
      }, 3500);
      return;
    }
    window.clearTimeout(clearTimer);
    button.classList.remove("confirming");
    $(".label", button).textContent = "Clear";
    await api().clear_history();
    await loadHistory();
  });
}

/* ============================== settings extras ============================== */

const QUICK_SITES = ["youtube.com", "instagram.com", "x.com", "tiktok.com", "reddit.com", "facebook.com", "pixiv.net", "patreon.com", "twitch.tv", "bilibili.com"];

async function loadSettingsExtras() {
  const [accounts, archives] = await Promise.all([api().sign_ins(), api().archives()]);
  renderAccounts(accounts);
  renderArchives(archives);
}

/** @param {SignIn[]} accounts */
function renderAccounts(accounts) {
  $("#accounts-row").hidden = accounts.length === 0;
  $("#accounts").innerHTML = accounts.map((s) => `<div class="signin"><strong>${esc(s.site)}</strong><span class="grow">${String(s.cookies)} cookies, saved ${esc(ago(s.saved))}</span>
    <button type="button" class="btn small" data-signin="${esc(s.site)}">Sign in again</button><button type="button" class="btn ghost small" data-signout="${esc(s.site)}">Forget</button></div>`).join("");
}

/** @param {Archive[]} archives */
function renderArchives(archives) {
  $("#archives").innerHTML = archives.length
    ? archives.map((a) => `<div class="archive"><strong>${esc(a.label)}</strong><span class="grow">${esc(a.tool)}, remembers ${String(a.entries)}</span><button type="button" class="btn small" data-archive="${esc(a.file)}">Look inside</button></div>`).join("")
    : '<span class="dim">Nothing is being remembered yet. Turn on "Skip anything already downloaded", or subscribe to something.</span>';
}

/** @type {{ name: string; lines: string[] }} */
const archiveView = { name: "", lines: [] };

function renderArchiveEntries() {
  const query = /** @type {HTMLInputElement} */ ($("#archive-q")).value.trim().toLowerCase();
  const shown = archiveView.lines.filter((l) => !query || l.toLowerCase().includes(query)).slice(0, 2000);
  $("#archive-entries").innerHTML = shown.map((l) => `<label><input type="checkbox" data-line="${esc(l)}"><span>${esc(l)}</span></label>`).join("") || '<span class="dim">Nothing matches.</span>';
}

/** @param {string} site */
async function signIn(site) {
  if (await api().sign_in(site)) {
    toast(`Sign in to ${site}, then close that window`);
  } else {
    toast("That does not look like a site");
  }
}

function bindSettingsExtras() {
  $("#signin-quick").innerHTML = QUICK_SITES.map((s) => `<button type="button" class="chip plain" data-signin="${esc(s)}">${esc(s)}</button>`).join("");
  on($("#signin-go"), "click", async () => {
    const site = /** @type {HTMLInputElement} */ ($("#signin-site")).value.trim();
    if (site) {
      await signIn(site);
    }
  });
  on(document.body, "click", async (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const signin = target?.closest("[data-signin]");
    const signout = target?.closest("[data-signout]");
    const archive = target?.closest("[data-archive]");
    const del = target?.closest("[data-preset-del]");
    const open = target?.closest("[data-open]");
    if (signin instanceof HTMLElement) {
      await signIn(signin.dataset["signin"] ?? "");
    } else if (signout instanceof HTMLElement) {
      if (armed(signout, "Forget this sign-in?")) {
        renderAccounts(await api().forget_sign_in(signout.dataset["signout"] ?? ""));
      }
    } else if (archive instanceof HTMLElement) {
      archiveView.name = archive.dataset["archive"] ?? "";
      archiveView.lines = await api().archive_entries(archiveView.name);
      $("#archive-name").textContent = `${archiveView.name}: ${String(archiveView.lines.length)} remembered`;
      $("#archive-view").hidden = false;
      renderArchiveEntries();
    } else if (del instanceof HTMLElement) {
      S.presets = await api().delete_preset(del.dataset["presetDel"] ?? "");
      fillPresets();
    } else if (open instanceof HTMLElement) {
      await api().open_folder(open.dataset["open"] ?? "downloads");
    }
  });
  on($("#archive-q"), "input", renderArchiveEntries);
  on($("#archive-close"), "click", () => {
    $("#archive-view").hidden = true;
  });
  on($("#archive-forget"), "click", async () => {
    const lines = $$("#archive-entries input:checked").map((el) => el.dataset["line"] ?? "");
    const removed = await api().archive_forget(archiveView.name, lines);
    toast(`Forgot ${String(removed)}: they will download again`);
    archiveView.lines = await api().archive_entries(archiveView.name);
    renderArchiveEntries();
    renderArchives(await api().archives());
  });
  for (const button of $$("[data-pick]")) {
    on(button, "click", async () => {
      const key = button.dataset["pick"] ?? "";
      const folder = await api().pick_folder(isSetting(key) ? String(S.settings[key]) : "");
      if (folder && isSetting(key)) {
        save(key, folder);
      }
    });
  }
  for (const button of $$("[data-folders]")) {
    on(button, "click", async () => {
      S.settings = await api().use_folders(button.dataset["folders"] ?? "own");
      paintSettings();
      toast(button.dataset["folders"] === "downloads" ? "Everything now goes to Downloads" : "Back in Windows' own folders");
    });
  }
  on($("#pick-cookies"), "click", async () => {
    const file = await api().pick_file("cookies");
    if (file) {
      save("cookie_file", file);
    }
  });
  on($("#reset"), "click", async () => {
    const answer = await ask("Type RESET to put every setting back to its default");
    if (answer === "RESET") {
      S.settings = await api().reset_settings();
      paintSettings();
      toast("Settings reset");
    }
  });
  on($("#export-settings"), "click", async () => {
    if (await api().export_settings()) {
      toast("Saved");
    }
  });
  on($("#import-settings"), "click", async () => {
    const loaded = await api().import_settings();
    if (loaded) {
      S.settings = loaded;
      paintSettings();
      toast("Imported");
    }
  });
  on($("#update-now"), "click", async () => {
    await api().update_tools("");
    await poll();
  });
  on($("#update"), "click", async () => {
    await api().update_tools("");
    await poll();
  });
  on($("#rollback-go"), "click", async () => {
    const version = /** @type {HTMLSelectElement} */ ($("#rollback")).value;
    if (version) {
      await api().update_tools(version);
      toast(`Installing yt-dlp ${version}`);
      await poll();
    }
  });
  on($("#app-check"), "click", async () => {
    await api().check_app_update();
    await poll();
  });
  on($("#app-restart"), "click", () => api().restart());
  on($("#app-restart-2"), "click", () => api().restart());
  const video = "javascript:location.href='keepsake://add?url='+encodeURIComponent(location.href)";
  $("#bm-video").setAttribute("href", video);
  $("#bm-audio").setAttribute("href", video.replace("'+encodeURIComponent(location.href)", "'+encodeURIComponent(location.href)+'&mode=audio'"));
  for (const link of $$(".bookmarklet")) {
    on(link, "click", (event) => {
      event.preventDefault();
      toast("Drag it to the bookmarks bar");
    });
  }
}

/* ============================== wiring ============================== */

function bindComposer() {
  on($("#download-btn"), "click", download);
  on($("#preview-btn"), "click", () => preview());
  on($("#clip-btn"), "click", () => preview(undefined, true));
  on($("#toggle-options"), "click", () => {
    const drawer = $("#drawer");
    drawer.hidden = !drawer.hidden;
    $("#toggle-options").setAttribute("aria-expanded", String(!drawer.hidden));
    if (!drawer.hidden) {
      refreshTextRemoval().catch(report);
    }
  });
  on($("#import-links"), "click", async () => {
    const file = await api().pick_file("links");
    if (!file) {
      return;
    }
    const found = await api().read_links(file);
    if (found) {
      urls().value = `${urls().value.trim()}\n${found}`.trim();
      grow();
      toast(`${String(found.split("\n").length)} links from the file`);
    } else {
      toast("No links in that file");
    }
  });
  const preset = /** @type {HTMLSelectElement} */ ($("#preset"));
  on(preset, "change", async () => {
    const name = preset.value;
    preset.value = "";
    if (name === "+save") {
      const chosen = await ask("Name these options");
      if (chosen) {
        S.presets = await api().save_preset(chosen);
        fillPresets();
        toast(`Saved \u201c${chosen}\u201d`);
      }
    } else if (name) {
      S.settings = await api().apply_preset(name);
      paintSettings();
      toast(name);
    }
  });
  on(urls(), "input", grow);
  on(urls(), "keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      await (event.ctrlKey ? preview() : download());
    }
  });
}

/** @param {KeyboardEvent} event */
function viewerKeys(event) {
  if (event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  const media = player();
  const root = document.querySelector("#lb-stage .player");
  const f = current();
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  /** @type {Record<string, () => unknown>} */
  const keys = {
    Escape: closeBox,
    Delete: deleteCurrent,
    t: removeTextHere,
    PageUp: () => {
      stepBox(-1);
    },
    PageDown: () => {
      stepBox(1);
    },
    ArrowLeft: () => {
      stepBox(-1);
    },
    ArrowRight: () => {
      stepBox(1);
    },
  };
  if (media && f) {
    const total = Number.isFinite(media.duration) ? media.duration : 0;
    Object.assign(keys, {
      " ": () => togglePlay(media),
      k: () => togglePlay(media),
      ArrowLeft: () => {
        if (event.shiftKey) {
          stepBox(-1);
        } else {
          seek(media, -5);
        }
      },
      ArrowRight: () => {
        if (event.shiftKey) {
          stepBox(1);
        } else {
          seek(media, 5);
        }
      },
      j: () => {
        seek(media, -10);
      },
      l: () => {
        seek(media, 10);
      },
      ArrowUp: () => {
        nudgeVolume(media, 0.05);
      },
      ArrowDown: () => {
        nudgeVolume(media, -0.05);
      },
      m: () => {
        toggleMute(media);
      },
      ",": () => {
        stepFrame(media, -1);
      },
      ".": () => {
        stepFrame(media, 1);
      },
      "<": () => {
        changeSpeed(media, -1, false);
      },
      ">": () => {
        changeSpeed(media, 1, false);
      },
      Home: () => {
        media.currentTime = 0;
      },
      End: () => {
        media.currentTime = total;
      },
      c: () => {
        cycleSubtitles(media);
      },
      r: () => {
        toggleLoop(media);
      },
      i: () => {
        mark("in");
      },
      o: () => {
        mark("out");
      },
      f: () => (root instanceof HTMLElement ? toggleFullscreen(root) : undefined),
      p: () => togglePip(media),
      s: () => (media instanceof HTMLVideoElement ? saveFrame(f, media) : undefined),
    });
    if (/^\d$/u.test(key)) {
      keys[key] = () => {
        media.currentTime = (total * Number(key)) / 10;
      };
    }
  }
  const action = keys[key];
  if (action) {
    event.preventDefault();
    const result = action();
    if (result instanceof Promise) {
      result.catch(report);
    }
  }
}

/* ============================== window ============================== */

/** @type {number | undefined} */
let resizeTimer;

async function paintMaximize() {
  const max = await api().maximized();
  const button = $("#win-max");
  button.innerHTML = icon(max ? "restore" : "maximize");
  button.title = max ? "Restore" : "Maximize";
  button.ariaLabel = button.title;
}

function bindWindow() {
  on($("#win-min"), "click", () => api().window_command("minimize"));
  on($("#win-max"), "click", () => api().window_command("maximize"));
  on($("#win-close"), "click", () => api().window_command("close"));
  on(window, "blur", () => {
    document.body.classList.add("away");
  });
  on(window, "focus", () => {
    document.body.classList.remove("away");
  });
}

/** Snapping, double-clicking the bar and dragging off the top all maximize or restore without a click here. */
function watchMaximize() {
  on(window, "resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      paintMaximize().catch(report);
    }, 120);
  });
  return paintMaximize();
}

function bindKeys() {
  on(document, "keydown", (event) => {
    if (!$("#lightbox").hidden) {
      viewerKeys(event);
      return;
    }
    const active = document.activeElement;
    const typing = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement || active instanceof HTMLSelectElement;
    const key = event.key.toLowerCase();
    if (event.ctrlKey && /^[1-6]$/u.test(event.key)) {
      event.preventDefault();
      show(PAGES[Number(event.key) - 1] ?? "downloads");
    } else if (event.ctrlKey && key === "o") {
      event.preventDefault();
      void api().open_folder("downloads");
    } else if (event.ctrlKey && key === "f") {
      event.preventDefault();
      show("search");
    } else if (event.ctrlKey && key === "a" && !typing && S.tab === "downloads") {
      event.preventDefault();
      for (const j of S.state?.jobs ?? []) {
        S.picked.add(j.id);
      }
      renderJobs();
    } else if (event.ctrlKey && key === "v" && !typing) {
      show("downloads");
      urls().focus();
    } else if (event.key === "?" && !typing) {
      /** @type {HTMLDialogElement} */ ($("#help")).showModal();
    } else if (event.key === "Escape" && S.preview) {
      S.preview = null;
      renderPreview();
    }
  });
  // A link dragged in from a browser fills the box instead of navigating the window to it.
  on(document, "dragover", (event) => {
    event.preventDefault();
    $("#composer").classList.add("drop");
  });
  on(document, "dragleave", (event) => {
    if (!event.relatedTarget) {
      $("#composer").classList.remove("drop");
    }
  });
  on(document, "drop", async (event) => {
    event.preventDefault();
    $("#composer").classList.remove("drop");
    const data = event.dataTransfer;
    if (!data) {
      return;
    }
    const file = data.files[0];
    const text = file ? await file.text() : data.getData("text/uri-list") || data.getData("text/plain");
    if (!text) {
      return;
    }
    show("downloads");
    const lines = text.split(/\r?\n/u).filter((l) => l && !l.startsWith("#")).join("\n").trim();
    urls().value = `${urls().value.trim()}\n${lines}`.trim();
    grow();
    urls().focus();
  });
}

function bindNav() {
  for (const button of $$("nav button")) {
    on(button, "click", () => {
      show(button.dataset["tab"] ?? "downloads");
    });
  }
}

async function boot() {
  const b = await api().boot();
  S.settings = b.settings;
  S.defaults = b.defaults;
  S.browsers = b.browsers;
  S.afterimage = b.afterimage;
  S.presets = b.presets;
  S.builtin = b.builtin;
  S.version = b.version;
  fillCookies();
  fillPresets();
  bindSettings();
  paintSettings();
  renderAccounts(b.accounts);
  $("#data-show").replaceChildren(Object.assign(document.createElement("bdi"), { textContent: b.data }));
  $("#data-show").title = b.data;
  refreshTextRemoval().catch(report);
  watchMaximize().catch(report);
  await poll();
  void watchClipboard();
  urls().focus();
}

paintIcons();
bindNav();
bindComposer();
bindPreview();
bindOffer();
bindQueue();
bindSearch();
bindSubs();
bindLibrary();
bindViewer();
bindHistory();
bindSettingsExtras();
bindSettingsIndex();
bindDrawerFolds();
bindTextRemoval();
bindWindow();
bindKeys();
window.addEventListener("pywebviewready", () => {
  boot().catch(report);
});
