import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

# Known scraper, automated vulnerability scanner, and hostile bot signatures
BLOCKED_USER_AGENTS = [
    "sqlmap", "nikto", "nmap", "masscan", "zgrab", "gobuster",
    "dirbuster", "wpscan", "havij", "acunetix", "netsparker",
    "nessus", "metasploit", "python-urllib", "scrapy", "mechanize",
    "libwww-perl", "autoit", "morfeus", "zmeu", "babygrid"
]

class InMemoryRateLimiter:
    """
    Sliding window per-IP rate limiter to protect against bot DDoS and rapid scraping.
    """
    def __init__(self, window_seconds: int = 60, max_requests: int = 60, max_post_requests: int = 15):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.max_post_requests = max_post_requests
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.post_requests: Dict[str, List[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup(self, now: float):
        if now - self.last_cleanup > 300: # Clean up every 5 minutes
            cutoff = now - self.window_seconds
            for ip in list(self.requests.keys()):
                self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
                if not self.requests[ip]:
                    del self.requests[ip]
            for ip in list(self.post_requests.keys()):
                self.post_requests[ip] = [t for t in self.post_requests[ip] if t > cutoff]
                if not self.post_requests[ip]:
                    del self.post_requests[ip]
            self.last_cleanup = now

    def check_rate_limit(self, ip: str, method: str) -> Optional[JSONResponse]:
        now = time.time()
        self._cleanup(now)
        cutoff = now - self.window_seconds

        # Clean old timestamps for this IP
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        self.post_requests[ip] = [t for t in self.post_requests[ip] if t > cutoff]

        # Check total requests
        if len(self.requests[ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": "Too many requests from this client. MediSync anti-bot protection triggered.",
                    "retry_after_seconds": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )

        # Stricter limit on POST/mutations (upload, book appointment)
        if method.upper() in ["POST", "PUT", "DELETE"]:
            if len(self.post_requests[ip]) >= self.max_post_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Submission rate limit exceeded",
                        "detail": "Form submission rate limit exceeded. Anti-spam bot protection triggered.",
                        "retry_after_seconds": self.window_seconds
                    },
                    headers={"Retry-After": str(self.window_seconds)}
                )
            self.post_requests[ip].append(now)

        self.requests[ip].append(now)
        return None

rate_limiter = InMemoryRateLimiter()

def inspect_request_for_bots(request: Request) -> Optional[JSONResponse]:
    """
    Validates request against known malicious bot signatures, headers, and rate limits.
    """
    # 1. Extract IP
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    # 2. Check User-Agent
    user_agent = (request.headers.get("user-agent") or "").lower()
    
    # Missing or empty User-Agent on write requests is typical of simple bot scripts
    if request.method in ["POST", "PUT", "DELETE"] and not user_agent:
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "detail": "Invalid or missing User-Agent header (Bot detected)."}
        )

    # Check for known hostile bot signatures
    for bad_ua in BLOCKED_USER_AGENTS:
        if bad_ua in user_agent:
            return JSONResponse(
                status_code=403,
                content={"error": "Access Denied", "detail": f"Automated bot signature identified ({bad_ua}). Access blocked."}
            )

    # 3. Rate limiting check
    limit_resp = rate_limiter.check_rate_limit(client_ip, request.method)
    if limit_resp:
        return limit_resp

    return None

def verify_honeypot(trap_value: Optional[str]):
    """
    Honeypot verification: Legitimate human users will leave hidden trap fields empty.
    Automated web spambots fill all input elements.
    """
    if trap_value and trap_value.strip():
        raise HTTPException(
            status_code=400,
            detail="Automated bot submission detected via honeypot trap."
        )

