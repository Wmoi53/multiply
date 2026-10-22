// Monte Carlo engine: recurring buys vs lump sum vs core + satellite.
// Assets: [core, stockA, stockB]. All figures are assumptions, not forecasts.
(function (root) {
  const DEFAULTS = {
    initial: 0,
    monthly: 1000,
    years: 10,
    sims: 2000,
    seed: 42,
    core: { mu: 0.08, sigma: 0.16 },
    stockA: { mu: 0.15, sigma: 0.55 }, // TSLA-like
    stockB: { mu: 0.15, sigma: 0.6 }, // SPCX-like
    corr: { coreA: 0.6, coreB: 0.5, AB: 0.5 },
    satellite: 0.4, // share of the portfolio held in the two stocks
    cap: 0.2, // max share of the portfolio in any one stock
    crashProb: 0, // yearly chance of a market-wide stock crash
    crashSize: 0.4,
  };

  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function normal(rand) {
    let u = 0;
    while (!u) u = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
  }

  function cholesky(m) {
    const n = m.length;
    const L = Array.from({ length: n }, () => new Array(n).fill(0));
    for (let i = 0; i < n; i++) {
      for (let j = 0; j <= i; j++) {
        let s = 0;
        for (let k = 0; k < j; k++) s += L[i][k] * L[j][k];
        L[i][j] = i === j ? Math.sqrt(m[i][i] - s) : (m[i][j] - s) / L[j][j];
      }
    }
    return L;
  }

  function percentile(sorted, p) {
    const i = (sorted.length - 1) * p;
    const lo = Math.floor(i);
    const hi = Math.ceil(i);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
  }

  // One path of monthly gross multipliers per asset: returns[t] = [core, A, B].
  function genReturns(p, rand, L) {
    const months = Math.round(p.years * 12);
    const assets = [p.core, p.stockA, p.stockB];
    const out = new Array(months);
    for (let t = 0; t < months; t++) {
      const z = [normal(rand), normal(rand), normal(rand)];
      const crash = rand() < p.crashProb / 12;
      out[t] = assets.map((a, i) => {
        const s = a.sigma / Math.sqrt(12);
        let corrZ = 0;
        for (let k = 0; k <= i; k++) corrZ += L[i][k] * z[k];
        const drift = Math.log(1 + a.mu) / 12 - (s * s) / 2;
        let m = Math.exp(drift + s * corrZ);
        if (crash && i > 0) m *= 1 - p.crashSize;
        return m;
      });
    }
    return out;
  }

  // cfg: { targets:[c,a,b], lump:boolean, rebalance:boolean, cap:number|null }
  function runStrategy(returns, p, cfg) {
    const months = returns.length;
    const h = [0, 0, 0];
    const invest = (amt) => cfg.targets.forEach((w, i) => (h[i] += amt * w));
    const total = () => h[0] + h[1] + h[2];
    const contributed = p.initial + p.monthly * months;
    const values = new Float64Array(months);
    let idx = 1;
    let peak = 1;
    let maxDD = 0;

    if (cfg.lump) invest(contributed);
    else invest(p.initial);

    for (let t = 0; t < months; t++) {
      if (!cfg.lump) invest(p.monthly);
      const before = total();
      for (let i = 0; i < 3; i++) h[i] *= returns[t][i];
      const after = total();
      if (before > 0) idx *= after / before;
      if (idx > peak) peak = idx;
      maxDD = Math.max(maxDD, 1 - idx / peak);
      if (cfg.rebalance && (t + 1) % 12 === 0) {
        const v = total();
        for (let i = 0; i < 3; i++) h[i] = v * cfg.targets[i];
      }
      if (cfg.cap != null) {
        const v = total();
        for (let i = 1; i < 3; i++) {
          if (h[i] > cfg.cap * v) {
            h[0] += h[i] - cfg.cap * v;
            h[i] = cfg.cap * v;
          }
        }
      }
      values[t] = total();
    }
    return { values, final: total(), maxDD, contributed };
  }

  function strategies(p) {
    const w = p.satellite;
    return {
      core: { label: 'DCA into core only', targets: [1, 0, 0], lump: false, rebalance: false, cap: null },
      dcaBasket: { label: 'DCA all-in on the two stocks', targets: [0, 0.5, 0.5], lump: false, rebalance: false, cap: null },
      lumpBasket: { label: 'Lump sum all-in on the two stocks', targets: [0, 0.5, 0.5], lump: true, rebalance: false, cap: null },
      coreSat: { label: 'Core + satellite (cap + rebalance)', targets: [1 - w, w / 2, w / 2], lump: false, rebalance: true, cap: p.cap },
    };
  }

  function simulate(overrides) {
    const p = Object.assign({}, DEFAULTS, overrides);
    const rand = rng(p.seed);
    const c = p.corr;
    const L = cholesky([
      [1, c.coreA, c.coreB],
      [c.coreA, 1, c.AB],
      [c.coreB, c.AB, 1],
    ]);
    const defs = strategies(p);
    const keys = Object.keys(defs);
    const months = Math.round(p.years * 12);
    const runs = {};
    keys.forEach((k) => (runs[k] = []));
    for (let s = 0; s < p.sims; s++) {
      const r = genReturns(p, rand, L); // shared across strategies = paired comparison
      keys.forEach((k) => runs[k].push(runStrategy(r, p, defs[k])));
    }
    const contributed = p.initial + p.monthly * months;
    const result = { params: p, contributed, months, strategies: {} };
    keys.forEach((k) => {
      const rs = runs[k];
      const finals = rs.map((x) => x.final).sort((a, b) => a - b);
      const dds = rs.map((x) => x.maxDD).sort((a, b) => a - b);
      const bands = { p10: [], p50: [], p90: [] };
      for (let t = 0; t < months; t++) {
        const col = rs.map((x) => x.values[t]).sort((a, b) => a - b);
        bands.p10.push(percentile(col, 0.1));
        bands.p50.push(percentile(col, 0.5));
        bands.p90.push(percentile(col, 0.9));
      }
      result.strategies[k] = {
        label: defs[k].label,
        p10: percentile(finals, 0.1),
        p50: percentile(finals, 0.5),
        p90: percentile(finals, 0.9),
        mean: finals.reduce((a, b) => a + b, 0) / finals.length,
        probLoss: finals.filter((f) => f < contributed).length / finals.length,
        medianMaxDD: percentile(dds, 0.5),
        probDD50: dds.filter((d) => d >= 0.5).length / dds.length,
        bands,
      };
    });
    return result;
  }

  const api = { DEFAULTS, simulate, runStrategy, genReturns, cholesky, rng, percentile };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Sim = api;
})(typeof self !== 'undefined' ? self : this);
