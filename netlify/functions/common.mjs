// Shared helpers for the KKZZ bulletin functions: HMAC signing, the
// session cookie, GitHub API access, and the page shell (site palette).
import { createHmac, timingSafeEqual } from "node:crypto";

export const REPO = "mmeamazon544/kzzhv";

export const secret = () => process.env.PRIVATE_PAGE_PASSWORD || "";
export const ghToken = () => process.env.GITHUB_DISPATCH_TOKEN || "";

export function hmac(text) {
  return createHmac("sha256", secret()).update(text).digest("hex").slice(0, 32);
}

export function safeEqual(a, b) {
  const ba = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  return ba.length === bb.length && timingSafeEqual(ba, bb);
}

// --- session cookie (set after the password is entered once) -------------
export function makeCookie() {
  const exp = Date.now() + 400 * 24 * 3600 * 1000;
  return `kkzz=${exp}.${hmac("cookie." + exp)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=34560000`;
}

export function cookieOk(req) {
  const raw = req.headers.get("cookie") || "";
  const m = raw.match(/kkzz=(\d+)\.([0-9a-f]+)/);
  if (!m) return false;
  const [, exp, sig] = m;
  return Number(exp) > Date.now() && safeEqual(sig, hmac("cookie." + exp));
}

// --- approval-link tokens: tied to bulletin id + proof revision ----------
export function linkToken(id, rev) {
  return hmac(`link.${id}.${rev}`);
}

export function linkOk(id, rev, sig) {
  return Boolean(id && rev && sig) && safeEqual(sig, linkToken(id, rev));
}

// --- GitHub API ----------------------------------------------------------
async function gh(path, init = {}) {
  const res = await fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${ghToken()}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "kzzhv-bulletin",
      ...(init.headers || {}),
    },
  });
  return res;
}

export async function readFile(path) {
  const res = await gh(`/repos/${REPO}/contents/${path}`);
  if (!res.ok) return { text: "", sha: null };
  const j = await res.json();
  return { text: Buffer.from(j.content, "base64").toString("utf-8"), sha: j.sha };
}

export async function writeFile(path, text, message, sha) {
  const body = {
    message,
    content: Buffer.from(text, "utf-8").toString("base64"),
    committer: { name: "KKZZ private page", email: "shabbat@kzzhv.org" },
  };
  if (sha) body.sha = sha;
  const res = await gh(`/repos/${REPO}/contents/${path}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return res.ok;
}

export async function dispatch(eventType, payload) {
  const res = await gh(`/repos/${REPO}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ event_type: eventType, client_payload: payload }),
  });
  return res.status === 204;
}

// --- page shell ----------------------------------------------------------
export function page(title, body) {
  return new Response(
    `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>${title} — Kehillah Kedoshah Zikhron Zvi</title>
<style>
  body { margin:0; background:#170611; color:#f1dccc; font-family:Georgia,'Times New Roman',serif; line-height:1.6; }
  .wrap { max-width:38rem; margin:0 auto; padding:3rem 1.5rem 4rem; }
  h1 { font-size:1.25rem; letter-spacing:0.18em; text-transform:uppercase; color:#e6c780; border-bottom:1px solid #5a2a48; padding-bottom:0.6rem; font-weight:400; }
  .crest { width:52px; margin-bottom:1rem; }
  label { display:block; letter-spacing:0.22em; text-transform:uppercase; color:#c79f50; font-size:0.72rem; margin:1.4rem 0 0.5rem; }
  textarea, input[type=password], select { width:100%; box-sizing:border-box; font-family:Georgia,serif; font-size:1rem; color:#f1dccc; background:#240a1c; border:1px solid #5a2a48; padding:0.7rem 0.9rem; }
  textarea { min-height:11rem; resize:vertical; }
  button { font-family:Georgia,serif; letter-spacing:0.22em; text-transform:uppercase; font-size:0.85rem; background:#170611; color:#f1dccc; border:1px solid #c79f50; padding:0.9rem 1.8rem; cursor:pointer; margin-top:1.6rem; }
  button:hover { background:#9d345a; }
  .note { color:#9a7273; font-size:0.9rem; font-style:italic; }
  .ok { color:#e6c780; }
  a { color:#e376a3; }
</style></head>
<body><div class="wrap">
<img class="crest" src="/assets/images/logo-deer-blush.png" alt="">
${body}
</div></body></html>`,
    { headers: { "content-type": "text/html; charset=utf-8" } }
  );
}

export function notConfigured() {
  return page("Not ready", "<h1>Not configured</h1><p class='note'>The page password has not been set yet.</p>");
}
