# 0013 Daily summary rules and time handling

Status: proposed
Date: 2026-10-26
Addresses: W2, W3; A11, A12, A13

## Context

The brief wants, per day, an average temperature and a condition such as sunny or cloudy.
Weather services and applications do not reduce a day to one number or to the most frequent
condition: they report min, max and mean, pick the condition from the daytime hours and let
significant weather (rain, storms) dominate. Days must be the location's calendar days, and
several South American countries observe daylight saving time (Chile, Paraguay), others do not.

## Options

Temperature: (a) mean only; (b) mean, min and max.
Condition: (a) most frequent over 24 hours; (b) most significant over daytime slots, most
frequent as tie break; (c) the midday slot only.
Day boundary: (a) UTC day; (b) the location's local day via a fixed offset; (c) the location's
local day via an IANA time zone.

## Decision

Temperature (b): `temp_avg` is the brief's number, `temp_min` and `temp_max` stand beside it.
Condition (b): daytime slots (`sys.pod = d` from the upstream, else 06:00 to 18:00 local),
priority thunderstorm > rain > snow > fog, else the most frequent of cloudy and clear with
cloudy on a tie; with no daytime slot all slots are used. Upstream condition codes map to the
closed set thunderstorm, rain, snow, fog, cloudy, clear, unknown (unmapped codes yield unknown,
never an error); 800 to 802 count as clear, 803 and 804 as cloudy. Precipitation probability
(`pop`) is not used in the rule in this iteration; a threshold would be a judgement call and is
left to the roadmap. The same rules apply to observed and forecast slots; temperatures are
reported to one decimal.
Day boundary (c): every timestamp is stored in UTC (`timestamptz`); each known location carries
an IANA zone name (`America/Santiago`); summaries convert samples to the local calendar day in
code, a slot belonging to the day in which it starts; the response states the zone and the
local date. Ad hoc coordinates use the offset the
upstream returns with the forecast, which is correct for the day of the request.

## Consequences

The forecast response has `today` (full for known locations once samples exist, else partial)
and `days`, five entries from tomorrow, the last one `partial` when the 120 hour window cuts it.
Each day reports `observed_samples`, `forecast_samples`, `partial`, and the response carries
`timezone`, `as_of` and `source`. A daylight saving transition day has 7 or 9 slots; the sample
counts show it, no special case is needed. The label set and the priority order live in one
module with a table test.
