"""Research cards: one per strategy family, phase 1 (retro) and phase 2.

A card states, before any result is read:
  question      what the family tests, in one sentence
  mechanism     why the rule could work (the economic story), or "none" for controls
  sources       ids in simcomp.research_sources.SOURCES (verified links)
  channels      decision-time information the family reads (CHANNELS below)
  predicts      the predicted sign of the effect on the settled universes
  falsified_if  what result would count against it on this snapshot
  kind          signal | control | null | placebo | sizing | exit | ablation

Common verdict rules are in simcomp/analysis.py and docs/RESEARCH.md; a card's
falsified_if adds family-specific conditions on top of them. The result of a
cited paper is never evidence for a simulated result: the card only records
which published idea suggested the rule.
"""

from __future__ import annotations

from simcomp.research_sources import SOURCES

CHANNELS = {
    "own_candles": "this market's decision candle and at most 24 prior candles (closing bid/ask/trade, volume, open interest)",
    "own_book": "this participant's own simulated position and cash",
    "event_quotes": "latest candle at or before T of every stored contract in the same Kalshi event (ctx.event)",
    "settled_pool": "official results of markets whose settlement_ts is strictly before T (ctx.settled)",
    "schedule": "event strike_date published by Kalshi (ctx.schedule); empty for Nobel events",
    "clock": "the decision timestamp itself (UTC hour, weekday, market age from open_time)",
    "seed": "a SHA-256 draw from a fixed seed; carries no market information",
}

STANDARD_FALSIFICATION = (
    "Not supported on this snapshot if, in a settled universe, the median ending equity of its traded "
    "variants is at or below the batch-001 null median, or fails any support condition: above the null "
    "p95 and above $10,000, above its matched placebo where one exists, and still above the null median "
    "after dropping the single most helpful event. Fewer than 3 traded variants, fewer than 3 settled "
    "events touched, or no YES outcome among them means low power, not support."
)
REFERENCE_NOTE = (
    "Reference family: it is a yardstick and is never itself given a supported or not-supported verdict."
)


def _c(question, mechanism, sources, channels, predicts, falsified_if="", kind="signal"):
    return {
        "question": question,
        "mechanism": mechanism,
        "sources": list(sources),
        "channels": list(channels),
        "predicts": predicts,
        "falsified_if": (falsified_if + " " if falsified_if else "")
        + (REFERENCE_NOTE if kind in ("null", "control", "placebo") else STANDARD_FALSIFICATION),
        "kind": kind,
    }


OWN = ("own_candles", "own_book")
EV = ("own_candles", "event_quotes", "own_book")
POOL = ("own_candles", "settled_pool", "own_book")

