from gui import campos


def test_para_float_virgula():
    assert campos.para_float("1,5") == 1.5
    assert campos.para_float("") == 0.0
    assert campos.para_float(None, default=2.0) == 2.0
    assert campos.para_float("xyz", default=9.0) == 9.0


def test_para_int():
    assert campos.para_int("3,9") == 4
    assert campos.para_int("") == 0
    assert campos.para_int(True) == 1


def test_para_complexo():
    assert campos.para_complexo("0.01+0.1j") == complex(0.01, 0.1)
    assert campos.para_complexo("0.01 + 0.1i") == complex(0.01, 0.1)
    assert campos.para_complexo("0.02,0.06") == complex(0.02, 0.06)


def test_formatadores():
    assert campos.fmt(1.23456, 2) == "1.23"
    assert campos.fmt("nan") == "—"
    assert campos.fmt_complexo(complex(1, -2), 1) == "1.0−j2.0"


def test_graus_rad():
    assert round(campos.graus_para_rad(180), 5) == round(3.14159265, 5)
