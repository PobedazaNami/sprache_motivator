# Contributing to Sprache Motivator

Thank you for your interest in contributing to Sprache Motivator! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

1. **Clear title**: Describe the issue briefly
2. **Description**: Detailed explanation of the problem
3. **Steps to reproduce**: How to recreate the issue
4. **Expected behavior**: What should happen
5. **Actual behavior**: What actually happens
6. **Environment**: OS, Python version, Docker version
7. **Logs**: Relevant error messages or logs

### Suggesting Features

For feature requests:

1. **Use case**: Explain why this feature is needed
2. **Proposed solution**: How you think it should work
3. **Alternatives**: Other approaches you've considered
4. **Additional context**: Screenshots, examples, etc.

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Test thoroughly**:
   ```bash
   pytest test_bot.py -v
   ```
5. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: description"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Create a Pull Request**

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Local Development

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/sprache_motivator.git
   cd sprache_motivator
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Setup environment:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. Start services:
   ```bash
   docker-compose up -d postgres redis
   ```

6. Run migrations:
   ```bash
   alembic upgrade head
   ```

7. Start bot:
   ```bash
   python -m bot.main
   ```

## Code Style

### Python Style

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters
- Use meaningful variable names

Example:
```python
async def get_user_by_id(user_id: int) -> Optional[User]:
    """
    Get user by Telegram ID.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        User object if found, None otherwise
    """
    # Implementation
    pass
```

### Async/Await

- Use async/await for I/O operations
- Use asyncio.gather() for parallel operations
- Handle exceptions properly

### Database

- Use SQLAlchemy ORM
- Create migrations for schema changes:
  ```bash
  alembic revision --autogenerate -m "description"
  ```
- Always use async sessions

### Documentation

- Add docstrings to functions and classes
- Update README.md for new features
- Add comments for complex logic
- Update ARCHITECTURE.md for structural changes

## Testing

### Running Tests

```bash
# All tests
pytest test_bot.py -v

# Specific test
pytest test_bot.py::TestLocalization::test_get_text_ukrainian -v

# With coverage
pytest test_bot.py --cov=bot --cov-report=html
```

### Writing Tests

- Test new features
- Test edge cases
- Use meaningful test names
- Mock external services (OpenAI, Telegram API)

Example:
```python
def test_user_creation():
    """Test that user is created with correct defaults"""
    user = User(telegram_id=123456)
    assert user.status == UserStatus.PENDING
    assert user.interface_language == InterfaceLanguage.RUSSIAN
```

## Project Structure

```
bot/
├── handlers/          # Message and callback handlers
│   ├── start.py      # Registration
│   ├── translator.py # Translation mode
│   ├── trainer.py    # Daily trainer
│   ├── settings.py   # User settings
│   └── admin.py      # Admin panel
├── models/
│   └── database.py   # Database models
├── services/
│   ├── redis_service.py       # Redis operations
│   ├── translation_service.py # OpenAI integration
│   └── database_service.py    # Database operations
├── locales/
│   └── texts.py      # Localization
├── utils/
│   └── keyboards.py  # Keyboard layouts
├── config.py         # Configuration
└── main.py          # Entry point
```

## Adding Features

### Adding a New Handler

1. Create handler in `bot/handlers/`
2. Define router
3. Add handlers for messages/callbacks
4. Register router in `bot/main.py`

Example:
```python
# bot/handlers/new_feature.py
from aiogram import Router

router = Router()

@router.message(F.text == "Feature")
async def handle_feature(message: Message):
    await message.answer("Feature response")
```

```python
# bot/main.py
from bot.handlers import new_feature

dp.include_router(new_feature.router)
```

### Adding Localization

1. Add keys to both `uk` and `ru` in `bot/locales/texts.py`
2. Use `get_text(lang, "key")` to retrieve

Example:
```python
LOCALES = {
    "uk": {
        "new_key": "Новий текст"
    },
    "ru": {
        "new_key": "Новый текст"
    }
}
```

### Adding Database Models

1. Add model to `bot/models/database.py`
2. Create migration:
   ```bash
   alembic revision --autogenerate -m "Add new model"
   ```
3. Review and apply:
   ```bash
   alembic upgrade head
   ```

## Commit Messages

Use clear, descriptive commit messages:

- `feat: Add voice message support`
- `fix: Resolve translation caching issue`
- `docs: Update README with new features`
- `test: Add tests for user service`
- `refactor: Optimize database queries`
- `chore: Update dependencies`

## Version Control

### Branching Strategy

- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

### Before Submitting PR

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] Reviewed your own changes

## Review Process

1. **Automated checks**: GitHub Actions runs tests
2. **Code review**: Maintainer reviews changes
3. **Feedback**: Address review comments
4. **Approval**: PR is approved
5. **Merge**: Changes merged to develop/main

## Getting Help

- **Issues**: Check existing issues or create new one
- **Discussions**: Use GitHub Discussions for questions
- **Telegram**: Contact @reeziat for support

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in the project README. Thank you for making Sprache Motivator better!

---

Happy coding! 🚀
