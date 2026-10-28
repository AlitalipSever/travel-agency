# 0013 Daily summary rules and time handling

Status: accepted (2026-10-27)
Date: 2026-10-26
Addresses: W2, W3; A11, A12, A13

## Context

The brief wants, per day, an average temperature and a condition such as sunny or cloudy.

Weather services and applications do not reduce a day to one number, or to the most frequent
condition. Instead they:

- report min, max and mean;
- pick the condition from the daytime hours;
- let significant weather (rain, storms) dominate.

Days must be the location's calendar days. Several South American countries observe daylight
saving time (Chile, Paraguay); others do not.

## Options

Temperature:

- (a) mean only;
- (b) mean, min and max.

Condition:

- (a) most frequent over 24 hours;
- (b) most significant over daytime slots, with most frequent as tie break;
- (c) the midday slot only.

Day boundary:

- (a) UTC day;
- (b) the location's local day via a fixed offset;
- (c) the location's local day via an IANA time zone (a named zone from the standard time zone
  database, which includes daylight saving rules).

## Decision

**Temperature (b).** `temp_avg` is the brief's number. `temp_min` and `temp_max` stand beside
it.

**Condition (b).**

- Daytime slots are used: `sys.pod = d` from the upstream, else 06:00 to 18:00 local.
- Priority is thunderstorm > rain > snow > fog.
- Otherwise the most frequent of cloudy and clear wins, with cloudy on a tie.
- With no daytime slot, all slots are used.
- Upstream condition codes map to the closed set thunderstorm, rain, snow, fog, cloudy, clear,
  unknown. Unmapped codes yield unknown, never an error.
- 800 to 802 count as clear; 803 and 804 count as cloudy.
- Precipitation probability (`pop`) is not used in the rule in this iteration. A threshold
  would be a judgement call, so it is left to the roadmap.
- The same rules apply to observed and forecast slots.
- Temperatures are reported to one decimal.

**Day boundary (c).**

- Every timestamp is stored in UTC (`timestamptz`).
- Each known location carries an IANA zone name (`America/Santiago`).
- Summaries convert samples to the local calendar day in code. A slot belongs to the day in
  which it starts.
- The response states the zone and the local date.
- Ad hoc coordinates use the offset the upstream returns with the forecast. That offset is
  correct for the day of the request.

## Consequences

The forecast response has these parts:

- `today`: full for known locations once samples exist, else partial.
- `days`: five entries from tomorrow. The last one is `partial` when the 120 hour window cuts it.

Each day reports `observed_samples`, `forecast_samples` and `partial`. The response carries
`timezone`, `as_of` and `source`.

A daylight saving transition day has 7 or 9 slots. The sample counts show it, so no special
case is needed.

The label set and the priority order live in one module, with a table test.
