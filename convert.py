"""
Converts Indian Railways Kaggle JSON files (stations.json, trains.json,
schedules.json) into clean, flat CSVs ready for MySQL LOAD DATA INFILE.

Confirmed schema:
  stations.json -> GeoJSON FeatureCollection, properties: state, code, name, zone, address
  trains.json   -> GeoJSON FeatureCollection, properties: number, name, from_station_code,
                    from_station_name, to_station_code, to_station_name, departure, arrival,
                    duration_h, duration_m, distance, type, zone, first_class, chair_car,
                    sleeper, first_ac, second_ac, third_ac, return_train, classes
                    geometry.coordinates -> full route path, kept as a JSON text column
                    (route_path) for possible future use (e.g. mapping), not used in any
                    of the current optimization queries.
  schedules.json -> plain flat array of {id, train_number, train_name, station_code,
                    station_name, arrival, departure, day}

Run from your project root:
    python convert.py
Expects the three JSON files in ./data/ and writes CSVs to the same folder.
"""

import json
import csv
import os

DATA_DIR = "data"


def clean(value):
    """Convert JSON null, the literal string 'None', and booleans into
    MySQL-friendly values. Booleans -> 1/0. None/'None' -> empty (NULL)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str) and value.strip() == "None":
        return ""
    return value


def get_feature_list(data):
    """Handle both {"type": "FeatureCollection", "features": [...]} and
    a bare list of features, depending on which Kaggle mirror was used."""
    if isinstance(data, dict) and "features" in data:
        return data["features"]
    return data


def convert_stations():
    path = os.path.join(DATA_DIR, "stations.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = get_feature_list(data)

    out_path = os.path.join(DATA_DIR, "stations.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "name", "state", "zone", "address", "latitude", "longitude"])
        count = 0
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry")
            lat, lng = "", ""
            if geom and geom.get("type") == "Point" and geom.get("coordinates"):
                lng, lat = geom["coordinates"][0], geom["coordinates"][1]
            writer.writerow([
                clean(props.get("code")),
                clean(props.get("name")),
                clean(props.get("state")),
                clean(props.get("zone")),
                clean(props.get("address")),
                lat,
                lng,
            ])
            count += 1
    print(f"stations.csv written: {count} rows")


def convert_trains():
    path = os.path.join(DATA_DIR, "trains.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = get_feature_list(data)

    out_path = os.path.join(DATA_DIR, "trains.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "train_number", "train_name", "train_type", "zone",
            "from_station_code", "from_station_name",
            "to_station_code", "to_station_name",
            "departure", "arrival", "duration_h", "duration_m", "distance",
            "first_class", "chair_car", "sleeper",
            "first_ac", "second_ac", "third_ac", "return_train",
            "route_path"
        ])
        count = 0
        for feat in features:
            p = feat.get("properties", {})
            geom = feat.get("geometry")

            # Keep the full route path as a compact JSON string (list of
            # [lng, lat] points). Stored but unused for now -- available
            # later for mapping/geospatial work without re-parsing the
            # original JSON files.
            route_path = ""
            if geom and geom.get("type") == "LineString" and geom.get("coordinates"):
                route_path = json.dumps(geom["coordinates"])

            writer.writerow([
                clean(p.get("number")),
                clean(p.get("name")),
                clean(p.get("type")),
                clean(p.get("zone")),
                clean(p.get("from_station_code")),
                clean(p.get("from_station_name")),
                clean(p.get("to_station_code")),
                clean(p.get("to_station_name")),
                clean(p.get("departure")),
                clean(p.get("arrival")),
                clean(p.get("duration_h")),
                clean(p.get("duration_m")),
                clean(p.get("distance")),
                clean(p.get("first_class")),
                clean(p.get("chair_car")),
                clean(p.get("sleeper")),
                clean(p.get("first_ac")),
                clean(p.get("second_ac")),
                clean(p.get("third_ac")),
                clean(p.get("return_train")),
                route_path,
            ])
            count += 1
    print(f"trains.csv written: {count} rows")


def convert_schedules():
    path = os.path.join(DATA_DIR, "schedules.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # schedules.json is a flat list of plain dicts (no geometry/properties nesting)
    records = data["schedules"] if isinstance(data, dict) and "schedules" in data else data

    out_path = os.path.join(DATA_DIR, "schedules.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "train_number", "train_name", "station_code",
            "station_name", "arrival", "departure", "day"
        ])
        count = 0
        for rec in records:
            writer.writerow([
                clean(rec.get("id")),
                clean(rec.get("train_number")),
                clean(rec.get("train_name")),
                clean(rec.get("station_code")),
                clean(rec.get("station_name")),
                clean(rec.get("arrival")),
                clean(rec.get("departure")),
                clean(rec.get("day")),
            ])
            count += 1
    print(f"schedules.csv written: {count} rows")


if __name__ == "__main__":
    convert_stations()
    convert_trains()
    convert_schedules()
    print("Done. CSVs are in the data/ folder.")