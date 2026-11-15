import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.security import inspect_request_for_bots, verify_honeypot, rate_limiter
from fastapi import Request, HTTPException

class DummyRequest:
    def __init__(self, method="GET", path="/api/reports", headers=None, client_ip="127.0.0.1"):
        self.method = method
        self.url = path
        self.headers = headers or {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        self.client = type("Client", (), {"host": client_ip})()

def run_security_tests():
    print("--- Running MediSync Anti-Bot & Security Defenses Verification ---")

    # 1. Test Malicious Bot User-Agent Detection
    for bad_ua in ["sqlmap/1.5", "nikto/2.1.6", "masscan/1.0", "wpscan v3.8"]:
        req = DummyRequest(headers={"user-agent": bad_ua})
        blocked_resp = inspect_request_for_bots(req)
        assert blocked_resp is not None, f"Expected {bad_ua} to be blocked!"
        assert blocked_resp.status_code == 403, f"Expected 403 Forbidden for {bad_ua}"
        print(f"[OK] Malicious Bot '{bad_ua}' successfully blocked with HTTP 403")

    # 2. Test Legitimate Human Request Allowed
    good_req = DummyRequest(headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    good_resp = inspect_request_for_bots(good_req)
    assert good_resp is None, "Legitimate browser request should not be blocked!"
    print("[OK] Legitimate human browser traffic allowed through")

    # 3. Test Honeypot Trap Detection
    caught = False
    try:
        verify_honeypot("spam_bot_input_123")
    except HTTPException as e:
        caught = True
        assert e.status_code == 400
    assert caught, "Honeypot trap must detect automated form bots!"
    print("[OK] Honeypot form trap caught automated spambot (HTTP 400)")

    # Legitimate user leaves honeypot empty
    verify_honeypot(None)
    verify_honeypot("")
    print("[OK] Legitimate empty honeypot field passes cleanly")

    # 4. Test Rate Limiter
    test_ip = "192.168.1.99"
    # Flood requests to trigger limit
    triggered = False
    for i in range(70):
        resp = rate_limiter.check_rate_limit(test_ip, "GET")
        if resp and resp.status_code == 429:
            triggered = True
            break
    assert triggered, "Rate limiter should trigger 429 when bot floods requests!"
    print("[OK] Anti-DDoS Rate Limiter triggered HTTP 429 Too Many Requests against rapid bot flood")

    # 5. Verify Gemini API Key Modal & Settings removed from frontend
    with open("backend/static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "openKeyModal" not in html_content, "openKeyModal must not be in index.html"
    assert "key-modal" not in html_content, "key-modal must not be in index.html"
    assert "modal-api-key-input" not in html_content, "modal-api-key-input must not be in index.html"
    print("[OK] Gemini API settings & key modal completely removed from HTML frontend")

    with open("backend/static/js/app.js", "r", encoding="utf-8") as f:
        js_content = f.read()
    assert "saveApiKey" not in js_content, "saveApiKey must not be in app.js"
    assert "checkApiStatus" not in js_content, "checkApiStatus must not be in app.js"
    print("[OK] Gemini API key configuration functions removed from client-side JS")

    print("\n==========================================================")
    print("ALL ANTI-BOT AND SECURITY SHIELD TESTS PASSED SUCCESSFULLY!")
    print("==========================================================")

if __name__ == "__main__":
    run_security_tests()

