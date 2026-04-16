from datetime import datetime, timedelta, timezone
from itertools import count

from bot.services.flashcards_service import (
    build_cards_by_set,
    build_srs_review_update,
    build_today_session_cards,
    prepare_autopilot_state,
)


_ID_COUNTER = count(1)


def make_set(name: str, created_at: datetime, **extra):
    return {
        "_id": f"set-{next(_ID_COUNTER)}",
        "name": name,
        "created_at": created_at,
        "updated_at": created_at,
        **extra,
    }


def make_card(set_id: str, created_at: datetime, **extra):
    return {
        "_id": f"card-{next(_ID_COUNTER)}",
        "set_id": set_id,
        "created_at": created_at,
        "front": extra.pop("front", "front"),
        "back": extra.pop("back", "back"),
        **extra,
    }


def test_first_non_empty_unresolved_set_becomes_active():
    now = datetime(2026, 4, 16, 9, 0, tzinfo=timezone.utc)
    empty_set = make_set("Empty", now - timedelta(days=3))
    first_set = make_set("Deck A", now - timedelta(days=2))
    second_set = make_set("Deck B", now - timedelta(days=1))

    cards = [
        make_card(str(first_set["_id"]), now - timedelta(days=2), srs_status="new"),
        make_card(str(first_set["_id"]), now - timedelta(days=2), srs_status="new"),
        make_card(str(second_set["_id"]), now - timedelta(days=1), srs_status="new"),
    ]
    overview = prepare_autopilot_state(
        [empty_set, first_set, second_set],
        build_cards_by_set(cards),
        user_doc={"trainer_timezone": "Europe/Berlin", "flashcards_daily_new_limit": 10},
        now=now,
    )

    statuses = {item["name"]: item["deck_status"] for item in overview["sets"]}
    assert statuses == {"Empty": "queued", "Deck A": "active", "Deck B": "queued"}
    assert overview["active_set"]["name"] == "Deck A"
    assert overview["next_set"]["name"] == "Deck B"
    assert overview["today_new_count"] == 2


def test_due_cards_from_completed_deck_stay_in_today_session_before_active_new_cards():
    now = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)
    completed_set = make_set("Deck 1", now - timedelta(days=3))
    active_set = make_set("Deck 2", now - timedelta(days=2))

    cards = [
        make_card(
            str(completed_set["_id"]),
            now - timedelta(days=3),
            srs_status="known",
            srs_interval=7,
            srs_next_review=now - timedelta(hours=1),
        ),
        make_card(str(active_set["_id"]), now - timedelta(days=2), srs_status="new"),
    ]
    overview = prepare_autopilot_state(
        [completed_set, active_set],
        build_cards_by_set(cards),
        user_doc={"trainer_timezone": "Europe/Berlin", "flashcards_daily_new_limit": 10},
        now=now,
    )

    assert overview["sets"][0]["deck_status"] == "completed"
    assert overview["sets"][1]["deck_status"] == "active"
    assert overview["today_due_count"] == 1
    assert overview["today_active_due_count"] == 0
    assert overview["today_backlog_due_count"] == 1
    assert overview["today_new_count"] == 1

    overview["cards_by_set"] = build_cards_by_set(cards)
    overview["now"] = now
    session_cards = build_today_session_cards(overview)
    assert [item["set_name"] for item in session_cards] == ["Deck 1", "Deck 2"]
    assert [item["session_type"] for item in session_cards] == ["due", "new"]


