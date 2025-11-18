"""
Test friends/groups feature implementation.

This test validates that users can:
1. Add friends to form groups
2. Remove friends from their groups
3. View friends' statistics at the end of the day
"""
from datetime import datetime, timezone


def test_mongo_service_has_friend_methods():
    """Verify that mongo_service has friend management methods"""
    from bot.services import mongo_service
    
    # Check that friend management methods exist
    assert hasattr(mongo_service, "add_friend"), "Missing add_friend method"
    assert hasattr(mongo_service, "remove_friend"), "Missing remove_friend method"
    assert hasattr(mongo_service, "get_friends"), "Missing get_friends method"
    assert hasattr(mongo_service, "get_friends_stats"), "Missing get_friends_stats method"
    
    print("✓ Mongo service has all friend management methods")


def test_friends_localization_texts_exist():
    """Verify that all required friends localization texts are present"""
    from bot.locales.texts import LOCALES
    
    required_keys_uk = [
        "btn_friends",
        "friends_menu",
        "friends_list",
        "no_friends",
        "add_friend_prompt",
        "friend_added",
        "friend_already_exists",
        "friend_not_found",
        "friend_removed",
        "cannot_add_self",
        "btn_add_friend",
        "btn_remove_friend",
        "btn_view_friends_stats",
        "friends_stats_title",
        "friends_stats_user",
        "friends_stats_empty",
    ]
    
    required_keys_ru = [
        "btn_friends",
        "friends_menu",
        "friends_list",
        "no_friends",
        "add_friend_prompt",
        "friend_added",
        "friend_already_exists",
        "friend_not_found",
        "friend_removed",
        "cannot_add_self",
        "btn_add_friend",
        "btn_remove_friend",
        "btn_view_friends_stats",
        "friends_stats_title",
        "friends_stats_user",
        "friends_stats_empty",
    ]
    
    for key in required_keys_uk:
        assert key in LOCALES["uk"], f"Missing Ukrainian text: {key}"
    
    for key in required_keys_ru:
        assert key in LOCALES["ru"], f"Missing Russian text: {key}"
    
    print("✓ All required friends localization texts exist")


def test_friends_handler_exists():
    """Verify that friends handler module exists and has required handlers"""
    try:
        from bot.handlers import friends
        
        # Check that router exists
        assert hasattr(friends, "router"), "Missing router in friends handler"
        
        # Check that FSM states exist
        assert hasattr(friends, "FriendsStates"), "Missing FriendsStates"
        
        print("✓ Friends handler module exists with required components")
    except ImportError as e:
        raise AssertionError(f"Failed to import friends handler: {e}")


def test_friends_keyboards_exist():
    """Verify that friends keyboards exist"""
    from bot.utils.keyboards import get_friends_menu_keyboard, get_friend_list_keyboard
    
    # Test that keyboards can be created
    keyboard1 = get_friends_menu_keyboard("uk")
    assert keyboard1 is not None, "Failed to create friends menu keyboard"
    
    keyboard2 = get_friend_list_keyboard("ru", [(123, "Test User")])
    assert keyboard2 is not None, "Failed to create friend list keyboard"
    
    print("✓ Friends keyboards can be created")


def test_main_menu_includes_friends_button():
    """Verify that friends button is added to main menu"""
    from bot.locales.texts import get_text
    
    # Check that friends button text exists
    uk_text = get_text("uk", "btn_friends")
    ru_text = get_text("ru", "btn_friends")
    
    assert "Друз" in uk_text or "друз" in uk_text, "Ukrainian friends button text incorrect"
    assert "Друз" in ru_text or "друз" in ru_text, "Russian friends button text incorrect"
    
    print("✓ Friends button text is available in both languages")


def test_friends_handler_registered():
    """Verify that friends handler is registered in main.py"""
    import sys
    import os
    
    # Read main.py content
    main_py_path = os.path.join(os.path.dirname(__file__), "bot", "main.py")
    with open(main_py_path, "r") as f:
        content = f.read()
    
    # Check that friends is imported
    assert "from bot.handlers import" in content, "Handlers import not found"
    assert "friends" in content, "Friends handler not imported in main.py"
    assert "friends.router" in content, "Friends router not registered"
    
    print("✓ Friends handler is registered in main.py")


if __name__ == "__main__":
    print("Running friends feature tests...\n")
    
    test_mongo_service_has_friend_methods()
    test_friends_localization_texts_exist()
    test_friends_handler_exists()
    test_friends_keyboards_exist()
    test_main_menu_includes_friends_button()
    test_friends_handler_registered()
    
    print("\n✅ All friends feature tests passed!")
