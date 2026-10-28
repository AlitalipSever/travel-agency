# Query plan: bookable packages search (P5.7, N2.6)

Status: measured 2026-10-27 on the compose PostgreSQL 16 (laptop, Colima, 4 CPU), API in the
container, synthetic data from `python manage.py load_bookable_fixture`.

## What is measured

`GET /api/v1/packages/bookable?from=<today>&to=<today+30>&danger=2`, implemented in
`catalogue/bookable.py` as two queries per page (N3.1):

1. **Packages.** Active, not deleted, `MAX(destination.danger) <= 2` (ADR 0003), and
   `EXISTS` a planned departure inside the range, on or after today in the agency's zone,
   with `capacity > SUM(confirmed seats)` (ADR 0002). Ordered by the earliest matching
   departure, name, id; `LIMIT 20`.
2. **Departures of the page.** The matching departures of those 20 packages with
   `remaining_seats` and `ends_on` (ADR 0011).

Pagination adds a `COUNT(*)` of query 1 without the limit.

## Data

| Table | Rows |
|---|---|
| packages | 2,001 (5 % inactive) |
| package destinations | about 5,000 over 200 destinations |
| departures | 20,000 (10 per package, spread over -60 to +400 days, 3 % cancelled) |
| bookings | 9,866 confirmed, seats random up to capacity (some departures sold out) |
| matches for the query | 546 packages |

## Result

| Measurement | Value |
|---|---|
| query 1, `EXPLAIN ANALYZE` execution time | 21 to 59 ms |
| query 1 + query 2 in process, 50 runs | median 10 ms, p95 15 ms |
| HTTP end to end (runserver, DEBUG, token auth, count + page + departures), warm | 67 to 75 ms |
| HTTP end to end on the seed data (13 capitals, a handful of packages) | 13 to 66 ms |

P5.7 asks for p95 under 100 ms on the seed data and under 300 ms with thousands of packages
and tens of thousands of departures: both hold with margin.

## The index that mattered

The first measurement, with only the unique `(package_id, starts_on)` and the partial
`(starts_on) WHERE status = 'planned'` indexes, took **1,340 ms** for query 1 (p95 764 ms for
the pair). The plan showed why: the correlated probe "does this package have a matching
departure" chose the date index and then filtered by package, removing 1,312 rows on every
one of its 546 loops (668,000 buffer hits).

Adding `departure_pkg_planned_idx` on `(package_id, starts_on) WHERE status = 'planned'`
(migration `catalogue.0003`) turns each probe into a two-row index scan; query 1 dropped to
21 ms (11,584 buffer hits). The partial index is small (planned rows only) and is exactly the
shape of the probe, so the planner prefers it over the unique index.

## Plan of query 1 after the index (buffers omitted)

