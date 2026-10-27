"""Synthetic catalogue for the bookable query plan (P5.7, N2.6):

    python manage.py load_bookable_fixture --packages 2000 --departures 10
    python manage.py load_bookable_fixture --explain
    python manage.py load_bookable_fixture --clean

Rows are tagged by the name prefix LOAD- and removed by --clean. Nothing here runs in
production; it exists so the plan in docs/plans/bookable.md is measured, not guessed.
"""

from __future__ import annotations

import random
import statistics
import time
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandParser
from django.db import connection, transaction
from django.utils import timezone

from booking.models import Booking, Traveller
from catalogue import bookable
from catalogue.models import (
    Departure,
    Destination,
    DestinationType,
    Package,
    PackageDestination,
)
from core.models import Role, User
from locations.models import Location

PREFIX = "LOAD-"


class Command(BaseCommand):
    help = "Create, explain or remove a synthetic catalogue for the bookable query plan."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--packages", type=int, default=2000)
        parser.add_argument("--departures", type=int, default=10, help="per package")
        parser.add_argument("--explain", action="store_true")
        parser.add_argument("--clean", action="store_true")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        if options["clean"]:
            self._clean()
            return
        if options["explain"]:
            self._explain()
            return
        self._load(options["packages"], options["departures"], options["seed"])

    @transaction.atomic
    def _load(self, n_packages: int, per_package: int, seed: int) -> None:
        rng = random.Random(seed)
        locations = list(Location.objects.filter(deleted_at__isnull=True)[:13])
        types = list(DestinationType.objects.all())
        if not locations or not types:
            self.stderr.write("seed locations and destination types first (make seed)")
            return
        user, _ = User.objects.get_or_create(
            username="load-user", defaults={"role": Role.SALES, "is_active": False}
        )
        traveller = Traveller.objects.create(name=f"{PREFIX}traveller")
        destinations = [
            Destination(
                location=rng.choice(locations),
                type=rng.choice(types),
                name=f"{PREFIX}dest-{i}",
                danger=rng.choice([0, 1, 1, 2, 2, 3]),
            )
            for i in range(200)
        ]
        Destination.objects.bulk_create(destinations)
        packages = [
            Package(
                name=f"{PREFIX}pkg-{i:05d}",
                price=rng.randrange(200, 4000),
                currency="EUR",
                duration_days=rng.randrange(2, 15),
                active=rng.random() > 0.05,
            )
            for i in range(n_packages)
        ]
        Package.objects.bulk_create(packages)
        rows = []
        for p in packages:
            for pos, d in enumerate(rng.sample(destinations, rng.randrange(1, 5)), start=1):
                rows.append(PackageDestination(package=p, destination=d, position=pos))
        PackageDestination.objects.bulk_create(rows, batch_size=5000)
        today = date.today()
        now = timezone.now()
        deps = []
        for p in packages:
            for off in rng.sample(range(-60, 400), per_package):
                cancelled = rng.random() < 0.03
                deps.append(
                    Departure(
                        package=p,
                        starts_on=today + timedelta(days=off),
                        capacity=rng.randrange(4, 40),
                        status="cancelled" if cancelled else "planned",
                        cancelled_at=now if cancelled else None,
                    )
                )
        Departure.objects.bulk_create(deps, batch_size=5000)
        bookings = []
        for i, dep in enumerate(deps):
            if rng.random() < 0.5:
                seats = rng.randrange(1, dep.capacity + 1)  # some sell out completely
                bookings.append(
                    Booking(
                        departure=dep,
                        traveller=traveller,
                        created_by=user,
                        seats=seats,
                        price_at_booking=1,
                        currency="EUR",
                        danger_at_booking=0,
                        idempotency_key=f"{PREFIX}{i}",
                    )
                )
        Booking.objects.bulk_create(bookings, batch_size=5000)
        self.stdout.write(
            f"loaded packages={len(packages)} departures={len(deps)} bookings={len(bookings)}"
        )

    def _clean(self) -> None:
        with transaction.atomic():
            Booking.objects.filter(idempotency_key__startswith=PREFIX).delete()
            Departure.objects.filter(package__name__startswith=PREFIX).delete()
            PackageDestination.objects.filter(package__name__startswith=PREFIX).delete()
            Package.objects.filter(name__startswith=PREFIX).delete()
            Destination.objects.filter(name__startswith=PREFIX).delete()
            Traveller.objects.filter(name__startswith=PREFIX).delete()
            User.objects.filter(username="load-user").delete()
        self.stdout.write("cleaned")

    def _explain(self) -> None:
        today = date.today()
        query = bookable.parse(
            {
                "from": today.isoformat(),
                "to": (today + timedelta(days=30)).isoformat(),
                "danger": "2",
            }
        )
        qs = bookable.packages(query)
        page = qs[:20]
        sql, params = page.query.sql_with_params()
        with connection.cursor() as cur:
            cur.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
            plan = "\n".join(r[0] for r in cur.fetchall())
        self.stdout.write("-- query 1: packages (page of 20)\n" + plan)
        ids = [p.pk for p in page]
        deps = bookable.departures_for(ids, query)
        n_rows = sum(len(v) for v in deps.values())
        self.stdout.write(f"-- query 2: departures for {len(ids)} packages, {n_rows} rows")
        times = []
        for _ in range(50):
            t0 = time.perf_counter()
            rows = list(qs[:20])
            bookable.departures_for([p.pk for p in rows], query)
            times.append((time.perf_counter() - t0) * 1000)
        times.sort()
        p95 = times[int(len(times) * 0.95) - 1]
        self.stdout.write(
            f"-- 50 runs, both queries: median {statistics.median(times):.1f} ms, p95 {p95:.1f} ms"
        )
        counts = {
            "packages": Package.objects.count(),
            "departures": Departure.objects.count(),
            "bookings": Booking.objects.count(),
            "matches": qs.count(),
        }
        self.stdout.write(f"-- table sizes {counts}")
