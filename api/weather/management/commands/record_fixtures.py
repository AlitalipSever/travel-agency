"""Record real upstream payloads into api/fixtures/openweather (needs OPENWEATHER_API_KEY).

    python manage.py record_fixtures lima=-12.046,-77.043 la_paz=-16.4897,-68.1193

The raw JSON is stored unchanged; tests and the mock client read it. Re-run to refresh.
"""

from __future__ import annotations

import json

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from weather.upstream.fixtures import FIXTURE_DIR


class Command(BaseCommand):
    help = "Record OpenWeatherMap current and forecast payloads as fixtures."

    def add_arguments(self, parser) -> None:  # noqa: ANN001
        parser.add_argument("places", nargs="+", help="slug=lat,lon")

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        key = settings.OPENWEATHER_API_KEY
        if not key:
            raise CommandError("OPENWEATHER_API_KEY is not set")
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        with httpx.Client(base_url=settings.OPENWEATHER_BASE_URL, timeout=10.0) as client:
            for spec in options["places"]:
                slug, coords = spec.split("=")
                lat, lon = (float(x) for x in coords.split(","))
                for kind, path in (
                    ("current", "/data/2.5/weather"),
                    ("forecast", "/data/2.5/forecast"),
                ):
                    r = client.get(
                        path, params={"appid": key, "units": "metric", "lat": lat, "lon": lon}
                    )
                    if r.status_code != 200:
                        raise CommandError(f"{kind} {slug}: upstream answered {r.status_code}")
                    (FIXTURE_DIR / f"{kind}_{slug}.json").write_text(
                        json.dumps(r.json(), indent=2) + "\n"
                    )
                    self.stdout.write(f"recorded {kind}_{slug}.json")
