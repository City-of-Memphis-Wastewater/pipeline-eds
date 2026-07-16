# src/pipeline_eds/boundary.py
from __future__ import annotations
import msgspec
from msgspec import Struct

# ----------------------------
# Data Models using msgspec
# ----------------------------
class Point(Struct):
    x: float
    y: float

class Series(Struct):
    label: str
    points: list[Point]

    def to_plotly_dict(self):
        # Convert to format expected by Plotly: { "x": [...], "y": [...] }
        return {
            "x": [p.x for p in self.points],
            "y": [p.y for p in self.points],
        }


# plot_buffer should not be global
