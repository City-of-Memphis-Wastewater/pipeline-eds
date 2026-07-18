# src/pipeline_eds/boundary.py
from __future__ import annotations
import msgspec
from msgspec import Struct
import uuid

# ----------------------------
# Data Models using msgspec
# ----------------------------
class Point(Struct):
    time: float
    magnitude: float
    x: float
    y: float
    z: float | None = None  # Third dimension is optional
    metadata: dict

class Series(Struct):
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

        return {
            "name": self.label,
            "type": "scatter",
            "mode": "lines+markers",
            "x": [p.x for p in self.points],
            "y": [p.y for p in self.points],
            "meta": {"unit": self.unit}
        }
    
from dataclasses import dataclass

@dataclass(slots=True)
class Point:
    x: float
    y: float
    z: float | None = None


@dataclass(slots=True)
class Series:
    label: str
    points: list[Point]
    unit: str | None = None

    def to_plotly_dict(self) -> dict:
        """
        Serializes the Series into a Plotly-ready trace layout.
        Decoupled from transport libraries; works natively with standard dicts.
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
                "meta": {"unit": self.unit}
            }
        
        return {
            "name": self.label,
            "type": "scatter",
            "mode": "lines+markers",
            "x": [p.x for p in self.points],
            "y": [p.y for p in self.points],
            "meta": {"unit": self.unit}
        }
class PlotData(Struct):
    __root__: dict[str, Series]
