from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from typing import Any
from zoneinfo import ZoneInfo

try:
    from bson import ObjectId
except Exception:  # pragma: no cover - local fallback when bson deps are absent
    class ObjectId(str):
        def __new__(cls, value: str = ""):
            return str.__new__(cls, value or "mock-object-id")

from bot.services import mongo_service


DECK_STATUS_QUEUED = "queued"
DECK_STATUS_ACTIVE = "active"
DECK_STATUS_COMPLETED = "completed"

SRS_RESULT_KNOW = "know"
SRS_RESULT_DONT_KNOW = "dontknow"

DEFAULT_FLASHCARDS_DAILY_NEW_LIMIT = 10
DEFAULT_FLASHCARDS_REMINDER_ENABLED = True
DEFAULT_FLASHCARDS_TIMEZONE = "Europe/Berlin"


def get_zoneinfo(tz_name: str | None):
    for candidate in (tz_name, DEFAULT_FLASHCARDS_TIMEZONE, "UTC"):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except Exception:
            continue
    return timezone.utc


def ensure_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_srs_status(card: dict[str, Any]) -> str:
    return card.get("srs_status") or "new"


def get_next_srs_interval(current_interval: int) -> int:
    if current_interval <= 0:
        return 1
    if current_interval == 1:
        return 3
    if current_interval == 3:
        return 7
    if current_interval == 7:
        return 14
    if current_interval == 14:
        return 30
    return current_interval * 2


def is_due_flashcard(card: dict[str, Any], now: datetime) -> bool:
    status = get_srs_status(card)
    if status == "new":
        return True

    next_review = ensure_utc_datetime(card.get("srs_next_review"))
    if next_review is None:
        return True
    return next_review <= now


def is_review_due_flashcard(card: dict[str, Any], now: datetime) -> bool:
    status = get_srs_status(card)
    if status == "new":
        return False

    next_review = ensure_utc_datetime(card.get("srs_next_review"))
    if next_review is None:
        return True
    return next_review <= now


