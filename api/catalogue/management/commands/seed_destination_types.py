"""Idempotent seed of the destination types (P2.3): python manage.py seed_destination_types."""

from django.core.management.base import BaseCommand

from catalogue.services import seed_destination_types


class Command(BaseCommand):
    help = "Insert the initial destination types that are missing (never overwrites)."

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        result = seed_destination_types()
        self.stdout.write(
            f"destination types: created={result['created']} skipped={result['skipped']}"
        )
