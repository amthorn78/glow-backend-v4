# Security Gaps & Next 90-Day Backlog (S7-FSR)

This document outlines the prioritized security backlog for the next 90 days, based on the S7-FSR security snapshot.

## Prioritized Backlog

### P0 - Critical
*(None at this time)*

### P1 - High

**1. Content-Security-Policy (CSP) Header**
- **Gap**: No CSP header is currently in place, increasing the risk of XSS attacks.
- **Proposed Fix**: Implement a strict CSP in report-only mode first, then enforce it.
- **Micro-gate Spec**: `S8-MP1_csp_header`
  - **Goal**: Add a `Content-Security-Policy` header to all responses.
  - **Scope**: 1 file, `app.py` (+10 LOC)
  - **Implementation**: Start with a strict policy in `Content-Security-Policy-Report-Only` mode.

**2. Rate Limit Persistence**
- **Gap**: The current login rate limiter is in-memory and node-local, which is not effective in a multi-replica environment.
- **Proposed Fix**: Use Redis to store rate limit data.
- **Micro-gate Spec**: `S8-MP2_redis_rate_limit`
  - **Goal**: Migrate rate limit storage from in-memory to Redis.
  - **Scope**: 1 file, `rate_limit.py` (+20 LOC)
  - **Implementation**: Use a Redis client to store and retrieve rate limit timestamps.

### P2 - Medium

**3. Dependency Scanning**
- **Gap**: No automated dependency scanning is in place, increasing the risk of using vulnerable packages.
- **Proposed Fix**: Integrate Dependabot or Snyk into the CI/CD pipeline.
- **Micro-gate Spec**: `S8-MP3_dependency_scanning`
  - **Goal**: Add automated dependency scanning to the CI/CD pipeline.
  - **Scope**: CI configuration file (+30 LOC)
  - **Implementation**: Add a new job to the GitHub Actions workflow to run `snyk test` or `dependabot`.

**4. Secrets Hygiene**
- **Gap**: No formal process for rotating secrets and credentials.
- **Proposed Fix**: Establish a quarterly rotation schedule for all secrets and enforce non-default credentials.
- **Micro-gate Spec**: `S8-MP4_secrets_rotation`
  - **Goal**: Document and automate the secrets rotation process.
  - **Scope**: Documentation only

**5. Audit Logging Review**
- **Gap**: No formal review process for audit logs to ensure no PII is being accidentally logged.
- **Proposed Fix**: Establish a monthly review of audit logs.
- **Micro-gate Spec**: `S8-MP5_audit_log_review`
  - **Goal**: Document and automate the audit log review process.
  - **Scope**: Documentation only

### P3 - Low

**6. Two-Factor Authentication (2FA) for Admin Accounts**
- **Gap**: Admin accounts are not protected by 2FA.
- **Proposed Fix**: Implement 2FA for all admin accounts.
- **Micro-gate Spec**: `S9-MP1_admin_2fa`
  - **Goal**: Add 2FA for admin accounts.
  - **Scope**: `app.py` (+50 LOC), frontend changes

**7. Permissions-Policy Header**
- **Gap**: No `Permissions-Policy` header is in place, which can help to further restrict browser features.
- **Proposed Fix**: Add a `Permissions-Policy` header to all responses.
- **Micro-gate Spec**: `S9-MP2_permissions_policy`
  - **Goal**: Add a `Permissions-Policy` header to all responses.
  - **Scope**: 1 file, `app.py` (+5 LOC)


