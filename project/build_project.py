from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "data" / "Uncleaned"
CLEAN = ROOT / "data" / "cleaned"
JS = ROOT / "js"


STATE_NAMES = {
    "NSW": "New South Wales",
    "Vic.": "Victoria",
    "Qld": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "Tas.": "Tasmania",
    "NT": "Northern Territory",
    "ACT": "Australian Capital Territory",
}

STATE_CENTROIDS = {
    "New South Wales": (147.0, -32.2),
    "Victoria": (144.4, -37.0),
    "Queensland": (145.5, -22.5),
    "South Australia": (135.0, -30.2),
    "Western Australia": (122.4, -25.5),
    "Tasmania": (146.6, -42.0),
    "Northern Territory": (133.6, -19.5),
    "Australian Capital Territory": (149.1, -35.3),
}


def val(x):
    if pd.isna(x) or str(x).strip().lower() in {"na", "np", ". .", "-"}:
        return None
    return float(str(x).replace(",", "").strip())


def write_csv(name, rows, fieldnames):
    path = CLEAN / name
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_sheet(path, sheet):
    return pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)


def make_geojson():
    # Lightweight simplified polygons for Australian states/territories.
    polygons = {
        "Western Australia": [[112, -14], [129, -14], [129, -35], [115, -35], [113, -30], [112, -24], [112, -14]],
        "Northern Territory": [[129, -11], [138, -11], [138, -26], [129, -26], [129, -11]],
        "South Australia": [[129, -26], [141, -26], [141, -38], [132, -38], [129, -35], [129, -26]],
        "Queensland": [[138, -10], [154, -10], [154, -29], [141, -29], [141, -26], [138, -26], [138, -10]],
        "New South Wales": [[141, -29], [153.8, -29], [153.8, -37.7], [149.5, -37.7], [141, -34], [141, -29]],
        "Victoria": [[141, -34], [149.5, -37.7], [147.5, -39.2], [141, -38], [141, -34]],
        "Tasmania": [[144.5, -40.6], [148.5, -40.6], [148.5, -43.8], [144.5, -43.8], [144.5, -40.6]],
        "Australian Capital Territory": [[148.75, -35.1], [149.4, -35.1], [149.4, -35.65], [148.75, -35.65], [148.75, -35.1]],
    }
    features = []
    for name, coords in polygons.items():
        features.append({
            "type": "Feature",
            "properties": {"state": name},
            "geometry": {"type": "Polygon", "coordinates": [coords]},
        })
    write_json(ROOT / "data" / "australia_states.geojson", {"type": "FeatureCollection", "features": features})


