"""Browserbase sessions driven over CDP with Playwright, one per agent run.

Natural-language act/extract use Claude over the page's accessibility snapshot / text
instead of Stagehand (a Node-first dependency); Playwright executes the chosen action.
Secrets are filled here and scrubbed from everything that leaves this service.
"""

import asyncio
import base64
import os

import httpx
from fastapi import APIRouter, Depends, Request
from propadmin_core import ProviderNotConfigured
from propadmin_core.providers import ClaudeProvider
from propadmin_runtime import credentials as vault
from propadmin_runtime.auth import require_internal
from pydantic import BaseModel, Field

router = APIRouter(prefix="/internal/sessions", dependencies=[Depends(require_internal)])

BROWSERBASE = "https://api.browserbase.com/v1"
# ponytail: in-process sessions; run the browser service with max-instances=1 (or session
# affinity) so a run's calls reach the instance holding its CDP connection.
SESSIONS = {}
TEXT_LIMIT = 20_000
USERNAME = (
    'input[autocomplete="username"], input[type="email"], input[name*="user" i], '
    'input[name*="email" i], input[id*="user" i], input[id*="email" i], input[type="text"]'
)
PASSWORD = 'input[type="password"]'
ONE_TIME_CODE = (
    'input[autocomplete="one-time-code"], input[name*="otp" i], input[name*="totp" i], '
    'input[name*="code" i], input[id*="otp" i], input[id*="code" i]'
)
ACT_PROMPT = (
    "You control a web page. Given an instruction and the page's ARIA snapshot, choose ONE "
    'action: {"action": "click"|"fill"|"select"|"check"|"press"|"goto"|"none", "role": '
    'ARIA role of the target, "name": its exact accessible name, "value": text/option/key/'
    'url when needed, "reason": short}. Use "none" if the instruction cannot be done.'
)
EXTRACT_PROMPT = (
    'Extract data from the page text following the instruction. Return {"data": ...} where '
    "data matches the given JSON schema; use null for values not on the page. Never invent."
)


class Open(BaseModel):
    url: str = Field(pattern=r"^https?://", max_length=4000)
    profile: str | None = None


class Instruction(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    schema_: dict | None = Field(default=None, alias="schema")


class Login(BaseModel):
    credential: str


class BrowserClaude(ClaudeProvider):
    def __init__(self):
        self.key, self.model = os.getenv("ANTHROPIC_API_KEY"), os.getenv("BROWSER_MODEL")
        if not self.key or not self.model:
            raise ProviderNotConfigured(
                "Browser actions require ANTHROPIC_API_KEY and BROWSER_MODEL"
            )


def browserbase_config():
    key, project = os.getenv("BROWSERBASE_API_KEY"), os.getenv("BROWSERBASE_PROJECT_ID")
    if not key or not project:
        raise ProviderNotConfigured(
            "Browserbase requires BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID"
        )
    return key, project


async def browserbase(path, payload):
    key, project = browserbase_config()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            BROWSERBASE + path,
            json={"projectId": project, **payload},
            headers={"X-BB-API-Key": key},
        )
    if response.status_code >= 400:
        raise ValueError(f"Browserbase returned HTTP {response.status_code}")
    return response.json()


async def login_context(store, credential_id):
    """One persisted Browserbase context per credential holds its cookies/local storage."""
    record = store.snapshot()["credentials"][credential_id]
    if record.get("browserbase_context_id"):
        return record["browserbase_context_id"]
    context_id = (await browserbase("/contexts", {}))["id"]

    def write(state):
        state["credentials"][credential_id]["browserbase_context_id"] = context_id

    store.mutate(write)
    return context_id


def redact(session, text):
    for secret in session["secrets"]:
        text = text.replace(secret, "[redacted]")
    return text


def current(run_id):
    if run_id not in SESSIONS:
        raise ValueError("No open browser session for this run; call browser_open first")
    return SESSIONS[run_id]


async def view(session, screenshot=False, limit=TEXT_LIMIT):
    page = session["page"]
    result = {
        "url": page.url,
        "title": await page.title(),
        "text": redact(session, await page.locator("body").inner_text())[:limit],
    }
    if screenshot:
        image = await page.screenshot(type="jpeg", quality=60)
        result["screenshot"] = base64.b64encode(image).decode()
    return result


async def close_session(run_id):
    session = SESSIONS.pop(run_id, None)
    if not session:
        return False
    try:
        await session["browser"].close()
    finally:
        await session["playwright"].stop()
        try:
            # Ending the session is what saves a persisted context.
            await browserbase(f"/sessions/{session['id']}", {"status": "REQUEST_RELEASE"})
        except (ValueError, httpx.HTTPError):
            pass  # disconnecting already ends a non-keepAlive session
    return True


