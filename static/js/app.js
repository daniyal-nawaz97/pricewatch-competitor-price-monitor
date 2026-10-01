/* PriceWatch front-end */
Object.assign(ICONS, {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  tag: '<path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
  store: '<path d="M3 9 4.5 4h15L21 9"/><path d="M4 9v11h16V9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M10 20v-5h4v5"/>',
  report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 17v-3"/><path d="M12 17v-6"/><path d="M15 17v-4"/>',
  trendDown: '<path d="m22 17-8.5-8.5-5 5L2 7"/><path d="M16 17h6v-6"/>',
  trendUp: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  pkg: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  scale: '<path d="M12 3v18"/><path d="M5 7h14"/><path d="m5 7-3 7a4 4 0 0 0 6 0z"/><path d="m19 7-3 7a4 4 0 0 0 6 0z"/>',
  play: '<path d="m6 3 14 9-14 9z"/>',
});

const App = { user: null, info: null, unread: 0 };
const canEdit = () => ["admin", "analyst"].includes(App.user?.role);
const isAdmin = () => App.user?.role === "admin";
const money = (v) => (v === null || v === undefined ? "—" : `Rs. ${Number(v).toLocaleString("en-US", { maximumFractionDigits: App.info?.rounding ?? 0, minimumFractionDigits: App.info?.rounding ?? 0 })}`);
const pct = (v, d = 1) => (v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(d)}%`);
const ALERT_IC = { price_drop: ["trendDown", "warn"], price_increase: ["trendUp", "good"], cheaper_than_you: ["alert", "high"], out_of_stock: ["pkg", "good"],
  back_in_stock: ["pkg", "info"], new_product: ["sparkles", "info"] };
const tip = (t) => `<div class="tip">${icon("lightbulb")}<span>${t}</span></div>`;
const posLabel = (r) => (r.rank ? `${r.rank}${["th", "st", "nd", "rd"][r.rank % 10 > 3 || [11, 12, 13].includes(r.rank % 100) ? 0 : r.rank % 10]} of ${r.of}` : "—");
const loadChart = () => window.Chart ? Promise.resolve() : new Promise((r) => { window.addEventListener("load", r, { once: true }); setTimeout(r, 4000); });

function brandHTML() {
  const i = App.info || {};
  return `<a class="brand" href="#/">${i.logo_url ? `<img src="${esc(i.logo_url)}" alt="logo">` : `<span class="brand-mark">${icon("tag")}</span>`}<span>PriceWatch</span>
    ${i.company_name ? `<span class="hide-sm" style="font-weight:500;color:var(--text-3);font-size:14px">· ${esc(i.company_name)}</span>` : ""}</a>`;
}

function shell(active, html, { wide = false } = {}) {
  const nav = [["overview", "#/", "grid", "Overview"], ["products", "#/products", "tag", "Products"], ["alerts", "#/alerts", "bell", "Alerts"],
    ["competitors", "#/competitors", "store", "Competitors"], ["reports", "#/reports", "report", "Reports"]];
  if (isAdmin()) nav.push(["settings", "#/settings", "settings", "Settings"]);
  const isDemo = App.user?.email === "demo@pricewatch.app";
  const badge = (k) => (k === "alerts" && App.unread ? ` <span class="badge err plain" style="padding:0 7px">${App.unread}</span>` : "");
  $("#app").innerHTML = `
    ${isDemo ? `<div class="demo-banner">Demo store: GadgetHub.pk and its competitors are fictitious. All products and prices are invented.</div>` : ""}
    <header class="topbar">${brandHTML()}
      <nav class="nav" aria-label="Main">${nav.map(([k, h, ic, l]) => `<a href="${h}" class="${active === k ? "active" : ""}">${icon(ic)}${l}${badge(k)}</a>`).join("")}</nav>
      <div class="spacer"></div>
      <div class="profile"><button class="avatar" id="avatarBtn" aria-label="Profile menu">${esc(initials(App.user?.name))}</button>
        <div class="menu hidden" id="profileMenu"><div class="menu-head"><div style="font-weight:600">${esc(App.user?.name)}</div><div class="muted small">${esc(App.user?.email)}</div><div class="tiny muted" style="text-transform:capitalize">${esc(App.user?.role)}</div></div>
          <a href="/privacy" target="_blank">${icon("shield")} Data sources &amp; privacy</a><button id="logoutBtn">${icon("logout")} Sign out</button></div></div>
    </header>
    <main class="page ${wide ? "wide" : ""}" id="main">${html}</main>
    <nav class="bottom-nav" aria-label="Main">${nav.slice(0, 5).map(([k, h, ic, l]) => `<a href="${h}" class="${active === k ? "active" : ""}">${icon(ic)}${l}</a>`).join("")}</nav>`;
  document.body.style.setProperty("--banner-h", isDemo ? "32px" : "0px");
  $("#avatarBtn").onclick = (e) => { e.stopPropagation(); $("#profileMenu").classList.toggle("hidden"); };
  document.addEventListener("click", () => $("#profileMenu")?.classList.add("hidden"));
  $("#logoutBtn").onclick = async () => { await api("/api/logout", { method: "POST" }); App.user = null; location.hash = "#/login"; };
  return $("#main");
}

async function ensureUser() {
  if (!App.info) App.info = await api("/api/app-info");
  setAccent(App.info.accent_color);
  if (!App.user) App.user = await api("/api/me");
  return App.user;
}

/* ---------- login ---------- */
Router.add("/login", async () => {
  App.info = await api("/api/app-info"); setAccent(App.info.accent_color);
  $("#app").innerHTML = `<div class="auth-wrap"><div class="card auth-card">${brandHTML()}
    <h1>Know every price change</h1><p class="lead">See when competitors change their prices, without checking a single website.</p>
    <form id="lf" class="stack" novalidate><label class="field">Email<input class="input" type="email" name="email" autocomplete="username" placeholder="you@store.com"></label>
      <label class="field">Password<input class="input" type="password" name="password" autocomplete="current-password" placeholder="••••••••"></label>
      <div id="le" class="alert err hidden" role="alert"></div><button class="btn btn-primary btn-lg btn-block">Sign in</button></form>
    <div class="divider">or</div><button class="btn btn-lg btn-block" id="demoBtn">${icon("store")} View demo store</button>
    <p class="tiny muted" style="text-align:center;margin-top:10px">A fictitious store with 56 products and 3 fictitious competitors.</p>
    <div class="privacy-line">${icon("shield")}<span>Only public product pages are read, gently. <a href="/privacy" target="_blank">How it works</a></span></div></div></div>`;
  $("#lf").onsubmit = async (e) => {
    e.preventDefault(); const f = new FormData(e.target);
    try { await api("/api/login", { method: "POST", body: { email: f.get("email"), password: f.get("password") } }); App.user = null; location.hash = sessionStorage.getItem("afterLogin") || "#/"; }
    catch (err) { $("#le").textContent = err.message; $("#le").classList.remove("hidden"); }
  };
  $("#demoBtn").onclick = async () => {
    const b = $("#demoBtn"); b.disabled = true; b.innerHTML = `<span class="spinner"></span> Opening demo store…`;
    for (let i = 0; i < 40; i++) {
      try { await api("/api/demo-login", { method: "POST" }); App.user = null; location.hash = "#/"; return; }
      catch (e) { if (e.status !== 503) { toast(e.message, "err"); break; } b.innerHTML = `<span class="spinner"></span> Preparing the demo store…`; await new Promise((r) => setTimeout(r, 2000)); }
    }
    b.disabled = false; b.innerHTML = `${icon("store")} View demo store`;
  };
});

/* ---------- overview ---------- */
Router.add("/", async () => {
  await ensureUser();
  const o = await api("/api/overview");
  App.unread = o.unread_alerts;
  const run = o.last_run || {};
  const st = o.stand, total = o.stand_total || 1;
  const pctOf = (n) => Math.round((n / total) * 100);
  const greet = new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 17 ? "Good afternoon" : "Good evening";
  shell("overview", `
    ${o.is_demo ? `<div class="notice">${icon("info")}<span><b>Demo data.</b> Today's prices were collected live from three fictitious demo shop websites; earlier history (60 days) was simulated to show how charts look after weeks of tracking.</span></div>` : ""}
    <div class="page-head"><div><h1>${greet}</h1><p class="fresh"><span class="dot"></span>Prices checked ${run.finished_at ? fmt.when(run.finished_at) : "—"} · ${run.pages ?? 0} pages · ${run.pages ? Math.round((run.ok / run.pages) * 100) : 0}% read successfully</p></div>
      <div class="row wrap">${o.pending_matches ? `<a class="btn" href="#/matches">${icon("scale")} ${o.pending_matches} match${o.pending_matches > 1 ? "es" : ""} to review</a>` : ""}
        ${canEdit() ? `<button class="btn btn-primary" id="runBtn">${icon("refresh")} Check prices now</button>` : ""}</div></div>
    <div class="grid grid-4" style="margin-bottom:16px">
      <a class="card stat" href="#/products" style="color:inherit;text-decoration:none"><div class="label">${icon("tag")} Products tracked</div><div class="value">${o.cards.tracked}</div><div class="sub">${o.cards.listings} competitor pages</div></a>
      <a class="card stat" href="#/alerts" style="color:inherit;text-decoration:none"><div class="label">${icon("refresh")} Price changes today</div><div class="value">${o.cards.changes_today}</div><div class="sub">across all competitors</div></a>
      <a class="card stat attention" href="#/products?only=more_expensive" style="color:inherit;text-decoration:none"><div class="label">${icon("alert")} Competitor cheaper than you</div><div class="value" style="color:var(--bad)">${o.cards.competitor_cheaper}</div><div class="sub">products where someone beats your price</div></a>
      <a class="card stat good" href="#/alerts?type=out_of_stock" style="color:inherit;text-decoration:none"><div class="label">${icon("pkg")} Competitor out of stock</div><div class="value">${o.cards.competitor_oos}</div><div class="sub">chances to sell more today</div></a>
    </div>
    <div class="dash-grid" style="margin-bottom:16px">
      <div class="card"><div class="card-head"><h2>Where you stand</h2><span class="small muted">${total} products with competitor prices</span></div><div class="card-body">
        ${[["cheapest", "Cheapest", "var(--good)"], ["middle", "In the middle", "#94a3b8"], ["most_expensive", "Most expensive", "var(--bad)"]].map(([k, l, c]) => `
          <div class="stand-row"><span style="font-weight:550">${l}</span><div class="bar-bg"><div class="bar-fill" style="width:${pctOf(st[k])}%;background:${c}"></div></div><span class="pct">${pctOf(st[k])}%</span></div>`).join("")}
        <div style="margin-top:10px">${tip(`You're the cheapest seller on <b>${st.cheapest}</b> products and the most expensive on <b>${st.most_expensive}</b>.`)}</div></div></div>
      <div class="card"><div class="card-head"><h2>Today's biggest changes</h2><a class="small" href="#/alerts">All alerts</a></div>
        ${o.biggest_changes.length ? o.biggest_changes.map((c) => `<div class="change-row" data-p="${c.product_id}"><span class="comp-dot" style="background:${c.color}"></span>
          <div class="grow" style="min-width:0"><div style="font-weight:550;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.product)}</div><div class="tiny muted">${esc(c.competitor)} · ${money(c.prev_price)} → ${money(c.price)}</div></div>
          <span class="delta ${c.pct < 0 ? "down" : "up"}">${icon(c.pct < 0 ? "arrowDown" : "arrowUp")}${Math.abs(c.pct).toFixed(1)}%</span></div>`).join("")
          : `<div class="empty" style="padding:28px"><p>No price changes today.</p></div>`}</div>
    </div>
    <div class="card"><div class="card-head"><h2>Price trend: you vs. the market</h2><span class="small muted">Average price of the same products, last 30 days</span></div>
      <div class="chart-box"><canvas id="trend"></canvas></div></div>
    <p class="tiny muted" style="margin-top:12px">Checking ${o.cards.listings} competitor pages by hand every day would take about ${o.hours_saved_week} hours a week (at ${o.manual_seconds} seconds per page).</p>`, { wide: true });
  $$(".change-row").forEach((r) => (r.onclick = () => (location.hash = `#/product/${r.dataset.p}`)));
  $("#runBtn") && ($("#runBtn").onclick = () => runNow());
  await loadChart();
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
  new Chart($("#trend"), { type: "line", data: { labels: o.trend.map((t) => t.day.slice(5).split("-").reverse().join("/")),
    datasets: [{ label: "Your average price", data: o.trend.map((t) => t.you), borderColor: accent, backgroundColor: accent, tension: .3, pointRadius: 0, borderWidth: 2.5, spanGaps: true },
      { label: "Market average (competitors)", data: o.trend.map((t) => t.market), borderColor: "#94a3b8", backgroundColor: "#94a3b8", borderDash: [6, 4], tension: .3, pointRadius: 0, borderWidth: 2, spanGaps: true }] },
    options: { maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${money(c.parsed.y)}` } } },
      scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } }, y: { grid: { color: "#eef0f3" }, ticks: { callback: (v) => "Rs. " + v.toLocaleString() } } } } });
});

async function runNow() {
  const r = await api("/api/runs", { method: "POST" });
  if (r.status === "busy") return toast("A check is already running", "warn");
  toast("Checking competitor prices…", "info");
  const t0 = Date.now();
  const poll = async () => {
    const run = await api("/api/runs/latest");
    if (run.status === "done" && new Date(run.started_at) >= new Date(t0 - 5000)) { toast(`Done: ${run.ok} of ${run.pages} pages read, ${run.changes} price changes`); Router.go(); }
    else setTimeout(poll, 1500);
  };
  setTimeout(poll, 1500);
}

/* ---------- products table ---------- */
Router.add("/products", async (_, query) => {
  await ensureUser();
  const state = { q: query.q || "", category: query.category || "", brand: "", only: query.only || "", sort: query.sort || (query.only ? "gap" : "name") };
  const main = shell("products", `
    <div class="page-head"><div><h1>Products</h1><p>Your price next to every competitor's, checked every morning.</p></div>
      <div class="row wrap">${canEdit() ? `<button class="btn" id="addP">${icon("plus")} Add product</button>` : ""}<a class="btn" href="/api/products/export.xlsx">${icon("download")} Export to Excel</a></div></div>
    <div class="filters">
      <div class="input-icon">${icon("search")}<input class="input" id="q" placeholder="Search product or SKU" value="${esc(state.q)}"></div>
      <select class="input" id="cat"><option value="">All categories</option></select>
      <select class="input" id="brand"><option value="">All brands</option></select>
      <select class="input" id="only"><option value="">All products</option><option value="more_expensive">Only where I'm more expensive</option><option value="cheapest">Only where I'm cheapest</option><option value="top">Top products</option></select>
      <select class="input" id="sort"><option value="name">Sort by name</option><option value="gap">Sort by biggest gap</option><option value="price">Sort by price</option></select>
    </div>
    <div class="row between wrap" style="margin-bottom:10px"><div class="legend"><span><i style="background:var(--err-bg);border:1px solid #fecaca"></i>Competitor cheaper than you</span>
      <span><i style="background:var(--ok-bg);border:1px solid #bbf7d0"></i>You're cheaper</span><span><i style="background:#f3f4f6"></i>Same price</span><span style="text-decoration:line-through">Out of stock</span></div>
      <span class="small muted" id="count"></span></div>
    <div class="card"><div class="table-wrap" style="max-height:calc(100vh - 290px);overflow:auto"><table class="ptable"><thead id="th"></thead><tbody id="tb"><tr><td><div class="skeleton" style="height:18px;width:300px"></div></td></tr></tbody></table></div></div>`, { wide: true });
  $("#only").value = state.only; $("#sort").value = state.sort;
  let first = true;
  const load = async () => {
    const qs = new URLSearchParams({ q: state.q, category: state.category, brand: state.brand, only: state.only, sort: state.sort });
    const d = await api(`/api/products?${qs}`);
    if (first) {
      $("#cat").innerHTML += d.categories.map((c) => `<option ${c === state.category ? "selected" : ""}>${esc(c)}</option>`).join("");
      $("#brand").innerHTML += d.brands.map((c) => `<option>${esc(c)}</option>`).join("");
      first = false;
    }
    $("#th").innerHTML = `<tr><th>Product</th><th class="right">Your price</th>${d.competitors.map((c) => `<th class="right"><span class="comp-dot" style="background:${c.color};margin-right:6px"></span>${esc(c.name)}</th>`).join("")}
      <th class="right"><button data-s="gap">Gap to cheapest ${state.sort === "gap" ? "↓" : ""}</button></th><th>Position</th></tr>`;
    $("#count").textContent = `${d.rows.length} product${d.rows.length !== 1 ? "s" : ""} · prices from ${fmt.date(d.day, "DD Mon YYYY")}`;
    $("#tb").innerHTML = d.rows.length ? d.rows.map((r) => `<tr data-id="${r.id}"><td><div class="pname" title="${esc(r.name)}">${r.top ? "★ " : ""}${esc(r.name)}</div><div class="tiny muted">${esc(r.sku)} · ${esc(r.category)}</div></td>
      <td class="right num" style="font-weight:700">${money(r.price)}</td>
      ${d.competitors.map((c) => {
        const x = r.competitors[c.id] || {};
        if (!x.price) return `<td class="right"><span class="cell none">${x.tracked ? "no data" : "not tracked"}</span></td>`;
        const cls = x.price < r.price ? "cheaper" : x.price > r.price ? "dearer" : "same";
        return `<td class="right"><span class="cell ${cls} ${x.in_stock ? "" : "oos"}" title="${x.in_stock ? "" : "Out of stock"}">${money(x.price)}<small>${x.in_stock ? (x.regular_price ? `sale, was ${money(x.regular_price)}` : "in stock") : "out of stock"}</small></span></td>`;
      }).join("")}
      <td class="right num">${r.gap === null ? "—" : r.gap > 0 ? `<span style="color:var(--bad);font-weight:650">+${money(r.gap)}</span><div class="tiny muted">${pct(r.gap_pct)}</div>` : `<span style="color:var(--good);font-weight:650">cheapest</span>`}</td>
      <td><span class="pos ${r.rank === 1 ? "p1" : r.position === "most_expensive" ? "plast" : "pmid"}">${posLabel(r)}</span></td></tr>`).join("")
      : `<tr><td colspan="${d.competitors.length + 4}"><div class="empty"><div class="empty-icon">${icon("tag")}</div><h3>No products match</h3><p>Try a different filter, or add your first product.</p></div></td></tr>`;
    $$("#tb tr[data-id]").forEach((tr) => (tr.onclick = () => (location.hash = `#/product/${tr.dataset.id}`)));
    $$("#th [data-s]").forEach((b) => (b.onclick = () => { state.sort = "gap"; $("#sort").value = "gap"; load(); }));
  };
  let t;
  $("#q").oninput = (e) => { state.q = e.target.value; clearTimeout(t); t = setTimeout(load, 200); };
  $("#cat").onchange = (e) => { state.category = e.target.value; load(); };
  $("#brand").onchange = (e) => { state.brand = e.target.value; load(); };
  $("#only").onchange = (e) => { state.only = e.target.value; if (state.only === "more_expensive") { state.sort = "gap"; $("#sort").value = "gap"; } load(); };
  $("#sort").onchange = (e) => { state.sort = e.target.value; load(); };
  $("#addP") && ($("#addP").onclick = () => productModal());
  load();
});

