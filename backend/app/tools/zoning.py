"""Phase 1: site geometry, setbacks and envelope limits (Shapely)."""
import json, math
from pathlib import Path
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import transform
from pyproj import CRS, Transformer

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "zoning"
if not CONFIG_DIR.exists():  # running from repo root
    CONFIG_DIR = Path(__file__).resolve().parents[3] / "config" / "zoning"


def get_zoning_config(country_code: str) -> dict:
    p = CONFIG_DIR / f"{country_code.upper()}.json"
    if not p.exists():
        return {"error": f"no config for {country_code}", "available": [f.stem for f in CONFIG_DIR.glob('*.json')]}
    return json.loads(p.read_text(encoding="utf-8"))


def _to_local_m(coords, crs):
    if crs == "local_m":
        return Polygon(coords)
    lon0 = sum(c[0] for c in coords) / len(coords)
    lat0 = sum(c[1] for c in coords) / len(coords)
    zone = int((lon0 + 180) // 6) + 1
    utm = CRS.from_proj4(f"+proj=utm +zone={zone} {'+south' if lat0 < 0 else ''} +datum=WGS84 +units=m")
    t = Transformer.from_crs("EPSG:4326", utm, always_xy=True).transform
    return transform(t, Polygon(coords))


def compute_envelope(coords, crs="local_m", front_edge_index=0, setbacks_m=None,
                     max_bcr=None, max_far=None, max_height_m=None, floor_height_m=3.0):
    """coords: [[x,y],...] (local metres, or [lon,lat] if crs='lonlat').
    setbacks_m: {"front":..,"side":..,"rear":..}. Edge i runs from point i to i+1.
    Setbacks are applied per edge as bands, so this is exact for convex lots and
    approximate for strongly concave ones."""
    poly = orient(_to_local_m(coords, crs), 1.0)  # counter-clockwise
    if not poly.is_valid:
        return {"error": "site polygon is invalid (self-intersecting?)"}
    pts = list(poly.exterior.coords)[:-1]
    n = len(pts)
    sb = {"front": 0, "side": 0, "rear": 0, **(setbacks_m or {})}

    def edge_vec(i):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        return x2 - x1, y2 - y1

    # orient() may reverse order; match front edge by nearest midpoint to the original edge
    orig = list(Polygon(_to_local_m(coords, crs)).exterior.coords)[:-1]
    fm = [(orig[front_edge_index % len(orig)][k] + orig[(front_edge_index + 1) % len(orig)][k]) / 2 for k in (0, 1)]
    mids = [((pts[i][0] + pts[(i + 1) % n][0]) / 2, (pts[i][1] + pts[(i + 1) % n][1]) / 2) for i in range(n)]
    f = min(range(n), key=lambda i: math.dist(mids[i], fm))
    fx, fy = edge_vec(f)
    fl = math.hypot(fx, fy)
    rear = min((i for i in range(n) if i != f),
               key=lambda i: (edge_vec(i)[0] * fx + edge_vec(i)[1] * fy) / (math.hypot(*edge_vec(i)) * fl))

    buildable = poly
    L = 1000.0
    for i in range(n):
        d = sb["front"] if i == f else sb["rear"] if i == rear else sb["side"]
        if d <= 0:
            continue
        dx, dy = edge_vec(i)
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        nx, ny = -uy, ux  # inward normal for CCW
        p, q = pts[i], pts[(i + 1) % n]
        band = Polygon([(p[0] - ux * L, p[1] - uy * L), (q[0] + ux * L, q[1] + uy * L),
                        (q[0] + ux * L + nx * d, q[1] + uy * L + ny * d), (p[0] - ux * L + nx * d, p[1] - uy * L + ny * d)])
        buildable = buildable.difference(band)

    site_area = poly.area
    out = {
        "site_area_m2": round(site_area, 2),
        "buildable_area_m2": round(buildable.area, 2),
        "buildable_polygon_local_m": [list(c) for c in getattr(buildable, "exterior", Polygon()).coords] if not buildable.is_empty and buildable.geom_type == "Polygon" else None,
        "front_edge": f, "rear_edge": rear,
    }
    fp = buildable.area
    if max_bcr is not None:
        fp = min(fp, site_area * max_bcr)
    out["max_footprint_m2"] = round(fp, 2)
    if max_far is not None:
        out["max_total_floor_area_m2"] = round(site_area * max_far, 2)
    if max_height_m is not None:
        out["max_floors_by_height"] = int(max_height_m // floor_height_m)
        if max_far is not None and fp > 0:
            out["max_floors_by_far"] = int((site_area * max_far) // fp)
    return out
