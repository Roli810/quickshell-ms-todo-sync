#!/usr/bin/env python3
import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from filelock import FileLock
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

APP_URL = "https://to-do.live.com/tasks/"


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class Task:
    content: str
    done: bool


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def normalize_tasks(raw) -> List[Task]:
    if not isinstance(raw, list):
        return []

    out: List[Task] = []
    seen = set()

    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("content", "")).strip()
        done = bool(item.get("done", False))

        if not title:
            continue
        if title in seen:
            raise SyncError(f"Duplicate task title not supported: {title!r}")

        seen.add(title)
        out.append(Task(content=title, done=done))

    return out


def tasks_to_json(tasks: List[Task]) -> List[dict]:
    return [{"content": t.content, "done": t.done} for t in tasks]


def to_map(tasks: List[Task]) -> Dict[str, bool]:
    return {t.content: t.done for t in tasks}


def load_snapshot_state(state_path: Path) -> List[Task]:
    state = load_json(state_path, {"snapshot": []})

    if isinstance(state, list):
        return normalize_tasks(state)

    if isinstance(state, dict):
        return normalize_tasks(state.get("snapshot", []))

    return []


def save_snapshot_state(state_path: Path, tasks: List[Task]):
    save_json(state_path, {"snapshot": tasks_to_json(tasks)})


