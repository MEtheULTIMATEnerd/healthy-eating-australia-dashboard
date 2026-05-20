# Healthy Intentions, Unhealthy Reality

Healthy Eating vs Fast Food Reality in Australia.

This FIT2179 Data Visualisation 2 project is a single-page Vega-Lite storytelling website for a general Australian audience. It uses public ABS and AIHW datasets to tell a narrative from health awareness to food exposure, behaviour, outcomes, and socioeconomic inequality.

## Structure

- `index.html` contains the scrolling editorial story.
- `style.css` defines the typography, layout, colour system, and responsive behaviour.
- `script.js` embeds each Vega-Lite view.
- `js/*.vg.json` contains human-readable Vega-Lite specifications.
- `data/cleaned/*.csv` contains lightweight chart-ready data.
- `data/australia_states.geojson` contains a simplified local GeoJSON used by the maps.
- `build_project.py` regenerates the cleaned data and Vega-Lite specifications from the raw Excel files in the parent workspace.

## Data Sources

- Australian Bureau of Statistics, National Health Survey 2022.
- Australian Bureau of Statistics, National Nutrition and Physical Activity Survey: Food and Nutrients 2023.
- Australian Bureau of Statistics, Apparent Consumption of Selected Foodstuffs 2023-24: Geospatial Dietary Indicators.
- Australian Institute of Health and Welfare, Overweight and obesity data tables 2024.

The provided raw datasets do not include individual fast-food outlet locations. Charts labelled as a fast-food pressure proxy therefore use transparent public-data proxies such as obesity rate and unmet fruit/vegetable recommendations rather than fabricated restaurant locations.

## Local Preview

From this folder:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## GitHub Pages Deployment

1. Commit the `project` folder contents to the repository.
2. In GitHub, open **Settings > Pages**.
3. Choose the branch containing this project.
4. Set the Pages source folder to the project root or move these files to the repository root.
5. Wait for GitHub Pages to publish the URL.

Suggested commands:

```bash
git add project
git commit -m "Build healthy eating Vega-Lite story"
git push origin main
```
