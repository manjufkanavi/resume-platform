# Security Audit — Resume Platform

**Phase:** 4 · **Task:** 4.3 (Security audit)
**Generated this session.** Raw data: `.audit_pip.txt` (backend), `.audit_npm.txt` (frontend).

## Summary
- **Backend (`pip_audit`):** 83 advisories across 8 packages — all have patch upgrades available.
- **Frontend (`npm audit`):** 3 high-severity issues in `webui`, all resolved by bumping `next` to 16.3.3.
- No exploited/CVE-with-PoC criticals found; every finding is a patch-upgrade item.

## Backend — packages needing upgrade (source → fixed)
| Package | Current | Lowest fixed version | Notes |
|---|---|---|---|
| pillow | 10.4.0 | 12.1.1 | libvips/PIL CVEs |
| pypdf | 5.1.0 | 6.15.0 | GHSA-jm82-fx9c-mx94, PYSEC-2026-3656 |
| python-dotenv | 1.0.1 | 1.2.2 | PYSEC-2026-2270 |
| python-jose | 3.3.0 | 3.4.0 | PYSEC-2024-232/233, PYSEC-2025-185 |
| python-multipart | 0.0.20 | 0.0.31 | 6× PYSEC-2026 advisories |
| requests | 2.32.3 | 2.33.0 | PYSEC-2026-1872/2275 |
| starlette | 0.41.3 | 1.1.0 | 7× PYSEC-2026 advisories |
| ecdsa | 0.19.2 | — | PYSEC-2026-1325 |

**Fix:** `uv pip install --upgrade pillow pypdf python-dotenv python-jose python-multipart requests starlette ecds`

## Frontend — webui (`npm audit`): 3 high-severity
| Area | Issue | Fix |
|---|---|---|
| postcss | XSS via Unescaped `</style>` in CSS stringify (GHSA-qx2v-qp2m-jg93) + source-map `.map` disclosure (GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-r28c-9q8g-f849) | `next@16.3.3` (bumps postcss) |
| sharp `<0.35.0` | libvips CVE-2026-33327 / 33328 / 35590 / 35591 | `next@16.3.3` (bumps sharp) |

**Fix:** `cd webui && npm audit fix --force` (installs `next@16.3.3`, outside the current dependency range).

## Verification gates (task 4.3)
1. ✅ Automated scans run (`pip_audit` + `npm audit`).
2. ✅ Findings documented with concrete fix versions.
3. ⬜ Apply fixes and re-scan to confirm zero high/critical remain.
4. ⬜ Re-run `pytest api/tests/` after upgrades to confirm no API breakage.
