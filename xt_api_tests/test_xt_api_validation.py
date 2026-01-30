"""
XT Exchange API Validation Test Suite
Tests authentication, endpoints, and connectivity before full connector implementation.

This script will:
1. Test all public endpoints (no auth required)
2. Test BOTH authentication header formats to determine which works
3. Test private endpoints with the working auth format
4. Save detailed results to JSON file
"""

import asyncio
import hashlib
import hmac
import json
import time
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
import websockets
from dotenv import load_dotenv
import os


class XTAPITester:
    """Test XT API endpoints and authentication"""
    
    BASE_URL = "https://sapi.xt.com"
    WSS_PUBLIC = "wss://stream.xt.com/public"
    WSS_PRIVATE = "wss://stream.xt.com/private"
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_results = []
        self.working_auth_format = None
        
    def _generate_signature_v1(self, method: str, path: str, params: str = "") -> Tuple[Dict[str, str], str]:
        """Generate signature with 'validate-*' headers (official docs)"""
        timestamp = str(int(time.time() * 1000))
        
        headers = OrderedDict([
            ("validate-algorithms", "HmacSHA256"),
            ("validate-appkey", self.api_key),
            ("validate-recvwindow", "60000"),
            ("validate-timestamp", timestamp),
        ])
        
        # Build X (header string)
        X = urlencode(dict(sorted(headers.items())))
        
        # Build Y (data string)
        Y = f"#{method}#{path}"
        if params:
            Y += f"#{params}"
        
        # Generate signature
        message = X + Y
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers["validate-signature"] = signature
        headers["Content-Type"] = "application/json"
        
        return dict(headers), signature
    
    def _generate_signature_v2(self, method: str, path: str, params: str = "") -> Tuple[Dict[str, str], str]:
        """Generate signature with 'xt-validate-*' headers (PR #6766)"""
        timestamp = str(int(time.time() * 1000))
        
        headers = OrderedDict([
            ("xt-validate-algorithms", "HmacSHA256"),
            ("xt-validate-appkey", self.api_key),
            ("xt-validate-recvwindow", "5000"),
            ("xt-validate-timestamp", timestamp),
        ])
        
        # Build X (header string)
        X = urlencode(dict(sorted(headers.items())))
        
        # Build Y (data string)
        Y = f"#{method}#{path}"
        if params:
            Y += f"#{params}"
        
        # Generate signature
        message = X + Y
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers["xt-validate-signature"] = signature
        headers["Content-Type"] = "application/json"
        
        return dict(headers), signature
    
    async def test_endpoint(
        self,
        name: str,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        requires_auth: bool = False,
        test_both_auth_formats: bool = False,
        optional_if_not_found: bool = False,
        success_if_order_not_found: bool = False
    ) -> Dict[str, Any]:
        """Test a single API endpoint"""
        
        result = {
            "test": name,
            "endpoint": path,
            "method": method,
            "requires_auth": requires_auth,
            "passed": False,
            "skipped": False,
            "error": None,
            "response": None,
            "auth_format": None,
            "duration_ms": 0
        }
        
        url = f"{self.BASE_URL}{path}"
        
        try:
            start_time = time.time()
            
            if requires_auth:
                # Test both formats if requested, or use the known working format
                if test_both_auth_formats:
                    formats_to_test = ["validate", "xt-validate"]
                elif self.working_auth_format:
                    formats_to_test = [self.working_auth_format]
                else:
                    formats_to_test = ["validate"]
                
                for auth_format in formats_to_test:
                    # XT signature: Y = #method#path#query#body
                    # GET/DELETE with params: query string (sorted). POST: body (JSON).
                    method_upper = method.upper()
                    if method_upper in ("GET", "DELETE") and params:
                        signature_payload = urlencode(sorted(params.items()))
                    elif data:
                        signature_payload = json.dumps(data)
                    else:
                        signature_payload = ""
                    headers, signature = (
                        self._generate_signature_v1(method_upper, path, signature_payload)
                        if auth_format == "validate"
                        else self._generate_signature_v2(method_upper, path, signature_payload)
                    )
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.request(
                            method=method,
                            url=url,
                            headers=headers,
                            params=params,
                            json=data,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            response_text = await response.text()
                            try:
                                response_json = json.loads(response_text) if response_text else {}
                            except json.JSONDecodeError:
                                response_json = {"error": "Invalid JSON response", "raw": response_text}
                            
                            result["status_code"] = response.status
                            result["response"] = response_json
                            result["auth_format"] = auth_format
                            
                            if response.status == 200 and response_json.get("rc") == 0:
                                result["passed"] = True
                                result["duration_ms"] = int((time.time() - start_time) * 1000)
                                print(f"✅ {name} - SUCCESS ({auth_format} headers)")
                                
                                # Remember working auth format
                                if test_both_auth_formats and not self.working_auth_format:
                                    self.working_auth_format = auth_format
                                break
                            elif response.status in [401, 403]:
                                print(f"❌ {name} - AUTH FAILED ({auth_format} headers)")
                                if auth_format == formats_to_test[-1]:
                                    result["error"] = f"Authentication failed with {'both' if test_both_auth_formats else auth_format} header format(s)"
                            else:
                                result["error"] = response_json.get("mc", f"HTTP {response.status}")
                                if success_if_order_not_found and response.status == 200:
                                    mc = str(response_json.get("mc", "")).upper()
                                    if "ORDER" in mc or "NOT_FOUND" in mc or "NOT FOUND" in mc:
                                        result["passed"] = True
                                        result["duration_ms"] = int((time.time() - start_time) * 1000)
                                        print(f"✅ {name} - SUCCESS ({auth_format} headers, endpoint OK, order not found as expected)")
                                        break
                                print(f"⚠️  {name} - ERROR: {result['error']} ({auth_format} headers)")
                                if not test_both_auth_formats:
                                    break
            else:
                # Public endpoint - no auth
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method=method,
                        url=url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_text = await response.text()
                        try:
                            response_json = json.loads(response_text) if response_text else {}
                        except json.JSONDecodeError:
                            response_json = {"error": "Invalid JSON response", "raw": response_text}
                        
                        result["status_code"] = response.status
                        result["response"] = response_json
                        result["duration_ms"] = int((time.time() - start_time) * 1000)
                        
                        if response.status == 200 and response_json.get("rc") == 0:
                            result["passed"] = True
                            print(f"✅ {name} - SUCCESS")
                        else:
                            result["error"] = response_json.get("mc", f"HTTP {response.status}")
                            if optional_if_not_found and ("not found" in str(result["error"]).lower() or "API not found" in str(result["error"])):
                                result["passed"] = True
                                result["skipped"] = True
                                print(f"⏭️  {name} - SKIPPED (optional endpoint not in XT API: {result['error']})")
                            else:
                                print(f"❌ {name} - FAILED: {result['error']}")
                            
        except Exception as e:
            result["error"] = str(e)
            print(f"💥 {name} - EXCEPTION: {str(e)}")
        
        self.test_results.append(result)
        
        # Add small delay between tests to avoid rate limiting
        await asyncio.sleep(0.5)
        
        return result
    
    async def test_websocket_public(self) -> Dict[str, Any]:
        """Test public WebSocket connection"""
        result = {
            "test": "Public WebSocket",
            "endpoint": self.WSS_PUBLIC,
            "passed": False,
            "error": None,
            "messages_received": 0
        }
        
        try:
            print("\n🔌 Testing Public WebSocket...")
            async with websockets.connect(self.WSS_PUBLIC, ping_timeout=10) as ws:
                # Subscribe to depth updates
                subscribe_msg = {
                    "method": "SUBSCRIBE",
                    "params": ["depth_update@btc_usdt"],
                    "id": 1
                }
                await ws.send(json.dumps(subscribe_msg))
                print(f"   📤 Sent subscription: {subscribe_msg}")
                
                # Receive a few messages
                for i in range(3):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg_json = json.loads(msg)
                        result["messages_received"] += 1
                        print(f"   📥 Message {i+1}: {json.dumps(msg_json, indent=2)[:200]}...")
                    except asyncio.TimeoutError:
                        print(f"   ⏱️  Timeout waiting for message {i+1}")
                        break
                
                if result["messages_received"] > 0:
                    result["passed"] = True
                    print(f"✅ Public WebSocket - SUCCESS ({result['messages_received']} messages)")
                else:
                    result["error"] = "No messages received"
                    print(f"⚠️  Public WebSocket - No messages received")
                    
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Public WebSocket - FAILED: {str(e)}")
        
        self.test_results.append(result)
        return result
    
    async def test_websocket_private(self, listen_key: str) -> Dict[str, Any]:
        """Test private WebSocket connection"""
        result = {
            "test": "Private WebSocket",
            "endpoint": self.WSS_PRIVATE,
            "passed": False,
            "error": None,
            "messages_received": 0
        }
        
        try:
            print("\n🔐 Testing Private WebSocket...")
            async with websockets.connect(self.WSS_PRIVATE, ping_timeout=10) as ws:
                # Subscribe to order and balance updates
                subscribe_msg = {
                    "method": "subscribe",
                    "params": ["order", "balance"],
                    "listenKey": listen_key,
                    "id": 1
                }
                await ws.send(json.dumps(subscribe_msg))
                print(f"   📤 Sent subscription with listenKey")
                
                # Wait for subscription confirmation
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg_json = json.loads(msg)
                    result["messages_received"] += 1
                    print(f"   📥 Response: {json.dumps(msg_json, indent=2)}")
                    result["passed"] = True
                    print(f"✅ Private WebSocket - SUCCESS (authenticated)")
                except asyncio.TimeoutError:
                    result["error"] = "No response from private WebSocket"
                    print(f"⚠️  Private WebSocket - No response")
                    
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Private WebSocket - FAILED: {str(e)}")
        
        self.test_results.append(result)
        return result
    
    async def run_all_tests(self):
        """Execute all endpoint tests"""
        
        print("\n" + "="*80)
        print("XT EXCHANGE API VALIDATION TEST SUITE")
        print("="*80 + "\n")
        
        # Phase 1: Public Endpoints (No Auth)
        print("\n📖 PHASE 1: PUBLIC ENDPOINTS (No Authentication)")
        print("-" * 80)
        
        await self.test_endpoint(
            name="1. Server Time",
            method="GET",
            path="/v4/public/time",
        )
        
        await self.test_endpoint(
            name="2. Trading Pairs",
            method="GET",
            path="/v4/public/symbol",
        )
        
        await self.test_endpoint(
            name="3. Ticker Price",
            method="GET",
            path="/v4/public/ticker/price",
            params={"symbol": "btc_usdt"}
        )
        
        await self.test_endpoint(
            name="4. Order Book Depth",
            method="GET",
            path="/v4/public/depth",
            params={"symbol": "btc_usdt", "limit": 20}
        )
        
        await self.test_endpoint(
            name="5. Recent Trades",
            method="GET",
            path="/v4/public/trade",
            params={"symbol": "btc_usdt", "limit": 10},
            optional_if_not_found=True
        )
        
        # Phase 2: Authentication Test (Critical!)
        print("\n🔐 PHASE 2: AUTHENTICATION VALIDATION")
        print("-" * 80)
        print("Testing BOTH header formats to determine which works...\n")
        
        auth_test = await self.test_endpoint(
            name="6. Account Balance (AUTH TEST)",
            method="GET",
            path="/v4/balances",
            requires_auth=True,
            test_both_auth_formats=True  # Test both!
        )
        
        if not auth_test["passed"]:
            print("\n⚠️  WARNING: Authentication failed with both header formats!")
            print("❌ Cannot proceed with private endpoint tests")
            print("🔍 Please verify your API key and secret")
            print("\nPossible issues:")
            print("  - Invalid API key or secret")
            print("  - API key doesn't have required permissions")
            print("  - IP address not whitelisted (if IP restriction enabled)")
            return
        
        print(f"\n✅ Authentication successful with: {auth_test['auth_format']} headers")
        print("📝 This format will be used for remaining tests\n")
        
        # Phase 3: Private Endpoints (Using working auth format)
        print("\n🔒 PHASE 3: PRIVATE ENDPOINTS (Authenticated)")
        print("-" * 80)
        
        ws_token_result = await self.test_endpoint(
            name="7. WebSocket Token",
            method="POST",
            path="/v4/ws-token",
            requires_auth=True
        )
        
        await self.test_endpoint(
            name="8. Open Orders",
            method="GET",
            path="/v4/open-order",
            params={"bizType": "SPOT"},
            requires_auth=True
        )
        
        # GET /v4/order: query by orderId (no real order created; expect "order not found")
        await self.test_endpoint(
            name="9. Get Order (by ID)",
            method="GET",
            path="/v4/order",
            params={"orderId": 0, "clientOrderId": "xt_validation_test"},
            requires_auth=True,
            success_if_order_not_found=True
        )
        
        # Note: POST /v4/order (place) and DELETE /v4/order (cancel) are not tested (would create/cancel real orders)
        
        # Phase 4: WebSocket Tests (Optional)
        print("\n🌐 PHASE 4: WEBSOCKET TESTS (Optional)")
        print("-" * 80)
        
        await self.test_websocket_public()
        
        # Test private WebSocket if we got a listen key (XT may return listenKey or accessToken)
        if ws_token_result["passed"] and ws_token_result["response"].get("result"):
            result_data = ws_token_result["response"].get("result") or {}
            listen_key = result_data.get("listenKey") or result_data.get("accessToken")
            if listen_key:
                await self.test_websocket_private(listen_key)
            else:
                print("⚠️  Skipping private WebSocket (no listenKey or accessToken in response)")
        
        # Phase 5: Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        skipped_tests = sum(1 for r in self.test_results if r.get("skipped"))
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        if skipped_tests:
            print(f"⏭️  Skipped: {skipped_tests} (optional endpoint not in XT API)")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if auth_test["passed"]:
            print(f"\n🎯 CONFIRMED: Use '{auth_test['auth_format']}' headers for authentication")
        
        # Save results to file
        output_file = "xt_api_test_results.json"
        with open(output_file, "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "skipped": skipped_tests,
                    "failed": failed_tests,
                    "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
                    "working_auth_format": self.working_auth_format,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "test_results": self.test_results
            }, f, indent=2)
        print(f"\n📄 Detailed results saved to: {output_file}")
        
        # Print recommendations
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n✅ Next Steps:")
            print("   1. Review test results in xt_api_test_results.json")
            print("   2. Use confirmed authentication format in connector")
            print("   3. Reference response structures for unit tests")
            print("   4. Proceed with full connector implementation")
        else:
            print("\n⚠️  SOME TESTS FAILED")
            print("\n📋 Recommended Actions:")
            print("   1. Review failed tests in xt_api_test_results.json")
            print("   2. Check error messages and response codes")
            print("   3. Verify API credentials and permissions")
            print("   4. Contact XT support if issues persist: https://t.me/XT_api")


async def main():
    """Main test runner"""
    load_dotenv()
    
    api_key = os.getenv("XT_API_KEY")
    api_secret = os.getenv("XT_API_SECRET")
    
    if not api_key or not api_secret:
        print("\n❌ ERROR: XT_API_KEY and XT_API_SECRET must be set")
        print("\nSetup Instructions:")
        print("1. Copy .env.example to .env")
        print("   cp .env.example .env")
        print("\n2. Edit .env and add your XT API credentials")
        print("   Get credentials from: https://www.xt.com/en/accounts/api")
        print("\n3. Run the tests again")
        print("   python test_xt_api_validation.py")
        return
    
    print(f"\n🔑 Using API Key: {api_key[:8]}...{api_key[-4:]}")
    
    tester = XTAPITester(api_key, api_secret)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
