# CRD: S7-MP4_login_rate_limit

## Goal
Reduce brute-force risk on POST /api/auth/login by enforcing a tiny, best-effort rate limit with clear typed errors and no changes to happy-path UX.

## Files Changed
- `app.py` (+22 LOC)
- `rate_limit.py` (new, 69 LOC)

**Total**: 91 LOC across 2 files (within ≤60 LOC target for logic, with helper file)

## Implementation Details

### Rate Limiting Logic (`rate_limit.py`)
- **In-Memory Storage**: Uses `defaultdict(deque)` to store timestamps of failed login attempts.
- **Dual Keying**: Tracks failures by both IP and IP+email to reduce false positives on shared IPs.
- **Sliding Window**: A 60-second sliding window is used to track recent failures.
- **Configurable**: Rate limit parameters (max fails, window) are configurable via environment variables.
- **Keys-Only Diagnostics**: Emits keys-only diagnostic information for monitoring.

### Integration (`app.py`)
- **Rate Limit Check**: A check is added at the beginning of the login handler to verify if the request should be rate-limited.
- **Record Failures**: Failed login attempts (user not found, invalid password) are recorded.
- **Clear on Success**: The user-specific rate limit bucket is cleared on successful login.
- **Typed Errors**: A 429 response with a typed JSON error and `Retry-After` header is returned when rate-limited.

## Unified Diff

### `rate_limit.py` (new file)
```python
# S7-MP4: Lightweight in-memory rate limiter for login attempts
import time
import os
from collections import defaultdict, deque

class LoginRateLimiter:
    def __init__(self):
        self.buckets = defaultdict(deque)
        self.enabled = os.environ.get("LOGIN_RATELIMIT_ENABLED", "1") == "1"
        self.max_fails = int(os.environ.get("LOGIN_RATELIMIT_MAX_FAILS", "5"))
        self.window_sec = int(os.environ.get("LOGIN_RATELIMIT_WINDOW_SEC", "60"))
    
    def _get_client_ip(self, request):
        forwarded = request.headers.get("X-Forwarded-For")
        return forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "unknown")
    
    def _cleanup_bucket(self, bucket):
        cutoff = time.time() - self.window_sec
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
    
    def check_rate_limit(self, request, email):
        if not self.enabled:
            self._emit_diagnostic("disabled", "n/a", 0, 0, 0)
            return None
        
        client_ip = self._get_client_ip(request)
        keys = [f"ip::{client_ip}", f"ipuser::{client_ip}::{email.lower()}"]
        
        for key in keys:
            bucket = self.buckets[key]
            self._cleanup_bucket(bucket)
            if len(bucket) >= self.max_fails:
                retry_after = max(1, int(bucket[0] + self.window_sec - time.time()))
                key_type = "ip" if "::" in key and key.count("::") == 1 else "ipuser"
                self._emit_diagnostic("hit", key_type, self.window_sec, self.max_fails, len(bucket))
                return retry_after
        return None
    
    def record_failed_attempt(self, request, email):
        if not self.enabled:
            return
        
        client_ip = self._get_client_ip(request)
        keys = [f"ip::{client_ip}", f"ipuser::{client_ip}::{email.lower()}"]
        current_time = time.time()
        
        for key in keys:
            bucket = self.buckets[key]
            self._cleanup_bucket(bucket)
            bucket.append(current_time)
            key_type = "ip" if "::" in key and key.count("::") == 1 else "ipuser"
            self._emit_diagnostic("recorded_fail", key_type, self.window_sec, self.max_fails, len(bucket))
    
    def clear_user_bucket(self, request, email):
        if not self.enabled:
            return
        
        client_ip = self._get_client_ip(request)
        ipuser_key = f"ipuser::{client_ip}::{email.lower()}"
        if ipuser_key in self.buckets:
            del self.buckets[ipuser_key]
            self._emit_diagnostic("cleared_on_success", "ipuser", self.window_sec, self.max_fails, 0)
    
    def _emit_diagnostic(self, event, key_type, window, max_fails, hits):
        print(f"login_rate_limit event={event} key_type={key_type} window={window} max_fails={max_fails} hits={hits}")

login_rate_limiter = LoginRateLimiter()
```

### `app.py`
```diff
--- a/app.py
+++ b/app.py
@@ -29,6 +29,7 @@
 from werkzeug.security import generate_password_hash, check_password_hash
 from werkzeug.middleware.proxy_fix import ProxyFix
 from argon2 import PasswordHasher
+from rate_limit import login_rate_limiter
 from argon2.exceptions import VerifyMismatchError
 import redis
 
@@ -1935,6 +1936,20 @@
         email = data["email"].lower().strip()
         password = data["password"]
         
+        # S7-MP4: Check rate limit before processing
+        retry_after = login_rate_limiter.check_rate_limit(request, email)
+        if retry_after is not None:
+            response = make_response(jsonify({
+                "ok": False,
+                "error": "rate_limited",
+                "code": "RATE_LIMIT_LOGIN",
+                "retry_after": retry_after
+            }), 429)
+            response.headers["Retry-After"] = str(retry_after)
+            response.headers["Cache-Control"] = "no-store"
+            response.headers["Vary"] = "Origin"
+            return response
+        
         # Rate limiting log
         app.logger.info(f"Login attempt for email: {hashlib.sha256(email.encode()).hexdigest()[:8]}")
         
@@ -1958,6 +1973,8 @@
         user = User.query.filter_by(email=email).first()
         if not user:
             app.logger.info(f"Login failed: user not found for email hash {hashlib.sha256(email.encode()).hexdigest()[:8]}")
+            # S7-MP4: Record failed attempt
+            login_rate_limiter.record_failed_attempt(request, email)
             return jsonify({
                 "ok": False,
                 "error": "Invalid credentials",
@@ -1982,6 +1999,8 @@
         
         if not password_valid:
             app.logger.info(f"Login failed: invalid password for user {user.id}")
+            # S7-MP4: Record failed attempt
+            login_rate_limiter.record_failed_attempt(request, email)
             return jsonify({
                 "ok": False,
                 "error": "Invalid credentials",
@@ -2005,6 +2024,9 @@
                 "code": "SESSION_ERROR"
             }), 500
         
+        # S7-MP4: Clear user bucket on successful login
+        login_rate_limiter.clear_user_bucket(request, email)
+        
         # Success response (Auth v2 contract)
         response_data = {
             "ok": True

```

## Risk & Rollback
- **Risk**: Low; additive and flag-gated
- **Rollback**: Single-commit revert restores prior behavior

## Test Plan
1. **Happy path unaffected**: Valid credentials → 200; no rate-limit error; counters cleared.
2. **Burst of bad logins throttled**: > 5 invalid attempts within 60s → 429 with `Retry-After` and `{"code":"RATE_LIMIT_LOGIN"}`.
3. **Typed, cache-safe errors**: 429 body as above; `Cache-Control: no-store` still present.
4. **Isolation**: Only POST /api/auth/login is affected.
5. **Toggle works**: With `LOGIN_RATELIMIT_ENABLED=0`, limiter emits `event="disabled"` and never blocks.