function productModal(p = null) {
  return modal({ title: p ? "Edit product" : "Add product", confirm: p ? "Save" : "Add product",
    body: `<div class="stack"><div class="grid grid-2"><label class="field">SKU<input class="input" id="pSku" value="${esc(p?.sku || "")}"></label><label class="field">Your price (Rs.)<input class="input" id="pPrice" type="number" value="${p?.price ?? ""}"></label></div>
      <label class="field">Product name<input class="input" id="pName" value="${esc(p?.name || "")}"></label>
      <div class="grid grid-2"><label class="field">Brand<input class="input" id="pBrand" value="${esc(p?.brand || "")}"></label><label class="field">Category<input class="input" id="pCat" value="${esc(p?.category || "")}"></label></div>
      <div class="grid grid-2"><label class="field">Cost (optional, for margin)<input class="input" id="pCost" type="number" value="${p?.cost ?? ""}"></label>
        <label class="row" style="gap:8px;margin-top:24px"><input type="checkbox" id="pTop" ${p?.top ? "checked" : ""}> Top product</label></div></div>`,
    onConfirm: async (m) => {
      const body = { sku: $("#pSku", m).value, name: $("#pName", m).value, brand: $("#pBrand", m).value, category: $("#pCat", m).value,
        price: +$("#pPrice", m).value, cost: $("#pCost", m).value ? +$("#pCost", m).value : null, top: $("#pTop", m).checked };
      if (!body.sku || !body.name || !body.price) { toast("SKU, name and price are needed", "warn"); return false; }
      if (p) await api(`/api/products/${p.id}`, { method: "PUT", body }); else await api("/api/products", { method: "POST", body });
      toast(p ? "Product saved" : "Product added. Now add competitor pages for it."); Router.go();
    } });
}

