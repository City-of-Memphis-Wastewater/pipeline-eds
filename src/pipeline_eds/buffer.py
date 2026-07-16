# src/pipeline_eds/buffer.py

from threading import Lock
from pipeline_eds.boundary import Series

class PlotBuffer:
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
