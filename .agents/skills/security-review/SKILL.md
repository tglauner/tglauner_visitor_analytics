---
name: security-review
description: Review changes for secret exposure, dangerous file access, auth weaknesses, admin-surface exposure, permission issues, and deployment-time security regressions.
---

# Security Review

Use this skill when the task touches credentials, admin surfaces, deployment configs, file access, auth, or permission boundaries.

## Review Checklist

1. Check whether `.env`, `confidential/`, secrets folders, credential exports, keys, or certificates are exposed.
2. Check whether logs, errors, or user-facing responses could leak secrets or local-only paths.
3. Check whether admin features are protected by authentication or strong shared secrets.
4. Check whether new shell commands or automation broaden risk unnecessarily.
5. Check whether deployment configs keep secrets on the server and out of git.

## Output

Summarize concrete findings first, ordered by severity. For each finding, identify the narrowest safe fix.
