(function () {
  "use strict";

  const NAV = [
    ["leaderboard", "Leaderboard"],
    ["competitions", "Competitions"],
    ["participants", "Participants"],
    ["strategies", "Strategies"],
    ["trades", "Trades"],
    ["markets", "Markets"],
    ["compare", "Compare"],
    ["activity", "Activity"],
    ["flags", "Flags"],
    ["quality", "Data quality"],
    ["sources", "Sources"],
    ["nobel", "Nobel record"],
    ["method", "Method"],
  ];

  const COLORS = ["#9a3412", "#1e3a5f", "#0f6e56", "#6b542c", "#7c3aed", "#9f1239", "#3f6212", "#0e7490", "#a16207", "#44403c", "#be185d"];

  const state = {
    summary: null,
    trades: [],
    tradesFor: "",
    positions: null,
    markets: [],
    results: null,
    comparisons: [],
    flags: null,
    equity: null,
    catalog: null,
    view: "leaderboard",
    arg: "",
    q: "",
    competition: "",
    showAssumptions: false,
    category: "all",
    error: "",
  };

  const main = document.getElementById("main");
  const nav = document.getElementById("nav");

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function num(value) {
    if (value == null || value === "") return "";
    const n = Number(value);
    if (!Number.isFinite(n)) return esc(value);
    const cls = n > 0 ? "pos" : n < 0 ? "neg" : "";
    return `<span class="${cls}">${esc(value)}</span>`;
  }

  function badge(kind, text) {
    return `<span class="badge ${kind}">${esc(text)}</span>`;
  }

  function sim() { return badge("sim", "Simulated"); }
  function official() { return badge("official", "Kalshi"); }
  function live() { return badge("live", "Live snapshot"); }
  function hist() { return badge("hist", "Historical"); }

  async function loadJSON(url) {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(url + " returned " + response.status);
    return response.json();
  }

  async function ensureTrades(id) {
    if (!id) return [];
    if (state.tradesFor === id) return state.trades;
    state.trades = await loadJSON("data/sim/trades_by_competition/" + encodeURIComponent(id) + ".json");
    state.tradesFor = id;
    return state.trades;
  }

  async function ensurePositions() {
    if (state.positions) return state.positions;
    state.positions = await loadJSON("data/sim/positions.json");
    return state.positions;
  }

  async function ensureResults() {
    if (state.results) return state.results;
    state.results = await loadJSON("data/sim/market_results.json");
    return state.results;
  }

  async function ensureFlags() {
    if (state.flags) return state.flags;
    state.flags = await loadJSON("data/sim/flags.json");
    return state.flags;
  }

  async function ensureEquity() {
    if (state.equity) return state.equity;
    state.equity = await loadJSON("data/sim/equity.json");
    return state.equity;
  }

  function parseHash() {
    const raw = (location.hash || "#leaderboard").replace(/^#/, "");
    const [view, arg] = raw.split("/");
    state.view = NAV.some((item) => item[0] === view) || view === "participant" || view === "market" || view === "prize"
      ? view
      : "leaderboard";
    state.arg = arg ? decodeURIComponent(arg) : "";
  }

  function go(hash) {
    if (location.hash === hash) render();
    else location.hash = hash;
  }

  function competitions() {
    return (state.summary && state.summary.competitions) || [];
  }

  function primaryComps() {
    return competitions().filter((comp) => comp.config.primary || state.showAssumptions);
  }

  function selectedCompetition() {
    const rows = competitions();
    return rows.find((comp) => comp.config.competition_id === state.competition) || rows.find((comp) => comp.config.primary) || rows[0];
  }

  function renderNav() {
    const current = ["participant", "market", "prize"].includes(state.view)
      ? (state.view === "prize" ? "nobel" : state.view === "participant" ? "participants" : "markets")
      : state.view;
    nav.innerHTML = NAV.map(([id, label]) =>
      `<a href="#${id}" ${id === current ? 'aria-current="page"' : ""}>${esc(label)}</a>`
    ).join("");
  }

  function nameMatchNote(market) {
    const series = String(market.series_ticker || "");
    const ticker = String(market.ticker || "");
    if (series.indexOf("TRUMPNOBEL") !== -1 || ticker.indexOf("TRUMPNOBEL") !== -1) {
      return `<p class="note">Name match only. This is not the Nobel Peace Prize winner market. Read the contract rules, not the ticker substring.</p>`;
    }
    return "";
  }

  function banner() {
    return `<div class="banner"><strong>Simulated.</strong> Participant names, orders, positions, and P&amp;L are paper trades against stored Kalshi prices. They are not Kalshi users and not exchange fills. A price or result is Kalshi data only when it carries an official source link.</div>`;
  }

  function toolbar() {
    const options = competitions().map((comp) => {
      const id = comp.config.competition_id;
      const mark = comp.config.primary ? "" : " · assumption";
      return `<option value="${esc(id)}" ${id === (selectedCompetition() || {}).config?.competition_id ? "selected" : ""}>${esc(comp.config.title + mark)}</option>`;
    }).join("");
    return `<div class="toolbar">
      <label>Competition<select id="comp">${options}</select></label>
      <label>Search<input id="q" type="search" value="${esc(state.q)}" placeholder="Ticker, name, reason"></label>
      <label>Assumption runs
        <select id="assumptions">
          <option value="hide" ${state.showAssumptions ? "" : "selected"}>Hide</option>
          <option value="show" ${state.showAssumptions ? "selected" : ""}>Show</option>
        </select>
      </label>
    </div>`;
  }

  function bindToolbar() {
    const comp = document.getElementById("comp");
    const q = document.getElementById("q");
    const assumptions = document.getElementById("assumptions");
    if (comp) comp.addEventListener("change", () => { state.competition = comp.value; render(); });
    if (q) q.addEventListener("input", () => { state.q = q.value; render(); });
    if (assumptions) assumptions.addEventListener("change", () => { state.showAssumptions = assumptions.value === "show"; render(); });
  }

  function leaderboardTable(comp) {
    const q = state.q.trim().toLowerCase();
    const rows = comp.leaderboard.filter((row) => !q || `${row.participant_id} ${row.strategy_id}`.toLowerCase().includes(q));
    const body = rows.map((row) => `<tr>
      <td class="num">${esc(displayRank(rows, row))}${rows.filter((other) => other.ending_equity === row.ending_equity).length > 1 ? " tie" : ""}</td>
      <td><a href="#participant/${esc(row.participant_id)}">${esc(row.participant_id)}</a><br><span class="muted small">${esc(row.display_name)} ${sim()}</span></td>
      <td><a href="#strategies">${esc(row.strategy_id)}</a></td>
      <td class="num">${num(row.ending_equity)}</td>
      <td class="num">${num(row.realized_pnl)}</td>
      <td class="num">${num(row.unrealized_pnl)}</td>
      <td class="num">${num(row.fees)}</td>
      <td class="num">${esc(row.trade_count)}</td>
      <td class="num">${row.win_rate_settled == null ? "—" : num(row.win_rate_settled)}</td>
      <td class="num">${num(row.max_drawdown)}</td>
    </tr>`).join("");
    return boardNote(comp) + `<div class="table-wrap"><table>
      <thead><tr>
        <th class="num">Rank</th><th>Participant</th><th>Strategy</th>
        <th class="num">Ending equity</th><th class="num">Realized</th><th class="num">Unrealized</th>
        <th class="num">Fees</th><th class="num">Trades</th><th class="num">Settled win rate</th><th class="num">Max drawdown</th>
      </tr></thead><tbody>${body || `<tr><td colspan="10">No rows.</td></tr>`}</tbody>
    </table></div>`;
  }

  function displayRank(rows, row) {
    const index = rows.findIndex((other) => other.ending_equity === row.ending_equity);
    return index >= 0 ? index + 1 : row.rank;
  }

  function boardNote(comp) {
    const rows = comp.leaderboard || [];
    if (!rows.length || comp.empty_reason) return "";
    const top = rows[0].ending_equity;
    const tied = rows.filter((row) => row.ending_equity === top);
    const bits = [];
    if (tied.length > 1) bits.push(tied.length + " participants share the top equity. Same cash is a tie. Alphabetical order is not a win.");
    if (tied.every((row) => Number(row.trade_count) === 0)) bits.push("The top equity did not place a simulated trade. Unspent cash is the baseline, not a market call.");
    return bits.length ? `<p class="note">${esc(bits.join(" "))}</p>` : "";
  }

  function coverageCard() {
    const nobel = state.markets.filter((market) => market.universe === "nobel" || String(market.series_ticker || "").indexOf("NOBEL") !== -1);
    const settled = nobel.filter((market) => market.result === "yes" || market.result === "no");
    const events = Array.from(new Set(settled.map((market) => market.event_ticker))).sort();
    const yes = settled.filter((market) => market.result === "yes").map((market) => market.ticker + " (" + (market.subtitle || market.title) + ")");
    const series = Array.from(new Set(nobel.map((market) => market.series_ticker)));
    const openOnly = series.filter((name) => !nobel.some((market) => market.series_ticker === name && (market.result === "yes" || market.result === "no")));
    return `<div class="card">
      <h3>What the settled Nobel book does not cover</h3>
      <p>Settled events stored: ${esc(events.join(", ") || "none")}.</p>
      <p>Official yes contracts: ${esc(yes.join("; ") || "none")}. A yes is Kalshi's result field, not a simulated call.</p>
      <p>Series with markets stored but no settled result: ${esc(openOnly.join(", ") || "none")}. That hole is not evidence the prize was not awarded, and no contract was invented to fill it.</p>
      <p class="small">A ticker containing NOBEL can be a name match. KXTRUMPNOBEL is not the Peace Prize winner market.</p>
    </div>`;
  }

  function renderLeaderboard() {
    const comps = primaryComps();
    const stats = state.summary.data_quality || {};
    main.innerHTML = banner() + `
      <h2>Leaderboard</h2>
      <p>Eleven simulated participants, same starting cash, same stored prices. They do not trade with each other. Rank is ending equity: cash plus a liquidation mark at the closing bid. ${sim()}</p>
      <div class="grid">
        <div class="stat"><b>${esc(stats.markets_stored || 0)}</b><span>Kalshi markets stored</span></div>
        <div class="stat"><b>${esc((stats.nobel_series || []).length)}</b><span>Nobel series found</span></div>
        <div class="stat"><b>${esc(stats.fetched_at || "—")}</b><span>Snapshot time (UTC)</span></div>
        <div class="stat"><b>${esc((state.summary.competitions || []).reduce((n, c) => n + Number(c.trade_count || 0), 0))}</b><span>Simulated ledger rows</span></div>
      </div>
      ${toolbar()}
      ${comps.map((comp) => `<section class="card">
        <p>${comp.config.kind === "forward_simulation" ? live() : hist()} ${sim()} ${comp.config.primary ? "" : badge("info", "Assumption run")}</p>
        <h3>${esc(comp.config.title)}</h3>
        <p class="small muted">${esc(comp.config.assumption_note)} Markets used: ${esc(comp.markets_used)}. Starting cash ${esc(comp.config.starting_cash)}.</p>
        ${comp.empty_reason ? `<p class="note">${esc(comp.empty_reason)}</p>` : leaderboardTable(comp)}
      </section>`).join("")}
      ${coverageCard()}
      <p class="small">A blank settled win rate means nothing has settled in that run. Forward ranks are mark-to-market, not a track record.</p>`;
    bindToolbar();
  }

  function renderCompetitions() {
    const body = competitions().map((comp) => `<tr>
      <td><a href="#leaderboard">${esc(comp.config.competition_id)}</a><br><span class="muted small">${esc(comp.config.title)}</span></td>
      <td>${esc(comp.config.kind)} ${comp.config.primary ? badge("official", "Primary") : badge("info", "Assumption")}</td>
      <td>${esc(comp.config.data_tier)}</td>
      <td class="num">${esc(comp.markets_used)}</td>
      <td class="num">${esc(comp.trade_count)}</td>
      <td class="small">${esc(comp.config.assumption_note)}</td>
    </tr>`).join("");
    main.innerHTML = banner() + `<h2>Current simulated competitions</h2>
      <p>Each competition is a separate paper portfolio. Do not add the equities together and call the sum one account.</p>
      <div class="table-wrap"><table><thead><tr>
        <th>Competition</th><th>Kind</th><th>Data tier</th><th class="num">Markets</th><th class="num">Ledger rows</th><th>Rule</th>
      </tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function renderParticipants() {
    const q = state.q.trim().toLowerCase();
    const rows = state.summary.participants.filter((p) => !q || `${p.username} ${p.display_name} ${p.strategy_id}`.toLowerCase().includes(q));
    main.innerHTML = banner() + `<h2>Simulated participants</h2>
      <p>Usernames are invented for the paper competition. ${sim()} ${badge("review", "Not a Kalshi account")}</p>
      ${toolbar()}
      <div class="cards">${rows.map((p) => `<article class="card">
        <h3><a href="#participant/${esc(p.id)}">${esc(p.display_name)}</a></h3>
        <p class="small"><code>${esc(p.username)}</code> · strategy <a href="#strategies">${esc(p.strategy_id)}</a> ${sim()}</p>
        <p class="small">${esc(p.strategy.summary)}</p>
      </article>`).join("")}</div>`;
    bindToolbar();
  }

  async function renderParticipant() {
    const person = (state.summary.participants || []).find((p) => p.id === state.arg);
    if (!person) {
      main.innerHTML = `<p>No simulated participant ${esc(state.arg)}.</p>`;
      return;
    }
    const boards = competitions().map((comp) => {
      const row = comp.leaderboard.find((item) => item.participant_id === person.id);
      if (!row) return "";
      return `<tr>
        <td>${esc(comp.config.competition_id)}<br><span class="muted small">${comp.config.primary ? "primary" : "assumption"}</span></td>
        <td class="num">${esc(row.rank)}</td>
        <td class="num">${num(row.ending_equity)}</td>
        <td class="num">${num(row.realized_pnl)}</td>
        <td class="num">${num(row.unrealized_pnl)}</td>
        <td class="num">${num(row.fees)}</td>
        <td class="num">${esc(row.trade_count)}</td>
        <td class="num">${row.win_rate_settled == null ? "—" : num(row.win_rate_settled)}</td>
        <td class="num">${num(row.max_drawdown)}</td>
      </tr>`;
    }).join("");
    const comp = selectedCompetition();
    let trades = [];
    let positions = [];
    try {
      trades = (await ensureTrades(comp.config.competition_id)).filter((row) => row.participant_id === person.id).slice(0, 80);
      positions = (await ensurePositions()).filter((row) => row.participant_id === person.id && row.competition_id === comp.config.competition_id);
    } catch (err) {
      trades = [];
    }
    main.innerHTML = banner() + `<p><a href="#participants">All participants</a></p>
      <h2>${esc(person.display_name)}</h2>
      <p><code>${esc(person.username)}</code> ${sim()} ${badge("review", "Not a real account")}</p>
      <p>${esc(person.strategy.summary)}</p>
      <h3>Performance by competition</h3>
      <div class="table-wrap"><table><thead><tr>
        <th>Competition</th><th class="num">Rank</th><th class="num">Equity</th><th class="num">Realized</th>
        <th class="num">Unrealized</th><th class="num">Fees</th><th class="num">Trades</th><th class="num">Win rate</th><th class="num">Drawdown</th>
      </tr></thead><tbody>${boards}</tbody></table></div>
      ${toolbar()}
      <h3>Open simulated positions</h3>
      ${positionTable(positions)}
      <h3>Recent simulated ledger rows for the selected competition</h3>
      ${tradeTable(trades)}`;
    bindToolbar();
  }

  function renderStrategies() {
    const cards = state.summary.strategies.map((s) => `<article class="card">
      <h3>${esc(s.name)} <code>${esc(s.id)}</code></h3>
      <p>${esc(s.summary)}</p>
      <p class="small">Parameters: <code>${esc(JSON.stringify(s.parameters))}</code></p>
      <p class="small">Uses: ${esc((s.information_used || []).join("; "))}</p>
      <p class="small">Does not use: ${esc((s.information_not_used || []).join("; "))}</p>
    </article>`).join("");
    main.innerHTML = banner() + `<h2>Strategy descriptions</h2>
      <p>Strategies are separate modules. Adding one does not change stored Kalshi files. Remove one by dropping it from the participant list and rerunning the engine.</p>
      ${cards}`;
  }

  function tradeTable(rows) {
    const body = rows.map((row) => `<tr>
      <td class="small">${esc(row.timestamp || "")}<br><span class="muted">${esc(row.competition_id)}</span></td>
      <td><a href="#participant/${esc(row.participant_id)}">${esc(row.participant_id)}</a><br>${sim()}</td>
      <td><a href="#market/${esc(row.market_ticker)}">${esc(row.market_ticker)}</a><br><span class="muted small">${esc(row.action)} ${esc(row.side)}</span></td>
      <td class="num">${esc(row.price)}</td>
      <td class="num">${esc(row.quantity)}</td>
      <td class="num">${num(row.fee)}</td>
      <td class="num">${num(row.realized_pnl_this_event)}</td>
      <td class="small">${esc(row.reason || "")}<br><span class="muted">Fill source: ${esc(row.fill_price_source || "")}. Outcome at decision: ${row.outcome_known_at_decision ? "yes" : "no"}. Later official result: ${esc(row.later_official_result || "unsettled")} (not used in the decision).</span></td>
    </tr>`).join("");
    return `<div class="table-wrap"><table><thead><tr>
      <th>Time</th><th>Participant</th><th>Market</th><th class="num">Price</th><th class="num">Qty</th>
      <th class="num">Fee</th><th class="num">Realized</th><th>Reason and audit</th>
    </tr></thead><tbody>${body || `<tr><td colspan="8">No simulated trades in this filter.</td></tr>`}</tbody></table></div>`;
  }

  async function renderTrades() {
    const comp = selectedCompetition();
    const id = comp ? comp.config.competition_id : "";
    let loaded = [];
    try { loaded = await ensureTrades(id); } catch (err) { loaded = []; }
    const q = state.q.trim().toLowerCase();
    const rows = loaded.filter((row) => {
      if (!q) return true;
      return `${row.market_ticker} ${row.participant_id} ${row.reason} ${row.strategy_id}`.toLowerCase().includes(q);
    }).slice(0, 300);
    const empty = comp && comp.empty_reason ? `<p class="note">${esc(comp.empty_reason)}</p>` : "";
    main.innerHTML = banner() + `<h2>Simulated trades and settlements</h2>
      <p>Showing up to 300 rows for the selected competition. The full ledger is <a href="data/sim/trades.csv">trades.csv</a>. ${sim()}</p>
      ${toolbar()}
      ${empty}
      ${comp && comp.empty_reason ? "" : tradeTable(rows)}`;
    bindToolbar();
  }

  function positionTable(rows) {
    const body = rows.map((row) => `<tr>
      <td><a href="#participant/${esc(row.participant_id)}">${esc(row.participant_id)}</a> ${sim()}</td>
      <td><a href="#market/${esc(row.market_ticker)}">${esc(row.market_ticker)}</a></td>
      <td>${esc(row.side)} × ${esc(row.quantity)}</td>
      <td class="num">${esc(row.avg_entry_price || "")}</td>
      <td class="num">${num(row.cost_basis)}</td>
      <td class="num">${num(row.liquidation_value)}</td>
      <td class="num">${num(row.unrealized_pnl)}</td>
      <td class="small">${esc(row.liquidation_source || "")}</td>
    </tr>`).join("");
    return `<div class="table-wrap"><table><thead><tr>
      <th>Participant</th><th>Market</th><th>Position</th><th class="num">Avg entry</th>
      <th class="num">Cost</th><th class="num">Liquidation</th><th class="num">Unrealized</th><th>Mark source</th>
    </tr></thead><tbody>${body || `<tr><td colspan="8">No open simulated positions.</td></tr>`}</tbody></table></div>`;
  }

  async function renderMarkets() {
    const comp = selectedCompetition();
    const id = comp ? comp.config.competition_id : "";
    const q = state.q.trim().toLowerCase();
    let results = [];
    try { results = (await ensureResults()).filter((row) => !id || row.competition_id === id); } catch (err) { results = []; }
    const byTicker = new Map(results.map((row) => [row.ticker + "|" + row.competition_id, row]));
    const rows = state.markets.filter((market) => {
      if (!q) return true;
      return `${market.ticker} ${market.title} ${market.subtitle} ${market.rules_primary}`.toLowerCase().includes(q);
    }).slice(0, 250);
    const body = rows.map((market) => {
      const result = byTicker.get(market.ticker + "|" + id);
      const tier = market.tier === "historical" ? hist() : live();
      return `<tr>
        <td><a href="#market/${esc(market.ticker)}">${esc(market.ticker)}</a><br>${tier} ${official()}</td>
        <td>${esc(market.subtitle || market.title)}<br><span class="muted small">${esc(market.series_ticker)} · ${esc(market.status)}</span>${nameMatchNote(market)}</td>
        <td>${esc(market.result || "unsettled")}<br><span class="muted small">official field, not simulated</span></td>
        <td class="num">${esc(market.volume_fp || "")}</td>
        <td class="num">${esc(market.yes_bid_dollars || "")} / ${esc(market.yes_ask_dollars || "")}</td>
        <td class="num">${result ? esc(result.decision_candles) : "0"}</td>
      </tr>`;
    }).join("");
    main.innerHTML = banner() + `<h2>Market information and market-by-market results</h2>
      <p>These rows are Kalshi payloads. Simulated activity is linked from each market. Snapshot quotes are the fetch-time book, which is later than the candle closes used for decisions. ${official()}</p>
      ${toolbar()}
      <div class="table-wrap"><table><thead><tr>
        <th>Ticker</th><th>Contract</th><th>Official result</th><th class="num">Volume</th><th class="num">Fetch-time bid / ask</th><th class="num">Decision candles</th>
      </tr></thead><tbody>${body || `<tr><td colspan="6">No markets stored yet.</td></tr>`}</tbody></table></div>
      <p class="small">List is capped at 250 matches. Download <a href="data/sim/market_index.json">market_index.json</a> for the full stored set.</p>`;
    bindToolbar();
  }

  async function renderMarket() {
    const market = state.markets.find((row) => row.ticker === state.arg);
    if (!market) {
      main.innerHTML = `<p>No stored Kalshi market ${esc(state.arg)}.</p>`;
      return;
    }
    let candles = [];
    try { candles = await loadJSON(`data/sim/candles/${encodeURIComponent(market.ticker)}.json`); } catch (err) { candles = []; }
    let trades = [];
    let results = [];
    try {
      const comp = selectedCompetition();
      trades = (await ensureTrades(comp.config.competition_id)).filter((row) => row.market_ticker === market.ticker);
      results = (await ensureResults()).filter((row) => row.ticker === market.ticker);
    } catch (err) { trades = []; results = []; }
    const sources = (market.settlement_sources || []).map((src) => `<a href="${esc(src.url)}">${esc(src.name)}</a>`).join(", ") || "—";
    main.innerHTML = banner() + `<p><a href="#markets">All markets</a></p>
      <h2>${esc(market.subtitle || market.title)}</h2>
      ${nameMatchNote(market)}
      <p><code>${esc(market.ticker)}</code> ${market.tier === "historical" ? hist() : live()} ${official()} ${sim()} activity is separate below.</p>
      <div class="split">
        <div>
          ${sparkline(candles)}
          <p class="small muted">Closing yes bid (ink) and yes ask (stamp). High and low are stored in the raw candle file and are not used as fill prices.</p>
        </div>
        <div class="card">
          <h3>Official fields</h3>
          <p class="small">Status ${esc(market.status)}. Result <strong>${esc(market.result || "unsettled")}</strong> — this word is Kalshi's, not a simulation.</p>
          <p class="small">Volume ${esc(market.volume_fp || "—")}. Open interest ${esc(market.open_interest_fp || "—")}.</p>
          <p class="small">Fetch-time bid / ask ${esc(market.yes_bid_dollars || "—")} / ${esc(market.yes_ask_dollars || "—")}. Last price ${esc(market.last_price_dollars || "—")}.</p>
          <p class="small">Fee type ${esc(market.fee_type || "—")}, multiplier ${esc(market.fee_multiplier || "—")}.</p>
          <p class="small">Settlement sources: ${sources}</p>
        </div>
      </div>
      <h3>Rules, as fetched</h3>
      <p>${esc(market.rules_primary || "No rules_primary in the stored payload.")}</p>
      <p class="links">
        <a href="${esc(market.source_url)}">API market record</a>
        ${market.candle_source_url ? `<a href="${esc(market.candle_source_url)}">Candlestick request</a>` : ""}
        ${market.contract_url ? `<a href="${esc(market.contract_url)}">Contract certification</a>` : ""}
        ${market.contract_terms_url ? `<a href="${esc(market.contract_terms_url)}">Contract terms</a>` : ""}
        ${market.kalshi_series_url ? `<a href="${esc(market.kalshi_series_url)}">Kalshi site path from ticker</a>` : ""}
      </p>
      <p class="note">The Kalshi website path is derived from the official series ticker. The API URL is the verification link.</p>
      <h3>Simulated activity on this market</h3>
      ${results.map((result) => `<section class="card">
        <h3>${esc(result.competition_id)} ${sim()}</h3>
        <p class="small">${esc(result.result_label)}. Decision candles: ${esc(result.decision_candles)}.</p>
        ${participantResultTable(result)}
      </section>`).join("") || "<p>No competition used this market.</p>"}
      <h3>Ledger rows</h3>
      ${tradeTable(trades.slice(0, 100))}`;
  }

  function participantResultTable(result) {
    const rows = Object.entries(result.participants || {}).map(([pid, row]) => `<tr>
      <td><a href="#participant/${esc(pid)}">${esc(pid)}</a></td>
      <td class="num">${esc(row.trades)}</td>
      <td class="num">${num(row.realized_pnl)}</td>
      <td class="num">${num(row.unrealized_pnl)}</td>
      <td>${esc(row.ending_side || "flat")} ${esc(row.ending_qty || "")}</td>
      <td class="small">${esc((row.reasons || []).filter(Boolean)[0] || "no simulated order")}</td>
    </tr>`).join("");
    return `<div class="table-wrap"><table><thead><tr>
      <th>Participant</th><th class="num">Trades</th><th class="num">Realized</th><th class="num">Unrealized</th><th>End position</th><th>Reason</th>
    </tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function sparkline(candles) {
    const points = (candles || []).filter((c) => c.yes_bid_close || c.yes_ask_close);
    if (points.length < 2) return `<p class="note">No stored candlestick closes to draw.</p>`;
    const w = 640, h = 180, pad = 16;
    const values = points.flatMap((c) => [Number(c.yes_bid_close || 0), Number(c.yes_ask_close || 0)]);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 1);
    const x = (i) => pad + (i * (w - pad * 2)) / (points.length - 1);
    const y = (v) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);
    const path = (key) => points.map((c, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(Number(c[key] || 0)).toFixed(1)}`).join(" ");
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Closing bid and ask">
      <path d="${path("yes_bid_close")}" fill="none" stroke="#1b1914" stroke-width="1.6"/>
      <path d="${path("yes_ask_close")}" fill="none" stroke="#9a3412" stroke-width="1.6"/>
    </svg>`;
  }

  function renderCompare() {
    const rows = state.comparisons || [];
    const ids = (state.summary.participants || []).map((p) => p.id);
    const header = rows.map((comp) => `<th class="num">${esc(comp.competition_id)}</th>`).join("");
    const body = ids.map((pid) => {
      const cells = rows.map((comp) => {
        const row = (comp.leaderboard || []).find((item) => item.participant_id === pid);
        return `<td class="num">${row ? num(row.ending_equity) : "—"}</td>`;
      }).join("");
      return `<tr><td><a href="#participant/${esc(pid)}">${esc(pid)}</a></td>${cells}</tr>`;
    }).join("");
    const notes = rows.map((comp) => `<li><strong>${esc(comp.competition_id)}</strong> ${comp.primary ? badge("official", "Primary") : badge("info", "Assumption")}: ${esc(comp.assumption_note)}</li>`).join("");
    main.innerHTML = banner() + `<h2>Strategy comparison and assumption sensitivity</h2>
      <p>Same participants. Different columns are different rules or different market sets. A change in rank between a primary column and an assumption column is the sensitivity result. ${sim()}</p>
      <div class="table-wrap"><table><thead><tr><th>Participant</th>${header}</tr></thead><tbody>${body}</tbody></table></div>
      <h3>What each column changed</h3>
      <ul class="clean">${notes}</ul>
      <div class="card">
        <h3>Questions this table is meant to answer</h3>
        <ul class="clean">${(state.summary.research_questions || []).map((q) => `<li><a href="#${esc(q.view)}">${esc(q.question)}</a></li>`).join("")}</ul>
      </div>`;
  }

  async function renderActivity() {
    const comp = selectedCompetition();
    const id = comp ? comp.config.competition_id : "";
    let equity = [];
    let trades = [];
    try {
      equity = await ensureEquity();
      trades = await ensureTrades(id);
    } catch (err) { equity = []; trades = []; }
    const series = {};
    equity.filter((point) => point.competition_id === id && point.timestamp_unix).forEach((point) => {
      (series[point.participant_id] = series[point.participant_id] || []).push(point);
    });
    const ids = Object.keys(series);
    const legend = ids.map((pid, i) => `<span><i class="swatch" style="background:${COLORS[i % COLORS.length]}"></i>${esc(pid)}</span>`).join("");
    main.innerHTML = banner() + `<h2>Strategy activity over time</h2>
      <p>Equity after simulated fills and settlements. The final liquidation mark is not on this clock if it has no timestamp. ${sim()}</p>
      ${toolbar()}
      ${equityChart(series, ids)}
      <div class="legend">${legend}</div>
      <h3>Simulated trades by day</h3>
      ${activityTable(trades)}`;
    bindToolbar();
  }

  function equityChart(series, ids) {
    const all = ids.flatMap((pid) => series[pid]);
    if (all.length < 2) return `<p class="note">No timestamped equity points for this competition yet.</p>`;
    const w = 960, h = 220, pad = 28;
    const minT = Math.min(...all.map((p) => p.timestamp_unix));
    const maxT = Math.max(...all.map((p) => p.timestamp_unix));
    const values = all.map((p) => Number(p.equity));
    const minV = Math.min(...values, 10000);
    const maxV = Math.max(...values, 10000);
    const x = (t) => pad + ((t - minT) / (maxT - minT || 1)) * (w - pad * 2);
    const y = (v) => h - pad - ((v - minV) / (maxV - minV || 1)) * (h - pad * 2);
    const paths = ids.map((pid, i) => {
      const pts = series[pid].slice().sort((a, b) => a.timestamp_unix - b.timestamp_unix);
      const d = pts.map((p, idx) => `${idx ? "L" : "M"}${x(p.timestamp_unix).toFixed(1)},${y(Number(p.equity)).toFixed(1)}`).join(" ");
      return `<path d="${d}" fill="none" stroke="${COLORS[i % COLORS.length]}" stroke-width="1.5"/>`;
    }).join("");
    return `<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Simulated equity">${paths}</svg>`;
  }

  function activityTable(trades) {
    const counts = {};
    (trades || []).filter((row) => row.timestamp).forEach((row) => {
      const day = row.timestamp.slice(0, 10);
      const key = day + "|" + row.strategy_id;
      counts[key] = (counts[key] || 0) + 1;
    });
    const rows = Object.entries(counts).sort().slice(-80).map(([key, count]) => {
      const [day, strategy] = key.split("|");
      return `<tr><td>${esc(day)}</td><td>${esc(strategy)}</td><td class="num">${esc(count)}</td></tr>`;
    }).join("");
    return `<div class="table-wrap"><table><thead><tr><th>Day (UTC)</th><th>Strategy</th><th class="num">Ledger rows</th></tr></thead><tbody>${rows || `<tr><td colspan="3">No timestamped simulated trades.</td></tr>`}</tbody></table></div>`;
  }

  async function renderFlags() {
    const q = state.q.trim().toLowerCase();
    let flags = [];
    try { flags = await ensureFlags(); } catch (err) { flags = []; }
    const rows = flags.filter((flag) => !q || JSON.stringify(flag).toLowerCase().includes(q)).slice(0, 400);
    const body = rows.map((flag) => `<tr>
      <td>${badge(flag.severity === "review" || flag.severity === "integrity" ? "review" : "info", flag.severity || "info")}</td>
      <td><code>${esc(flag.code || "")}</code></td>
      <td class="small">${esc(flag.message || "")}</td>
      <td>${flag.market_ticker ? `<a href="#market/${esc(flag.market_ticker)}">${esc(flag.market_ticker)}</a>` : ""}</td>
      <td class="small">${esc(flag.competition_id || "")}</td>
    </tr>`).join("");
    main.innerHTML = banner() + `<h2>Flags and irregularities</h2>
      <p>Review flags are not corrections. They mark a gap, a wide book, a failed request, or a fee type the engine did not treat as a plain quadratic taker fee.</p>
      ${toolbar()}
      <div class="table-wrap"><table><thead><tr><th>Severity</th><th>Code</th><th>Message</th><th>Market</th><th>Competition</th></tr></thead><tbody>${body || `<tr><td colspan="5">No flags.</td></tr>`}</tbody></table></div>`;
    bindToolbar();
  }

  function renderQuality() {
    const q = state.summary.data_quality || {};
    const exchange = q.exchange_status || {};
    main.innerHTML = banner() + `<h2>Data-quality status</h2>
      <div class="grid">
        <div class="stat"><b>${esc(q.status || "—")}</b><span>Bundle status</span></div>
        <div class="stat"><b>${esc(q.markets_stored || 0)}</b><span>Markets stored</span></div>
        <div class="stat"><b>${esc(q.markets_with_candle_responses || 0)}</b><span>Candle responses OK</span></div>
        <div class="stat"><b>${esc(q.collection_failures || 0)}</b><span>Collection failures</span></div>
      </div>
      <div class="card">
        <h3>Snapshot</h3>
        <p>Fetched at ${esc(q.fetched_at || "—")}. Exchange active: ${esc(String(exchange.exchange_active))}. Trading active: ${esc(String(exchange.trading_active))}.</p>
        <p class="small">Historical cutoff: <code>${esc(JSON.stringify(q.historical_cutoff || {}))}</code></p>
        <p>Nobel series: ${esc((q.nobel_series || []).join(", ") || "none")}.</p>
        <p>Panel series: ${esc((q.panel_series || []).join(", ") || "none")}. Kept: <code>${esc(JSON.stringify(q.panel_kept || {}))}</code></p>
        <p>Universes simulated: <code>${esc(JSON.stringify(q.universes || {}))}</code></p>
      </div>
      ${coverageCard()}
      <div class="card">
        <h3>Scope, so the gaps are visible</h3>
        <p>${esc((q.scope || {}).nobel || "")}</p>
        <p>${esc((q.scope || {}).panel || "")}</p>
        <p>${esc((q.scope || {}).not_invented || "")}</p>
      </div>
      <div class="card">
        <h3>Reproduction</h3>
        <p>Input SHA-256 of <code>data/kalshi/markets.jsonl</code>: <code>${esc(state.summary.input_sha256 || "")}</code></p>
        <p class="small">Engine ${esc(state.summary.engine_version)}. Build reruns every competition before writing and refuses a ledger that does not match. Replay: ${esc((state.summary.replay || {}).status || "not recorded")} ${esc((state.summary.replay || {}).ledger_sha256 || "")}.</p>
      </div>
      <p class="links"><a href="data/kalshi/manifest.json">manifest.json</a> <a href="data/kalshi/failures.json">failures.json</a> <a href="data/kalshi/SCHEMA.md">field sources</a></p>`;
  }

  function renderSources() {
    const rows = (state.summary.sources || []).map((src) => `<tr>
      <td><a href="${esc(src.url)}">${esc(src.name)}</a></td>
      <td>${esc(src.role)}</td>
      <td class="small"><a href="${esc(src.url)}">${esc(src.url)}</a></td>
    </tr>`).join("");
    main.innerHTML = banner() + `<h2>Source information and verification links</h2>
      <div class="table-wrap"><table><thead><tr><th>Source</th><th>Role</th><th>URL</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="card">
        <h3>Where to check a line</h3>
        <ul class="clean">
          <li>A Kalshi market: the API URL on its market page, plus <a href="data/kalshi/markets.jsonl">markets.jsonl</a>.</li>
          <li>A simulated trade: <a href="data/sim/trades.csv">trades.csv</a>. The candle close it used is on the row. The later result is labeled as unused at decision time.</li>
          <li>A Nobel prize: the summary, API, and nomination-list links on the prize page. Row files: <a href="data/nobel/prizes.csv">prizes.csv</a>, <a href="data/nobel/laureates.csv">laureates.csv</a>, <a href="data/nobel/nominations.csv">nominations.csv</a>.</li>
          <li>Flags that still need a person: <a href="data/nobel/FLAGS.md">Nobel FLAGS.md</a> and the Flags view.</li>
        </ul>
      </div>`;
  }

  async function ensureCatalog() {
    if (state.catalog) return;
    state.catalog = await loadJSON("data/nobel/catalog.json");
  }

  async function renderNobel() {
    main.innerHTML = `<p class="loading">Loading the Nobel catalog…</p>`;
    try {
      await ensureCatalog();
    } catch (err) {
      main.innerHTML = `<p>The Nobel catalog did not load. ${esc(err.message)}</p>`;
      return;
    }
    const meta = state.catalog.meta || {};
    const counts = meta.counts || {};
    const categories = state.catalog.categories || [];
    const q = state.q.trim().toLowerCase();
    const prizes = state.catalog.prizes.filter((prize) => {
      if (state.category !== "all" && prize.category !== state.category) return false;
      if (!q) return true;
      const names = (prize.laureates || []).map((row) => row.displayName).join(" ");
      const nominees = ((prize.nomination || {}).nominees || []).map((row) => row.name).join(" ");
      return `${prize.year} ${prize.categoryLabel} ${prize.overallMotivation || ""} ${names} ${nominees}`.toLowerCase().includes(q);
    });
    const chips = [`<button class="ghost" data-cat="all" type="button">All</button>`].concat(categories.map((cat) =>
      `<button class="ghost" data-cat="${esc(cat.id)}" type="button">${esc(cat.label)}</button>`
    )).join("");
    main.innerHTML = `
      <div class="banner"><strong>Official record, not a ranking.</strong> Motivations are the published reason. Nomination names are included only where a nomination-archive list was stored. Sealed years are empty on purpose.</div>
      <h2>Nobel Prize record</h2>
      <p class="small">Independent copy for this project. Not endorsed by Nobel Prize Outreach. Counts: ${esc(counts.prizeRecords)} prize records, ${esc(counts.awardedPrizeRecords)} awarded, ${esc(counts.unawardedPrizeRecords)} not awarded, ${esc(counts.laureateEntities)} laureates. Latest year in the file: ${esc(meta.latestAwardYearInSources)}. <a href="https://buffedlizard55-lab.github.io/NOBEL-PRIZE/">Earlier Nobel desk</a>.</p>
      <div class="toolbar">
        <label>Search<input id="q" type="search" value="${esc(state.q)}" placeholder="Name, year, motivation"></label>
        <div>${chips}</div>
      </div>
      <p class="muted small">${prizes.length} prize records match. ${state.category === "all" && !q ? "Showing the latest 40. Search or filter to narrow." : ""}</p>
      ${(q || state.category !== "all" ? prizes : prizes.slice(0, 40)).map(prizeCard).join("")}
      <p class="links"><a href="data/nobel/prizes.csv">prizes.csv</a> <a href="data/nobel/laureates.csv">laureates.csv</a> <a href="data/nobel/nominations.csv">nominations.csv</a> <a href="data/nobel/FLAGS.md">FLAGS.md</a> <a href="data/nobel/PROVENANCE.md">Provenance</a></p>`;
    document.getElementById("q").addEventListener("input", (event) => { state.q = event.target.value; render(); });
    main.querySelectorAll("[data-cat]").forEach((button) => button.addEventListener("click", () => {
      state.category = button.getAttribute("data-cat");
      render();
    }));
  }

  function prizeCard(prize) {
    const names = (prize.laureates || []).map((row) => row.displayName).join(", ") || "Not awarded";
    const nom = prize.nomination || {};
    return `<article class="prize">
      <p class="small muted">${esc(prize.year)} · ${esc(prize.categoryFullName)} ${prize.inAlfredNobelsWill ? "" : "· not in Alfred Nobel’s will"}</p>
      <h3><a href="#prize/${esc(prize.key)}">${esc(names)}</a></h3>
      <p class="quote">${esc(prize.overallMotivation || (prize.laureates || []).map((row) => row.motivation).filter(Boolean)[0] || "No motivation text in the API record.")}</p>
      <p class="small">${badge(nom.status === "ingested" ? "official" : "info", nom.status || "nomination unknown")} ${nom.statedCount != null ? esc(nom.statedCount) + " stated nominations" : ""}</p>
    </article>`;
  }

  async function renderPrize() {
    main.innerHTML = `<p class="loading">Loading the prize…</p>`;
    try { await ensureCatalog(); } catch (err) {
      main.innerHTML = `<p>${esc(err.message)}</p>`;
      return;
    }
    const prize = state.catalog.prizes.find((row) => row.key === state.arg);
    if (!prize) {
      main.innerHTML = `<p>No prize ${esc(state.arg)}.</p>`;
      return;
    }
    const laureates = (prize.laureates || []).map((row) => `<li>
      <strong>${esc(row.displayName)}</strong> · portion ${esc(row.portion || "")} · status ${esc(row.prizeStatus || "")}
      <br>${esc(row.motivation || "")}
      <br><span class="muted small">${esc((row.affiliations || []).join("; "))}</span>
      <br><a href="${esc(row.factsUrl || "")}">Facts</a> · <a href="${esc(row.apiUrl || "")}">API</a>
    </li>`).join("");
    const nominees = ((prize.nomination || {}).nominees || []).map((row) => `<li>
      <a href="${esc(row.url)}">${esc(row.name)}</a> · ${esc(row.nominations)} nomination record${row.nominations === 1 ? "" : "s"}
    </li>`).join("");
    const flags = (state.catalog.flags || []).filter((flag) => flag.prizeKey === prize.key).slice(0, 12);
    main.innerHTML = `<p><a href="#nobel">All prizes</a></p>
      <h2>${esc(prize.categoryFullName)} ${esc(prize.year)}</h2>
      <p>${prize.awarded ? badge("official", "Awarded") : badge("info", "Not awarded")} ${prize.inAlfredNobelsWill ? "" : badge("hist", "Not in the will")}</p>
      <p class="quote">${esc(prize.overallMotivation || "No overall motivation in the API record.")}</p>
      <p class="small">Date awarded ${esc(prize.dateAwarded || "—")}. Amount ${esc(prize.prizeAmount || "—")} ${esc(prize.currency || "SEK")}. Adjusted amount ${esc(prize.prizeAmountAdjusted || "—")}.</p>
      <h3>Laureates</h3>
      <ul class="clean">${laureates || "<li>None in the API record.</li>"}</ul>
      <h3>Why this project, and who else was named</h3>
      <p>${esc((prize.selection || {}).statement || "")}</p>
      <p class="small">Nomination status: <strong>${esc((prize.nomination || {}).status)}</strong>. ${esc((prize.nomination || {}).note || "")}</p>
      ${nominees ? `<ul class="clean">${nominees}</ul><p class="note">A nomination is not a vote and is not a published ranking. Counts are how many stored nomination records name that person or organization for this year and subject.</p>` : `<p class="note">No nominee names are stored for this prize. That is a seal, a missing page, or a category the public archive does not cover. Names were not guessed.</p>`}
      <p class="links">
        <a href="${esc(prize.links.summary)}">Official summary</a>
        <a href="${esc(prize.links.apiPrize)}">API record</a>
        <a href="${esc(prize.links.nominationList)}">Nomination list</a>
        <a href="${esc(prize.links.categoryList)}">Category list</a>
      </p>
      ${flags.length ? `<h3>Flags on this prize</h3><ul class="clean">${flags.map((flag) => `<li>${esc(flag.code)}: ${esc(flag.message)}</li>`).join("")}</ul>` : ""}`;
  }

  function renderMethod() {
    main.innerHTML = `<h2>Method</h2>
      <div class="card">
        <h3>Two layers, kept apart</h3>
        <p>The Nobel layer is an archive of official prize and nomination records. The competition layer is a paper simulation on stored Kalshi quotes. A simulated fill is never shown as a Kalshi trade. A Kalshi result is never shown as something a strategy knew early.</p>
      </div>
      <div class="card">
        <h3>Decision clock</h3>
        <p>A strategy at candle end T sees only that market's candles with <code>end_period_ts &lt;= T</code>, and only if T is before <code>settlement_ts</code>. Fills use the closing bid or ask, not the high or low inside the bar. The official result is attached after the decision loop and labeled unused.</p>
        <p>Participants do not share an order book. Comparing them is the competition. Inventing trades between them would invent prices.</p>
      </div>
      <div class="card">
        <h3>Fees</h3>
        <p>The market payload has <code>fee_type</code> and <code>fee_multiplier</code>. It does not include the 0.07 coefficient. The <a href="https://kalshi.com/fee-schedule">fee schedule</a> retrieved 2026-09-24 lists most markets at multiplier 1 with a taker range of $0.07–$1.75 per 100 contracts. The engine uses round-up-to-cent of multiplier × 0.07 × contracts × price × (1 − price), which matches that range at 1 cent and at 50 cents. Fee-off runs are on the Compare page so the interpretation is not hidden inside the rank.</p>
      </div>
      <div class="card">
        <h3>What was refused</h3>
        <ul class="clean">
          <li>No guessed nominees for sealed years.</li>
          <li>No filled-in Kalshi history when an endpoint failed or a candle had no price.</li>
          <li>No use of the fetch-time order book as if it had been the book at an earlier decision.</li>
          <li>No claim that this panel is the whole Kalshi exchange. The scope is in Data quality.</li>
        </ul>
      </div>
      <p><a href="docs/METHOD.md">Full method note</a> · <a href="LIMITATIONS.md">Limitations for the next session</a></p>`;
  }

  function renderMissing(err) {
    main.innerHTML = `<div class="banner"><strong>Competition snapshot not in this checkout yet.</strong> ${esc(err.message)}</div>
      <h2>Leaderboard</h2>
      <p>The paper competition is built from a stored Kalshi snapshot. This page will show it as soon as <code>data/sim/summary.json</code> is present. The collector is <code>python scripts/refresh.py</code>. It uses the public Trade API and does not invent prices when a request fails.</p>
      <p>The Nobel record is already in the repository.</p>
      <p class="links"><a href="#nobel">Open the Nobel record</a> <a href="docs/METHOD.md">Method</a> <a href="LIMITATIONS.md">Limitations</a></p>`;
    state.view = "missing";
  }

  async function render() {
    parseHash();
    renderNav();
    if (!state.summary && state.view !== "nobel" && state.view !== "prize" && state.view !== "method") {
      renderMissing(new Error(state.error || "summary.json is not loaded"));
      if (state.view === "nobel" || state.view === "prize") return;
      if (location.hash.includes("nobel") || location.hash.includes("prize") || location.hash.includes("method")) {
        /* fall through only when those views are requested */
      } else return;
    }
    if (state.view === "nobel") return renderNobel();
    if (state.view === "prize") return renderPrize();
    if (state.view === "method") return renderMethod();
    if (!state.summary) return;
    if (!state.competition) {
      const first = competitions().find((comp) => comp.config.primary) || competitions()[0];
      state.competition = first ? first.config.competition_id : "";
    }
    if (state.view === "leaderboard") return renderLeaderboard();
    if (state.view === "competitions") return renderCompetitions();
    if (state.view === "participants") return renderParticipants();
    if (state.view === "participant") return renderParticipant();
    if (state.view === "strategies") return renderStrategies();
    if (state.view === "trades") return renderTrades();
    if (state.view === "markets") return renderMarkets();
    if (state.view === "market") return renderMarket();
    if (state.view === "compare") return renderCompare();
    if (state.view === "activity") return renderActivity();
    if (state.view === "flags") return renderFlags();
    if (state.view === "quality") return renderQuality();
    if (state.view === "sources") return renderSources();
    renderLeaderboard();
  }

  async function boot() {
    renderNav();
    try {
      const [summary, markets, comparisons] = await Promise.all([
        loadJSON("data/sim/summary.json"),
        loadJSON("data/sim/market_index.json"),
        loadJSON("data/sim/comparisons.json"),
      ]);
      state.summary = summary;
      state.markets = markets;
      state.comparisons = comparisons;
    } catch (err) {
      state.error = err.message;
    }
    window.addEventListener("hashchange", render);
    render();
  }

  boot();
})();
