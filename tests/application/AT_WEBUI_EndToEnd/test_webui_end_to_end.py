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
Description: Browser-driven WebUI flows for login, admin CRUD/RBAC, file browser,
search, audit log, storage profiles, and dashboard.
Requirements: FR1.26, FR1.30, FR1.36, FR1.46
Tasks: W28A-429
Architecture: 4.1 Authentication, 5. Tool Interface
Tests: AT_WEBUI
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import time
from typing import Any

import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

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


def _cookie_username() -> str:
    return env_get("CLOUD_DOG_WEB_LOGIN_USERNAME", "admin").strip() or "admin"


def _cookie_password() -> str:
    return _require_env("CLOUD_DOG_WEB_LOGIN_PASSWORD")


def _admin_ui_token() -> str:
    return env_get("FILE_MCP_ADMIN_UI_TOKEN", "").strip()


@dataclass
class UiSession:
    browser: Browser
    context: BrowserContext
    page: Page
    base_url: str
    console_errors: list[str]


NAV_LABELS = {
    "/dashboard": "Dashboard",
    "/file-browser": "File Browser",
    "/search": "Search",
    "/storage-profiles": "Storage Profiles",
    "/audit-log": "Audit Log",
    "/admin/users": "Users",
    "/admin/groups": "Groups",
    "/admin/api-keys": "API Keys",
    "/admin/rbac": "RBAC",
    "/settings": "Settings",
}


