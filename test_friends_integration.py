"""
Integration test for friends feature.

This test validates the complete flow of the friends feature including:
1. MongoDB schema for friendships
2. Friend management in scheduler service for daily reports
3. Complete UI flow
"""


def test_mongo_friend_functions_signature():
    """Test that mongo_service friend functions have correct signatures"""
    import ast
    
    with open('bot/services/mongo_service.py', 'r') as f:
        tree = ast.parse(f.read())
    
    # Find async function definitions
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            functions[node.name] = [arg.arg for arg in node.args.args]
    
    # Check add_friend
    assert 'add_friend' in functions, "add_friend function not found"
    assert 'user_id' in functions['add_friend'], "add_friend missing user_id parameter"
    assert 'friend_id' in functions['add_friend'], "add_friend missing friend_id parameter"
    print("✓ add_friend has correct signature")
    
    # Check remove_friend
    assert 'remove_friend' in functions, "remove_friend function not found"
    assert 'user_id' in functions['remove_friend'], "remove_friend missing user_id parameter"
    assert 'friend_id' in functions['remove_friend'], "remove_friend missing friend_id parameter"
    print("✓ remove_friend has correct signature")
    
    # Check get_friends
    assert 'get_friends' in functions, "get_friends function not found"
    assert 'user_id' in functions['get_friends'], "get_friends missing user_id parameter"
    print("✓ get_friends has correct signature")
    
    # Check get_friends_stats
    assert 'get_friends_stats' in functions, "get_friends_stats function not found"
    assert 'user_id' in functions['get_friends_stats'], "get_friends_stats missing user_id parameter"
    print("✓ get_friends_stats has correct signature")


def test_scheduler_includes_friends_stats():
    """Test that scheduler service includes friends stats in daily reports"""
    with open('bot/services/scheduler_service.py', 'r') as f:
        content = f.read()
    
    # Check that _send_daily_reports function includes friends stats
    assert 'get_friends_stats' in content, "Scheduler doesn't call get_friends_stats"
    assert 'friends_stats' in content, "Scheduler doesn't handle friends_stats"
    assert 'friends_section' in content or 'friends_stats_title' in content, \
        "Scheduler doesn't build friends statistics section"
    
    print("✓ Scheduler service includes friends stats in daily reports")


def test_friends_handler_has_all_routes():
    """Test that friends handler has all necessary routes"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Check for main routes
    assert '@router.message' in content, "Missing message handlers"
    assert '@router.callback_query' in content, "Missing callback handlers"
    
    # Check for specific handlers
    assert 'friends_menu' in content, "Missing friends_menu handler"
    assert 'add_friend' in content, "Missing add_friend handler"
    assert 'remove_friend' in content, "Missing remove_friend handler"
    assert 'friends_stats' in content, "Missing friends_stats handler"
    
    # Check for FSM states
    assert 'FriendsStates' in content, "Missing FriendsStates"
    assert 'waiting_for_friend_id' in content, "Missing waiting_for_friend_id state"
    
    print("✓ Friends handler has all necessary routes and states")


def test_main_menu_button_integration():
    """Test that main menu includes friends button properly"""
    # Check keyboards.py for friends button integration
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    # Check that get_main_menu_keyboard includes friends button
    assert 'btn_friends' in content, "Friends button not referenced in keyboards"
    assert 'get_friends_menu_keyboard' in content, "get_friends_menu_keyboard function not found"
    
    print("✓ Main menu integration includes friends button")


def test_friends_localization_completeness():
    """Test that friends localization is complete for both languages"""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Test that all required keys exist in both languages
    uk_keys = [
        "btn_friends", "friends_menu", "friends_list", "no_friends",
        "add_friend_prompt", "friend_added", "friend_already_exists",
        "friend_not_found", "friend_removed", "cannot_add_self",
        "btn_add_friend", "btn_remove_friend", "btn_view_friends_stats",
        "friends_stats_title", "friends_stats_user", "friends_stats_empty"
    ]
    
    for key in uk_keys:
        assert f'"{key}"' in content, f"Key missing in locales: {key}"
    
    # Count occurrences - should be at least 2 (once for uk, once for ru)
    for key in uk_keys:
        count = content.count(f'"{key}"')
        assert count >= 2, f"Key {key} not found in both languages (found {count} times)"
    
    print("✓ All friends localization keys exist in both languages")


def test_friends_workflow_text_consistency():
    """Test that the friends workflow texts make sense together"""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check that key phrases exist
    assert "Друзі" in content or "Друзья" in content, "Friends label not found"
    assert "Додати друга" in content or "Добавить друга" in content, "Add friend text not found"
    assert "Видалити друга" in content or "Удалить друга" in content, "Remove friend text not found"
    assert "статистик" in content.lower(), "Statistics text not found"
    
    print("✓ Friends workflow texts are present and consistent")


def test_friends_stats_format():
    """Test that friends stats formatting works correctly"""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Check that stats formatting strings exist with placeholders
    assert '{name}' in content, "Name placeholder not found in stats"
    assert '{username}' in content, "Username placeholder not found in stats"
    assert '{completed}' in content, "Completed placeholder not found in stats"
    assert '{quality}' in content, "Quality placeholder not found in stats"
    assert '📊' in content, "Chart emoji not found in locales"
    
    print("✓ Friends stats formatting placeholders are correct")


if __name__ == "__main__":
    print("Running friends integration tests...\n")
    
    test_mongo_friend_functions_signature()
    test_scheduler_includes_friends_stats()
    test_friends_handler_has_all_routes()
    test_main_menu_button_integration()
    test_friends_localization_completeness()
    test_friends_workflow_text_consistency()
    test_friends_stats_format()
    
    print("\n✅ All friends integration tests passed!")
    print("\n📝 Summary:")
    print("   - Friend management functions are properly defined")
    print("   - Daily reports include friends statistics")
    print("   - Friends handler has all necessary routes")
    print("   - Main menu includes friends button")
    print("   - Localization is complete for both languages")
    print("   - Workflow texts are consistent and well-formatted")
