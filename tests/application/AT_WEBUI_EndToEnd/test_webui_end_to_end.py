# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""WebUI end-to-end verification for file-mcp-server.

License: Apache 2.0
Ownership: Cloud-Dog, Viewdeck Engineering Limited
Description: Browser-driven WebUI flows for login, dashboard, file browser, search,
storage profiles, audit visibility, and admin route availability checks.
Requirements: FR1.26, FR1.30, FR1.36, FR1.46
Tasks: W28A-408-E
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: AT_WEBUI
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from tests.env_runtime import env_get


def _require_env(key: str) -> str:
    value = env_get(key, "").strip()
    if not value:
        pytest.fail(f"Missing required test env var: {key}")
    return value


def _web_base_url() -> str:
    host = _require_env("FILE_MCP_HTTP_HOST")
    port = _require_env("CLOUD_DOG__WEB_SERVER__PORT")
    return f"http://{host}:{port}"


def _api_key() -> str:
    candidate = env_get("FILE_MCP_WEBUI_E2E_API_KEY", "").strip()
    if candidate:
        return candidate
    return _require_env("FILE_MCP_API_KEY_PRIMARY")


def _login_value() -> str:
    raw = _api_key()
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return raw


def _auth_header_value() -> str:
    raw = _api_key()
    if raw.lower().startswith("bearer "):
        return raw
    return f"Bearer {raw}"