def build_srs_review_update(card: dict[str, Any], result: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = ensure_utc_datetime(now) or datetime.now(timezone.utc)
    current_interval = int(card.get("srs_interval", 0) or 0)

    if result == SRS_RESULT_KNOW:
        next_interval = get_next_srs_interval(current_interval)
        return {
            "$set": {
                "srs_status": "known",
                "srs_interval": next_interval,
                "srs_next_review": now + timedelta(days=next_interval),
                "last_reviewed_at": now,
                "last_review_result": result,
            },
            "$inc": {"srs_correct": 1},
        }

    return {
        "$set": {
            "srs_status": "learning",
            "srs_interval": 1,
            "srs_next_review": now + timedelta(days=1),
            "last_reviewed_at": now,
            "last_review_result": result,
        },
        "$inc": {"srs_incorrect": 1},
    }


def get_user_timezone_name(user_doc: dict[str, Any] | None) -> str:
    tz_name = (user_doc or {}).get("trainer_timezone") or DEFAULT_FLASHCARDS_TIMEZONE
    zone = get_zoneinfo(tz_name)
    return getattr(zone, "key", "UTC")


def get_user_local_date(user_doc: dict[str, Any] | None, dt_value: datetime | None = None) -> date:
    base_dt = ensure_utc_datetime(dt_value) or datetime.now(timezone.utc)
    return base_dt.astimezone(get_zoneinfo(get_user_timezone_name(user_doc))).date()


def get_flashcards_daily_new_limit(user_doc: dict[str, Any] | None) -> int:
    raw_value = (user_doc or {}).get("flashcards_daily_new_limit", DEFAULT_FLASHCARDS_DAILY_NEW_LIMIT)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_FLASHCARDS_DAILY_NEW_LIMIT
    return max(1, min(50, value))


def is_flashcards_reminder_enabled(user_doc: dict[str, Any] | None) -> bool:
    return bool((user_doc or {}).get("flashcards_reminder_enabled", DEFAULT_FLASHCARDS_REMINDER_ENABLED))


def build_cards_by_set(cards: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    cards_by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        set_id = card.get("set_id")
        if set_id:
            cards_by_set[set_id].append(card)
    return cards_by_set


def compute_set_counts(cards: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    new_count = 0
    learning_count = 0
    known_count = 0
    due_count = 0
    latest_reviewed_at: datetime | None = None

    for card in cards:
        status = get_srs_status(card)
        if status == "new":
            new_count += 1
        elif status == "learning":
            learning_count += 1
        else:
            known_count += 1

        if is_review_due_flashcard(card, now):
            due_count += 1

        reviewed_at = ensure_utc_datetime(card.get("last_reviewed_at"))
        if reviewed_at and (latest_reviewed_at is None or reviewed_at > latest_reviewed_at):
            latest_reviewed_at = reviewed_at

    return {
        "card_count": len(cards),
        "new_count": new_count,
        "learning_count": learning_count,
        "known_count": known_count,
        "due_count": due_count,
        "latest_reviewed_at": latest_reviewed_at,
    }


def _derive_completed_at(set_doc: dict[str, Any], stats: dict[str, Any], now: datetime) -> datetime:
    for candidate in (
        stats.get("latest_reviewed_at"),
        ensure_utc_datetime(set_doc.get("last_studied_at")),
        ensure_utc_datetime(set_doc.get("updated_at")),
        ensure_utc_datetime(set_doc.get("created_at")),
        now,
    ):
        if candidate is not None:
            return candidate
    return now


def _build_set_summary(
    set_doc: dict[str, Any],
    stats: dict[str, Any],
    *,
    queue_position: int,
    deck_status: str,
    activated_at: datetime | None,
    completed_at: datetime | None,
    last_studied_at: datetime | None,
) -> dict[str, Any]:
    return {
        "_id": str(set_doc["_id"]),
        "name": set_doc.get("name", ""),
        "created_at": ensure_utc_datetime(set_doc.get("created_at")),
        "updated_at": ensure_utc_datetime(set_doc.get("updated_at")),
        "queue_position": queue_position,
        "deck_status": deck_status,
        "activated_at": activated_at,
        "completed_at": completed_at,
        "last_studied_at": last_studied_at,
        "card_count": stats["card_count"],
        "new_count": stats["new_count"],
        "learning_count": stats["learning_count"],
        "known_count": stats["known_count"],
        "due_count": stats["due_count"],
        "problem_count": stats["learning_count"],
    }


def prepare_autopilot_state(
    raw_sets: list[dict[str, Any]],
    cards_by_set: dict[str, list[dict[str, Any]]],
    *,
    user_doc: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = ensure_utc_datetime(now) or datetime.now(timezone.utc)
    user_doc = user_doc or {}
    today_local = get_user_local_date(user_doc, now)
    daily_new_limit = get_flashcards_daily_new_limit(user_doc)

    computed_sets: list[dict[str, Any]] = []
    first_unresolved_index: int | None = None
    current_active_index: int | None = None
    activation_blocked_today = False

    for index, set_doc in enumerate(raw_sets):
        set_id = str(set_doc["_id"])
        cards = cards_by_set.get(set_id, [])
        stats = compute_set_counts(cards, now)
        has_cards = stats["card_count"] > 0
        unresolved = stats["new_count"] > 0 or stats["learning_count"] > 0

        completed_at = ensure_utc_datetime(set_doc.get("completed_at"))
        if completed_at and get_user_local_date(user_doc, completed_at) == today_local:
            activation_blocked_today = True

        if unresolved and has_cards and first_unresolved_index is None:
            first_unresolved_index = index

        if (
            set_doc.get("deck_status") == DECK_STATUS_ACTIVE
            and unresolved
            and has_cards
            and current_active_index is None
        ):
            current_active_index = index

        computed_sets.append(
            {
                "raw": set_doc,
                "cards": cards,
                "stats": stats,
                "has_cards": has_cards,
                "unresolved": unresolved,
            }
        )

    if current_active_index is not None:
        active_index = current_active_index
    elif activation_blocked_today:
        active_index = None
    else:
        active_index = first_unresolved_index

    total_new = 0
    total_learning = 0
    total_known = 0
    total_due = 0
    prepared_sets: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []

    for index, item in enumerate(computed_sets, start=1):
        set_doc = item["raw"]
        stats = item["stats"]
        total_new += stats["new_count"]
        total_learning += stats["learning_count"]
        total_known += stats["known_count"]
        total_due += stats["due_count"]

        if not item["has_cards"]:
            desired_status = DECK_STATUS_QUEUED
        elif item["unresolved"]:
            desired_status = DECK_STATUS_ACTIVE if active_index == index - 1 else DECK_STATUS_QUEUED
        else:
            desired_status = DECK_STATUS_COMPLETED

        existing_activated_at = ensure_utc_datetime(set_doc.get("activated_at"))
        existing_completed_at = ensure_utc_datetime(set_doc.get("completed_at"))
        existing_last_studied_at = ensure_utc_datetime(set_doc.get("last_studied_at"))

        if desired_status == DECK_STATUS_ACTIVE:
            activated_at = existing_activated_at or now
        else:
            activated_at = existing_activated_at

        if desired_status == DECK_STATUS_COMPLETED:
            completed_at = existing_completed_at or _derive_completed_at(set_doc, stats, now)
        else:
            completed_at = None

        last_studied_at = existing_last_studied_at or stats["latest_reviewed_at"]

        summary = _build_set_summary(
            set_doc,
            stats,
            queue_position=index,
            deck_status=desired_status,
            activated_at=activated_at,
            completed_at=completed_at,
            last_studied_at=last_studied_at,
        )
        prepared_sets.append(summary)

        changed = (
            set_doc.get("deck_status") != desired_status
            or int(set_doc.get("queue_position", 0) or 0) != index
            or ensure_utc_datetime(set_doc.get("activated_at")) != activated_at
            or ensure_utc_datetime(set_doc.get("completed_at")) != completed_at
            or ensure_utc_datetime(set_doc.get("last_studied_at")) != last_studied_at
        )
        if changed:
            update_doc: dict[str, Any] = {
                "$set": {
                    "deck_status": desired_status,
                    "queue_position": index,
                    "updated_at": now,
                }
            }
            if activated_at is not None:
                update_doc["$set"]["activated_at"] = activated_at
            if completed_at is not None:
                update_doc["$set"]["completed_at"] = completed_at
            if last_studied_at is not None:
                update_doc["$set"]["last_studied_at"] = last_studied_at

            unset_fields: dict[str, str] = {}
            if activated_at is None and set_doc.get("activated_at") is not None:
                unset_fields["activated_at"] = ""
            if completed_at is None and set_doc.get("completed_at") is not None:
                unset_fields["completed_at"] = ""
            if last_studied_at is None and set_doc.get("last_studied_at") is not None:
                unset_fields["last_studied_at"] = ""
            if unset_fields:
                update_doc["$unset"] = unset_fields

            updates.append({"set_id": set_doc["_id"], "update": update_doc})

    active_set = next((item for item in prepared_sets if item["deck_status"] == DECK_STATUS_ACTIVE), None)
    next_set = None
    if active_set is not None:
        for item in prepared_sets:
            if (
                item["queue_position"] > active_set["queue_position"]
                and item["deck_status"] == DECK_STATUS_QUEUED
                and item["card_count"] > 0
                and (item["new_count"] > 0 or item["learning_count"] > 0)
            ):
                next_set = item
                break
    else:
        next_set = next(
            (
                item
                for item in prepared_sets
                if item["deck_status"] == DECK_STATUS_QUEUED
                and item["card_count"] > 0
                and (item["new_count"] > 0 or item["learning_count"] > 0)
            ),
            None,
        )

    today_due_count = sum(item["due_count"] for item in prepared_sets)
    today_new_count = min(active_set["new_count"], daily_new_limit) if active_set else 0

    return {
        "sets": prepared_sets,
        "active_set": active_set,
        "next_set": next_set,
        "today_due_count": today_due_count,
        "today_new_count": today_new_count,
        "daily_new_limit": daily_new_limit,
        "can_activate_next_today": False,
        "activation_blocked_today": activation_blocked_today,
        "today_local_date": today_local.isoformat(),
        "timezone": get_user_timezone_name(user_doc),
        "totals": {
            "new": total_new,
            "learning": total_learning,
            "known": total_known,
            "due": total_due,
        },
        "updates": updates,
    }


async def get_user_flashcards_overview(
    user_id: int,
    *,
    now: datetime | None = None,
    user_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not mongo_service.is_ready():
        raise RuntimeError("Mongo DB is not initialized")

    now = ensure_utc_datetime(now) or datetime.now(timezone.utc)
    users_collection = mongo_service.db().users
    flashcard_sets_collection = mongo_service.db().flashcard_sets
    flashcards_collection = mongo_service.db().flashcards

    user_doc = user_doc or await users_collection.find_one({"telegram_id": user_id}) or {}
    raw_sets = await flashcard_sets_collection.find({"user_id": user_id}).sort("created_at", 1).to_list(length=500)
    cards = await flashcards_collection.find({"user_id": user_id}).to_list(length=10000)
    cards_by_set = build_cards_by_set(cards)

    overview = prepare_autopilot_state(raw_sets, cards_by_set, user_doc=user_doc, now=now)
    for update in overview["updates"]:
        await flashcard_sets_collection.update_one({"_id": update["set_id"]}, update["update"])

    overview["cards_by_set"] = cards_by_set
    overview["user_doc"] = user_doc
    overview["now"] = now
    return overview


def _card_sort_key(card: dict[str, Any]) -> tuple[Any, ...]:
    next_review = ensure_utc_datetime(card.get("srs_next_review"))
    created_at = ensure_utc_datetime(card.get("created_at"))
    return (
        next_review or datetime.min.replace(tzinfo=timezone.utc),
        created_at or datetime.min.replace(tzinfo=timezone.utc),
        str(card.get("_id", "")),
    )


def build_today_session_cards(overview: dict[str, Any]) -> list[dict[str, Any]]:
    now = overview["now"]
    cards_by_set = overview["cards_by_set"]
    active_set_id = overview["active_set"]["_id"] if overview["active_set"] else None
    daily_new_limit = overview["daily_new_limit"]

    review_cards: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    active_due_cards: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    active_new_cards: list[tuple[int, dict[str, Any], dict[str, Any]]] = []

    for set_summary in overview["sets"]:
        queue_position = int(set_summary["queue_position"])
        for card in cards_by_set.get(set_summary["_id"], []):
            status = get_srs_status(card)
            if set_summary["_id"] == active_set_id:
                if status == "new":
                    active_new_cards.append((queue_position, set_summary, card))
                elif is_review_due_flashcard(card, now):
                    active_due_cards.append((queue_position, set_summary, card))
            elif is_review_due_flashcard(card, now):
                review_cards.append((queue_position, set_summary, card))

    review_cards.sort(key=lambda item: (item[0],) + _card_sort_key(item[2]))
    active_due_cards.sort(key=lambda item: (item[0],) + _card_sort_key(item[2]))
    active_new_cards.sort(key=lambda item: (item[0],) + _card_sort_key(item[2]))

    session_cards = review_cards + active_due_cards + active_new_cards[:daily_new_limit]
    payload: list[dict[str, Any]] = []

    for _, set_summary, card in session_cards:
        status = get_srs_status(card)
        payload.append(
            {
                "_id": str(card["_id"]),
                "set_id": card.get("set_id"),
                "set_name": set_summary["name"],
                "deck_status": set_summary["deck_status"],
                "queue_position": set_summary["queue_position"],
                "front": card.get("front", ""),
                "back": card.get("back", ""),
                "example": card.get("example", ""),
                "has_image": bool(card.get("image_url")),
                "srs_status": status,
                "session_type": "new" if status == "new" and card.get("set_id") == active_set_id else "due",
                "last_reviewed_at": ensure_utc_datetime(card.get("last_reviewed_at")),
                "last_review_result": card.get("last_review_result"),
            }
        )

    return payload


def serialize_flashcard_overview(overview: dict[str, Any]) -> dict[str, Any]:
    def serialize_set(item: dict[str, Any] | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return {
            "_id": item["_id"],
            "name": item["name"],
            "queue_position": item["queue_position"],
            "deck_status": item["deck_status"],
            "created_at": item["created_at"].isoformat() if item["created_at"] else None,
            "updated_at": item["updated_at"].isoformat() if item["updated_at"] else None,
            "activated_at": item["activated_at"].isoformat() if item["activated_at"] else None,
            "completed_at": item["completed_at"].isoformat() if item["completed_at"] else None,
            "last_studied_at": item["last_studied_at"].isoformat() if item["last_studied_at"] else None,
            "card_count": item["card_count"],
            "new_count": item["new_count"],
            "learning_count": item["learning_count"],
            "known_count": item["known_count"],
            "due_count": item["due_count"],
            "problem_count": item["problem_count"],
        }

    return {
        "new": overview["totals"]["new"],
        "learning": overview["totals"]["learning"],
        "known": overview["totals"]["known"],
        "due": overview["totals"]["due"],
        "today_due_count": overview["today_due_count"],
        "today_new_count": overview["today_new_count"],
        "daily_new_limit": overview["daily_new_limit"],
        "can_activate_next_today": overview["can_activate_next_today"],
        "activation_blocked_today": overview["activation_blocked_today"],
        "today_local_date": overview["today_local_date"],
        "timezone": overview["timezone"],
        "active_set": serialize_set(overview["active_set"]),
        "next_set": serialize_set(overview["next_set"]),
    }


async def review_session_card(user_id: int, card_id: str, result: str, *, now: datetime | None = None) -> None:
    if result not in {SRS_RESULT_KNOW, SRS_RESULT_DONT_KNOW}:
        raise ValueError("Unsupported flashcard review result")

    if not mongo_service.is_ready():
        raise RuntimeError("Mongo DB is not initialized")

    now = ensure_utc_datetime(now) or datetime.now(timezone.utc)
    cards_collection = mongo_service.db().flashcards
    sets_collection = mongo_service.db().flashcard_sets

    card = await cards_collection.find_one({"_id": ObjectId(card_id), "user_id": user_id})
    if not card:
        raise LookupError("Card not found")

    update_doc = build_srs_review_update(card, result, now=now)
    await cards_collection.update_one({"_id": ObjectId(card_id)}, update_doc)

    if card.get("set_id"):
        await sets_collection.update_one(
            {"_id": ObjectId(card["set_id"]), "user_id": user_id},
            {"$set": {"last_studied_at": now, "updated_at": now}},
        )

    await mongo_service.update_flashcard_daily_stats(user_id, result)
    await get_user_flashcards_overview(user_id, now=now)
