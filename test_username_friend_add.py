"""
Test to verify that adding friends by username works correctly.
This test validates the fix for the issue where entering a username
would always return "user not found".
"""
import asyncio
from bot.services.database_service import UserService
from bot.models.database import UserStatus


async def test_get_user_by_username():
    """Test that we can find users by username"""
    print("Testing get_user_by_username method...")
    
    # Create test users
    session = None  # MongoDB doesn't need session but we keep for compatibility
    
    # Create first user
    user1 = await UserService.get_or_create_user(
        session, 
        telegram_id=111111,
        username="testuser1",
        first_name="Test User 1"
    )
    
    # Create second user
    user2 = await UserService.get_or_create_user(
        session,
        telegram_id=222222,
        username="testuser2",
        first_name="Test User 2"
    )
    
    # Update user1 to APPROVED status
    await UserService.update_user(session, user1, status=UserStatus.APPROVED)
    
    # Test finding user by username
    found_user = await UserService.get_user_by_username(session, "testuser1")
    
    assert found_user is not None, "User should be found by username"
    assert found_user.telegram_id == 111111, f"Expected telegram_id 111111, got {found_user.telegram_id}"
    assert found_user.username == "testuser1", f"Expected username 'testuser1', got {found_user.username}"
    assert found_user.first_name == "Test User 1", f"Expected first_name 'Test User 1', got {found_user.first_name}"
    
    print("✓ Found user by username successfully")
    
    # Test finding non-existent user
    not_found = await UserService.get_user_by_username(session, "nonexistent")
    assert not_found is None, "Non-existent user should return None"
    
    print("✓ Non-existent username returns None as expected")
    
    print("\n✅ All username search tests passed!")


async def test_username_without_at_symbol():
    """Test that username search works without @ symbol"""
    print("\nTesting username search without @ symbol...")
    
    session = None
    
    # The handler removes @ before calling get_user_by_username
    # So we test that the username in DB doesn't have @ symbol
    user = await UserService.get_or_create_user(
        session,
        telegram_id=333333,
        username="userwithoutatsymbol",
        first_name="Test User 3"
    )
    
    # Search without @ (as it will be stripped by handler)
    found = await UserService.get_user_by_username(session, "userwithoutatsymbol")
    assert found is not None, "Should find user when searching without @"
    assert found.telegram_id == 333333
    
    print("✓ Username search without @ works correctly")


if __name__ == "__main__":
    from bot.services import mongo_service
    from bot.config import settings
    
    print("Initializing MongoDB connection...\n")
    mongo_service.init(settings.MONGO_URI, settings.MONGO_DB_NAME)
    
    try:
        asyncio.run(test_get_user_by_username())
        asyncio.run(test_username_without_at_symbol())
        print("\n🎉 All tests completed successfully!")
    finally:
        mongo_service.close()
