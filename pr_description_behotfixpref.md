## BE-HOTFIX-PREF: Preferences Round-Trip & Minimal Writer

This pull request fixes the critical bug where `PUT /api/profile/preferences` was not persisting the `preferred_pace` value. The handler has been rewritten to correctly save the preference to the database and return a lake-compliant response.

### Implementation Details

- **Persistence:** The `preferred_pace` value is now correctly saved to the `user_preferences.prefs` JSONB field.
- **Writer Response:** The endpoint now returns a `200 OK` with `{"status":"ok"}` and `Cache-Control: no-store`, which is a lake-compliant minimal writer response.
- **Reader Composition:** The `/api/auth/me` endpoint now correctly reads the `preferred_pace` value from the same persistence path, ensuring a successful write-read round-trip. It also defaults to `"medium"` if the preference is not set.
- **Validation:** The handler continues to validate the `preferred_pace` value against the allowed enum (`["slow","medium","fast"]`) and returns a `400` on bad values.
- **Security:** CSRF and authentication requirements are unchanged.

### Acceptance Criteria Met

- **Round-Trip Success:** Writing `"medium"` to `PUT /api/profile/preferences` is now correctly reflected in the subsequent `GET /api/auth/me` response.
- **Lake Compliance:** The writer returns a minimal `200 OK` with `{"status":"ok"}` and `Cache-Control: no-store`.
- **Negative Cases:** The endpoint correctly returns `400` for bad enum values and `403` for missing CSRF tokens.
- **LOC Tally:** The change is approximately **25 lines of code**.
- **Single-Commit Rollback:** The change can be reverted with a single `git revert`.

### Artifacts

**CLI Transcript:**

```
== PUT medium ==
PUT status: 200

Read pace: medium

✅ BE-HOTFIX-PREF acceptance passed.
```

**CI Guards:** Both the drift guard and writer minimalism guard remain green.

### Rollback Plan

```
git revert <commit-hash>
```

