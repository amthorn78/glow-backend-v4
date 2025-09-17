# Configuration Baseline (S7-FSR)

This document outlines the recommended non-secret environment variables for production to maintain the security posture of the GLOW Intelligence App.

## Rate Limiting

These variables control the login rate limiter. The defaults are recommended for production.

- `LOGIN_RATELIMIT_ENABLED=1`
  - **Description**: Enables or disables the login rate limiter.
  - **Recommended Value**: `1` (enabled)

- `LOGIN_RATELIMIT_MAX_FAILS=5`
  - **Description**: The number of failed login attempts before rate limiting is triggered.
  - **Recommended Value**: `5`

- `LOGIN_RATELIMIT_WINDOW_SEC=60`
  - **Description**: The time window in seconds for tracking failed attempts.
  - **Recommended Value**: `60`

## Telemetry

This variable controls the CSRF telemetry feature. It should be disabled by default for privacy and performance.

- `NEXT_PUBLIC_GLOW_TELEMETRY_CSRF=0`
  - **Description**: Enables or disables the CSRF telemetry feature.
  - **Recommended Value**: `0` (disabled)

## General

- `FLASK_ENV=production`
  - **Description**: Sets the Flask environment to production.
  - **Recommended Value**: `production`

- `SESSION_TYPE=redis`
  - **Description**: Configures server-side sessions to use Redis.
  - **Recommended Value**: `redis`

