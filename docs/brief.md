KKZZ Bulletin — project brief

This file is the complete hand-off from a claude.ai conversation in which every decision below was made with Marc. Treat it as settled unless Marc changes it. Read it in full before doing anything.

What this is

An unattended program that produces, proofs, publishes, and mails the weekly Shabbat bulletin and the festival and fast-day bulletins of Kehillah Kedoshah Zikhron Zvi (KKZZ), a small traditional egalitarian home synagogue in the Hudson Valley that prays in the Western Sephardic rite. Site: https://kzzhv.org (currently https://kzzhv.netlify.app). Marc is the person you are working for; he runs the congregation's site and communications.

Each bulletin carries the dates, parashah and readings, times, observances, announcements, and two short teachings, one halakhic and one aggadic, in a voice that is inclusive and egalitarian while traditional in the Western Sephardic high style.

How Marc works with you

Plain text in replies. No bold, no bullets, no headers, no summaries, no meta-commentary, no preamble. Real line breaks for lists.
No unsolicited suggestions. Do what was asked; ask when you must.
Ask one question at a time. Give the concrete answer you would pick alongside the question.
Never invent a source, citation, page number, or book. Label anything unverified as unverified.
No Chabad material of any kind, anywhere, ever: not Chabad.org, not sites that repackage it, not Kehot, not Sichos in English, not the Chabad literature from Shneur Zalman of Liadi onward (Tanya, Shulhan Arukh HaRav, Hayom Yom, the Rebbes' sichot and ma'amarim). Do not use Chabad.org's zemanim either.
Marc finds API keys confusing. When a key is needed, tell him exactly which page and button in the other service, then have him paste it at a terminal prompt (gh secret set NAME, or netlify env:set) so it never lives in a file. Never write a key into any file. Never echo a key back.
Mac-safe filenames for documents Marc will handle: AUTHOR Title, plain spaces, no punctuation. Code files follow normal conventions.
Hebrew transliteration follows Sephardic pronunciation (Shabbat, Sukkot, Habdala, Selihot, Kippur). The congregation's own spellings on the site win over yours.
Never publish to the site and never send mail without Marc's explicit approval for that specific bulletin. The approval mechanism below is the only path to publication. During development, never send anything to the real list; use Marc's own address only.
Never delete, restructure, or restyle the existing site pages. The bulletin is added alongside them.
Interaction on this project is casual and quick; results are formal and finished.

Fixed facts

Site source: a zip of the current site is on Marc's Mac at /Volumes/DB PRIMARY LOCAL/Dropbox/15-WEBSITES/CURRENT KKZZ WEBSITE 09-02-2026.zip The site was deployed to Netlify by drag and drop. There is no Git repository yet. Netlify project name: kzzhv.
Domain: kzzhv.org, registered through Netlify on 3 September 2026, DNS managed in Netlify. Records for kzzhv.org and www.kzzhv.org already point to kzzhv.netlify.app. IPv6 left off.
Secretary's address, for RSVPs and replies: kehillatzikhronzvi@gmail.com
Bulletin sending address: shabbat@kzzhv.org (authenticated through Mailchimp; no mailbox exists or is needed). Reply-To: the secretary's Gmail.
Mailchimp: account exists, created 3 September 2026. Audience name not yet known; ask Marc, or use the only one if there is only one.
Anthropic: Marc has an Anthropic Console account with credit. He will create a key named KKZZ bulletin when you tell him to. Do not use identity federation.
GitHub: not yet known whether Marc has an account. Ask. Create the repository under his account.
Location for all times: Poughkeepsie, NY, 41.70 N, 73.92 W, America/New_York.
Sister congregations, where the community is sometimes guests: Congregation Shearith Israel, New York (Kippur, by default); Sha'ar HaShamayim, London, at Lauderdale Road or Bevis Marks (Shabbat Bereshit, by default); Mikveh Israel, Philadelphia (various Shabbatot).

Architecture (decided)

