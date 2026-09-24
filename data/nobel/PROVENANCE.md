# Nobel data provenance

This directory is an organized copy of official Nobel Prize records for review inside this project. It is not a new scrape of every nomination page.

## What was copied, and from where

Copied on 2026-09-24 from the public repository [buffedlizard55-lab/NOBEL-PRIZE](https://github.com/buffedlizard55-lab/NOBEL-PRIZE) at commit `274e3734b5bb656a907e1e1d29b298ce56dfeee5`:

- `catalog.json`
- `prizes.csv`
- `laureates.csv`
- `nominations.csv`
- `flags.json`
- `FLAGS.md`
- `verification-report.json`

That repository states the files were retrieved on 2026-09-24 from `https://api.nobelprize.org` and from downloaded nomination-archive list pages. Its verification report recorded 682 prize records (633 awarded, 49 not awarded), 1,018 laureate records, and 1,026 award slots. Those counts are re-checked by `tests/test_engine.py` against the files in this directory.

The raw HTML archive and the per-year nomination JSON tree were not copied. They remain in that repository. Every stored nomination row in `nominations.csv` has a `showUrl` and a `listUrl` on nobelprize.org.

## What this sandbox checked directly

This environment could not open a TLS connection to `api.nobelprize.org` or `www.nobelprize.org` (OpenSSL `SSL_ERROR_SYSCALL`). A separate fetch of the official API did succeed:

- `https://api.nobelprize.org/2.1/nobelPrizes?limit=1` returned `meta.count` 682 on 2026-09-24.
- `https://api.nobelprize.org/2/nobelPrize/phy/2025` returned John Clarke, Michel H. Devoret, and John M. Martinis, date awarded 2025-10-07, prize amount 11,000,000 SEK, motivation “for the discovery of macroscopic quantum mechanical tunnelling and energy quantisation in an electric circuit”. That matches `catalog.json` prize `physics-2025`.

## What is not in these files

- Nominations from 1976 onward are still sealed. The archive tables retrieved in September 2026 stop at 1975 (medicine at 1953). Sealed prizes have an empty nominee list. Names were not guessed.
- Economic sciences nominations are not in the public nomination archive. A zero from that archive is not evidence that nobody was nominated.
- The awarding institutions do not publish a ranked explanation of why one project was chosen over another. The stated reason is the official motivation. Nomination counts are not votes. The archive manual says so: [nomination archive manual](https://www.nobelprize.org/nomination/archive/manual.php).
- 2026 prizes had not been awarded on 2026-09-24. They are not in the catalog. The official physics list said the 2026 physics prize would be announced on 6 October 2026 at the earliest.

## Terms

Nobel Prize API data is published under the [API terms](https://www.nobelprize.org/about/terms-of-use-for-api-nobelprize-org-and-data-nobelprize-org/). This project is not affiliated with, endorsed by, or sponsored by Nobel Prize Outreach or the Nobel Foundation. Data is not altered to hide a disagreement; disagreements are flags.
