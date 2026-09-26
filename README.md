# Lebanon's tourism supply: a few hubs, many empty towns

**Live app:** https://lebanon-tourism-chakhtoura.streamlit.app

A one-page Streamlit app for the MSBA 325 interactivity activity (American University of Beirut).
It builds on my Plotly assignment and uses the same dataset: counts of restaurants, cafés, hotels and
guest houses in 1,137 Lebanese towns, published by IMPACT Open Data and served through AUB's CODEC
platform (linked.aub.edu.lb).

## What the page does

- **Two related charts from the Plotly assignment.** The grouped bar chart of venues by type, and the
  restaurants-vs-cafés scatter plot with one dot per town.
- **Two linked interaction features.** A governorate control (①) sets the options of a town search
  box (②), so the reader drills down from Lebanon to a governorate to a single town. The bar chart
  switches from governorates to that governorate's top towns, the scatter highlights the selection
  against the rest of Lebanon in grey, and the chosen town is labelled in both charts.
- **Context, insights and design justifications** are on the page itself. The justifications are
  under "Why the page works this way".

## Run it locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Files

| File | Purpose |
|---|---|
| `streamlit_app.py` | The app: data cleaning, both charts, the linked widgets and the page text |
| `data/tourism.csv` | The dataset (CODEC *Tourism*, one row per town) |
| `requirements.txt` | Package versions the app was tested with |
| `.streamlit/config.toml` | Light theme with the violet accent colour used in the charts |

Antonio Chakhtoura · MSBA 325