def _wait_for_http_200(url: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        request = Request(url, method="GET")
        try:
            with urlopen(request, timeout=3.0) as response:
                if int(response.status) == 200:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    pytest.fail(f"WebUI endpoint did not return 200 in {timeout_s:.1f}s: {url}")


@dataclass
class UiSession:
    browser: Browser
    context: BrowserContext
    page: Page
    base_url: str


@pytest.fixture()
def ui_session(request: pytest.FixtureRequest) -> UiSession:
    base_url = _web_base_url()
    _wait_for_http_200(f"{base_url}/login")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    try:
        page.goto(f"{base_url}/login", wait_until="domcontentloaded")
        page.get_by_placeholder("Enter API key").fill(_login_value())
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_url(re.compile(".*/dashboard$"), timeout=15_000)
        yield UiSession(browser=browser, context=context, page=page, base_url=base_url)
    finally:
        failed = bool(
            hasattr(request.node, "rep_call") and request.node.rep_call.failed  # type: ignore[attr-defined]
        )
        if failed:
            screenshot_dir = Path("working/W28A-408-E/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", request.node.nodeid)
            screenshot_path = screenshot_dir / f"{safe_name}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
        context.close()
        browser.close()
        playwright.stop()


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _safe_rmdir(path: Path) -> None:
    try:
        if path.exists() and path.is_dir():
            path.rmdir()
    except Exception:
        pass


def _unique_suffix() -> str:
    return str(int(time.time() * 1000))


def _path_exists_on_disk(path: Path, timeout_s: float = 5.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.1)
    return False


def _wait_for_text_on_disk(path: Path, expected: str, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if path.exists() and path.read_text(encoding="utf-8") == expected:
            return True
        time.sleep(0.2)
    return False


def test_webui_t1_api_key_login(ui_session: UiSession) -> None:
    page = ui_session.page
    page.goto(f"{ui_session.base_url}/dashboard", wait_until="networkidle")
    assert page.get_by_role("heading", name="Dashboard").is_visible()
    assert page.get_by_role("link", name=re.compile("Dashboard")).is_visible()
    assert page.get_by_role("link", name=re.compile("File Browser")).is_visible()
    assert page.get_by_role("link", name=re.compile("Search")).is_visible()


def test_webui_t10_dashboard(ui_session: UiSession) -> None:
    page = ui_session.page
    page.goto(f"{ui_session.base_url}/dashboard", wait_until="networkidle")
    assert page.get_by_role("heading", name="Dashboard").is_visible()
    assert page.get_by_text("Service status", exact=False).is_visible()
    assert page.get_by_text("Active backend", exact=False).is_visible()
    assert page.get_by_role("heading", name="Quick actions").is_visible()
    assert page.get_by_role("heading", name="Recent file activity").is_visible()
    assert page.get_by_role("button", name="Refresh").is_visible()


def test_webui_t6_t11_file_read_edit_and_revert(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    root_dir = Path("working") / f"w28a408-ui-file-{run_id}"
    root_dir.mkdir(parents=True, exist_ok=True)
    test_file = root_dir / "edit-target.txt"
    original_text = f"original-{run_id}\n"
    updated_text = f"{original_text}edited-{run_id}\n"
    test_file.write_text(original_text, encoding="utf-8")

    try:
        page.goto(f"{ui_session.base_url}/file-browser", wait_until="networkidle")
        page.get_by_label("Current path").fill(str(root_dir))
        page.get_by_role("button", name="Browse path").click()
        file_row = page.locator("table tbody tr").filter(has_text="edit-target.txt").first
        file_row.get_by_role("button", name="Open").click()
        selected_path = page.get_by_label("Selected file path")
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if selected_path.input_value().endswith("edit-target.txt"):
                break
            page.wait_for_timeout(200)
        assert selected_path.input_value().endswith("edit-target.txt")
        editor = page.get_by_label("Inline editor")
        assert editor.input_value() == original_text

        editor.fill(updated_text)
        page.get_by_role("button", name="Save file").click()
        assert _path_exists_on_disk(test_file)
        assert _wait_for_text_on_disk(test_file, updated_text)

        editor.fill(original_text)
        page.get_by_role("button", name="Save file").click()
        assert _wait_for_text_on_disk(test_file, original_text)
    finally:
        _safe_unlink(test_file)
        _safe_unlink(test_file.with_suffix(".txt.lock"))
        _safe_rmdir(root_dir)


def test_webui_t7_search_and_open_result(ui_session: UiSession) -> None:
    page = ui_session.page
    page.goto(f"{ui_session.base_url}/search", wait_until="networkidle")
    page.get_by_label("Search text").fill("README")
    page.get_by_label("Search type").select_option("path")
    page.get_by_role("button", name="Search").click()
    deadline = time.time() + 60.0
    while time.time() < deadline:
        if "Searching..." not in page.locator("body").inner_text():
            break
        page.wait_for_timeout(300)
    row = page.locator("table tbody tr").first
    row.wait_for(timeout=10_000)
    row.get_by_role("button", name="Open").click()

    page.get_by_role("heading", name="File Browser").wait_for(timeout=10_000)
    assert page.get_by_text("Opened file:", exact=False).is_visible()
    assert page.get_by_label("Selected file path").input_value() != ""


def test_webui_t8_audit_log_filters(ui_session: UiSession) -> None:
    page = ui_session.page
    page.goto(f"{ui_session.base_url}/audit-log", wait_until="networkidle")

    assert page.get_by_role("heading", name="Audit Log").is_visible()
    assert page.get_by_role("heading", name="Entries").is_visible()
    assert page.locator("table tbody tr").count() > 0

    page.get_by_label("Action filter").select_option("write")
    page.get_by_label("Outcome filter").select_option("success")
    assert page.locator("table tbody tr").count() > 0
    assert page.get_by_role("button", name="Export CSV").is_visible()


def test_webui_t9_storage_profile_crud(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    profile_name = f"w28a408-profile-{run_id}"
    updated_notes = f"updated-notes-{run_id}"

    save_button = None
    for _ in range(3):
        page.goto(f"{ui_session.base_url}/storage-profiles", wait_until="networkidle")
        page.get_by_role("heading", name="Storage Profiles").wait_for(timeout=10_000)
        candidate = page.locator("button", has_text="Save profile").first
        if candidate.count() > 0:
            save_button = candidate
            break
        page.wait_for_timeout(500)
    if save_button is None:
        pytest.fail("Storage Profiles editor did not expose Save profile button")

    page.get_by_label("Profile name").fill(profile_name)
    page.get_by_label("Profile type").select_option("local")
    page.get_by_label("Endpoint").fill(f"file:///{profile_name}")
    page.get_by_label("Username").fill("e2e-user")
    page.get_by_label("Notes").fill("initial-notes")
    save_button.wait_for(timeout=10_000)
    save_button.click()

    profile_row = page.get_by_role("row", name=re.compile(profile_name))
    profile_row.wait_for(timeout=10_000)
    assert profile_row.is_visible()

    profile_row.get_by_role("button", name="Edit").click()
    page.get_by_label("Notes").fill(updated_notes)
    save_button = page.locator("button", has_text="Save profile").first
    save_button.wait_for(timeout=10_000)
    save_button.click()
    page.get_by_role("row", name=re.compile(updated_notes)).wait_for(timeout=10_000)

    page.get_by_role("row", name=re.compile(profile_name)).get_by_role(
        "button", name="Delete"
    ).click()
    assert page.get_by_role("row", name=re.compile(profile_name)).count() == 0


def test_webui_t2_t3_t4_t5_t12_admin_routes_present(ui_session: UiSession) -> None:
    base_url = ui_session.base_url
    auth_header = _auth_header_value()
    expected_routes = [
        "/admin/identity",
        "/admin/users",
        "/admin/groups",
        "/admin/api-keys",
        "/admin/rbac",
    ]

    missing: list[str] = []
    for route in expected_routes:
        request = Request(f"{base_url}{route}", method="GET")
        request.add_header("Authorization", auth_header)
        try:
            with urlopen(request, timeout=5.0) as response:
                if int(response.status) >= 400:
                    missing.append(route)
        except HTTPError:
            missing.append(route)
        except Exception:
            missing.append(route)

    if missing:
        pytest.fail(
            "Required admin/rbac WebUI routes unavailable for T2/T3/T4/T5/T12: "
            + ", ".join(sorted(set(missing)))
        )
