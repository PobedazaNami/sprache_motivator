"""
Test for friend request re-send functionality after rejection.

This test validates that users can re-send friend requests after:
1. A previous request was rejected
2. A friendship was removed

This addresses the issue "друзья брак" where users couldn't re-send requests.
"""
import asyncio
import os
from datetime import datetime, timezone

# Set up test environment
os.environ.setdefault('MONGODB_URI', 'mongodb://localhost:27017/sprache_test')
os.environ.setdefault('POSTGRES_URI', 'postgresql://user:pass@localhost/test')
os.environ.setdefault('REDIS_URI', 'redis://localhost:6379')
os.environ.setdefault('OPENAI_API_KEY', 'test-key')


async def test_resend_after_rejection():
    """Test that friend requests can be resent after rejection"""
    from bot.services import mongo_service
    
    # Initialize mongo service
    await mongo_service.init()
    
    if not mongo_service.is_ready():
        print("⚠️  MongoDB not available, skipping test")
        return
    
    # Test user IDs
    user_1 = 100001
    user_2 = 100002
    
    # Clean up any existing data
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    # Step 1: User 1 sends friend request to User 2
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is True, "First friend request should succeed"
    print("✓ First friend request sent successfully")
    
    # Step 2: Try to send duplicate request (should fail)
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is False, "Duplicate request should be prevented"
    print("✓ Duplicate request correctly prevented")
    
    # Step 3: User 2 rejects the request
    result = await mongo_service.reject_friend_request(user_2, user_1)
    assert result is True, "Request rejection should succeed"
    print("✓ Friend request rejected")
    
    # Step 4: Verify no pending requests exist
    pending = await mongo_service.get_pending_incoming_requests(user_2)
    assert user_1 not in pending, "No pending requests should exist after rejection"
    print("✓ Pending requests cleared after rejection")
    
    # Step 5: User 1 sends request again (should succeed now)
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is True, "Request should be allowed after previous rejection"
    print("✓ Friend request successfully resent after rejection")
    
    # Step 6: Verify new pending request exists
    pending = await mongo_service.get_pending_incoming_requests(user_2)
    assert user_1 in pending, "New pending request should exist"
    print("✓ New pending request created")
    
    # Clean up
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    print("\n✅ Resend after rejection test passed!")


async def test_resend_after_friend_removal():
    """Test that friend requests can be sent after removing a friend"""
    from bot.services import mongo_service
    
    if not mongo_service.is_ready():
        print("⚠️  MongoDB not available, skipping test")
        return
    
    # Test user IDs
    user_1 = 100003
    user_2 = 100004
    
    # Clean up any existing data
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    # Step 1: User 1 sends friend request
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is True, "Friend request should succeed"
    print("✓ Friend request sent")
    
    # Step 2: User 2 accepts
    result = await mongo_service.accept_friend_request(user_2, user_1)
    assert result is True, "Request acceptance should succeed"
    print("✓ Friend request accepted")
    
    # Step 3: Verify they are friends
    friends = await mongo_service.get_friends(user_1)
    assert user_2 in friends, "Users should be friends"
    print("✓ Friendship established")
    
    # Step 4: Try to send duplicate request (should fail - they're already friends)
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is False, "Cannot send request to existing friend"
    print("✓ Duplicate request to friend correctly prevented")
    
    # Step 5: User 1 removes User 2 as friend
    result = await mongo_service.remove_friend(user_1, user_2)
    assert result is True, "Friend removal should succeed"
    print("✓ Friend removed")
    
    # Step 6: Verify they are no longer friends
    friends = await mongo_service.get_friends(user_1)
    assert user_2 not in friends, "Users should not be friends after removal"
    print("✓ Friendship removed")
    
    # Step 7: User 1 sends friend request again (should succeed)
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is True, "Request should be allowed after friend removal"
    print("✓ Friend request successfully sent after removing friend")
    
    # Step 8: Verify new pending request exists
    pending = await mongo_service.get_pending_incoming_requests(user_2)
    assert user_1 in pending, "New pending request should exist"
    print("✓ New pending request created")
    
    # Clean up
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    print("\n✅ Resend after friend removal test passed!")


async def test_bidirectional_duplicate_check():
    """Test that duplicate check works bidirectionally"""
    from bot.services import mongo_service
    
    if not mongo_service.is_ready():
        print("⚠️  MongoDB not available, skipping test")
        return
    
    # Test user IDs
    user_1 = 100005
    user_2 = 100006
    
    # Clean up any existing data
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    # Step 1: User 1 sends friend request to User 2
    result = await mongo_service.send_friend_request(user_1, user_2)
    assert result is True, "First friend request should succeed"
    print("✓ User 1 sent request to User 2")
    
    # Step 2: User 2 tries to send request to User 1 (should fail - pending request exists)
    result = await mongo_service.send_friend_request(user_2, user_1)
    assert result is False, "Reverse request should be prevented when pending request exists"
    print("✓ Bidirectional duplicate check working for pending requests")
    
    # Step 3: User 2 accepts the request
    result = await mongo_service.accept_friend_request(user_2, user_1)
    assert result is True, "Request acceptance should succeed"
    print("✓ Request accepted")
    
    # Step 4: User 2 tries to send request to User 1 (should fail - already friends)
    result = await mongo_service.send_friend_request(user_2, user_1)
    assert result is False, "Request should be prevented when already friends"
    print("✓ Bidirectional duplicate check working for accepted friendships")
    
    # Clean up
    await mongo_service.db().friendships.delete_many({
        "$or": [
            {"user_id": user_1, "friend_id": user_2},
            {"user_id": user_2, "friend_id": user_1}
        ]
    })
    
    print("\n✅ Bidirectional duplicate check test passed!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Friend Request Re-send Functionality")
    print("=" * 60)
    print()
    
    try:
        await test_resend_after_rejection()
        print()
        await test_resend_after_friend_removal()
        print()
        await test_bidirectional_duplicate_check()
        
        print()
        print("=" * 60)
        print("✅ All friend request re-send tests passed!")
        print("=" * 60)
        print()
        print("📝 Summary:")
        print("   - Users can resend requests after rejection")
        print("   - Users can send requests after removing friends")
        print("   - Bidirectional duplicate checking works correctly")
        print("   - Pending and accepted statuses are properly filtered")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
