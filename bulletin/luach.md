Luach — customs and conventions of Kehillah Kedoshah Zikhron Zvi

This file records every convention the bulletin program follows, so that the
program's behavior can be read in one place. Rules marked PENDING await
calibration or a decision from Marc and are not yet in force.

Location and clock

All times are computed for Poughkeepsie, NY, 41.70° N, 73.92° W, in
America/New_York, and are ALWAYS Poughkeepsie times, even when the
congregation is guests elsewhere. The times section is headed exactly:

Shabbat times for Poughkeepsie, NY (41.70° N, 73.92° W)

Times print to the minute, 12-hour clock, lowercase am and pm.

Candle lighting

18 minutes before sunset. In the times block, candle lighting and sunset
are two separate lines of equal weight — candle lighting (noted "18
minutes to sunset") first, then sunset, then Habdala. The printed sunset
is the computed sunset rounded to the nearest minute, and the candle time
is 18 minutes before the printed sunset, so the arithmetic on the page is
exact. (Layout revised 3 September 2026 at Marc's direction, superseding
the brief's single-line parenthetical form.)

End of Shabbat and festivals

CALIBRATED 3 September 2026. The congregation follows Congregation
Shearith Israel, New York. Their published times do not fit a fixed solar
depression (the working hypothesis in the project brief): winter weeks run
six to nine minutes earlier than any depression that fits the equinoxes.
They fit a seasonal rule:

End of Shabbat = sunset plus 33.75 seasonal minutes, rounded up to the
whole minute, where one seasonal minute is one sixtieth of one twelfth of
that day's sunrise-to-sunset span (standard refracted sunrise and sunset).

Data: 157 independent Shabbatot of Shearith Israel's own published Habdala
times, October 2020 through September 2026 (continuous weekly coverage
August 2024 onward), gathered from their website, their weekly handout
PDFs, and Wayback Machine snapshots of their pages; the dataset is
program/data/shearith-times.csv and the verification tool is
program/calibrate_habdala.py. Computed for New York, the rule reproduces
their published figure to the minute in 64% of those weeks and to within
one minute in 93%, and comes out earlier than their figure in only 12 of
the 157 (11 of them by a single minute; the one large residual is a
misprint on their own 6 February 2021 page). The residue traces to their own
generator's coarser sunsets, which differ from precise astronomy by a
minute in roughly a third of the sampled weeks; exact reproduction is
therefore not attainable in principle. The upward rounding is chosen so the
printed end of Shabbat practically never falls earlier than their
convention. Both anchor figures in the project brief reproduce exactly
(4–5 September 2026: Habdala 7:58 pm; 17 July 2021: 9:07 pm).

The same nightfall rule, computed on the Poughkeepsie sky, ends festivals
and Kippur. Festival candle lighting on the eve is as above; second-day
lighting is after the stated end of the first day, from a flame lit before
the festival. Fast beginnings: dawn at solar depression 16.1° (the
classical alot hashachar equivalent), rounded down to the minute —
PROVISIONAL, chosen 3 September 2026, pending calibration against
Shearith Israel's published fast times.

Festival bulletins (built 3 September 2026)

A festival or fast within two days of Shabbat or another festival joins
one cluster bulletin (the brief's rule). When Shabbat is itself a festival
day, the bulletin is the festival's (title "Rosh Hashana 5787"); when the
festival falls near an ordinary Shabbat, one bulletin carries both
("Shabbat Ha'azinu and Kippur 5787"), Shabbat's times and reading first.
Festival times are headed "Times for Poughkeepsie, NY (…)" — the exact
Shabbat heading stays reserved for ordinary weeks. The Reflections heading
follows: "Reflections on Rosh Hashana", "Reflections on the Parasha and
Kippur".

Service times in the bulletin come from bulletin/service-times.md (the
standing Shabbat schedule) unless a festival file exists at
bulletin/service-times/<festival>.md — Rosh Hashana's, given by Marc
3 September 2026, is bulletin/service-times/rosh-hashana.md. The schedule
block on the services page is program-managed the same way (spliced at
publish between weekly-schedule markers).

Layout of the service-times block (Marc's direction, 7 September 2026):
the block sits directly under the banner, before the halakhic times.
File format, rendered strictly in file order: "# BIG — normal" headings
(the part before the em-dash set larger); "Label = time | description"
rows; "Label =" with no time for a label-only row (BREAK); "* note"
paragraphs wherever they fall; "---" for a William Morris separation bar
(the pimpernel pattern; the email uses bar-pimpernel.jpg). The halakhic
times block is headed "Halakhic (Ritual) Times — Poughkeepsie, NY 41.70 N
73.92 W", split the same way. A trailing fast gets its own section
inside the times block (Marc's layout, 7 September 2026): after the
festival's ends-line, a Morris bar, a header with the fast's name, its
tiny description (FAST_NOTES in bulletin.py — the Fast of Gedalia text
is Marc's own), then "Fast begins" and "Fast ends" lines. In the
readings section each reading carries its own interpretations: the
drafting writes a Torah summary and a haftarah summary per reading, and
each sits directly under what it interprets.

More of Marc's directions, 7 September 2026: a festival bulletin carries
no "Weekly Bulletin" eyebrow (ordinary Shabbat bulletins keep it).
"All times approximate", in italics, stands under the service-times
title everywhere the schedule appears. In-the-Week-Ahead can be
overridden for one bulletin by bulletin/week-ahead/<saturday>.md — one
line per item, replacing the computed list for that date alone (used
first for Rosh Hashana 5787: just Shabbat Shuvah, and Yom Kippur as
beginning Sunday night).

Weeks with no services (settled 4 September 2026): the service times do
not appear anywhere, and a line in red states, verbatim: No services will
be held this week

Ari's Friday email (Marc's commission, 3-4 September 2026): every Friday
at 6:00 am, exclusively to Ari; subject "Good Shabbos Ári ❤️! Shabbat
Times For Tufts University: Parashat <name>"; eyebrow "Sponsored by your
home congregation, Kehillah Kedoshah Zikhron Zvi", then "❤️WITH LOVE FROM
אבא and ANYU❤️", then Ahad Haʿam's line on Shabbat keeping the Jews
(Hebrew with Marc's English rendering and his citation to Ha-Shiloaḥ,
Sivan 5658 / June 1898); times computed for Tufts University, Medford, MA
(42.41° N, 71.12° W); then the summaries, the week ahead, and the week's
Reflections.

Calendar scope

Every Shabbat receives a bulletin.

Every festival and every fast receives its own bulletin: Rosh Hashana,
Kippur, Sukkot, Shemini Atseret, Simhat Torah, Hanukkah, Purim, Pesah,
Shabuot, Tish'a Be'Ab, the minor fasts (Gedalia, Tebet, Esther, Tammuz),
plus Tu BiShbat and Lag LaOmer.

If a festival or fast falls within two days of Shabbat or another festival,
one bulletin covers the cluster and the earliest proof date applies.

In force since 15 November 2026 (Marc's order that every holiday get a
bulletin; program/occasions.py): the rule above is applied to every
occasion in the list, transitively — Pesah VII on a Wednesday joins Pesah
VIII on the Thursday and the Shabbat after; the Fast of Esther on a Monday
joins the Shabbat before it and Purim on the Tuesday. A Shabbat bulletin
that carries a festival or fast prints its times in date order, each
section under its own heading (Hanukkah's eight candles, Purim's two
Megillah readings, a fast's beginning and end — Tish'a Be'Ab from sunset
the evening before, the minor fasts from dawn), and its readings (the yom
tob days', Purim's, Tish'a Be'Ab's; a minor fast's weekday reading only in
a bulletin of its own). An occasion more than two days from any Shabbat
gets a bulletin of its own, keyed by its first day: no "Weekly Bulletin"
eyebrow, the festival's name and year for a title, no service schedule or
Kiddush unless Marc writes bulletin/service-times/<festival>.md for it,
its week-ahead lines free of itself, and Reflections on the festival. The
first such bulletin in the calendar is Lag LaOmer, Tuesday 25 May 2027
(proof Sunday the 23rd, mail Monday the 24th); 5788 brings Pesah on
Tuesday 11 April 2028, Tzom Tammuz, Tish'a Be'Ab and Hanukkah on their
own. Hanukkah counts by its first day only, so that it never fuses two
Shabbatot into one bulletin; a Shabbat within two days of its first day
carries all eight candle lightings. A Shabbat that is itself an
intermediate day of Pesah or Sukkot inside a cluster makes that bulletin
the festival's, named for the festival. python3 program/occasions.py
<year> lists a year's festival bulletins; python3 program/schedule.py
--list the next eight with their proof and mailing days.

Rosh Hodesh, Purim Katan, and Pesah Sheni are announced in the preceding
Shabbat bulletin and receive no separate bulletin.

No modern days (Yom HaShoah, Yom HaZikaron, Yom HaAtsmaut, Yom Yerushalayim).

Second-day Yom Tob is observed (diaspora).

Schedule

Shabbat (Marc's rule, 15 November 2026): the proof reaches Marc on
Thursday, for his review on Thursday night. It is built at 10:00 am New
York nominal and lands during the afternoon or evening, since GitHub queues
its crons hours late. The bulletin goes out on Friday: the send moment is
6:00 am Friday, America/New_York, and the morning runs (6:00 and 10:00
nominal) publish and send an approved bulletin as soon as the first of
them starts; an approval that arrives after the send moment publishes and
sends at once. A reminder goes to Marc on Thursday evening if the proof is
still unapproved; a proof whose mailing day has passed is not nagged about
again — the Desk shows it, and the next proof supersedes it.

Festivals and fasts follow the same two days measured from the bulletin's
first eve: proof the day before the eve, mail on the eve. So Pesah
beginning Thursday 22 April 2027 is proofed Tuesday the 20th and mailed
Wednesday the 21st; Shabuot beginning Friday 11 June 2027 is proofed
Wednesday the 9th and mailed Thursday the 10th; Lag LaOmer, alone on
Tuesday 25 May 2027, is proofed Sunday the 23rd and mailed Monday the
24th. program/schedule.py is the one place this rule lives, for Shabbat
bulletins and standalone ones alike (it asks program/occasions.py which
bulletins exist); each proof records its proof_day, send_day and
send_moment in current.json, and publish.py and the reminder read them
from there. Every proof also writes bulletin/state/schedule.json, the
next eight bulletins with their days, which the Desk shows under Coming
up. The family letters (family.py --auto, daily at 6:00 am) go out on
every bulletin's mailing day — Fridays and the eves of standalone
festivals and fasts — with "Festival Times" or "Fast Times" in the
subject and a festival sign-off in place of GOOD SHABBOS when the letter
is not a Shabbat letter: GOOD YONTIF! for a yom tob, AN EASY AND
MEANINGFUL FAST! for a fast, HAPPY HANUKKAH!, HAPPY PURIM!, HAPPY TU
BISHBAT!, HAPPY LAG LAOMER! (approved by Marc 15 November 2026; the
words live in family.festival_greeting).
Nothing is ever published or sent without approval.

Proof mailbox (Marc's order, 15 November 2026): everything the program
sends Marc — the proof, the "awaiting approval" reminder and his copy of
each family letter — goes to the congregation's own Gmail mailbox, not
his personal one, so KKZZ business stays apart from his own. Mailchimp's
Proof segment holds that one address (moved with the
mailchimp-repoint-proof workflow; the address travels as a temporary
repository secret and appears nowhere in code or logs). A filter in that
mailbox files all mail from shabbat@kzzhv.org under the label
Shabbat-Holiday PROOFS. The proof itself stays Thursday night.

(History of the schedule: Thursday proof and Thursday 6:00 pm send in the
brief; Wednesday 6:00 am / 6:00 pm from 3 September 2026; Thursday proof
and Friday send from 15 November 2026. Between 30 September and 11
November 2026 five of seven Wednesday proofs died unmailed because a
rewritten cache file blocked the workflow's rebase, and the two that
arrived sat unread; the site stood at Shabbat Shuvah for eight weeks.
The commit step now keeps that cache and discards everything else before
rebasing.)

The Desk (kzzhv.org/private, 15 November 2026): the private page shows
the bulletin in hand with its status, Approve and Request-changes on the
page itself, the proof image, and previews of the email and the web page;
a ledger of the last six weeks' mailings read live from Mailchimp — the
congregational send, each family letter and who received it, the students
on the latest congregational mailing, and the people named in the Netlify
variable DESK_WATCH; what the live site is showing and whether it is
behind; the coming proof and mailing days; then the announcements and
location form as before. It reads Mailchimp with the Netlify variable
MAILCHIMP_API_KEY and never shows an address.

Request changes on a proof: the box's instructions edit the content files
Marc owns — banner, announcements, location, service times, greetings —
and reach the teachings drafting; a fresh proof follows, again to Marc
alone. Layout, template, and program changes are outside the box's reach:
the fresh proof's banner names whatever a request asked for that must go
to Claude directly. The change step never invents facts — a missing time
or name is asked for in that banner line, not guessed. (Widened from
teachings-only at Marc's direction, 7 September 2026, after his greeting
corrections on the Rosh Hashana proof changed nothing.)

Localized bulletin sends (Marc's commission, 7 September 2026,
program/localized_send.py + the localized-send workflow): the current
PUBLISHED bulletin, complete with banner and greetings, sent to a family
member's own tag segment with the KKZZ service times dropped and the
halakhic times, their heading, and the subject recomputed for that
member's sky (Ari at Tufts, Misha and Gabi in Philadelphia, Mom in New
York). Teachings come from the published state, never redrafted. Manual
workflow only; proof by default, live at Marc's word. First used for
Rosh Hashana 5787.

Joy Schwartz (Marc's order, 15 November 2026): she is the one recipient
of the letter addressed "Mom" and was also on the congregational Weekly
segment. She was taken off the Weekly segment that day (the mailchimp-
private workflow, by segment key, no address in code or logs; the segment
went from 60 members to 59) and now receives her own letter only, every
Shabbat and every holiday, on the bulletin's mailing morning. The Desk
shows her under "Mom" by first name; DESK_WATCH is no longer set.

Copies to Marc (his word, 9 September 2026): every live family or
localized send also mails him one copy, its subject labeled with whose
letter it is, so he can see what each of them received. He is himself on
the Weekly segment, so the congregational bulletin reaches him once by
that route and gets no extra copy. The repository variable CC_MARC set
to "false" stops the family copies. One copy per letter: from 9 September
to 15 November 2026 the shared sender's own copy mechanism doubled every
family copy, so each Friday brought him eight emails for four letters;
the family and localized senders now switch that mechanism off and send
the one labeled copy.

Sister congregations

Congregation Shearith Israel, New York — Kippur, by default.
Sha'ar HaShamayim, London, at Lauderdale Road or Bevis Marks — Shabbat
Bereshit, by default.
Mikveh Israel, Philadelphia — various Shabbatot.

When away, the bulletin opens: "This Shabbat the congregation is guests
of ..." naming the host. When there are no services, it says so plainly.
Away weeks drop the kiddush, address, and RSVP lines only; times remain
Poughkeepsie times.

Standing lines

Home weeks carry this line verbatim:
To RSVP and to register food issues and avoidances, kindly contact the
Congregation's secretary at kehillatzikhronzvi@gmail.com by Thursday night
at 10:00 pm
(Deadline added at Marc's direction, 3 September 2026.)

Addresses

Secretary, for RSVPs and replies: kehillatzikhronzvi@gmail.com
Bulletin sending address: shabbat@kzzhv.org (authenticated through
Mailchimp; no mailbox exists or is needed). Reply-To: the secretary's Gmail.

Bulletin composition (settled 3 September 2026)

Readings show the verse range — no verse count, no aliyot listing —
followed by a one-paragraph summary of the parashah's highlights, then
the haftarah with its own one-paragraph summary. The Sephardic haftarah
is noted where it differs from the Ashkenazic.

The teachings: plain, loving, humane language; citations as numbered
footnotes, never in the prose; the halakhic teaching is one Mishneh Torah
paragraph on the season plus one short Keter Shem Tob paragraph on lived
custom, the aggadic one short paragraph of parshanut or midrash; nothing
that reflects negative attitudes toward women or toward non-Jews. The
full brief is bulletin/voice.md (revised 3 September 2026).

The Leil Selihot notice reads: "Leil Selihot for Ashkenazim; Sephardim
have been saying Selihot since 2 Elul."

The two teachings sit under one heading, "Reflections on the Parasha",
with "Halakha" and "Aggada" as subheads.

Transliteration

Hebrew transliteration follows Sephardic pronunciation (Shabbat, Sukkot,
Habdala, Selihot, Kippur). The congregation's own spellings on the site win.
