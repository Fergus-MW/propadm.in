import { createHash } from "node:crypto";
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export async function createCsvSignupStore(path) {
  await mkdir(dirname(path), { recursive: true });
  try {
    await writeFile(path, "created_at,email\n", { flag: "wx" });
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
  }
  const rows = (await readFile(path, "utf8")).split("\n").slice(1);
  const emails = new Set(rows.map((row) => row.split(",")[1]).filter(Boolean));
  return async (email) => {
    if (emails.has(email)) return false;
    emails.add(email);
    try {
      await appendFile(path, `${new Date().toISOString()},${email}\n`);
    } catch (error) {
      emails.delete(email);
      throw error;
    }
    return true;
  };
}

// Cloud Run supplies short-lived credentials; no service-account key is stored.
export function createCloudSignupStore({ bucket, request = fetch }) {
  let token;
  let expiresAt = 0;
  return async (email) => {
    if (!token || Date.now() >= expiresAt) {
      const response = await request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        { headers: { "Metadata-Flavor": "Google" }, signal: AbortSignal.timeout(5000) },
      );
      if (!response.ok) throw new Error(`Signup credentials unavailable (${response.status})`);
      const credentials = await response.json();
      if (!credentials.access_token || !Number.isFinite(credentials.expires_in)) {
        throw new Error("Invalid signup credentials");
      }
      token = credentials.access_token;
      expiresAt = Date.now() + Math.max(0, credentials.expires_in - 60) * 1000;
    }
    const hash = createHash("sha256").update(email).digest("hex");
    const url = new URL(`https://storage.googleapis.com/upload/storage/v1/b/${encodeURIComponent(bucket)}/o`);
    url.search = new URLSearchParams({
      uploadType: "media", name: `signups/${hash}.json`, ifGenerationMatch: "0",
    }).toString();
    const response = await request(url, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ created_at: new Date().toISOString(), email }),
      signal: AbortSignal.timeout(10000),
    });
    // The create-only precondition deduplicates across requests and instances.
    if (response.status === 412) return false;
    if (!response.ok) {
      if (response.status === 401) expiresAt = 0;
      throw new Error(`Signup storage unavailable (${response.status})`);
    }
    return true;
  };
}
