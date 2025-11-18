"""
Test to verify the friends username fix is implemented correctly.
This test validates code changes without requiring runtime dependencies.
"""
import ast


def test_database_service_has_username_method():
    """Verify that database_service has get_user_by_username method"""
    with open('bot/services/database_service.py', 'r') as f:
        content = f.read()
    
    # Parse the code
    tree = ast.parse(content)
    
    # Find all methods in UserService class
    user_service_methods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'UserService':
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef):
                    user_service_methods.append(item.name)
    
    assert 'get_user_by_username' in user_service_methods, \
        "UserService should have get_user_by_username method"
    
    print("✓ UserService has get_user_by_username method")
    
    # Verify the method signature
    assert 'async def get_user_by_username' in content, \
        "get_user_by_username should be async"
    assert 'username: str' in content, \
        "get_user_by_username should accept username parameter"
    
    print("✓ get_user_by_username has correct signature")


def test_friends_handler_uses_username_search():
    """Verify that friends handler now uses username search instead of rejecting it"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Verify that username search is implemented
    assert 'await UserService.get_user_by_username(session, username)' in content, \
        "Friends handler should call get_user_by_username when username is provided"
    
    print("✓ Friends handler calls get_user_by_username for @username input")
    
    # Verify that the old error message telling users to use ID instead is removed
    assert 'Будь ласка, використовуйте Telegram ID користувача' not in content, \
        "Old error message asking for Telegram ID should be removed"
    assert 'Пожалуйста, используйте Telegram ID пользователя' not in content, \
        "Old error message asking for Telegram ID should be removed"
    
    print("✓ Old error message asking to use Telegram ID is removed")
    
    # Verify that we strip @ from username before searching
    assert 'username = friend_identifier[1:]' in content, \
        "Handler should strip @ symbol from username before searching"
    
    print("✓ Handler strips @ symbol before searching")


def test_username_search_logic_flow():
    """Verify the complete logic flow for username-based friend adding"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Find the process_add_friend function
    start_idx = content.find('async def process_add_friend')
    end_idx = content.find('\n\n@router.callback_query', start_idx)
    function_content = content[start_idx:end_idx]
    
    # Verify the flow:
    # 1. If starts with @, extract username
    assert 'if friend_identifier.startswith("@")' in function_content, \
        "Should check if input starts with @"
    
    # 2. Search by username
    assert 'await UserService.get_user_by_username' in function_content, \
        "Should search for user by username"
    
    # 3. Get friend_id from found user
    assert 'friend_id = friend.telegram_id' in function_content, \
        "Should extract telegram_id from found user"
    
    # 4. Check if friend was found
    assert 'if not friend:' in function_content, \
        "Should check if friend was found"
    
    # 5. Return error if not found
    lines_after_not_found = function_content[function_content.find('if not friend:'):function_content.find('if not friend:') + 300]
    assert 'friend_not_found' in lines_after_not_found, \
        "Should return friend_not_found error if user not found"
    
    print("✓ Complete logic flow for username search is correct")


def test_optimization_no_double_fetch():
    """Verify that we don't fetch the same user twice"""
    with open('bot/handlers/friends.py', 'r') as f:
        content = f.read()
    
    # Find the process_add_friend function
    start_idx = content.find('async def process_add_friend')
    end_idx = content.find('\n\n@router.callback_query', start_idx)
    function_content = content[start_idx:end_idx]
    
    # Verify we only fetch by ID if not already fetched by username
    assert 'if not friend:' in function_content, \
        "Should check if friend is already fetched before fetching by ID"
    
    # Verify that get_or_create_user is called inside the "if not friend:" block
    # This ensures we don't fetch the user twice
    assert 'if not friend:' in function_content and \
           'get_or_create_user' in function_content, \
        "Should conditionally fetch by ID only if friend is not already set"
    
    # Verify the pattern: fetch by ID only happens inside "if not friend:" block
    # This ensures we don't fetch the user twice
    if_not_friend_idx = function_content.find('if not friend:')
    assert if_not_friend_idx > 0, "Should have 'if not friend:' check"
    
    # Extract the block after "if not friend:"
    # Look for the next line that is at the same indentation level (end of if block)
    lines = function_content[if_not_friend_idx:].split('\n')
    if_block_lines = []
    capturing = False
    for i, line in enumerate(lines):
        if i == 0:  # The "if not friend:" line
            capturing = True
            continue
        if capturing:
            # Check indentation - if it's less than or equal to "if" statement, we're done
            if line and not line.startswith('        '):  # 8 spaces or more means inside if block
                break
            if_block_lines.append(line)
    
    if_block = '\n'.join(if_block_lines)
    
    # The friend fetch by ID should be inside this block
    assert 'UserService.get_or_create_user(session, friend_id)' in if_block, \
        "Friend fetch by ID should be inside 'if not friend:' block"
    
    print("✓ Optimization: user is not fetched twice")


if __name__ == "__main__":
    print("Testing friends username fix implementation...\n")
    
    test_database_service_has_username_method()
    print()
    test_friends_handler_uses_username_search()
    print()
    test_username_search_logic_flow()
    print()
    test_optimization_no_double_fetch()
    
    print("\n✅ All validation tests passed!")
    print("\n📝 Summary of changes:")
    print("   1. Added get_user_by_username method to UserService")
    print("   2. Updated friends handler to search by username when @ is provided")
    print("   3. Removed old error message that told users to use Telegram ID only")
    print("   4. Optimized to avoid fetching the same user twice")
    print("   5. Properly handles both @username and numeric ID formats")
