"""P1.1, P1.2, P1.4, P2.1, P2.2, P2.4, P4.1 to P4.3 and the role matrix over HTTP."""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from catalogue import services
from catalogue.models import Destination

TYPES = "/api/v1/destination-types"
DEST = "/api/v1/destinations"
PKG = "/api/v1/packages"


def _pkg(ops: APIClient, name: str, ids: list, **extra) -> dict:  # noqa: ANN003
    body = {
        "name": name,
        "price": "1200.00",
        "currency": "eur",
        "duration_days": 7,
        "destination_ids": [str(i) for i in ids],
        **extra,
    }
    r = ops.post(PKG, body, format="json")
    assert r.status_code == 201, r.content
    return r.json()


@pytest.mark.django_db
def test_p1_1_p2_1_every_role_reads_only_ops_writes(ops, sales, lima, types) -> None:  # noqa: ANN001
    body = {
        "name": "Barranco",
        "location_id": str(lima.pk),
        "type_id": str(types["urban"].pk),
        "danger": 1,
    }
    assert sales.post(DEST, body, format="json").status_code == 403
    assert sales.post(TYPES, {"key": "ski", "label": "Ski"}, format="json").status_code == 403
    r = ops.post(DEST, body, format="json")
    assert r.status_code == 201, r.content
    assert sales.get(DEST).status_code == 200
    assert sales.get(TYPES).status_code == 200
    assert sales.patch(f"{DEST}/{r.json()['id']}", {"danger": 2}, format="json").status_code == 403
    assert APIClient().get(PKG).status_code == 401


@pytest.mark.django_db
def test_p2_2_danger_scale_is_enforced(ops, lima, types) -> None:  # noqa: ANN001
    body = {"name": "X", "location_id": str(lima.pk), "type_id": str(types["nature"].pk)}
    assert ops.post(DEST, {**body, "danger": 4}, format="json").status_code == 400
    assert ops.post(DEST, {**body, "danger": -1}, format="json").status_code == 400
    r = ops.post(DEST, {**body, "danger": 3}, format="json")
    assert r.status_code == 201 and r.json()["danger_label"] == "high"
    assert r.json()["type"] == "nature" and r.json()["location"]["name"] == "Lima"


@pytest.mark.django_db
def test_p2_4_name_unique_within_location_only(ops, lima, la_paz, types) -> None:  # noqa: ANN001
    body = {"name": "Old town", "type_id": str(types["cultural"].pk), "danger": 0}
    assert ops.post(DEST, {**body, "location_id": str(lima.pk)}, format="json").status_code == 201
    assert ops.post(DEST, {**body, "location_id": str(la_paz.pk)}, format="json").status_code == 201
    r = ops.post(DEST, {**body, "location_id": str(lima.pk)}, format="json")
    assert r.status_code == 400, r.content


