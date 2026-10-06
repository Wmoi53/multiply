"""Worked example: python -m equity_decision.example"""

from . import (EquityConfig, MarketContext, brier_score, decide,
               expected_calibration_error)


def main() -> None:
    cfg = EquityConfig()
    print("BUY :", decide(cfg, 0.62, 0.54,
                          MarketContext(momentum=0.03, realized_vol=0.22)))
    print("HOLD:", decide(cfg, 0.55, 0.54))
    print("SELL:", decide(cfg, 0.40, 0.52))
    preds = [0.6, 0.55, 0.7, 0.3, 0.8]
    outs = [1, 0, 1, 0, 1]
    print(f"Brier: {brier_score(preds, outs):.4f}")
    print(f"ECE  : {expected_calibration_error(preds, outs):.4f}")


if __name__ == "__main__":
    main()
