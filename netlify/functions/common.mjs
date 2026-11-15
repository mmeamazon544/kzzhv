// Shared helpers for the KKZZ bulletin functions: HMAC signing, the
// session cookie, GitHub API access, read-only Mailchimp access for the
// Desk, and the page shell (site palette).
import { createHmac, timingSafeEqual } from "node:crypto";

export const REPO = "mmeamazon544/kzzhv";
export const RAW = `https://raw.githubusercontent.com/${REPO}/main`;
export const SITE = "https://kzzhv.org";

export const secret = () => process.env.PRIVATE_PAGE_PASSWORD || "";
export const ghToken = () => process.env.GITHUB_DISPATCH_TOKEN || "";
export const mcKey = () => process.env.MAILCHIMP_API_KEY || "";

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
  // Reads of this public repository work without a token (local testing);
  // writes and dispatches need GITHUB_DISPATCH_TOKEN.
  const auth = ghToken() ? { Authorization: `Bearer ${ghToken()}` } : {};
  const res = await fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      ...auth,
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
  let detail = "";
  if (!res.ok) {
    try {
      detail = (await res.json()).message || "";
    } catch {
      /* keep empty */
    }
  }
  return { ok: res.ok, status: res.status, detail };
}

export async function dispatch(eventType, payload) {
  const res = await gh(`/repos/${REPO}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ event_type: eventType, client_payload: payload }),
  });
  return res.status === 204;
}

// --- Mailchimp, read-only (the Desk's ledger) ----------------------------
// The key is the Netlify variable MAILCHIMP_API_KEY (set by Marc at a
// terminal prompt; never in a file). Nothing here creates or sends.
export async function mcGet(server, path) {
  const res = await fetch(`https://${server}.api.mailchimp.com/3.0${path}`, {
    headers: {
      Authorization: "Basic " + Buffer.from("key:" + mcKey()).toString("base64"),
      "User-Agent": "kzzhv-desk",
    },
    signal: AbortSignal.timeout(7000),
  });
  if (!res.ok) {
    throw new Error(`Mailchimp answered ${res.status} on ${path.split("?")[0]}`);
  }
  return res.json();
}

// A public page's text, or "" when it cannot be fetched in time.
export async function fetchText(url) {
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "kzzhv-desk" },
      signal: AbortSignal.timeout(6000),
    });
    return res.ok ? await res.text() : "";
  } catch {
    return "";
  }
}

// --- page shell ----------------------------------------------------------
export function page(title, body, opts = {}) {
  const wide = opts.wide ? " wide" : "";
  return new Response(
    `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>${title} — Kehillah Kedoshah Zikhron Zvi</title>
<style>
  body { margin:0; background:#170611; color:#f1dccc; font-family:Georgia,'Times New Roman',serif; line-height:1.6; }
  .wrap { max-width:38rem; margin:0 auto; padding:3rem 1.5rem 4rem; }
  .wide .wrap { max-width:64rem; }
  h1 { font-size:1.25rem; letter-spacing:0.18em; text-transform:uppercase; color:#e6c780; border-bottom:1px solid #5a2a48; padding-bottom:0.6rem; font-weight:400; }
  h2 { font-size:0.78rem; letter-spacing:0.24em; text-transform:uppercase; color:#c79f50; margin:2.6rem 0 0.9rem; font-weight:400; }
  .crest { width:52px; margin-bottom:1rem; }
  label { display:block; letter-spacing:0.22em; text-transform:uppercase; color:#c79f50; font-size:0.72rem; margin:1.4rem 0 0.5rem; }
  textarea, input[type=password], select { width:100%; box-sizing:border-box; font-family:Georgia,serif; font-size:1rem; color:#f1dccc; background:#240a1c; border:1px solid #5a2a48; padding:0.7rem 0.9rem; }
  textarea { min-height:11rem; resize:vertical; }
  textarea.short { min-height:6rem; }
  button { font-family:Georgia,serif; letter-spacing:0.22em; text-transform:uppercase; font-size:0.85rem; background:#170611; color:#f1dccc; border:1px solid #c79f50; padding:0.9rem 1.8rem; cursor:pointer; margin-top:1.6rem; }
  button:hover { background:#9d345a; }
  button.primary { background:#611c40; }
  .note { color:#9a7273; font-size:0.9rem; font-style:italic; }
  .ok { color:#e6c780; }
  .yes { color:#e6c780; }
  .no { color:#ff6b6b; }
  .mute { color:#9a7273; }
  .small { font-size:0.86rem; }
  .status { font-size:1.08rem; margin:0.4rem 0 0.8rem; }
  .flash { border-left:3px solid #e6c780; padding:0.6rem 1rem; background:#240a1c; margin:1.2rem 0; }
  .card { border:1px solid #5a2a48; background:#1d0816; padding:1.2rem 1.4rem 1.4rem; }
  .actions form { display:inline-block; margin:0 1.2rem 0 0; vertical-align:top; }
  .actions button { margin-top:0.6rem; }
  .proofbox { max-height:72vh; overflow:auto; border:1px solid #5a2a48; margin-top:1.2rem; background:#000; }
  .proofbox img { width:100%; display:block; }
  .scroll { overflow-x:auto; }
  table.ledger { width:100%; border-collapse:collapse; font-size:0.9rem; }
  .ledger th { text-align:left; font-weight:400; letter-spacing:0.14em; text-transform:uppercase; font-size:0.66rem; color:#c79f50; padding:0.5rem 0.6rem; border-bottom:1px solid #5a2a48; white-space:nowrap; }
  .ledger td { padding:0.55rem 0.6rem; border-bottom:1px solid #3a1630; vertical-align:top; }
  .ledger td.wk { white-space:nowrap; }
  .people { margin:0.3rem 0 0; }
  .people span { display:inline-block; margin:0 1rem 0.2rem 0; }
  a { color:#e376a3; }
</style></head>
<body class="${wide.trim()}"><div class="wrap">
<img class="crest" src="/assets/images/logo-deer-blush.png" alt="">
${body}
</div></body></html>`,
    { headers: { "content-type": "text/html; charset=utf-8" } }
  );
}

export function notConfigured() {
  return page("Not ready", "<h1>Not configured</h1><p class='note'>The page password has not been set yet.</p>");
}
