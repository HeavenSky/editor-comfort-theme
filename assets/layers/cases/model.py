from dataclasses import dataclass, field
import re

PATTERN = re.compile(r"^[a-z_]+\d*$")

@dataclass
class Order:
    id: int
    items: list[str] = field(default_factory=list)
    paid: bool = False

    def total(self, rate: float = 1.0) -> float:
        if not self.items:
            raise ValueError(f"order {self.id} empty")
        return sum(len(i) * rate for i in self.items if PATTERN.match(i))
