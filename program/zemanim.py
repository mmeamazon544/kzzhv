"""Solar computations for the KKZZ bulletin.

Pure Python, no dependencies. NOAA solar-position formulas (Meeus), good to
well under a minute for civil latitudes, which is what the bulletin needs.

All public functions take a date (datetime.date), latitude north-positive,
longitude EAST-positive (Poughkeepsie is -73.92), and an IANA zone name, and
return timezone-aware datetimes.

The congregation's rules (see bulletin/luach.md):
  candle lighting = 18 minutes before sunset
  end of Shabbat/festivals = sun at a fixed depression below the horizon,
  calibrated to reproduce Congregation Shearith Israel's published times.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Poughkeepsie, per the project brief. Longitude east-positive.
KKZZ_LAT = 41.70
KKZZ_LON = -73.92
KKZZ_TZ = "America/New_York"

# Standard sunset/sunrise zenith: 90° + 34' refraction + 16' semidiameter.
SUNSET_ZENITH = 90.0 + 50.0 / 60.0


def _julian_day(dt_utc: datetime) -> float:
    y, m = dt_utc.year, dt_utc.month
    d = (
        dt_utc.day
        + (dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0) / 24.0
    )
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def _solar_position(jd: float) -> tuple[float, float]:
    """Return (declination degrees, equation of time in minutes) at jd."""
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360.0
    m = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    mrad = math.radians(m)
    c = (
        math.sin(mrad) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * mrad) * (0.019993 - 0.000101 * t)
        + math.sin(3 * mrad) * 0.000289
    )
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(
        math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(app_long)))
    )
    y = math.tan(math.radians(eps / 2.0)) ** 2
    l0r = math.radians(l0)
    eqtime = 4.0 * math.degrees(
        y * math.sin(2 * l0r)
        - 2 * e * math.sin(mrad)
        + 4 * e * y * math.sin(mrad) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * e * e * math.sin(2 * mrad)
    )
    return decl, eqtime


def _hour_angle(lat: float, decl: float, zenith: float) -> float:
    """Evening hour angle in degrees for the given zenith; ValueError if the
    sun never reaches it that day (polar conditions)."""
    latr, declr = math.radians(lat), math.radians(decl)
    cos_ha = (
        math.cos(math.radians(zenith)) - math.sin(latr) * math.sin(declr)
    ) / (math.cos(latr) * math.cos(declr))
    if cos_ha < -1.0 or cos_ha > 1.0:
        raise ValueError(f"sun does not reach zenith {zenith} at latitude {lat}")
    return math.degrees(math.acos(cos_ha))


def sun_event(
    d: date, lat: float, lon: float, tz: str, zenith: float, evening: bool = True
) -> datetime:
    """UTC-iterated time the sun crosses the given zenith on local date d."""
    zone = ZoneInfo(tz)
    # Start from local noon of the civil date, expressed in UTC.
    guess = datetime.combine(d, time(12, 0), tzinfo=zone).astimezone(timezone.utc)
    for _ in range(3):
        jd = _julian_day(guess)
        decl, eqtime = _solar_position(jd)
        ha = _hour_angle(lat, decl, zenith)
        if not evening:
            ha = -ha
        # Minutes UTC from 0:00 UTC of the guess's UTC date.
        minutes_utc = 720.0 - 4.0 * lon - eqtime + 4.0 * ha
        day0 = datetime(guess.year, guess.month, guess.day, tzinfo=timezone.utc)
        guess = day0 + timedelta(minutes=minutes_utc)
    return guess.astimezone(zone)


def sunset(d: date, lat: float = KKZZ_LAT, lon: float = KKZZ_LON, tz: str = KKZZ_TZ) -> datetime:
    return sun_event(d, lat, lon, tz, SUNSET_ZENITH, evening=True)


def sunrise(d: date, lat: float = KKZZ_LAT, lon: float = KKZZ_LON, tz: str = KKZZ_TZ) -> datetime:
    return sun_event(d, lat, lon, tz, SUNSET_ZENITH, evening=False)


def depression(
    d: date,
    degrees: float,
    lat: float = KKZZ_LAT,
    lon: float = KKZZ_LON,
    tz: str = KKZZ_TZ,
    evening: bool = True,
) -> datetime:
    """Time the sun's center reaches the given depression below the horizon
    (no refraction term, per the usual twilight convention)."""
    return sun_event(d, lat, lon, tz, 90.0 + degrees, evening=evening)


def round_nearest(dt: datetime) -> datetime:
    """To the nearest minute."""
    return (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)


def format_time(dt: datetime) -> str:
    """12-hour clock, lowercase am/pm, no leading zero: 7:05 pm."""
    s = dt.strftime("%I:%M %p").lower()
    return s.lstrip("0")


if __name__ == "__main__":
    # Self-checks against known figures.
    ny_lat, ny_lon = 40.7690, -73.9813  # Shearith Israel, Central Park West
    d = date(2026, 9, 4)
    ss = sunset(d, ny_lat, ny_lon)
    print("NYC sunset 2026-09-04:", format_time(round_nearest(ss)), "(SI candles 7:05 pm -> sunset 7:23 pm)")
    print("  candles (sunset-18):", format_time(round_nearest(ss - timedelta(minutes=18))))
    for deg in (7.0, 7.5, 8.0):
        hb = depression(date(2026, 9, 5), deg, ny_lat, ny_lon)
        print(f"  2026-09-05 sun at -{deg}: {format_time(round_nearest(hb))} (SI Habdala 7:58 pm)")
    hb21 = depression(date(2021, 7, 17), 7.5, ny_lat, ny_lon)
    print("2021-07-17 sun at -7.5:", format_time(round_nearest(hb21)), "(SI Habdala 9:07 pm)")
    pk = sunset(date(2026, 9, 4))
    print("Poughkeepsie sunset 2026-09-04:", format_time(round_nearest(pk)))
