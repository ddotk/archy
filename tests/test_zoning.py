import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
from app.tools.zoning import compute_envelope, get_zoning_config

SITE = [[0, 0], [20, 0], [20, 30], [0, 30]]  # 20 x 30 m, front edge = edge 0 (y=0)

def test_setbacks_rectangle():
    r = compute_envelope(SITE, front_edge_index=0, setbacks_m={"front": 3, "side": 2, "rear": 2},
                         max_bcr=0.7, max_far=2.0, max_height_m=12, floor_height_m=3.2)
    assert r["site_area_m2"] == 600
    assert r["buildable_area_m2"] == 16 * 25  # (20-4) x (30-5)
    assert r["max_footprint_m2"] == 400
    assert r["max_total_floor_area_m2"] == 1200
    assert r["max_floors_by_height"] == 3 and r["max_floors_by_far"] == 3

def test_clockwise_input_same_result():
    r = compute_envelope(SITE[::-1], front_edge_index=2, setbacks_m={"front": 3, "side": 2, "rear": 2})
    assert r["buildable_area_m2"] == 400

def test_lonlat():
    s = [[100.0, 15.0], [100.0002, 15.0], [100.0002, 15.0003], [100.0, 15.0003]]
    assert compute_envelope(s, crs="lonlat")["site_area_m2"] > 500

def test_config():
    assert "residential_house" in get_zoning_config("TH")["building_types"]
