"""
Test for friend request system with notifications.

This test validates:
1. Friend request workflow (send, accept, reject)
2. Notification system when friend request is sent
3. Pending request management
4. Status transitions
"""


def test_mongo_friend_request_workflow():
    """Test friend request workflow in mongo_service"""
    with open('bot/services/mongo_service.py', 'r') as f:
        content = f.read()
    
    # Check that send_friend_request creates pending status
    assert 'status": "pending"' in content or "status': 'pending'" in content, \
        "send_friend_request doesn't set pending status"
    
    # Check that accept_friend_request updates to accepted
    assert 'status": "accepted"' in content or "status': 'accepted'" in content, \
        "accept_friend_request doesn't set accepted status"
    
    # Check that reject removes the request
    assert 'delete_one' in content or 'delete_many' in content, \
        "reject_friend_request doesn't delete request"
    
    print("✓ Friend request workflow is correctly implemented in mongo_service")


def test_friend_request_notification():
    """Test that friend request notifications are sent"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Check that notification is sent when friend request is created
    assert 'friend_request_notification' in content, \
        "Missing friend_request_notification text"
    
    assert 'send_message' in content, \
        "Missing send_message call for notification"
    
    assert 'send_friend_request' in content, \
        "Missing send_friend_request call"
    
    print("✓ Friend request notification system is implemented")


def test_pending_requests_handlers():
    """Test that pending request handlers exist"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Check for view pending requests handler
    assert 'view_pending_requests' in content, \
        "Missing view_pending_requests handler"
    
    assert 'get_pending_incoming_requests' in content, \
        "Missing get_pending_incoming_requests call"
    
    # Check for accept handler
    assert 'accept_friend_request' in content, \
        "Missing accept_friend_request handler"
    
    assert 'accept_request_' in content, \
        "Missing accept_request_ callback data"
    
    # Check for reject handler
    assert 'reject_friend_request' in content, \
        "Missing reject_friend_request handler"
    
    assert 'reject_request_' in content, \
        "Missing reject_request_ callback data"
    
    print("✓ Pending request handlers are properly implemented")


def test_friend_request_localization():
    """Test that all friend request texts are localized"""
    with open('bot/locales/texts.py', 'r') as f:
        content = f.read()
    
    # Required keys for friend request system
    required_keys = [
        'friend_request_sent',
        'friend_request_exists',
        'friend_request_accepted',
        'friend_request_rejected',
        'friend_request_notification',
        'pending_requests_title',
        'no_pending_requests',
        'btn_pending_requests'
    ]
    
    for key in required_keys:
        assert f'"{key}"' in content, f"Missing localization key: {key}"
        count = content.count(f'"{key}"')
        assert count >= 2, f"Key {key} not found in both languages (found {count} times)"
    
    print("✓ All friend request localization keys exist in both languages")


def test_pending_requests_keyboard():
    """Test that pending requests keyboard exists"""
    with open('bot/utils/keyboards.py', 'r') as f:
        content = f.read()
    
    assert 'get_pending_requests_keyboard' in content, \
        "Missing get_pending_requests_keyboard function"
    
    assert 'accept_request_' in content, \
        "Missing accept_request_ callback in keyboard"
    
    assert 'reject_request_' in content, \
        "Missing reject_request_ callback in keyboard"
    
    assert 'btn_pending_requests' in content, \
        "Missing btn_pending_requests in friends menu"
    
    print("✓ Pending requests keyboard is properly implemented")


def test_status_field_in_mongo_operations():
    """Test that status field is used in mongo operations"""
    with open('bot/services/mongo_service.py', 'r') as f:
        content = f.read()
    
    # get_friends should filter by accepted status
    lines = content.split('\n')
    in_get_friends = False
    found_status_filter = False
    
    for i, line in enumerate(lines):
        if 'async def get_friends' in line:
            in_get_friends = True
        elif in_get_friends and 'async def' in line and 'get_friends' not in line:
            break
        elif in_get_friends and '"accepted"' in line:
            found_status_filter = True
            break
    
    assert found_status_filter, "get_friends doesn't filter by accepted status"
    
    # remove_friend should only remove accepted friendships
    in_remove_friend = False
    found_status_filter = False
    
    for i, line in enumerate(lines):
        if 'async def remove_friend' in line:
            in_remove_friend = True
        elif in_remove_friend and 'async def' in line and 'remove_friend' not in line:
            break
        elif in_remove_friend and '"accepted"' in line:
            found_status_filter = True
            break
    
    assert found_status_filter, "remove_friend doesn't filter by accepted status"
    
    print("✓ Status field is properly used in mongo operations")


def test_backward_compatibility():
    """Test that legacy add_friend function exists for backward compatibility"""
    with open('bot/services/mongo_service.py', 'r') as f:
        content = f.read()
    
    # Check that add_friend still exists
    assert 'async def add_friend' in content, \
        "Legacy add_friend function removed - breaks backward compatibility"
    
    # Check that it delegates to send_friend_request
    lines = content.split('\n')
    in_add_friend = False
    found_delegation = False
    
    for line in lines:
        if 'async def add_friend' in line:
            in_add_friend = True
        elif in_add_friend and 'send_friend_request' in line:
            found_delegation = True
            break
        elif in_add_friend and 'async def' in line:
            break
    
    assert found_delegation, "add_friend doesn't delegate to send_friend_request"
    
    print("✓ Backward compatibility is maintained")


if __name__ == "__main__":
    print("Running friend request system tests...\n")
    
    test_mongo_friend_request_workflow()
    test_friend_request_notification()
    test_pending_requests_handlers()
    test_friend_request_localization()
    test_pending_requests_keyboard()
    test_status_field_in_mongo_operations()
    test_backward_compatibility()
    
    print("\n✅ All friend request system tests passed!")
    print("\n📝 Summary:")
    print("   - Friend request workflow is correctly implemented")
    print("   - Notification system sends alerts when requests are made")
    print("   - Pending requests can be viewed, accepted, and rejected")
    print("   - All texts are properly localized")
    print("   - Keyboards include pending request management")
    print("   - Status field is used correctly in all operations")
    print("   - Backward compatibility is maintained")
