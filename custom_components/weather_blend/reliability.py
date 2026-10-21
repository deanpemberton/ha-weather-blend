"""Metric-specific station reliability, local-only and in-memory.

Reliability is learned from agreement with independent peers over time.
No data is persisted or transmitted. Spatially patchy metrics are excluded
from consensus-based penalties to avoid punishing genuine microclimates.
"""
from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from .blend import Observation, TOLERANCE

CONSENSUS_METRICS = frozenset({"temperature", "humidity", "pressure", "dewpoint"})
MIN_RELIABILITY = 0.25
RECOVERY = 0.015
PENALTY = 0.08

@dataclass(frozen=True)
class StationHealth:
    reliability: float
    accepted: int
    rejected: int

class ReliabilityTracker:
    def __init__(self):
        self._scores = defaultdict(lambda: 1.0)
        self._accepted = defaultdict(int)
        self._rejected = defaultdict(int)

    def reliability(self, metric: str, station: str) -> float:
        return self._scores[(metric, station)]

    def update(self, metric: str, observations: list[Observation]):
        """Update at most once per new upstream sample, not on HA refresh ticks."""
        if metric not in CONSENSUS_METRICS or len(observations) < 3:
            return
        for observation in observations:
            peers = [o.value for o in observations if o.source != observation.source]
            if len(peers) < 2:
                continue
            if max(peers) - min(peers) > TOLERANCE[metric]:
                continue
            disagreement = abs(observation.value - median(peers))
            key = (metric, observation.source)
            if disagreement > TOLERANCE[metric] * 2:
                self._scores[key] = max(MIN_RELIABILITY, self._scores[key] - PENALTY)
                self._rejected[key] += 1
            else:
                self._scores[key] = min(1.0, self._scores[key] + RECOVERY)
                self._accepted[key] += 1

    def health(self, metric: str, station: str) -> StationHealth:
        key = (metric, station)
        return StationHealth(self._scores[key], self._accepted[key], self._rejected[key])
