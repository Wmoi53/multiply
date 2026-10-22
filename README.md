# multiply
agent multi tasking for a single project in 60days

## DCA simulator

Open `index.html` in a browser. It compares, on the same simulated price paths:

1. DCA into a diversified core only
2. DCA all-in on two high-volatility stocks (defaults resemble TSLA and SpaceX)
3. Lump sum all-in on the two stocks
4. Core + satellite with a per-stock cap and yearly rebalance

It reports the 10th, median and 90th percentile outcomes, chance of ending below what you put in, typical worst drop and chance of a 50%+ drop.

Prices are simulated from the assumptions you enter. They are not live data and not forecasts. Educational only, not investment advice.

```
node test.js   # engine tests
```
