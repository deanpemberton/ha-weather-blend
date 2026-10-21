"""Pure, local weather aggregation. No network or telemetry."""
import math
from statistics import median

def robust_blend(readings, circular=False):
    """Readings: (value, weight). Reject large isolated deviations when >=3."""
    pairs = [(float(v), float(w)) for v, w in readings if v is not None and w > 0 and math.isfinite(float(v))]
    if not pairs:
        return None, 0
    if circular:
        x = sum(w * math.cos(math.radians(v)) for v, w in pairs)
        y = sum(w * math.sin(math.radians(v)) for v, w in pairs)
        coherence = math.hypot(x, y) / sum(w for _, w in pairs)
        return ((math.degrees(math.atan2(y, x)) + 360) % 360 if coherence >= .15 else None), len(pairs)
    if len(pairs) >= 3:
        mid = median(v for v, _ in pairs)
        deviations = [abs(v - mid) for v, _ in pairs]
        mad = median(deviations)
        threshold = max(3 * 1.4826 * mad, .05 * max(abs(mid), 1))
        retained = [(v, w) for v, w in pairs if abs(v - mid) <= threshold]
        if len(retained) >= 2:
            pairs = retained
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs), len(pairs)
