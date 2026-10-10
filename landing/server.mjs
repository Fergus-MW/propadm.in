// Serves the landing page from public/ and saves signup emails to a CSV file.
// Zero dependencies: run with `node landing/server.mjs`.
import { createServer } from "node:http";
import { appendFile, mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname, extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const CSV_HEADER = "created_at,email\n";
const MAX_BODY_BYTES = 2048;
// The first character must be alphanumeric so a saved email can never start a
// spreadsheet formula; the character set also rules out commas and quotes in the CSV.
const EMAIL = /^[a-z0-9][a-z0-9._%+-]{0,63}@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/;
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".jpg": "image/jpeg",
  ".png": "image/png",
};

const send = (res, status, body, headers = {}) => {
  res.writeHead(status, headers);
  res.end(body);
};

const json = (res, status, data, headers = {}) =>
  send(res, status, JSON.stringify(data), { "Content-Type": "application/json; charset=utf-8", ...headers });

const readBody = (req) =>
  new Promise((done, fail) => {
    let size = 0;
    const chunks = [];
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size <= MAX_BODY_BYTES) chunks.push(chunk);
    });
    req.on("end", () =>
      size > MAX_BODY_BYTES
        ? fail(Object.assign(new Error("Request too large"), { status: 413 }))
        : done(Buffer.concat(chunks).toString("utf8"))
    );
    req.on("error", fail);
  });

async function loadSavedEmails(path) {
  await mkdir(dirname(path), { recursive: true });
  try {
    await writeFile(path, CSV_HEADER, { flag: "wx" });
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  const rows = (await readFile(path, "utf8")).split("\n").slice(1);
  return new Set(rows.map((row) => row.split(",")[1]).filter(Boolean));
}

export async function createLandingServer({
  publicDir = join(HERE, "public"),
  signupsPath = join(HERE, ".data", "signups.csv"),
} = {}) {
  const root = resolve(publicDir);
  const emails = await loadSavedEmails(signupsPath);

  async function signup(req, res) {
    if (!(req.headers["content-type"] ?? "").startsWith("application/json")) {
      return json(res, 415, { error: "Send the signup as JSON." });
    }
    let payload;
    try {
      payload = JSON.parse(await readBody(req));
    } catch (error) {
      return error.status === 413
        ? json(res, 413, { error: "That request is too large." })
        : json(res, 400, { error: "That request wasn't valid JSON." });
    }
    // Bots fill in the hidden "website" field. Look successful but save nothing.
    if (payload?.website) return json(res, 201, { ok: true });

    const email = typeof payload?.email === "string" ? payload.email.trim().toLowerCase() : "";
    if (email.length > 254 || !EMAIL.test(email)) {
      return json(res, 400, { error: "That doesn't look like an email address." });
    }
    if (emails.has(email)) return json(res, 200, { ok: true, duplicate: true });

    emails.add(email); // claim it before the write so concurrent duplicates are caught
    try {
      await appendFile(signupsPath, `${new Date().toISOString()},${email}\n`);
    } catch (error) {
      emails.delete(email);
      throw error;
    }
    return json(res, 201, { ok: true });
  }

  async function serveStatic(req, res, pathname) {
    let file;
    try {
      file = resolve(root, `.${decodeURIComponent(pathname)}`);
    } catch {
      return send(res, 400, "Bad request");
    }
    if (file !== root && !file.startsWith(root + sep)) return send(res, 404, "Not found");
    try {
      if ((await stat(file)).isDirectory()) file = join(file, "index.html");
      const body = await readFile(file);
      const type = extname(file);
      res.writeHead(200, {
        "Content-Type": TYPES[type] ?? "application/octet-stream",
        "Cache-Control": type === ".html" ? "no-cache" : "public, max-age=3600",
      });
      res.end(req.method === "HEAD" ? undefined : body);
    } catch (error) {
      if (["ENOENT", "ENOTDIR"].includes(error.code)) return send(res, 404, "Not found");
      throw error;
    }
  }

  return createServer(async (req, res) => {
    try {
      const { pathname } = new URL(req.url, "http://localhost");
      if (pathname === "/healthz") return send(res, 200, "ok", { "Content-Type": "text/plain" });
      if (pathname === "/api/signup") {
        return req.method === "POST"
          ? await signup(req, res)
          : json(res, 405, { error: "Use POST." }, { Allow: "POST" });
      }
      if (req.method === "GET" || req.method === "HEAD") return await serveStatic(req, res, pathname);
      send(res, 405, "Method not allowed", { Allow: "GET, HEAD" });
    } catch (error) {
      console.error(error);
      if (res.headersSent) res.end();
      else json(res, 500, { error: "Something went wrong. Please try again." });
    }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT ?? 3001);
  const host = process.env.HOST ?? "127.0.0.1";
  const signupsPath = resolve(process.env.SIGNUPS_PATH ?? join(HERE, ".data", "signups.csv"));
  const server = await createLandingServer({ signupsPath });
  server.listen(port, host, () => {
    console.log(`Landing page: http://${host}:${port} (signups saved to ${signupsPath})`);
  });
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}
