# Verification, 2026-09-24 (second session)

Re-checked Nobel lines against the official API from this sandbox's fetch tool
(the sandbox itself cannot open TLS to nobelprize.org; the tool runs outside it).
Source of record remains `catalog.json`; this note records that the live API
still agrees with the stored copy.

| Stored prize | Official API check | Result |
| --- | --- | --- |
| physics-2025 | [api.nobelprize.org/2/nobelPrize/phy/2025](https://api.nobelprize.org/2/nobelPrize/phy/2025) — John Clarke, Michel H. Devoret, John M. Martinis, 2025-10-07, "macroscopic quantum mechanical tunnelling and energy quantisation in an electric circuit" | Matches catalog (names, portions 1/3 each, date, motivation) |
| literature-2025 | [api.nobelprize.org/2/nobelPrize/lit/2025](https://api.nobelprize.org/2/nobelPrize/lit/2025) — László Krasznahorkai, 2025-10-09, "compelling and visionary oeuvre…" | Matches catalog; also the official YES contract stored for `KXNOBELLIT-25` |
| peace-2025 | [api.nobelprize.org/2/nobelPrize/pea/2025](https://api.nobelprize.org/2/nobelPrize/pea/2025) — Maria Corina Machado, 2025-10-10, "for her tireless work promoting democratic rights for the people of Venezuela…" | Matches catalog; matches the stored `KXNOBELPEACE-25` YES contract |
| economics-2025 | [api.nobelprize.org/2/nobelPrize/eco/2025](https://api.nobelprize.org/2/nobelPrize/eco/2025) — Joel Mokyr (1/2), Philippe Aghion (1/4), Peter Howitt (1/4), 2025-10-13, "for having explained innovation-driven economic growth" | Matches catalog; confirms the `laureate_not_in_stored_contracts` flag is about the Kalshi contract list, not the Nobel record |

Also checked: [buffedlizard55-lab.github.io/NOBEL-PRIZE](https://buffedlizard55-lab.github.io/NOBEL-PRIZE/) is live and shows the same 2025 prizes (including medicine 2025: Brunkow, Ramsdell, Sakaguchi, and chemistry 2025: Kitagawa, Robson, Yaghi), consistent with this repository's catalog copy in `data/nobel/catalog.json`.

No 2026 prize was in the API responses. Announcements are due 6–13 October 2026; nothing was filled in ahead of them.
