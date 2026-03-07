"""
Web server for Telegram Mini App (Web App) - Flashcards
Serves static files and API endpoints for flashcard management
"""

import os
import hashlib
import hmac
import json
import logging
import base64
from urllib.parse import parse_qsl
from datetime import datetime, timezone, timedelta
from pathlib import Path
import random

from aiohttp import web
from bson import ObjectId

from bot.config import settings
from bot.services import mongo_service, cloudinary_service
from bot.services.database_service import UserService
from bot.models.database import async_session_maker

logger = logging.getLogger(__name__)

# Get the webapp directory path
WEBAPP_DIR = Path(__file__).parent
STATIC_DIR = WEBAPP_DIR / "static"
TEMPLATES_DIR = WEBAPP_DIR / "templates"


def validate_telegram_data(init_data: str) -> dict | None:
    """
    Validate Telegram WebApp init data and extract user info.
    Returns user data if valid, None otherwise.
    """
    if not init_data:
        return None
    
    try:
        # Parse init data
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        
        # Get hash from data
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None
        
        # Sort and create data check string
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # Create secret key
        secret_key = hmac.new(
            b"WebAppData",
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Validate hash
        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("Invalid hash in Telegram init data")
            return None
        
        # Parse user data
        user_data = parsed_data.get('user')
        if user_data:
            return json.loads(user_data)
        
        return None
        
    except Exception as e:
        logger.error(f"Error validating Telegram data: {e}")
        return None


def get_user_id_from_request(request: web.Request) -> int | None:
    """Extract and validate user ID from request headers."""
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    user_data = validate_telegram_data(init_data)
    
    if user_data and 'id' in user_data:
        return user_data['id']
    
    return None


def get_srs_status(card: dict) -> str:
    """Normalize SRS status for cards created before SRS fields existed."""
    return card.get("srs_status") or "new"


def get_next_srs_interval(current_interval: int) -> int:
    """Return the next review interval for a known card."""
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


def is_due_flashcard(card: dict, now: datetime) -> bool:
    """Return True if a card should appear in the global review session."""
    status = get_srs_status(card)
    if status == "new":
        return True

    next_review = card.get("srs_next_review")
    if next_review is None:
        return True

    # Old cards may have naive datetimes stored — treat them as UTC
    if next_review.tzinfo is None:
        next_review = next_review.replace(tzinfo=timezone.utc)

    return next_review <= now


def build_srs_review_update(card: dict, result: str) -> dict:
    """Build the MongoDB update document for a self-rated flashcard review."""
    now = datetime.now(timezone.utc)
    current_interval = int(card.get("srs_interval", 0) or 0)

    if result == "know":
        next_interval = get_next_srs_interval(current_interval)
        return {
            "$set": {
                "srs_status": "known",
                "srs_interval": next_interval,
                "srs_next_review": now + timedelta(days=next_interval),
            },
            "$inc": {"srs_correct": 1},
        }

    return {
        "$set": {
            "srs_status": "learning",
            "srs_interval": 1,
            "srs_next_review": now + timedelta(days=1),
        },
        "$inc": {"srs_incorrect": 1},
    }


async def get_dashboard_payload(user_id: int) -> dict:
    """Return aggregate flashcard stats for the mini app dashboard."""
    now = datetime.now(timezone.utc)
    collection = mongo_service.db().flashcards

    new_count = await collection.count_documents(
        {
            "user_id": user_id,
            "$or": [
                {"srs_status": {"$exists": False}},
                {"srs_status": "new"},
            ],
        }
    )
    learning_count = await collection.count_documents({"user_id": user_id, "srs_status": "learning"})
    known_count = await collection.count_documents({"user_id": user_id, "srs_status": "known"})
    due_count = await collection.count_documents(
        {
            "user_id": user_id,
            "$or": [
                {"srs_status": {"$exists": False}},
                {"srs_status": "new"},
                {"srs_next_review": {"$exists": False}},
                {"srs_next_review": {"$lte": now}},
            ],
        }
    )

    return {
        "new": new_count,
        "learning": learning_count,
        "known": known_count,
        "due": due_count,
    }


async def get_due_session_cards(user_id: int, limit: int = 50) -> list[dict]:
    """Return due/new cards from all sets for a mini app study session."""
    now = datetime.now(timezone.utc)
    cards = await mongo_service.db().flashcards.find({"user_id": user_id}).to_list(length=5000)
    user_sets = await mongo_service.db().flashcard_sets.find({"user_id": user_id}).to_list(length=500)
    set_names = {str(item["_id"]): item.get("name", "") for item in user_sets}

    due_cards = []
    for card in cards:
        if not is_due_flashcard(card, now):
            continue
        due_cards.append(
            {
                "_id": str(card["_id"]),
                "set_id": card.get("set_id"),
                "set_name": set_names.get(card.get("set_id"), ""),
                "front": card.get("front", ""),
                "back": card.get("back", ""),
                "example": card.get("example", ""),
                "has_image": bool(card.get("image_url")),
                "srs_status": get_srs_status(card),
            }
        )

    random.shuffle(due_cards)
    return due_cards[:limit]


# Routes

async def serve_flashcards_app(request: web.Request) -> web.Response:
    """Serve the flashcards Mini App HTML."""
    html_path = TEMPLATES_DIR / "flashcards.html"
    
    if not html_path.exists():
        raise web.HTTPNotFound(text="App not found")

    return web.FileResponse(
        html_path,
        headers={
            "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


async def get_user_lang(request: web.Request) -> web.Response:
    """Get user's interface language."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        return web.json_response({"lang": "ru"})
    
    try:
        async with async_session_maker() as session:
            user = await UserService.get_or_create_user(session, user_id)
            lang = user.interface_language.value if user else "ru"
            return web.json_response({"lang": lang})
    except Exception as e:
        logger.error(f"Error getting user lang: {e}")
        return web.json_response({"lang": "ru"})


async def get_dashboard(request: web.Request) -> web.Response:
    """Get dashboard stats for the flashcards mini app."""
    user_id = get_user_id_from_request(request)

    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")

    try:
        return web.json_response(await get_dashboard_payload(user_id))
    except Exception as e:
        logger.error(f"Error getting flashcards dashboard: {e}")
        raise web.HTTPInternalServerError(text="Failed to get dashboard")


async def get_global_session(request: web.Request) -> web.Response:
    """Get due cards for the global SRS study session in the mini app."""
    user_id = get_user_id_from_request(request)

    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")

    try:
        cards = await get_due_session_cards(user_id)
        return web.json_response({"cards": cards})
    except Exception as e:
        logger.error(f"Error getting flashcards session cards: {e}")
        raise web.HTTPInternalServerError(text="Failed to get session cards")


async def review_global_session_card(request: web.Request) -> web.Response:
    """Review a card from the global SRS session."""
    user_id = get_user_id_from_request(request)

    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")

    try:
        data = await request.json()
        card_id = (data.get("card_id") or "").strip()
        result = (data.get("result") or "").strip()

        if not card_id or result not in {"know", "dontknow"}:
            raise web.HTTPBadRequest(text="card_id and valid result are required")

        card = await mongo_service.db().flashcards.find_one({
            "_id": ObjectId(card_id),
            "user_id": user_id,
        })

        if not card:
            raise web.HTTPNotFound(text="Card not found")

        update_doc = build_srs_review_update(card, result)
        await mongo_service.db().flashcards.update_one({"_id": ObjectId(card_id)}, update_doc)

        return web.json_response({"success": True})

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing flashcard in session: {e}")
        raise web.HTTPInternalServerError(text="Failed to review card")


async def get_sets(request: web.Request) -> web.Response:
    """Get all flashcard sets for user."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    try:
        # Get user's flashcard sets
        sets = await mongo_service.db().flashcard_sets.find(
            {"user_id": user_id}
        ).sort("created_at", -1).to_list(length=100)
        
        # Add card count to each set
        for s in sets:
            card_count = await mongo_service.db().flashcards.count_documents(
                {"set_id": str(s["_id"])}
            )
            s["card_count"] = card_count
            s["_id"] = str(s["_id"])
            s["created_at"] = s["created_at"].isoformat() if s.get("created_at") else None
            s["updated_at"] = s["updated_at"].isoformat() if s.get("updated_at") else None
        
        return web.json_response({"sets": sets})
        
    except Exception as e:
        logger.error(f"Error getting sets: {e}")
        raise web.HTTPInternalServerError(text="Failed to get sets")


async def create_set(request: web.Request) -> web.Response:
    """Create a new flashcard set."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        
        if not name:
            raise web.HTTPBadRequest(text="Name is required")
        
        if len(name) > 50:
            name = name[:50]
        
        # Create the set
        set_doc = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = await mongo_service.db().flashcard_sets.insert_one(set_doc)
        
        return web.json_response({
            "success": True,
            "set_id": str(result.inserted_id)
        })
        
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating set: {e}")
        raise web.HTTPInternalServerError(text="Failed to create set")


async def delete_set(request: web.Request) -> web.Response:
    """Delete a flashcard set and all its cards."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    set_id = request.match_info.get('set_id')
    
    if not set_id:
        raise web.HTTPBadRequest(text="Set ID is required")
    
    try:
        # Verify ownership
        flashcard_set = await mongo_service.db().flashcard_sets.find_one({
            "_id": ObjectId(set_id),
            "user_id": user_id
        })
        
        if not flashcard_set:
            raise web.HTTPNotFound(text="Set not found")
        
        # Delete all cards in the set
        await mongo_service.db().flashcards.delete_many({"set_id": set_id})
        
        # Delete the set
        await mongo_service.db().flashcard_sets.delete_one({
            "_id": ObjectId(set_id),
            "user_id": user_id
        })
        
        return web.json_response({"success": True})
        
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting set: {e}")
        raise web.HTTPInternalServerError(text="Failed to delete set")


async def update_set(request: web.Request) -> web.Response:
    """Update flashcard set name."""
    user_id = get_user_id_from_request(request)

    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")

    set_id = request.match_info.get('set_id')

    if not set_id:
        raise web.HTTPBadRequest(text="Set ID is required")

    try:
        flashcard_set = await mongo_service.db().flashcard_sets.find_one({
            "_id": ObjectId(set_id),
            "user_id": user_id
        })

        if not flashcard_set:
            raise web.HTTPNotFound(text="Set not found")

        data = await request.json()
        name = data.get("name", "").strip()

        if not name:
            raise web.HTTPBadRequest(text="Name is required")

        if len(name) > 50:
            name = name[:50]

        await mongo_service.db().flashcard_sets.update_one(
            {"_id": ObjectId(set_id), "user_id": user_id},
            {"$set": {"name": name, "updated_at": datetime.now(timezone.utc)}}
        )

        return web.json_response({"success": True})

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating set: {e}")
        raise web.HTTPInternalServerError(text="Failed to update set")


async def get_cards(request: web.Request) -> web.Response:
    """Get all cards in a flashcard set."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    set_id = request.match_info.get('set_id')
    
    if not set_id:
        raise web.HTTPBadRequest(text="Set ID is required")
    
    try:
        # Verify ownership of the set
        flashcard_set = await mongo_service.db().flashcard_sets.find_one({
            "_id": ObjectId(set_id),
            "user_id": user_id
        })
        
        if not flashcard_set:
            raise web.HTTPNotFound(text="Set not found")
        
        # Get cards
        cards = await mongo_service.db().flashcards.find(
            {"set_id": set_id}
        ).sort("created_at", 1).to_list(length=1000)
        
        # Convert ObjectId to string
        for card in cards:
            card["_id"] = str(card["_id"])
            card["created_at"] = card["created_at"].isoformat() if card.get("created_at") else None
            card["example"] = card.get("example", "")
            card["has_image"] = bool(card.get("image_url"))
        
        return web.json_response({"cards": cards})
        
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cards: {e}")
        raise web.HTTPInternalServerError(text="Failed to get cards")


async def add_card(request: web.Request) -> web.Response:
    """Add a card to a flashcard set."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    set_id = request.match_info.get('set_id')
    
    if not set_id:
        raise web.HTTPBadRequest(text="Set ID is required")
    
    try:
        # Verify ownership of the set
        flashcard_set = await mongo_service.db().flashcard_sets.find_one({
            "_id": ObjectId(set_id),
            "user_id": user_id
        })
        
        if not flashcard_set:
            raise web.HTTPNotFound(text="Set not found")
        
        data = await request.json()
        front = data.get("front", "").strip()
        back = data.get("back", "").strip()
        example = data.get("example", "").strip()
        
        if not front or not back:
            raise web.HTTPBadRequest(text="Front and back are required")
        
        if len(front) > 200:
            front = front[:200]
        if len(back) > 200:
            back = back[:200]
        
        # Create the card
        card_doc = {
            "user_id": user_id,
            "set_id": set_id,
            "front": front,
            "back": back,
            "example": example,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = await mongo_service.db().flashcards.insert_one(card_doc)
        
        # Update set's updated_at
        await mongo_service.db().flashcard_sets.update_one(
            {"_id": ObjectId(set_id)},
            {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )
        
        return web.json_response({
            "success": True,
            "card_id": str(result.inserted_id)
        })
        
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding card: {e}")
        raise web.HTTPInternalServerError(text="Failed to add card")


async def delete_card(request: web.Request) -> web.Response:
    """Delete a card from a flashcard set."""
    user_id = get_user_id_from_request(request)
    
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")
    
    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")
    
    set_id = request.match_info.get('set_id')
    card_id = request.match_info.get('card_id')
    
    if not set_id or not card_id:
        raise web.HTTPBadRequest(text="Set ID and Card ID are required")
    
    try:
        # Verify ownership
        card = await mongo_service.db().flashcards.find_one({
            "_id": ObjectId(card_id),
            "set_id": set_id,
            "user_id": user_id
        })
        
        if not card:
            raise web.HTTPNotFound(text="Card not found")
        
        # Delete the card
        await mongo_service.db().flashcards.delete_one({
            "_id": ObjectId(card_id),
            "user_id": user_id
        })
        
        return web.json_response({"success": True})
        
    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting card: {e}")
        raise web.HTTPInternalServerError(text="Failed to delete card")


async def update_card(request: web.Request) -> web.Response:
    """Update an existing flashcard."""
    user_id = get_user_id_from_request(request)

    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    if not mongo_service.is_ready():
        raise web.HTTPServiceUnavailable(text="Database unavailable")

    set_id = request.match_info.get('set_id')
    card_id = request.match_info.get('card_id')

    if not set_id or not card_id:
        raise web.HTTPBadRequest(text="Set ID and Card ID are required")

    try:
        # Verify ownership
        card = await mongo_service.db().flashcards.find_one({
            "_id": ObjectId(card_id),
            "set_id": set_id,
            "user_id": user_id
        })

        if not card:
            raise web.HTTPNotFound(text="Card not found")

        data = await request.json()
        front = data.get("front", "").strip()
        back = data.get("back", "").strip()
        example = data.get("example", "").strip()

        if not front or not back:
            raise web.HTTPBadRequest(text="Front and back are required")

        if len(front) > 200:
            front = front[:200]
        if len(back) > 200:
            back = back[:200]
        if len(example) > 300:
            example = example[:300]

        await mongo_service.db().flashcards.update_one(
            {"_id": ObjectId(card_id)},
            {
                "$set": {
                    "front": front,
                    "back": back,
                    "example": example
                }
            }
        )

        await mongo_service.db().flashcard_sets.update_one(
            {"_id": ObjectId(set_id)},
            {"$set": {"updated_at": datetime.now(timezone.utc)}}
        )

        return web.json_response({"success": True})

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating card: {e}")
        raise web.HTTPInternalServerError(text="Failed to update card")


# ---- Card Image endpoints ----

MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 MB after base64


async def upload_card_image(request: web.Request) -> web.Response:
    """Upload an image for a flashcard to Cloudinary."""
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    set_id = request.match_info.get('set_id')
    card_id = request.match_info.get('card_id')
    if not set_id or not card_id:
        raise web.HTTPBadRequest(text="Set ID and Card ID are required")

    try:
        # Verify card exists and belongs to user
        if mongo_service.is_ready():
            card = await mongo_service.db().flashcards.find_one({
                "_id": ObjectId(card_id),
                "set_id": set_id,
                "user_id": user_id
            })
            if not card:
                raise web.HTTPNotFound(text="Card not found")

        # Read multipart or JSON body
        content_type = request.content_type

        if 'multipart' in content_type:
            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != 'image':
                raise web.HTTPBadRequest(text="Image field is required")
            raw = await field.read(decode=False)
            mime = field.headers.get('Content-Type', 'image/jpeg')
        else:
            # JSON with base64
            data = await request.json()
            b64 = data.get('image_data', '')
            mime = data.get('mime', 'image/jpeg')
            if not b64:
                raise web.HTTPBadRequest(text="image_data is required")
            raw = base64.b64decode(b64)

        if len(raw) > MAX_IMAGE_SIZE:
            raise web.HTTPRequestEntityTooLarge(text="Image too large (max 2MB)")

        # Upload to Cloudinary with unique public_id
        public_id = f"user_{user_id}_card_{card_id}"
        result = await cloudinary_service.upload_image(
            image_data=raw,
            public_id=public_id,
            format=mime.split('/')[-1] if '/' in mime else 'jpg'
        )

        if not result:
            raise web.HTTPInternalServerError(text="Failed to upload image")

        # Store Cloudinary URL in MongoDB (if available)
        if mongo_service.is_ready():
            await mongo_service.db().flashcards.update_one(
                {"_id": ObjectId(card_id)},
                {"$set": {
                    "image_url": result.get('secure_url'),
                    "cloudinary_public_id": result.get('public_id')
                }}
            )

        return web.json_response({
            "success": True,
            "url": result.get('secure_url')
        })

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading card image: {e}")
        raise web.HTTPInternalServerError(text="Failed to upload image")


async def get_card_image(request: web.Request) -> web.Response:
    """Get card's image URL from Cloudinary."""
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    set_id = request.match_info.get('set_id')
    card_id = request.match_info.get('card_id')

    try:
        # Try to get URL from MongoDB first
        image_url = None
        if mongo_service.is_ready():
            card = await mongo_service.db().flashcards.find_one(
                {"_id": ObjectId(card_id), "set_id": set_id, "user_id": user_id},
                {"image_url": 1}
            )
            if card:
                image_url = card.get("image_url")
        
        # If not in DB, generate URL from Cloudinary
        if not image_url:
            public_id = f"user_{user_id}_card_{card_id}"
            image_url = await cloudinary_service.get_image_url(public_id)
        
        if not image_url:
            raise web.HTTPNotFound(text="Image not found")

        # Return JSON with URL (client will load it)
        return web.json_response({
            "url": image_url
        })

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting card image: {e}")
        raise web.HTTPInternalServerError(text="Failed to get image")


async def delete_card_image(request: web.Request) -> web.Response:
    """Delete a card's image from Cloudinary."""
    user_id = get_user_id_from_request(request)
    if not user_id:
        raise web.HTTPUnauthorized(text="Invalid authentication")

    set_id = request.match_info.get('set_id')
    card_id = request.match_info.get('card_id')

    try:
        # Verify ownership
        if mongo_service.is_ready():
            card = await mongo_service.db().flashcards.find_one({
                "_id": ObjectId(card_id), "set_id": set_id, "user_id": user_id
            })
            if not card:
                raise web.HTTPNotFound(text="Card not found")

        # Delete from Cloudinary
        public_id = f"user_{user_id}_card_{card_id}"
        deleted = await cloudinary_service.delete_image(public_id)

        # Remove URL from MongoDB
        if mongo_service.is_ready():
            await mongo_service.db().flashcards.update_one(
                {"_id": ObjectId(card_id)},
                {"$unset": {"image_url": "", "cloudinary_public_id": ""}}
            )

        return web.json_response({"success": deleted})

    except web.HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting card image: {e}")
        raise web.HTTPInternalServerError(text="Failed to delete image")


def create_webapp_routes() -> web.Application:
    """Create and return the web application with all routes."""
    app = web.Application(client_max_size=4 * 1024 * 1024)  # 4MB max body
    
    # Static files
    app.router.add_static('/static', STATIC_DIR, name='static')
    
    # Main app page
    app.router.add_get('/flashcards', serve_flashcards_app)
    
    # API routes
    app.router.add_get('/api/flashcards/user/lang', get_user_lang)
    app.router.add_get('/api/flashcards/dashboard', get_dashboard)
    app.router.add_get('/api/flashcards/session', get_global_session)
    app.router.add_post('/api/flashcards/session/review', review_global_session_card)
    app.router.add_get('/api/flashcards/sets', get_sets)
    app.router.add_post('/api/flashcards/sets', create_set)
    app.router.add_put('/api/flashcards/sets/{set_id}', update_set)
    app.router.add_delete('/api/flashcards/sets/{set_id}', delete_set)
    app.router.add_get('/api/flashcards/sets/{set_id}/cards', get_cards)
    app.router.add_post('/api/flashcards/sets/{set_id}/cards', add_card)
    app.router.add_put('/api/flashcards/sets/{set_id}/cards/{card_id}', update_card)
    app.router.add_delete('/api/flashcards/sets/{set_id}/cards/{card_id}', delete_card)
    # Card image routes
    app.router.add_post('/api/flashcards/sets/{set_id}/cards/{card_id}/image', upload_card_image)
    app.router.add_get('/api/flashcards/sets/{set_id}/cards/{card_id}/image', get_card_image)
    app.router.add_delete('/api/flashcards/sets/{set_id}/cards/{card_id}/image', delete_card_image)
    
    return app


async def start_webapp_server(host: str = "0.0.0.0", port: int = 8080):
    """Start the web server."""
    app = create_webapp_routes()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Web app server started at http://{host}:{port}")
    return runner
