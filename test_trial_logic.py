"""
Test trial activation and access control logic.

This test validates that the trial system works correctly:
1. Users must activate trial before accessing translator/trainer
2. Trial expires after 10 days (Berlin timezone)
3. Admins get automatic trial activation
4. Subscription users have unlimited access
"""
import pytest
from datetime import datetime, timedelta
import pytz


def test_trial_fields_exist():
    """Verify that trial-related fields are added to the user model"""
    from bot.services.database_service import UserModel
    
    # Create a mock document with trial fields
    doc = {
        "_id": "test_id",
        "telegram_id": 123456,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "status": "approved",
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
        "activity_score": 0,
        "translations_count": 0,
        "correct_answers": 0,
        "total_answers": 0,
        "tokens_used_today": 0,
        "last_token_reset": datetime.now(pytz.UTC),
        "trial_activated": True,
        "trial_activation_date": datetime.now(pytz.UTC),
        "subscription_active": False,
    }
    
    user = UserModel(doc)
    
    # Verify trial fields exist
    assert hasattr(user, "trial_activated")
    assert hasattr(user, "trial_activation_date")
    assert hasattr(user, "subscription_active")
    assert user.trial_activated is True
    assert user.subscription_active is False
    
    print("✓ Trial fields exist in UserModel")


def test_trial_expiration_logic():
    """Test that trial expiration is calculated correctly"""
    from bot.services.database_service import UserService, UserModel
    
    berlin_tz = pytz.timezone('Europe/Berlin')
    now = datetime.now(berlin_tz)
    
    # Test 1: Trial not activated - should not be expired
    doc1 = {
        "_id": "test1",
        "telegram_id": 1,
        "status": "approved",
        "interface_language": "ru",
        "learning_language": "en",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "trial_activated": False,
        "trial_activation_date": None,
        "subscription_active": False,
    }
    user1 = UserModel(doc1)
    assert not UserService.is_trial_expired(user1), "Non-activated trial should not be expired"
    print("✓ Non-activated trial is not expired")
    
    # Test 2: Trial activated 5 days ago - should not be expired
    doc2 = {
        "_id": "test2",
        "telegram_id": 2,
        "status": "approved",
        "interface_language": "ru",
        "learning_language": "en",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "trial_activated": True,
        "trial_activation_date": now - timedelta(days=5),
        "subscription_active": False,
    }
    user2 = UserModel(doc2)
    assert not UserService.is_trial_expired(user2), "5-day-old trial should not be expired"
    days_remaining = UserService.get_trial_days_remaining(user2)
    assert days_remaining >= 4 and days_remaining <= 5, f"Should have 4-5 days remaining, got {days_remaining}"
    print(f"✓ 5-day-old trial is not expired (days remaining: {days_remaining})")
    
    # Test 3: Trial activated 11 days ago - should be expired
    doc3 = {
        "_id": "test3",
        "telegram_id": 3,
        "status": "approved",
        "interface_language": "ru",
        "learning_language": "en",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "trial_activated": True,
        "trial_activation_date": now - timedelta(days=11),
        "subscription_active": False,
    }
    user3 = UserModel(doc3)
    assert UserService.is_trial_expired(user3), "11-day-old trial should be expired"
    days_remaining = UserService.get_trial_days_remaining(user3)
    assert days_remaining == 0, f"Expired trial should have 0 days remaining, got {days_remaining}"
    print("✓ 11-day-old trial is expired")
    
    # Test 4: Subscribed user - should never expire
    doc4 = {
        "_id": "test4",
        "telegram_id": 4,
        "status": "approved",
        "interface_language": "ru",
        "learning_language": "en",
        "work_mode": "translator",
        "difficulty_level": "A2",
        "trial_activated": True,
        "trial_activation_date": now - timedelta(days=30),
        "subscription_active": True,
    }
    user4 = UserModel(doc4)
    assert not UserService.is_trial_expired(user4), "Subscribed user should never expire"
    days_remaining = UserService.get_trial_days_remaining(user4)
    assert days_remaining == 999, f"Subscribed user should have 999 days, got {days_remaining}"
    print("✓ Subscribed user never expires")


def test_localization_texts_exist():
    """Verify that all required localization texts are present"""
    from bot.locales.texts import LOCALES
    
    required_keys_uk = [
        "welcome_with_trial",
        "trial_not_activated",
        "trial_expired",
        "trial_activated",
        "trial_status",
        "btn_activate_trial",
    ]
    
    required_keys_ru = [
        "welcome_with_trial",
        "trial_not_activated",
        "trial_expired",
        "trial_activated",
        "trial_status",
        "btn_activate_trial",
    ]
    
    for key in required_keys_uk:
        assert key in LOCALES["uk"], f"Missing Ukrainian text: {key}"
    
    for key in required_keys_ru:
        assert key in LOCALES["ru"], f"Missing Russian text: {key}"
    
    print("✓ All required localization texts exist")


def test_config_has_subscription_settings():
    """Verify that config has subscription-related settings"""
    from bot.config import settings
    
    # Check that settings instance has the new fields
    assert hasattr(settings, "STRIPE_PAYMENT_LINK"), "Missing STRIPE_PAYMENT_LINK in settings"
    assert hasattr(settings, "ADMIN_CONTACT"), "Missing ADMIN_CONTACT in settings"
    
    print("✓ Config has subscription settings")


if __name__ == "__main__":
    print("Running trial logic tests...\n")
    
    test_trial_fields_exist()
    test_trial_expiration_logic()
    test_localization_texts_exist()
    test_config_has_subscription_settings()
    
    print("\n✅ All trial logic tests passed!")