/* ---------- product detail ---------- */
Router.add("/product/:id", async ({ id }, query) => {
  await ensureUser();
  const days = +(query.days || 30);
  const d = await api(`/api/products/${id}?days=${days}`);
  const p = d.product;
  const main = shell("products", `
    <div class="small muted" style="margin-bottom:10px"><a href="#/products">Products</a> / ${esc(p.sku)}</div>
    <div class="card card-pad" style="margin-bottom:16px"><div class="row between wrap" style="gap:16px">
      <div class="detail-head"><div class="prod-img">${icon("pkg")}</div><div><h1 style="font-size:23px">${esc(p.name)}</h1><div class="muted small">${esc(p.sku)} · ${esc(p.category)} · ${esc(p.brand || "")}${p.top ? " · ★ top product" : ""}</div></div></div>
      <div class="row wrap" style="gap:26px"><div><div class="small muted">Your price</div><div class="big-price">${money(d.your_price)}</div></div>
        <div><div class="small muted">Market average</div><div class="big-price" style="color:var(--text-3)">${money(d.market_avg)}</div></div>
        ${canEdit() ? `<button class="btn btn-sm" id="editP">${icon("edit")} Edit</button>` : ""}</div></div></div>
    <div class="grid grid-2" style="margin-bottom:16px">${d.insight ? `<div class="insight">${icon("info")}<span>${esc(d.insight)}</span></div>` : ""}
      ${d.suggestion ? `<div class="suggest">${icon("lightbulb")}<span>${esc(d.suggestion)}</span></div>` : ""}</div>
    <div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Price history</h2><div class="seg">${[7, 30, 90].map((n) => `<button data-d="${n}" class="${n === days ? "active" : ""}">${n} days</button>`).join("")}</div></div>
      <div class="chart-box tall"><canvas id="hist"></canvas></div></div>
    <div class="grid grid-2" style="align-items:start">
      <div class="card"><div class="card-head"><h2>Competitors</h2>${canEdit() ? `<button class="btn btn-sm" id="addL">${icon("link")} Track a page</button>` : ""}</div>
        <div class="table-wrap"><table class="table"><thead><tr><th>Competitor</th><th class="right">Price</th><th>Stock</th><th class="hide-sm">Last checked</th><th></th></tr></thead><tbody>
        ${d.series.length ? d.series.map((s) => `<tr><td><span class="comp-dot" style="background:${s.color};margin-right:8px"></span><b>${esc(s.competitor)}</b><div class="tiny muted" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(s.title || "")}">${esc(s.title || "")}</div></td>
          <td class="right num"><b style="color:${s.current < d.your_price ? "var(--bad)" : "var(--good)"}">${money(s.current)}</b>${s.regular_price ? `<div class="tiny muted"><s>${money(s.regular_price)}</s> sale</div>` : ""}</td>
          <td>${s.in_stock === null ? "—" : s.in_stock ? `<span class="badge ok">In stock</span>` : `<span class="badge err">Out of stock</span>`}</td>
          <td class="hide-sm small">${s.last_ok === false ? `<span style="color:var(--bad)" title="${esc(s.error || "")}">Failed: ${esc(s.error || "")}</span>` : esc(fmt.when(s.last_checked))}</td>
          <td><a class="btn btn-ghost icon-btn btn-sm" href="${s.url.startsWith("/") ? s.url : esc(s.url)}" target="_blank" rel="noopener" aria-label="Open competitor page">${icon("external")}</a></td></tr>`).join("")
          : `<tr><td colspan="5"><div class="empty" style="padding:24px"><p>No competitor pages tracked for this product yet.</p></div></td></tr>`}</tbody></table></div></div>
      <div class="card"><div class="card-head"><h2>Timeline of changes</h2></div>
        <ul class="timeline">${d.timeline.length ? d.timeline.slice(0, 15).map((t) => `<li><span class="when">${fmt.date(t.day, "DD Mon YYYY").slice(0, 6)}</span><span class="comp-dot" style="background:${t.color}"></span>
          <span class="grow">${t.type === "price" ? `<b>${esc(t.competitor)}</b> ${t.to < t.from ? "dropped" : "raised"} from ${money(t.from)} to <b>${money(t.to)}</b>` : `<b>${esc(t.competitor)}</b> ${t.in_stock ? "back in stock" : "went out of stock"}`}</span>
          ${t.type === "price" ? `<span class="delta ${t.to < t.from ? "down" : "up"}">${Math.abs(((t.to - t.from) / t.from) * 100).toFixed(0)}%</span>` : ""}</li>`).join("") : `<li class="muted">No changes recorded yet.</li>`}</ul></div>
    </div>`, { wide: true });
  $$(".seg [data-d]").forEach((b) => (b.onclick = () => (location.hash = `#/product/${id}?days=${b.dataset.d}`)));
  $("#editP") && ($("#editP").onclick = () => productModal({ ...p, price: d.your_price }));
  $("#addL") && ($("#addL").onclick = () => modal({ title: "Track a competitor page", confirm: "Track and test",
    body: `<div class="stack"><label class="field">Competitor<select class="input" id="lc">${d.competitors.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></label>
      <label class="field">Product page address<input class="input" id="lu" placeholder="https://competitor.com/products/..."></label>
      <p class="small muted">We read the page once now to check the price can be found. Only public pages are read.</p></div>`,
    onConfirm: async (m) => {
      const r = await api("/api/listings", { method: "POST", body: { product_id: +id, competitor_id: +$("#lc", m).value, url: $("#lu", m).value } });
      if (r.ok) toast(`Found ${money(r.price)} (${r.in_stock ? "in stock" : "out of stock"}) using ${r.method}`); else toast(r.error, "warn", 6000);
      Router.go();
    } }));
  await loadChart();
  const labels = d.own.map((o) => o.day.slice(5).split("-").reverse().join("/"));
  const datasets = [{ label: "You", data: d.own.map((o) => o.price), borderColor: "#111827", backgroundColor: "#111827", borderWidth: 3, pointRadius: 0, stepped: true }]
    .concat(d.series.map((s) => ({ label: s.competitor, data: d.own.map((o) => { const pt = s.points.find((x) => x.day === o.day); return pt ? pt.price : null; }),
      borderColor: s.color, backgroundColor: s.color, borderWidth: 2, pointRadius: days <= 7 ? 3 : 0, stepped: true, spanGaps: true,
      segment: { borderDash: (ctx) => { const pt = s.points.find((x) => x.day === d.own[ctx.p1DataIndex]?.day); return pt && !pt.in_stock ? [3, 4] : undefined; } } })));
  new Chart($("#hist"), { type: "line", data: { labels, datasets },
    options: { maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${money(c.parsed.y)}` } } },
      scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }, y: { grid: { color: "#eef0f3" }, ticks: { callback: (v) => "Rs. " + v.toLocaleString() } } } } });
});

/* ---------- alerts ---------- */
Router.add("/alerts", async (_, query) => {
  await ensureUser();
  const [d, s] = await Promise.all([api(`/api/alerts?limit=300${query.type ? `&type=${query.type}` : ""}`), api("/api/settings")]);
  api("/api/alerts/read", { method: "POST" }); App.unread = 0;
  let type = query.type || "", comp = 0;
  const main = shell("alerts", `
    <div class="page-head"><div><h1>Alerts</h1><p>Every important change, newest first. The same alerts go to email, WhatsApp or Telegram if you switch them on.</p></div></div>
    <div class="row wrap" style="margin-bottom:14px"><div class="chips" id="types"><button class="chip ${!type ? "active" : ""}" data-t="">All</button>${Object.entries(d.types).map(([k, v]) => `<button class="chip ${type === k ? "active" : ""}" data-t="${k}">${esc(v)}</button>`).join("")}</div>
      <select class="input" id="ac" style="width:180px"><option value="0">All competitors</option>${d.competitors.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) 340px;align-items:start" id="ag">
      <div class="card" id="feed"></div>
      <div class="stack"><div class="card"><div class="card-head"><h2>Alert rules</h2></div><div class="card-body" id="rules"></div></div>
        <div class="card"><div class="card-head"><h2>Send alerts to</h2></div><div class="card-body" id="chans"></div></div></div></div>`, { wide: true });
  if (window.innerWidth < 1000) $("#ag").style.gridTemplateColumns = "minmax(0,1fr)";
  const renderFeed = (list) => {
    let last = "";
    $("#feed").innerHTML = list.length ? list.map((a) => {
      const [ic, sev] = ALERT_IC[a.type] || ["bell", "info"];
      const head = a.day !== last ? `<div class="day-label">${a.day === new Date().toISOString().slice(0, 10) ? "Today" : fmt.date(a.day, "DD Mon YYYY")}</div>` : "";
      last = a.day;
      return `${head}<div class="alert-item ${a.is_read ? "" : "unread"}"><span class="a-ic ${a.severity === "high" ? "high" : sev}">${icon(ic)}</span>
        <div class="grow"><div style="font-weight:550">${esc(a.message)}</div><div class="tiny muted" style="margin-top:3px">${esc(d.types[a.type])}${a.competitor ? ` · ${esc(a.competitor)}` : ""}${a.delivered && a.delivered !== "in_app" && a.delivered !== "demo" ? ` · sent by ${esc(a.delivered)}` : ""}</div></div>
        ${a.product_id ? `<a class="btn btn-sm" href="#/product/${a.product_id}">View</a>` : a.type === "new_product" ? `<a class="btn btn-sm" href="#/matches">Review</a>` : ""}</div>`;
    }).join("") : `<div class="empty"><div class="empty-icon">${icon("bell")}</div><h3>No alerts</h3><p>Nothing matches this filter.</p></div>`;
  };
  const refresh = async () => { const r = await api(`/api/alerts?limit=300${type ? `&type=${type}` : ""}${comp ? `&competitor=${comp}` : ""}`); renderFeed(r.alerts); };
  renderFeed(d.alerts);
  $$("#types .chip").forEach((c) => (c.onclick = () => { type = c.dataset.t; $$("#types .chip").forEach((x) => x.classList.toggle("active", x === c)); refresh(); }));
  $("#ac").onchange = (e) => { comp = +e.target.value; refresh(); };
  const r = s.rules, ro = !canEdit() ? "disabled" : "";
  $("#rules").innerHTML = `
    <div class="rule-row"><span class="grow">Competitor cheaper than me by at least</span><input class="input" type="number" id="r1" value="${r.cheaper_than_you_pct}" min="1" max="50" ${ro}><span>%</span></div>
    <div class="rule-row"><span class="grow">Price drop of at least</span><input class="input" type="number" id="r2" value="${r.price_drop_pct}" min="1" max="50" ${ro}><span>%</span></div>
    <div class="rule-row"><span class="grow">Price increase of at least</span><input class="input" type="number" id="r3" value="${r.price_increase_pct}" min="1" max="50" ${ro}><span>%</span></div>
    <label class="rule-row"><span class="switch"><input type="checkbox" id="r4" ${r.top_out_of_stock ? "checked" : ""} ${ro}><span></span></span><span>Stock alerts only for top products</span></label>
    <label class="rule-row"><span class="switch"><input type="checkbox" id="r5" ${r.back_in_stock ? "checked" : ""} ${ro}><span></span></span><span>Back in stock</span></label>
    ${isAdmin() ? `<button class="btn btn-primary btn-sm" id="saveR" style="margin-top:10px">Save rules</button>` : ""}`;
  const cs = s.channel_status;
  $("#chans").innerHTML = [["in_app", "In the app", true, "Always on"], ["email", "Email (daily report)", cs.email, "Set SMTP_HOST in .env"], ["whatsapp", "WhatsApp", cs.whatsapp, "Set WHATSAPP_TOKEN in .env"], ["telegram", "Telegram", cs.telegram, "Set TELEGRAM_BOT_TOKEN in .env"]].map(([k, l, ok, hint]) =>
    `<label class="chan"><span class="switch"><input type="checkbox" data-ch="${k}" ${s.channels[k] ? "checked" : ""} ${k === "in_app" || !isAdmin() ? "disabled" : ""}><span></span></span>
      <span class="grow"><b style="font-weight:550">${l}</b><div class="tiny muted">${ok ? (k === "in_app" ? hint : "Connected") : hint}</div></span></label>`).join("") +
    (isAdmin() ? `<div class="grid grid-2" style="margin-top:10px"><label class="field">WhatsApp number<input class="input" id="waTo" value="${esc(s.whatsapp_to)}" placeholder="923001234567"></label><label class="field">Telegram chat ID<input class="input" id="tgId" value="${esc(s.telegram_chat_id)}"></label></div>
      <button class="btn btn-sm" id="saveC" style="margin-top:10px">Save delivery</button>` : "");
  $("#saveR") && ($("#saveR").onclick = async () => {
    await api("/api/settings", { method: "PUT", body: { rules: { cheaper_than_you_pct: +$("#r1").value, price_drop_pct: +$("#r2").value, price_increase_pct: +$("#r3").value,
      top_out_of_stock: $("#r4").checked, back_in_stock: $("#r5").checked, new_product: true } } });
    toast("Rules saved. They apply from the next check.");
  });
  $("#saveC") && ($("#saveC").onclick = async () => {
    const channels = { in_app: true }; $$("[data-ch]").forEach((c) => { if (c.dataset.ch !== "in_app") channels[c.dataset.ch] = c.checked; });
    await api("/api/settings", { method: "PUT", body: { channels, whatsapp_to: $("#waTo").value.trim(), telegram_chat_id: $("#tgId").value.trim() } }); toast("Delivery settings saved");
  });
});

/* ---------- match review ---------- */
Router.add("/matches", async () => {
  await ensureUser();
  const d = await api("/api/matches");
  let i = 0;
  const main = shell("competitors", `<div style="max-width:880px;margin:0 auto">
    <div class="page-head"><div><h1>Match review</h1><p>New competitor listings we found. Confirm which of your products each one is, so prices are compared correctly.</p></div></div>
    <div id="mBody"></div><div style="margin-top:14px;display:flex;justify-content:center">${tip("Keyboard: <kbd>Y</kbd> yes, <kbd>N</kbd> no, <kbd>S</kbd> skip.")}</div></div>`);
  const render = () => {
    const m = d.pending[i];
    if (!m) { $("#mBody").innerHTML = `<div class="card"><div class="empty"><div class="empty-icon">${icon("checkCircle")}</div><h3>All matches reviewed</h3><p>${d.reviewed} competitor listings are matched to your products.</p><a class="btn btn-primary" href="#/competitors">Back to competitors</a></div></div>`; return; }
    $("#mBody").innerHTML = `<div class="row between" style="margin-bottom:10px"><span class="small muted">${i + 1} of ${d.pending.length} to review</span>
      <span class="conf ${m.label.split(" ")[0]}">${m.label === "No match" ? "No similar product found" : `${m.label} confidence (${Math.round(m.confidence * 100)}%)`}</span></div>
      <div class="card"><div class="match-card">
        <div class="match-side"><div class="tiny muted" style="font-weight:700;letter-spacing:.06em">YOUR PRODUCT</div><div class="ph">${icon("pkg")}</div>
          ${m.product_id ? `<h3>${esc(m.product)}</h3><div class="small muted">${esc(m.sku)} · ${esc(m.category)}</div><div class="big-price" style="font-size:22px;margin-top:8px">${money(m.your_price)}</div>`
            : `<label class="field">Which of your products is it?<select class="input" id="pick"><option value="">Choose a product…</option>${d.products.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label>
               <p class="small muted" style="margin-top:8px">Or press <b>No</b> if you don't sell it (it stays out of your comparisons).</p>`}</div>
        <div class="match-mid">${icon("scale")}</div>
        <div class="match-side"><div class="tiny muted" style="font-weight:700;letter-spacing:.06em"><span class="comp-dot" style="background:${m.color};margin-right:6px"></span>${esc(m.competitor).toUpperCase()}</div><div class="ph">${icon("store")}</div>
          <h3>${esc(m.title || m.url)}</h3><a class="small" href="${esc(m.url)}" target="_blank" rel="noopener">Open their page ${icon("external")}</a>
          <div class="big-price" style="font-size:22px;margin-top:8px">${money(m.their_price)}</div></div>
      </div><div class="match-actions">
        <button class="btn btn-primary btn-lg" data-dec="yes">${icon("check")} Yes, same product</button>
        <button class="btn btn-lg btn-danger" data-dec="no">${icon("x")} No</button><button class="btn btn-lg btn-ghost" data-dec="skip">Skip</button></div></div>`;
    $$("[data-dec]").forEach((b) => (b.onclick = () => decide(b.dataset.dec)));
  };
  const decide = async (dec) => {
    const m = d.pending[i]; if (!m || !canEdit()) return toast("Only admins and analysts can confirm matches", "warn");
    const product_id = m.product_id || +($("#pick")?.value || 0) || null;
    if (dec === "yes" && !product_id) return toast("Choose which of your products it is", "warn");
    await api(`/api/matches/${m.id}`, { method: "POST", body: { decision: dec, product_id } });
    toast(dec === "yes" ? "Matched. Its price is now compared every day." : dec === "no" ? "Marked as not the same product" : "Skipped for now", dec === "no" ? "info" : "ok", 1800);
    if (dec === "yes") d.reviewed++;
    i++; render();
  };
  const onKey = (e) => { if (["INPUT", "SELECT"].includes(e.target.tagName)) return; const k = { y: "yes", n: "no", s: "skip" }[e.key.toLowerCase()]; if (k) decide(k); };
  document.addEventListener("keydown", onKey);
  render();
  return () => document.removeEventListener("keydown", onKey);
});

/* ---------- competitors & data health ---------- */
Router.add("/competitors", async () => {
  await ensureUser();
  const d = await api("/api/competitors");
  const run = d.last_run || {};
  const pending = d.competitors.reduce((s, c) => s + c.pending, 0);
  const label = { good: "All good", warn: "Some pages failed", bad: "Site not reachable", idle: "Not checked yet", paused: "Paused" };
  const main = shell("competitors", `
    <div class="page-head"><div><h1>Competitors &amp; data health</h1><p>Which sites are tracked, when they were last checked, and how reliably prices were read.</p></div>
      <div class="row wrap">${pending ? `<a class="btn" href="#/matches">${icon("scale")} Review ${pending} match${pending > 1 ? "es" : ""}</a>` : ""}${canEdit() ? `<button class="btn" id="addC">${icon("plus")} Add competitor</button><button class="btn btn-primary" id="runBtn">${icon("refresh")} Check now</button>` : ""}</div></div>
    <div class="card card-pad" style="margin-bottom:16px"><div class="row wrap" style="gap:30px">
      <div><div class="small muted">Last check</div><b>${run.finished_at ? fmt.when(run.finished_at) : "—"}</b></div><div><div class="small muted">Pages read</div><b>${run.ok ?? 0} of ${run.pages ?? 0}</b></div>
      <div><div class="small muted">Price changes found</div><b>${run.changes ?? 0}</b></div><div><div class="small muted">Started by</div><b style="text-transform:capitalize">${esc((run.trigger || "—").replace("-", " "))}</b></div></div></div>
    <div class="grid grid-3">${d.competitors.map((c) => `<div class="card comp-card">
      <div class="row between"><div class="row"><span class="comp-dot" style="background:${c.color};width:14px;height:14px"></span><h3>${esc(c.name)}</h3></div><span class="health ${c.status}">${label[c.status]}</span></div>
      <a class="small" href="${esc(c.website)}" target="_blank" rel="noopener">${esc(c.website.startsWith("/") ? location.host + c.website : c.website)}</a>${c.is_demo ? ` <span class="badge info plain">Demo shop</span>` : ""}
      <div class="kv"><div><b>${c.tracked}</b><span>products tracked</span></div><div><b>${c.success_rate ?? "—"}${c.success_rate != null ? "%" : ""}</b><span>read today</span></div><div><b>${c.week_rate ?? "—"}${c.week_rate != null ? "%" : ""}</b><span>last 7 days</span></div></div>
      <div class="small muted" style="margin-top:12px">Last checked ${c.last_check ? fmt.when(c.last_check) : "never"} · reads ${c.price_selector ? "custom selector" : "standard product data"}</div>
      ${c.errors.length ? `<div class="alert warn" style="margin-top:10px">${icon("alert")}<div>${c.errors.map(esc).join("<br>")}</div></div>` : ""}
      ${canEdit() ? `<div class="row" style="margin-top:12px"><button class="btn btn-sm" data-edit="${c.id}">${icon("edit")} Settings</button></div>` : ""}</div>`).join("")}</div>
    <div style="margin-top:14px">${tip("Websites change. When a site fails, its card turns amber or red and the error is shown, and fixing it is part of maintenance.")}</div>`);
  $("#runBtn") && ($("#runBtn").onclick = runNow);
  const compModal = (c = {}) => modal({ title: c.id ? `${c.name} settings` : "Add competitor", confirm: "Save",
    body: `<div class="stack"><label class="field">Name<input class="input" id="cn" value="${esc(c.name || "")}"></label><label class="field">Website<input class="input" id="cw" value="${esc(c.website || "")}" placeholder="https://"></label>
      <label class="field">Catalogue page (optional, to find new products)<input class="input" id="cc" value="${esc(c.catalog_url || "")}"></label>
      <div class="grid grid-2"><label class="field">Price selector (optional)<input class="input" id="cp" value="${esc(c.price_selector || "")}" placeholder=".product-price"></label>
        <label class="field">Stock selector (optional)<input class="input" id="cs" value="${esc(c.stock_selector || "")}" placeholder=".stock-status"></label></div>
      <p class="small muted">Most stores publish standard product data, so selectors are only needed for sites without it.</p>
      <div class="row" style="gap:10px"><label class="field" style="flex:1">Colour<input class="input" type="color" id="ccol" value="${esc(c.color || "#64748b")}" style="height:40px;padding:3px"></label>
        ${c.id ? `<label class="row" style="gap:8px;margin-top:22px"><input type="checkbox" id="cact" ${c.active ? "checked" : ""}> Active</label>` : ""}</div></div>`,
    onConfirm: async (m) => {
      const body = { name: $("#cn", m).value, website: $("#cw", m).value, catalog_url: $("#cc", m).value, price_selector: $("#cp", m).value, stock_selector: $("#cs", m).value,
        color: $("#ccol", m).value, active: c.id ? $("#cact", m).checked : true };
      if (!body.name) { toast("Name is required", "warn"); return false; }
      if (c.id) await api(`/api/competitors/${c.id}`, { method: "PUT", body }); else await api("/api/competitors", { method: "POST", body });
      toast("Competitor saved"); Router.go();
    } });
  $("#addC") && ($("#addC").onclick = () => compModal());
  $$("[data-edit]").forEach((b) => (b.onclick = () => compModal(d.competitors.find((c) => c.id === +b.dataset.edit))));
});

/* ---------- reports ---------- */
Router.add("/reports", async (_, query) => {
  await ensureUser();
  const [d, s] = await Promise.all([api("/api/reports"), api("/api/settings")]);
  let active = d.reports.find((r) => String(r.id) === query.id) || d.reports[0];
  const main = shell("reports", `
    <div class="page-head"><div><h1>Reports</h1><p>The morning report and the weekly summary, as email, PDF and Excel.</p></div></div>
    <div class="reports-grid"><div class="stack">
      <div class="card"><div class="card-head"><h2>Report library</h2><span class="small muted">${d.channels.email ? "Emailed automatically" : "Email not connected: reports stay here"}</span></div><div id="rlist"></div></div>
      <div class="card"><div class="card-head"><h2>Schedule</h2></div><div class="card-body stack">
        <div class="grid grid-2"><label class="field">Check prices every day at<input class="input" type="time" id="ct" value="${esc(s.check_time)}"></label><label class="field">Send the morning report at<input class="input" type="time" id="rt" value="${esc(s.report_time)}"></label></div>
        <label class="field">Morning report goes to (comma separated)<input class="input" id="dr" value="${esc(s.daily_recipients.join(", "))}"></label>
        <div class="grid grid-2"><label class="field">Weekly summary on<select class="input" id="wd">${["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((x) => `<option ${x === s.weekly_day ? "selected" : ""}>${x}</option>`).join("")}</select></label>
          <label class="field">Weekly summary goes to<input class="input" id="wr" value="${esc(s.weekly_recipients.join(", "))}"></label></div>
        ${isAdmin() ? `<div><button class="btn btn-primary" id="saveS">Save schedule</button></div>` : ""}</div></div></div>
      <div><div class="row between" style="margin-bottom:10px"><b>Preview on a phone</b><div class="row" id="rbtns"></div></div><div class="phone"><iframe id="pv" title="Report preview"></iframe></div></div></div>`, { wide: true });
  const show = () => {
    $("#rlist").innerHTML = d.reports.map((r) => `<div class="report-row ${r.id === active?.id ? "active" : ""}" data-id="${r.id}" style="cursor:pointer">
      <span class="a-ic ${r.kind === "weekly" ? "good" : "info"}">${icon("report")}</span><div class="grow" style="min-width:0"><div style="font-weight:550">${esc(r.title)}</div>
      <div class="tiny muted">${r.kind === "weekly" ? "Weekly summary" : "Morning report"} · ${r.sent_to ? `Sent to ${esc(r.sent_to)}` : "Not sent yet"}</div></div></div>`).join("") || `<div class="empty"><p>No reports yet. The first one is created after the first price check.</p></div>`;
    $$(".report-row").forEach((el) => (el.onclick = () => { active = d.reports.find((r) => r.id === +el.dataset.id); show(); }));
    if (!active) return;
    $("#pv").src = `/api/reports/${active.id}/html`;
    $("#rbtns").innerHTML = `<a class="btn btn-sm" href="/api/reports/${active.id}/pdf">${icon("download")} PDF</a><a class="btn btn-sm" href="/api/reports/${active.id}/xlsx">${icon("table")} Excel</a>
      ${canEdit() ? `<button class="btn btn-sm btn-primary" id="sendR">${icon("mail")} Send now</button>` : ""}`;
    $("#sendR") && ($("#sendR").onclick = async () => { const r = await api(`/api/reports/${active.id}/send`, { method: "POST" }); toast(r.sent_to === "outbox" ? "Email isn't connected yet, so the report stays in the library." : `Sent to ${r.sent_to}`, r.sent_to === "outbox" ? "warn" : "ok", 4500); });
  };
  show();
  $("#saveS") && ($("#saveS").onclick = async () => {
    const split = (v) => v.split(",").map((x) => x.trim()).filter(Boolean);
    try { await api("/api/settings", { method: "PUT", body: { check_time: $("#ct").value, report_time: $("#rt").value, daily_recipients: split($("#dr").value), weekly_recipients: split($("#wr").value), weekly_day: $("#wd").value } }); toast("Schedule saved"); }
    catch (e) { toast(e.message, "err"); }
  });
});

/* ---------- settings ---------- */
Router.add("/settings", async (_, query) => {
  await ensureUser();
  if (!isAdmin()) { location.hash = "#/"; return; }
  let s = await api("/api/settings");
  let tab = query.tab || "general";
  const main = shell("settings", `<div class="settings-layout"><div class="page-head"><div><h1>Settings</h1><p>Your store, products, team and branding.</p></div></div>
    <div class="tabs" id="tabs">${[["general", "General"], ["products", "Products & import"], ["team", "Team"], ["branding", "Branding"]].map(([k, l]) => `<button data-t="${k}" class="${k === tab ? "active" : ""}">${l}</button>`).join("")}</div><div id="tb"></div></div>`);
  const save = async (patch) => { try { s = await api("/api/settings", { method: "PUT", body: patch }); App.info = await api("/api/app-info"); toast("Saved"); return true; } catch (e) { toast(e.message, "err"); return false; } };
  const tabs = {
    general: () => `<div class="card card-body stack" style="gap:18px"><label class="field">Store name<input class="input" id="sn" value="${esc(s.company_name)}"></label>
      <div class="grid grid-2"><label class="field">Currency<select class="input" id="scur">${["PKR", "USD", "AED", "SAR", "GBP", "EUR"].map((c) => `<option ${c === s.currency ? "selected" : ""}>${c}</option>`).join("")}</select></label>
        <label class="field">Show prices with<select class="input" id="srd"><option value="0" ${!s.rounding ? "selected" : ""}>No decimals (1,499)</option><option value="2" ${s.rounding == 2 ? "selected" : ""}>2 decimals (1,499.00)</option></select></label></div>
      <label class="field" style="max-width:260px">Daily price check at<input class="input" type="time" id="sct" value="${esc(s.check_time)}"></label>
      <div><button class="btn btn-primary" id="sv">Save</button></div></div>`,
    products: () => `<div class="card card-body stack" style="gap:14px"><h3>Import your product list</h3>
      <p class="muted small">Upload a CSV with columns <code>sku, name, price</code> and optionally <code>brand, category, cost, top</code>. Existing SKUs are updated.</p>
      <div class="row wrap"><label class="btn btn-primary">${icon("upload")} Upload CSV<input type="file" id="csv" accept=".csv,text/csv" hidden></label><button class="btn" id="tmpl">${icon("download")} Download template</button></div>
      <div class="alert info">${icon("info")}<div>Categories in use: ${s.categories.map(esc).join(", ") || "none yet"}. Then add competitor pages per product (Products → product → Track a page), or set a competitor's catalogue page so new listings appear in Match review.</div></div></div>`,
    team: () => `<div class="card"><div class="card-head"><h2>Team</h2><button class="btn btn-sm btn-primary" id="addU">${icon("plus")} Add person</button></div><div class="card-body" id="ul"></div></div>
      <div style="margin-top:12px">${tip("<b>Admins</b> change everything. <b>Analysts</b> manage products, competitors and matches. <b>Viewers</b> see dashboards and reports.")}</div>`,
    branding: () => `<div class="card card-body stack" style="gap:18px"><div class="row wrap" style="gap:18px"><div class="card" style="width:180px;height:70px;display:grid;place-items:center;background:var(--surface-2)">${s.logo_url ? `<img src="${esc(s.logo_url)}" style="max-height:48px;max-width:150px" alt="Logo">` : `<span class="muted small">No logo yet</span>`}</div>
      <label class="btn">${icon("upload")} Upload logo<input type="file" id="logo" accept=".png,.jpg,.jpeg,.svg,.webp" hidden></label></div>
      <label class="field" style="max-width:200px">Accent colour<input class="input" type="color" id="acc" value="${esc(s.accent_color)}" style="height:42px;padding:3px"></label>
      <div><button class="btn btn-primary" id="sb">Save branding</button></div></div>`,
  };
  const render = () => {
    $("#tb").innerHTML = tabs[tab](); $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.t === tab));
    if (tab === "general") $("#sv").onclick = () => save({ company_name: $("#sn").value.trim(), currency: $("#scur").value, rounding: +$("#srd").value, check_time: $("#sct").value }).then((ok) => ok && Router.go());
    if (tab === "products") {
      $("#csv").onchange = async (e) => { const fd = new FormData(); fd.append("file", e.target.files[0]); try { const r = await api("/api/products/import", { method: "POST", form: fd }); toast(`Imported: ${r.added} added, ${r.updated} updated`); } catch (err) { toast(err.message, "err"); } };
      $("#tmpl").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["sku,name,price,brand,category,cost,top\nSKU-001,Example 20W Charger,1499,Example,Chargers,950,yes\n"], { type: "text/csv" })); a.download = "products_template.csv"; a.click(); };
    }
    if (tab === "team") loadTeam();
    if (tab === "branding") {
      $("#acc").oninput = (e) => setAccent(e.target.value);
      $("#sb").onclick = () => save({ accent_color: $("#acc").value });
      $("#logo").onchange = async (e) => { const fd = new FormData(); fd.append("file", e.target.files[0]); try { await api("/api/settings/logo", { method: "POST", form: fd }); App.info = await api("/api/app-info"); Router.go(); } catch (err) { toast(err.message, "err"); } };
    }
  };
  const loadTeam = async () => {
    const us = await api("/api/users");
    $("#ul").innerHTML = us.map((u) => `<div class="member"><span class="avatar" style="cursor:default">${esc(initials(u.name))}</span><div class="grow"><b style="font-weight:600">${esc(u.name)}</b><div class="small muted">${esc(u.email)}</div></div>
      ${u.id !== App.user.id ? `<select class="input" style="width:130px;height:34px" data-r="${u.id}">${["admin", "analyst", "viewer"].map((r) => `<option value="${r}" ${u.role === r ? "selected" : ""}>${r[0].toUpperCase() + r.slice(1)}</option>`).join("")}</select>
      <button class="btn btn-ghost icon-btn btn-sm" data-del="${u.id}" aria-label="Remove">${icon("trash")}</button>` : `<span class="badge neutral plain">You</span>`}</div>`).join("");
    $$("[data-r]").forEach((sel) => (sel.onchange = async () => { await api(`/api/users/${sel.dataset.r}`, { method: "PATCH", body: { role: sel.value } }); toast("Role updated"); }));
    $$("#ul [data-del]").forEach((b) => (b.onclick = async () => { if (await modal({ title: "Remove person?", body: "<p>They lose access immediately.</p>", confirm: "Remove", danger: true })) { await api(`/api/users/${b.dataset.del}`, { method: "DELETE" }); loadTeam(); } }));
    $("#addU").onclick = () => modal({ title: "Add person", confirm: "Add", body: `<div class="stack"><label class="field">Name<input class="input" id="un"></label><label class="field">Email<input class="input" id="ue"></label>
      <label class="field">Role<select class="input" id="ur"><option value="viewer">Viewer</option><option value="analyst">Analyst</option><option value="admin">Admin</option></select></label></div>`,
      onConfirm: async (m) => { const r = await api("/api/users", { method: "POST", body: { name: $("#un", m).value, email: $("#ue", m).value, role: $("#ur", m).value } }); loadTeam();
        setTimeout(() => modal({ title: "Person added", body: `<p>Temporary password: <code style="font-size:16px">${esc(r.temporary_password)}</code></p>`, confirm: "Done", cancel: null }), 50); } });
  };
  $$("#tabs button").forEach((b) => (b.onclick = () => { tab = b.dataset.t; render(); }));
  render();
});

(async () => {
  try { App.info = await api("/api/app-info"); setAccent(App.info.accent_color); } catch {}
  Router.start();
})();
