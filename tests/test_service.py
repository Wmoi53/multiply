import pytest

from multiply.models import Club, Player, Subscriber
from multiply.notifier import ConsoleChannel, NotificationDispatcher
from multiply.service import ValuationService
from multiply.store import Store


@pytest.fixture
def service():
    store = Store(":memory:")
    console = ConsoleChannel()
    dispatcher = NotificationDispatcher({"console": console})
    svc = ValuationService(store, dispatcher)

    store.save_club(Club(id="ofc", name="Oakview FC", revenue_eur=90_000_000,
                          net_debt_eur=20_000_000, league_tier=2))
    store.save_player(Player(id="p1", name="A. Rossi", age=24, position="ST",
                              performance_score=78, contract_years_remaining=2.5, league_tier=2),
                       club_id="ofc")

    store.save_subscriber(Subscriber(id="inv1", name="Riverbend Capital", audience="investor",
                                      channel="console", contact="riverbend", watched_ids={"ofc", "p1"}))
    store.save_subscriber(Subscriber(id="fan1", name="Sam", audience="fan",
                                      channel="console", contact="sam", watched_ids=None))
    store.save_subscriber(Subscriber(id="inv2", name="Uninterested Capital", audience="investor",
                                      channel="console", contact="other", watched_ids={"some-other-club"}))

    svc._console = console  # stash for assertions
    yield svc
    store.close()


def test_new_high_bid_triggers_notification(service):
    bid, notified = service.submit_bid("club", "ofc", "Northstar Partners", 300_000_000, verified=True)
    assert notified is True
    sent = service._console.sent
    assert len(sent) == 2  # inv1 (watching) + fan1 (watch-all); inv2 not watching
    recipients = {s.id for s, _, _ in sent}
    assert recipients == {"inv1", "fan1"}


def test_small_non_record_bid_is_not_notify_worthy(service):
    current_value = service.current_valuation("player", "p1")
    # Establish a high unverified bid first, then clear its (expected) notification.
    service.submit_bid("player", "p1", "Scout A", current_value * 1.10, verified=False)
    service._console.sent.clear()

    # A second, lower bid that is neither a new high nor >=5% away from the
    # model valuation, and is unverified, should not be notify-worthy.
    _, notified = service.submit_bid("player", "p1", "Scout B", current_value * 1.02, verified=False)
    assert notified is False
    assert service._console.sent == []


def test_verified_bid_always_notifies_even_if_not_a_new_high(service):
    service.submit_bid("player", "p1", "Scout A", 50_000_000, verified=False)
    service._console.sent.clear()

    _, notified = service.submit_bid("player", "p1", "Scout A", 40_000_000, verified=True)
    assert notified is True
    assert len(service._console.sent) == 2  # inv1 watches p1 directly; fan1 watches everything
