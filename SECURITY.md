# Security Policy

> **Adaptive Cyber-Immunity Framework** — Dependabot is enabled on this
> repository with grouped, labeled, reviewer-routed version updates. Known
> vulnerable versions are patched immediately by GitHub, outside any schedule.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < latest | :x:                |

## Dependabot Adaptive Security Configuration

This repository ships `.github/dependabot.yml` encoding the
**Detect → Analyse → Validate → Respond → Record → Update → Learn → Adapt**
workflow:

- **Detect** — weekly scheduled scans of every dependency ecosystem present
  (npm / pip / composer / gomod / docker / GitHub Actions).
- **Analyse** — grouped, typed updates so related dependencies move together;
  production major/minor-patch and development batches are separated.
- **Validate** — every change lands as a distinct, reviewable PR (never
  auto-merged); CI must be green before merge.
- **Respond** — `karun99` is the reviewer/assignee; `dependencies`,
  `security`, `automated` labels route each PR.
- **Record** — `deps:` prefixed commit messages plus labels form a searchable
  audit trail.
- **Adapt** — weekly cadence keeps the dependency surface continuously fresh.

### Incident Response Mechanism

| Severity  | CVSS        | Triage    | Remediation SLA | Action                                            |
| --------- | ----------- | --------- | --------------- | ------------------------------------------------- |
| Critical  | 9.0–10.0    | 24 hours  | 48 hours        | Patch immediately, pin exact fix, hotfix redeploy |
| High      | 7.0–8.9     | 24 hours  | 7 days          | Patch in next release; document workaround        |
| Medium    | 4.0–6.9     | 48 hours  | 30 days         | Patch in next scheduled release                   |
| Low       | 0.1–3.9     | 7 days    | 90 days         | Schedule with regular maintenance                 |

1. Dependabot opens a PR for the vulnerable dependency.
2. CI runs the test suite against the updated dependency — the PR must pass
   all checks.
3. A maintainer reviews the diff (changelog, breaking changes, licenses).
4. Merged PRs are deployed per the documented release process.
5. The alert is automatically closed once the fixed version is merged.

## Reporting a Vulnerability

Use the GitHub private security advisory feature:

1. Open the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Provide a description, affected dependency/version, and proof-of-concept.

**Expected acknowledgment:** within 3 business days. Reports are kept
confidential and are only shared with maintainers. Credit is given in release
notes unless anonymity is requested.

## Dependency Hygiene

- Direct dependencies are pinned or semver-locked in manifests
  (`package.json`, `requirements.txt`, `pyproject.toml`, etc.).
- Lockfiles are kept in-repo for reproducible builds.
- PRs that introduce known-vulnerable packages are blocked by Dependabot and CI.
- Deprecated or unmaintained packages are migrated at least twice a year.