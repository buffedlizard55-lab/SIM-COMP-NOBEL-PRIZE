(function () {
  "use strict";

  const NAV = [
    ["leaderboard", "Leaderboard"],
    ["board", "Program board"],
    ["research", "Research"],
    ["program", "Program"],
    ["families", "Families"],
    ["topics", "Topics"],
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

  const PROGRAM_UNIVERSES = [
    ["nobel_settled", "Settled Nobel", "historical backtest"],
    ["panel_settled", "Settled panel", "historical backtest"],
    ["nobel_forward", "Forward Nobel", "forward mark, unsettled"],
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
    pManifest: null,
    pBoard: null,
    pFamilies: null,
    pPeople: null,
    pBatches: {},
    pMarkets: null,
    pActivity: null,
    pResearch: null,
    rs: { kind: "all", verdict: "all", q: "" },
    pLedger: { key: "", rows: [], error: "" },
    pb: { u: "nobel_settled", batch: "all", family: "all", page: 0, sort: "r", dir: 1, q: "" },
    fam: { u: "nobel_settled", family: "" },
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

  async function ensureProgramManifest() {
    if (state.pManifest) return state.pManifest;
    try {
      state.pManifest = await loadJSON("data/sim/program/manifest.json");
    } catch (err) {
      state.pManifest = { status: "missing", _error: err.message };
    }
    return state.pManifest;
  }

  async function ensureProgramBoard() {
    if (state.pBoard) return state.pBoard;
    state.pBoard = await loadJSON("data/sim/program/leaderboard.json");
    return state.pBoard;
  }

  async function ensureProgramFamilies() {
    if (state.pFamilies) return state.pFamilies;
    state.pFamilies = await loadJSON("data/sim/program/families.json");
    return state.pFamilies;
  }

  async function ensureProgramPeople() {
    if (state.pPeople) return state.pPeople;
    state.pPeople = await loadJSON("data/sim/program/participants.json");
    return state.pPeople;
  }

  async function ensureBatchReport(batch) {
    if (state.pBatches[batch]) return state.pBatches[batch];
    state.pBatches[batch] = await loadJSON(`data/sim/program/batches/${encodeURIComponent(batch)}.json`);
    return state.pBatches[batch];
  }

  function programMissing() {
    return `<div class="card"><p>The research program bundle is not in this checkout. Run <code>python scripts/refresh.py</code> to build it from the stored Kalshi snapshot. ${sim()}</p></div>`;
  }

  async function loadProgramLedger(batch, universe, pid) {
    const key = `${batch}|${universe}|${pid}`;
    if (state.pLedger.key === key) return state.pLedger.rows;
    const url = `data/sim/program/trades/${encodeURIComponent(batch)}/${encodeURIComponent(universe)}.csv.gz`;
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(url + " returned " + response.status);
    let text;
    if (window.DecompressionStream) {
      const stream = response.body.pipeThrough(new DecompressionStream("gzip"));
      text = await new Response(stream).text();
    } else {
      const buffer = await response.arrayBuffer();
      const bytes = window.pako ? window.pako.ungzip(buffer) : null;
      if (!bytes) throw new Error("This browser cannot decompress gzip. Download the CSV directly.");
      text = new TextDecoder().decode(bytes);
    }
    const lines = text.split("\n");
    const header = parseCsvLine(lines[0].replace(/\r$/, ""));
    const rows = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].replace(/\r$/, "");
      if (!line) continue;
      const cells = parseCsvLine(line);
      if (cells[0] !== pid) continue;
      const row = {};
      header.forEach((name, index) => { row[name] = cells[index] == null ? "" : cells[index]; });
      rows.push(row);
    }
    state.pLedger = { key, rows, error: "" };
    return rows;
  }

  function parseCsvLine(line) {
    const out = [];
    let field = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQuotes) {
        if (ch === '"') {
          if (line[i + 1] === '"') { field += '"'; i++; }
          else inQuotes = false;
        } else field += ch;
      } else if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        out.push(field);
        field = "";
      } else field += ch;
    }
    out.push(field);
    return out;
  }

  async function ensureProgramMarkets() {
    if (state.pMarkets) return state.pMarkets;
    state.pMarkets = await loadJSON("data/sim/program/markets.json");
    return state.pMarkets;
  }

  async function ensureProgramActivity() {
    if (state.pActivity) return state.pActivity;
    state.pActivity = await loadJSON("data/sim/program/activity.json");
    return state.pActivity;
  }

  function fmtUnix(value) {
    if (value == null || value === "") return "";
    const date = new Date(Number(value) * 1000);
    return Number.isFinite(date.getTime()) ? date.toISOString().replace("T", " ").replace(".000Z", "Z") : esc(value);
  }

  function programNote(note) {
    const code = String(note || "");
    return `<span class="muted small" title="Decision note code. Expanded rules are in the Topics view and data/sim/program/notes.json.">${esc(code)}</span>`;
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

  async function renderLeaderboard() {
    const comps = primaryComps();
    const stats = state.summary.data_quality || {};
    let programCard = "";
    try {
      const [manifest, board] = await Promise.all([
        ensureProgramManifest(),
        ensureProgramBoard().catch(() => null),
      ]);
      if (manifest && !manifest._error && manifest.status !== "missing") {
        const replay = manifest.replay || {};
        const topRows = board ? PROGRAM_UNIVERSES.map(([u, label]) => {
          const rows = board.filter((row) => row.u === u).sort((a, b) => a.r - b.r).slice(0, 3);
          return `<tr><td>${esc(label)}</td><td class="small">${rows.map((row) =>
            `${esc(row.r)}. <a href="#participant/${esc(row.p)}">${esc(row.p)}</a> ${num(row.eq)} <span class="muted">(${esc(row.f)})</span>`
          ).join("<br>")}</td></tr>`;
        }).join("") : "";
        programCard = `<div class="card">
          <h3><a href="#board">The research program</a> ${sim()}</h3>
          <p>${esc(manifest.participants)} simulated participants in ${esc((manifest.batches || []).length)} batches, ${esc(manifest.trade_rows_total)} ledger rows, replay ${esc(replay.status || "—")}. The board is the working competition leaderboard: <a href="#board">open it</a>. Top three per universe:</p>
          <div class="table-wrap"><table><tbody>${topRows}</tbody></table></div>
        </div>`;
        try { programCard += pWinCard(await ensureResearch()); } catch (err) { /* research.json optional */ }
      }
    } catch (err) {
      programCard = "";
    }
    main.innerHTML = banner() + `
      <h2>Leaderboard</h2>
      <p>Eleven primary simulated participants, same starting cash, same stored prices. They do not trade with each other. Rank is ending equity: cash plus a liquidation mark at the closing bid. ${sim()}</p>
      ${programCard}
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
      let programPerson = null;
      try {
        const people = await ensureProgramPeople();
        programPerson = people.find((p) => p.id === state.arg || p.strategy_id === state.arg);
      } catch (err) {
        programPerson = null;
      }
      if (programPerson) return renderProgramParticipant(programPerson);
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
    try {
      const programMarkets = await ensureProgramMarkets();
      state.pMarketByTicker = {};
      programMarkets.forEach((rollup) => {
        (state.pMarketByTicker[rollup.ticker] = state.pMarketByTicker[rollup.ticker] || []).push(rollup);
      });
    } catch (err) { state.pMarketByTicker = {}; }
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
      ${programRollupTable(market.ticker)}
      <h3>Ledger rows</h3>
      ${tradeTable(trades.slice(0, 100))}`;
  }

  function programRollupTable(ticker) {
    const rollups = (state.pMarketByTicker && state.pMarketByTicker[ticker]) || [];
    if (!rollups.length) {
      return `<h3>Program market-by-market results</h3><p class="note">No program participant placed a simulated order on this market, or the program markets file is not loaded. ${sim()}</p>`;
    }
    const blocks = rollups.map((rollup) => {
      const families = Object.entries(rollup.families || {}).map(([family, stats]) =>
        `<tr><td>${esc(family)}</td><td class="num">${esc(stats.n)}</td><td class="num">${num(stats.median_pnl)}</td><td class="num">${num(stats.mean_pnl)}</td><td class="num">${num(stats.min_pnl)}</td><td class="num">${num(stats.max_pnl)}</td></tr>`
      ).join("");
      return `<section class="card">
        <h4>${esc(universeNote(rollup.universe))} ${sim()}</h4>
        <p class="small">${esc(rollup.result_label)}${rollup.official_result ? ` — official result ${esc(rollup.official_result)} (Kalshi field, not simulated)` : ""}. Decision candles: ${esc(rollup.decision_candles)}. Program participants that traded here: ${esc(rollup.participants_traded)}.</p>
        <div class="table-wrap"><table><thead><tr>
          <th>Family</th><th class="num">Participants</th><th class="num">Median P&amp;L</th><th class="num">Mean P&amp;L</th><th class="num">Min P&amp;L</th><th class="num">Max P&amp;L</th>
        </tr></thead><tbody>${families || `<tr><td colspan="6">No family traded this market.</td></tr>`}</tbody></table></div>
        <p class="small"><a href="${esc(rollup.source_url)}">Kalshi API record</a> · <a href="data/sim/program/markets.json">program markets.json</a></p>
      </section>`;
    }).join("");
    return `<h3>Program market-by-market results</h3>${blocks}`;
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
    let programBlock = "";
    try {
      const activity = await ensureProgramActivity();
      const blocks = PROGRAM_UNIVERSES.map(([universe, label]) => {
        const days = (activity[universe] || []).slice(-30);
        if (!days.length) return "";
        const peak = Math.max(...days.map((row) => Number(row.ledger_rows)));
        return `<h4>${esc(label)} <span class="muted small">${sim()} last ${esc(days.length)} active days</span></h4>
          <div class="table-wrap"><table><thead><tr><th>Day (UTC)</th><th class="num">Ledger rows, all program participants</th><th></th></tr></thead><tbody>
          ${days.map((row) => `<tr><td>${esc(row.day)}</td><td class="num">${esc(row.ledger_rows)}</td><td><span class="bar" style="width:${Math.max(1, Math.round(120 * Number(row.ledger_rows) / peak))}px"></span></td></tr>`).join("")}
          </tbody></table></div>`;
      }).join("");
      programBlock = `<h3>Program activity over time</h3>
        <p class="small">Ledger rows per day for the full program, from the same stored candles. ${sim()}</p>
        ${blocks || "<p class=\"note\">No program activity file loaded.</p>"}`;
    } catch (err) { programBlock = ""; }
    main.innerHTML = banner() + `<h2>Strategy activity over time</h2>
      <p>Equity after simulated fills and settlements. The final liquidation mark is not on this clock if it has no timestamp. ${sim()}</p>
      ${toolbar()}
      ${equityChart(series, ids)}
      <div class="legend">${legend}</div>
      <h3>Simulated trades by day</h3>
      ${activityTable(trades)}
      ${programBlock}`;
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
    let programBlock = "";
    try {
      const manifest = await ensureProgramManifest();
      if (manifest && !manifest._error && manifest.status !== "missing") {
        const counts = Object.entries(manifest.flag_counts || {});
        const samples = (manifest.flag_samples || []).map((flag) => `<li class="small"><code>${esc(flag.code)}</code> (${esc(flag.universe || "")}) ${esc(flag.market_ticker || "")}: ${esc((flag.message || "").slice(0, 180))}</li>`).join("");
        programBlock = `<div class="card">
          <h3>Program data flags</h3>
          <p class="small">Data-quality flags raised while preparing the program run. They name candle gaps and unusable market metadata, not strategy behavior.</p>
          <div class="table-wrap"><table><tbody>${counts.map(([code, count]) => `<tr><td><code>${esc(code)}</code></td><td class="num">${esc(count)}</td></tr>`).join("") || `<tr><td>No program flags.</td></tr>`}</tbody></table></div>
          ${samples ? `<details><summary>Sample flag messages</summary><ul class="clean">${samples}</ul></details>` : ""}
        </div>`;
      }
    } catch (err) { programBlock = ""; }
    main.innerHTML = banner() + `<h2>Flags and irregularities</h2>
      <p>Review flags are not corrections. They mark a gap, a wide book, a failed request, or a fee type the engine did not treat as a plain quadratic taker fee.</p>
      ${toolbar()}
      <div class="table-wrap"><table><thead><tr><th>Severity</th><th>Code</th><th>Message</th><th>Market</th><th>Competition</th></tr></thead><tbody>${body || `<tr><td colspan="5">No flags.</td></tr>`}</tbody></table></div>
      ${programBlock}`;
    bindToolbar();
  }

  async function renderQuality() {
    const q = state.summary.data_quality || {};
    const exchange = q.exchange_status || {};
    let programBlock = "";
    try {
      const manifest = await ensureProgramManifest();
      if (manifest && !manifest._error && manifest.status !== "missing") {
        const replay = manifest.replay || {};
        const clock = manifest.decision_clock || {};
        const universeRows = Object.entries(manifest.universes || {}).map(([u, info]) =>
          `<tr><td>${esc(u)}</td><td class="num">${esc(info.trade_rows)}</td><td class="num">${esc(info.runtime_seconds)}s</td><td class="small"><code>${esc(String(info.combined_ledger_sha256 || "").slice(0, 24))}…</code></td></tr>`
        ).join("");
        programBlock = `<div class="card">
          <h3>Research program reproduction</h3>
          <p>Program ${esc(manifest.program_version || "?")} on engine ${esc(manifest.engine_version || "?")}, built ${esc(manifest.generated_at || "—")}. ${esc(manifest.participants || 0)} participants, ${esc(manifest.trade_rows_total || 0)} ledger rows.</p>
          <p class="small">Decision clock: ${esc(clock.rule || "")} Prior window: ${esc(clock.prior_window)} candles. ${esc(clock.settlement_rule || "")}</p>
          <p class="small">Replay: ${esc(replay.status || "—")} — ${esc(replay.note || "")}</p>
          <div class="table-wrap"><table><thead><tr><th>Universe</th><th class="num">Ledger rows</th><th class="num">Runtime</th><th>Combined ledger SHA-256</th></tr></thead><tbody>${universeRows}</tbody></table></div>
          <p class="links"><a href="data/sim/program/manifest.json">manifest.json</a> <a href="data/sim/program/ledger_hashes.json">ledger_hashes.json</a> <a href="data/sim/program/SCHEMA.md">SCHEMA.md</a></p>
        </div>`;
      }
    } catch (err) {
      programBlock = "";
    }
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
      ${programBlock}
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
        <h3>The research program</h3>
        <p>Twenty research topics, twenty batches of one hundred parameterized strategies (2,000 simulated participants). Batch-001 trades at seeded random times and exists as the null band; batch-020 adds a second, matched-rate null. Every family has a research card (question, mechanism, verified source, information used, predicted sign, falsification rule) and most entry families have a matched placebo that keeps the trigger and randomizes only the side. Batches 011-020 may also read three decision-time channels: sibling contracts of the same event at or before T, markets whose official result settled strictly before T, and Kalshi's published event strike_date (never close_time, which leaks on settled Nobel markets). The program engine shares the primary engine's fill rule (<code>compute_fill</code>) and decision clock; a test compares the two engines' ledgers line by line, and the build replays batches 001, 011, 013 and 018 and refuses to publish on mismatch.</p>
        <p class="small">Program ledgers stream to one gzipped CSV per batch and universe: participant, time, market, action, side, price, qty, fee, cash after, realized P&amp;L, fill source, note. The price column always names the stored candle field it came from. A strategy sees at most the 24 prior candles of its market — every declared lookback fits inside that window, which the tests assert.</p>
        <p class="small"><a href="#program">Program overview</a> · <a href="#research">Research findings</a> · <a href="#board">Program board</a> · <a href="#topics">Topics and hypotheses</a> · <a href="data/sim/program/SCHEMA.md">Ledger schema</a></p>
      </div>
      <div class="card">
        <h3>What was refused</h3>
        <ul class="clean">
          <li>No guessed nominees for sealed years.</li>
          <li>No filled-in Kalshi history when an endpoint failed or a candle had no price.</li>
          <li>No use of the fetch-time order book as if it had been the book at an earlier decision.</li>
          <li>No claim that this panel is the whole Kalshi exchange. The scope is in Data quality.</li>
          <li>No family result presented as an edge when its median sits inside the batch-001 null band.</li>
        </ul>
      </div>
      <p><a href="docs/METHOD.md">Full method note</a> · <a href="LIMITATIONS.md">Limitations for the next session</a></p>`;
  }

  function nullBandRows(families) {
    const bands = (families && families.null_band) || {};
    return PROGRAM_UNIVERSES.map(([u, label, kind]) => {
      const band = bands[u];
      if (!band || !band.n) return "";
      return `<tr>
        <td>${esc(label)}<br><span class="muted small">${esc(kind)}</span></td>
        <td class="num">${esc(band.n)}</td>
        <td class="num">${num(band.p05 != null ? band.p05.toFixed(4) : "")}</td>
        <td class="num">${num(band.median != null ? band.median.toFixed(4) : "")}</td>
        <td class="num">${num(band.p95 != null ? band.p95.toFixed(4) : "")}</td>
        <td class="num">${num(band.min != null ? band.min.toFixed(4) : "")} – ${num(band.max != null ? band.max.toFixed(4) : "")}</td>
      </tr>`;
    }).join("");
  }

  function universeNote(u) {
    const found = PROGRAM_UNIVERSES.find((row) => row[0] === u);
    return found ? `${found[1]} — ${found[2]}` : u;
  }

  function batchQuickStats(board, batch) {
    const out = {};
    board.filter((row) => row.b === batch).forEach((row) => {
      (out[row.u] = out[row.u] || []).push(Number(row.eq));
    });
    Object.keys(out).forEach((u) => {
      const values = out[u].sort((a, b) => a - b);
      out[u] = { n: values.length, median: values[Math.floor((values.length - 1) / 2)], min: values[0], max: values[values.length - 1] };
    });
    return out;
  }

  async function renderProgram() {
    main.innerHTML = `<p class="loading">Loading the program bundle…</p>`;
    const manifest = await ensureProgramManifest();
    if (!manifest || manifest._error || manifest.status === "missing") {
      main.innerHTML = banner() + "<h2>The research program</h2>" + programMissing();
      return;
    }
    let families = null;
    try { families = await ensureProgramFamilies(); } catch (err) { families = null; }
    let board = [];
    try { board = await ensureProgramBoard(); } catch (err) { board = []; }
    const replay = manifest.replay || {};
    const universeRows = Object.entries(manifest.universes || {}).map(([u, info]) => `<tr>
      <td>${esc(universeNote(u))}<br><span class="muted small"><code>${esc(info.competition_id || "")}</code></span></td>
      <td class="num">${esc(info.markets_used)}</td>
      <td class="num">${esc(info.candle_events)}</td>
      <td class="num">${esc(info.trade_rows)}</td>
      <td class="num">${esc(info.open_positions)}</td>
      <td class="small"><code title="Fold of the sorted per-participant ledger SHA-256 values. Reproduce any batch with scripts/verify_program.py.">${esc(String(info.combined_ledger_sha256 || "").slice(0, 16))}…</code></td>
    </tr>`).join("");
    const batchCards = (manifest.batches || []).map((batch) => {
      const stats = board.length ? batchQuickStats(board, batch) : {};
      const statLine = PROGRAM_UNIVERSES.map(([u, label]) => {
        const row = stats[u];
        if (!row) return "";
        return `<span class="chip">${esc(label)} median ${esc(row.median != null ? row.median.toFixed(2) : "—")}</span>`;
      }).join(" ");
      return `<article class="card">
        <h3><a href="#topics">${esc(batch)}</a></h3>
        <p class="small">${statLine || "No ledger rows loaded."}</p>
        <p class="small"><a href="data/sim/program/batches/${esc(batch)}.json">Batch report JSON</a> · <a href="#board">Board filtered to ${esc(batch)}</a> · ${sim()}</p>
      </article>`;
    }).join("");
    const files = (manifest.files || []).map((file) => `<tr>
      <td class="small"><a href="${esc(file.path)}">${esc(file.path)}</a></td>
      <td class="num">${esc(file.bytes)}</td>
      <td class="small"><code title="${esc(file.sha256)}">${esc(file.sha256.slice(0, 12))}…</code></td>
    </tr>`).join("");
    main.innerHTML = banner() + `<h2>The research program</h2>
      <p>${esc(manifest.participants)} simulated participants in ${esc((manifest.batches || []).length)} batches of 100, each batch one research topic, each variant one predeclared hypothesis. Same decision clock, size rules, and fee reading as the primary competitions. ${sim()} ${badge("review", "Not Kalshi users")}</p>
      <div class="grid">
        <div class="stat"><b>${esc(manifest.participants)}</b><span>Simulated participants</span></div>
        <div class="stat"><b>${esc(manifest.trade_rows_total)}</b><span>Ledger rows (all paper)</span></div>
        <div class="stat"><b>${esc(replay.status || "—")}</b><span>Replay of ${esc(replay.batch || "")} (${esc(replay.participants_checked || 0)} ledgers)</span></div>
        <div class="stat"><b>${esc(manifest.generated_at || "—")}</b><span>Built at (UTC)</span></div>
      </div>
      <h3>Null band — the floor every claim has to clear</h3>
      <p class="small">Distribution of the 100 random-entry participants (batch-001) per universe. A family median inside this band is not evidence of an edge. ${esc((families || {}).wording || "")}</p>
      <div class="table-wrap"><table><thead><tr>
        <th>Universe</th><th class="num">n</th><th class="num">p05</th><th class="num">Median</th><th class="num">p95</th><th class="num">Min – max</th>
      </tr></thead><tbody>${nullBandRows(families) || `<tr><td colspan="6">families.json not loaded.</td></tr>`}</tbody></table></div>
      <h3>Universes</h3>
      <div class="table-wrap"><table><thead><tr>
        <th>Universe</th><th class="num">Markets</th><th class="num">Candle events</th><th class="num">Ledger rows</th><th class="num">Open positions</th><th>Ledger hash</th>
      </tr></thead><tbody>${universeRows}</tbody></table></div>
      <h3>Batches</h3>
      <div class="cards">${batchCards}</div>
      <h3>How to verify a line</h3>
      <div class="card">
        <ul class="clean">
          <li>Every ledger row's price names the candle field it came from. The candle is in <code>data/sim/candles/{ticker}.json</code>; the recipe is <a href="data/sim/program/SCHEMA.md">data/sim/program/SCHEMA.md</a>.</li>
          <li>Replay any batch: <code>python scripts/verify_program.py batch-004</code>; the hashes are in <a href="data/sim/program/ledger_hashes.json">ledger_hashes.json</a>.</li>
          <li>Audit cash, P&amp;L, and prices line by line: <code>python scripts/audit_program.py</code>. Last audit in this checkout: see LIMITATIONS.md.</li>
          <li>The build re-ran ${esc(replay.batch || "the replay batch")} after the full pass and compared per-participant ledger hashes: ${badge(replay.status === "matched" ? "official" : "review", replay.status || "unknown")}.</li>
        </ul>
      </div>
      <h3>File inventory (sha-256 in manifest.json)</h3>
      <div class="table-wrap"><table><thead><tr><th>File</th><th class="num">Bytes</th><th>SHA-256</th></tr></thead><tbody>${files}</tbody></table></div>
      <p class="links"><a href="#board">Program board</a> <a href="#families">Family results</a> <a href="#topics">Research topics</a> <a href="data/sim/program/manifest.json">manifest.json</a> <a href="data/sim/program/leaderboard.csv">leaderboard.csv</a></p>`;
  }

  function programBoardToolbar(familiesInUniverse) {
    const batches = ["all"].concat([...new Set(state.pBoard.map((row) => row.b))].sort());
    const opts = batches.map((b) => `<option value="${esc(b)}" ${state.pb.batch === b ? "selected" : ""}>${esc(b)}</option>`).join("");
    const famOpts = ["all"].concat(familiesInUniverse).map((f) => `<option value="${esc(f)}" ${state.pb.family === f ? "selected" : ""}>${esc(f)}</option>`).join("");
    const tabs = PROGRAM_UNIVERSES.map(([u, label, kind]) =>
      `<button class="ghost" type="button" data-u="${esc(u)}" ${state.pb.u === u ? 'aria-current="true"' : ""}>${esc(label)}</button>`
    ).join("");
    return `<div class="toolbar">
      <div>${tabs}</div>
      <label>Batch<select id="pbbatch">${opts}</select></label>
      <label>Family<select id="pbfamily">${famOpts}</select></label>
      <label>Search<input id="pbq" type="search" value="${esc(state.pb.q)}" placeholder="Participant, strategy"></label>
    </div>`;
  }

  const BOARD_COLUMNS = [
    ["r", "Rank"], ["p", "Participant"], ["f", "Family"], ["s", "Strategy id"],
    ["eq", "Equity"], ["real", "Realized"], ["unreal", "Unrealized"], ["fees", "Fees"],
    ["n", "Trades"], ["mkts", "Markets"], ["dd", "Drawdown"], ["roi", "ROI"], ["wr", "Win rate"],
  ];

  async function renderProgramBoard() {
    main.innerHTML = `<p class="loading">Loading the program board…</p>`;
    const [manifest, board, people] = await Promise.all([ensureProgramManifest(), ensureProgramBoard().catch(() => null), ensureProgramPeople().catch(() => [])]);
    if (!board) {
      main.innerHTML = banner() + "<h2>Program board</h2>" + programMissing();
      return;
    }
    let families = null;
    try { families = await ensureProgramFamilies(); } catch (err) { families = null; }
    const peopleById = {};
    people.forEach((person) => { peopleById[person.id] = person; });
    if (!PROGRAM_UNIVERSES.some(([u]) => u === state.pb.u)) state.pb.u = PROGRAM_UNIVERSES[0][0];
    const universeRows = board.filter((row) => row.u === state.pb.u);
    const familiesInUniverse = [...new Set(universeRows.map((row) => row.f))].sort();
    const q = state.pb.q.trim().toLowerCase();
    let rows = universeRows.filter((row) => {
      if (state.pb.batch !== "all" && row.b !== state.pb.batch) return false;
      if (state.pb.family !== "all" && row.f !== state.pb.family) return false;
      if (!q) return true;
      const person = peopleById[row.p] || {};
      return `${row.p} ${row.s} ${person.display_name || ""} ${row.f}`.toLowerCase().includes(q);
    });
    const sortKey = state.pb.sort;
    rows = rows.slice().sort((a, b) => {
      if (sortKey === "p" || sortKey === "f" || sortKey === "s" || sortKey === "b") {
        return state.pb.dir * String(a[sortKey]).localeCompare(String(b[sortKey]));
      }
      const av = a[sortKey] == null ? -Infinity : Number(a[sortKey]);
      const bv = b[sortKey] == null ? -Infinity : Number(b[sortKey]);
      return sortKey === "r" ? state.pb.dir * (av - bv) : state.pb.dir * (bv - av);
    });
    const nullBand = families && families.null_band ? families.null_band[state.pb.u] : null;
    const pageSize = 50;
    const pages = Math.max(1, Math.ceil(rows.length / pageSize));
    state.pb.page = Math.min(state.pb.page, pages - 1);
    const pageRows = rows.slice(state.pb.page * pageSize, (state.pb.page + 1) * pageSize);
    const header = BOARD_COLUMNS.map(([key, label]) =>
      `<th class="num"><button class="ghost sort" type="button" data-sort="${esc(key)}">${esc(label)}${state.pb.sort === key ? (state.pb.dir === 1 ? " ▲" : " ▼") : ""}</button></th>`
    ).join("");
    const body = pageRows.map((row) => {
      const person = peopleById[row.p] || {};
      return `<tr>
        <td class="num">${esc(row.r)}${row.tied_flag ? " tie" : ""}</td>
        <td><a href="#participant/${esc(row.p)}">${esc(row.p)}</a><br><span class="muted small">${esc(person.display_name || person.hypothesis || "")} ${sim()}</span></td>
        <td><a href="#families" data-family-link="${esc(row.f)}">${esc(row.f)}</a></td>
        <td class="small"><code>${esc(row.s)}</code></td>
        <td class="num">${num(row.eq)}</td>
        <td class="num">${num(row.real)}</td>
        <td class="num">${num(row.unreal)}</td>
        <td class="num">${num(row.fees)}</td>
        <td class="num">${esc(row.n)}</td>
        <td class="num">${esc(row.mkts)}</td>
        <td class="num">${num(row.dd)}</td>
        <td class="num">${num(row.roi)}</td>
        <td class="num">${row.wr == null ? "—" : num(row.wr)}</td>
      </tr>`;
    }).join("");
    main.innerHTML = banner() + `<h2>Program board</h2>
      <p>${esc(universeNote(state.pb.u))}. All ${esc(board.length / 3)} participants share the same stored prices and $10,000 paper cash. ${sim()}</p>
      ${nullBand ? `<p class="note">Null band here: p05 ${esc(nullBand.p05.toFixed(2))}, median ${esc(nullBand.median.toFixed(2))}, p95 ${esc(nullBand.p95.toFixed(2))} across ${esc(nullBand.n)} random entries. Outranking p95 is the floor, not a trophy.</p>` : ""}
      ${programBoardToolbar(familiesInUniverse)}
      <p class="muted small">${esc(rows.length)} of ${esc(universeRows.length)} participants shown after filters. Ledger rows per participant are on the participant page.</p>
      <div class="table-wrap"><table><thead><tr>${header}</tr></thead><tbody>${body || `<tr><td colspan="${BOARD_COLUMNS.length}">No rows.</td></tr>`}</tbody></table></div>
      <p><button class="ghost" type="button" id="pbprev" ${state.pb.page === 0 ? "disabled" : ""}>Previous</button>
      Page ${esc(state.pb.page + 1)} of ${esc(pages)}
      <button class="ghost" type="button" id="pbnext" ${state.pb.page >= pages - 1 ? "disabled" : ""}>Next</button></p>`;
    main.querySelectorAll("[data-u]").forEach((button) => button.addEventListener("click", () => {
      state.pb.u = button.getAttribute("data-u");
      state.pb.page = 0;
      render();
    }));
    main.querySelectorAll("[data-sort]").forEach((button) => button.addEventListener("click", () => {
      const key = button.getAttribute("data-sort");
      if (state.pb.sort === key) state.pb.dir *= -1;
      else { state.pb.sort = key; state.pb.dir = key === "r" ? 1 : -1; }
      render();
    }));
    main.querySelectorAll("[data-family-link]").forEach((link) => link.addEventListener("click", () => {
      state.fam.family = link.getAttribute("data-family-link");
      state.fam.u = state.pb.u;
    }));
    const batchSelect = document.getElementById("pbbatch");
    const familySelect = document.getElementById("pbfamily");
    const qInput = document.getElementById("pbq");
    if (batchSelect) batchSelect.addEventListener("change", () => { state.pb.batch = batchSelect.value; state.pb.page = 0; render(); });
    if (familySelect) familySelect.addEventListener("change", () => { state.pb.family = familySelect.value; state.pb.page = 0; render(); });
    if (qInput) qInput.addEventListener("input", () => { state.pb.q = qInput.value; state.pb.page = 0; render(); });
    const prev = document.getElementById("pbprev");
    const next = document.getElementById("pbnext");
    if (prev) prev.addEventListener("click", () => { state.pb.page = Math.max(0, state.pb.page - 1); render(); });
    if (next) next.addEventListener("click", () => { state.pb.page = Math.min(pages - 1, state.pb.page + 1); render(); });
  }

  function sensitivityTable(sensitivity) {
    const families = Object.keys(sensitivity || {});
    if (!families.length) return "";
    return families.map((family) => {
      const rows = Object.entries(sensitivity[family]).map(([param, points]) =>
        `<tr><td class="small">${esc(param)}</td><td class="small">${points.map((point) =>
          `<span class="chip" title="n=${esc(point.n)} variants">${esc(point.value)} → ${num(point.median_equity.toFixed(2))}</span>`
        ).join(" ")}</td></tr>`
      ).join("");
      return `<h4>${esc(family)} — median equity by parameter value</h4>
        <div class="table-wrap"><table><tbody>${rows}</tbody></table></div>`;
    }).join("");
  }

  async function renderFamilies() {
    main.innerHTML = `<p class="loading">Loading family results…</p>`;
    const [families, board, people] = await Promise.all([
      ensureProgramFamilies().catch(() => null),
      ensureProgramBoard().catch(() => null),
      ensureProgramPeople().catch(() => []),
    ]);
    if (!families || !board) {
      main.innerHTML = banner() + "<h2>Family results</h2>" + programMissing();
      return;
    }
    if (!PROGRAM_UNIVERSES.some(([u]) => u === state.fam.u)) state.fam.u = PROGRAM_UNIVERSES[0][0];
    const u = state.fam.u;
    const bands = families.null_band || {};
    const band = bands[u] || {};
    const names = Object.keys(families.families || {}).sort();
    const peopleById = {};
    people.forEach((person) => { peopleById[person.id] = person; });
    const sidToVariant = {};
    people.forEach((person) => { sidToVariant[person.strategy_id] = person; });
    const rows = names.map((family) => {
      const stats = (families.families[family] || {})[u];
      if (!stats || family === "null_model") return "";
      const top = (stats.top || [])[2] || {};
      const bottom = (stats.bottom || [])[0] || {};
      const topPerson = sidToVariant[top.s] || {};
      return `<tr>
        <td><a href="#families" data-fam="${esc(family)}"><strong>${esc(family)}</strong></a></td>
        <td class="num">${esc(stats.n)}</td>
        <td class="num">${num(stats.median != null ? stats.median.toFixed(2) : "")}</td>
        <td class="num">${num(stats.q1 != null ? stats.q1.toFixed(2) : "")} – ${num(stats.q3 != null ? stats.q3.toFixed(2) : "")}</td>
        <td class="num">${esc((100 * (stats.share_above_null_p95 || 0)).toFixed(1))}%</td>
        <td class="small">${topPerson.id ? `<a href="#participant/${esc(topPerson.id)}">${esc(top.s)}</a> ${num(top.eq)}` : "—"}</td>
        <td class="small">${bottom.s ? `${esc(bottom.s)} ${num(bottom.eq)}` : "—"}</td>
      </tr>`;
    }).join("");
    const tabs = PROGRAM_UNIVERSES.map(([uu, label]) =>
      `<button class="ghost" type="button" data-u="${esc(uu)}" ${u === uu ? 'aria-current="true"' : ""}>${esc(label)}</button>`
    ).join("");
    let detail = "";
    if (state.fam.family && (families.families || {})[state.fam.family]) {
      const family = state.fam.family;
      const stats = (families.families[family] || {})[u] || {};
      const variants = people.filter((person) => person.family === family);
      const boardById = {};
      board.filter((row) => row.u === u && row.f === family).forEach((row) => { boardById[row.p] = row; });
      const sorted = variants.slice().sort((a, b) => {
        const ra = boardById[a.id] || { r: 99999 };
        const rb = boardById[b.id] || { r: 99999 };
        return ra.r - rb.r;
      });
      detail = `<h3>${esc(family)} on ${esc(universeNote(u))}</h3>
        <p class="small"><a href="#research/${esc(family)}">Research card and verdict for ${esc(family)}</a></p>
        <p class="small">${esc((variants[0] || {}).hypothesis ? "Each variant below is one predeclared hypothesis. Parameters make the difference; the entry rule is shared." : "")}</p>
        <div class="table-wrap"><table><thead><tr>
          <th class="num">Rank</th><th>Variant</th><th>Hypothesis</th><th class="num">Equity</th><th class="num">Fees</th><th class="num">Trades</th>
        </tr></thead><tbody>${sorted.map((person) => {
          const row = boardById[person.id] || {};
          return `<tr>
            <td class="num">${esc(row.r != null ? row.r : "—")}</td>
            <td><a href="#participant/${esc(person.id)}">${esc(person.display_name)}</a><br><code class="small">${esc(person.strategy_id)}</code></td>
            <td class="small">${esc(person.hypothesis)}</td>
            <td class="num">${row.eq != null ? num(row.eq) : "—"}</td>
            <td class="num">${row.fees != null ? num(row.fees) : "—"}</td>
            <td class="num">${row.n != null ? esc(row.n) : "—"}</td>
          </tr>`;
        }).join("")}</tbody></table></div>
        <p class="small">Family stats on this universe: median ${num(stats.median != null ? stats.median.toFixed(2) : "")}, n=${esc(stats.n)}, share above the null p95 ${esc((100 * (stats.share_above_null_p95 || 0)).toFixed(1))}%.</p>`;
    }
    main.innerHTML = banner() + `<h2>Family results</h2>
      <p>A family shares one entry rule; variants scan its parameters. Reading a family median against the null band answers "does this rule do anything at all on this snapshot?" ${sim()}</p>
      <p class="note">Null band on ${esc(universeNote(u))}: median ${esc(band.median != null ? band.median.toFixed(2) : "—")}, p95 ${esc(band.p95 != null ? band.p95.toFixed(2) : "—")}. ${esc(families.wording || "")}</p>
      <div class="toolbar"><div>${tabs}</div></div>
      <div class="table-wrap"><table><thead><tr>
        <th>Family</th><th class="num">Variants</th><th class="num">Median equity</th><th class="num">q1 – q3</th><th class="num">Above null p95</th><th>Top variant</th><th>Bottom variant</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      ${detail}
      <p class="links"><a href="#board">Program board</a> <a href="#topics">Research topics</a></p>`;
    main.querySelectorAll("[data-u]").forEach((button) => button.addEventListener("click", () => {
      state.fam.u = button.getAttribute("data-u");
      render();
    }));
    main.querySelectorAll("[data-fam]").forEach((link) => link.addEventListener("click", () => {
      state.fam.family = link.getAttribute("data-fam");
      state.fam.u = state.fam.u;
      render();
    }));
  }

  // ---------------------------------------------------------------------------
  // Research view: research cards, predeclared verdict rules, power, sources.
  // Reads data/sim/program/research.json (written by simcomp/analysis.py).
  // ---------------------------------------------------------------------------

  async function ensureResearch() {
    if (state.pResearch) return state.pResearch;
    state.pResearch = await loadJSON("data/sim/program/research.json");
    return state.pResearch;
  }

  function verdictBadge(verdict) {
    const v = String(verdict || "");
    const kind = v === "SUPPORTED-ON-SNAPSHOT" ? "official"
      : v === "NOT SUPPORTED" ? "review"
      : v === "REFERENCE" ? "hist"
      : v === "MIXED" ? "live"
      : "info";
    return badge(kind, v || "—");
  }

  function signed(value) {
    if (value == null) return "—";
    const n = Number(value);
    return (n >= 0 ? "+" : "") + n.toFixed(2);
  }

  function researchCell(stats) {
    if (!stats) return "—";
    if (!stats.entered) return `<span class="muted">no fills</span><br>${verdictBadge(stats.verdict)}`;
    return `${num(stats.median_eq != null ? stats.median_eq.toFixed(2) : "")} <span class="muted small">(${esc(signed(stats.vs_null_median))} vs null)</span><br>${verdictBadge(stats.verdict)}`;
  }

  function sourceLinks(research, ids) {
    return (ids || []).map((id) => {
      const src = (research.sources || {})[id] || {};
      return src.url
        ? `<a href="${esc(src.url)}" rel="noopener" title="${esc(src.citation || "")}">${esc(id)}</a>`
        : `<span title="${esc(src.citation || "")}">${esc(id)}</span>`;
    }).join(", ");
  }

  function researchDetail(research, fam) {
    const card = fam.card || {};
    const rows = ["nobel_settled", "panel_settled", "nobel_forward"].map((u) => {
      const s = (fam.universes || {})[u];
      if (!s) return "";
      return `<tr>
        <td>${esc(universeNote(u))}</td>
        <td class="num">${esc(s.entered)}/${esc(s.n)}</td>
        <td class="num">${s.median_eq != null ? num(s.median_eq.toFixed(2)) : "—"}</td>
        <td class="num">${esc(signed(s.vs_null_median))}</td>
        <td class="num">${esc(signed(s.vs_cash))}</td>
        <td class="num">${s.placebo_median_eq != null ? esc(signed(s.vs_placebo)) : "—"}</td>
        <td class="num">${esc((100 * (s.share_above_null_p95 || 0)).toFixed(1))}%<br><span class="muted small">p=${esc(s.binom_p_indep < 0.000001 ? "<1e-6" : s.binom_p_indep)}</span></td>
        <td class="num">${s.loo_worst_median_eq != null ? num(s.loo_worst_median_eq.toFixed(2)) : "—"}<br><span class="muted small">${esc(s.loo_worst_event || "")}</span></td>
        <td class="num">${esc(s.settled_events_touched)} (${esc(s.yes_events_touched)} YES)</td>
        <td class="small">${esc(s.top_event || "—")} ${s.top_event_share != null ? esc((100 * s.top_event_share).toFixed(0)) + "%" : ""}</td>
        <td class="num">${esc((100 * (s.p_top_decile || 0)).toFixed(0))}%</td>
        <td class="num">${esc((100 * (s.clip_rate || 0)).toFixed(1))}%</td>
        <td>${verdictBadge(s.verdict)}<br><span class="small muted">${esc(s.why || "")}</span></td>
      </tr>`;
    }).join("");
    const channels = (card.channels || []).map((c) => `<li><code>${esc(c)}</code> — ${esc((research.channels || {})[c] || "")}</li>`).join("");
    const sources = (card.sources || []).map((id) => {
      const src = (research.sources || {})[id] || {};
      return `<li>${src.url ? `<a href="${esc(src.url)}" rel="noopener">${esc(src.citation || id)}</a>` : esc(src.citation || id)}<br><span class="small muted">Used for: ${esc(src.claim_used || "")}</span></li>`;
    }).join("");
    return `<section class="card" id="research-detail">
      <p>${sim()} ${badge("info", card.kind || "")} ${verdictBadge(fam.overall)}</p>
      <h3><code>${esc(fam.family)}</code> <span class="muted small">${esc((fam.batches || []).join(", "))} · ${esc(fam.variants)} variants</span></h3>
      <dl class="card-fields">
        <dt>Question</dt><dd>${esc(card.question)}</dd>
        <dt>Mechanism</dt><dd>${esc(card.mechanism)}</dd>
        <dt>Predicts</dt><dd>${esc(card.predicts)}</dd>
        <dt>Falsified if</dt><dd>${esc(card.falsified_if)}</dd>
        ${card.placebo_of ? `<dt>Placebo of</dt><dd><a href="#research/${esc(card.placebo_of)}">${esc(card.placebo_of)}</a></dd>` : ""}
        <dt>Consistency</dt><dd>${esc(fam.consistency || "—")}</dd>
      </dl>
      <h4>Information the rule reads at decision time</h4><ul class="small">${channels}</ul>
      <h4>Sources (verified ${esc(research.sources_verified_on)})</h4><ul class="small">${sources}</ul>
      <p class="small">A cited paper suggested the rule; its result is not evidence for the simulated result.</p>
      <h4>Results by universe</h4>
      <div class="table-wrap"><table><thead><tr>
        <th>Universe</th><th class="num">Traded</th><th class="num">Median equity (traded)</th><th class="num">vs null median</th><th class="num">vs $10,000</th><th class="num">vs placebo</th><th class="num">Above null p95</th><th class="num">Worst leave-one-event-out</th><th class="num">Settled events</th><th>Largest event share</th><th class="num">P(top 10%)</th><th class="num">Clip rate</th><th>Verdict</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      <p class="small">The p-value assumes independent variants; they share signals and markets, so it overstates the evidence. <a href="#families" data-fam-link="${esc(fam.family)}">Variants and parameters</a> · <a href="#research">All families</a></p>
    </section>`;
  }

  async function renderResearch() {
    main.innerHTML = `<p class="loading">Loading research findings…</p>`;
    let research = null;
    try { research = await ensureResearch(); } catch (err) { research = null; }
    if (!research) {
      main.innerHTML = banner() + "<h2>Research findings</h2>" + programMissing();
      return;
    }
    const f = state.rs;
    const families = research.families || [];
    const selected = state.arg ? families.find((fam) => fam.family === state.arg) : null;
    const kinds = Array.from(new Set(families.map((fam) => (fam.card || {}).kind))).sort();
    const verdicts = Array.from(new Set(families.map((fam) => fam.overall))).sort();
    const q = f.q.trim().toLowerCase();
    const shown = families.filter((fam) =>
      (f.kind === "all" || (fam.card || {}).kind === f.kind)
      && (f.verdict === "all" || fam.overall === f.verdict)
      && (!q || fam.family.toLowerCase().includes(q) || String((fam.card || {}).question || "").toLowerCase().includes(q))
    );
    const rows = shown.map((fam) => {
      const ns = (fam.universes || {}).nobel_settled;
      const ps = (fam.universes || {}).panel_settled;
      return `<tr>
        <td>${esc((fam.batches || [""])[0].replace("batch-", ""))}</td>
        <td><a href="#research/${esc(fam.family)}"><code>${esc(fam.family)}</code></a><br><span class="small muted">${esc((fam.card || {}).question || "")}</span></td>
        <td class="small">${esc((fam.card || {}).kind || "")}</td>
        <td class="num">${researchCell(ns)}</td>
        <td class="num">${researchCell(ps)}</td>
        <td class="num small">${ns ? esc((100 * (ns.p_top_decile || 0)).toFixed(0)) : "—"}% / ${ps ? esc((100 * (ps.p_top_decile || 0)).toFixed(0)) : "—"}%</td>
        <td>${verdictBadge(fam.overall)}<br><span class="small muted">${esc(fam.consistency || "")}</span></td>
      </tr>`;
    }).join("");
    const power = Object.entries(research.universes || {}).map(([u, info]) => `<tr>
      <td>${esc(universeNote(u))}</td><td class="num">${esc(info.markets)}</td><td class="num">${esc(info.events)}</td>
      <td class="num">${esc(info.settled_events)}</td><td class="num">${esc(info.events_with_yes)}</td>
      <td class="num">${esc((info.null || {}).p05)} / ${esc((info.null || {}).median)} / ${esc((info.null || {}).p95)}</td>
      <td class="num">${esc(info.top_decile_cut)}</td>
    </tr>`).join("");
    const rules = Object.entries(research.rules || {}).map(([k, v]) => `<li>${verdictBadge(k)} ${esc(v)}</li>`).join("");
    const counts = Object.entries(research.overall_counts || {}).sort().map(([k, v]) => `<div class="stat"><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join("");
    const mt = research.multiple_testing || {};
    const quality = (research.data_quality || []).map((flag) => `<li>${badge(flag.severity === "warning" ? "review" : "info", flag.code)} ${esc(flag.message)}</li>`).join("");
    const sourceRows = Object.entries(research.sources || {}).map(([id, src]) => `<tr>
      <td><code>${esc(id)}</code></td>
      <td class="small">${esc(src.citation)}<br><span class="muted">${esc(src.claim_used || "")}</span></td>
      <td class="small">${src.url ? `<a href="${esc(src.url)}" rel="noopener">link</a>` : "—"}</td>
    </tr>`).join("");
    const opt = (value, current, label) => `<option value="${esc(value)}" ${value === current ? "selected" : ""}>${esc(label || value)}</option>`;
    main.innerHTML = banner() + `<h2>Research findings</h2>
      <p>Every family below has a research card written with its rule: the question, the mechanism, the published idea that suggested it, the information it reads, the predicted sign, and what would count against it. Verdicts follow fixed rules and are recomputed on every build. ${sim()}</p>
      ${selected ? researchDetail(research, selected) : ""}
      <div class="grid">${counts}</div>
      <p class="note"><strong>Maximize P(Win), own the outcome.</strong> ${esc(mt.family_universe_tests)} family × universe tests reached a verdict; about ${esc(mt.expected_false_passes_at_5pct)} would pass a 5% bar by luck alone. A "supported" family is a lead to test on new markets, not a proven edge. Most families are not supported or cannot be told apart from luck on this snapshot.</p>
      <h3>Verdict rules</h3><ul class="small">${rules}</ul>
      <h3>Power: what each universe can show</h3>
      <div class="table-wrap"><table><thead><tr><th>Universe</th><th class="num">Markets</th><th class="num">Events</th><th class="num">Settled events</th><th class="num">Events with a YES</th><th class="num">Null p05 / median / p95</th><th class="num">Top-10% cut</th></tr></thead><tbody>${power}</tbody></table></div>
      <h3>Families</h3>
      <div class="toolbar">
        <label>Kind<select id="rs-kind">${opt("all", f.kind, "All kinds")}${kinds.map((k) => opt(k, f.kind)).join("")}</select></label>
        <label>Overall verdict<select id="rs-verdict">${opt("all", f.verdict, "All verdicts")}${verdicts.map((v) => opt(v, f.verdict)).join("")}</select></label>
        <label>Search<input id="rs-q" type="search" value="${esc(f.q)}" placeholder="family or question"></label>
      </div>
      <p class="small muted">${esc(shown.length)} of ${esc(families.length)} families. Medians use the variants that traded; a variant that never trades ends at $10,000 and is not evidence. P(top 10%) counts all variants: Nobel / panel.</p>
      <div class="table-wrap"><table><thead><tr>
        <th>Batch</th><th>Family and question</th><th>Kind</th><th class="num">Settled Nobel</th><th class="num">Settled panel</th><th class="num">P(top 10%)</th><th>Overall</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      <h3>Data-quality limits that affect research</h3><ul class="small">${quality}</ul>
      <h3>Sources</h3>
      <div class="table-wrap"><table><thead><tr><th>id</th><th>Citation and the claim used</th><th>Link</th></tr></thead><tbody>${sourceRows}</tbody></table></div>
      <p class="links"><a href="data/sim/program/research.json">research.json</a> <a href="docs/RESEARCH.md">RESEARCH.md</a> <a href="#families">Families</a> <a href="#board">Program board</a></p>`;
    const kindSel = document.getElementById("rs-kind");
    const verdictSel = document.getElementById("rs-verdict");
    const qInput = document.getElementById("rs-q");
    if (kindSel) kindSel.addEventListener("change", () => { f.kind = kindSel.value; renderResearch(); });
    if (verdictSel) verdictSel.addEventListener("change", () => { f.verdict = verdictSel.value; renderResearch(); });
    if (qInput) qInput.addEventListener("change", () => { f.q = qInput.value; renderResearch(); });
    main.querySelectorAll("[data-fam-link]").forEach((link) => link.addEventListener("click", () => {
      state.fam.family = link.getAttribute("data-fam-link");
    }));
    if (selected) {
      const el = document.getElementById("research-detail");
      if (el && el.scrollIntoView) el.scrollIntoView();
    }
  }

  function pWinCard(research) {
    if (!research || !research.families) return "";
    const blocks = ["nobel_settled", "panel_settled"].map((u) => {
      const REF = ["null", "control", "placebo"];
      const pool = research.families
        .filter((fam) => (fam.universes || {})[u])
        .map((fam) => ({ fam, s: fam.universes[u] }))
        .filter((item) => item.s.n >= 4)
        .sort((a, b) => (b.s.p_top_decile - a.s.p_top_decile) || a.fam.family.localeCompare(b.fam.family));
      const ranked = pool.filter((item) => !REF.includes((item.fam.card || {}).kind)).slice(0, 5);
      const luck = pool.find((item) => REF.includes((item.fam.card || {}).kind));
      const pct = (item) => esc((100 * item.s.p_top_decile).toFixed(0)) + "%";
      return `<tr><td>${esc(universeNote(u))}</td><td class="small">${ranked.map((item) =>
        `<a href="#research/${esc(item.fam.family)}">${esc(item.fam.family)}</a> ${pct(item)} ${verdictBadge(item.s.verdict)}`
      ).join("<br>")}${luck ? `<br><span class="muted">Luck yardstick: best reference family <a href="#research/${esc(luck.fam.family)}">${esc(luck.fam.family)}</a> ${pct(luck)}</span>` : ""}</td></tr>`;
    }).join("");
    return `<div class="card">
      <h3>Maximize P(Win): which families finish in the top 10%? ${sim()}</h3>
      <p class="small">Share of each family's variants (families with at least 4) that ended in the top decile of the 2,000-participant board, settled universes only. Null, control and placebo families are left out of the ranking; the best of them is shown as a yardstick, because a random side choice can also land in the top decile on few events. A high share with a weak verdict means the family got lucky on few events. <a href="#research">Research findings</a></p>
      <div class="table-wrap"><table><tbody>${blocks}</tbody></table></div>
    </div>`;
  }

  async function renderTopics() {
    main.innerHTML = `<p class="loading">Loading the research topics…</p>`;
    const manifest = await ensureProgramManifest();
    if (!manifest || manifest.status === "missing") {
      main.innerHTML = banner() + "<h2>Research topics</h2>" + programMissing();
      return;
    }
    const batches = manifest.batches || [];
    let reports = [];
    try {
      reports = await Promise.all(batches.map((batch) => ensureBatchReport(batch)));
    } catch (err) {
      reports = [];
    }
    let people = [];
    try { people = await ensureProgramPeople(); } catch (err) { people = []; }
    const sections = reports.map((report, index) => {
      const batch = batches[index];
      const variants = people.filter((person) => person.batch === batch);
      const universeBlocks = Object.entries(report.universes || {}).map(([u, info]) => {
        const best = info.best || {};
        const worst = info.worst || {};
        return `<div class="card">
          <h4>${esc(universeNote(u))}</h4>
          <p class="small">
            ${esc(info.entered)} of ${esc((info.leaderboard || []).length)} variants placed a simulated order.
            Median equity ${num(info.equity && info.equity.median != null ? info.equity.median.toFixed(2) : "—")};
            best ${best.p ? `<a href="#participant/${esc(best.p)}">${esc(best.p)}</a> ${num(best.eq)}` : "—"};
            worst ${worst.p ? `${esc(worst.p)} ${num(worst.eq)}` : "—"}.
            Share above the null p95: ${esc((100 * (info.share_above_null_p95 || 0)).toFixed(1))}%.
            Ledger rows: ${esc(info.trade_rows)}.
          </p>
          <p class="small">Null band here: median ${esc(info.null_band && info.null_band.median != null ? info.null_band.median.toFixed(2) : "—")}, p05–p95 ${esc(info.null_band && info.null_band.p05 != null ? info.null_band.p05.toFixed(2) : "—")}–${esc(info.null_band && info.null_band.p95 != null ? info.null_band.p95.toFixed(2) : "—")}.</p>
          ${sensitivityTable(info.param_sensitivity)}
          <p class="small"><a href="${esc(info.trades_csv)}">Gzipped simulated ledger CSV</a> · ${sim()}</p>
        </div>`;
      }).join("");
      const hypothesisList = variants.map((person) =>
        `<li><strong><a href="#participant/${esc(person.id)}">${esc(person.display_name)}</a></strong> <code class="small">${esc(person.strategy_id)}</code><br>
        <span class="muted small">${esc(JSON.stringify(person.parameters))}</span><br>${esc(person.hypothesis)}</li>`
      ).join("");
      return `<section class="card" id="${esc(batch)}">
        <h3>${esc(batch)} — ${esc(report.topic)}</h3>
        <p>${esc(report.statement)}</p>
        <p class="small muted">${esc(report.variant_count)} variants, families: ${esc((report.families || []).join(", "))}. ${esc((report.universes?.nobel_settled?.caution) || "")}</p>
        <details><summary>Open the ${esc(report.variant_count)} predeclared hypotheses, one by one</summary>
          <ul class="clean">${hypothesisList}</ul>
        </details>
        ${universeBlocks}
        <p class="links"><a href="data/sim/program/batches/${esc(batch)}.json">Batch JSON</a> <a href="#board">Board</a></p>
      </section>`;
    }).join("");
    main.innerHTML = banner() + `<h2>Research topics</h2>
      <p>${esc(batches.length)} topics, ${esc(batches.length)} batches, one hundred predeclared hypotheses per topic. Batch-001 is the null reference on purpose: it exists so no other number has to be read as skill. Family verdicts: <a href="#research">Research findings</a>. ${sim()}</p>
      ${sections || "<p>Batch reports did not load.</p>"}`;
  }

  async function renderProgramParticipant(person) {
    const [board, manifest] = await Promise.all([ensureProgramBoard().catch(() => null), ensureProgramManifest()]);
    const boards = board ? board.filter((row) => row.p === person.id) : [];
    const boardRows = boards.map((row) => `<tr>
      <td>${esc(universeNote(row.u))}</td>
      <td class="num">${esc(row.r)}${row.tied_flag ? " tie" : ""}</td>
      <td class="num">${num(row.eq)}</td>
      <td class="num">${num(row.real)}</td>
      <td class="num">${num(row.unreal)}</td>
      <td class="num">${num(row.fees)}</td>
      <td class="num">${esc(row.n)}</td>
      <td class="num">${esc(row.mkts)}</td>
      <td class="num">${row.wr == null ? "—" : num(row.wr)}</td>
      <td class="num">${num(row.dd)}</td>
      <td class="num">${esc(fmtUnix(row.t0))}<br>${esc(fmtUnix(row.t1))}</td>
    </tr>`).join("");
    const ledgerButtons = PROGRAM_UNIVERSES.map(([u, label]) =>
      `<button class="ghost" type="button" data-ledger="${esc(person.batch)}|${esc(u)}|${esc(person.id)}">${esc(label)} ledger rows</button>`
    ).join(" ");
    main.innerHTML = banner() + `<p><a href="#board">Program board</a> · <a href="#topics">${esc(person.batch)}</a></p>
      <h2>${esc(person.display_name)}</h2>
      <p><code>${esc(person.username)}</code> · strategy <code>${esc(person.strategy_id)}</code> · family <a href="#families">${esc(person.family)}</a> ${sim()} ${badge("review", "Not a real account")}</p>
      <div class="card">
        <h3>Predeclared hypothesis</h3>
        <p>${esc(person.hypothesis)}</p>
        <p class="small">Parameters: <code>${esc(JSON.stringify(person.parameters))}</code></p>
        <p class="small">Topic: ${esc(person.topic)} · batch ${esc(person.batch)}. Research card and family verdict: <a href="#research/${esc(person.family)}">${esc(person.family)}</a>.</p>
      </div>
      <h3>Performance by universe</h3>
      <div class="table-wrap"><table><thead><tr>
        <th>Universe</th><th class="num">Rank</th><th class="num">Equity</th><th class="num">Realized</th><th class="num">Unrealized</th><th class="num">Fees</th><th class="num">Trades</th><th class="num">Markets</th><th class="num">Win rate</th><th class="num">Drawdown</th><th>First / last ledger row (UTC)</th>
      </tr></thead><tbody>${boardRows || `<tr><td colspan="11">program leaderboard not loaded</td></tr>`}</tbody></table></div>
      <h3>Simulated ledger rows</h3>
      <p class="small">Rows stream from the gzipped per-batch ledgers. Loading one file may take a few seconds. The price in every row names its candle field; audit recipe in <a href="data/sim/program/SCHEMA.md">SCHEMA.md</a>.</p>
      <p>${ledgerButtons}</p>
      <div id="pledger"></div>`;
    main.querySelectorAll("[data-ledger]").forEach((button) => button.addEventListener("click", async () => {
      const [batch, universe, pid] = button.getAttribute("data-ledger").split("|");
      const mount = document.getElementById("pledger");
      mount.innerHTML = `<p class="loading">Loading ${esc(universe)} ledger…</p>`;
      try {
        const rows = await loadProgramLedger(batch, universe, pid);
        const shown = rows.slice(0, 300);
        mount.innerHTML = `<p class="small">${esc(rows.length)} ledger rows for ${esc(pid)} on ${esc(universe)}. Showing ${esc(shown.length)}. Full file: <a href="data/sim/program/trades/${esc(batch)}/${esc(universe)}.csv.gz">${esc(batch)}/${esc(universe)}.csv.gz</a>. ${sim()}</p>
          <div class="table-wrap"><table><thead><tr>
            <th>Time (UTC)</th><th>Market</th><th>Action</th><th class="num">Price</th><th class="num">Qty</th><th class="num">Fee</th><th class="num">Cash after</th><th class="num">Realized</th><th>Fill src</th><th>Note</th>
          </tr></thead><tbody>${shown.map((row) => `<tr>
            <td class="small">${esc(fmtUnix(row.ts_unix))}</td>
            <td><a href="#market/${esc(row.ticker)}">${esc(row.ticker)}</a></td>
            <td>${esc(row.action)} ${esc(row.side)}</td>
            <td class="num">${esc(row.price)}</td>
            <td class="num">${esc(row.qty)}</td>
            <td class="num">${num(row.fee)}</td>
            <td class="num">${num(row.cash_after)}</td>
            <td class="num">${num(row.realized_pnl)}</td>
            <td class="num">${esc(row.fill_src)}</td>
            <td>${programNote(row.note)}</td>
          </tr>`).join("") || `<tr><td colspan="10">No rows for this participant in this universe.</td></tr>`}</tbody></table></div>`;
      } catch (err) {
        mount.innerHTML = `<p class="note">Ledger load failed: ${esc(err.message)}. The file is <a href="data/sim/program/trades/${esc(batch)}/${esc(universe)}.csv.gz">${esc(batch)}/${esc(universe)}.csv.gz</a>.</p>`;
      }
    }));
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
    if (state.view === "board") return renderProgramBoard();
    if (state.view === "research") return renderResearch();
    if (state.view === "program") return renderProgram();
    if (state.view === "families") return renderFamilies();
    if (state.view === "topics") return renderTopics();
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
