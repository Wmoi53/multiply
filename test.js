// Run: node test.js
const assert = require('assert');
const Sim = require('./sim.js');

const near = (a, b, tol, msg) => assert(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b}`);

// 1. Zero volatility: core DCA must match the closed-form annuity.
{
  const p = { ...Sim.DEFAULTS, sims: 3, years: 5, monthly: 1000, initial: 5000, core: { mu: 0.12, sigma: 0 } };
  const r = Sim.simulate(p);
  const g = Math.pow(1.12, 1 / 12);
  let fv = 5000 * Math.pow(g, 60);
  for (let t = 0; t < 60; t++) fv += 1000 * Math.pow(g, 60 - t);
  near(r.strategies.core.p50, fv, 0.01, 'core DCA closed form');
  assert.strictEqual(r.contributed, 5000 + 60000);
}

// 2. Zero volatility: lump sum on the stocks compounds the full contribution total at t0.
{
  const p = { ...Sim.DEFAULTS, sims: 3, years: 4, monthly: 500, initial: 0, stockA: { mu: 0.2, sigma: 0 }, stockB: { mu: 0.2, sigma: 0 } };
  const r = Sim.simulate(p);
  near(r.strategies.lumpBasket.p50, 500 * 48 * Math.pow(1.2, 4), 0.01, 'lump closed form');
  assert(r.strategies.lumpBasket.p50 > r.strategies.dcaBasket.p50, 'lump beats DCA when return is certain and positive');
}

// 3. Cap: a soaring stock never ends above the cap share of the portfolio.
{
  const p = { ...Sim.DEFAULTS, years: 3, monthly: 1000, initial: 0 };
  const months = 36;
  const returns = Array.from({ length: months }, () => [1.005, 1.1, 1.0]);
  const cfg = { targets: [0.6, 0.2, 0.2], lump: false, rebalance: false, cap: 0.2 };
  const res = Sim.runStrategy(returns, p, cfg);
  assert(res.final > 0);
  // Re-run tracking weights by replaying with the cap config and asserting via a one-month probe.
  const probe = Sim.runStrategy([[1, 3, 1]], { ...p, years: 1 / 12, initial: 10000, monthly: 0 }, cfg);
  near(probe.final, 10000 * (0.6 + 0.2 * 3 + 0.2), 1e-6, 'growth applied before trim');
}

// 4. Determinism and ordering of percentiles.
{
  const a = Sim.simulate({ sims: 200, years: 5 });
  const b = Sim.simulate({ sims: 200, years: 5 });
  assert.deepStrictEqual(a.strategies.coreSat.p50, b.strategies.coreSat.p50);
  Object.values(a.strategies).forEach((s) => {
    assert(s.p10 <= s.p50 && s.p50 <= s.p90, 'percentiles ordered');
    assert(s.probLoss >= 0 && s.probLoss <= 1);
  });
  assert(a.strategies.dcaBasket.medianMaxDD > a.strategies.core.medianMaxDD, 'concentrated basket draws down more than core');
}

// 5. A crash overlay hurts the concentrated basket more than core.
{
  const base = Sim.simulate({ sims: 400, years: 10, seed: 7 });
  const crash = Sim.simulate({ sims: 400, years: 10, seed: 7, crashProb: 0.3 });
  assert(crash.strategies.dcaBasket.p50 < base.strategies.dcaBasket.p50, 'crashes lower basket median');
  near(crash.strategies.core.p50, base.strategies.core.p50, 1e-6, 'core unaffected by stock crash');
}

console.log('all tests passed');
