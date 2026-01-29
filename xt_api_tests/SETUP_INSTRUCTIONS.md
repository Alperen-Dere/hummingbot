# XT API Validation Tests - Setup Instructions

## ⚡ Quick Start (5 minutes)

### Step 1: Get Your XT API Credentials

1. Go to https://www.xt.com/en/accounts/api
2. Create a new API key with these permissions:
   - ✅ **Read** - View account balance and orders
   - ✅ **Trade** - (Optional, for full testing)
   - ⚠️ **Withdraw** - NOT REQUIRED (keep disabled for security)

3. Save your API Key and API Secret securely

### Step 2: Configure Environment

```bash
# Navigate to test directory
cd /home/alp/hummingbot/xt_api_tests

# Create .env file from template
cp .env.example .env

# Edit .env and add your credentials
nano .env  # or use vi, vim, code, etc.
```

Your `.env` file should look like:
```
XT_API_KEY=your_actual_api_key_here
XT_API_SECRET=your_actual_api_secret_here
```

### Step 3: Activate Virtual Environment

```bash
# Activate the virtual environment
source venv/bin/activate

# Verify activation (you should see (venv) in your prompt)
which python
# Should show: /home/alp/hummingbot/xt_api_tests/venv/bin/python
```

### Step 4: Run Tests

```bash
# Run the validation test suite
python test_xt_api_validation.py
```

## 📊 Expected Output

If everything is configured correctly, you should see:

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

🌐 PHASE 4: WEBSOCKET TESTS (Optional)
--------------------------------------------------------------------------------
🔌 Testing Public WebSocket...
✅ Public WebSocket - SUCCESS (3 messages)

🔐 Testing Private WebSocket...
✅ Private WebSocket - SUCCESS (authenticated)

================================================================================
TEST SUMMARY
================================================================================

Total Tests: 10
✅ Passed: 10
❌ Failed: 0
Success Rate: 100.0%

🎯 CONFIRMED: Use 'validate' headers for authentication

📄 Detailed results saved to: xt_api_test_results.json
```

## 🔍 What Gets Tested

### Phase 1: Public Endpoints (No Authentication)
- ✅ Server time - Tests connectivity and time sync
- ✅ Trading pairs - Validates available markets
- ✅ Ticker prices - Checks market data access
- ✅ Order book depth - Validates order book retrieval
- ✅ Recent trades - Tests trade history access

### Phase 2: Authentication Testing (CRITICAL!)
- 🔐 Tests **BOTH** header formats:
  - `validate-*` headers (official docs)
  - `xt-validate-*` headers (PR #6766)
- ✅ Determines which format actually works
- ✅ Saves working format for remaining tests

### Phase 3: Private Endpoints
- ✅ Account balances - Tests authenticated data access
- ✅ WebSocket token - Gets listenKey for private WS
- ✅ Open orders - Tests order query functionality

### Phase 4: WebSocket Tests
- ✅ Public WebSocket - Order book updates, trades
- ✅ Private WebSocket - Order/balance updates

## 📁 Output Files

After running tests, you'll find:

1. **`xt_api_test_results.json`** - Detailed results:
   ```json
   {
     "summary": {
       "total_tests": 10,
       "passed": 10,
       "failed": 0,
       "success_rate": "100.0%",
       "working_auth_format": "validate",
       "timestamp": "2026-01-29 12:34:56"
     },
     "test_results": [ ... ]
   }
   ```

2. **Console output** - Real-time test progress

## ❌ Troubleshooting

### Problem: "XT_API_KEY and XT_API_SECRET must be set"

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# If not, create it
cp .env.example .env

# Edit and add your credentials
nano .env
```

### Problem: "Authentication failed with both header formats"

**Possible causes:**
1. **Invalid API credentials** - Double-check key and secret
2. **Insufficient permissions** - Enable Read permission on XT
3. **IP whitelist** - If you have IP restrictions, add your IP
4. **Expired API key** - Create a new key if needed

**Debug steps:**
```bash
# Verify .env file has actual credentials (not placeholders)
cat .env

# Should show real values, not:
# XT_API_KEY=your_api_key_here  ❌
```

### Problem: "Public endpoints fail"

**Possible causes:**
1. **Network connectivity** - Check internet connection
2. **Firewall blocking** - Whitelist sapi.xt.com
3. **XT API down** - Check https://status.xt.com

**Test connectivity:**
```bash
# Test if you can reach XT API
curl https://sapi.xt.com/v4/public/time
```

### Problem: "Rate limit errors"

**Solution:**
- Tests include 0.5s delays between requests
- If still hitting limits, edit test script and increase delays
- Check your API key rate limit tier on XT

### Problem: "WebSocket tests timeout"

**Causes:**
- WebSocket ports blocked by firewall
- Network instability
- XT WebSocket service issues

**Solution:**
- WebSocket tests are optional for validation
- Main goal is REST API auth validation
- Can skip WebSocket tests and still proceed

## 🎯 Next Steps After Successful Tests

1. **Review Results**
   ```bash
   cat xt_api_test_results.json | jq .summary
   ```

2. **Note Authentication Format**
   - Check which header format worked: `validate` or `xt-validate`
   - Use this format in connector implementation

3. **Review Response Structures**
   - Examine actual API responses in JSON file
   - Use for unit test mocking

4. **Proceed with Connector**
   - Use validated endpoints in `xt_constants.py`
   - Use confirmed auth format in `xt_auth.py`
   - Reference response structures for parsing

## 📞 Support

### XT API Support
- **Documentation**: https://doc.xt.com/
- **Telegram Group**: https://t.me/XT_api
- **Email**: Check XT website for support contact

### Hummingbot Community
- **Discord**: https://discord.gg/hummingbot
- **GitHub**: https://github.com/hummingbot/hummingbot

## 🔒 Security Notes

1. **Never commit .env file** - It contains your API credentials
2. **Use read-only API keys** for testing when possible
3. **Enable IP whitelist** for production API keys
4. **Rotate API keys** regularly
5. **Keep API secrets secure** - Never share or expose them

## 🧪 Development Testing

If you're developing the connector and need to test repeatedly:

```bash
# Quick test run
source venv/bin/activate && python test_xt_api_validation.py

# View last results
cat xt_api_test_results.json | jq .

# Clean up old results
rm xt_api_test_results.json

# Run tests again
python test_xt_api_validation.py
```

## ✅ Success Criteria

Tests are successful when:
- ✅ All public endpoints return HTTP 200
- ✅ Authentication works with one header format
- ✅ Private endpoints accessible with working auth
- ✅ Response structures match expectations
- ✅ `xt_api_test_results.json` created with results

Once all tests pass, you're ready to implement the full XT connector!
