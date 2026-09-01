"""Ties bids to valuations and auto-notifies investors and fans.

The trigger rule is deliberately simple and explainable: notify when a bid
sets a new high for its target, moves materially away from the current model
valuation, or is flagged verified (e.g. confirmed by the club/press rather
than rumoured). Investors get the financial detail (amount, valuation,
delta, implied multiple); fans get a short plain-language headline.
"""

from __future__ import annotations

import uuid

from . import valuation
from .models import Bid, Subscriber
from .notifier import NotificationDispatcher
from .store import Store

NOTIFY_MOVE_THRESHOLD = 0.05  # 5% away from current model valuation


class UnknownTargetError(LookupError):
    pass


class ValuationService:
    def __init__(self, store: Store, dispatcher: NotificationDispatcher | None = None) -> None:
        self.store = store
        self.dispatcher = dispatcher or NotificationDispatcher()

    # -- valuations ---------------------------------------------------------
    def current_valuation(self, target_type: str, target_id: str) -> float:
        if target_type == "player":
            player = self.store.get_player(target_id)
            if player is None:
                raise UnknownTargetError(f"unknown player {target_id!r}")
            return valuation.estimate_player_value(player)
        if target_type == "club":
            club = self.store.get_club(target_id)
            if club is None:
                raise UnknownTargetError(f"unknown club {target_id!r}")
            return valuation.estimate_club_value(club)
        raise ValueError("target_type must be 'player' or 'club'")

    def _target_name(self, target_type: str, target_id: str) -> str:
        if target_type == "player":
            player = self.store.get_player(target_id)
            return player.name if player else target_id
        club = self.store.get_club(target_id)
        return club.name if club else target_id

    # -- bids ---------------------------------------------------------
    def submit_bid(
        self,
        target_type: str,
        target_id: str,
        bidder: str,
        amount_eur: float,
        verified: bool = False,
    ) -> tuple[Bid, bool]:
        """Record a bid and auto-notify subscribers if it is notify-worthy.

        Returns (bid, notified) so callers/tests can assert on both.
        """
        previous_high = self.store.get_highest_bid(target_type, target_id)
        bid = Bid(
            id=str(uuid.uuid4()), target_type=target_type, target_id=target_id,
            bidder=bidder, amount_eur=amount_eur, verified=verified,
        )
        self.store.save_bid(bid)

        current_value = self.current_valuation(target_type, target_id)
        is_new_high = previous_high is None or amount_eur > previous_high.amount_eur
        move_pct = (amount_eur - current_value) / current_value if current_value else 0.0
        notify_worthy = is_new_high or abs(move_pct) >= NOTIFY_MOVE_THRESHOLD or verified

        notified = False
        if notify_worthy:
            self._notify(bid, current_value, move_pct, is_new_high)
            notified = True
        return bid, notified

    def _notify(self, bid: Bid, current_value: float, move_pct: float, is_new_high: bool) -> None:
        name = self._target_name(bid.target_type, bid.target_id)
        subject = f"New {'verified ' if bid.verified else ''}bid for {name}"

        investor_body = (
            f"Bidder: {bid.bidder}\n"
            f"Amount: EUR {bid.amount_eur:,.0f}\n"
            f"Model valuation: EUR {current_value:,.0f}\n"
            f"Delta vs. model: {move_pct:+.1%}\n"
            f"New high bid: {'yes' if is_new_high else 'no'}\n"
            f"Verified: {'yes' if bid.verified else 'no'}"
        )
        fan_body = (
            f"{bid.bidder} have {'confirmed' if bid.verified else 'reportedly'} bid "
            f"EUR {bid.amount_eur:,.0f} for {name}"
            f"{' -- a new record bid' if is_new_high else ''}!"
        )

        subscribers = self._subscribers_watching(bid.target_id)
        self.dispatcher.dispatch(
            subscribers, subject, {"investor": investor_body, "fan": fan_body}
        )

    def _subscribers_watching(self, target_id: str) -> list[Subscriber]:
        return [s for s in self.store.list_subscribers() if s.is_watching(target_id)]
