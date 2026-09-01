from multiply.models import Club, Player
from multiply.valuation import estimate_club_value, estimate_player_value


def make_player(**overrides):
    defaults = dict(id="p", name="P", age=26, position="ST", performance_score=70,
                     contract_years_remaining=3, league_tier=1)
    defaults.update(overrides)
    return Player(**defaults)


def test_peak_age_beats_very_young_and_very_old():
    peak = estimate_player_value(make_player(age=26))
    young = estimate_player_value(make_player(age=16))
    old = estimate_player_value(make_player(age=37))
    assert peak > young
    assert peak > old


def test_higher_performance_increases_value():
    low = estimate_player_value(make_player(performance_score=20))
    high = estimate_player_value(make_player(performance_score=95))
    assert high > low


def test_expiring_contract_lowers_value():
    long_deal = estimate_player_value(make_player(contract_years_remaining=4))
    expiring = estimate_player_value(make_player(contract_years_remaining=0))
    assert expiring < long_deal
    assert expiring == 0.30 * long_deal


def test_lower_league_tier_lowers_value():
    top = estimate_player_value(make_player(league_tier=1))
    lower = estimate_player_value(make_player(league_tier=5))
    assert lower < top


def test_club_value_combines_revenue_squad_and_debt():
    debt_free = Club(id="c1", name="C1", revenue_eur=100_000_000, net_debt_eur=0, league_tier=1,
                      squad=[make_player()])
    indebted = Club(id="c2", name="C2", revenue_eur=100_000_000, net_debt_eur=50_000_000,
                     league_tier=1, squad=[make_player()])
    assert estimate_club_value(debt_free) - estimate_club_value(indebted) == 50_000_000

    no_squad = Club(id="c3", name="C3", revenue_eur=100_000_000, net_debt_eur=0, league_tier=1)
    assert estimate_club_value(debt_free) > estimate_club_value(no_squad)
