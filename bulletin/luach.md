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

18 minutes before sunset, printed with sunset shown, exactly in this form:
Candle lighting 7:05 pm (18 minutes before sunset; sunset 7:23 pm)
The printed sunset is the computed sunset rounded to the nearest minute,
and the candle time is 18 minutes before the printed sunset, so the
arithmetic on the page is exact.

End of Shabbat and festivals

CALIBRATED 3 September 2026. The congregation follows Congregation
Shearith Israel, New York. Their published times do not fit a fixed solar
depression (the working hypothesis in the project brief): winter weeks run
six to nine minutes earlier than any depression that fits the equinoxes.
They fit a seasonal rule:

End of Shabbat = sunset plus 33.75 seasonal minutes, rounded up to the
whole minute, where one seasonal minute is one sixtieth of one twelfth of
that day's sunrise-to-sunset span (standard refracted sunrise and sunset).

Data: 143 independent Shabbatot of Shearith Israel's own published Habdala
times, October 2020 through September 2026, gathered from their website,
their weekly handout PDFs, and Wayback Machine snapshots of their pages;
the dataset is program/data/shearith-times.csv and the verification tool is
program/calibrate_habdala.py. Computed for New York, the rule reproduces
their published figure to the minute in 65% of those weeks and to within
one minute in 93%, and comes out earlier than their figure in only 12 of
the 143 (11 of them by a single minute). The residue traces to their own
generator's coarser sunsets, which differ from precise astronomy by a
minute in roughly a third of the sampled weeks; exact reproduction is
therefore not attainable in principle. The upward rounding is chosen so the
printed end of Shabbat practically never falls earlier than their
convention. Both anchor figures in the project brief reproduce exactly
(4–5 September 2026: Habdala 7:58 pm; 17 July 2021: 9:07 pm).

The same nightfall rule, computed on the Poughkeepsie sky, ends festivals
and Kippur. Festival candle lighting on the eve is as above; second-day
lighting is after the stated end of the first day. Fast beginnings (dawn)
are PENDING calibration against Shearith Israel's published fast times and
will be recorded here before the first fast-day bulletin.

Calendar scope

Every Shabbat receives a bulletin.

Every festival and every fast receives its own bulletin: Rosh Hashana,
Kippur, Sukkot, Shemini Atseret, Simhat Torah, Hanukkah, Purim, Pesah,
Shabuot, Tish'a Be'Ab, the minor fasts (Gedalia, Tebet, Esther, Tammuz),
plus Tu BiShbat and Lag LaOmer.

If a festival or fast falls within two days of Shabbat or another festival,
one bulletin covers the cluster and the earliest proof date applies.

Rosh Hodesh, Purim Katan, and Pesah Sheni are announced in the preceding
Shabbat bulletin and receive no separate bulletin.

No modern days (Yom HaShoah, Yom HaZikaron, Yom HaAtsmaut, Yom Yerushalayim).

Second-day Yom Tob is observed (diaspora).

Schedule

Shabbat: proof to Marc at 6:00 am Thursday, America/New_York. Publish and
send at 6:00 pm Thursday once approved; if approval comes later, publish and
send immediately on approval. Reminder to Marc at 5:00 pm Thursday if not
yet approved. Festivals and fasts: same pattern, proof at 6:00 am two days
before the eve. Nothing is ever published or sent without approval.

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
Congregation's secretary at kehillatzikhronzvi@gmail.com

Addresses

Secretary, for RSVPs and replies: kehillatzikhronzvi@gmail.com
Bulletin sending address: shabbat@kzzhv.org (authenticated through
Mailchimp; no mailbox exists or is needed). Reply-To: the secretary's Gmail.

Transliteration

Hebrew transliteration follows Sephardic pronunciation (Shabbat, Sukkot,
Habdala, Selihot, Kippur). The congregation's own spellings on the site win.
