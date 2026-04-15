import requests
from typing import Literal
import xml.etree.ElementTree as ET

URL = "http://localhost:8000/"


def create_employee(first_name: str, last_name: str, email: str, eid: str) -> dict:
    url = f"{URL}employees"
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "eid": eid,
    }
    res = requests.post(url=url, json=payload)
    return res.json()


def get_employee_by_id(eid: str) -> dict:
    url = f"{URL}employees/{eid}"
    payload = {"eid": eid}
    res = requests.get(url=url, json=payload)
    return res.json()


def create_asset(
    asset_type: str,
    description: str,
    estimated_value: int,
    geometry_type: Literal["point", "line"],
    coords: list[list[float]],
) -> dict:
    url = f"{URL}assets"
    if geometry_type == "point":
        payload = {
            "asset_type": asset_type,
            "description": description,
            "estimated_value": estimated_value,
            "geometry_type": geometry_type,
            "point": coords[0],
            "line": None,
        }
    elif geometry_type == "line":
        payload = {
            "asset_type": asset_type,
            "description": description,
            "estimated_value": estimated_value,
            "geometry_type": geometry_type,
            "point": None,
            "line": {"linestring": coords},
        }
    res = requests.post(url=url, json=payload)
    return res.json()


def make_coords(coords: str) -> list[list[float]]:
    xyz_coords = []
    arr = coords.split(" ")
    for xyz in arr:
        xyz_coords.append(xyz.split(","))
    return xyz_coords


def get_linestring_from_kml(path: str):
    coords_str = ""
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"kml": "http://earth.google.com/kml/2.2"}
    lines = root.findall(".//kml:Document/kml:Placemark/kml:LineString", ns)
    for line in lines:
        coords = line.find("kml:coordinates", ns)
        if coords is not None:
            coords_str = coords.text.strip()
    return coords_str


if __name__ == "__main__":
    type = "trail"
    descr = "test description of a morning walk"
    value = 3000
    gtype = "line"
    linestring = get_linestring_from_kml(r"C:\Users\bowen\Desktop\Morning walking.kml")
    coords = make_coords(linestring)
    # for lon, lat in coords:
    #     print(f"lon: {lon} lat: {lat}")
    print(create_asset(type, descr, value, gtype, coords))
