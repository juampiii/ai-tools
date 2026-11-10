from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Card:
    id: int
    title: str
    type: str


class TrackerClient(Protocol):
    def get_card(self, card_id: int) -> Card: ...
