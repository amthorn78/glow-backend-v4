## hotfix(app): remove stray text after 500; fix boot SyntaxError

This pull request resolves the critical `SyntaxError` in `app.py` that was preventing the application from booting. A stray line of code was appended to a `return` statement, causing a fatal error during Python parsing.

### The Fix

- **File:** `app.py`
- **Change:** Removed the extraneous text `serPreferences.query.filter_by(user_id=g.user).first()` that was appended to a `return jsonify({"error": "server_error"}), 500` line.

### Acceptance Criteria Met

- **Surgical Fix:** The change is a single-line edit to remove the syntax error.
- **LOC Tally:** 1 line of code.
- **Single-Commit Rollback:** The change can be reverted with a single `git revert`.

### Next Steps

- **Deploy:** This commit will be pushed to `main` to trigger a new deployment on Railway.
- **Validate Boot:** The Railway deploy logs will be monitored to confirm the application boots successfully.
- **Test Round-Trip:** The `PUT /api/profile/preferences` and `GET /api/auth/me` endpoints will be tested to confirm the preferences round-trip now works as expected.

### Rollback Plan

```
git revert <commit-hash>
```
```
