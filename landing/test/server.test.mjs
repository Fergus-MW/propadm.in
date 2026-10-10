import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createLandingServer } from "../server.mjs";
import { createCloudSignupStore } from "../signup-store.mjs";

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
const person = { name: "Ada Lovelace", company: "Analytical Lets" };
const signup = (body, type = "application/json") =>
  fetch(`${base}/api/signup`, {
    method: "POST",
    headers: { "Content-Type": type },
    body: typeof body === "string" ? body : JSON.stringify({ ...person, ...body }),
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
  assert.equal((await signup({ email: "ok@example.com", name: " " })).status, 400);
  assert.equal((await signup({ email: "ok@example.com", company: "x".repeat(101) })).status, 400);
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

test("cloud signups deduplicate atomically across concurrent instances", async () => {
  const objects = new Map();
  let credentialRequests = 0;
  const request = async (url, options) => {
    if (String(url).startsWith("http://metadata.google.internal/")) {
      credentialRequests++;
      assert.equal(options.headers["Metadata-Flavor"], "Google");
      return Response.json({ access_token: "test-token", expires_in: 3600 });
    }
    assert.equal(options.headers.Authorization, "Bearer test-token");
    const query = new URL(url).searchParams;
    assert.equal(query.get("ifGenerationMatch"), "0");
    const name = query.get("name");
    assert.match(name, /^signups\/[a-f0-9]{64}\.json$/);
    if (objects.has(name)) return new Response(null, { status: 412 });
    objects.set(name, JSON.parse(options.body));
    return Response.json({ generation: "1" });
  };
  const first = createCloudSignupStore({ bucket: "test-signups", request });
  const second = createCloudSignupStore({ bucket: "test-signups", request });
  assert.deepEqual(await Promise.all([first("hello@example.com"), second("hello@example.com")]), [true, false]);
  assert.equal(await first("hello@example.com"), false);
  assert.equal(credentialRequests, 2);
  assert.equal(objects.size, 1);
  assert.equal([...objects.values()][0].email, "hello@example.com");
});

test("cloud storage failures never acknowledge a signup and refresh expired credentials", async () => {
  let credentialRequests = 0;
  let uploadStatus = 401;
  const request = async (url) => {
    if (String(url).startsWith("http://metadata.google.internal/")) {
      credentialRequests++;
      return Response.json({ access_token: "test-token", expires_in: 3600 });
    }
    return new Response(null, { status: uploadStatus });
  };
  const save = createCloudSignupStore({ bucket: "test-signups", request });
  await assert.rejects(save("hello@example.com"), /Signup storage unavailable \(401\)/);
  uploadStatus = 503;
  await assert.rejects(save("hello@example.com"), /Signup storage unavailable \(503\)/);
  uploadStatus = 200;
  assert.equal(await save("hello@example.com"), true);
  assert.equal(credentialRequests, 2);
});

test("the HTTP endpoint normalises emails for a durable signup store", async () => {
  const saved = new Set();
  const durable = await createLandingServer({ signupStore: async (email) => {
    if (saved.has(email)) return false;
    saved.add(email);
    return true;
  } });
  await new Promise((ready) => durable.listen(0, "127.0.0.1", ready));
  try {
    const post = (email) => fetch(`http://127.0.0.1:${durable.address().port}/api/signup`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...person, email }),
    });
    assert.equal((await post(" Hello@Example.com ")).status, 201);
    assert.deepEqual(await (await post("hello@example.com")).json(), { ok: true, duplicate: true });
    assert.deepEqual([...saved], ["hello@example.com"]);
  } finally {
    await new Promise((done) => durable.close(done));
  }
});

test("runtime analytics config exposes only a public ingestion token", async () => {
  for (const token of ["phc_test", "phx_private", ""]) {
    const analyticsServer = await createLandingServer({
      signupStore: async () => true,
      analytics: { projectToken: token, host: "https://us.i.posthog.com", environment: "test" },
    });
    await new Promise((ready) => analyticsServer.listen(0, "127.0.0.1", ready));
    try {
      const config = await fetch(`http://127.0.0.1:${analyticsServer.address().port}/api/analytics-config`);
      assert.equal(config.headers.get("cache-control"), "no-store");
      assert.equal((await config.json()).projectToken, token.startsWith("phc_") ? token : "");
    } finally {
      await new Promise((done) => analyticsServer.close(done));
    }
  }
});

test("new signups post one sanitised chat message; webhook outages still save", async () => {
  const sent = [];
  let webhookStatus = 200;
  const hooked = await createLandingServer({
    signupStore: async (email) => email !== "dupe@example.com",
    webhookUrl: "https://chat.example/hook",
    request: async (url, options) => {
      sent.push({ url, ...JSON.parse(options.body) });
      return new Response(null, { status: webhookStatus });
    },
  });
  await new Promise((ready) => hooked.listen(0, "127.0.0.1", ready));
  try {
    const post = (body) => fetch(`http://127.0.0.1:${hooked.address().port}/api/signup`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    assert.equal((await post({ name: "Ada <users/all>\n", company: "Lets Ltd", email: "Ada@Example.com" })).status, 201);
    assert.deepEqual(sent, [{
      url: "https://chat.example/hook",
      text: "New signup: Ada users/all (Lets Ltd) <mailto:ada@example.com|ada@example.com>",
    }]);
    assert.equal((await post({ ...person, email: "dupe@example.com" })).status, 200);
    assert.equal(sent.length, 1);
    webhookStatus = 500;
    assert.equal((await post({ ...person, email: "down@example.com" })).status, 201);
  } finally {
    await new Promise((done) => hooked.close(done));
  }
});