One GitHub repository holds the whole site and the program. Netlify is linked to it; every push deploys. Drag-and-drop stops.
GitHub Actions is the scheduler and the worker. Nothing runs on Marc's Mac.
Netlify Functions on the same site provide the private page and the approval endpoints. They trigger GitHub workflows by repository_dispatch using a fine-grained GitHub token stored as a Netlify environment variable.
Mailchimp holds the list and sends the congregational email. The program sends its own fully designed HTML through the Mailchimp API; no Mailchimp template.
Proof emails to Marc go by the route that needs no additional service or key: first choice, a Mailchimp campaign to a Proof segment or one-member audience containing only Marc.
Calendar (dates, parashiyot, holidays, Hebrew dates) from Hebcal's JSON API. Zemanim computed locally from standard solar formulas so the rules below can be applied exactly; Hebcal may be used to cross-check.
Teachings drafted by the Claude API from voice.md and sources.md, with every citation verified against Sefaria before use.
Rendering: one HTML template for the web page, one table-based inline-CSS template for the email, Playwright for the proof image and PDF.
Secrets: ANTHROPIC_API_KEY, MAILCHIMP_API_KEY, MAILCHIMP_AUDIENCE_ID (GitHub secrets); GITHUB_DISPATCH_TOKEN and PRIVATE_PAGE_PASSWORD (Netlify env vars).

Repository layout (target)

site/ — the existing site, untouched except for the addition of the bulletin pages and one navigation link, the latter only after Marc approves the wording and position.
site/bulletin/index.html — the current bulletin. site/bulletin/YYYY-MM-DD-slug/index.html — the archive.
bulletin/announcements.md — this week's notices. Written by the private page; Marc can also edit it directly.
bulletin/voice.md — the brief for the teachings.
bulletin/sources.md — the source policy.
bulletin/luach.md — customs and conventions (times rules, calendar scope, sister congregations, standing lines).
bulletin/archive/teachings/ — every approved teaching, so nothing repeats and a library accumulates.
bulletin/templates/ — web and email templates, set once against the site's own CSS.
netlify/functions/ — private page, approve, changes, announcements.
.github/workflows/ — proof, poll-for-approval, publish, reminder.
Anything Marc might ever want to touch lives in bulletin/ as plain text. Everything else is mechanism.

Schedule

Shabbat: proof at 6:00 am Thursday (America/New_York; GitHub cron is UTC, so handle daylight saving by running the workflow at both candidate UTC hours and checking local time). Publish and send at 6:00 pm Thursday once approved; if approval comes later, publish and send immediately on approval. Reminder to Marc at 5:00 pm if not yet approved.
Festivals and fasts: same pattern, proof at 6:00 am two days before the eve. If a festival or fast falls within two days of Shabbat or another festival, one bulletin covers the cluster and the earliest proof date applies.
Nothing is ever published or sent without approval.

Approval flow

Proof email to Marc contains: the finished email exactly as recipients will see it; the web page as PNG and PDF attachments or links; at the top, two links: Approve, and Request changes.
Approve: one tap. Marks the bulletin approved; the 6:00 pm workflow (or an immediate run if after 6:00 pm) publishes and sends.
Request changes: opens a plain page with one text box. Marc writes instructions in plain English ("move the memorial notice above the class listing; cite the Zohar passage instead of the midrash"). Submitting regenerates the bulletin with those instructions and sends a fresh proof within minutes.
Links carry a signed token tied to the bulletin's identifier and date so they cannot be replayed.

The private page

One page on the site, password protected (PRIVATE_PAGE_PASSWORD), reachable from a bookmark. It is the only thing Marc touches week to week.
Fields: a box for this week's announcements; a line "This week we are at" with the choices Poughkeepsie; Poughkeepsie, no services this week; Shearith Israel, New York; Sha'ar HaShamayim, London (Lauderdale Road or Bevis Marks); Mikveh Israel, Philadelphia. Kippur defaults to New York; Shabbat Bereshit defaults to London.
Saving writes bulletin/announcements.md and the week's location to the repository (a commit through the GitHub API), which the proof workflow reads.

Bulletin contents, in order

1. Crest and congregation name, in the site's own style.
2. If away: "This Shabbat the congregation is guests of ..." naming the host. If "no services this week", say so plainly.
3. Shabbat or festival name, parashah, Gregorian and Hebrew dates.
4. Times, headed exactly: Shabbat times for Poughkeepsie, NY (41.70° N, 73.92° W). Times are ALWAYS Poughkeepsie, even when the congregation is away.
5. Readings: Torah with the aliyot, maftir, haftarah; note Sephardic haftarah where it differs.
6. Observances falling in the week: Rosh Hodesh (announced the preceding Shabbat), fasts, minor days, Selihot, and so on.
7. Home weeks only: the kiddush and address lines as the site handles them, and this line verbatim: To RSVP and to register food issues and avoidances, kindly contact the Congregation's secretary at kehillatzikhronzvi@gmail.com Away weeks drop the kiddush, address, and RSVP lines only.
8. Announcements from announcements.md.
9. Halakhic teaching.
10. Aggadic teaching.
11. Colophon: Hebcal attribution as Hebcal requires; source links; Mailchimp's unsubscribe merge tag in the email.

