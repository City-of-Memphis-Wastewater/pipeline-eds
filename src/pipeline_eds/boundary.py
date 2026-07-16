# src/pipeline_eds/boundary.py
from __future__ import annotations
import msgspec
from msgspec import Struct
import uuid

# ----------------------------
# Data Models using msgspec
# ----------------------------
class Point(Struct):
    time:
    magnitude:

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
    
# src/pipeline_eds/boundary.py
from __future__ import annotations
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

# ---

from __future__ import annotations
from dataclasses import dataclass, field
import time

@dataclass(slots=True)
class Observation:
    """
    The absolute atomic unit of telemetry. 
    It has no concept of spatial layout—only value, index, and timeline.
    Should this thing even have a label? No, let's say no. Ergo, there is no use case for a hypothetical ObservationDefiniton class which is consumed by an Obervationclass.
    Metadata is not expected at time of capture, only for annotation later.
    """
    value: float
    timestamp: float = field(default_factory=time.time)
    index: int | None = None
    annotations: dict[str, str | float] = field(default_factory=dict)
    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "index": self.index,
            "annotations": self.annotations,
        }

@dataclass(slots=True)
class SeriesDefinition:
    """
    A single, isolated stream definition for one specific metric which can be reused for atomic write,  of data over time .
    """
    uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    label: str = "new series"           # e.g., "elevation", "speed"
    display_label: str = label.capitalize(),
    unit: str | None
    #observations: list[Observation] = field(default_factory=list)
    metadata: dict[str, str | float] = field(default_factory=dict)
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "label": self.label,
            "unit": self.unit,
            #"observations": [obs.to_dict() for obs in self.observations],
            "metadata": self.metadata,
        }

@dataclass(slots=True)
class SeriesMemory(SeriesDefinition):
    """
    A series with an observation attribute held in memory
    """
    observations: list[Observation] = field(default_factory=list)
    
    #def import_from_file(self,atomic_json_file):
    #   """No, inferred by from_dict"""
    #    #self.observations
    #    pass
    def consume_observation(self,observation:Observation):
        self.observations.append(observation)

    def from_dict(self,obs_dict:dict):
        self.observations.join(obs_dict)
    #def write_to_file(self,atomic_json_file):
    #    """No, inferred by to_dict"""
    #    #self.observations
    #    pass

    def to_dict(self) -> dict:
        return Series.to_dict().join({
            "observations": [obs.to_dict() for obs in self.observations],
        })

@dataclass(slots=True)
class MultidimensionalEntityMoment:
    """
    Shared time stamp for multiple observations, each with a unique SerialDefinion
    """
    pass

@dataclass(slots=True)
class EntityTrack:
    """
    The narrative unit. Groups multiple parallel series that belong 
    to a single tracked object (e.g., a person, a drone, a process drop), with timestamps that may or may no correlate, if various sensors or samples have their own frequency of the target phenomena.
    If 
    """
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    display_name: str = "unnamed entity"                          # e.g., "individual_01", "Maxson_Influent"
    # Independent dimensions, sampled at their own native rates
    series: dict[uuid.UUID, Series] = field(default_factory=dict) # label -> Series
    metadata: dict[str, str | float] = field(default_factory=dict)

    def register_series_definition(self,series_definition:SeriesDefinition) -> None:
        self.series_definitions[series_definition.uuid] = series_definition
        
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "display_name": self.display_name,
            "series": {label: s.to_dict() for label, s in self.series.items()},
            "metadata": self.metadata,
        }
