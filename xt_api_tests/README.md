# XT Exchange API Validation Tests

This test suite validates XT Exchange API connectivity and determines the correct authentication header format before implementing the full Hummingbot connector.

## Purpose

1. **Resolve authentication header format** (`validate-*` vs `xt-validate-*`)
2. **Verify all endpoint paths and response structures**
3. **Confirm rate limits and error handling**
4. **Test both REST and WebSocket connectivity**

## Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your XT API credentials
# Get credentials from: https://www.xt.com/en/accounts/api
nano .env  # or use your preferred editor
```

### 3. Run Tests

```bash
# Run the validation test suite
python test_xt_api_validation.py
```

## What Gets Tested

### Public Endpoints (No Auth)
- ✅ Server time
- ✅ Trading pairs list
- ✅ Ticker prices
- ✅ Order book depth
- ✅ Recent trades

### Private Endpoints (Auth Required)
- ✅ Account balances (tests BOTH auth formats)
- ✅ WebSocket token generation
- ✅ Open orders list

### WebSocket Tests (Optional)
- WebSocket public connection and subscriptions
- WebSocket private connection with authentication

## Expected Output

```
================================================================================
XT EXCHANGE API VALIDATION TEST SUITE
================================================================================

📖 PHASE 1: PUBLIC ENDPOINTS (No Authentication)
--------------------------------------------------------------------------------
✅ 1. Server Time - SUCCESS
✅ 2. Trading Pairs - SUCCESS
✅ 3. Ticker Price - SUCCESS
✅ 4. Order Book Depth - SUCCESS
✅ 5. Recent Trades - SUCCESS

🔐 PHASE 2: AUTHENTICATION VALIDATION
--------------------------------------------------------------------------------
Testing BOTH header formats to determine which works...

✅ 6. Account Balance (AUTH TEST) - SUCCESS (validate headers)

✅ Authentication successful with: validate headers
📝 This format will be used for remaining tests

🔒 PHASE 3: PRIVATE ENDPOINTS (Authenticated)
--------------------------------------------------------------------------------
✅ 7. WebSocket Token - SUCCESS
⚠️  Skipping order placement tests (would create real orders)
✅ 8. Open Orders - SUCCESS

================================================================================
TEST SUMMARY
================================================================================

Total Tests: 8
✅ Passed: 8
❌ Failed: 0
Success Rate: 100.0%

🎯 CONFIRMED: Use 'validate' headers for authentication

📄 Detailed results saved to: xt_api_test_results.json
```

## Test Results

After running, check:
- **Console output**: Real-time test results
- **`xt_api_test_results.json`**: Detailed test data including:
  - Endpoint responses
  - Authentication format used
  - Response times
  - Error messages (if any)

## Troubleshooting

### Authentication Fails
- Verify your API key and secret in `.env`
- Check API key permissions on XT.com
- Ensure API key has spot trading enabled

### Public Endpoints Fail
- Check network connectivity
- Verify XT API is not blocked by firewall
- Try accessing https://sapi.xt.com directly

### Rate Limit Errors
- Tests include delays between requests
- If still hitting limits, increase delays in script
- Check your API key rate limit tier

## Next Steps

After successful validation:
1. Review `xt_api_test_results.json` for confirmed endpoints
2. Note which authentication header format works
3. Use validated information for full connector implementation
4. Reference response structures for unit test mocking

## Support

- **XT API Documentation**: https://doc.xt.com/
- **XT API Support**: https://t.me/XT_api
- **Hummingbot Discord**: https://discord.gg/hummingbot
