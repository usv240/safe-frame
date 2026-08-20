import numpy as np

from safe_frame.metrics import changed_area_direct, changed_area_from_tiles


def test_eight_by_eight_average_can_destroy_spatial_change():
    # Each 8x8 diagnostic tile contains equal black/white samples in both frames,
    # but every pixel reverses. Tile averages report no change; direct area is 100%.
    checker = (np.indices((64, 64)).sum(axis=0) % 2).astype(float)
    previous = np.repeat(checker[..., None], 3, axis=2)
    current = 1 - previous
    assert changed_area_direct(previous, current) == 1.0
    assert changed_area_from_tiles(previous, current) == 0.0


def test_direct_area_passes_small_region():
    previous = np.zeros((64, 64, 3))
    current = previous.copy()
    current[:16, :16] = 1
    assert changed_area_direct(previous, current) == 0.0625
