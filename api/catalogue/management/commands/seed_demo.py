"""Demo data for a walkthrough (B12, A17): python manage.py seed_demo

Idempotent: the demo partner, four demo users with tokens (one per role), eight destinations
in the seeded capitals, four packages (one inactive), planned departures over the next ninety
days and a few bookings so that remaining seats vary and one departure is sold out. Rows are
matched by name; nothing operations may have edited is overwritten. Tokens are printed once
per run so that `make demo` gives a usable Authorization header.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from booking.models import Booking, Traveller
from catalogue import services
from catalogue.models import Departure, Destination, DestinationType, Package
from core.models import Partner, Role, User
from locations.models import Location

DESTINATIONS = [
    # (location, type, name, danger)
    ("Lima", "cultural", "Historic centre of Lima", 0),
    ("Lima", "beach", "Miraflores coast", 0),
    ("La Paz", "adventure", "Death Road ride", 2),
    ("La Paz", "urban", "El Alto market", 1),
    ("Quito", "nature", "Cotopaxi foothills", 2),
    ("Santiago", "adventure", "Andes high passes", 3),
    ("Buenos Aires", "urban", "San Telmo and La Boca", 0),
    ("Montevideo", "beach", "Rambla and Pocitos", 0),
]

PACKAGES = [
    # (name, price, duration, destinations, active)
    ("Lima weekend", "450.00", 3, ["Historic centre of Lima", "Miraflores coast"], True),
    (
        "Andes adventure",
        "1200.00",
        7,
        ["Historic centre of Lima", "Death Road ride", "El Alto market"],
        True,
    ),
    ("Volcano trek", "1650.00", 9, ["Cotopaxi foothills", "Andes high passes"], True),
    ("Rio de la Plata", "780.00", 5, ["San Telmo and La Boca", "Rambla and Pocitos"], True),
    ("Retired itinerary", "300.00", 2, ["Miraflores coast"], False),
]

USERS = [("demo-ops", Role.OPS), ("demo-sales", Role.SALES), ("demo-finance", Role.FINANCE)]


class Command(BaseCommand):
    help = "Insert the demo partner, users, destinations, packages, departures and bookings."

    @transaction.atomic
    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        partner, _ = Partner.objects.get_or_create(
            name="Demo Travel Partner", defaults={"is_demo": True}
        )
        tokens: dict[str, str] = {}
        for username, role in USERS:
            user, _ = User.objects.get_or_create(username=username, defaults={"role": role})
            tokens[username] = Token.objects.get_or_create(user=user)[0].key
        partner_user, _ = User.objects.get_or_create(
            username="demo-partner", defaults={"role": Role.PARTNER, "partner": partner}
        )
        tokens["demo-partner"] = Token.objects.get_or_create(user=partner_user)[0].key

        locations = {loc.name: loc for loc in Location.objects.filter(deleted_at__isnull=True)}
        types = {t.key: t for t in DestinationType.objects.all()}
        missing = [name for name, *_ in DESTINATIONS if name not in locations]
        if missing or not types:
            self.stderr.write(f"run seed first; missing locations {missing}, types {len(types)}")
            return

        created = {"destinations": 0, "packages": 0, "departures": 0, "bookings": 0}
        destinations: dict[str, Destination] = {}
        for loc_name, type_key, name, danger in DESTINATIONS:
            dest, was_created = Destination.objects.get_or_create(
                location=locations[loc_name],
                name=name,
                deleted_at__isnull=True,
                defaults={"type": types[type_key], "danger": danger},
            )
            destinations[name] = dest
            created["destinations"] += int(was_created)

        today = date.today()
        packages: dict[str, Package] = {}
        for name, price, duration, dest_names, active in PACKAGES:
            pkg = Package.objects.live().filter(name=name).first()
            if pkg is None:
                pkg = services.create_package(
                    {"name": name, "price": price, "currency": "EUR", "duration_days": duration},
                    [destinations[d].pk for d in dest_names],
                )
                if not active:
                    pkg.active = False
                    pkg.save(update_fields=["active", "updated_at"])
                created["packages"] += 1
            packages[name] = pkg
            if active:
                for offset in (7, 21, 35, 49, 63, 77, 91):
                    day = today + timedelta(days=offset)
                    if not pkg.departures.filter(starts_on=day).exists():
                        services.create_departure(pkg, day, capacity=12)
                        created["departures"] += 1

        # bookings: vary the remaining seats, sell out one departure (the walkthrough's 409)
        sales = User.objects.get(username="demo-sales")
        traveller, _ = Traveller.objects.get_or_create(
            name="Ana Demo", defaults={"risk_appetite": 2}
        )
        plan = [("Andes adventure", 7, 12), ("Andes adventure", 21, 10), ("Lima weekend", 7, 3)]
        for pkg_name, offset, seats in plan:
            dep = Departure.objects.get(
                package=packages[pkg_name], starts_on=today + timedelta(days=offset)
            )
            key = f"demo-{pkg_name}-{offset}"
            if not Booking.objects.filter(created_by=sales, idempotency_key=key).exists():
                Booking.objects.create(
                    departure=dep,
                    traveller=traveller,
                    created_by=sales,
                    seats=seats,
                    price_at_booking=dep.package.price,
                    currency=dep.package.currency,
                    danger_at_booking=2 if pkg_name == "Andes adventure" else 0,
                    idempotency_key=key,
                )
                created["bookings"] += 1

        self.stdout.write(f"demo: created {created}")
        self.stdout.write("tokens (Authorization: Token <value>):")
        for name, key in tokens.items():
            self.stdout.write(f"  {name:13s} {key}")