class TodoUI:
    def __init__(self, page, list_name: str, debug: bool = False):
        self.page = page
        self.list_name = list_name
        self.debug = debug

    def log(self, *parts):
        if self.debug:
            print(*parts, file=sys.stderr)

    def wait_signed_in(self, timeout: int = 60000):
        self.page.goto(APP_URL, wait_until="domcontentloaded", timeout=timeout)
        self.page.wait_for_timeout(2500)

        url = self.page.url.lower()
        if "login" in url or "signin" in url:
            raise SyncError(
                "Not signed in in the Playwright profile. Run once with --login-ui."
            )

        try:
            self.page.wait_for_load_state("load", timeout=8000)
        except Exception:
            pass

        self.page.wait_for_timeout(1200)

    def dump_debug_state(self):
        try:
            button_labels = self.page.get_by_role("button").evaluate_all(
                """els => els
                .map(e => (e.getAttribute('aria-label') || e.innerText || '').trim())
                .filter(Boolean)
                .slice(0, 100)"""
            )
            self.log("BUTTON ARIA/TEXT:", button_labels)
        except Exception as e:
            self.log("DEBUG button dump failed:", repr(e))

        try:
            checkbox_labels = self.page.get_by_role("checkbox").evaluate_all(
                """els => els
                .map(e => (e.getAttribute('aria-label') || '').trim())
                .filter(Boolean)
                .slice(0, 100)"""
            )
            self.log("CHECKBOX LABELS:", checkbox_labels)
        except Exception as e:
            self.log("DEBUG checkbox dump failed:", repr(e))

        try:
            textbox_labels = self.page.get_by_role("textbox").evaluate_all(
                """els => els
                .map(e => (
                    e.getAttribute('aria-label') ||
                    e.getAttribute('name') ||
                    e.getAttribute('placeholder') ||
                    ''
                ).trim())
                .filter(Boolean)
                .slice(0, 50)"""
            )
            self.log("TEXTBOX LABELS:", textbox_labels)
        except Exception as e:
            self.log("DEBUG textbox dump failed:", repr(e))

        try:
            visible_text = self.page.evaluate(
                """() => (document.body.innerText || '')
                .split(/\\n+/)
                .map(s => s.trim())
                .filter(Boolean)
                .slice(0, 120)"""
            )
            self.log("VISIBLE TEXT:", visible_text)
        except Exception as e:
            self.log("DEBUG visible-text dump failed:", repr(e))

    def close_details_pane(self):
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
        except Exception:
            pass

    def open_target_list(self):
        self.wait_signed_in()
        self.close_details_pane()

        toggle = self.page.get_by_role("button", name=re.compile(r"toggle sidebar", re.I))

        candidates = [
            self.page.get_by_text(self.list_name, exact=True),
            self.page.get_by_role("link", name=re.compile(rf"^{re.escape(self.list_name)}$", re.I)),
            self.page.get_by_role("button", name=re.compile(rf"^{re.escape(self.list_name)}$", re.I)),
        ]

        def try_click_candidates() -> bool:
            for loc in candidates:
                try:
                    if loc.count() > 0 and loc.first.is_visible(timeout=1500):
                        loc.first.click(timeout=3000)
                        self.page.wait_for_timeout(2200)
                        return True
                except Exception:
                    pass
            return False

        if not try_click_candidates():
            try:
                if toggle.count() > 0 and toggle.first.is_visible(timeout=1000):
                    toggle.first.click(timeout=2000)
                    self.page.wait_for_timeout(1000)
            except Exception:
                pass

            if not try_click_candidates():
                self.dump_debug_state()
                raise SyncError(f"Could not click target list: {self.list_name!r}")

        # Confirm list view actually loaded.
        textbox_ready = False
        task_ready = False

        try:
            self.page.get_by_role(
                "textbox",
                name=re.compile(r"^List .*Press shift\+tab$", re.I),
            ).first.wait_for(timeout=4000)
            textbox_ready = True
        except PlaywrightTimeoutError:
            pass

        try:
            self.page.get_by_role(
                "checkbox",
                name=re.compile(r"^Mark as completed\s+.+", re.I),
            ).first.wait_for(timeout=4000)
            task_ready = True
        except PlaywrightTimeoutError:
            pass

        if not textbox_ready and not task_ready:
            self.dump_debug_state()
            raise SyncError(
                f"Target list clicked, but list view did not finish loading: {self.list_name!r}"
            )

    def scrape_tasks(self) -> List[Task]:
        self.close_details_pane()
        checkboxes = self.page.get_by_role(
            "checkbox",
            name=re.compile(r"^Mark as completed\s+.+", re.I),
        )
        count = checkboxes.count()
        tasks: List[Task] = []
        seen: set = set()
        for i in range(count):
            cb = checkboxes.nth(i)
            try:
                aria = (cb.get_attribute("aria-label") or "").strip()
                m = re.match(r"^Mark as completed\s+(.+)$", aria, re.I)
                if not m:
                    continue
                title = m.group(1).strip()
                if not title or title in seen:
                    continue
                seen.add(title)
                aria_checked = cb.get_attribute("aria-checked")
                done = str(aria_checked).lower() in ("true", "mixed")
                tasks.append(Task(content=title, done=done))
            except Exception:
                continue
        tasks.sort(key=lambda t: t.content.lower())
        self.log("REMOTE SCRAPE:", tasks_to_json(tasks))
        return tasks

    def task_checkbox_exact(self, title: str):
        return self.page.get_by_role(
            "checkbox",
            name=re.compile(rf"^Mark as completed {re.escape(title)}$", re.I),
        )

    def task_button_exact(self, title: str):
        return self.page.get_by_role(
            "button",
            name=re.compile(rf"^task\s+{re.escape(title)}$", re.I),
        )

    def ensure_task_entry(self):
        # First try to focus the known add-task container.
        try:
            add_container = self.page.locator(".baseAdd.addTask").first
            if add_container.count() > 0 and add_container.is_visible(timeout=1000):
                add_container.click(timeout=2000)
                self.page.wait_for_timeout(400)
        except Exception:
            pass

        candidates = [
            self.page.get_by_role(
                "textbox",
                name=re.compile(rf"^List {re.escape(self.list_name)}.*Press shift\+tab$", re.I),
            ),
            self.page.get_by_role(
                "textbox",
                name=re.compile(r"^List .*Press shift\+tab$", re.I),
            ),
            self.page.locator(
                '.baseAdd.addTask textarea, '
                '.baseAdd.addTask input, '
                '.baseAdd.addTask [contenteditable="true"]'
            ),
            self.page.locator(
                '.taskCreation textarea, '
                '.taskCreation input, '
                '.taskCreation [contenteditable="true"]'
            ),
        ]

        for loc in candidates:
            try:
                if loc.count() > 0 and loc.first.is_visible(timeout=1200):
                    return loc.first
            except Exception:
                pass

        self.dump_debug_state()
        raise SyncError("Task entry textbox was not found. Refusing to use generic Add controls.")

    def add_task(self, title: str, done: bool = False):
        existing = self.task_checkbox_exact(title)
        if existing.count() > 0:
            if done:
                self.set_done(title, True)
            return

        box = self.ensure_task_entry()

        try:
            box.click(timeout=2000)
        except Exception:
            pass
        self.page.wait_for_timeout(150)

        typed = False

        for method in (
            lambda: box.fill(title, timeout=3000),
            lambda: (box.press("ControlOrMeta+a"), box.type(title, delay=10)),
            lambda: box.type(title, delay=10),
        ):
            try:
                method()
                typed = True
                break
            except Exception:
                pass

        if not typed:
            self.dump_debug_state()
            raise SyncError(f"Could not type into task entry for task: {title!r}")

        self.page.wait_for_timeout(150)
        box.press("Enter")
        self.page.wait_for_timeout(1200)

        created = self.task_checkbox_exact(title)
        if created.count() == 0:
            self.dump_debug_state()
            raise SyncError(f"Task creation failed; task did not appear: {title!r}")

        if done:
            self.set_done(title, True)

    def set_done(self, title: str, desired: bool):
        cb = self.task_checkbox_exact(title)
        if cb.count() == 0:
            self.dump_debug_state()
            raise SyncError(f"Could not find remote checkbox for task: {title!r}")

        aria = cb.first.get_attribute("aria-checked")
        current = str(aria).lower() in ("true", "mixed")

        if current != desired:
            cb.first.click(timeout=3000)
            self.page.wait_for_timeout(900)

    def delete_task(self, title: str):
        cb = self.task_checkbox_exact(title)
        if cb.count() == 0:
            return
        try:
            # Click the task row (its parent container) to select it
            row = cb.first.locator("xpath=ancestor::li[1]")
            if row.count() == 0:
                row = cb.first  # fallback: click the checkbox itself
            row.first.click(timeout=3000)
            self.page.wait_for_timeout(500)
            self.page.keyboard.press("Delete")
            self.page.wait_for_timeout(1200)
        except Exception:
            self.dump_debug_state()
            raise SyncError(f"Remote deletion failed for task: {title!r}")


