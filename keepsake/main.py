"""Starting Keepsake, or handing this launch's links to the copy already open."""

import sys
import threading
import uuid
from collections.abc import Mapping
from typing import cast

import webview

from keepsake import APP, former, paths, store, winapi
from keepsake.api import Api
from keepsake.app import App, create_window
from keepsake.links import links_from_args


def hand_over(links: list[tuple[str, str | None]], *, show: bool) -> None:
    """Give links to the copy of Keepsake that is already running, and bring it forward."""
    store.save(
        paths.DATA / "inbox" / f"{uuid.uuid4().hex}.json",
        {"links": [list(pair) for pair in links], "show": show},
    )
    raw = store.load(paths.DATA / "instance.json", {})
    hwnd = cast("Mapping[str, object]", raw).get("hwnd") if isinstance(raw, Mapping) else None
    if isinstance(hwnd, int) and show and not links:
        winapi.bring_forward(hwnd)


def main() -> None:
    """Open Keepsake, or hand this launch's links to the copy already open."""
    args = sys.argv[1:]
    if "--after" in args:  # a restart: let the old copy finish closing first
        at = args.index("--after")
        winapi.wait_for_exit(int(args[at + 1]))
        del args[at : at + 2]
    tray_only = "--tray" in args
    links = links_from_args(arg for arg in args if arg != "--tray")
    former.move_in()
    paths.DATA.mkdir(parents=True, exist_ok=True)
    if not winapi.claim_instance():
        hand_over(links, show=not tray_only)
        return
    winapi.set_app_id()
    app = App()
    for url, mode in links:
        app.queue.add(url, mode or app.options.mode, app.options)
    window = create_window(
        APP,
        (paths.UI / "index.html").as_uri(),
        js_api=Api(app),
        width=1360,
        height=860,
        min_size=(960, 640),
        background_color="#0a0a0a",
        text_select=True,
        hidden=tray_only,
    )
    if window is None:
        return
    app.window = window
    window.events.before_show += app.before_show
    window.events.shown += app.shown
    window.events.closing += app.closing
    threading.Thread(target=app.tray, daemon=True, name="tray").start()
    threading.Thread(target=app.inbox, daemon=True, name="inbox").start()
    winapi.listen_for_hotkey(app.add_copied, lambda: app.options.hotkey)
    # Not private: a site signed into from Keepsake stays signed in between runs.
    webview.start(app.start, private_mode=False, storage_path=str(paths.DATA / "webview"))
