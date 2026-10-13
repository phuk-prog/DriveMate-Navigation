# Public project: no personal data

**Strict policy:** this is a public GitHub repository. No user, driver or device personal data is permitted in commits, issues, pull requests, release artifacts, workflow logs or reference fixtures.

## Allowed

- Hand-created **synthetic** road networks with explicit synthetic classification.
- Independently selected, generally available public highway geometry from properly licensed open data, only after legal/provenance review. Public-road coordinates alone are not a person's GPS history.
- Open-source routing implementation and test code reviewed for redistribution rights.
- Aggregated performance numbers from controlled **non-personal** tests, with full methodology and limitations.

## Never upload

- Actual journey origin/destination, journey history, raw GPS fixes, routes from someone's usage, home/work positions, location timestamps or private place lists.
- Private DriveMate repository code, log bundles, cloud backups, vehicle information, phone IDs, photos, videos, screenshots, Bluetooth/device data, accounts or tokens.
- Commercial provider route datasets, imagery, audio or other outputs without explicit distribution rights.

## Protections

1. `.gitignore` blocks common sensitive file extensions and folder names.
2. `tools/privacy_guard.py` scans all **tracked** repository files for suspicious paths, tokens, emails and location-recording formats. The GitHub workflow runs it on each push/PR.
3. Benchmark adapters deliberately return aggregate distance and duration **only**. They do not expose route geometry or GPS coordinates.
4. Large real OSM datasets are kept outside Git and are never downloaded or uploaded by automatic CI.
5. A human must review any new external data and any code that transmits data.

**Limits:** scanning is heuristic and cannot find every identifier, private dataset or unusual secret. Never rely on a passing scan as permission to share sensitive data.

If something sensitive is accidentally uploaded, immediately stop further publication, rotate leaked credentials if applicable and purge the exposed Git history using appropriate GitHub procedures. Merely deleting a file in a later commit is insufficient.