def run_login_ui(config: dict):
    profile_dir = Path(config["profile_dir"]).expanduser()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded")

        print()
        print("A browser window is open.")
        print("1) Sign in to Microsoft To Do manually")
        print(f"2) Open the actual target list {config['list_name']!r}")
        print("3) Leave that list visible")
        input("Press Enter here when it is open and loaded... ")

        print("Profile preserved.")
        context.close()


def run_sync(config: dict, debug_override: bool = False):
    profile_dir = Path(config["profile_dir"]).expanduser()
    todo_path = Path(config["todo_json_path"]).expanduser()
    state_path = Path(config["state_path"]).expanduser()
    lock_path = Path(config["lock_path"]).expanduser()

    list_name = config.get("list_name")
    if not list_name:
        raise SyncError("Config is missing 'list_name'.")

    debug = bool(config.get("debug", False) or debug_override)
    sync_deletions = bool(config.get("sync_deletions", True))
    headless = bool(config.get("headless", True))

    with FileLock(str(lock_path)):
        local_tasks = normalize_tasks(load_json(todo_path, []))
        prev_tasks = load_snapshot_state(state_path)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless if not debug_override else False,
                viewport={"width": 1440, "height": 1000},
            )
            page = context.pages[0] if context.pages else context.new_page()

            ui = TodoUI(page=page, list_name=list_name, debug=debug)
            ui.open_target_list()
            remote_before = ui.scrape_tasks()

            prev_map = to_map(prev_tasks)
            local_map = to_map(local_tasks)
            remote_map = to_map(remote_before)

            prev_titles = set(prev_map)
            local_titles = set(local_map)
            remote_titles = set(remote_map)

            local_created = local_titles - prev_titles
            local_deleted = prev_titles - local_titles
            remote_created = remote_titles - prev_titles

            local_toggled = {
                t for t in (local_titles & prev_titles)
                if local_map[t] != prev_map[t]
            }

            if debug:
                print(
                    f"LOCAL DELTA added={sorted(local_created)} "
                    f"removed={sorted(local_deleted)} "
                    f"done={sorted(local_toggled)}",
                    file=sys.stderr,
                )

            # Apply local deletions first, unless remote independently created same title.
            if sync_deletions:
                for title in sorted(local_deleted - remote_created):
                    if title in remote_titles:
                        ui.delete_task(title)
                        ui.open_target_list()

            # Apply local creations unless remote already created same title.
            for title in sorted(local_created - remote_created):
                ui.add_task(title, local_map[title])
                ui.open_target_list()

            # Apply local done/undone toggles.
            for title in sorted(local_toggled):
                current_remote = to_map(ui.scrape_tasks())
                if title in current_remote:
                    ui.set_done(title, local_map[title])
                    ui.open_target_list()

            remote_after = ui.scrape_tasks()
            context.close()

        save_json(todo_path, tasks_to_json(remote_after))
        save_snapshot_state(state_path, remote_after)

        if debug:
            print(f"Synced {len(remote_after)} tasks.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="~/.config/ms-todo-ui-sync/config.json")
    parser.add_argument("--login-ui", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    config = load_json(config_path, None)
    if not isinstance(config, dict):
        print(f"Config missing or invalid: {config_path}", file=sys.stderr)
        return 1

    try:
        if args.login_ui:
            run_login_ui(config)
        else:
            run_sync(config, debug_override=args.debug)
        return 0

    except PlaywrightTimeoutError as e:
        print(f"Timeout talking to Microsoft To Do: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