CARDS: dict[str, dict] = {
    # ---------------- phase 1 (retro cards; the rules predate this file) ----------------
    "null_model": _c(
        "What spread of outcomes does random valid entry produce under the competition rules?",
        "None. Seeded draws fire on a fixed share of candles; the band is the yardstick for every other family.",
        ("none-design-control", "harvey-liu-zhu-2016"), ("own_candles", "own_book", "seed"),
        "No edge: centred near the fee-and-spread drag.", "", "null"),
    "favorite_band": _c(
        "Does buying and holding YES in a declared favorite band beat random entry?",
        "Favorite-longshot bias: high-price contracts win more often than their price implies.",
        ("burgi-deng-whelan-2025", "snowberg-wolfers-2010", "thaler-ziemba-1988"), OWN,
        "Positive vs null in settled universes.", "Negative if favorites in this sample lost at their price."),
    "longshot_band": _c(
        "Does buying and holding YES at low asks lose, as the longshot-bias literature predicts?",
        "Longshots are over-priced by risk-seeking or probability-weighting buyers.",
        ("burgi-deng-whelan-2025", "kahneman-tversky-1979", "snowberg-wolfers-2010"), OWN,
        "Negative vs null (buying longshots should lose).", "Counts as surprising if it beats the null p95."),
    "momentum": _c(
        "Do close-to-close moves continue on the next candles?",
        "Slow diffusion of information across traders.", ("jegadeesh-titman-1993", "moskowitz-ooi-pedersen-2012"), OWN,
        "Positive vs null if information arrives gradually.", "Mirror of contrarian; both losing means the trigger picks costly moments."),
    "contrarian": _c(
        "Do close-to-close moves reverse?", "Overreaction and liquidity-driven price pressure.",
        ("de-bondt-thaler-1985", "jegadeesh-1990"), OWN, "Positive vs null if moves overshoot.", "Mirror of momentum."),
    "mean_reversion": _c(
        "Does a price below its recent mean return toward it?", "Temporary price pressure from uninformed flow.",
        ("jegadeesh-1990", "glosten-milgrom-1985"), OWN, "Positive vs null.", ""),
    "favorite_exit": _c(
        "Does taking profit or cutting loss change a favorite entry's result?", "Exit rules trade variance against expected value.",
        ("none-technical-rule",), OWN, "Close to the favorite band; exits pay extra spread.", "", "exit"),
    "favorite_exit_reentry": _c(
        "Does re-entering after an exit add value?", "Re-entry recaptures a favorite after noise.",
        ("none-technical-rule",), OWN, "Close to the favorite band minus extra spread.", "", "exit"),
    "stop_loss_favorite": _c(
        "Does a stop-loss on favorites help?", "Stops cut losing tails, but in a binary market a drop is often information.",
        ("none-technical-rule",), OWN, "Slightly negative vs hold (stops sell at the bid).", "", "exit"),
    "take_profit_favorite": _c(
        "Does taking profit early on favorites help?", "Locks in gains but gives up the payout to $1.",
        ("none-technical-rule",), OWN, "Negative vs hold if favorites usually settle YES.", "", "exit"),
    "relative_spread_value": _c(
        "Do tight relative spreads mark better entries?", "Tighter spreads mean less adverse selection per contract.",
        ("glosten-milgrom-1985", "tetlock-2008-liquidity"), OWN, "Positive vs null.", ""),
    "volatility_gate": _c(
        "Do entries in calm markets do better?", "Calm prices suggest no pending information shock.",
        ("none-technical-rule",), OWN, "Mildly positive vs null.", ""),
    "volume_momentum_window": _c(
        "Do moves on above-median volume continue?", "Volume marks informed trading.",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", ""),
    "breakout_hold": _c(
        "Do new highs of the recent window continue?", "Breakouts mark information arrival.",
        ("moskowitz-ooi-pedersen-2012", "none-technical-rule"), OWN, "Positive vs null.", ""),
    "entry_timing_band": _c(
        "Does the same favorite band do better entered later in a market's life?", "Prices become more accurate near close.",
        ("burgi-deng-whelan-2025", "page-clemen-2013"), ("own_candles", "own_book", "clock"), "Later entries closer to fair value.", ""),
    "entry_timing_slice": _c(
        "Same question for a narrow price slice.", "As above.", ("burgi-deng-whelan-2025",), ("own_candles", "own_book", "clock"),
        "As above.", ""),
    "favorite_band_wide": _c(
        "How much spread can a favorite entry tolerate?", "Wide spreads are paid on entry and at the mark.",
        ("glosten-milgrom-1985",), OWN, "Worse than the tight favorite band.", ""),
    "longshot_band_wide": _c(
        "How much spread can a longshot entry tolerate?", "As above.", ("glosten-milgrom-1985",), OWN, "Worse than the tight band.", ""),
    "slice_band": _c(
        "Do narrow price slices differ from each other?", "Maps the calibration curve slice by slice.",
        ("snowberg-wolfers-2010", "page-clemen-2013"), OWN, "Low slices lose, high slices win (FLB shape).", ""),
    "tight_value_ranged": _c(
        "Do cheap contracts with tight spreads do better than cheap contracts in general?",
        "Tight spreads may remove the worst-priced longshots.", ("tetlock-2008-liquidity",), OWN, "Less negative than the longshot band.", ""),

    # ---------------- batch 011: event structure ----------------
    "event_normalized": _c(
        "Is a contract mispriced relative to its share of the event's total probability mass?",
        "In a one-winner field the YES prices should sum to about 1; dividing by the sum removes a common over-round.",
        ("wolfers-zitzewitz-2004", "rothschild-sethi-2016", "kalshi-get-event"), EV,
        "Positive vs null where the stored field is complete.", "Nobel economics can have several laureates, so W=1 is an assumption; incomplete fields bias the sum."),
    "event_overround_no": _c(
        "When YES bids across an event sum well above 1, does buying NO on cheap legs pay?",
        "An over-round means the field is over-priced as a whole; the cheapest legs carry the most over-pricing (FLB).",
        ("saguillo-2025-arbitrage", "burgi-deng-whelan-2025"), EV, "Positive vs null.", "Not a true arbitrage: single legs, fees, and multi-winner events."),
    "event_underround_yes": _c(
        "In a mutually exclusive event whose asks sum below 1, does buying YES pay?",
        "An under-round prices the whole field below its guaranteed $1 payout.",
        ("saguillo-2025-arbitrage", "kalshi-get-event"), EV, "Positive vs null if it ever fires.", "Fires only if Kalshi marks the event mutually_exclusive and the stored mass is >= the gate."),
    "event_leader": _c(
        "Does the clear leader of an event field win more often than its price implies?",
        "Favorite-longshot bias at the event level: mass leaks to the long tail.",
        ("burgi-deng-whelan-2025", "snowberg-wolfers-2010"), EV, "Positive vs null.", ""),
    "event_rank_k": _c(
        "Are the second and third favorites of an event priced fairly?",
        "Tests where on the rank curve the bias turns: next-to-leaders may be the most over-priced.",
        ("snowberg-wolfers-2010",), EV, "Negative or flat vs null.", ""),
    "event_field_no": _c(
        "Does selling the long tail of an event field (buying NO on low-ranked legs) pay?",
        "Longshots in a many-candidate field are over-bought.",
        ("burgi-deng-whelan-2025", "thaler-ziemba-1988"), EV, "Positive vs null, small per trade.", "A single surprise laureate from the tail can wipe out many small gains."),
    "event_concentration": _c(
        "Is a leader more reliable when the event's mass is concentrated (high HHI) or diffuse?",
        "Concentration measures consensus; diffuse fields may have under-priced leaders or none.",
        ("manski-2006", "wolfers-zitzewitz-2004"), EV, "High-concentration leaders beat low-concentration leaders.", ""),
    "event_leader_change": _c(
        "When the event leader changes, does the new leader keep winning?",
        "A leader change marks information arrival that is not fully priced on the first candle.",
        ("moskowitz-ooi-pedersen-2012",), EV, "Positive vs null.", ""),
    "event_rotation": _c(
        "Do moves that rotate mass between siblings (total unchanged) continue?",
        "Rotation is candidate-specific news; repricing the whole field is not.",
        ("wolfers-zitzewitz-2004",), EV, "Positive vs null.", ""),

    # ---------------- batch 012: literature priors ----------------
    "logit_scale": _c(
        "Does stretching prices away from 50% in logit space (k>1) find value?",
        "Favorite-longshot bias written as a logit slope above 1: true odds are more extreme than prices.",
        ("burgi-deng-whelan-2025", "page-clemen-2013", "snowberg-wolfers-2010"), OWN,
        "Positive vs null, larger for larger k if the bias is strong.", ""),
    "logit_reverse": _c(
        "Control: does compressing prices toward 50% (k<1) lose?",
        "The opposite of the favorite-longshot bias; included so the logit family has a mirror.",
        ("snowberg-wolfers-2010", "none-design-control"), OWN, "Negative vs null.", "", "control"),
    "longshot_no_writer": _c(
        "Does buying NO against cheap YES contracts pay after fees?",
        "Low-price contracts win far less often than their price on Kalshi.",
        ("burgi-deng-whelan-2025", "kalshi-fee-schedule"), OWN, "Positive vs null.", ""),
    "high_favorite_yes": _c(
        "Do very high favorites (85-99 cents) earn the small positive return reported for Kalshi?",
        "Favorites are under-priced; returns per contract are small but frequent.",
        ("burgi-deng-whelan-2025",), OWN, "Small positive vs null.", ""),
    "prelec_inverse": _c(
        "If prices are probability-weighted beliefs (Prelec w), does inverting the weighting find value?",
        "Prelec's w overweights small and underweights large probabilities.",
        ("prelec-1998", "kahneman-tversky-1979"), OWN, "Positive vs null (acts like strong NO on longshots).", ""),
    "fee_aware_logit": _c(
        "Does requiring the model edge to exceed the Kalshi taker fee improve the logit family?",
        "A hurdle that includes the fee should remove trades whose edge the fee consumes.",
        ("kalshi-fee-schedule", "burgi-deng-whelan-2025"), OWN, "Better than logit_scale at the same k.", ""),

    # ---------------- batch 013: walk-forward learning ----------------
    "learned_bucket_calibration": _c(
        "Can a calibration table estimated from already-settled markets beat the price?",
        "If mis-calibration is stable across markets, past price-bucket hit rates predict new ones.",
        ("page-clemen-2013", "burgi-deng-whelan-2025", "bailey-lopez-de-prado-2014"), POOL,
        "Positive vs null once the pool is large.", "Pool is small and selected; abstains most of the time."),
    "learned_base_rate": _c(
        "Does the series' past YES rate beat the price?",
        "Base-rate neglect: traders may ignore how often a series resolves YES.",
        ("kahneman-tversky-1979",), POOL, "Positive vs null for repeated series (Fed, weather).", "Nobel series have too few settled markets."),
    "learned_logit_slope": _c(
        "Does a logit slope fitted on settled markets beat a fixed literature slope?",
        "Learning k from data avoids assuming its size.",
        ("page-clemen-2013", "bailey-lopez-de-prado-2014"), POOL, "At least as good as logit_scale.", ""),
    "learned_recency_rate": _c(
        "Does weighting recent settlements more heavily help the base rate?",
        "Regimes change; recent outcomes may be more relevant.", ("none-technical-rule",), POOL, "Slightly better than the flat base rate.", ""),
    "learned_age_calibration": _c(
        "Does calibration depend on how long the market has been open?",
        "Prices are less accurate far from expiry.", ("page-clemen-2013",), POOL + ("clock",), "Positive vs null for young markets.", ""),
    "uniform_field_prior": _c(
        "Does shrinking each contract toward 1/N of its event help?",
        "A uniform prior corrects over-confidence in the leaders; the opposite of the FLB story, so it doubles as a test of which way bias runs.",
        ("manski-2006",), ("own_candles", "event_quotes", "settled_pool", "own_book"), "Negative if the FLB holds.", ""),

    # ---------------- batch 014: time ----------------
    "time_age_min": _c(
        "Do entries in older markets do better?", "Prices become more accurate as a market matures.",
        ("page-clemen-2013", "burgi-deng-whelan-2025"), OWN + ("clock",), "Favorite entries improve with age.", ""),
    "time_age_max": _c(
        "Do entries in very young markets do worse (or better)?", "Young markets can be mispriced before liquidity arrives.",
        ("page-clemen-2013",), OWN + ("clock",), "Longshot NO in young markets positive.", ""),
    "time_horizon_near": _c(
        "Do entries close to Kalshi's scheduled strike time do better?", "Calibration improves as expiry nears.",
        ("burgi-deng-whelan-2025", "page-clemen-2013", "kalshi-get-event"), OWN + ("schedule",),
        "Favorites near expiry positive.", "Only events with a strike_date (Fed, NY temperature) can trade; Nobel abstains."),
    "time_horizon_far": _c(
        "Do entries far from the scheduled strike carry more bias?", "The FLB grows with time to expiry.",
        ("page-clemen-2013", "kalshi-get-event"), OWN + ("schedule",), "Longshot NO far from expiry positive.", ""),
    "time_utc_hour": _c(
        "Does the UTC hour of the decision matter?", "Liquidity and attention vary by time of day.",
        ("none-technical-rule",), OWN + ("clock",), "No effect expected (a check for artefacts).", "Daily candles all close at the same hour; only hourly markets can vary.", "control"),
    "time_weekday": _c(
        "Do weekend entries differ from weekday entries?", "Weekend effect in asset returns.",
        ("french-1980",), OWN + ("clock",), "Small or none.", ""),
    "time_pre_close_exit": _c(
        "Does selling a favorite before the scheduled close beat holding to settlement?",
        "Exiting avoids event risk but pays the spread and gives up the $1 payout.",
        ("kalshi-get-event", "none-technical-rule"), OWN + ("schedule",), "Negative vs holding if favorites usually win.", "", "exit"),

    # ---------------- batch 015: liquidity / volume / OI ----------------
    "oi_growth_follow": _c(
        "Do price moves backed by rising open interest continue?", "New positions (not just trading) signal conviction.",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", ""),
    "oi_decline_fade": _c(
        "Do moves on falling open interest reverse?", "Moves from positions closing carry less information.",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", ""),
    "volume_spike_follow": _c(
        "Do moves on volume spikes continue?", "High-volume moves are informed (high-volume return premium).",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", "Mirror of volume_spike_fade."),
    "volume_spike_fade": _c(
        "Do moves on volume spikes reverse?", "Spikes can be liquidity demand that reverses.",
        ("jegadeesh-1990", "glosten-milgrom-1985"), OWN, "Positive vs null.", "Mirror of volume_spike_follow."),
    "dormant_wakeup": _c(
        "When a market trades after several dormant candles, does the first move continue?", "Dormancy then activity marks news.",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", ""),
    "liquidity_gate": _c(
        "Do simple entries work better in liquid markets?", "Liquid markets are better priced and cheaper to trade.",
        ("tetlock-2008-liquidity",), OWN, "Favorite entries closer to fair; less FLB.", ""),
    "illiquidity_gate": _c(
        "Do simple entries work better in illiquid markets?", "Illiquid markets carry more mispricing but cost more.",
        ("tetlock-2008-liquidity", "shleifer-vishny-1997"), OWN, "Longshot NO stronger in illiquid markets.", ""),
    "spread_compression": _c(
        "When the spread tightens, does the concurrent move continue?", "Market makers tighten when uncertainty resolves.",
        ("glosten-milgrom-1985",), OWN, "Positive vs null.", ""),
    "stale_quote_drift": _c(
        "Do quote moves without trade prints continue?", "Quotes move ahead of trades when makers update.",
        ("glosten-milgrom-1985",), OWN, "Positive vs null.", ""),
    "turnover_fade": _c(
        "Do moves on high turnover (volume / open interest) reverse?", "Churn without new positions is noise.",
        ("gervais-kaniel-mingelgrin-2001",), OWN, "Positive vs null.", ""),

    # ---------------- batch 016: trend / reversal ----------------
    "ma_crossover": _c(
        "Do moving-average crossovers of the reference price predict settlement?", "Technical trend rule.",
        ("none-technical-rule",), OWN, "No edge expected.", ""),
    "tsmom_window": _c(
        "Does the sign of the move over a window predict settlement?", "Time-series momentum.",
        ("moskowitz-ooi-pedersen-2012",), OWN, "Positive vs null.", ""),
    "big_move_follow": _c(
        "Do large one-candle moves continue?", "Large moves are news.", ("moskowitz-ooi-pedersen-2012",), OWN,
        "Positive vs null.", "Mirror of big_move_fade."),
    "big_move_fade": _c(
        "Do large one-candle moves reverse?", "Overreaction.", ("de-bondt-thaler-1985", "jegadeesh-1990"), OWN,
        "Positive vs null.", "Mirror of big_move_follow."),
    "rsi_fade": _c(
        "Does fading an extreme relative-strength index work?", "Technical overbought/oversold rule.",
        ("none-technical-rule",), OWN, "No edge expected.", ""),
    "bollinger_revert": _c(
        "Do prices outside a z-score band revert?", "Technical band rule; mean reversion.",
        ("none-technical-rule", "jegadeesh-1990"), OWN, "No edge expected.", ""),
    "run_follow": _c(
        "Do runs of consecutive moves continue?", "Trend persistence.", ("moskowitz-ooi-pedersen-2012",), OWN, "Small positive.", "Mirror of run_fade."),
    "run_fade": _c(
        "Do runs of consecutive moves reverse?", "Overreaction.", ("de-bondt-thaler-1985",), OWN, "Small positive.", "Mirror of run_follow."),
    "range_revert": _c(
        "Do prices at the edge of their recent range revert?", "Range trading.", ("none-technical-rule",), OWN, "No edge expected.", "Mirror of range_breakout."),
    "range_breakout": _c(
        "Do prices at the edge of their recent range continue?", "Breakout trading.", ("none-technical-rule",), OWN, "No edge expected.", "Mirror of range_revert."),
    "buy_the_dip": _c(
        "Does buying a sharp drop from the recent high pay?", "Overreaction to bad news.", ("de-bondt-thaler-1985",), OWN,
        "Negative if drops are information (binary markets).", ""),
    "fade_the_rally": _c(
        "Does buying NO after a sharp rally pay?", "Overreaction to good news.", ("de-bondt-thaler-1985",), OWN,
        "Negative if rallies are information.", ""),

    # ---------------- batch 017: sizing ----------------
    "kelly_fraction": _c(
        "Does Kelly-style sizing on a logit edge change the result versus the default size?",
        "Kelly maximizes log growth when the probability model is right; fractional Kelly cuts model risk.",
        ("kelly-1956",), OWN, "Larger fractions amplify whatever the logit edge does.", "Competition caps ($100 entry target, 5% of cash, 500 contracts, $300 per market) bind above small fractions, so larger fractions may not trade larger; the clip rate is reported.", "sizing"),
    "fixed_contracts": _c(
        "How does a fixed contract count compare with the fixed-dollar default?", "Fixed contracts spend more on favorites and less on longshots.",
        ("none-design-control",), OWN, "Same sign as the entry rule; scale differs.", "", "sizing"),
    "edge_scaled_size": _c(
        "Does sizing in proportion to model edge help?", "Bet more where the model disagrees most with the price.",
        ("kelly-1956",), OWN, "Better than flat size if the edge estimate carries information.", "", "sizing"),
    "cash_fraction_size": _c(
        "Does sizing as a fraction of current cash change the result?", "Automatically de-risks after losses.",
        ("kelly-1956",), OWN, "Smaller swings, same sign.", "Cash is never recycled mid-run, so this mostly scales down.", "sizing"),
    "payout_target_size": _c(
        "Does targeting a fixed payout per trade change the result?", "Equalizes the upside across prices.",
        ("none-design-control",), OWN, "Same sign as entry, less weight on favorites.", "", "sizing"),
    "cash_reserve_gate": _c(
        "Does keeping a cash reserve change rank?", "Stops trading once cash falls below the reserve.",
        ("none-design-control",), OWN, "Scales exposure; tests whether early trades are better than late ones.", "", "sizing"),
    "ladder_average_down": _c(
        "Does adding to a favorite as its price falls help?", "Averaging down buys cheaper if the drop is noise.",
        ("none-technical-rule",), OWN, "Negative if drops are information.", "", "sizing"),
    "ladder_pyramid": _c(
        "Does adding to a favorite as its price rises help?", "Pyramiding adds when the market confirms.",
        ("moskowitz-ooi-pedersen-2012",), OWN, "Positive if confirmation carries information.", "", "sizing"),
    "split_entry": _c(
        "Does spreading an entry over several candles help?", "Time diversification of the entry price.",
        ("none-design-control",), OWN, "Close to single entry.", "", "sizing"),

    # ---------------- batch 018: exits ----------------
    "exit_time_stop": _c("Does exiting after n candles beat holding?", "Caps exposure time.", ("none-technical-rule",), OWN, "Negative vs hold for favorites.", "Compare with exit_hold_control.", "exit"),
    "exit_clock_stop": _c("Does exiting after a fixed wall-clock time beat holding?", "As above, independent of candle interval.", ("none-technical-rule",), OWN + ("clock",), "Negative vs hold.", "Compare with exit_hold_control.", "exit"),
    "exit_trailing_stop": _c("Does a trailing stop beat holding?", "Protects gains.", ("none-technical-rule",), OWN, "Negative vs hold in binary markets.", "Compare with exit_hold_control.", "exit"),
    "exit_breakeven_stop": _c("Does moving the stop to breakeven after a gain help?", "Removes loss once in profit.", ("none-technical-rule",), OWN, "Negative vs hold.", "Compare with exit_hold_control.", "exit"),
    "exit_price_target": _c("Does selling at a price target beat holding to $1?", "Takes near-certain gains early and frees risk.", ("none-technical-rule",), OWN, "Slightly negative vs hold (gives up the last cents).", "Compare with exit_hold_control.", "exit"),
    "exit_edge_gone": _c("Does exiting when the model edge disappears help?", "Hold only while the model says the price is cheap.", ("kelly-1956", "burgi-deng-whelan-2025"), OWN, "Close to hold.", "Compare with exit_hold_control.", "exit"),
    "exit_stop_and_reverse": _c("Does flipping to NO after a stop help?", "A drop may be news; reversing follows it.", ("moskowitz-ooi-pedersen-2012",), OWN, "Positive if drops continue.", "Compare with exit_hold_control.", "exit"),
    "exit_volatility_stop": _c("Does a stop scaled to recent volatility help?", "Adapts the stop to noise.", ("none-technical-rule",), OWN, "Negative vs hold.", "Compare with exit_hold_control.", "exit"),
    "exit_partial_take": _c("Does selling half at a gain help?", "Balances locking gains against the payout.", ("none-technical-rule",), OWN, "Between hold and full take-profit.", "Compare with exit_hold_control.", "exit"),
    "exit_ladder_take": _c("Does selling in three rungs help?", "Staged profit taking.", ("none-technical-rule",), OWN, "Between hold and full take-profit.", "Compare with exit_hold_control.", "exit"),
    "exit_max_loss": _c("Does a dollar loss limit help?", "Caps loss per market.", ("none-technical-rule",), OWN, "Negative vs hold.", "Compare with exit_hold_control.", "exit"),
    "exit_hold_control": _c("Control: same entries, hold to settlement.", "None; the reference every exit rule is read against.", ("none-design-control",), OWN, "Reference.", "", "control"),
    "exit_random_control": _c("Control: same entries, exit at random.", "None; tells us whether any timed exit beats a random exit.", ("none-design-control",), OWN + ("seed",), "Worse than hold by the spread paid.", "", "control"),

    # ---------------- batch 019: ablations ----------------
    "ablation_lagged_signal": _c(
        "How fast does a momentum signal decay if acted on d candles late?", "Tests whether information in moves is priced quickly.",
        ("burgi-deng-whelan-2025", "none-design-control"), OWN, "Results converge to the null as d grows.", "", "ablation"),
    "ablation_delayed_entry": _c(
        "How much does waiting d candles after a signal cost?", "Timing sensitivity of band entries.",
        ("none-design-control",), OWN, "Small cost if the signal persists.", "", "ablation"),
    "ablation_price_source": _c(
        "Does the momentum result depend on which price defines the move (trade, mid, bid, ask)?", "Quote-driven vs trade-driven moves.",
        ("glosten-milgrom-1985",), OWN, "Trade and mid similar; bid/ask noisier.", "", "ablation"),
    "ablation_decision_frequency": _c(
        "Does deciding on every k-th candle change results?", "Tests sensitivity to decision frequency.",
        ("none-design-control",), OWN, "Fewer trades, similar per-trade sign.", "", "ablation"),
    "ablation_spread_tolerance": _c(
        "How does the result change as the spread cap loosens?", "Spread cost vs coverage.",
        ("glosten-milgrom-1985",), OWN, "Monotone decline with wider caps.", "", "ablation"),
    "ablation_noisy_price": _c(
        "How robust are the rules to seeded noise in the reference price?", "If noise barely changes results, the rule's precision is not doing the work.",
        ("none-design-control",), OWN + ("seed",), "Results degrade smoothly toward the null.", "", "ablation"),
    "ablation_coarse_grid": _c(
        "Do rules still work when prices are rounded to a coarse grid?", "Tests how much price precision matters.",
        ("none-design-control",), OWN, "Coarse grids approach the null.", "", "ablation"),
    "ablation_first_quote": _c(
        "Control: enter YES or NO at the first fillable quote with no price rule.", "None; isolates the value of any price rule.",
        ("none-design-control",), OWN, "Near the null.", "", "control"),
    "ablation_window_truncation": _c(
        "Does the mean-reversion result depend on how much history is visible?", "Tests information-set length.",
        ("none-design-control",), OWN, "Short windows noisier.", "", "ablation"),
    "ablation_trade_print_gate": _c(
        "Do rules behave differently on candles with and without a trade print?", "Trade prints are real transactions; quotes can be stale.",
        ("glosten-milgrom-1985",), OWN, "Entries with prints better.", "", "ablation"),

    # ---------------- batch 020: ensembles ----------------
    "ensemble_vote": _c(
        "Does requiring several simple signals to agree help?", "Independent weak signals combine into a stronger one if their errors differ.",
        ("bailey-lopez-de-prado-2014",), OWN, "Fewer trades, better per trade.", ""),
    "ensemble_crowd_fade": _c(
        "Does fading moments when several trend signals agree help?", "Crowded trends overshoot.",
        ("de-bondt-thaler-1985",), OWN, "Positive if trends overshoot.", ""),
    "regime_switch": _c(
        "Does switching between reversion (volatile) and trend (calm) help?", "Different regimes favor different rules.",
        ("none-technical-rule",), OWN, "No edge expected.", ""),
    "logit_momentum_agree": _c(
        "Does the logit model work better when recent momentum agrees?", "Two independent reasons for the same side.",
        ("burgi-deng-whelan-2025", "moskowitz-ooi-pedersen-2012"), OWN, "Better than logit alone.", ""),
    "logit_skip_conflict": _c(
        "Does skipping logit trades that fight momentum help?", "Conflicting momentum may be news the model misses.",
        ("burgi-deng-whelan-2025",), OWN, "Better than logit alone.", "Pair with logit_only_conflict."),
    "logit_only_conflict": _c(
        "Do logit trades that fight momentum do worse?", "Mirror of logit_skip_conflict.", ("burgi-deng-whelan-2025",), OWN,
        "Worse than logit alone.", "Pair with logit_skip_conflict."),
    "event_leader_oi": _c(
        "Is an event leader with rising open interest a better bet?", "Conviction plus consensus.",
        ("gervais-kaniel-mingelgrin-2001", "burgi-deng-whelan-2025"), EV, "Positive vs null.", ""),
    "consensus_favorite": _c(
        "Do favorites confirmed by calm, volume, OI and event rank do better?", "Multiple confirmations.",
        ("burgi-deng-whelan-2025",), EV, "Better than the plain favorite band.", ""),
    "calm_event_favorite": _c(
        "Do calm favorites that lead their event do better?", "Stable consensus favorites.",
        ("burgi-deng-whelan-2025",), EV, "Better than the plain favorite band.", ""),
    "momentum_liquidity": _c(
        "Does momentum work only in liquid markets?", "Liquid markets aggregate information faster.",
        ("tetlock-2008-liquidity", "moskowitz-ooi-pedersen-2012"), OWN, "Positive vs null in liquid markets.", ""),
    "rule_mixture_control": _c(
        "Control: each market is assigned to one of three simple rules by a seed.", "None; shows the spread from mixing rules at random.",
        ("none-design-control",), OWN + ("seed",), "Between its component rules.", "", "control"),
    "null_matched_rate": _c(
        "Second null: random entries at controlled rates with a fixed or random side.", "None; checks that the batch-001 band is not special.",
        ("none-design-control", "harvey-liu-zhu-2016"), OWN + ("seed",), "Same band as batch-001 for side=coin.", "", "null"),
    "learned_plus_structure": _c(
        "Does a learned calibration edge confirmed by the normalized event price help?", "Two independent fair-value estimates agree.",
        ("page-clemen-2013", "wolfers-zitzewitz-2004"), ("own_candles", "event_quotes", "settled_pool", "own_book"), "Better than either alone.", ""),
    "horizon_learned": _c(
        "Does a learned calibration edge work better near the scheduled close?", "Calibration and horizon interact.",
        ("page-clemen-2013", "kalshi-get-event"), ("own_candles", "settled_pool", "schedule", "own_book"), "Positive vs null near expiry.", ""),
}


def card_for(family: str) -> dict:
    """The card for a family. Placebo cards are derived from their parent family."""
    if family in CARDS:
        return CARDS[family]
    if family.startswith("placebo_"):
        parent = family[len("placebo_"):]
        base = CARDS[parent]
        return {
            "question": f"Placebo for {parent}: same trigger, markets, times and size; the side is a seeded coin.",
            "mechanism": "None. The difference between the family and this placebo is the value of choosing the side.",
            "sources": ["none-design-control"],
            "channels": sorted(set(base["channels"]) | {"seed"}),
            "predicts": f"Worse than {parent} if its side choice carries information; equal if only the timing matters.",
            "falsified_if": f"If {parent} does not beat this placebo, {parent}'s side choice is not supported.",
            "kind": "placebo",
            "placebo_of": parent,
        }
    raise KeyError(f"no research card for family {family}")


def validate_cards(families) -> None:
    for family in families:
        card = card_for(family)
        for key in ("question", "mechanism", "sources", "channels", "predicts", "falsified_if", "kind"):
            if not card.get(key):
                raise ValueError(f"card {family} missing {key}")
        for source in card["sources"]:
            if source not in SOURCES:
                raise ValueError(f"card {family} cites unknown source {source}")
        for channel in card["channels"]:
            if channel not in CHANNELS:
                raise ValueError(f"card {family} uses unknown channel {channel}")
