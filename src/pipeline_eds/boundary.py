# src/pipeline_eds/boundary.py
from __future__ import annotations
from dataclasses import KW_ONLY
import msgspec
from msgspec import Struct, field
import uuid

# ----------------------------
# Data Models using msgspec
# ----------------------------
class Point(Struct, kw_only = True):
    x: float
    y: float
    time: float = 0.0
    magnitude: float = 0.0
    z: float | None = None  # Third dimension is optional
    #metadata: dict = msgspec.NODEFAULT  # Required field (or default to factory if needed)
    metadata: dict = field(default_factory=dict)

class Series(Struct, kw_only=True):
    label: str
    points: list[Point]
    unit: str | None = None  # optional, default None

    def to_dict(self):
        # Convert to format expected by Plotly: { "x": [...], "y": [...] }
        return {
            "x": [p.x for p in self.points],
            "y": [p.y for p in self.points],
        }

    
    def to_plotly_dict(self) -> dict:
        """
        Serializes the Series into a Plotly-ready trace layout.
        Dynamically adjusts to 2D or 3D based on the presence of 'z' values.
        """
        if not self.points:
            return {
                "name": self.label,
                "x": [],
                "y": [],
                "type": "scatter",
                "meta": {"unit": self.unit}
            }

        is_3d = self.points[0].z is not None

        if is_3d:
            return {
                "name": self.label,
                "type": "scatter3d",
                "mode": "lines+markers",
                "x": [p.x for p in self.points],
                "y": [p.y for p in self.points],
                "z": [p.z for p in self.points],
                "meta": {"unit": self.unit},
            }

        return {
            "name": self.label,
            "type": "scatter",
            "mode": "lines+markers",
            "x": [p.x for p in self.points],
            "y": [p.y for p in self.points],
            "meta": {"unit": self.unit},
        }
class PlotData(Struct):
    __root__: dict[str, Series]
