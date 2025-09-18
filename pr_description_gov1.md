## GOV-1: Repo & CI Governance Tightenings

This pull request implements key governance controls to make the registry system unfakeable and secure. It introduces restrictive CI permissions, a stable version pointer, a changelog, a standardized PR template, and code ownership for critical files.

### Implementation Details

- **CI Workflow (`.github/workflows/registry-validation.yml`):**
    - Added a `permissions` block to restrict token scope (`contents: read`, `pull-requests: read`).
    - Added `workflow_dispatch` and `schedule` triggers to run validation manually and nightly.

- **Registry Versioning:**
    - `contracts/registry/current.version`: A new file containing `v1` to serve as a stable pointer.
    - `contracts/registry/CHANGELOG.md`: A new keys-only changelog seeded with the v1 entry.

- **Standardized Templates:**
    - `.github/pull_request_template.md`: A new template with checkboxes for Privacy, Security, Rollback, and Contracts.

- **Code Ownership:**
    - `.github/CODEOWNERS`: A new file requiring review from `nathanamthor@gmail.com` for any changes to `contracts/registry/*` and the validation workflow.

### Acceptance Criteria Met

- **CI/Repo Artifacts:** All specified files have been created or modified as per the card's scope.
- **LOC Tally:** The total lines of code for this change is **~37 LOC**, well within the budget.
- **Single-Commit Rollback:** The entire change can be reverted with a single `git revert`.

### Rollback Plan

```
git revert <commit-hash>
```

