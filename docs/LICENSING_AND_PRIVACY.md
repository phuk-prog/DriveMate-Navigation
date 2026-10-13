# Public-repository licensing, privacy and security

## Public does not mean open-source licensed

There is intentionally no project-wide `LICENSE` file yet; selecting a licence requires an explicit decision. Do not copy source from another engine into this repository merely because it is visible on GitHub. Track component author, exact version/commit, licence, provenance, notices, derivative obligations and compatibility **before** importing.

Examples to investigate independently: MIT (Valhalla), BSD-2-Clause (OSRM), Apache-2.0 (GraphHopper / Organic Maps source), GPLv3 (OsmAnd); data, artwork and bundled maps may have different obligations. Commercial providers require specific rights to access, benchmark, cache, reproduce or use their outputs. Do not redistribute proprietary route data.

## Road data

OpenStreetMap is supplied under ODbL obligations (including attribution and potential share-alike for derivative databases). Do not upload unredacted location histories or download and recommit large map extracts. Keep import scripts and checksums in version control; store source datasets externally with licence records.

## Personal data, location history and API credentials

No real GPS track, home/work location, vehicle identifier, licence plate, user profile, phone logs, server token, paid API credential, private street imagery or proprietary maps in this **public** repository. Synthetic fixtures are safe. Real recordings must be consented, held separately and access-controlled; derived regression fixtures need privacy review.

Treat pull requests and provider responses as untrusted input. GitHub Actions should never expose secrets to untrusted fork code. Do not enable expensive external APIs, APK builds or deployments by default.

## Deployment safeguard

Changes to the existing private `phuk-prog/DriveMate` Android app are out of scope until the owner expressly approves integration and the necessary independent tests pass.
