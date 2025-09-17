# GLOW Intelligence App - E2E Contract Tests

## Overview

These tests validate the API contracts established during Calcination:
- `/api/auth/me` response shape (no profile_version)
- Logout JSON standardization (idempotent behavior)
- Session renewal and idle expiry behavior

## Safety & Prerequisites

⚠️ **IMPORTANT:** These tests are **DISABLED BY DEFAULT** to prevent accidental execution against production.

### Required Environment Variables

```bash
# Enable tests (required)
export RUN_E2E=1

# Target environment (required)
export BASE_URL=https://www.glowme.io

# Test account credentials (required)
export SMOKE_EMAIL=admin@glow.app
export SMOKE_PASSWORD=admin123

# Optional: Custom idle timeout for session tests
export SESSION_IDLE_MIN_FOR_TESTS=2
```

### Safety Notes

1. **Dedicated Test Account:** Tests use the same account as smoke scripts (`admin@glow.app`)
2. **Non-Destructive:** Tests avoid mutating production user data
3. **Idempotent Payloads:** Where writes are needed, they use safe/reversible values
4. **Skip by Default:** Without `RUN_E2E=1`, all tests are skipped

## Running Tests

### Local Development

```bash
# Install dependencies (if not already installed)
pip3 install pytest flask flask-sqlalchemy werkzeug

# Run all contract tests
RUN_E2E=1 BASE_URL=https://www.glowme.io \
SMOKE_EMAIL=admin@glow.app SMOKE_PASSWORD=admin123 \
python3 -m pytest tests/ -v

# Run specific test module
RUN_E2E=1 BASE_URL=https://www.glowme.io \
SMOKE_EMAIL=admin@glow.app SMOKE_PASSWORD=admin123 \
python3 -m pytest tests/test_auth_me.py -v

# Run only contract shape tests (fast)
RUN_E2E=1 BASE_URL=https://www.glowme.io \
SMOKE_EMAIL=admin@glow.app SMOKE_PASSWORD=admin123 \
python3 -m pytest -q tests/test_auth_me.py -k contract
```

### Verify Skip Behavior (Default)

```bash
# Without RUN_E2E=1, tests should be skipped
python3 -m pytest tests/ -v
# Expected output: SKIPPED [3] E2E contract tests disabled by default
```

### GitHub Actions (Future)

```yaml
# Commented example for future CI integration
# name: E2E Contract Tests
# on: [push, pull_request]
# jobs:
#   contract-tests:
#     runs-on: ubuntu-latest
#     steps:
#       - uses: actions/checkout@v3
#       - name: Set up Python
#         uses: actions/setup-python@v4
#         with:
#           python-version: '3.11'
#       - name: Install dependencies
#         run: pip install pytest flask flask-sqlalchemy werkzeug
#       - name: Run contract tests
#         env:
#           RUN_E2E: 1
#           BASE_URL: https://staging.glowme.io  # Use staging when available
#           SMOKE_EMAIL: ${{ secrets.SMOKE_EMAIL }}
#           SMOKE_PASSWORD: ${{ secrets.SMOKE_PASSWORD }}
#         run: pytest tests/ -v
```

## Test Modules

### `test_auth_me.py`
- Response shape validation
- profile_version absence verification
- Security headers validation
- Unauthorized request handling

### `test_logout_json.py`
- Standardized JSON contract validation
- Idempotent behavior testing
- No-redirect verification
- Session clearing confirmation

### `test_session_idle.py`
- Rolling refresh testing
- Idle expiry testing
- SESSION_EXPIRED JSON format validation
- User data preservation during renewal

### `conftest.py`
- Test configuration and fixtures
- Environment variable handling
- Safe test account setup

## Troubleshooting

### Tests Are Skipped
- Ensure `RUN_E2E=1` is set
- Check that all required environment variables are provided

### Import Errors
- Install required dependencies: `pip3 install pytest flask flask-sqlalchemy werkzeug`
- Ensure you're in the correct directory with `app.py`

### Session Tests Fail
- Set `SESSION_IDLE_MIN_FOR_TESTS=2` for faster testing
- Ensure session renewal is enabled in the target environment

### Authentication Errors
- Verify `SMOKE_EMAIL` and `SMOKE_PASSWORD` are correct
- Ensure the test account exists and is approved in the target environment

## Current Status

- **CI Integration:** Not enabled (uses existing smoke script workflow)
- **Target Environment:** Production (https://www.glowme.io)
- **Test Account:** Same as smoke scripts (`admin@glow.app`)
- **Execution:** Manual only (requires explicit `RUN_E2E=1`)

## Future Enhancements

- Enable in CI once staging environment is available
- Add more comprehensive contract validation
- Integrate with existing smoke test workflows
- Add performance benchmarking

