## BE-NEG-01: Add Negative Writer Fixture Smoke Test

This pull request adds a new, opt-in CLI smoke test (`pnpm writers:violation:smoke`) to prove that the writer-minimalism validator correctly fails on a deliberate violation and then passes after cleanup. This provides a crucial confidence check for the validator's effectiveness.

### Implementation Details

- **New Script (`tools/writers_violation_smoke.js`):**
    - Creates a temporary violation fixture at `tests/fixtures/writers/_tmp_violation.json`.
    - Runs the existing validator (`pnpm contracts:validate-writers`), expecting it to fail with a clear keys-only message.
    - Deletes the temporary fixture.
    - Re-runs the validator, expecting it to pass.
    - Prints concise PASS/FAIL lines suitable for CI logs.

- **New Package Script:**
    - Added `"writers:violation:smoke": "node tools/writers_violation_smoke.js"` to `package.json`.

### Acceptance Criteria Met

- **Expected Failure:** The script correctly identifies the validator's failure when the violation fixture is present.
- **Cleanup and Pass:** The script successfully cleans up the temporary fixture and confirms that the validator passes on the clean set of fixtures.
- **No Leftovers:** The script ensures that `_tmp_violation.json` is removed on both success and failure.
- **LOC Tally:** The change is approximately **45 lines of code**.
- **Single-Commit Rollback:** The change can be reverted with a single `git revert`.

### Artifacts

**Terminal Output:**

```
--- Running Writer Validator Negative Smoke Test ---

[1/4] Creating temporary violation fixture...
Fixture created.

[2/4] Running validator (expecting failure)...

> Running: pnpm contracts:validate-writers
...
❌ /api/_tmp_violation (from _tmp_violation.json):
    - 200 writer must be {"status":"ok"} (found keys: data)
    - Forbidden key found at: data
...
❌ Writer minimalism violations detected

✅ PASS: Validator failed as expected.

[3/4] Cleaning up temporary fixture...
Fixture deleted.

[4/4] Re-running validator (expecting success)...

> Running: pnpm contracts:validate-writers
...
✅ All writers conform to minimalism rules

✅ PASS: Validator succeeded on cleanup run.

--- Test Complete ---
```

### Rollback Plan

```
git revert <commit-hash>
```

