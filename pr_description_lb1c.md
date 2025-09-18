## LB-1c: Writer Validator Fix (Denylist & Status Codes)

This pull request fixes the critical security flaw in the writer minimalism validator (`tools/contracts_validate_writers.js`). The validator now correctly enforces the denylist regardless of headers and tightens the rules for 200, 201, and 204 status codes.

### Implementation Details

- **Authoritative Body Detection:** The validator now uses `body && Object.keys(body).length > 0` to determine if a body is present, ignoring `Content-Length` headers.
- **Stricter Status Code Rules:**
    - **204:** Must have an empty body.
    - **201:** Must have an empty body and a `Location` header.
    - **200:** Must have a body of exactly `{"status":"ok"}` with no extra keys.
- **Recursive Denylist Enforcement:** The validator now correctly identifies forbidden keys (`user`, `profile`, `auth`, etc.) in the response body, even when nested.
- **Keys-Only Error Messages:** All error messages are keys-only and do not contain any values from the fixture files.

### Acceptance Criteria Met

- **A1 (Happy Path):** The validator passes all existing valid fixtures.
- **A2 (Denylist Violation):** The validator correctly fails a fixture with a denylisted key (`data.user`) even when `Content-Length` is `0`.
- **A3 (200 Extras):** The validator correctly fails a 200 response with extra keys in the body.
- **A4 (201 Missing Location):** The validator correctly fails a 201 response without a `Location` header.
- **LOC Tally:** The change is approximately **45 lines of code**.
- **Single-Commit Rollback:** The change can be reverted with a single `git revert`.

### Artifacts

**Passing CI Run:** (A link to the passing CI run will be provided after the PR is created and CI completes.)

**Negative Keys-Only Error Output:**

```
# A2 - Denylist Violation
Forbidden key found at: data.user

# A3 - 200 with Extra Keys
200 writer must be {"status":"ok"} (found keys: extra)

# A4 - 201 without Location Header
201 writer requires Location header
```

### Rollback Plan

```
git revert <commit-hash>
```
```

