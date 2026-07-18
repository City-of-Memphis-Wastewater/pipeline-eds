# src/pipeline_eds/buffer.py

from threading import Lock

class PlotBuffer_:
    def __init__(self):
        self._series: dict[str, Series] = {}
        self._lock = Lock()

    def update(self, series: Series):
        with self._lock:
            self._series[series.label] = series

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {
                label: s.to_plotly_dict()
                for label, s in self._series.items()
            }

    def clear(self):
        with self._lock:
            self._series.clear()


# src/pipeline_eds/buffer.py
from __future__ import annotations
import logging
from threading import Lock
from collections import defaultdict
from pipeline_eds.boundary import Point, Series

logger = logging.getLogger(__name__)

class PlotBuffer:
    """
    A unified, thread-safe memory buffer for live EDS plots.
    Manages a collection of msgspec Series objects, ensuring that
    updates from data pipelines do not clash with ASGI server reads.
    """
    def __init__(self, max_points: int = 100, keep_all_live_points: bool = True):
        self.max_points = max_points
        self.keep_all_live_points = keep_all_live_points
        
        # Internal storage: maps label -> list of Point structs
        self._points: dict[str, list[Point]] = defaultdict(list)
        # Optional storage for units per label
        self._units: dict[str, str | None] = {}
        
        self._lock = Lock()

    def append(self, label: str, x: float, y: float, unit: str | None = None) -> None:
        """Appends a single data point to a specific series in a thread-safe manner."""
        with self._lock:
            self._points[label].append(Point(x=x, y=y))
            if unit is not None:
                self._units[label] = unit

            # Enforce max_points ceiling if we aren't configured to keep everything
            if not self.keep_all_live_points and len(self._points[label]) > self.max_points:
                self._points[label].pop(0)

    def update_series(self, series: Series) -> None:
        """Overwrites or inserts an entire Series object directly."""
        with self._lock:
            self._points[series.label] = list(series.points)
            self._units[series.label] = series.unit

    def get_series_list(self) -> list[Series]:
        """
        Returns a snapshot copy of the buffer as a list of msgspec Series.
        Safe for iterating over or serializing without holding the lock.
        """
        with self._lock:
            return [
                Series(label=label, points=list(pts), unit=self._units.get(label))
                for label, pts in self._points.items()
            ]

    def snapshot(self) -> dict[str, dict]:
        """
        Formats data directly into a Plotly-ready dict structure.
        """
        with self._lock:
            return {
                label: {
                    "x": [p.x for p in pts],
                    "y": [p.y for p in pts],
                    "unit": self._units.get(label)
                }
                for label, pts in self._points.items()
            }

    def clear(self) -> None:
        """Resets the buffer."""
        with self._lock:
            self._points.clear()
            self._units.clear()

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._points) == 0
        
# src/pipeline_eds/buffer.py
from __future__ import annotations
import logging
from threading import Lock
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class PlotBuffer:
    """
    A unified, thread-safe memory buffer for live EDS plots.
    Manages historical sliding windows of Points using optimized deques,
    delegating dimensionality to the Point and Series boundary models.
    """
    def __init__(self, max_points: int = 100, keep_all_live_points: bool = True):
        self.max_points = max_points
        self.keep_all_live_points = keep_all_live_points
        
        self._maxlen = None if keep_all_live_points else max_points
        
        # Internal storage: maps label -> deque of Point structs
        self._points: dict[str, deque[Point]] = defaultdict(
            lambda: deque(maxlen=self._maxlen)
        )
        self._units: dict[str, str | None] = {}
        self._lock = Lock()

    def append(self, label: str, point: Point, unit: str | None = None) -> None:
        """Appends a Point struct to a specific series in a thread-safe manner."""
        with self._lock:
            self._points[label].append(point)
            if unit is not None:
                self._units[label] = unit

    def update_series(self, series: Series) -> None:
        """Overwrites or inserts an entire Series object directly."""
        with self._lock:
            self._points[series.label] = deque(series.points, maxlen=self._maxlen)
            self._units[series.label] = series.unit

    def get_series_list(self) -> list[Series]:
        """Returns a snapshot copy of the buffer as a list of msgspec Series."""
        with self._lock:
            return [
                Series(label=label, points=list(pts), unit=self._units.get(label))
                for label, pts in self._points.items()
            ]

    def snapshot(self) -> dict[str, dict]:
        """
        Returns a dictionary mapping series labels to their native Plotly representations,
        delegating format structure entirely to the Series boundary model.
        """
        with self._lock:
            return {
                label: Series(
                    label=label, 
                    points=list(pts), 
                    unit=self._units.get(label)
                ).to_plotly_dict()
                for label, pts in self._points.items()
            }

    def clear(self) -> None:
        """Resets the buffer."""
        with self._lock:
            self._points.clear()
            self._units.clear()

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._points) == 0
        
    def get_all(self) -> dict[str, list[Point]]:
        """
        Returns a point-in-time snapshot of the raw points dictionary.
        Safe for downstream utilities (like show_static) to process without
        causing threading race conditions on the active buffer.
        """
        with self._lock:
            # We copy the dictionary and convert deques to lists so 
            # downstream readers get a stable, standard list of Points.
            return {label: list(pts) for label, pts in self._points.items()}
