"""
Cloudinary service for image storage.
Handles upload, retrieval, and deletion of flashcard images.
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Optional, Dict
import logging

from bot.config import settings

logger = logging.getLogger(__name__)

_initialized = False


def init() -> bool:
    """Initialize Cloudinary with URL from settings."""
    global _initialized
    
    if not settings.CLOUDINARY_URL:
        logger.warning("CLOUDINARY_URL not configured - image upload will be disabled")
        return False
    
    try:
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
        _initialized = True
        logger.info("Cloudinary initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Cloudinary: {e}")
        return False


def is_ready() -> bool:
    """Check if Cloudinary is initialized and ready."""
    return _initialized


async def upload_image(
    image_data: bytes,
    public_id: str,
    folder: Optional[str] = None,
    **options
) -> Optional[Dict]:
    """
    Upload image to Cloudinary.
    
    Args:
        image_data: Binary image data
        public_id: Unique identifier for the image (e.g., "user_123_card_456")
        folder: Folder path in Cloudinary (defaults to CLOUDINARY_FOLDER from settings)
        **options: Additional Cloudinary upload options
    
    Returns:
        Upload result dict with url, secure_url, public_id, etc. or None on error
    """
    if not is_ready():
        logger.error("Cloudinary not initialized")
        return None
    
    if folder is None:
        folder = settings.CLOUDINARY_FOLDER
    
    try:
        result = cloudinary.uploader.upload(
            image_data,
            public_id=public_id,
            folder=folder,
            resource_type="image",
            **options
        )
        logger.info(f"Image uploaded: {result.get('public_id')}")
        return result
    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        return None


async def get_image_url(public_id: str, folder: Optional[str] = None) -> Optional[str]:
    """
    Get secure URL for an image.
    
    Args:
        public_id: Image identifier
        folder: Folder path (defaults to CLOUDINARY_FOLDER)
    
    Returns:
        Secure HTTPS URL or None if not found
    """
    if not is_ready():
        return None
    
    if folder is None:
        folder = settings.CLOUDINARY_FOLDER
    
    try:
        # Build full public_id with folder
        full_public_id = f"{folder}/{public_id}"
        
        # Generate URL (Cloudinary SDK handles this locally, no API call needed)
        url = cloudinary.CloudinaryImage(full_public_id).build_url(secure=True)
        return url
    except Exception as e:
        logger.error(f"Failed to get image URL: {e}")
        return None


async def delete_image(public_id: str, folder: Optional[str] = None) -> bool:
    """
    Delete image from Cloudinary.
    
    Args:
        public_id: Image identifier
        folder: Folder path (defaults to CLOUDINARY_FOLDER)
    
    Returns:
        True if deleted successfully, False otherwise
    """
    if not is_ready():
        logger.error("Cloudinary not initialized")
        return False
    
    if folder is None:
        folder = settings.CLOUDINARY_FOLDER
    
    try:
        # Build full public_id with folder
        full_public_id = f"{folder}/{public_id}"
        
        result = cloudinary.uploader.destroy(full_public_id, resource_type="image")
        
        if result.get("result") == "ok":
            logger.info(f"Image deleted: {full_public_id}")
            return True
        else:
            logger.warning(f"Image deletion returned: {result}")
            return False
    except Exception as e:
        logger.error(f"Failed to delete image: {e}")
        return False
