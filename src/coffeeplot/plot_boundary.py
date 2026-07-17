# src/pipeline_eds/plot_boundary.py
from __future__ import annotations
from dataclasses import dataclass, field
import time
import uuid

@dataclass(slots=True)
class Observation:
    """
    The absolute atomic unit of telemetry. 
    It has no concept of spatial layout—only value, index, and timeline.
    Should this thing even have a label? No, let's say no. Ergo, there is no use case for a hypothetical ObservationDefiniton class which is consumed by an Obervationclass.
    Metadata is not expected at time of capture, only for annotation later.
    """
    value: float
    timestamp_creation: float = field(default_factory=lambda: time.time()) # defaults to right now as the time stamp
    timestamp: float | None = None
    index: int | None = None
    annotations: dict[str, str | float] = field(default_factory=dict)
    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "timestamp_creation": self.timestamp_creation,
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
    display_label: str = "New Series"
    unit: str | None = None
    metadata: dict[str, str | float] = field(default_factory=dict)
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "label": self.label,
            "display_label": self.display_label,
            "unit": self.unit,
            "metadata": self.metadata,
        }

@dataclass(slots=True)
class SeriesMemory(SeriesDefinition):
    """
    A series with an observation attribute held in memory

    from_dict() is not necesary because the best dict is not a dict but is instead a SeriesMemory instance.
    """
    observations: list[Observation] = field(default_factory=list)
    
    def consume_observation(self,observation:Observation):
        """The rich man's append."""
        self.observations.append(observation)

    def to_dict(self) -> dict:
        # Pull parent definitions and merge in the historical observations
        base = super().to_dict()
        base["observations"] = [obs.to_dict() for obs in self.observations]
        return base

@dataclass(slots=True)
class EntityTrack:
    """
    The narrative unit. Groups multiple parallel series that belong 
    to a single tracked object (e.g., a person, a drone, a process drop), with timestamps that may or may no correlate, if various sensors or samples have their own frequency of the target phenomena.
    If 
    """
    uuid: uuid.UUID = field(default_factory=uuid.uuid4)
    display_name: str = "unnamed entity"                          # e.g., "individual_01", "Maxson_Influent"
    # Independent dimensions, sampled at their own native rates
    series_definitions: dict[uuid.UUID, SeriesDefinition] = field(default_factory=dict) # label -> Series
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
    

@dataclass(slots=True)
class MultidimensionalEntityMoment:
    """
    A shared single timestamp with multiple Observation instances, each with a related SeriesDefinition
    """
    pass