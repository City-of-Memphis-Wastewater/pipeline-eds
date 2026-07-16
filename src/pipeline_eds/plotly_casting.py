# src/pipeline_eds/plotly_casting.py

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(slots=True)
class TraceStyle:
    """
    Decoupled presentation rules for a trace.
    Keeps layout & design concerns separated from raw telemetry arrays.
    """
    marker_diameter: float | list[float] | None = None
    marker_color: str | list[float] | None = None
    line_width: float | None = None
    hoverinfo: str | None = None
    text: str | list[str] | None = None
    opacity: float | None = None

    def apply_to_trace_dict(self, trace_dict: dict) -> None:
        """Injects these style properties into an existing raw Plotly dictionary."""
        marker_cfg = {}
        if self.marker_diameter is not None:
            marker_cfg["size"] = self.marker_diameter
        if self.marker_color is not None:
            marker_cfg["color"] = self.marker_color
        if marker_cfg:
            trace_dict["marker"] = marker_cfg

        if self.line_width is not None:
            trace_dict["line"] = {"width": self.line_width}
            
        if self.hoverinfo:
            trace_dict["hoverinfo"] = self.hoverinfo
        if self.text:
            trace_dict["text"] = self.text
        if self.opacity:
            trace_dict["opacity"] = self.opacity


@dataclass(slots=True)
class PlotTrace:
    """
    Represents only the spatial layout, identity, and raw data coordinates.
    Zero visual formatting concerns.
    """
    name: str
    x: list[float]
    y: list[float]
    z: list[float] | None = None
    trace_type: str = "scatter"
    mode: str = "lines+markers"
    metadata: dict[str, str | float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        trace = {
            "name": self.name,
            "type": self.trace_type,
            "mode": self.mode,
            "x": self.x,
            "y": self.y,
        }
        if self.z is not None:
            trace["z"] = self.z
        if self.metadata:
            trace["meta"] = self.metadata
        return trace
    

@dataclass(slots=True)
class PlotTraces:
    """
    A pure, passive container for a single chart's data.
    """
    title: str = "Telemetry Visualization"
    # Pure data + visual mapping storage
    entries: list[tuple[PlotTrace, TraceStyle | None]] = field(default_factory=list)

    def add_trace(self, trace: PlotTrace, style: TraceStyle | None = None) -> None:
        """Appends a data trace and its optional presentation style."""
        self.entries.append((trace, style))

    def serialize_data(self) -> list[dict]:
        """
        Only serializes the data entries themselves into raw dictionaries.
        No layout wrapper, no axis building, no guessing.
        """
        serialized = []
        for trace, style in self.entries:
            trace_dict = trace.to_dict()
            if style:
                style.apply_to_trace_dict(trace_dict)
            serialized.append(trace_dict)
        return serialized