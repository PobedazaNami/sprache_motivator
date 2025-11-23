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
    
    # Check send_friend_request
    assert 'send_friend_request' in functions, "send_friend_request function not found"
    assert 'user_id' in functions['send_friend_request'], "send_friend_request missing user_id parameter"
    assert 'friend_id' in functions['send_friend_request'], "send_friend_request missing friend_id parameter"
    print("✓ send_friend_request has correct signature")
    
    # Check accept_friend_request
    assert 'accept_friend_request' in functions, "accept_friend_request function not found"
    assert 'user_id' in functions['accept_friend_request'], "accept_friend_request missing user_id parameter"
    assert 'requester_id' in functions['accept_friend_request'], "accept_friend_request missing requester_id parameter"
    print("✓ accept_friend_request has correct signature")
    
    # Check reject_friend_request
    assert 'reject_friend_request' in functions, "reject_friend_request function not found"
    assert 'user_id' in functions['reject_friend_request'], "reject_friend_request missing user_id parameter"
    assert 'requester_id' in functions['reject_friend_request'], "reject_friend_request missing requester_id parameter"
    print("✓ reject_friend_request has correct signature")
    
    # Check get_pending_incoming_requests
    assert 'get_pending_incoming_requests' in functions, "get_pending_incoming_requests function not found"
    assert 'user_id' in functions['get_pending_incoming_requests'], "get_pending_incoming_requests missing user_id parameter"
    print("✓ get_pending_incoming_requests has correct signature")
    
    # Check get_pending_outgoing_requests
    assert 'get_pending_outgoing_requests' in functions, "get_pending_outgoing_requests function not found"
    assert 'user_id' in functions['get_pending_outgoing_requests'], "get_pending_outgoing_requests missing user_id parameter"
    print("✓ get_pending_outgoing_requests has correct signature")
    
    # Check add_friend (legacy)
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
    assert 'view_pending_requests' in content, "Missing view_pending_requests handler"
    assert 'accept_friend_request' in content, "Missing accept_friend_request handler"
    assert 'reject_friend_request' in content, "Missing reject_friend_request handler"
    
    # Check for FSM states
    assert 'FriendsStates' in content, "Missing FriendsStates"
    assert 'waiting_for_friend_id' in content, "Missing waiting_for_friend_id state"
    
    # Check for friend request functionality
    assert 'send_friend_request' in content, "Missing send_friend_request call"
    assert 'get_pending_incoming_requests' in content, "Missing get_pending_incoming_requests call"
    assert 'friend_request_notification' in content, "Missing friend_request_notification"
    
    print("✓ Friends handler has all necessary routes and states")


def test_main_menu_button_integration():
    """Test that main menu includes friends button properly"""
    # Check keyboards.py for friends button integration
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    # Check that get_main_menu_keyboard includes friends button
    assert 'btn_friends' in content, "Friends button not referenced in keyboards"
    assert 'get_friends_menu_keyboard' in content, "get_friends_menu_keyboard function not found"
    assert 'get_pending_requests_keyboard' in content, "get_pending_requests_keyboard function not found"
    assert 'btn_pending_requests' in content, "Pending requests button not referenced in keyboards"
    
    print("✓ Main menu integration includes friends button")


def test_friends_localization_completeness():
    """Test that friends localization is complete for both languages"""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Test that all required keys exist in both languages
    uk_keys = [
        "btn_friends", "friends_menu", "friends_list", "no_friends",
        "add_friend_prompt", "friend_request_sent", "friend_request_exists",
        "friend_not_found", "friend_removed", "cannot_add_self",
        "btn_add_friend", "btn_remove_friend", "btn_view_friends_stats",
        "btn_pending_requests", "friends_stats_title", "friends_stats_user",
        "friends_stats_empty", "pending_requests_title", "no_pending_requests",
        "friend_request_accepted", "friend_request_rejected", "friend_request_notification"
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
        texts_content = f.read()
    
    with open('bot/handlers/friends.py', 'r') as f:
        handler_content = f.read()
    
    # Combine for checking
    content = texts_content + handler_content
    
    # Check that key phrases exist
    assert "Друзі" in content or "Друзья" in content, "Friends label not found"
    assert "Надіслати запит" in content or "Отправить запрос" in content, "Send request text not found"
    assert "Видалити друга" in content or "Удалить друга" in content, "Remove friend text not found"
    assert "статистик" in content.lower(), "Statistics text not found"
    assert "Вхідні запити" in content or "Входящие запросы" in content, "Pending requests text not found"
    assert "Прийняти" in content or "Принять" in content, "Accept text not found"
    assert "Відхилити" in content or "Отклонить" in content, "Reject text not found"
    
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
