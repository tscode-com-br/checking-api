from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from sistema.app.services.user_sync import ResolvedUserActivity, should_enqueue_forms_for_action


SGT = ZoneInfo("Asia/Singapore")


@pytest.mark.parametrize(
    ("latest_action", "event_action", "latest_time", "event_time", "expected"),
    [
        (
            "checkout",
            "checkin",
            datetime(2026, 5, 21, 7, 30, tzinfo=SGT),
            datetime(2026, 5, 21, 8, 0, tzinfo=SGT),
            True,
        ),
        (
            "checkin",
            "checkout",
            datetime(2026, 5, 21, 7, 30, tzinfo=SGT),
            datetime(2026, 5, 21, 8, 0, tzinfo=SGT),
            True,
        ),
        (
            "checkin",
            "checkin",
            datetime(2026, 5, 21, 7, 30, tzinfo=SGT),
            datetime(2026, 5, 21, 8, 0, tzinfo=SGT),
            False,
        ),
        (
            "checkin",
            "checkin",
            datetime(2026, 5, 20, 23, 30, tzinfo=SGT),
            datetime(2026, 5, 21, 8, 0, tzinfo=SGT),
            True,
        ),
        (
            "checkout",
            "checkout",
            datetime(2026, 5, 20, 23, 30, tzinfo=SGT),
            datetime(2026, 5, 21, 8, 0, tzinfo=SGT),
            False,
        ),
    ],
)
def test_should_enqueue_forms_for_action_follows_forms_business_rules(
    latest_action,
    event_action,
    latest_time,
    event_time,
    expected,
):
    latest_activity = ResolvedUserActivity(
        action=latest_action,
        event_time=latest_time,
        local="Web",
        ontime=True,
    )

    should_enqueue = should_enqueue_forms_for_action(
        latest_activity=latest_activity,
        action=event_action,
        event_time=event_time,
        timezone_name="Asia/Singapore",
    )

    assert should_enqueue is expected