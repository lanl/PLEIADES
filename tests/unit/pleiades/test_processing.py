from pleiades.processing import Roi


def test_roi():

    roi = Roi(x1=10, y1=20, x2=30, y2=40)
    assert roi.get_roi() == (10, 20, 30, 40)

    roi.set_roi(5, 15, 25, 35)
    assert roi.get_roi() == (5, 15, 25, 35)

    try:
        Roi(x1=-10, y1=20, x2=30, y2=40)
    except ValueError as e:
        assert str(e) == "ROI top left corner coordinates must be non-negative"

    try:
        Roi(x1=10, y1=20, x2=5, y2=40)
    except ValueError as e:
        assert str(e) == "ROI x2 must be greater than or equal to x1"

    try:
        Roi(x1=10, y1=20, x2=30, y2=15)
    except ValueError as e:
        assert str(e) == "ROI y2 must be greater than or equal to y1"

    try:
        Roi(x1=10, y1=20, x2=30, y2=40, width=-5)
    except ValueError as e:
        assert str(e) == "ROI cannot have both x2 and width defined"

    try:
        Roi(x1=10, y1=20, y2=40)
    except ValueError as e:
        assert str(e) == "ROI width must be positive when x2 is not defined"

    try:
        Roi(x1=10, y1=20, width=-5)
    except ValueError as e:
        assert str(e) == "ROI width must be positive when x2 is not defined"

    