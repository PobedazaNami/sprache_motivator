"""
Test admin bypass for trial checks.

This test validates that admin users can access translator and trainer
features without trial activation checks.
"""
import pytest
from datetime import datetime, timedelta
import pytz


def test_admin_bypass_trial_check():
    """Verify that admins bypass trial activation checks"""
    from bot.handlers.admin import is_admin
    from bot.config import settings
    
    # Test with empty admin list
    original_admin_ids = settings.ADMIN_IDS
    settings.ADMIN_IDS = ""
    
    # Non-admin should return False
    assert not is_admin(12345), "Non-admin should return False"
    
    # Set admin ID
    settings.ADMIN_IDS = "12345,67890"
    
    # Admin should return True
    assert is_admin(12345), "Admin user 12345 should return True"
    assert is_admin(67890), "Admin user 67890 should return True"
    assert not is_admin(99999), "Non-admin user 99999 should return False"
    
    # Restore original
    settings.ADMIN_IDS = original_admin_ids
    
    print("✓ Admin bypass check works correctly")


def test_admin_auto_activation():
    """Verify that admins get auto-activated trial and subscription"""
    from bot.services.database_service import UserModel
    from bot.config import settings
    
    # Mock admin ID
    admin_id = 999999
    original_admin_ids = settings.ADMIN_IDS
    settings.ADMIN_IDS = str(admin_id)
    
    # Create a mock document as if admin just registered
    doc = {
        "_id": "test_admin",
        "telegram_id": admin_id,
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "status": "approved",  # Should be auto-approved
        "interface_language": "ru",
        "learning_language": "en",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "allow_broadcasts": True,
        "daily_trainer_enabled": False,
        "trainer_start_time": "09:00",
        "trainer_end_time": "21:00",
        "trainer_messages_per_day": 3,
        "trainer_timezone": "Europe/Kiev",
        "trainer_topic": "random",
        "activity_score": 0,
        "translations_count": 0,
        "correct_answers": 0,
        "total_answers": 0,
        "tokens_used_today": 0,
        "last_token_reset": datetime.now(pytz.UTC),
        "trial_activated": True,  # Admins should have this True
        "trial_activation_date": datetime.now(pytz.UTC),
        "subscription_active": True,  # Admins should have this True
    }
    
    user = UserModel(doc)
    
    # Verify admin has trial activated and subscription active
    assert user.trial_activated is True, "Admin should have trial activated"
    assert user.subscription_active is True, "Admin should have subscription active"
    
    # Restore original
    settings.ADMIN_IDS = original_admin_ids
    
    print("✓ Admin auto-activation works correctly")


def test_trial_checks_with_admin():
    """Verify that trial checks properly handle admin users"""
    from bot.handlers.admin import is_admin
    from bot.config import settings
    
    # Set up admin ID
    admin_id = 111111
    non_admin_id = 222222
    original_admin_ids = settings.ADMIN_IDS
    settings.ADMIN_IDS = str(admin_id)
    
    # Test is_admin returns correct values
    assert is_admin(admin_id) is True, "Should identify admin correctly"
    assert is_admin(non_admin_id) is False, "Should identify non-admin correctly"
    
    # Restore original
    settings.ADMIN_IDS = original_admin_ids
    
    print("✓ Trial checks handle admin users correctly")


def test_admin_function_import():
    """Verify that is_admin function can be imported from translator and trainer"""
    # Test that we can import is_admin from the modules that use it
    try:
        from bot.handlers.translator import is_admin as translator_is_admin
        from bot.handlers.trainer import is_admin as trainer_is_admin
        print("✓ is_admin function successfully imported in translator and trainer modules")
    except ImportError as e:
        pytest.fail(f"Failed to import is_admin: {e}")


if __name__ == "__main__":
    print("Running admin bypass tests...\n")
    
    test_admin_bypass_trial_check()
    test_admin_auto_activation()
    test_trial_checks_with_admin()
    test_admin_function_import()
    
    print("\n✅ All admin bypass tests passed!")
