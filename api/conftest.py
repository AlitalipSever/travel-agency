"""Project-wide pytest setup.

Celery reads its configuration lazily; under pytest the app can be configured before
pytest-django switches to the test settings, so the eager flags are applied here explicitly.
No task ever reaches a broker from a test.
"""

import pytest


@pytest.fixture(autouse=True, scope="session")
def _celery_eager() -> None:
    from config.celery import app

    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    app.conf.task_store_eager_result = False
