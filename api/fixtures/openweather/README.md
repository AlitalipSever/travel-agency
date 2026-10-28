# OpenWeatherMap fixtures

Raw 2.5 payloads recorded live with `python manage.py record_fixtures lima=-12.046,-77.043
la_paz=-16.4897,-68.1193` (first recording 2026-10-27). Used by tests and by the mock client when
no API key is set; the mock shifts timestamps to now. Re-run the command to refresh. The payloads
carry no key; check before committing a new recording.
