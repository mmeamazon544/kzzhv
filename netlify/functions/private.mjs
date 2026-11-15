// The Desk: the one page Marc touches week to week (kzzhv.org/private).
// Password-protected. It shows the current bulletin and its status, with
// Approve and Request-changes on the page itself (the same dispatches the
// proof email's links fire); the proof image and previews of the email and
// the web page; a ledger of the last six weeks' mailings, read live from
// Mailchimp — the congregational send, each family letter and who got it,
// the students on the latest congregational mailing, the people named in
// the Netlify variable DESK_WATCH — and what the live site is showing;
// then the announcements and location form, whose Save commits
// bulletin/announcements.md and bulletin/location.md through the GitHub
// API as before. No address is ever shown; names come from Mailchimp.
import {
  RAW, SITE, cookieOk, dispatch, fetchText, makeCookie, mcGet, mcKey,
  notConfigured, page, readFile, safeEqual, secret, writeFile,
} from "./common.mjs";

export const config = { path: ["/private", "/private/email", "/private/web"] };

const NY = "America/New_York";
const FAMILY = {
  ari: "Ári",
  misha: "Misha and Hannah",
  gabi: "Gabi and Pascale",
  mom: "Mom",
};

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

// ------------------------------------------------------------ small tools
function esc(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function stripComments(s) {
  return s.replace(/<!--[\s\S]*?-->/g, "").trim();
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

// New York wall-clock parts of an instant.
function nyParts(d) {
  const f = new Intl.DateTimeFormat("en-US", {
    timeZone: NY, hourCycle: "h23", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    weekday: "long",
  });
  const p = {};
  for (const { type, value } of f.formatToParts(d)) p[type] = value;
  return p;
}

// ISO date (YYYY-MM-DD) of an instant in New York.
function nyDate(d) {
  const p = nyParts(d);
  return `${p.year}-${p.month}-${p.day}`;
}

// A New York wall time ("20261111T133054" or "2026-11-11T13:30:54") → Date.
function fromNY(s) {
  const m = String(s).match(/(\d{4})-?(\d{2})-?(\d{2})T(\d{2}):?(\d{2}):?(\d{2})?/);
  if (!m) return null;
  if (/[+-]\d{2}:\d{2}$/.test(s)) return new Date(s); // already carries its offset
  const [, Y, M, D, h, mi, se] = m.map(Number);
  let guess = Date.UTC(Y, M - 1, D, h, mi, se || 0);
  for (let i = 0; i < 2; i++) {
    const p = nyParts(new Date(guess));
    const asUtc = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
    guess += Date.UTC(Y, M - 1, D, h, mi, se || 0) - asUtc;
  }
  return new Date(guess);
}

function addDays(iso, n) {
  const d = new Date(iso + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function weekday(iso) {
  return new Date(iso + "T12:00:00Z").getUTCDay(); // 0 Sunday … 6 Saturday
}

function saturdayOnOrAfter(iso) {
  return addDays(iso, (6 - weekday(iso) + 7) % 7);
}

// "21 November 2026"
function fmtDate(iso) {
  const d = new Date(iso + "T12:00:00Z");
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

// "Thursday 19 November" / "Thursday 19 November, 2:12 pm"
function fmtDay(iso) {
  const d = new Date(iso + "T12:00:00Z");
  const wd = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][d.getUTCDay()];
  return `${wd} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

function fmtWhen(d) {
  if (!d || isNaN(d)) return "";
  const p = nyParts(d);
  const h = +p.hour;
  const ampm = h >= 12 ? "pm" : "am";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${p.weekday} ${+p.day} ${MONTHS[+p.month - 1]}, ${hh}:${p.minute} ${ampm}`;
}

function fmtShort(d) {
  const p = nyParts(d);
  const h = +p.hour;
  const ampm = h >= 12 ? "pm" : "am";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${p.weekday.slice(0, 3)} ${+p.day} ${MONTHS[+p.month - 1].slice(0, 3)}, ${hh}:${p.minute} ${ampm}`;
}

function fullName(mf) {
  return `${(mf && mf.FNAME) || ""} ${(mf && mf.LNAME) || ""}`.trim();
}

// ----------------------------------------------------------------- state
async function current() {
  const f = await readFile("bulletin/state/current.json");
  try {
    return JSON.parse(f.text || "{}");
  } catch {
    return {};
  }
}

async function mailchimpConfig() {
  const f = await readFile("program/data/mailchimp.json");
  try {
    return JSON.parse(f.text || "{}");
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------- ledger
async function ledger(cfg, weeks) {
  if (!mcKey()) return { missing: true };
  if (!cfg.audience_id) return { error: "mailchimp.json could not be read from the repository." };
  const server = cfg.server_prefix || "us2";
  const list = cfg.audience_id;

  const kindOf = {};
  if (cfg.proof_segment_id) kindOf[cfg.proof_segment_id] = "proof";
  if (cfg.weekly_segment_id) kindOf[cfg.weekly_segment_id] = "weekly";
  for (const m of Object.keys(FAMILY)) {
    if (cfg[`${m}_segment_id`]) kindOf[cfg[`${m}_segment_id`]] = m;
  }

  const since = new Date(Date.now() - 63 * 86400e3).toISOString();
  const fields = [
    "campaigns.id", "campaigns.send_time", "campaigns.emails_sent",
    "campaigns.settings.subject_line", "campaigns.settings.title",
    "campaigns.recipients.segment_opts.saved_segment_id",
  ].join(",");
  const data = await mcGet(server,
    `/campaigns?list_id=${list}&status=sent&since_send_time=${encodeURIComponent(since)}` +
    `&count=300&sort_field=send_time&sort_dir=DESC&fields=${fields}`);

  const camps = (data.campaigns || []).map((c) => {
    const sent = new Date(c.send_time);
    const seg = c.recipients && c.recipients.segment_opts && c.recipients.segment_opts.saved_segment_id;
    const title = (c.settings && c.settings.title) || "";
    let kind = kindOf[seg] || "other";
    if (/^(PROOF |COPY TO MARC)/.test(title) || /^(PROOF: |Awaiting approval)/.test((c.settings && c.settings.subject_line) || "")) kind = "proof";
    return {
      id: c.id, sent, n: c.emails_sent || 0, kind,
      subject: (c.settings && c.settings.subject_line) || "",
      week: saturdayOnOrAfter(nyDate(sent)),
    };
  }).filter((c) => !isNaN(c.sent));

  const latest = {};
  for (const c of camps) if (!latest[c.kind]) latest[c.kind] = c;

  // Who actually received the latest of each kind (names only).
  const want = ["weekly", ...Object.keys(FAMILY)].filter((k) => latest[k]);
  const sentTo = {};
  const jobs = want.map(async (k) => {
    const r = await mcGet(server,
      `/reports/${latest[k].id}/sent-to?count=300&fields=sent_to.email_address,sent_to.merge_fields,sent_to.status`);
    sentTo[k] = r.sent_to || [];
  });
  let students = null;
  jobs.push((async () => {
    const ts = await mcGet(server, `/lists/${list}/tag-search?name=student`);
    const tag = (ts.tags || []).find((t) => String(t.name).toLowerCase() === "student");
    if (!tag) return;
    const r = await mcGet(server,
      `/lists/${list}/segments/${tag.id}/members?count=300&fields=members.email_address,members.merge_fields`);
    students = r.members || [];
  })());
  await Promise.all(jobs);

  const rows = weeks.map((wk) => {
    const inWeek = camps.filter((c) => c.week === wk);
    const cell = {};
    for (const k of ["weekly", ...Object.keys(FAMILY)]) {
      const hits = inWeek.filter((c) => c.kind === k).sort((a, b) => a.sent - b.sent);
      cell[k] = hits;
    }
    cell.toMarc = inWeek.filter((c) => c.kind === "proof").length;
    cell.other = inWeek.filter((c) => c.kind === "other");
    return { week: wk, cell };
  });

  return { camps, rows, latest, sentTo, students };
}

// ----------------------------------------------------------------- site
async function siteStatus() {
  const [bul, svc] = await Promise.all([fetchText(`${SITE}/bulletin/`), fetchText(`${SITE}/services.html`)]);
  const title = ((bul.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || "")
    .replace(/\s*—\s*Kehillah.*$/s, "").trim();
  const m = svc.match(/Saturday,\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/);
  let iso = "";
  if (m) {
    const mi = MONTHS.findIndex((x) => x.toLowerCase() === m[2].toLowerCase());
    if (mi >= 0) iso = `${m[3]}-${String(mi + 1).padStart(2, "0")}-${String(m[1]).padStart(2, "0")}`;
  }
  return { reachable: Boolean(bul || svc), title, iso };
}

// ------------------------------------------------------------- rendering
function loginPage(wrong = false) {
  return page("Bulletin Desk", `
<h1>Bulletin Desk</h1>
${wrong ? "<p class='note'>That was not the password.</p>" : ""}
<form method="POST">
  <input type="hidden" name="action" value="login">
  <label>Password</label>
  <input type="password" name="password" autofocus autocomplete="current-password">
  <button type="submit">Enter</button>
</form>`);
}

function statusCopy(cur, now) {
  const st = cur.status || "";
  const sendDay = cur.send_day || addDays(cur.id, -1);
  const moment = cur.send_moment ? new Date(cur.send_moment) : fromNY(sendDay + "T06:00:00");
  const passed = now >= moment;
  // A proof whose Shabbat has gone by is stale: it is shown, never offered
  // for approval (approving it would mail last month's bulletin).
  const stale = cur.id < nyDate(now) && st !== "sent";
  let text = "";
  let cls = "";
  if (st === "proofed") {
    text = `Proofed ${fmtWhen(fromNY(cur.proofed_at || cur.rev))}.`;
    if (stale) {
      text += ` Its Shabbat passed without approval; nothing went out. The next proof supersedes it.`;
      cls = "no";
    } else if (passed) {
      text += ` Awaiting your word.`;
      text += ` Its mailing morning has come: approving now publishes and sends it within the hour.`;
    } else {
      text += ` Awaiting your word. Once approved it goes out on ${fmtDay(sendDay)}, in the morning.`;
    }
  } else if (st === "approved" && stale) {
    text = `Approved ${fmtWhen(new Date(cur.approved_at))}, but its Shabbat passed before it went out. Tell Claude.`;
    cls = "no";
  } else if (st === "approved") {
    text = `Approved ${fmtWhen(new Date(cur.approved_at))}. ` +
      (passed ? "Its mailing morning has come; the next run publishes and sends it."
              : `Goes out on ${fmtDay(sendDay)}, in the morning.`);
    cls = "yes";
  } else if (st === "published") {
    text = `Published to the site ${fmtWhen(new Date(cur.published_at))}; the email follows in the same run.`;
    cls = "yes";
  } else if (st === "sent") {
    text = `Published and sent ${fmtWhen(new Date(cur.sent_at))}` +
      (cur.dry_run ? " — a dry run, to you only." : " to the congregation.");
    cls = "yes";
  } else {
    text = "No bulletin has been proofed yet.";
  }
  return { text, cls, stale, moment, sendDay };
}

function thisWeekCard(cur, now, flash) {
  if (!cur.id) {
    return `<div class="card"><p class="status">No bulletin is in hand yet.</p></div>`;
  }
  const s = statusCopy(cur, now);
  const png = `${RAW}/bulletin/state/${esc(cur.id)}/proof.png?v=${esc(cur.rev)}`;
  const pdf = `${RAW}/bulletin/state/${esc(cur.id)}/proof.pdf?v=${esc(cur.rev)}`;
  const canApprove = cur.status === "proofed" && !s.stale;
  const canChange = (cur.status === "proofed" || cur.status === "approved") && !s.stale;
  let actions = "";
  if (canApprove || canChange) {
    actions = `<div class="actions">
${canApprove ? `<form method="POST">
  <input type="hidden" name="action" value="approve">
  <input type="hidden" name="id" value="${esc(cur.id)}">
  <input type="hidden" name="rev" value="${esc(cur.rev)}">
  <button type="submit" class="primary">Approve this bulletin</button>
</form>` : ""}
</div>
${canChange ? `<form method="POST">
  <input type="hidden" name="action" value="changes">
  <input type="hidden" name="id" value="${esc(cur.id)}">
  <input type="hidden" name="rev" value="${esc(cur.rev)}">
  <label>Request changes</label>
  <textarea class="short" name="instructions" placeholder="Plain English: Musaf at 11:15, not 11:00; add an announcement about the sukka raising; make the halakha teaching shorter."></textarea>
  <button type="submit">Send and regenerate</button>
  <p class="note small">Service times, announcements, the banner, greetings, and the teachings change from here; a fresh proof follows in about ten minutes, here and in your inbox. Page design and layout go to Claude directly.</p>
</form>` : ""}`;
  }
  const note = cur.note ? `<p class="note">Not changed from the last proof cycle — bring it to Claude: ${esc(cur.note)}</p>` : "";
  return `<div class="card">
<p class="mute small" style="margin:0 0 0.2rem; letter-spacing:0.18em; text-transform:uppercase; font-size:0.66rem;">Bulletin for Shabbat ${esc(fmtDate(cur.id))}</p>
<p style="margin:0; font-size:1.25rem; color:#e6c780;">${esc(cur.title || cur.id)}</p>
<p class="status ${s.cls}">${esc(s.text)}</p>
${flash ? `<div class="flash">${esc(flash)}</div>` : ""}
${note}
${actions}
<p class="small" style="margin-top:1.4rem;">
  <a href="/private/email">The email as recipients see it</a> &nbsp;·&nbsp;
  <a href="/private/web">The web page</a> &nbsp;·&nbsp;
  <a href="${pdf}">PDF of the page</a> &nbsp;·&nbsp;
  <a href="${png}">Image of the page</a>
</p>
<div class="proofbox"><img src="${png}" alt="Proof of the bulletin page" loading="lazy"></div>
</div>`;
}

function people(list, cls = "yes") {
  if (!list || !list.length) return `<span class="mute">no one on record</span>`;
  return list.map((p) => `<span class="${cls}">${esc(p)} ✓</span>`).join("");
}

function ledgerSection(led, weeks, thisSat) {
  if (led.missing) {
    return `<div class="card"><p class="note">Mailchimp is not connected to the Desk yet. Once the Netlify variable
MAILCHIMP_API_KEY is set (Claude has the one-line command), this table fills itself from
Mailchimp's own records of what went out and to whom.</p></div>`;
  }
  if (led.error) {
    return `<div class="card"><p class="note">The ledger could not be read just now: ${esc(led.error)}. Reload in a minute.</p></div>`;
  }
  const cellHtml = (hits) => {
    if (!hits.length) return `<span class="mute">—</span>`;
    return hits.map((c) => `<span class="yes">✓</span> ${esc(fmtShort(c.sent))} <span class="mute">· ${c.n}</span>`).join("<br>");
  };
  const head = ["Shabbat", "Congregation", ...Object.values(FAMILY), "To you"]
    .map((h) => `<th>${esc(h)}</th>`).join("");
  const body = led.rows.map((r) => {
    const label = r.week === thisSat
      ? `Shabbat ${fmtDate(r.week)}<br><span class="mute small">this week</span>`
      : `Shabbat ${fmtDate(r.week)}`;
    const extra = r.cell.other.length
      ? `<br><span class="mute small">+ ${r.cell.other.length} other mailing${r.cell.other.length === 1 ? "" : "s"}</span>` : "";
    return `<tr><td class="wk">${label}</td><td>${cellHtml(r.cell.weekly)}${extra}</td>` +
      Object.keys(FAMILY).map((k) => `<td>${cellHtml(r.cell[k])}</td>`).join("") +
      `<td class="mute">${r.cell.toMarc || "—"}</td></tr>`;
  }).join("\n");

  // Who received the latest congregational mailing.
  let who = "";
  const w = led.latest.weekly;
  if (w) {
    const got = led.sentTo.weekly || [];
    const gotEmails = new Set(got.map((p) => String(p.email_address).toLowerCase()));
    const watch = String(process.env.DESK_WATCH || "").split(/[;,]/).map((s) => s.trim()).filter(Boolean);
    const watchHtml = watch.length
      ? watch.map((name) => {
          const hit = got.find((p) => fullName(p.merge_fields).toLowerCase().includes(name.toLowerCase()) ||
                                      String(p.email_address).toLowerCase() === name.toLowerCase());
          return hit
            ? `<span class="yes">${esc(name)} ✓</span>`
            : `<span class="no">${esc(name)} — not on this mailing</span>`;
        }).join("")
      : `<span class="mute">set the Netlify variable DESK_WATCH to name the people to watch for</span>`;
    let studentsHtml;
    if (led.students === null) studentsHtml = `<span class="mute">no "student" tag in Mailchimp</span>`;
    else if (!led.students.length) studentsHtml = `<span class="mute">no one carries the student tag</span>`;
    else {
      const n = led.students.filter((s) => gotEmails.has(String(s.email_address).toLowerCase())).length;
      studentsHtml = `<span class="${n === led.students.length ? "yes" : "no"}">${n} of ${led.students.length} received it</span> ` +
        led.students.map((s) => {
          const ok = gotEmails.has(String(s.email_address).toLowerCase());
          return `<span class="${ok ? "yes" : "no"}">${esc(fullName(s.merge_fields) || "(no name on file)")} ${ok ? "✓" : "✗"}</span>`;
        }).join("");
    }
    who = `<h2>The latest congregational mailing</h2>
<div class="card">
<p style="margin:0 0 0.6rem;">${esc(w.subject)} <span class="mute small">· ${esc(fmtWhen(w.sent))} · ${w.n} sent</span></p>
<p class="people"><span class="mute small" style="letter-spacing:0.14em; text-transform:uppercase;">Watched</span><br>${watchHtml}</p>
<p class="people"><span class="mute small" style="letter-spacing:0.14em; text-transform:uppercase;">Students</span><br>${studentsHtml}</p>
</div>`;
  }

  // The family letters: who received each latest one.
  const fam = Object.keys(FAMILY).filter((k) => led.latest[k]).map((k) => {
    const c = led.latest[k];
    const names = (led.sentTo[k] || []).map((p) => (p.merge_fields && p.merge_fields.FNAME) || fullName(p.merge_fields) || "(no name on file)");
    return `<p class="people"><span class="mute small" style="letter-spacing:0.14em; text-transform:uppercase;">${esc(FAMILY[k])}</span>
<span class="mute small">· ${esc(fmtShort(c.sent))}</span><br>${people(names)}</p>`;
  }).join("");
  const famHtml = fam ? `<h2>The latest family letters</h2><div class="card">${fam}</div>` : "";

  return `<div class="card scroll"><table class="ledger"><thead><tr>${head}</tr></thead><tbody>
${body}
</tbody></table>
<p class="note small" style="margin:0.9rem 0 0;">Each mark is Mailchimp's own record of a send, with the New York time and how many addresses it went to. "To you" counts the proofs, reminders, and copies that reached your inbox that week.</p></div>
${who}
${famHtml}`;
}

function siteSection(site, thisSat) {
  if (!site.reachable) {
    return `<div class="card"><p class="note">kzzhv.org could not be reached just now.</p></div>`;
  }
  const prevSat = addDays(thisSat, -7);
  let verdict;
  if (!site.iso) {
    verdict = `<span class="no">The services page shows no Shabbat date.</span>`;
  } else if (site.iso === thisSat) {
    verdict = `<span class="yes">This week's bulletin is live. ✓</span>`;
  } else if (site.iso === prevSat) {
    verdict = `<span class="yes">Last Shabbat's bulletin is live; this week's replaces it on its mailing day. ✓</span>`;
  } else {
    const behind = Math.round((new Date(prevSat) - new Date(site.iso)) / (7 * 86400e3));
    verdict = `<span class="no">The site is ${behind} week${behind === 1 ? "" : "s"} behind.</span>`;
  }
  return `<div class="card">
<p style="margin:0 0 0.4rem;">Live now: <strong>${esc(site.title || "(no bulletin page)")}</strong>${site.iso ? ` — Shabbat of ${esc(fmtDate(site.iso))}` : ""}</p>
<p style="margin:0;">${verdict} <span class="small"><a href="${SITE}/bulletin/">bulletin page</a> &nbsp;·&nbsp; <a href="${SITE}/services.html">services page</a></span></p>
</div>`;
}

function comingUp(cur, today, thisSat) {
  const lines = [];
  const inHand = cur.id === thisSat && cur.status && cur.status !== "sent";
  const nextSat = (cur.id === thisSat && cur.status === "sent") || today === thisSat ? addDays(thisSat, 7) : thisSat;
  if (inHand) {
    lines.push(`This week's bulletin is in hand above; it goes out on ${fmtDay(cur.send_day || addDays(cur.id, -1))}, in the morning.`);
  }
  if (!inHand || nextSat !== thisSat) {
    lines.push(`Next bulletin: Shabbat ${fmtDate(nextSat)}. Its proof lands here and in your inbox on ${fmtDay(addDays(nextSat, -2))}, during the afternoon or evening; it goes out on ${fmtDay(addDays(nextSat, -1))}, in the morning, once approved.`);
  }
  lines.push(`Festival weeks run earlier by the same rule: the proof comes the day before the first eve, and the mail goes out on the eve.`);
  lines.push(`The family letters go out every Friday morning, and on festival eves, on their own.`);
  return `<div class="card">${lines.map((l) => `<p style="margin:0 0 0.5rem;">${esc(l)}</p>`).join("")}</div>`;
}

async function noticesForm(saved) {
  const ann = stripComments((await readFile("bulletin/announcements.md")).text);
  const loc = stripComments((await readFile("bulletin/location.md")).text) || "Poughkeepsie";
  const options = LOCATIONS.map(
    (l) => `<option${l === loc ? " selected" : ""}>${esc(l)}</option>`
  ).join("");
  return `<div class="card">
${saved ? "<p class='ok'>Saved. The next proof will carry these.</p>" : ""}
<form method="POST">
  <input type="hidden" name="action" value="save">
  <label>Announcements</label>
  <textarea name="announcements" placeholder="One announcement per paragraph; leave empty for none.">${esc(ann)}</textarea>
  <label>This week we are at</label>
  <select name="location">${options}</select>
  <p class="note">Kippur defaults to New York; Shabbat Bereshit defaults to London.</p>
  <button type="submit">Save</button>
</form></div>`;
}

async function desk({ flash = "", saved = false } = {}) {
  const now = new Date();
  const today = nyDate(now);
  const thisSat = saturdayOnOrAfter(today);
  const weeks = [];
  for (let i = 0; i < 6; i++) weeks.push(addDays(thisSat, -7 * i));

  const [cur, cfg] = await Promise.all([current(), mailchimpConfig()]);
  let led;
  const [ledResult, site, notices] = await Promise.all([
    ledger(cfg, weeks).catch((e) => ({ error: e.message || String(e) })),
    siteStatus(),
    noticesForm(saved),
  ]);
  led = ledResult;

  return page("Bulletin Desk", `
<h1>Bulletin Desk</h1>
<p class="mute small" style="margin-top:-0.4rem;">Kehillah Kedoshah Zikhron Zvi · what is in hand, what went out, what the site shows. Today is ${esc(fmtDay(today))}.</p>

<h2>This week</h2>
${thisWeekCard(cur, now, flash)}

<h2>What went out — the last six weeks</h2>
${ledgerSection(led, weeks, thisSat)}

<h2>The website</h2>
${siteSection(site, thisSat)}

<h2>Coming up</h2>
${comingUp(cur, today, thisSat)}

<h2>This week's notices</h2>
${notices}`, { wide: true });
}

// ------------------------------------------------------------- previews
async function preview(kind) {
  const cur = await current();
  if (!cur.id) return page("Bulletin Desk", "<h1>Bulletin Desk</h1><p class='note'>No bulletin is in hand.</p>");
  const f = await readFile(`bulletin/state/${cur.id}/${kind}.html`);
  if (!f.text) return page("Bulletin Desk", "<h1>Bulletin Desk</h1><p class='note'>That file is not in the repository yet.</p>");
  return new Response(f.text, {
    headers: { "content-type": "text/html; charset=utf-8", "x-robots-tag": "noindex, nofollow" },
  });
}

// --------------------------------------------------------------- handler
export default async function handler(req) {
  if (!secret()) return notConfigured();
  const url = new URL(req.url);

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

    if (!cookieOk(req)) return loginPage();

    if (action === "approve" || action === "changes") {
      const id = String(form.get("id") || "");
      const rev = String(form.get("rev") || "");
      const cur = await current();
      if (id !== cur.id || rev !== cur.rev) {
        return desk({ flash: "That proof has been superseded by a newer one; this page now shows the latest." });
      }
      if (cur.id < nyDate(new Date()) && cur.status !== "sent") {
        return desk({ flash: "That bulletin's Shabbat has passed; it cannot be approved or changed now." });
      }
      if (action === "approve") {
        if (cur.status !== "proofed") {
          return desk({ flash: `This bulletin is already ${cur.status}; nothing more to approve.` });
        }
        const ok = await dispatch("bulletin-approve", { id, rev });
        return desk({
          flash: ok
            ? "Approved. The approval is being recorded (allow a minute); the bulletin goes out on its mailing morning, or at once if that morning has passed."
            : "The repository could not be reached; try again in a minute.",
        });
      }
      const instructions = String(form.get("instructions") || "").trim();
      if (!instructions) return desk({ flash: "Write what should change, then send." });
      if (cur.status !== "proofed" && cur.status !== "approved") {
        return desk({ flash: `This bulletin is already ${cur.status}; changes now need Claude.` });
      }
      const ok = await dispatch("bulletin-changes", { id, rev, instructions });
      return desk({
        flash: ok
          ? "Understood. A fresh proof is being prepared; it appears here and in your inbox in about ten minutes."
          : "The repository could not be reached; try again in a minute.",
      });
    }

    if (action === "save") {
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
        return page("Bulletin Desk", `
<h1>Bulletin Desk</h1>
<p class='note'>NOT saved — the repository refused the write
(HTTP ${bad.status}${bad.detail ? ": " + esc(bad.detail) : ""}).
Tell Claude; this usually means the GitHub token lacks access.</p>
<p><a href="/private">Back</a></p>`);
      }
      return desk({ saved: true });
    }
  }

  if (!cookieOk(req)) return loginPage();
  if (url.pathname === "/private/email") return preview("email");
  if (url.pathname === "/private/web") return preview("web");
  return desk();
}
