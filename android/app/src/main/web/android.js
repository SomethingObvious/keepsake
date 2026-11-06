"use strict";
// The Android app's stand-in for pywebview: the same window.pywebview.api the page
// calls on Windows, answered by Keepsake's Python through the app's bridge.
(() => {
  document.documentElement.dataset["platform"] = "android";
  // A pinch would zoom the whole window, tab bar and all, which an app's own window never does.
  document.querySelector('meta[name="viewport"]')?.setAttribute("content", "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no");
  const waiting = new Map();
  let next = 0;
  window.__keepsake = (id, reply) => {
    const call = waiting.get(id);
    waiting.delete(id);
    if (call && "error" in reply) {
      call.reject(new Error(reply.error));
    } else if (call) {
      call.resolve(reply.value);
    }
  };
  const api = new Proxy({}, {
    // "then" is left out, or awaiting the api object itself would call Python.
    get: (_, name) => (typeof name !== "string" || name === "then") ? undefined : (...args) => new Promise((resolve, reject) => {
      next += 1;
      waiting.set(next, { resolve, reject });
      KeepsakeAndroid.call(next, name, JSON.stringify(args));
    }),
  });
  window.pywebview = { api };
  // The page runs to the screen's sides and bottom; the app says what its contents keep clear of,
  // in pixels: the bars, the camera's cutout and the screen's rounded corners, and how much of
  // each side is a system bar itself, which no fill of the page's runs under.
  window.keepsakeSafe = (left, right, bottom, systemLeft, systemRight) => {
    const root = document.documentElement.style;
    root.setProperty("--safe-left", `${String(left)}px`);
    root.setProperty("--safe-right", `${String(right)}px`);
    root.setProperty("--safe-bottom", `${String(bottom)}px`);
    root.setProperty("--system-left", `${String(systemLeft)}px`);
    root.setProperty("--system-right", `${String(systemRight)}px`);
  };
  document.addEventListener("DOMContentLoaded", () => {
    window.dispatchEvent(new Event("pywebviewready"));
  });

  const escape = () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  // Android's Back closes the topmost thing, as Escape does on Windows, then goes to Downloads.
  window.keepsakeBack = () => {
    const dialog = document.querySelector("dialog[open]");
    const viewer = document.querySelector("#lightbox");
    if (dialog) {
      dialog.close();
    } else if (viewer && !viewer.hidden) {
      escape();
    } else if (S.preview) {
      escape();
    } else if (S.tab === "library" && S.libFilter !== "lists" && S.libPicking) {
      document.querySelector("#lib-none")?.click();
    } else if (S.tab === "library" && S.libFilter === "lists" && S.listOpen) {
      S.listOpen = "";
      renderLists();
    } else if (S.tab !== "downloads") {
      show("downloads");
    } else {
      return false;
    }
    return true;
  };
  // What the viewer is playing goes to the app's player in the notification bar and on the lock screen.
  document.addEventListener("keepsake:media", (event) => {
    KeepsakeAndroid.media(JSON.stringify(event.detail));
  });
  window.keepsakeShare = (text) => {
    show("downloads");
    const box = urls();
    box.value = text;
    grow();
    box.focus();
  };

  // Windows-only controls the page still carries. A phone cannot sleep or shut down when the
  // queue empties, has no shell for a command per file, and gets a new Keepsake as a new app.
  // The plugins folder is out of reach in app storage.
  document.addEventListener("DOMContentLoaded", () => {
    for (const option of document.querySelectorAll('#after-all option[value="sleep"], #after-all option[value="shutdown"]')) {
      option.remove();
    }
    for (const selector of ["#run-after", '[data-set="self_update"]', '[data-open="plugins"]']) {
      document.querySelector(selector)?.closest(".setting")?.setAttribute("data-desktop", "");
    }
    // What is left of "When done" on a phone is a second notification or quitting, so it goes too.
    for (const selector of ["#app-check", "#app-state", "#after-all"]) {
      document.querySelector(selector)?.setAttribute("data-desktop", "");
    }
    // The empty queue's own hint is about dropping links and a desktop hotkey, so the phone says how links arrive here.
    document.querySelector(".job.ghost .item[data-desktop]")?.insertAdjacentHTML(
      "afterend",
      '<div class="item">Or share one to Keepsake from YouTube or your browser.</div>',
    );
    // Recordings are saved as videos here, so their folder is not called Music.
    const music = [...document.querySelectorAll(".setting .l")].find((label) => label.textContent === "Music");
    if (music) {
      music.textContent = "Recordings";
    }
    const own = document.querySelector('[data-folders="own"]');
    if (own?.lastChild) {
      own.lastChild.textContent = "Phone's Folders";
    }
    // Hints that talk about Explorer, Windows' path limit or borrowing a desktop browser's cookies.
    const hints = {
      "File date": "The day your gallery and the Files app put it under",
      "Longest file name": "Characters. Android allows 255 for a name.",
      "Sign in to a site from Keepsake": "Opens the site in a screen of its own. Sign in as usual and press Done, and downloads from that site use the session.",
      Otherwise: "Automatic uses a Keepsake sign-in for that site when there is one.",
      "Preview playback": "How big a video a link's preview plays. A smaller one saves data and battery, or the sound alone. The clip bar works with any of them, even off.",
    };
    for (const row of document.querySelectorAll(".setting")) {
      const hint = hints[row.querySelector(".l")?.textContent?.trim() ?? ""];
      const words = row.querySelector(".h");
      if (hint && words) {
        words.textContent = hint;
      }
    }
  });
})();
