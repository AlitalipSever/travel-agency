# OpenWeatherMap fixtures

Raw 2.5 payloads used by tests and by the mock client when no API key is set.
The current files are placeholders in the real shape; `python manage.py record_fixtures
lima=-12.046,-77.043 la_paz=-16.4897,-68.1193` replaces them with live payloads once the key
is active. Never commit a payload that contains the key (the API echoes nothing, but check).
