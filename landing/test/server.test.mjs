import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createLandingServer } from "../server.mjs";

let dir;
let csv;
let server;
let base;

const start = async () => {
  server = await createLandingServer({ publicDir: join(dir, "public"), signupsPath: csv });
  await new Promise((ready) => server.listen(0, "127.0.0.1", ready));
  base = `http://127.0.0.1:${server.address().port}`;
};
const stop = () => new Promise((done) => server.close(done));
const rows = async () => (await readFile(csv, "utf8")).trim().split("\n");
const signup = (body, type = "application/json") =>
  fetch(`${base}/api/signup`, {
    method: "POST",
    headers: { "Content-Type": type },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

before(async () => {
  dir = await mkdtemp(join(tmpdir(), "landing-"));
  await mkdir(join(dir, "public"));
  await writeFile(join(dir, "public", "index.html"), "<h1>Properly</h1>");
  await writeFile(join(dir, "secret.txt"), "outside public");
  csv = join(dir, ".data", "signups.csv");
  await start();
});

after(async () => {
  await stop();
  await rm(dir, { recursive: true, force: true });
});

test("saves a normalised email once, even across restarts", async () => {
  assert.equal((await signup({ email: "  Hello@Example.com " })).status, 201);

  const again = await signup({ email: "hello@example.com" });
  assert.equal(again.status, 200);
  assert.deepEqual(await again.json(), { ok: true, duplicate: true });

  await stop();
  await start();
  assert.deepEqual(await (await signup({ email: "hello@example.com" })).json(), { ok: true, duplicate: true });

  const saved = await rows();
  assert.equal(saved[0], "created_at,email");
  assert.equal(saved.length, 2);
  assert.match(saved[1], /^\d{4}-\d{2}-\d{2}T[\d:.]+Z,hello@example\.com$/);
});

test("rejects bad input without saving anything", async () => {
  const before = await rows();
  for (const email of ["", "not-an-email", "=HYPERLINK()@evil.com", "a,b@example.com", 42]) {
    assert.equal((await signup({ email })).status, 400, `accepted ${email}`);
  }
  assert.equal((await signup("{not json")).status, 400);
  assert.equal((await signup("email=a@example.com", "application/x-www-form-urlencoded")).status, 415);
  assert.equal((await signup({ email: `${"x".repeat(3000)}@example.com` })).status, 413);
  assert.deepEqual(await rows(), before);
});

test("drops honeypot submissions while looking successful", async () => {
  const res = await signup({ email: "bot@example.com", website: "https://spam.example" });
  assert.equal(res.status, 201);
  assert.doesNotMatch(await readFile(csv, "utf8"), /bot@example\.com/);
});

test("serves the page and health check but nothing outside public/", async () => {
  const page = await fetch(`${base}/`);
  assert.equal(page.status, 200);
  assert.match(page.headers.get("content-type"), /text\/html/);
  assert.equal(await page.text(), "<h1>Properly</h1>");

  assert.equal((await fetch(`${base}/healthz`)).status, 200);
  assert.equal((await fetch(`${base}/..%2fsecret.txt`)).status, 404);
  assert.equal((await fetch(`${base}/missing.css`)).status, 404);
  assert.equal((await fetch(`${base}/api/signup`)).status, 405);
});
