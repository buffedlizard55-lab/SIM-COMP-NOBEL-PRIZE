"""Verified literature and official documentation behind the research program.

Every entry was opened on the verification date (publisher page, DOI landing
page, SSRN/arXiv abstract page, or official Kalshi documentation) and the
``claim_used`` field paraphrases only what that page's abstract or text states.
A strategy family that cites a source is testing an idea *suggested by* that
source on this project's Kalshi snapshot. It is not a replication of the paper,
and the paper's result is not evidence for the simulated result.

Families whose rule has no academic source (for example a Bollinger-style band)
cite ``none-technical-rule`` and say so on the site.
"""

from __future__ import annotations

VERIFIED_ON = "2026-09-24"

SOURCES: dict[str, dict] = {
    "burgi-deng-whelan-2025": {
        "citation": "Bürgi, C., Deng, W., & Whelan, K. (2025). Makers and Takers: The Economics of the Kalshi Prediction Market. CESifo Working Paper No. 12122; CEPR Discussion Paper No. 20631.",
        "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5502658",
        "also": ["https://cepr.org/voxeu/columns/economics-kalshi-prediction-market"],
        "doi": "10.2139/ssrn.5502658",
        "claim_used": (
            "On Kalshi, prices are informative and become more accurate as markets approach closing, "
            "but show a favorite-longshot bias: low-price contracts win far less often than needed to "
            "break even; high-price contracts win more often and earn small positive returns. Takers "
            "lose more than makers."
        ),
    },
    "page-clemen-2013": {
        "citation": "Page, L., & Clemen, R. T. (2013). Do Prediction Markets Produce Well-Calibrated Probability Forecasts? The Economic Journal, 123(568), 491-513.",
        "url": "https://doi.org/10.1111/j.1468-0297.2012.02561.x",
        "doi": "10.1111/j.1468-0297.2012.02561.x",
        "claim_used": (
            "Prediction markets are reasonably well calibrated when time to expiration is short, but "
            "prices are significantly biased (favourite/longshot direction) for events farther in the future."
        ),
    },
    "snowberg-wolfers-2010": {
        "citation": "Snowberg, E., & Wolfers, J. (2010). Explaining the Favorite-Long Shot Bias: Is it Risk-Love or Misperceptions? Journal of Political Economy, 118(4), 723-746.",
        "url": "https://ideas.repec.org/a/ucp/jpolec/v118y2010i4p723-746.html",
        "doi": "10.1086/655844",
        "claim_used": (
            "Long shots are overbet and favorites underbet in betting markets; the evidence favors "
            "misperception of probabilities (as in prospect theory) over risk-love."
        ),
    },
    "thaler-ziemba-1988": {
        "citation": "Thaler, R. H., & Ziemba, W. T. (1988). Anomalies: Parimutuel Betting Markets: Racetracks and Lotteries. Journal of Economic Perspectives, 2(2), 161-174.",
        "url": "https://www.aeaweb.org/articles?id=10.1257/jep.2.2.161",
        "doi": "10.1257/jep.2.2.161",
        "claim_used": "Survey of wagering-market anomalies, including racetrack betting, despite conditions (quick, repeated feedback) that should favor efficiency.",
    },
    "kahneman-tversky-1979": {
        "citation": "Kahneman, D., & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. Econometrica, 47(2), 263-292.",
        "url": "https://www.jstor.org/stable/1914185",
        "claim_used": "Decision weights are non-linear in probability; small probabilities are overweighted.",
    },
    "prelec-1998": {
        "citation": "Prelec, D. (1998). The Probability Weighting Function. Econometrica, 66(3), 497-527.",
        "url": "https://www.jstor.org/stable/2998573",
        "doi": "10.2307/2998573",
        "claim_used": "Empirical probability weighting w(p) is regressive (w(p) > p for small p, < p for large p), s-shaped, and crosses the diagonal near 1/3.",
    },
    "manski-2006": {
        "citation": "Manski, C. F. (2006). Interpreting the predictions of prediction markets. Economics Letters, 91(3), 425-429.",
        "url": "https://doi.org/10.1016/j.econlet.2006.01.004",
        "doi": "10.1016/j.econlet.2006.01.004",
        "claim_used": "With heterogeneous beliefs, a contract's price is a quantile of the budget-weighted belief distribution, not the mean belief; prices should not be read loosely as probabilities.",
    },
    "wolfers-zitzewitz-2004": {
        "citation": "Wolfers, J., & Zitzewitz, E. (2004). Prediction Markets. Journal of Economic Perspectives, 18(2), 107-126.",
        "url": "https://www.aeaweb.org/articles?id=10.1257/0895330041371321",
        "doi": "10.1257/0895330041371321",
        "claim_used": "Market-generated forecasts are typically fairly accurate and outperform most moderately sophisticated benchmarks; contract design determines what a price reveals.",
    },
    "tetlock-2008-liquidity": {
        "citation": "Tetlock, P. C. (2008). Liquidity and Prediction Market Efficiency. SSRN Working Paper 929916.",
        "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=929916",
        "doi": "10.2139/ssrn.929916",
        "claim_used": "Cited (Science 2008 'The Promise of Prediction Markets' and later work) for the finding that more liquidity does not necessarily mean better-calibrated prices on TradeSports.",
    },
    "saguillo-2025-arbitrage": {
        "citation": "Saguillo, O., Ghafouri, V., Kiffer, L., & Suarez-Tangil, G. (2025). Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets. arXiv:2508.03474.",
        "url": "https://arxiv.org/abs/2508.03474",
        "doi": "10.48550/arXiv.2508.03474",
        "claim_used": "In exhaustive, mutually exclusive condition sets, collective prices should sum to $1; Polymarket shows rebalancing mispricings where the set can be bought for less (or sold for more) than $1.",
    },
    "shleifer-vishny-1997": {
        "citation": "Shleifer, A., & Vishny, R. W. (1997). The Limits of Arbitrage. Journal of Finance, 52(1), 35-55.",
        "url": "https://doi.org/10.1111/j.1540-6261.1997.tb03807.x",
        "doi": "10.1111/j.1540-6261.1997.tb03807.x",
        "claim_used": "Arbitrage is limited in practice: it requires capital and bears risk, so identified mispricings need not be corrected.",
    },
    "rothschild-sethi-2016": {
        "citation": "Rothschild, D., & Sethi, R. (2016). Trading Strategies and Market Microstructure: Evidence from a Prediction Market. The Journal of Prediction Markets, 10(1).",
        "url": "https://doi.org/10.5750/jpm.v10i1.1179",
        "doi": "10.5750/jpm.v10i1.1179",
        "claim_used": "Intrade's 2012 presidential market showed a diverse ecology of strategies, from arbitrage with fleeting exposure to large directional positions.",
    },
    "glosten-milgrom-1985": {
        "citation": "Glosten, L. R., & Milgrom, P. R. (1985). Bid, ask and transaction prices in a specialist market with heterogeneously informed traders. Journal of Financial Economics, 14(1), 71-100.",
        "url": "https://doi.org/10.1016/0304-405X(85)90044-3",
        "doi": "10.1016/0304-405X(85)90044-3",
        "claim_used": "Informed traders produce a positive bid-ask spread; a spread implies a gap between observed and realizable returns.",
    },
    "gervais-kaniel-mingelgrin-2001": {
        "citation": "Gervais, S., Kaniel, R., & Mingelgrin, D. H. (2001). The High-Volume Return Premium. Journal of Finance, 56(3), 877-919.",
        "url": "https://doi.org/10.1111/0022-1082.00349",
        "doi": "10.1111/0022-1082.00349",
        "claim_used": "Stocks with unusually high (low) trading volume over a day or week tend to appreciate (depreciate) over the following month, consistent with a visibility effect.",
    },
    "de-bondt-thaler-1985": {
        "citation": "De Bondt, W. F. M., & Thaler, R. (1985). Does the Stock Market Overreact? Journal of Finance, 40(3), 793-805.",
        "url": "https://doi.org/10.1111/j.1540-6261.1985.tb05004.x",
        "doi": "10.1111/j.1540-6261.1985.tb05004.x",
        "claim_used": "Extreme price movements tend to be followed by movements in the opposite direction, and more extreme moves by larger reversals.",
    },
    "jegadeesh-1990": {
        "citation": "Jegadeesh, N. (1990). Evidence of Predictable Behavior of Security Returns. Journal of Finance, 45(3), 881-898.",
        "url": "https://doi.org/10.1111/j.1540-6261.1990.tb05110.x",
        "doi": "10.1111/j.1540-6261.1990.tb05110.x",
        "claim_used": "Negative first-order serial correlation in monthly stock returns (short-horizon reversal); positive correlation at longer lags.",
    },
    "jegadeesh-titman-1993": {
        "citation": "Jegadeesh, N., & Titman, S. (1993). Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency. Journal of Finance, 48(1), 65-91.",
        "url": "https://doi.org/10.1111/j.1540-6261.1993.tb04702.x",
        "doi": "10.1111/j.1540-6261.1993.tb04702.x",
        "claim_used": "Buying past winners and selling past losers earned positive returns over 3-12 month holding periods (cross-sectional momentum).",
    },
    "moskowitz-ooi-pedersen-2012": {
        "citation": "Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. Journal of Financial Economics, 104(2), 228-250.",
        "url": "https://doi.org/10.1016/j.jfineco.2011.11.003",
        "doi": "10.1016/j.jfineco.2011.11.003",
        "claim_used": "An instrument's own past 12-month return predicts its next-month return across 58 liquid futures; partial reversal at longer horizons.",
    },
    "french-1980": {
        "citation": "French, K. R. (1980). Stock returns and the weekend effect. Journal of Financial Economics, 8(1), 55-69.",
        "url": "https://doi.org/10.1016/0304-405X(80)90021-5",
        "doi": "10.1016/0304-405X(80)90021-5",
        "claim_used": "Documented calendar (weekend) regularities in stock returns.",
    },
    "kelly-1956": {
        "citation": "Kelly, J. L. (1956). A New Interpretation of Information Rate. Bell System Technical Journal, 35(4), 917-926.",
        "url": "https://doi.org/10.1002/j.1538-7305.1956.tb03809.x",
        "doi": "10.1002/j.1538-7305.1956.tb03809.x",
        "claim_used": "Growth-optimal bet sizing for a gambler with an information edge (the Kelly criterion).",
    },
    "bailey-lopez-de-prado-2014": {
        "citation": "Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. Journal of Portfolio Management, 40(5), 94-107.",
        "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551",
        "claim_used": "Not controlling for the number of trials behind a discovery leads to over-optimistic performance expectations (selection bias under multiple testing).",
    },
    "harvey-liu-zhu-2016": {
        "citation": "Harvey, C. R., Liu, Y., & Zhu, H. (2016). ...and the Cross-Section of Expected Returns. Review of Financial Studies, 29(1), 5-68.",
        "url": "https://doi.org/10.1093/rfs/hhv059",
        "doi": "10.1093/rfs/hhv059",
        "claim_used": "After hundreds of tested factors, the usual significance bar is too lenient; a multiple-testing-adjusted threshold is required.",
    },
    "kalshi-get-event": {
        "citation": "Kalshi API documentation: Get Event (fields mutually_exclusive, strike_date, markets).",
        "url": "https://docs.kalshi.com/api-reference/events/get-event",
        "claim_used": "The event object publishes mutually_exclusive and strike_date; used for event grouping and the scheduled clock.",
    },
    "kalshi-historical-data": {
        "citation": "Kalshi API documentation: Historical Data (live/historical cutoff).",
        "url": "https://docs.kalshi.com/getting_started/historical_data",
        "claim_used": "Settled markets older than market_settled_ts are only on /historical/markets; GET /events nested markets older than the cutoff are not included.",
    },
    "kalshi-fee-schedule": {
        "citation": "Kalshi fee schedule.",
        "url": "https://kalshi.com/fee-schedule",
        "claim_used": "Most markets: taker fee range $0.07-$1.75 per 100 contracts, multiplier 1 (the range this project reads as a quadratic taker fee).",
    },
    "none-technical-rule": {
        "citation": "No academic source. A technical or folk trading rule tested for completeness.",
        "url": "",
        "claim_used": "None. The family is included as a comparison point, not because any literature supports it.",
    },
    "none-design-control": {
        "citation": "No external source. A design control built by this project (placebo, null, or ablation).",
        "url": "",
        "claim_used": "None. Controls exist to separate a rule's side choice, timing, or information from luck.",
    },
}


def source_ids() -> set[str]:
    return set(SOURCES)