@pytest.mark.django_db
def test_p1_2_p1_4_package_fields_are_validated(ops, old_town) -> None:  # noqa: ANN001
    base = {"name": "A", "price": "10.00", "currency": "EUR", "duration_days": 1}
    assert ops.post(PKG, {**base, "price": "abc"}, format="json").status_code == 400
    assert ops.post(PKG, {**base, "price": "-1"}, format="json").status_code == 400
    assert ops.post(PKG, {**base, "currency": "EURO"}, format="json").status_code == 400
    assert ops.post(PKG, {**base, "duration_days": 0}, format="json").status_code == 400
    assert ops.post(PKG, {**base, "description": "x" * 2001}, format="json").status_code == 400
    r = ops.post(PKG, {**base, "currency": "eur", "price": "10.5"}, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["price"] == "10.50" and r.json()["currency"] == "EUR"


@pytest.mark.django_db
def test_p4_1_p4_3_danger_is_derived_and_never_stale(ops, old_town, death_road) -> None:  # noqa: ANN001
    pkg = _pkg(ops, "Andes", [old_town.pk, death_road.pk])
    assert pkg["danger"] == 2 and pkg["danger_label"] == "medium"
    assert [d["position"] for d in pkg["destinations"]] == [1, 2]
    assert pkg["destinations"][1]["name"] == "Death Road ride"

    r = ops.patch(f"{DEST}/{death_road.pk}", {"danger": 3}, format="json")
    assert r.status_code == 200
    detail = ops.get(f"{PKG}/{pkg['id']}").json()
    assert detail["danger"] == 3 and detail["danger_label"] == "high"

    # inactive destinations still count (P4 statement)
    ops.patch(f"{DEST}/{death_road.pk}", {"active": False}, format="json")
    assert ops.get(f"{PKG}/{pkg['id']}").json()["danger"] == 3


@pytest.mark.django_db
def test_p4_2_draft_without_destinations_has_null_danger(ops, old_town) -> None:  # noqa: ANN001
    draft = _pkg(ops, "Draft", [])
    assert draft["danger"] is None and draft["danger_label"] is None
    _pkg(ops, "Real", [old_town.pk])
    names = [p["name"] for p in ops.get(f"{PKG}?danger_max=3").json()["results"]]
    assert names == ["Real"]  # drafts never match a danger filter
    assert len(ops.get(PKG).json()["results"]) == 2


@pytest.mark.django_db
def test_package_list_filters(ops, old_town, death_road) -> None:  # noqa: ANN001
    _pkg(ops, "Calm", [old_town.pk], price="300.00")
    _pkg(ops, "Wild", [old_town.pk, death_road.pk], price="900.00")
    get = lambda q: [p["name"] for p in ops.get(f"{PKG}?{q}").json()["results"]]  # noqa: E731
    assert get("danger_max=0") == ["Calm"]
    assert get("type=adventure") == ["Wild"]
    assert get("max_price=500") == ["Calm"]
    assert get("q=wil") == ["Wild"]
    assert ops.get(f"{PKG}?danger_max=7").status_code == 400
    assert ops.get(f"{PKG}?max_price=cheap").status_code == 400


@pytest.mark.django_db
def test_patch_replaces_itinerary_and_delete_guards(ops, old_town, death_road) -> None:  # noqa: ANN001
    pkg = _pkg(ops, "Andes", [old_town.pk])
    r = ops.patch(
        f"{PKG}/{pkg['id']}",
        {"destination_ids": [str(death_road.pk), str(old_town.pk)], "duration_days": 9},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert [d["name"] for d in r.json()["destinations"]] == ["Death Road ride", "Historic centre"]
    assert r.json()["duration_days"] == 9

    r = ops.delete(f"{DEST}/{old_town.pk}")
    assert r.status_code == 409 and r["Content-Type"].startswith("application/problem+json")
    assert r.json()["packages"][0]["name"] == "Andes"

    assert ops.delete(f"{PKG}/{pkg['id']}").status_code == 204
    assert ops.get(f"{PKG}/{pkg['id']}").status_code == 404
    assert ops.delete(f"{DEST}/{old_town.pk}").status_code == 204  # no live package lists it
    assert Destination.objects.get(pk=old_town.pk).deleted_at is not None


@pytest.mark.django_db
def test_type_delete_409_while_used(ops, old_town, types) -> None:  # noqa: ANN001
    assert ops.delete(f"{TYPES}/{types['cultural'].pk}").status_code == 409
    assert ops.delete(f"{TYPES}/{types['beach'].pk}").status_code == 204


@pytest.mark.django_db
def test_n3_1_package_list_query_count_is_bounded(ops, old_town, death_road) -> None:  # noqa: ANN001
    for i in range(12):
        services.create_package(
            {"name": f"P{i:02d}", "price": 100, "currency": "EUR", "duration_days": 3},
            [old_town.pk, death_road.pk],
        )
    with CaptureQueriesContext(connection) as ctx:
        r = ops.get(PKG)
    assert r.status_code == 200 and len(r.json()["results"]) == 12
    assert len(ctx.captured_queries) <= 7, [q["sql"][:80] for q in ctx.captured_queries]