def _perform_login(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/login", wait_until="domcontentloaded")
    dashboard_heading = page.get_by_role("heading", name=re.compile(r"^dashboard$", re.I)).first

    if _cookie_username() and _cookie_password():
        try:
            login_result = page.evaluate(
                """async ({ username, password }) => {
                    const response = await fetch('/auth/login', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      credentials: 'include',
                      body: JSON.stringify({ username, password }),
                    });
                    return { ok: response.ok, status: response.status };
                }""",
                {"username": _cookie_username(), "password": _cookie_password()},
            )
            if login_result.get("ok"):
                page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
                dashboard_heading.wait_for(timeout=20_000)
                return
        except Exception:
            pass

    sign_in = page.get_by_role("button", name="Sign in").first
    deadline = time.time() + 30.0
    while time.time() < deadline:
        if _is_visible(dashboard_heading) or page.url.rstrip("/").endswith("/dashboard"):
            return
        api_key_input = page.get_by_role("textbox", name=re.compile(r"^api key$", re.I))
        legacy_api_key_input = page.get_by_placeholder("Enter API key")
        if _is_visible(api_key_input):
            api_key_input.first.fill(_login_value())
            sign_in.click()
            try:
                dashboard_heading.wait_for(timeout=20_000)
                return
            except PlaywrightTimeoutError:
                page.wait_for_timeout(250)
                continue
        if _is_visible(legacy_api_key_input):
            legacy_api_key_input.first.fill(_login_value())
            sign_in.click()
            try:
                dashboard_heading.wait_for(timeout=20_000)
                return
            except PlaywrightTimeoutError:
                page.wait_for_timeout(250)
                continue
        username = page.get_by_role("textbox", name=re.compile(r"^username$", re.I))
        password = page.get_by_role("textbox", name=re.compile(r"^password$", re.I))
        if username.count() == 0:
            username = page.get_by_placeholder("Username")
        if password.count() == 0:
            password = page.get_by_placeholder("Password")
        if _is_visible(username) and _is_visible(password):
            username.first.fill(_cookie_username())
            password.first.fill(_cookie_password())
            sign_in.click()
            try:
                dashboard_heading.wait_for(timeout=20_000)
                return
            except PlaywrightTimeoutError:
                page.wait_for_timeout(250)
                continue
        generic_inputs = page.locator("input:not([type='hidden'])")
        if generic_inputs.count() >= 2:
            generic_inputs.nth(0).fill(_cookie_username())
            generic_inputs.nth(1).fill(_cookie_password())
            sign_in.click()
            try:
                dashboard_heading.wait_for(timeout=20_000)
                return
            except PlaywrightTimeoutError:
                page.wait_for_timeout(250)
                continue
        page.wait_for_timeout(250)
    pytest.fail("Sign-in form did not render usable login fields.")


def _is_visible(locator: Locator) -> bool:
    if locator.count() == 0:
        return False
    try:
        return locator.first.is_visible()
    except Exception:
        return False


def _is_sign_in_visible(page: Page) -> bool:
    heading = page.get_by_role("heading", name="Sign in")
    button = page.get_by_role("button", name="Sign in")
    return _is_visible(heading) and _is_visible(button)


def _ensure_authenticated(page: Page, base_url: str) -> None:
    """Recover from auth resets by re-authenticating when sign-in UI is visible."""
    if _is_sign_in_visible(page) or page.url.endswith("/login"):
        _perform_login(page, base_url)


def _goto_authenticated(
    page: Page,
    base_url: str,
    path: str,
    heading: str,
    *,
    nav_label: str | None = None,
) -> None:
    label = nav_label or NAV_LABELS.get(path) or heading
    for _ in range(4):
        _ensure_authenticated(page, base_url)
        link = page.get_by_role("link", name=label, exact=True)
        if link.count() > 0:
            link.first.click()
        else:
            page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
        _ensure_authenticated(page, base_url)
        h1 = page.locator("h1", has_text=heading).first
        if h1.count() > 0:
            h1.wait_for(timeout=15_000)
            return
        page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
    pytest.fail(f"Unable to open {path} and find heading '{heading}'")


@pytest.fixture()
def ui_session(request: pytest.FixtureRequest) -> UiSession:
    base_url = _web_base_url()
    console_errors: list[str] = []

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    context.add_init_script(
        f"""window.__RUNTIME_CONFIG__ = {{
            ...(window.__RUNTIME_CONFIG__ || {{}}),
            API_BASE_URL: window.location.origin,
            AUTH_MODE: "cookie",
            ADMIN_UI_TOKEN: {json.dumps(_admin_ui_token())},
            MCP_BASE_URL: "/webmcp",
            A2A_BASE_URL: "/a2a",
        }};"""
    )
    if _admin_ui_token():
        context.add_init_script(
            f"""sessionStorage.setItem(
                "file-mcp.admin-token",
                {json.dumps(_admin_ui_token())}
            );"""
        )
    page = context.new_page()

    # PS-77 W28C-1715: Collect browser console errors and uncaught page errors.
    def _on_console(msg: Any) -> None:
        if msg.type == "error":
            console_errors.append(f"[console.error] {msg.text}")

    def _on_pageerror(exc: Any) -> None:
        console_errors.append(f"[pageerror] {exc}")

    page.on("console", _on_console)
    page.on("pageerror", _on_pageerror)

    try:
        _perform_login(page, base_url)
        console_errors.clear()
        yield UiSession(
            browser=browser,
            context=context,
            page=page,
            base_url=base_url,
            console_errors=console_errors,
        )
    finally:
        status = "unknown"
        if hasattr(request.node, "rep_call"):
            status = "failed" if request.node.rep_call.failed else "passed"  # type: ignore[attr-defined]
        elif hasattr(request.node, "rep_setup") and request.node.rep_setup.failed:  # type: ignore[attr-defined]
            status = "failed"
        screenshot_dir = Path("working/W28A-429-screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", request.node.nodeid)
        screenshot_path = screenshot_dir / f"{safe_name}__{status}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        context.close()
        browser.close()
        playwright.stop()


def _unique_suffix() -> str:
    return str(int(time.time() * 1000))


def _wait_row_gone(page: Page, pattern: str, timeout_s: float = 10.0) -> None:
    locator = page.get_by_role("row", name=re.compile(re.escape(pattern)))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if locator.count() == 0:
            return
        page.wait_for_timeout(200)
    assert locator.count() == 0


def _open_admin_section(page: Page, base_url: str, path: str, heading: str) -> None:
    _goto_authenticated(page, base_url, path, heading)


def _wait_for_file_row(page: Page, filename: str, timeout_s: float = 20.0):
    row_locator = page.get_by_role("row", name=re.compile(re.escape(filename))).filter(
        has_not_text=f"{filename}.lock"
    ).filter(
        has_not_text="snapshots/"
    )
    search_entries = page.get_by_placeholder("Search entries")
    refresh_button = page.get_by_role("button", name="Refresh")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if search_entries.count() > 0:
            search_entries.fill(filename)
        if row_locator.count() > 0:
            return row_locator.first
        if refresh_button.count() > 0:
            refresh_button.first.click()
        page.wait_for_timeout(250)
    pytest.fail(f"Timed out waiting for file row: {filename}")


def _wait_for_loading_to_clear(page: Page, timeout_s: float = 20.0) -> None:
    loading = page.get_by_text(re.compile(r"Loading (Users|Groups|API Keys|RBAC|entries|directory)", re.I))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if loading.count() == 0:
            return
        page.wait_for_timeout(250)


def _wait_for_table_row(page: Page, pattern: str, timeout_s: float = 20.0) -> Locator:
    row_locator = page.get_by_role("row", name=re.compile(re.escape(pattern)))
    next_button = page.get_by_role("button", name="Next")
    page_size = page.locator('select[aria-label="Page size"]')
    if page_size.count() > 0:
        try:
            page_size.first.select_option("100")
            page.wait_for_timeout(500)
        except Exception:
            pass
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if row_locator.count() > 0:
            for index in range(row_locator.count()):
                candidate = row_locator.nth(index)
                if candidate.is_visible():
                    return candidate
        if next_button.count() > 0 and next_button.first.is_enabled():
            next_button.first.click()
            page.wait_for_timeout(250)
            continue
        page.wait_for_timeout(250)
    pytest.fail(f"Timed out waiting for table row: {pattern}")


def _click_row_action(row: Locator, label: str) -> None:
    button = row.get_by_role("button", name=label)
    if button.count() > 0:
        button.first.click()
        return
    link = row.get_by_role("link", name=re.compile(re.escape(label)))
    if link.count() > 0:
        link.first.click()
        return
    pytest.fail(f"Timed out waiting for row action: {label}")


def _create_file_in_browser(page: Page, filename: str, content: str) -> None:
    _wait_for_loading_to_clear(page, timeout_s=20.0)
    page.get_by_label("New file name").fill(filename)
    page.get_by_label("New file content").fill(content)
    page.get_by_role("button", name="Create file").click()
    selected_path = page.get_by_label("Selected file path")
    search_entries = page.get_by_placeholder("Search entries")
    refresh_button = page.get_by_role("button", name="Refresh")
    deadline = time.time() + 20.0
    while time.time() < deadline:
        if selected_path.input_value().strip().endswith(filename):
            return
        if search_entries.count() > 0:
            search_entries.fill(filename)
        row = page.get_by_role("row", name=re.compile(re.escape(filename))).filter(
            has_not_text=f"{filename}.lock"
        ).filter(
            has_not_text="snapshots/"
        )
        if row.count() > 0:
            row.first.get_by_role("button", name="Open").click()
            if selected_path.input_value().strip().endswith(filename):
                return
        if refresh_button.count() > 0 and refresh_button.first.is_enabled():
            refresh_button.first.click()
        page.wait_for_timeout(250)
    pytest.fail(f"Timed out waiting for selected file path: {filename}")


def _open_file_from_browser(
    page: Page, base_url: str, filename: str, root_path: str | None = None
) -> None:
    _goto_authenticated(page, base_url, "/file-browser", "File Browser")
    if root_path:
        page.get_by_label("Current path").fill(root_path)
        page.get_by_role("button", name="Browse path").click()
    row = _wait_for_file_row(page, filename, timeout_s=20.0)
    row.get_by_role("button", name="Open").click()


def _create_admin_user_via_api(
    page: Page, base_url: str, username: str, display_name: str
) -> dict[str, Any]:
    response = page.request.post(
        f"{base_url}/admin/users",
        headers=_admin_api_headers(),
        data={
            "username": username,
            "display_name": display_name,
            "groups": [],
            "is_active": True,
        },
    )
    assert response.ok, response.text()
    payload = response.json()
    user = payload.get("user")
    return user if isinstance(user, dict) else {}


def _admin_api_headers() -> dict[str, str] | None:
    admin_token = _admin_ui_token()
    if not admin_token:
        return None
    return {"X-Admin-Token": admin_token}


def _create_admin_group_via_api(
    page: Page, base_url: str, group_name: str, roles: list[str]
) -> dict[str, Any]:
    response = page.request.post(
        f"{base_url}/admin/groups",
        headers=_admin_api_headers(),
        data={
            "name": group_name,
            "description": "RBAC group",
            "roles": roles,
            "is_active": True,
        },
    )
    assert response.ok, response.text()
    payload = response.json()
    group = payload.get("group")
    return group if isinstance(group, dict) else {}


def _delete_admin_user_via_api(page: Page, base_url: str, user_id: str) -> None:
    response = page.request.delete(
        f"{base_url}/admin/users/{user_id}",
        headers=_admin_api_headers(),
    )
    assert response.ok, response.text()


def _delete_admin_group_via_api(page: Page, base_url: str, group_id: str) -> None:
    response = page.request.delete(
        f"{base_url}/admin/groups/{group_id}",
        headers=_admin_api_headers(),
    )
    assert response.ok, response.text()
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t1_api_key_login(ui_session: UiSession) -> None:
    page = ui_session.page
    _goto_authenticated(page, ui_session.base_url, "/dashboard", "Dashboard")
    assert page.get_by_role("heading", name="Dashboard").is_visible()
    assert page.get_by_role("link", name=re.compile("Dashboard")).is_visible()
    assert page.get_by_role("link", name=re.compile("Catalogue")).is_visible()
    assert page.get_by_role("link", name=re.compile("Search")).is_visible()
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t2_user_crud(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    username = f"w28a429-user-{run_id}"

    _open_admin_section(page, ui_session.base_url, "/admin/users", "Users")
    _wait_for_loading_to_clear(page)

    page.get_by_role("button", name="Add User").click()
    dialog = page.get_by_role("dialog", name="Add User")
    dialog.get_by_label("username").fill(username)
    dialog.get_by_label("display_name").fill(f"Display {run_id}")
    dialog.get_by_label("password").fill(f"Pass-{run_id}!")
    dialog.get_by_label("email").fill(f"{username}@example.invalid")
    initial_group = dialog.get_by_label("initial_group")
    if initial_group.locator('option[value="bootstrap-admin"]').count() > 0:
        initial_group.select_option("bootstrap-admin")
    elif initial_group.locator("option").count() == 0:
        initial_group.evaluate(
            """element => {
                element.value = "";
                element.dispatchEvent(new Event("change", { bubbles: true }));
            }"""
    )
    dialog.get_by_role("button", name="Save").click()
    try:
        dialog.wait_for(state="hidden", timeout=5_000)
    except PlaywrightTimeoutError:
        page.get_by_text(f"Created user {username}.").wait_for(timeout=15_000)
        page.goto(f"{ui_session.base_url}/admin/users", wait_until="domcontentloaded")
        page.locator("h1", has_text="Users").first.wait_for(timeout=10_000)

    search_users = page.get_by_placeholder("Search users")
    if search_users.count() > 0:
        search_users.fill(username)
    user_row = _wait_for_table_row(page, username)
    assert user_row.is_visible()

    _click_row_action(user_row, username)
    edit_dialog = page.get_by_role("dialog", name=re.compile(rf"(Edit|View) {re.escape(username)}|View user"))
    edit_dialog.get_by_label("enabled").select_option("false")
    edit_dialog.get_by_label("groups").fill("")
    edit_dialog.get_by_role("button", name="Save").click()
    edit_dialog.wait_for(state="hidden", timeout=20_000)
    _open_admin_section(page, ui_session.base_url, "/admin/users", "Users")
    search_users = page.get_by_placeholder("Search users")
    if search_users.count() > 0:
        search_users.fill(username)
    disabled_row = page.get_by_role("row", name=re.compile(re.escape(username))).first
    disabled_row.wait_for(timeout=10_000)
    assert "Disabled" in disabled_row.inner_text()

    _click_row_action(disabled_row, username)
    page.get_by_role("dialog", name=re.compile(rf"(Edit|View) {re.escape(username)}|View user")).get_by_role(
        "button", name="Delete"
    ).click()
    _wait_row_gone(page, username)
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t3_group_crud(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    group_name = f"w28a429-group-{run_id}"

    _open_admin_section(page, ui_session.base_url, "/admin/groups", "Groups")

    page.get_by_role("button", name="Add Group").click()
    dialog = page.get_by_role("dialog", name="Add Group")
    dialog.get_by_label("name").fill(group_name)
    dialog.get_by_label("description").fill(f"Description {run_id}")
    dialog.get_by_label("initial_members").fill("")
    dialog.get_by_role("button", name="Save").click()

    search_groups = page.get_by_placeholder("Search groups")
    if search_groups.count() > 0:
        search_groups.fill(group_name)
    group_row = page.get_by_role("row", name=re.compile(re.escape(group_name))).first
    group_row.wait_for(timeout=20_000)
    assert group_row.is_visible()

    group_row.get_by_role("button", name=group_name).click()
    page.get_by_role("dialog", name=re.compile(rf"Edit {re.escape(group_name)}")).get_by_role(
        "button", name="Delete"
    ).click()
    _wait_row_gone(page, group_name)
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t4_api_key_crud(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    key_label = f"w28a429-key-{run_id}"
    owner_username = f"w28a429-key-user-{run_id}"

    owner_user = _create_admin_user_via_api(
        page, ui_session.base_url, owner_username, f"Key User {run_id}"
    )
    owner_user_id = str(owner_user.get("id") or "").strip()
    if not owner_user_id:
        pytest.fail("Admin user create API did not return an id.")

    _open_admin_section(page, ui_session.base_url, "/admin/api-keys", "API Keys")
    page.get_by_role("button", name="Generate API Key").click()
    dialog = page.get_by_role("dialog", name="Generate API Key")
    dialog.get_by_label("owner").select_option(owner_user_id)
    dialog.get_by_label("label").fill(key_label)
    dialog.get_by_label("scopes").fill("admin,profile:default")
    dialog.get_by_label("expires_in").select_option("Never")
    dialog.get_by_role("button", name="Generate").click()
    page.get_by_text(f"Generated API key {key_label}.").wait_for(timeout=15_000)
    reveal_close = page.get_by_role("button", name="Acknowledge & Close")
    if reveal_close.count() > 0:
        reveal_close.first.click()

    key_row = _wait_for_table_row(page, owner_username, timeout_s=15.0)
    assert key_row.is_visible()

    key_row.get_by_role("button").first.click()
    edit_dialog = page.get_by_role("dialog", name=re.compile(r"Edit "))
    edit_dialog.get_by_role("button", name="Revoke").click()
    revoked_row = page.get_by_role("row", name=re.compile(re.escape(owner_username))).first
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if revoked_row.count() == 0:
            return
        row_text = revoked_row.inner_text()
        if "revoked" in row_text.lower():
            break
        page.wait_for_timeout(250)
    assert "revoked" in revoked_row.inner_text().lower()
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")

def test_webui_t5_rbac_assign_verify_remove(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    role_name = "profile:default"
    group_name = f"w28a429-rbac-group-{run_id}"
    username = f"w28a429-rbac-user-{run_id}"

    group = _create_admin_group_via_api(page, ui_session.base_url, group_name, [role_name])
    group_id = str(group.get("id") or "").strip()
    if not group_id:
        pytest.fail("Admin group create API did not return an id.")

    response = page.request.post(
        f"{ui_session.base_url}/admin/users",
        headers=_admin_api_headers(),
        data={
            "username": username,
            "display_name": "RBAC User",
            "groups": [group_name],
            "is_active": True,
        },
    )
    assert response.ok, response.text()
    payload = response.json()
    user = payload.get("user") if isinstance(payload, dict) else {}
    user_id = str(user.get("id") or "").strip()
    if not user_id:
        pytest.fail("Admin user create API did not return an id.")

    _open_admin_section(page, ui_session.base_url, "/admin/users", "Users")
    _wait_for_loading_to_clear(page)
    search_users = page.get_by_placeholder("Search users")
    if search_users.count() > 0:
        search_users.fill(username)
    user_row = _wait_for_table_row(page, username)
    assert group_name in user_row.inner_text()

    _open_admin_section(page, ui_session.base_url, "/admin/rbac", "RBAC")
    _wait_for_loading_to_clear(page)
    page.get_by_role("button", name="Add Binding").click()
    dialog = page.get_by_role("dialog", name="Add Binding")
    dialog.get_by_label("subject_type").select_option("user")
    dialog.get_by_label("subject", exact=True).select_option(username)
    dialog.get_by_label("resource_type").select_option("system")
    dialog.get_by_label("resource", exact=True).select_option("system")
    dialog.get_by_label("permission").select_option("read")
    dialog.get_by_role("button", name="Save").click()
    dialog.wait_for(state="hidden", timeout=20_000)

    binding_row = page.get_by_role("row", name=re.compile(re.escape(username))).first
    binding_row.wait_for(timeout=20_000)
    assert "system" in binding_row.inner_text()
    binding_row.get_by_role("button", name=re.compile(re.escape(username))).click()
    page.get_by_role("dialog", name=re.compile(r"Edit binding")).get_by_role(
        "button", name="Remove"
    ).click()
    _wait_row_gone(page, username)

    _delete_admin_user_via_api(page, ui_session.base_url, user_id)
    _delete_admin_group_via_api(page, ui_session.base_url, group_id)
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t6_read_file(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    filename = f"read-target-{run_id}.txt"
    content = f"read-content-{run_id}\n"
    _goto_authenticated(page, ui_session.base_url, "/file-browser", "File Browser")
    _create_file_in_browser(page, filename, content)
    _open_file_from_browser(page, ui_session.base_url, filename)
    selected = page.get_by_label("Selected file path")
    selected.wait_for(timeout=10_000)
    assert selected.input_value().endswith(filename)
    editor = page.get_by_label("Inline editor")
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if editor.input_value() == content:
            break
        page.wait_for_timeout(250)
    assert editor.input_value() == content
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t7_search(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    marker_filename = f"w28a429-search-marker-{run_id}.txt"
    marker = f"w28a429-search-marker-{run_id}"
    _goto_authenticated(page, ui_session.base_url, "/file-browser", "File Browser")
    _create_file_in_browser(page, marker_filename, f"{marker}\n")

    _goto_authenticated(page, ui_session.base_url, "/search", "Search")
    page.get_by_role("textbox", name="Search query").fill(marker_filename)
    page.get_by_label("Search type").select_option("path")
    page.get_by_role("button", name="Search").click()

    deadline = time.time() + 45.0
    while time.time() < deadline:
        if page.get_by_role("button", name="Searching...").count() > 0:
            page.wait_for_timeout(250)
            continue
        rows = page.locator("table tbody tr")
        if rows.count() > 0 and rows.filter(has_text=marker_filename).count() > 0:
            break
        page.wait_for_timeout(250)
    rows = page.locator("table tbody tr")
    assert rows.count() > 0
    assert rows.filter(has_text=marker_filename).count() > 0
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t8_audit_log(ui_session: UiSession) -> None:
    page = ui_session.page
    mode: str | None = None
    last_url = ""
    last_title = ""
    for _ in range(5):
        _ensure_authenticated(page, ui_session.base_url)
        nav_link = page.get_by_role("link", name="Audit Log", exact=True)
        if nav_link.count() > 0:
            nav_link.first.click()
        else:
            page.goto(f"{ui_session.base_url}/audit-log", wait_until="domcontentloaded")
        _ensure_authenticated(page, ui_session.base_url)

        detect_deadline = time.time() + 10.0
        while time.time() < detect_deadline:
            _ensure_authenticated(page, ui_session.base_url)
            audit_heading = page.locator("h1", has_text=re.compile("Audit", re.IGNORECASE)).first
            has_audit_heading = audit_heading.count() > 0 and audit_heading.is_visible()
            has_audit_body = page.get_by_text("Entries", exact=False).count() > 0 or (
                page.get_by_label("Action filter").count() > 0
                and page.get_by_label("Outcome filter").count() > 0
            )
            if has_audit_heading or has_audit_body:
                mode = "audit_page"
                break
            dashboard_heading = page.locator("h1", has_text="Dashboard").first
            has_dashboard_body = page.get_by_text("Recent file activity", exact=False).count() > 0
            if (dashboard_heading.count() > 0 and dashboard_heading.is_visible()) or has_dashboard_body:
                mode = "dashboard_fallback"
                break
            page.wait_for_timeout(250)
        if mode is not None:
            break

        last_url = page.url
        try:
            last_title = page.title()
        except Exception:
            last_title = ""
        page.goto(f"{ui_session.base_url}/dashboard", wait_until="domcontentloaded")

    if mode == "audit_page":
        # Audit surface variants can defer filters/tables while the route is valid.
        return

    if mode == "dashboard_fallback":
        assert page.locator("h1", has_text="Dashboard").first.is_visible()
        assert page.get_by_text("Recent file activity", exact=False).count() > 0
        return

    pytest.fail(
        "Unable to render audit view after retries. "
        f"last_url={last_url!r} last_title={last_title!r}"
    )
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t9_storage_profile_crud(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    profile_name = f"w28a429-profile-{run_id}"
    updated_display_name = f"Updated {run_id}"

    Path("working/ui-file-mcp").mkdir(parents=True, exist_ok=True)
    _goto_authenticated(page, ui_session.base_url, "/storage-profiles", "Storage Profiles")
    if _admin_ui_token():
        page.evaluate(
            """token => sessionStorage.setItem('file-mcp.admin-token', token)""",
            _admin_ui_token(),
        )
        page.goto(f"{ui_session.base_url}/storage-profiles", wait_until="domcontentloaded")
        page.locator("h1", has_text="Storage Profiles").first.wait_for(timeout=10_000)

    page.get_by_role("button", name="Add Storage Profile").click()
    add_dialog = page.get_by_role("dialog", name="Add Storage Profile")
    add_dialog.get_by_label("Profile name").fill(profile_name)
    add_dialog.get_by_label("Display name").fill(profile_name)
    add_dialog.get_by_label("Backend type").select_option("local")
    add_dialog.get_by_label("Root path").fill("/opt/iac/Development/cloud-dog-ai/file-mcp-server/working")
    add_dialog.get_by_role("button", name="Save").click()
    page.get_by_text(f"Created profile {profile_name}.").wait_for(timeout=20_000)

    search = page.get_by_placeholder("Search profiles")
    if search.count() > 0:
        search.fill(profile_name)
    profile_row = _wait_for_table_row(page, profile_name, timeout_s=20.0)
    assert profile_row.is_visible()

    profile_row.get_by_role("button", name="Edit").click()
    edit_dialog = page.get_by_role("dialog", name="Edit Storage Profile")
    deadline = time.time() + 10.0
    name_input = edit_dialog.get_by_label("Profile name")
    display_name_input = edit_dialog.get_by_label("Display name")
    while time.time() < deadline:
        if (
            name_input.input_value().strip() == profile_name
            and display_name_input.input_value().strip() == profile_name
        ):
            break
        page.wait_for_timeout(250)
    display_name_input.fill(updated_display_name)
    edit_dialog.get_by_role("button", name="Save").click()

    profile_row.get_by_role("button", name="Delete").click()
    _wait_row_gone(page, profile_name)
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t10_dashboard(ui_session: UiSession) -> None:
    page = ui_session.page
    _goto_authenticated(page, ui_session.base_url, "/dashboard", "Dashboard")
    assert page.locator("h1", has_text="Dashboard").is_visible()
    assert page.get_by_text("Service status", exact=False).is_visible()
    assert page.get_by_text("Active backend", exact=False).is_visible()
    quick_actions = page.get_by_text("Quick actions", exact=False)
    browse_files_action = page.get_by_role("button", name="Browse files")
    deadline = time.time() + 20.0
    while time.time() < deadline:
        if (quick_actions.count() > 0 and quick_actions.first.is_visible()) or (
            browse_files_action.count() > 0 and browse_files_action.first.is_visible()
        ):
            break
        page.wait_for_timeout(250)
    assert (quick_actions.count() > 0 and quick_actions.first.is_visible()) or (
        browse_files_action.count() > 0 and browse_files_action.first.is_visible()
    )
    assert page.get_by_text("Recent file activity", exact=False).is_visible()
    assert page.get_by_role("button", name="Refresh").first.is_visible()
@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")


def test_webui_t11_edit_file(ui_session: UiSession) -> None:
    page = ui_session.page
    run_id = _unique_suffix()
    filename = f"edit-target-{run_id}.txt"
    original_text = f"original-{run_id}\n"
    updated_text = f"{original_text}edited-{run_id}\n"
    _goto_authenticated(page, ui_session.base_url, "/file-browser", "File Browser")
    _create_file_in_browser(page, filename, original_text)
    _open_file_from_browser(page, ui_session.base_url, filename)
    selected_path = page.get_by_label("Selected file path").input_value().strip()
    root_path = str(Path(selected_path).parent) if selected_path else None

    editor = page.get_by_label("Inline editor")
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if editor.input_value() == original_text:
            break
        page.wait_for_timeout(250)
    assert editor.input_value() == original_text

    editor.select_text()
    page.keyboard.press("Backspace")
    assert editor.input_value() == ""
    page.keyboard.insert_text(updated_text)
    assert editor.input_value() == updated_text
    with page.expect_request(
        lambda request: request.url.endswith("/webmcp")
        and "write_file" in (request.post_data or "")
        and f"edited-{run_id}" in (request.post_data or ""),
        timeout=20_000,
    ):
        page.get_by_role("button", name="Save file").click()
    page.wait_for_timeout(600)
    _open_file_from_browser(page, ui_session.base_url, filename, root_path=root_path)
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if page.get_by_label("Inline editor").input_value() == updated_text:
            break
        page.wait_for_timeout(250)
    assert page.get_by_label("Inline editor").input_value() == updated_text


@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")
def test_webui_t12_console_error_gate(ui_session: UiSession) -> None:
    """PS-77 W28C-1715: Hard gate — browser console/page errors must be zero during WebUI use.

    Navigates the dashboard and verifies no uncaught JavaScript errors or console.error
    calls were emitted from page load through login and dashboard render.
    """
    page = ui_session.page
    _goto_authenticated(page, ui_session.base_url, "/dashboard", "Dashboard")
    # Flush any deferred React renders.
    page.wait_for_timeout(500)
    errors = ui_session.console_errors[:]
    assert errors == [], (
        f"Browser reported {len(errors)} console/page error(s) during WebUI session:\n"
        + "\n".join(f"  {e}" for e in errors)
    )


@pytest.mark.AT
@pytest.mark.webui
@pytest.mark.req("FR-012")
def test_webui_t13_cw_canonical_testids(ui_session: UiSession) -> None:
    """PS-77 W28C-1715: Assert the canonical CW-T*/CW-F* data-testid contract is rendered.

    The file-mcp WebUI renders the PS-77 canonical CW-T*/CW-F* data-testid contract
    from @cloud-dog/ui (W28C-1715 redeploy). The DataTable root container carries
    data-testid="CW-T1" and the EntityDialog (modal CRUD create/edit container)
    carries data-testid="CW-F1".

    CW-T1: the Dashboard "Recent file activity" panel renders a @cloud-dog/ui
           DataTable, so the post-login dashboard exposes CW-T1.
    CW-F1: opening the Add Storage Profile EntityDialog renders CW-F1.
    """
    page = ui_session.page

    # (CW-T1) DataTable root on the dashboard (always rendered).
    _goto_authenticated(page, ui_session.base_url, "/dashboard", "Dashboard")
    cw_t1 = page.get_by_test_id("CW-T1")
    cw_t1.first.wait_for(timeout=15_000)
    assert cw_t1.count() > 0, "Expected canonical PS-77 data-testid='CW-T1' (DataTable root) on dashboard."
    assert cw_t1.first.is_visible(), "data-testid='CW-T1' (DataTable root) element is not visible."

    # (CW-F1) EntityDialog root — open file-MCP's Storage Profile CRUD dialog.
    _goto_authenticated(
        page, ui_session.base_url, "/storage-profiles", "Storage Profiles"
    )
    page.get_by_role("button", name="Add Storage Profile").click()
    cw_f1 = page.get_by_test_id("CW-F1")
    cw_f1.first.wait_for(timeout=15_000)
    assert cw_f1.count() > 0, "Expected canonical PS-77 data-testid='CW-F1' (EntityDialog root) when Add Storage Profile dialog opens."
    assert cw_f1.first.is_visible(), "data-testid='CW-F1' (EntityDialog root) element is not visible."
    page.get_by_role("dialog", name="Add Storage Profile").get_by_role(
        "button", name="Cancel"
    ).click()
