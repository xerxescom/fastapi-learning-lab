import pytest

from app.services import CapacityExceeded, ensure_capacity

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("current,maximum", [(0, 1), (2, 3), (99, 100)])
def test_capacity_available(current, maximum):
    ensure_capacity(current, maximum)


@pytest.mark.parametrize("current,maximum", [(0, 0), (3, 3), (4, 3)])
def test_capacity_reached(current, maximum):
    with pytest.raises(CapacityExceeded):
        ensure_capacity(current, maximum)
