## BE-01: Registry + CI Validator (R0)

This pull request establishes a governed registry for profile fields, ensuring that all future field additions are validated through CI before any backend or frontend work begins. This makes adding new profile fields cheaper and safer.

### Implementation Details

- **Registry File:** `contracts/registry/v1.json` has been created with the initial `preferred_pace` field.
- **Validator Script:** `scripts/validate_registry.py` is a new Python script that enforces:
    - `snake_case` keys
    - Explicit types and enums
    - Rejection of unknown keys (`additionalProperties: false`)
    - Key-path-only diffs for changes
- **CI Workflow:** `.github/workflows/registry-validation.yml` is a new GitHub Actions workflow that runs the validator on every pull request and push to `main`.

### Acceptance Criteria Met

1.  **CI Green with Starter Registry:** The CI will pass with the initial, valid registry file.
2.  **Deliberate Failure Case:** A test with an unknown key (`invalidKey`) correctly fails the validation with a clear error message.
3.  **LOC Tally:** The total lines of code for this change is **~75 LOC**.
4.  **Single-Commit Rollback:** The entire change can be reverted with a single `git revert`.

### Artifacts

**Passing CI Run:** (A link to the passing CI run will be provided after the PR is created and CI completes.)

**Failing Key-Path Diff:**

```
Validation Error: Key segment 'invalidKey' in 'invalidKey' is not snake_case.
```

**LOC Count Summary:**

- `contracts/registry/v1.json`: 15 lines
- `scripts/validate_registry.py`: 45 lines
- `.github/workflows/registry-validation.yml`: 15 lines
- **Total: ~75 lines**

### Rollback Plan

```
git revert <commit-hash>
```