def test_overview_splits_active_due_from_backlog_due():
    now = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)
    completed_set = make_set("Deck 1", now - timedelta(days=3))
    active_set = make_set("Deck 2", now - timedelta(days=2))

    cards = [
        make_card(
            str(completed_set["_id"]),
            now - timedelta(days=3),
            srs_status="known",
            srs_interval=7,
            srs_next_review=now - timedelta(hours=1),
        ),
        make_card(
            str(active_set["_id"]),
            now - timedelta(days=2),
            srs_status="learning",
            srs_interval=1,
            srs_next_review=now - timedelta(minutes=5),
        ),
        make_card(str(active_set["_id"]), now - timedelta(days=2), srs_status="new"),
    ]

    overview = prepare_autopilot_state(
        [completed_set, active_set],
        build_cards_by_set(cards),
        user_doc={"trainer_timezone": "Europe/Berlin", "flashcards_daily_new_limit": 10},
        now=now,
    )

    assert overview["today_due_count"] == 2
    assert overview["today_total_due_count"] == 2
    assert overview["today_active_due_count"] == 1
    assert overview["today_backlog_due_count"] == 1
    assert overview["today_new_count"] == 1


def test_next_deck_is_blocked_until_tomorrow_after_completion_today():
    now = datetime(2026, 4, 16, 18, 30, tzinfo=timezone.utc)
    completed_today = make_set(
        "Deck 1",
        now - timedelta(days=4),
        deck_status="completed",
        completed_at=now - timedelta(hours=1),
    )
    queued_next = make_set("Deck 2", now - timedelta(days=2))
    cards = [
        make_card(
            str(completed_today["_id"]),
            now - timedelta(days=4),
            srs_status="known",
            srs_interval=14,
            srs_next_review=now + timedelta(days=1),
        ),
        make_card(str(queued_next["_id"]), now - timedelta(days=2), srs_status="new"),
    ]

    overview = prepare_autopilot_state(
        [completed_today, queued_next],
        build_cards_by_set(cards),
        user_doc={"trainer_timezone": "Europe/Berlin", "flashcards_daily_new_limit": 10},
        now=now,
    )

    assert overview["active_set"] is None
    assert overview["next_set"]["name"] == "Deck 2"
    assert overview["activation_blocked_today"] is True
    assert overview["today_new_count"] == 0


def test_session_limits_new_cards_to_daily_budget():
    now = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)
    active_set = make_set("Deck A", now - timedelta(days=3))
    queued_set = make_set("Deck B", now - timedelta(days=2))
    cards = [
        make_card(str(active_set["_id"]), now - timedelta(days=2), srs_status="new", front=f"n-{idx}")
        for idx in range(12)
    ]
    cards.append(
        make_card(
            str(queued_set["_id"]),
            now - timedelta(days=1),
            srs_status="learning",
            srs_next_review=now - timedelta(minutes=10),
            front="due-card",
        )
    )

    overview = prepare_autopilot_state(
        [active_set, queued_set],
        build_cards_by_set(cards),
        user_doc={"trainer_timezone": "Europe/Berlin", "flashcards_daily_new_limit": 10},
        now=now,
    )
    overview["cards_by_set"] = build_cards_by_set(cards)
    overview["now"] = now

    session_cards = build_today_session_cards(overview)
    assert len(session_cards) == 11
    assert session_cards[0]["session_type"] == "due"
    assert sum(1 for item in session_cards if item["session_type"] == "new") == 10


def test_srs_interval_progression_is_preserved():
    now = datetime(2026, 4, 16, 12, 0, tzinfo=timezone.utc)
    card = {"srs_interval": 14}

    know_update = build_srs_review_update(card, "know", now=now)
    dont_know_update = build_srs_review_update(card, "dontknow", now=now)

    assert know_update["$set"]["srs_interval"] == 30
    assert know_update["$set"]["srs_next_review"] == now + timedelta(days=30)
    assert dont_know_update["$set"]["srs_interval"] == 1
    assert dont_know_update["$set"]["srs_next_review"] == now + timedelta(days=1)


if __name__ == "__main__":
    test_first_non_empty_unresolved_set_becomes_active()
    test_due_cards_from_completed_deck_stay_in_today_session_before_active_new_cards()
    test_overview_splits_active_due_from_backlog_due()
    test_next_deck_is_blocked_until_tomorrow_after_completion_today()
    test_session_limits_new_cards_to_daily_budget()
    test_srs_interval_progression_is_preserved()
    print("flashcards_service_tests_ok")
