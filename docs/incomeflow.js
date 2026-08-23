/* StockLab — income-statement flow diagram (Sankey) for the deep-dive page.
 *
 * Geometry rule: x = level in the income statement, y = inherited from the
 * parent the branch splits from. The surviving profit line is TOP-ANCHORED at
 * every level and each cost peels off directly beneath it, so vertical
 * position always encodes the hierarchy. Every bar height uses one dollar
 * scale, so all splits are visually to scale.
 *
 * Loss handling: a Sankey cannot show a negative branch (children would exceed
 * the parent). When a profit line is <= 0 the parent flows entirely into the
 * cost side and the shortfall is drawn as a separate red "loss" node, which is
 * the honest representation rather than a broken ribbon.
 *
 * Segment detail (left column) is optional: data/segments/<TICKER>.json. When
 * absent the diagram simply starts at Revenue.
 */
(() => {
  const NSU = "http://www.w3.org/2000/svg";
  const C = {
    blue: "#4b93e8", blueR: "#4b93e8", green: "#2ebd63", greenR: "#2ebd63",
    red: "#ef4a44", redR: "#ef4a44", violet: "#a855f7",
    ink: "#e6edf3", muted: "#93a1b5"
  };
  const OPR = 0.30;                       // ribbon opacity

  const mk = (t, a) => { const e = document.createElementNS(NSU, t);
    for (const k in a) e.setAttribute(k, a[k]); return e; };

  function money(v) {
    const a = Math.abs(v);
    if (a >= 1e12) return "$" + (v / 1e12).toFixed(2) + "T";
    if (a >= 1e9)  return "$" + (v / 1e9).toFixed(a >= 1e10 ? 1 : 2) + "B";
    if (a >= 1e6)  return "$" + (v / 1e6).toFixed(0) + "M";
    return "$" + (v / 1e3).toFixed(0) + "K";
  }
  const pct = (n, d) => (d > 0 ? (100 * n / d).toFixed(1) + "%" : "—");
  const last = a => (Array.isArray(a) && a.length ? a[a.length - 1] : null);
  const num = v => (typeof v === "number" && isFinite(v) ? v : null);

  /* ---------- pull the latest quarter's income statement out of history ---------- */
  function model(h) {
    const s = h.series || {}, qs = h.quarters || [];
    const at = k => num(last(s[k]));
    const prevAt = k => (Array.isArray(s[k]) && s[k].length > 4
      ? num(s[k][s[k].length - 5]) : null);          // same quarter, prior year

    const revenue = at("revenue");
    if (!revenue || revenue <= 0) return null;
    const gross = at("gross_profit");
    const cogs  = at("cost_of_revenue") != null ? at("cost_of_revenue")
                : (gross != null ? revenue - gross : null);
    const opinc = at("operating_income");
    const opex  = (gross != null && opinc != null) ? gross - opinc : null;
    const net   = at("net_income");
    const pretax = at("pretax_income");
    const tax    = at("tax_expense");
    const other  = (pretax != null && opinc != null) ? pretax - opinc
                 : (net != null && opinc != null ? net - opinc : null);

    const yoy = k => { const a = at(k), b = prevAt(k);
      return (a != null && b != null && b !== 0)
        ? (a - b) / Math.abs(b) : null; };
    const fmtY = v => v == null ? "" : (v >= 0 ? "+" : "−") +
      (Math.abs(v) * 100).toFixed(0) + "% Y/Y";

    return { q: last(qs), revenue, cogs, gross, opex, opinc, other, pretax, tax, net,
             revYoY: fmtY(yoy("revenue")), opYoY: fmtY(yoy("operating_income")),
             netYoY: fmtY(yoy("net_income")),
             rnd: at("rnd"), sga: at("sga") };
  }

  /* ---------- render ---------- */
  function render(host, hist, segData) {
    const m = model(hist);
    host.innerHTML = "";
    if (!m) { host.innerHTML =
      '<div class="flow-empty">No income-statement data for this quarter.</div>'; return; }

    const W = 1280, H = 520, PADT = 96, PADB = 92, NW = 11;
    const svg = mk("svg", { viewBox: `0 0 ${W} ${H}`, class: "flowsvg",
      role: "img", "aria-label": hist.ticker + " income statement flow" });

    const T = (x, y, s, o = {}) => { const t = mk("text", { x, y,
      "font-size": o.fs || 11.5, "font-weight": o.fw || 400,
      fill: o.fill || C.ink, "text-anchor": o.an || "start" });
      t.textContent = s; svg.appendChild(t); return t; };
    const band = (x0, y0, x1, y1, h, fill) => { if (h <= 0.4) return;
      const mx = (x0 + x1) / 2;
      svg.appendChild(mk("path", { fill, opacity: OPR,
        d: `M${x0},${y0} C${mx},${y0} ${mx},${y1} ${x1},${y1} L${x1},${y1 + h} `
         + `C${mx},${y1 + h} ${mx},${y0 + h} ${x0},${y0 + h} Z` })); };
    const bar = (x, y, h, fill) => { if (h <= 0.4) return;
      svg.appendChild(mk("rect", { x, y, width: NW, height: Math.max(h, 2), rx: 2, fill })); };

    // segment files may be written in $M; normalise to raw dollars so the
    // whole diagram shares ONE dollar scale (bars are sub-pixel otherwise).
    const segMul = (segData && /million/i.test(segData.unit || "")) ? 1e6 : 1;
    const segs = (segData && segData.segments || [])
      .map(s => ({ ...s, v: s.v * segMul })).filter(s => s.v > 0);
    const hasSeg = segs.length > 1;

    // ---- values, clamped so a negative profit never breaks conservation ----
    const gross = Math.max(m.gross ?? 0, 0), cogs = Math.max(m.cogs ?? 0, 0);
    const opinc = Math.max(m.opinc ?? 0, 0);
    const opex  = m.opinc != null && m.opinc < 0 ? gross : Math.max(m.opex ?? 0, 0);
    const opLoss = m.opinc != null && m.opinc < 0 ? -m.opinc : 0;
    const other = Math.max(m.other ?? 0, 0);
    const pretax = opinc + other;
    const net = Math.max(m.net ?? 0, 0);
    const tax = Math.max(Math.min(m.tax ?? 0, pretax), 0);
    const netLoss = m.net != null && m.net < 0 ? -m.net : 0;

    // ---- one dollar scale for the whole diagram ----
    const span = Math.max(m.revenue, pretax, net + tax, gross + cogs);
    const SC = (H - PADT - PADB) / span;
    const X = hasSeg
      ? { seg: 180, rev: 360, gr: 520, op: 680, oth: 812, pre: 920, net: 1050 }
      : { seg: null, rev: 170, gr: 380, op: 590, oth: 770, pre: 900, net: 1050 };
    const TY = PADT;

    const revH = m.revenue * SC, grH = gross * SC, cgH = cogs * SC;
    const opH = opinc * SC, oxH = opex * SC, othH = other * SC;
    const preH = pretax * SC, ntH = net * SC, txH = tax * SC;

    // ---- ribbons first (behind bars) ----
    if (hasSeg) {
      const GAP = Math.min(10, (revH * 0.22) / Math.max(segs.length - 1, 1));
      const tot = segs.reduce((a, s) => a + s.v * SC, 0) + GAP * (segs.length - 1);
      let sy = TY + revH / 2 - tot / 2, land = TY;
      segs.forEach(s => { const h = s.v * SC;
        band(X.seg + NW, sy, X.rev, land, h, C.blueR);
        s._y = sy; s._h = h; sy += h + GAP; land += h; });
    }
    band(X.rev + NW, TY,       X.gr,  TY,       grH, C.greenR);
    band(X.rev + NW, TY + grH, X.gr,  TY + grH, cgH, C.redR);
    band(X.gr  + NW, TY,       X.op,  TY,       opH, C.greenR);
    band(X.gr  + NW, TY + opH, X.op,  TY + opH, oxH, C.redR);
    if (!opLoss) {
      band(X.op  + NW, TY,       X.pre, TY,       opH, C.greenR);
      band(X.oth + NW, TY + opH, X.pre, TY + opH, othH, C.violet);
      band(X.pre + NW, TY,       X.net, TY,       ntH, C.greenR);
      band(X.pre + NW, TY + ntH, X.net, TY + ntH, txH, C.redR);
    }

    // ---- bars ----
    if (hasSeg) segs.forEach(s => bar(X.seg, s._y, s._h, C.blue));
    bar(X.rev, TY, revH, C.blue);
    bar(X.gr, TY, grH, C.green);        bar(X.gr, TY + grH, cgH, C.red);
    bar(X.op, TY, opH, C.green);        bar(X.op, TY + opH, oxH, C.red);
    if (!opLoss) {
      if (othH > 0) bar(X.oth, TY + opH, othH, C.violet);
      bar(X.pre, TY, preH, C.green);
      bar(X.net, TY, ntH, C.green);     bar(X.net, TY + ntH, txH, C.red);
    }

    // ---- labels: profits above their node, costs below ----
    const above = (x, y, t1, t2, t3, col) => { const b = y - 10;
      if (t3) T(x, b, t3, { fs: 10.5, fill: C.muted });
      T(x, t3 ? b - 15 : b, t2, { fs: 14, fw: 700, fill: col });
      T(x, t3 ? b - 30 : b - 15, t1, { fs: 11, fw: 700, fill: col }); };
    const below = (x, y, t1, t2, subs, col) => {
      T(x, y + 15, t1, { fs: 11, fw: 700, fill: col });
      T(x, y + 31, t2, { fs: 14, fw: 700, fill: col });
      (subs || []).forEach((s, i) => T(x, y + 45 + i * 13, s, { fs: 10.5, fill: C.muted })); };

    above(X.rev, TY, "Revenue", money(m.revenue), m.revYoY, C.blue);
    above(X.gr,  TY, "Gross profit", money(gross), pct(gross, m.revenue) + " margin", C.green);
    below(X.gr, TY + grH + cgH, "Cost of revenue", "(" + money(cogs) + ")",
          [pct(cogs, m.revenue) + " of revenue"], C.red);

    if (opLoss > 0) {
      below(X.op, TY + opH + oxH, "Operating expenses", "(" + money(opex) + ")", null, C.red);
      T(X.op, TY - 25, "Operating loss", { fs: 11, fw: 700, fill: C.red });
      T(X.op, TY - 10, "(" + money(opLoss) + ")", { fs: 14, fw: 700, fill: C.red });
    } else {
      above(X.op, TY, "Operating profit", money(opinc),
            pct(opinc, m.revenue) + " margin · " + m.opYoY, C.green);
      const subs = [];
      if (m.rnd) subs.push("R&D " + money(m.rnd));
      if (m.sga) subs.push("SG&A " + money(m.sga));
      below(X.op, TY + opH + oxH, "Operating expenses", "(" + money(opex) + ")",
            subs.length ? [subs.join(" · ")] : null, C.red);
    }

    if (othH > 0 && !opLoss) { const cy = TY + opH + othH / 2;
      T(X.oth + NW + 9, cy - 13, "Other income", { fs: 11, fw: 700, fill: C.violet });
      T(X.oth + NW + 9, cy + 3, "+" + money(other), { fs: 14, fw: 700, fill: C.violet });
      T(X.oth + NW + 9, cy + 18, "non-operating", { fs: 10.5, fill: C.muted }); }

    if (!opLoss && preH > 0 && (othH > 0 || m.pretax != null))
      above(X.pre, TY, "Pre-tax income", money(pretax), null, C.ink);

    const nx = X.net + NW + 10;
    if (netLoss > 0 || opLoss > 0) {
      const lx = opLoss > 0 ? X.pre : nx, ly = opLoss > 0 ? TY - 25 : TY + 4;
      T(lx, ly, netLoss > 0 ? "Net loss" : "Net profit",
        { fs: 11, fw: 700, fill: netLoss > 0 ? C.red : C.green });
      T(lx, ly + 18, (netLoss > 0 ? "(" + money(netLoss) + ")" : money(net)),
        { fs: 16, fw: 800, fill: netLoss > 0 ? C.red : C.green });
      if (opLoss > 0) T(lx, ly + 34, "after tax & other items", { fs: 10.5, fill: C.muted });
    } else {
      const cy = TY + ntH / 2;
      T(nx, cy - 13, "Net profit", { fs: 11, fw: 700, fill: C.green });
      T(nx, cy + 4, money(net), { fs: 16, fw: 800, fill: C.green });
      T(nx, cy + 19, pct(net, m.revenue) + " of revenue", { fs: 10.5, fill: C.muted });
      T(nx, cy + 32, m.netYoY, { fs: 10.5, fill: C.muted });
    }
    if (txH > 0 && !opLoss) { const cy = TY + ntH + txH / 2;
      T(nx, cy - 6, "Income tax", { fs: 11, fw: 700, fill: C.red });
      T(nx, cy + 11, "(" + money(tax) + ")", { fs: 13, fw: 700, fill: C.red });
      T(nx, cy + 25, pct(tax, pretax) + " eff. rate", { fs: 10.5, fill: C.muted }); }

    if (hasSeg) {
      T(X.seg - 9, segs[0]._y - 18, (segData.label || "REVENUE BY SOURCE").toUpperCase(),
        { fs: 9.5, fw: 700, an: "end", fill: C.muted });
      let guard = -1e9;
      segs.forEach(s => { const cy = Math.max(s._y + s._h / 2, guard + 26); guard = cy;
        T(X.seg - 9, cy - 2, s.name, { fs: 11, fw: 600, an: "end" });
        T(X.seg - 9, cy + 12, money(s.v) + (s.yoy ? "   " + s.yoy : ""),
          { fs: 10.5, an: "end", fill: C.muted }); });
    }
    host.appendChild(svg);

    const notes = [];
    if (opinc > 0 && other > opinc)
      notes.push("Net profit is inflated by a large non-operating item in “Other income” — "
        + "operating profit (" + money(opinc) + ") is the measure of the business itself.");
    if (opLoss > 0) notes.push("Operating expenses exceeded gross profit this quarter, "
      + "so there is no operating-profit branch.");
    if (m.pretax == null) notes.push("Pre-tax and tax lines are not in this ticker's data yet, "
      + "so below-the-line items are shown as a single net adjustment.");
    if (!hasSeg) notes.push("Segment detail is not available for this ticker; "
      + "the diagram starts at total revenue.");
    const f = document.createElement("div");
    f.className = "flow-foot";
    f.textContent = "Quarter ended " + (m.q || "—")
      + ". Bar heights share one dollar scale, so every split is to scale."
      + (notes.length ? " " + notes.join(" ") : "");
    host.appendChild(f);
  }

  async function show(host, hist) {
    let seg = null;
    try { const r = await fetch("data/segments/" + hist.ticker + ".json");
      if (r.ok) seg = await r.json(); } catch (e) { /* optional */ }
    render(host, hist, seg);
  }
  window.SLFlow = { show, render };
})();
