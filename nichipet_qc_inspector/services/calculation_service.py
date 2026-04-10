import math
import numpy as np

def mass_to_volume(mass_mg: float, z_factor: float = 1.0040) -> float:
    return float(mass_mg) * float(z_factor)

def mean_volume(volumes):
    return float(np.mean(np.array(volumes, dtype=float)))

def systematic_error_percent(v_mean: float, selected_volume: float) -> float:
    return ((float(v_mean) - float(selected_volume)) / float(selected_volume)) * 100.0

def cv_percent(volumes):
    arr = np.array(volumes, dtype=float)
    if len(arr) < 2:
        return None
    mean_val = np.mean(arr)
    if mean_val == 0:
        return None
    return float(np.std(arr, ddof=1) / mean_val * 100.0)

def threshold_equal(value: float, limit: float, tol: float = 1e-12) -> bool:
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=tol)