import pytest
from project import (
    design_loads,
    resolve_force,
    select_shackle,
    pin_plate_check,
    strong_axis_allowable,
    plate_check,
    weld_check,
    weld_leg_needed,
    dnv_checks,
)

LUG_A = {
    "t": 25.0,
    "r": 60.0,
    "dh": 42.0,
    "y": 90.0,
    "l": 250.0,
    "tc": 10.0,
    "w": 10.0,
    "tb": 12.0,
    "fy": 275.0,
    "fu": 430.0,
    "exx": 480.0,
}

LUG_B = {
    "t": 16.0,
    "r": 45.0,
    "dh": 42.0,
    "y": 90.0,
    "l": 150.0,
    "tc": 14.0,
    "w": 5.0,
    "tb": 12.0,
    "fy": 275.0,
    "fu": 430.0,
    "exx": 480.0,
}


def test_design_loads():
    f_lug, f_shackle = design_loads(60000.0, 1.1, 1.0, 1.3)
    assert f_lug == pytest.approx(85800.0)
    assert f_shackle == pytest.approx(60000.0)


def test_resolve_force():
    pull, along, out, angle = resolve_force(85800.0, 0.0, 4000.0, 1000.0, "+Y", "X")
    assert pull == pytest.approx(83238.0, abs=1.0)
    assert along == pytest.approx(20810.0, abs=1.0)
    assert out == pytest.approx(2574.0, abs=1.0)
    assert angle == pytest.approx(75.96, abs=0.01)

    pull2, along2, out2, angle2 = resolve_force(86082.0, -2250.0, 7000.0, 0.0, "-Z", "X")
    assert pull2 == pytest.approx(0.0, abs=1.0)
    assert along2 == pytest.approx(81952.0, abs=1.0)
    assert out2 == pytest.approx(28924.0, abs=1.0)
    assert angle2 == pytest.approx(72.18, abs=0.01)


def test_select_shackle():
    shackle_1 = select_shackle(60000.0, 42.0, 45.0)
    assert shackle_1 is not None
    assert shackle_1["size"] == "1-3/8"

    shackle_2 = select_shackle(60000.0, 40.0, 20.0)
    assert shackle_2 is not None
    assert shackle_2["size"] == "1-1/4"

    assert select_shackle(200000.0, 42.0, 45.0) is None


def test_pin_plate_check():
    ratios = pin_plate_check(85800.0, LUG_A, 38.86, 2.0)
    assert ratios["3-45"] == pytest.approx(0.252, abs=0.001)
    assert ratios["3-49"] == pytest.approx(0.306, abs=0.001)
    assert ratios["3-50"] == pytest.approx(0.296, abs=0.001)
    assert ratios["3-53"] == pytest.approx(0.285, abs=0.001)


def test_strong_axis_allowable():
    assert strong_axis_allowable(90.0, 250.0, 25.0, 275.0, 2.0) == pytest.approx(171.875, abs=0.001)
    assert strong_axis_allowable(900.0, 400.0, 20.0, 275.0, 2.0) == pytest.approx(162.4, abs=0.1)
    assert strong_axis_allowable(300.0, 500.0, 10.0, 275.0, 2.0) == pytest.approx(126.67, abs=0.01)


def test_plate_check():
    ratios = plate_check(83238.0, 20810.0, 2574.0, LUG_A, 38.86, 2.0)
    assert ratios["3-35"] == pytest.approx(0.206, abs=0.001)
    assert ratios["3-28"] == pytest.approx(0.055, abs=0.001)
    assert ratios["3-37"] == pytest.approx(0.240, abs=0.001)


def test_weld_check():
    ratio_a, min_leg_a = weld_check(83238.0, 20810.0, 2574.0, LUG_A, 38.86, 2.0)
    assert ratio_a == pytest.approx(0.369, abs=0.001)
    assert min_leg_a == 5

    ratio_b, _ = weld_check(62429.0, 15607.0, 1931.0, LUG_B, 38.86, 2.0)
    assert ratio_b == pytest.approx(1.188, abs=0.001)


def test_weld_leg_needed():
    assert weld_leg_needed(62429.0, 15607.0, 1931.0, LUG_B, 38.86, 2.0) == 6
    assert weld_leg_needed(83238.0, 20810.0, 2574.0, LUG_A, 38.86, 2.0) == 5


def test_dnv_checks():
    shackle = {"size": "1-3/8", "wll": 13.5, "pin": 38.86, "jaw": 57.15}

    res_pass = dnv_checks(LUG_A, shackle, 0.03)
    assert res_pass["G1"] == "PASS"
    assert res_pass["G2"] == "PASS"
    assert res_pass["G3"] == "PASS"
    assert res_pass["G4"] == "PASS"
    assert res_pass["G5"] == "PASS"
    assert res_pass["G6"] == "PASS"

    res_g5 = dnv_checks(LUG_A, shackle, 0.20)
    assert res_g5["G5"] == "FAIL"

    lug_no_cheek = LUG_A.copy()
    lug_no_cheek["tc"] = 0.0
    res_g2 = dnv_checks(lug_no_cheek, shackle, 0.03)
    assert res_g2["G2"] == "FAIL"
