# src/forms/layout.py

from dataclasses import dataclass

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class TableLayout:

    columns: dict[str, tuple[float, float]]
    top: float
    bottom: float
    n_rows: int
    inset: float = 0.003

    def cell(self, row: int, column: str) -> Box:
        x0, x1 = self.columns[column]
        row_height = (self.bottom - self.top) / self.n_rows
        y0 = self.top + row * row_height
        return (
            x0 + self.inset,
            y0 + self.inset,
            x1 - self.inset,
            y0 + row_height - self.inset,
        )