@router.post("/{run_id}/open")
async def open_session(run_id: str, body: Open, request: Request):
    browserbase_config()
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ProviderNotConfigured("Install playwright for the browser service") from exc
    await close_session(run_id)
    settings = {}
    if body.profile:
        context_id = await login_context(request.app.state.store, body.profile)
        settings["context"] = {"id": context_id, "persist": True}
    created = await browserbase("/sessions", {"browserSettings": settings})
    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.connect_over_cdp(created["connectUrl"])
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()
    except Exception:
        await playwright.stop()
        await browserbase(f"/sessions/{created['id']}", {"status": "REQUEST_RELEASE"})
        raise
    session = {
        "id": created["id"],
        "playwright": playwright,
        "browser": browser,
        "page": page,
        "secrets": set(),
    }
    SESSIONS[run_id] = session
    await page.goto(body.url, wait_until="domcontentloaded")
    return {"session_id": created["id"], **await view(session, screenshot=True)}


@router.post("/{run_id}/act")
async def act(run_id: str, body: Instruction):
    session = current(run_id)
    page = session["page"]
    snapshot = redact(session, await page.locator("body").aria_snapshot())[:40_000]
    choice = await asyncio.to_thread(
        BrowserClaude().json,
        ACT_PROMPT,
        {"instruction": body.instruction, "url": page.url, "snapshot": snapshot},
    )
    action, value = choice.get("action"), choice.get("value") or ""
    if action == "goto":
        await page.goto(value, wait_until="domcontentloaded")
    elif action == "press":
        await page.keyboard.press(value)
    elif action in {"click", "fill", "select", "check"}:
        target = page.get_by_role(choice["role"], name=choice["name"], exact=True).first
        if action == "click":
            await target.click()
        elif action == "fill":
            await target.fill(value)
        elif action == "select":
            await target.select_option(value)
        else:
            await target.check()
        await page.wait_for_load_state("domcontentloaded")
    elif action != "none":
        raise ValueError(f"Model chose an unsupported action {action!r}")
    performed = {key: choice.get(key) for key in ("action", "role", "name", "value", "reason")}
    return {"performed": performed, **await view(session, limit=8_000)}


@router.post("/{run_id}/extract")
async def extract(run_id: str, body: Instruction):
    session = current(run_id)
    page = await view(session, limit=60_000)
    result = await asyncio.to_thread(
        BrowserClaude().json,
        EXTRACT_PROMPT,
        {"instruction": body.instruction, "schema": body.schema_ or {}, "page": page["text"]},
    )
    return {"url": page["url"], "data": result.get("data")}


@router.post("/{run_id}/login")
async def login(run_id: str, body: Login, request: Request):
    """Fills secrets only on allowed domains; returns the outcome, never a value."""
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import TimeoutError as PlaywrightTimeout

    session = current(run_id)
    page = session["page"]
    record = request.app.state.store.snapshot()["credentials"][body.credential]
    domains = record["allowed_domains"]
    if not vault.domain_allowed(page.url, domains):
        return {
            "logged_in": False,
            "error": "Page origin is not an allowed domain",
            "url": page.url,
        }
    secret = vault.get_secret(request.app.state.settings, body.credential)
    session["secrets"].update(value for value in secret.values() if value)

    async def fill(locator, value):
        # Re-check before every fill: a redirect mid-login must not receive the secret.
        if not vault.domain_allowed(page.url, domains):
            raise PermissionError("Page left the allowed domains during login")
        await locator.fill(value)
        await locator.press("Enter")

    try:
        password = page.locator(PASSWORD).first
        if not await password.is_visible():  # two-step forms ask for the username first
            await fill(page.locator(USERNAME).first, record["username"])
            await password.wait_for(state="visible", timeout=15_000)
        else:
            username = page.locator(USERNAME).first
            if await username.count():
                await username.fill(record["username"])
        await fill(password, secret["password"])
        await page.wait_for_load_state("domcontentloaded")
        if secret.get("totp_seed"):
            code = page.locator(ONE_TIME_CODE).first
            try:
                await code.wait_for(state="visible", timeout=10_000)
                await fill(code, vault.totp(secret["totp_seed"]))
                await page.wait_for_load_state("domcontentloaded")
            except PlaywrightTimeout:
                pass  # no 2FA prompt this time (trusted device)
        await page.wait_for_timeout(1_500)
        logged_in = not await page.locator(PASSWORD).first.is_visible()
    except (PermissionError, PlaywrightError) as exc:
        return {"logged_in": False, "error": redact(session, str(exc))[:300], "url": page.url}
    result = {"logged_in": logged_in, "url": page.url, "title": await page.title()}
    if not logged_in:
        result["error"] = "Login form is still shown; credential may be wrong or expired"
    return result


@router.post("/{run_id}/screenshot")
async def screenshot(run_id: str):
    page = current(run_id)["page"]
    image = await page.screenshot(type="jpeg", quality=60)
    return {"url": page.url, "screenshot": base64.b64encode(image).decode()}


@router.post("/{run_id}/close")
async def close(run_id: str):
    """Also called before an agent run sleeps: sessions never persist across a sleep."""
    return {"closed": await close_session(run_id)}