Times rules

Candle lighting: 18 minutes before sunset, printed with sunset shown, exactly in this form: Candle lighting 7:05 pm (18 minutes before sunset; sunset 7:23 pm)
End of Shabbat and festivals: follow Congregation Shearith Israel, New York, which uses the earliest conventional Orthodox ending. Their published figures: Shabbat 4–5 September 2026, candles 7:05 pm, Habdala 7:58 pm (about 37 minutes after sunset that week); 17 July 2021, Habdala 9:07 pm. These fit a fixed solar depression of roughly 7.5°, not a fixed number of minutes. Calibrate against a full year of their published times (shearithisrael.org: the home page shows the current week; the calendar page and archived PDF handouts show others) so the rule reproduces theirs to the minute for New York, then apply the same rule to the Poughkeepsie sky. Record the fitted rule in luach.md with the data used.
Festivals: candle lighting on the eve as above; second-day lighting after the stated end of the first day; fast beginning and end per the same conventions; state the rule used in luach.md.
Print all times to the minute, 12-hour clock, lowercase am/pm.

Calendar scope

Every Shabbat.
Every festival and every fast: Rosh Hashana, Kippur, Sukkot, Shemini Atseret, Simhat Torah, Hanukkah, Purim, Pesah, Shabuot, Tish'a Be'Ab, the minor fasts (Gedalia, Tebet, Esther, Tammuz), plus Tu BiShbat and Lag LaOmer, each with its own bulletin unless clustered per the schedule rule.
Rosh Hodesh, Purim Katan, Pesah Sheni: announced in the preceding Shabbat bulletin, no separate bulletin.
No modern days (Yom HaShoah, Yom HaZikaron, Yom HaAtsmaut, Yom Yerushalayim).
Second-day Yom Tob observed (diaspora).

Design

Match the existing site exactly: its typefaces, palette, spacing, and the deer crest (site/assets/images/logo-deer-blush.png). Read the site's CSS from the zip before writing any template.
The email must look like the site: table-based HTML, inline CSS, images hosted on kzzhv.org, tested in Gmail and Apple Mail rendering, graceful in plain text.
Restrained, dignified, unhurried. No badges, no emoji, no marketing furniture.

voice.md and sources.md

The operative texts live at bulletin/voice.md and bulletin/sources.md in this repository.

Build order

1. Confirm GitHub account; create the repository; unzip the site into site/; verify it deploys from Git on Netlify at kzzhv.org with HTTPS; confirm it looks identical to the drag-and-drop version before anything else.
2. Calendar and zemanim engine, including the Shearith Israel calibration. Show Marc a plain-text year of Shabbat times to approve.
3. Bulletin generator without teachings; templates matched to the site; proof image and PDF. Show Marc a proof.
4. Teachings pipeline with Sefaria verification and Keter Shem Tob retrieval. Show Marc two sample teachings.
5. Private page and approval endpoints.
6. Mailchimp: domain authentication records for kzzhv.org (give Marc the exact records to add in Netlify DNS), audience wiring, proof segment, first test send to Marc only.
7. Workflows and schedule; a full dry run end to end with Marc's address as the only recipient.
8. Hand-over: one page of instructions for Marc, plain text, and a note in luach.md of every convention chosen.

Keys are requested only at the step that needs them: Anthropic at step 4, GitHub token and page password at step 5, Mailchimp at step 6.

Open questions for Marc (ask one at a time, when reached)

Mailchimp Audience name.
GitHub username, or whether an account must be created.
Standing service times and the kiddush and address wording for home weeks, or confirmation that these come from the site's Services and Kiddush pages.
Wording and position of the bulletin link in the site navigation.
Whether the archive of past bulletins should be public.

Deviations from the brief, with reasons

The Rome Yigdal video (assets/video/yigdal-rome-tempio-maggiore-hoshana-rabbah.mp4, 157 MB) exceeds GitHub's hard 100 MB per-file limit and cannot be pushed. Both large Yigdal mp4s therefore live as assets on the GitHub release tagged site-media, and the Netlify build downloads them into site/assets/video/ before publishing (scripts/fetch-media.sh, wired in netlify.toml). The deployed site is byte-identical to the original. Git LFS was rejected because its free bandwidth quota (1 GB/month) would be exhausted by weekly builds.
