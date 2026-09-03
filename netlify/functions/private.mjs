// The private page: the one thing Marc touches week to week.
// Password-protected; saving commits bulletin/announcements.md and
// bulletin/location.md to the repository through the GitHub API.
import {
  cookieOk, makeCookie, notConfigured, page, readFile, safeEqual, secret,
  writeFile,
} from "./common.mjs";

export const config = { path: "/private" };

const LOCATIONS = [
  "Poughkeepsie",
  "Poughkeepsie, no services this week",
  "Shearith Israel, New York",
  "Sha'ar HaShamayim, London (Lauderdale Road)",
  "Sha'ar HaShamayim, London (Bevis Marks)",
  "Mikveh Israel, Philadelphia",
];

const ANN_HEADER = `<!-- This week's notices. Written by the private page; Marc may also edit
this file directly. If there is nothing here but this comment, the bulletin
omits its announcements section. -->
`;

const LOC_HEADER = `<!-- Where the congregation is this week. Written by the private page; Marc
may also edit this file directly. Exactly one of:
${LOCATIONS.join("\n")}
Kippur defaults to New York; Shabbat Bereshit defaults to London. -->
`;

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function stripComments(s) {
  return s.replace(/<!--[\s\S]*?-->/g, "").trim();
}

function loginPage(wrong = false) {
  return page("Private page", `
<h1>Private Page</h1>
${wrong ? "<p class='note'>That was not the password.</p>" : ""}
<form method="POST">
  <input type="hidden" name="action" value="login">
  <label>Password</label>
  <input type="password" name="password" autofocus autocomplete="current-password">
  <button type="submit">Enter</button>
</form>`);
}

async function formPage(saved = false) {
  const ann = stripComments((await readFile("bulletin/announcements.md")).text);
  const loc = stripComments((await readFile("bulletin/location.md")).text) || "Poughkeepsie";
  const options = LOCATIONS.map(
    (l) => `<option${l === loc ? " selected" : ""}>${esc(l)}</option>`
  ).join("");
  return page("Private page", `
<h1>This Week's Bulletin</h1>
${saved ? "<p class='ok'>Saved. The next proof will carry these.</p>" : ""}
<form method="POST">
  <input type="hidden" name="action" value="save">
  <label>Announcements</label>
  <textarea name="announcements" placeholder="One announcement per paragraph; leave empty for none.">${esc(ann)}</textarea>
  <label>This week we are at</label>
  <select name="location">${options}</select>
  <p class="note">Kippur defaults to New York; Shabbat Bereshit defaults to London.</p>
  <button type="submit">Save</button>
</form>`);
}

export default async function handler(req) {
  if (!secret()) return notConfigured();

  if (req.method === "POST") {
    const form = await req.formData();
    const action = form.get("action");

    if (action === "login") {
      if (safeEqual(form.get("password") || "", secret())) {
        return new Response(null, {
          status: 303,
          headers: { location: "/private", "set-cookie": makeCookie() },
        });
      }
      return loginPage(true);
    }

    if (action === "save") {
      if (!cookieOk(req)) return loginPage();
      const ann = String(form.get("announcements") || "").trim();
      const loc = String(form.get("location") || "Poughkeepsie");
      const chosen = LOCATIONS.includes(loc) ? loc : "Poughkeepsie";

      const annFile = await readFile("bulletin/announcements.md");
      const w1 = await writeFile(
        "bulletin/announcements.md",
        ANN_HEADER + (ann ? ann + "\n" : ""),
        "Private page: announcements",
        annFile.sha
      );
      const locFile = await readFile("bulletin/location.md");
      const w2 = await writeFile(
        "bulletin/location.md",
        LOC_HEADER + chosen + "\n",
        "Private page: location",
        locFile.sha
      );
      const bad = [w1, w2].find((w) => !w.ok);
      if (bad) {
        return page("Private page", `
<h1>This Week's Bulletin</h1>
<p class='note'>NOT saved — the repository refused the write
(HTTP ${bad.status}${bad.detail ? ": " + bad.detail : ""}).
Tell Claude; this usually means the GitHub token lacks access.</p>
<p><a href="/private">Back</a></p>`);
      }
      return formPage(true);
    }
  }

  if (!cookieOk(req)) return loginPage();
  return formPage();
}
