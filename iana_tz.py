import re
import sys
from collections import defaultdict

import requests

# ISO 6709: ±DDMM±DDDMM  or  ±DDMMSS±DDDMMSS
ISO6709 = re.compile(
    r"""
    ^
    (?P<lat_sign>[+-])(?P<lat_d>\d{2})(?P<lat_m>\d{2})(?P<lat_s>\d{2})?
    (?P<lon_sign>[+-])(?P<lon_d>\d{3})(?P<lon_m>\d{2})(?P<lon_s>\d{2})?
    $
""",
    re.VERBOSE,
)


def parse_iso6709(s: str) -> tuple[float, float]:
    m = ISO6709.match(s)
    if not m:
        raise ValueError(f"bad ISO 6709 coord: {s!r}")
    g = m.groupdict()

    def to_deg(sign, d, mn, sec):
        val = int(d) + int(mn) / 60 + (int(sec) / 3600 if sec else 0)
        return -val if sign == "-" else val

    lat = to_deg(g["lat_sign"], g["lat_d"], g["lat_m"], g["lat_s"])
    lon = to_deg(g["lon_sign"], g["lon_d"], g["lon_m"], g["lon_s"])
    return lat, lon


resp = requests.get("https://data.iana.org/time-zones/data/zone1970.tab")
resp.raise_for_status()

data = resp.text
print(data)

from_country = defaultdict(list)
from_tz = {}

for row in data.splitlines():
    row = row.strip()
    if row.startswith("#"):
        continue

    row = row.split("\t")
    if len(row) not in (3, 4):
        print(
            f"invalid number of items on row, got={len(row)} expected=2-3",
            file=sys.stderr,
        )
        continue

    country_codes = row[0].split(",")
    coords = parse_iso6709(row[1])
    tz = row[2]
    comment = row[3] if len(row) == 4 else ""

    data = {
        "countries": country_codes,
        "coords": coords,
        "tz": tz,
        "comment": comment,
    }

    if tz in from_tz:
        raise ValueError(f"TZ is multiple times in data: {tz}")

    for country_code in country_codes:
        from_country[country_code].append(data)
    from_tz[tz] = data

# print(from_country)
# print(from_tz)

tz = input("TZ: ")
print(from_tz[tz.strip()])
