# S7-MP4: Lightweight in-memory rate limiter for login attempts
import time
import os
from collections import defaultdict, deque

class LoginRateLimiter:
    def __init__(self):
        self.buckets = defaultdict(deque)
        self.enabled = os.environ.get('LOGIN_RATELIMIT_ENABLED', '1') == '1'
        self.max_fails = int(os.environ.get('LOGIN_RATELIMIT_MAX_FAILS', '5'))
        self.window_sec = int(os.environ.get('LOGIN_RATELIMIT_WINDOW_SEC', '60'))
    
    def _get_client_ip(self, request):
        forwarded = request.headers.get('X-Forwarded-For')
        return forwarded.split(',')[0].strip() if forwarded else (request.remote_addr or 'unknown')
    
    def _cleanup_bucket(self, bucket):
        cutoff = time.time() - self.window_sec
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
    
    def check_rate_limit(self, request, email):
        if not self.enabled:
            self._emit_diagnostic('disabled', 'n/a', 0, 0, 0)
            return None
        
        client_ip = self._get_client_ip(request)
        keys = [f"ip::{client_ip}", f"ipuser::{client_ip}::{email.lower()}"]
        
        for key in keys:
            bucket = self.buckets[key]
            self._cleanup_bucket(bucket)
            if len(bucket) >= self.max_fails:
                retry_after = max(1, int(bucket[0] + self.window_sec - time.time()))
                key_type = 'ip' if '::' in key and key.count('::') == 1 else 'ipuser'
                self._emit_diagnostic('hit', key_type, self.window_sec, self.max_fails, len(bucket))
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
            key_type = 'ip' if '::' in key and key.count('::') == 1 else 'ipuser'
            self._emit_diagnostic('recorded_fail', key_type, self.window_sec, self.max_fails, len(bucket))
    
    def clear_user_bucket(self, request, email):
        if not self.enabled:
            return
        
        client_ip = self._get_client_ip(request)
        ipuser_key = f"ipuser::{client_ip}::{email.lower()}"
        if ipuser_key in self.buckets:
            del self.buckets[ipuser_key]
            self._emit_diagnostic('cleared_on_success', 'ipuser', self.window_sec, self.max_fails, 0)
    
    def _emit_diagnostic(self, event, key_type, window, max_fails, hits):
        print(f"login_rate_limit event={event} key_type={key_type} window={window} max_fails={max_fails} hits={hits}")

login_rate_limiter = LoginRateLimiter()