def build_data():
    CLEAN.mkdir(parents=True, exist_ok=True)
    JS.mkdir(parents=True, exist_ok=True)
    make_geojson()

    # Awareness/behaviour over time.
    n14 = SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC14.xlsx"
    awareness = []
    for year, sheet in [(1995, "Table 14.5_Proportions 1995"), (2012, "Table 14.3_Proportions 2011-12"), (2023, "Table 14.1_Proportions 2023")]:
        df = load_sheet(n14, sheet)
        for row_idx in [22, 23, 24, 31]:
            awareness.append({
                "year": year,
                "metric": str(df.iloc[row_idx, 0]).replace("(a)", "").strip(),
                "percent": val(df.iloc[row_idx, 10]),
                "source": "ABS NNPAS sweetened beverages",
            })
    nhs1 = load_sheet(SRC / "National-Health-Survey-2022" / "NHSDC01.xlsx", "Table 1.3_Proportions")
    years = [2007, 2012, 2015, 2018, 2022]
    for idx, year in enumerate(years, start=3):
        awareness.append({
            "year": year,
            "metric": "Did not meet fruit and vegetable recommendation",
            "percent": val(nhs1.iloc[76, idx]),
            "source": "ABS NHS fruit and vegetable intake",
        })
    write_csv("food_awareness.csv", awareness, ["year", "metric", "percent", "source"])

    # Recommended vs actual intake.
    adg = load_sheet(SRC / "4316DO002_202324_ESTIMATES.xlsx", "Table 5")
    recommended = {
        "Grains and cereals": 6.0,
        "Vegetables and legumes/beans": 5.0,
        "Fruit": 2.0,
        "Milk, yoghurt, cheese and/or alternatives": 2.5,
        "Meats, poultry, fish, eggs, tofu, nuts and seeds and legumes/beans": 2.5,
        "Unsaturated spreads and oils": 2.0,
    }
    intake = []
    for r in range(13, 19):
        group = str(adg.iloc[r, 1])
        actual = val(adg.iloc[r, 8])
        rec = recommended[group]
        short = {
            "Vegetables and legumes/beans": "Vegetables",
            "Milk, yoghurt, cheese and/or alternatives": "Dairy",
            "Meats, poultry, fish, eggs, tofu, nuts and seeds and legumes/beans": "Protein foods",
            "Unsaturated spreads and oils": "Healthy oils",
        }.get(group, group)
        intake.append({"food_group": short, "recommended_serves": rec, "actual_serves": actual, "gap": actual - rec})
    write_csv("healthy_vs_actual_intake.csv", intake, ["food_group", "recommended_serves", "actual_serves", "gap"])

    # State outcomes and map proxies.
    nhs2 = load_sheet(SRC / "National-Health-Survey-2022" / "NHSDC02.xlsx", "Table 2.3_Proportions")
    states = list(STATE_NAMES.keys())
    state_rows = []
    for i, abbr in enumerate(states, start=1):
        name = STATE_NAMES[abbr]
        lon, lat = STATE_CENTROIDS[name]
        obesity = val(nhs2.iloc[64, i])
        overweight_obese = val(nhs2.iloc[65, i])
        unmet_fruit = val(nhs2.iloc[73, i])
        unmet_veg = val(nhs2.iloc[74, i])
        exposure = round((unmet_fruit + unmet_veg + obesity) / 3, 1)
        state_rows.append({
            "state": name,
            "abbr": abbr.replace(".", ""),
            "obesity_rate": obesity,
            "overweight_obese_rate": overweight_obese,
            "did_not_meet_fruit": unmet_fruit,
            "did_not_meet_vegetables": unmet_veg,
            "fast_food_pressure_proxy": exposure,
            "urban_regional": "Mostly urban" if name in {"New South Wales", "Victoria", "Queensland", "Australian Capital Territory"} else "More regional/remote",
            "lon": lon,
            "lat": lat,
        })
    write_csv("obesity_by_state.csv", state_rows, list(state_rows[0].keys()))
    write_csv("fastfood_density.csv", state_rows, list(state_rows[0].keys()))

    # Discretionary energy by age.
    disc = load_sheet(SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC08.xlsx", "Table 8.1_Proportions Persons")
    ages = ["2-4", "5-11", "12-17", "18-29", "30-49", "50-64", "65-74", "75+"]
    selected_rows = {
        13: "Soft drinks",
        24: "Cereal-based discretionary foods",
        25: "Sweet biscuits",
        27: "Cakes and desserts",
        28: "Pastries",
        30: "Fats and oils",
    }
    stream = []
    for r, group in selected_rows.items():
        for c, age in enumerate(ages, start=1):
            stream.append({"age_group": age, "category": group, "energy_percent": val(disc.iloc[r, c])})
    write_csv("discretionary_stream.csv", stream, ["age_group", "category", "energy_percent"])

    # Sankey-style proxy path and heatmap from disadvantage tables.
    risk = load_sheet(SRC / "National-Health-Survey-2022" / "NHSDC06.xlsx", "Table 6.3_Proportions")
    bev_all = load_sheet(SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC19-20.xlsx", "Table 19.1_Proportions")
    quintiles = ["First quintile", "Second quintile", "Third quintile", "Fourth quintile", "Fifth quintile"]
    sankey = []
    for qi, q in enumerate(quintiles, start=1):
        zero_activity = val(risk.iloc[20 + qi, 4])
        sweet_drinks = val(bev_all.iloc[24, qi])
        obesity = val(risk.iloc[20 + qi, 10])
        sankey += [
            {"source": q, "target": "Time pressure proxy", "value": zero_activity, "stage": "constraint"},
            {"source": "Time pressure proxy", "target": "Sweetened drink exposure", "value": sweet_drinks, "stage": "choice"},
            {"source": "Sweetened drink exposure", "target": "Obesity outcome", "value": obesity, "stage": "outcome"},
        ]
    write_csv("sankey_pathways.csv", sankey, ["source", "target", "value", "stage"])

    child = load_sheet(SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC19-20.xlsx", "Table 20.1_Proportions Child")
    adult = load_sheet(SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC19-20.xlsx", "Table 20.3_Proportions Adult")
    heat = []
    for label, df in [("Children 2-17", child), ("Adults 18+", adult)]:
        for i, q in enumerate(quintiles, start=1):
            heat.append({"age_group": label, "income_group": q.replace(" quintile", ""), "selected_beverage_percent": val(df.iloc[19, i])})
    write_csv("heatmap_age_income.csv", heat, ["age_group", "income_group", "selected_beverage_percent"])

    # Socioeconomic divide / barriers.
    foodsec = load_sheet(SRC / "NNPAS-2023-Food-and-nutrients" / "NNPASDC13.xlsx", "Table 13.3_Proportions")
    dumbbell = []
    for r in range(17, 22):
        group = str(foodsec.iloc[r, 0]).replace("Lowest", "Lowest income").replace("Highest", "Highest income")
        dumbbell.append({
            "income_group": group,
            "food_secure": val(foodsec.iloc[r, 1]),
            "food_insecure": val(foodsec.iloc[r, 6]),
        })
    write_csv("barriers_to_healthy_eating.csv", dumbbell, ["income_group", "food_secure", "food_insecure"])
    barriers = [
        {"barrier": "Vegetable recommendation not met", "group": "All adults", "percent": 93.5},
        {"barrier": "Fruit recommendation not met", "group": "All adults", "percent": 55.8},
        {"barrier": "Selected beverages consumed", "group": "Children, lowest quintile", "percent": 38.1},
        {"barrier": "Obesity", "group": "Lowest disadvantage quintile", "percent": 35.4},
        {"barrier": "Food insecurity: lone-parent households", "group": "Lone-parent households", "percent": 34.0},
        {"barrier": "Food insecurity: lowest income quintile", "group": "Lowest income quintile", "percent": 23.2},
    ]
    write_csv("lollipop_barriers.csv", barriers, ["barrier", "group", "percent"])


def base_spec(title, subtitle=None):
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": title, "subtitle": subtitle or "", "anchor": "start", "font": "Poppins", "fontSize": 18, "subtitleFontSize": 12},
        "config": {
            "font": "Inter",
            "axis": {"labelColor": "#46524f", "titleColor": "#24302d", "gridColor": "#e7ebe8", "tickColor": "#d8ded9"},
            "view": {"stroke": None},
            "legend": {"orient": "bottom", "titleColor": "#24302d", "labelColor": "#46524f"},
        },
        "width": "container",
        "height": 320,
    }
    return spec


def specs():
    green = "#2e7d62"
    teal = "#2f9c95"
    orange = "#e66a35"
    red = "#c7432f"
    purple = "#4b345f"

    awareness = base_spec("The health signal is visible, but incomplete", "Sweetened beverage participation fell while fruit-and-vegetable gaps persisted.")
    awareness.update({
        "data": {"url": "data/cleaned/food_awareness.csv"},
        "mark": {"type": "line", "point": {"filled": True, "size": 70}, "strokeWidth": 3},
        "encoding": {
            "x": {"field": "year", "type": "ordinal", "title": None},
            "y": {"field": "percent", "type": "quantitative", "title": "% of people", "scale": {"domain": [0, 100]}},
            "color": {"field": "metric", "type": "nominal", "scale": {"range": [green, orange, red, teal]}},
            "tooltip": [{"field": "year"}, {"field": "metric"}, {"field": "percent", "format": ".1f"}],
        },
    })

    intake = base_spec("Recommended plates, actual plates", "Most Australian Dietary Guideline groups sit below recommended serves.")
    intake.update({
        "data": {"url": "data/cleaned/healthy_vs_actual_intake.csv"},
        "transform": [{"fold": ["recommended_serves", "actual_serves"], "as": ["Measure", "Serves"]}],
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "y": {"field": "food_group", "type": "nominal", "sort": ["Grains and cereals", "Vegetables", "Healthy oils", "Protein foods", "Dairy", "Fruit"], "title": None},
            "x": {"field": "Serves", "type": "quantitative", "title": "Serves per 10,000 kJ"},
            "color": {"field": "Measure", "type": "nominal", "scale": {"domain": ["recommended_serves", "actual_serves"], "range": [green, orange]}, "legend": {"labelExpr": "datum.label == 'recommended_serves' ? 'Recommended' : 'Actual'"}},
            "yOffset": {"field": "Measure"},
            "tooltip": [{"field": "food_group", "title": "Food Group"}, {"field": "Measure", "title": "Measure"}, {"field": "Serves", "title": "Serves per 10,000 kJ", "format": ".1f"}],
        },
    })

    fastmap = base_spec("Fast-food pressure proxy by state", "Proxy combines adult obesity and unmet fruit/vegetable recommendations.")
    fastmap.update({
        "layer": [
            {
                "data": {"url": "data/australia_states.geojson", "format": {"type": "json", "property": "features"}},
                "transform": [
                    {"calculate": "datum.properties.STATE_NAME || datum.properties.state || datum.properties.name", "as": "state_name"},
                    {"lookup": "state_name", "from": {"data": {"url": "data/cleaned/fastfood_density.csv"}, "key": "state", "fields": ["fast_food_pressure_proxy", "obesity_rate", "did_not_meet_vegetables"]}}
                ],
                "projection": {"type": "mercator", "center": [134, -27], "scale": 520},
                "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 1},
                "encoding": {"color": {"field": "fast_food_pressure_proxy", "type": "quantitative", "title": "Pressure proxy", "scale": {"range": ["#d6ede1", "#f1a35f", red]}}, "tooltip": [{"field": "state_name", "title": "State"}, {"field": "fast_food_pressure_proxy", "format": ".1f"}, {"field": "obesity_rate", "format": ".1f"}]},
            }
        ],
    })

    bubble = base_spec("Exposure concentrates differently across the map", "Bubbles show the same proxy at state centroids for direct comparison.")
    bubble.update({
        "data": {"url": "data/cleaned/fastfood_density.csv"},
        "projection": {"type": "mercator", "center": [134, -27], "scale": 520},
        "layer": [
            {"data": {"url": "data/australia_states.geojson", "format": {"type": "json", "property": "features"}}, "mark": {"type": "geoshape", "fill": "#edf3ef", "stroke": "#cfd8d2"}},
            {"mark": {"type": "circle", "opacity": 0.78, "stroke": "white", "strokeWidth": 1.5}, "encoding": {"longitude": {"field": "lon"}, "latitude": {"field": "lat"}, "size": {"field": "fast_food_pressure_proxy", "type": "quantitative", "scale": {"range": [120, 1600]}, "title": "Proxy"}, "color": {"field": "obesity_rate", "type": "quantitative", "scale": {"range": ["#f3ba77", red]}, "title": "Obesity %"}, "tooltip": [{"field": "state"}, {"field": "fast_food_pressure_proxy"}, {"field": "obesity_rate"}]}},
        ],
    })

    stream = base_spec("Discretionary energy is embedded across age", "Selected discretionary food groups as a share of daily energy.")
    stream.update({
        "data": {"url": "data/cleaned/discretionary_stream.csv"},
        "mark": {"type": "area", "interpolate": "monotone"},
        "encoding": {
            "x": {"field": "age_group", "type": "ordinal", "title": "Age group"},
            "y": {"field": "energy_percent", "type": "quantitative", "stack": "center", "title": "Discretionary energy share"},
            "color": {"field": "category", "scale": {"range": ["#c7432f", "#e66a35", "#f0aa4b", "#8e5b48", "#5c4b51", "#2f9c95"]}},
            "tooltip": [{"field": "age_group"}, {"field": "category"}, {"field": "energy_percent", "format": ".1f"}],
        },
    })

    sankey = base_spec("A constraint pathway, not a simple choice", "A Vega-Lite flow proxy links disadvantage, time constraints, beverage exposure and obesity.")
    sankey.update({
        "data": {"url": "data/cleaned/sankey_pathways.csv"},
        "mark": {"type": "bar", "cornerRadiusEnd": 5},
        "encoding": {
            "y": {"field": "source", "type": "nominal", "sort": None, "title": None},
            "x": {"field": "value", "type": "quantitative", "title": "% proxy value"},
            "color": {"field": "stage", "scale": {"range": [purple, orange, red]}},
            "tooltip": [{"field": "source"}, {"field": "target"}, {"field": "value", "format": ".1f"}],
        },
    })

    heat = base_spec("Convenience exposure is steepest for lower-income children", "Selected beverage consumption by age band and disadvantage quintile.")
    heat.update({
        "data": {"url": "data/cleaned/heatmap_age_income.csv"},
        "mark": {"type": "rect", "cornerRadius": 4},
        "encoding": {
            "x": {"field": "income_group", "type": "ordinal", "title": "Disadvantage quintile"},
            "y": {"field": "age_group", "type": "nominal", "title": None},
            "color": {"field": "selected_beverage_percent", "type": "quantitative", "scale": {"range": ["#f8e7d2", "#e66a35", "#9f2d26"]}, "title": "% consumed"},
            "tooltip": [{"field": "age_group"}, {"field": "income_group"}, {"field": "selected_beverage_percent", "format": ".1f"}],
        },
    })

    obesity_map = base_spec("Obesity outcomes are geographically uneven", "Adult obesity rates by state and territory, NHS 2022.")
    obesity_map.update({
        "data": {"url": "data/australia_states.geojson", "format": {"type": "json", "property": "features"}},
        "transform": [
            {"calculate": "datum.properties.STATE_NAME || datum.properties.state || datum.properties.name", "as": "state_name"},
            {"lookup": "state_name", "from": {"data": {"url": "data/cleaned/obesity_by_state.csv"}, "key": "state", "fields": ["obesity_rate", "overweight_obese_rate"]}}
        ],
        "projection": {"type": "mercator", "center": [134, -27], "scale": 520},
        "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 1},
        "encoding": {"color": {"field": "obesity_rate", "type": "quantitative", "scale": {"range": ["#dceee4", "#7f7aa8", purple]}, "title": "Obesity %"}, "tooltip": [{"field": "state_name", "title": "State"}, {"field": "obesity_rate", "format": ".1f"}, {"field": "overweight_obese_rate", "format": ".1f"}]},
    })

    scatter = base_spec("Exposure and outcomes move together", "State-level proxy exposure versus adult obesity rate.")
    scatter.update({
        "data": {"url": "data/cleaned/obesity_by_state.csv"},
        "mark": {"type": "circle", "filled": True, "opacity": 0.82, "stroke": "white", "strokeWidth": 1},
        "encoding": {
            "x": {"field": "fast_food_pressure_proxy", "type": "quantitative", "title": "Fast-food pressure proxy"},
            "y": {"field": "obesity_rate", "type": "quantitative", "title": "Adult obesity (%)", "scale": {"zero": False}},
            "size": {"field": "overweight_obese_rate", "type": "quantitative", "title": "Overweight/obese %", "scale": {"range": [160, 900]}},
            "color": {"field": "urban_regional", "scale": {"range": [teal, purple]}, "title": None},
            "tooltip": [{"field": "state"}, {"field": "fast_food_pressure_proxy"}, {"field": "obesity_rate"}, {"field": "overweight_obese_rate"}],
        },
    })

    dumbbell = base_spec("Food security splits sharply by income", "A dumbbell-style access gap: secure versus insecure households.")
    dumbbell.update({
        "data": {"url": "data/cleaned/barriers_to_healthy_eating.csv"},
        "layer": [
            {"mark": {"type": "rule", "strokeWidth": 3, "color": "#ccd7cf"}, "encoding": {"y": {"field": "income_group", "type": "nominal", "sort": None, "title": None}, "x": {"field": "food_insecure", "type": "quantitative"}, "x2": {"field": "food_secure"}}},
            {"mark": {"type": "circle", "size": 130, "color": red}, "encoding": {"y": {"field": "income_group", "type": "nominal", "sort": None}, "x": {"field": "food_insecure", "type": "quantitative", "title": "% of households"}, "tooltip": [{"field": "income_group"}, {"field": "food_insecure"}]}},
            {"mark": {"type": "circle", "size": 130, "color": green}, "encoding": {"y": {"field": "income_group", "type": "nominal", "sort": None}, "x": {"field": "food_secure", "type": "quantitative"}, "tooltip": [{"field": "income_group"}, {"field": "food_secure"}]}},
        ],
        "resolve": {"scale": {"x": "shared"}},
    })

    lollipop = base_spec("The barriers are practical, not just educational", "Lollipop ranking of access, intake and outcome barriers.")
    lollipop.update({
        "data": {"url": "data/cleaned/lollipop_barriers.csv"},
        "encoding": {"y": {"field": "barrier", "type": "nominal", "sort": None, "title": None}},
        "layer": [
            {"mark": {"type": "bar", "height": 3, "color": "#d7ded8"}, "encoding": {"x": {"field": "percent", "type": "quantitative", "title": "%"}}},
            {"mark": {"type": "circle", "size": 160, "color": orange, "stroke": "white", "strokeWidth": 1}, "encoding": {"x": {"field": "percent", "type": "quantitative", "title": "%"}, "tooltip": [{"field": "barrier"}, {"field": "group"}, {"field": "percent"}]}},
        ],
    })

    for filename, spec in {
        "awareness.vg.json": awareness,
        "intake.vg.json": intake,
        "fastfood_map.vg.json": fastmap,
        "bubble_map.vg.json": bubble,
        "streamgraph.vg.json": stream,
        "sankey.vg.json": sankey,
        "heatmap.vg.json": heat,
        "obesity_map.vg.json": obesity_map,
        "scatter.vg.json": scatter,
        "dumbbell.vg.json": dumbbell,
        "lollipop.vg.json": lollipop,
    }.items():
        write_json(JS / filename, spec)


if __name__ == "__main__":
    build_data()
    specs()
