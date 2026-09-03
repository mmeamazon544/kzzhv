KZZHV — Kehillah Kedoshah Zikhron Zvi

This repository holds the congregation's website (kzzhv.org) and the
unattended program that produces, proofs, publishes, and mails the weekly
Shabbat bulletin and the festival and fast-day bulletins.

Layout

site/                the website, published to kzzhv.org by Netlify
bulletin/            everything Marc might ever want to touch, all plain text
  announcements.md   this week's notices
  location.md        where the congregation is this week
  voice.md           the brief for the two weekly teachings
  sources.md         the source policy
  luach.md           customs and conventions: times rules, calendar scope,
                     sister congregations, standing lines
  archive/teachings/ every approved teaching, so nothing repeats
  templates/         web and email templates
scripts/             build mechanism
netlify/functions/   private page and approval endpoints
.github/workflows/   proof, approval polling, publish, reminder
docs/brief.md        the full project brief; read it in full before changing
                     anything

The two large Yigdal videos exceed or press against GitHub's file-size
limits and live as assets on the GitHub release tagged site-media; the
Netlify build fetches them into site/assets/video/ before publishing
(scripts/fetch-media.sh), so the deployed site is byte-identical to the
original.

Marc's weekly touchpoint is https://kzzhv.org/private — password-protected;
it saves announcements and the week's location straight into bulletin/ as
commits. Approval and change-request links in each proof email land on
/approve and /changes, token-bound to that proof.

Nothing is ever published to the site and nothing is ever mailed without
Marc's explicit approval for that specific bulletin.