```
Limit  (cost=37691.92..38358.52 rows=20 width=74) (actual time=58.836..58.914 rows=20 loops=1)
  ->  Result  (cost=37691.92..48324.19 rows=319 width=74) (actual time=58.835..58.912 rows=20 loops=1)
        ->  Sort  (cost=37691.92..37692.71 rows=319 width=73) (actual time=58.798..58.803 rows=20 loops=1)
              Sort Key: ((SubPlan 2)), catalogue_package.name, catalogue_package.id
              Sort Method: top-N heapsort  Memory: 29kB
              ->  GroupAggregate  (cost=32339.04..37683.43 rows=319 width=73) (actual time=56.015..58.567 rows=546 loops=1)
                    Group Key: catalogue_package.id
                    Filter: (max(catalogue_destination.danger) <= 2)
                    Rows Removed by Filter: 381
                    ->  Sort  (cost=32339.04..32345.00 rows=2385 width=69) (actual time=55.944..56.040 rows=2309 loops=1)
                          Sort Key: catalogue_package.id
                          Sort Method: quicksort  Memory: 313kB
                          ->  Hash Left Join  (cost=181.35..32205.24 rows=2385 width=69) (actual time=17.387..55.165 rows=2309 loops=1)
                                Hash Cond: (catalogue_package.id = catalogue_packagedestination.package_id)
                                ->  Index Scan using package_active_idx on catalogue_package  (cost=0.28..31993.14 rows=957 width=67) (actual time=3.292..40.627 rows=927 loops=1)
                                      Index Cond: (active = true)
                                      Filter: ((deleted_at IS NULL) AND (SubPlan 3))
                                      Rows Removed by Filter: 988
                                      SubPlan 3
                                        ->  Limit  (cost=16.63..16.66 rows=1 width=22) (actual time=0.019..0.019 rows=0 loops=1915)
                                              ->  GroupAggregate  (cost=16.63..16.66 rows=1 width=22) (actual time=0.018..0.018 rows=0 loops=1915)
                                                    Group Key: u0_2.id
                                                    Filter: (u0_2.capacity > COALESCE(sum(u1_2.seats) FILTER (WHERE (u1_2.status = 'confirmed'::text)), '0'::bigint))
                                                    Rows Removed by Filter: 0
                                                    ->  Sort  (cost=16.63..16.64 rows=1 width=30) (actual time=0.018..0.018 rows=1 loops=1915)
                                                          Sort Key: u0_2.id
                                                          Sort Method: quicksort  Memory: 25kB
                                                          ->  Nested Loop Left Join  (cost=0.57..16.62 rows=1 width=30) (actual time=0.015..0.018 rows=1 loops=1915)
                                                                ->  Index Scan using departure_pkg_planned_idx on catalogue_departure u0_2  (cost=0.29..8.31 rows=1 width=18) (actual time=0.006..0.006 rows=1 loops=1915)
                                                                      Index Cond: ((package_id = catalogue_package.id) AND (starts_on >= '2026-10-27'::date) AND (starts_on <= '2026-11-26'::date))
                                                                ->  Index Scan using booking_booking_departure_id_a51e0b6b on booking_booking u1_2  (cost=0.29..8.30 rows=1 width=28) (actual time=0.017..0.017 rows=1 loops=1252)
                                                                      Index Cond: (departure_id = u0_2.id)
                                ->  Hash  (cost=118.75..118.75 rows=4986 width=18) (actual time=13.951..13.953 rows=4986 loops=1)
                                      Buckets: 8192  Batches: 1  Memory Usage: 308kB
                                      ->  Hash Left Join  (cost=8.52..118.75 rows=4986 width=18) (actual time=0.093..13.167 rows=4986 loops=1)
                                            Hash Cond: (catalogue_packagedestination.destination_id = catalogue_destination.id)
                                            ->  Seq Scan on catalogue_packagedestination  (cost=0.00..96.86 rows=4986 width=32) (actual time=0.008..11.059 rows=4986 loops=1)
                                            ->  Hash  (cost=6.01..6.01 rows=201 width=18) (actual time=0.059..0.059 rows=201 loops=1)
                                                  Buckets: 1024  Batches: 1  Memory Usage: 18kB
                                                  ->  Seq Scan on catalogue_destination  (cost=0.00..6.01 rows=201 width=18) (actual time=0.004..0.029 rows=201 loops=1)
                    SubPlan 2
                      ->  Limit  (cost=16.63..16.66 rows=1 width=22) (actual time=0.004..0.004 rows=1 loops=546)
                            ->  GroupAggregate  (cost=16.63..16.66 rows=1 width=22) (actual time=0.003..0.004 rows=1 loops=546)
                                  Group Key: u0_1.capacity
                                  Filter: (u0_1.capacity > COALESCE(sum(u1_1.seats) FILTER (WHERE (u1_1.status = 'confirmed'::text)), '0'::bigint))
                                  Rows Removed by Filter: 0
                                  ->  Sort  (cost=16.63..16.64 rows=1 width=34) (actual time=0.003..0.003 rows=1 loops=546)
                                        Sort Key: u0_1.capacity
                                        Sort Method: quicksort  Memory: 25kB
                                        ->  Nested Loop Left Join  (cost=0.57..16.62 rows=1 width=34) (actual time=0.002..0.003 rows=1 loops=546)
                                              ->  Index Scan using departure_pkg_planned_idx on catalogue_departure u0_1  (cost=0.29..8.31 rows=1 width=38) (actual time=0.001..0.001 rows=1 loops=546)
                                                    Index Cond: ((package_id = catalogue_package.id) AND (starts_on >= '2026-10-27'::date) AND (starts_on <= '2026-11-26'::date))
                                              ->  Index Scan using booking_booking_departure_id_a51e0b6b on booking_booking u1_1  (cost=0.29..8.30 rows=1 width=28) (actual time=0.001..0.001 rows=0 loops=718)
                                                    Index Cond: (departure_id = u0_1.id)
        SubPlan 1
          ->  Limit  (cost=16.63..16.66 rows=1 width=22) (actual time=0.005..0.005 rows=1 loops=20)
                ->  GroupAggregate  (cost=16.63..16.66 rows=1 width=22) (actual time=0.005..0.005 rows=1 loops=20)
                      Group Key: u0.id
                      Filter: (u0.capacity > COALESCE(sum(u1.seats) FILTER (WHERE (u1.status = 'confirmed'::text)), '0'::bigint))
                      ->  Sort  (cost=16.63..16.64 rows=1 width=30) (actual time=0.004..0.005 rows=1 loops=20)
                            Sort Key: u0.id
                            Sort Method: quicksort  Memory: 25kB
                            ->  Nested Loop Left Join  (cost=0.57..16.62 rows=1 width=30) (actual time=0.003..0.003 rows=1 loops=20)
                                  ->  Index Scan using departure_pkg_planned_idx on catalogue_departure u0  (cost=0.29..8.31 rows=1 width=18) (actual time=0.001..0.001 rows=1 loops=20)
                                        Index Cond: ((package_id = catalogue_package.id) AND (starts_on >= '2026-10-27'::date) AND (starts_on <= '2026-11-26'::date))
                                  ->  Index Scan using booking_booking_departure_id_a51e0b6b on booking_booking u1  (cost=0.29..8.30 rows=1 width=28) (actual time=0.001..0.001 rows=0 loops=29)
                                        Index Cond: (departure_id = u0.id)
Planning:
Planning Time: 20.368 ms
Execution Time: 59.175 ms
```

## Reading the plan

- `Index Scan using package_active_idx` with `SubPlan 3` as a filter: the `EXISTS` probe per
  active package (1,915 loops, 0.02 ms each).
- `GroupAggregate ... Filter: (max(danger) <= 2)`: the derived danger, computed once per
  package in the same statement; 381 packages removed here.
- `Sort Key: ((SubPlan 2)), name, id` with `top-N heapsort`: the earliest matching departure
  per package (`SubPlan 2`, 546 loops) feeds the order; only the page is kept in memory.
- `SubPlan 1` (20 loops): the same minimum re-evaluated for the 20 output rows.

## What would change at the next order of magnitude

- Tens of thousands of packages: the `EXISTS` probe is still per package; the next step is
  to invert the query (aggregate the departures of the range once, grouped by package, and
  join the packages to that set). It is a change inside `bookable.py` only.
- A stored `remaining_seats` counter (ADR 0002, option 3) only if the bookings aggregate
  shows up in the plan; today it is 0.001 ms per departure.
- Re-run: `make up`, `python manage.py load_bookable_fixture`, `... --explain`, `... --clean`.
