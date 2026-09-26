"""Lebanon's tourism supply, from governorate to town.

MSBA 325 - Streamlit interactivity activity.

Two charts from the Plotly assignment (the grouped bar of venues and the
restaurants-vs-cafes scatter) are driven by two LINKED widgets:

    1. a governorate control  ->  sets the options of
    2. a town search box      ->  which picks one town inside that governorate

so the reader drills down Lebanon -> governorate -> town instead of applying
two independent filters.

Run locally with:  streamlit run streamlit_app.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

AUTHOR = "Antonio Chakhtoura"

# The CSV path is built from this file's location, not from the current
# working directory, so the app finds its data wherever it is launched from
# (locally, or on Streamlit Community Cloud).
DATA_FILE = Path(__file__).parent / "data" / "tourism.csv"

ALL = "All of Lebanon"

# Venue types in a fixed order. Food & drink first, then lodging, so the two
# related pairs sit next to each other inside every group of bars.
VENUES = ["Restaurants", "Cafés", "Hotels", "Guest houses"]
SOURCE_COLUMNS = {
    "Total number of restaurants": "Restaurants",
    "Total number of cafes": "Cafés",
    "Total number of hotels": "Hotels",
    "Total number of guest houses": "Guest houses",
}

# Colour-blind-checked categorical palette: one fixed colour per venue type,
# the same at every drill-down level.
VENUE_COLORS = {
    "Restaurants": "#2a78d6",
    "Cafés": "#eb6834",
    "Hotels": "#1baf7a",
    "Guest houses": "#eda100",
}
FOCUS = "#4a3aa7"      # towns in the selected governorate (same violet as the selected button)
CONTEXT = "#cfcdc4"    # every other town: grey context
HIGHLIGHT = "#0b0b0b"  # the one town the reader asked about
INK = "#31333f"
MUTED = "#6b6a66"
GRID = "#ebeae4"
AXIS = "#c3c2b7"
FONT = '"Source Sans Pro", "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif'

# refArea names a district on some rows and only a governorate on others.
# Each district is mapped up to its governorate so the seven governorate
# totals are complete and do not overlap.
DISTRICT_TO_GOVERNORATE = {
    "Aley": "Mount Lebanon", "Baabda": "Mount Lebanon", "Byblos": "Mount Lebanon",
    "Chouf": "Mount Lebanon", "Keserwan": "Mount Lebanon", "Matn": "Mount Lebanon",
    "Batroun": "North", "Bsharri": "North", "Koura": "North",
    "Miniyeh–Danniyeh": "North", "Tripoli": "North", "Zgharta": "North",
    "Jezzine": "South", "Sidon": "South", "Tyre": "South",
    "Bint Jbeil": "Nabatieh", "Hasbaya": "Nabatieh", "Marjeyoun": "Nabatieh",
    "Nabatieh": "Nabatieh",
    "Rashaya": "Beqaa", "Western Beqaa": "Beqaa", "Zahlé": "Beqaa",
    "Baalbek": "Baalbek-Hermel", "Hermel": "Baalbek-Hermel",
    "Akkar": "Akkar",
}

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
}


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def fix_mojibake(text: str) -> str:
    """The file is UTF-8 encoded twice ('Zahlé' arrives as 'ZahlÃ©')."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def area_name(uri: str) -> str:
    """Turn a DBpedia URI such as .../Zahl%C3%A9_District into 'Zahlé'."""
    name = fix_mojibake(str(uri).rstrip("/").split("/")[-1])
    name = name.replace("Tripoli_District,_Lebanon", "Tripoli_District").replace("_", " ")
    for suffix in (" Governorate", " District"):
        name = name.removesuffix(suffix)
    return name.strip()


@st.cache_data
def load_data(path: Path = DATA_FILE) -> pd.DataFrame:
    """Read and clean the CODEC tourism file: one row per town."""
    raw = pd.read_csv(path, encoding="utf-8")

    town = raw["Town"].astype(str).str.strip().map(fix_mojibake)
    town = town.str[0].str.upper() + town.str[1:]  # 9 names start in lower case ('yahchouch')
    df = pd.DataFrame({"Town": town})
    area = raw["refArea"].map(area_name)
    has_district = raw["refArea"].str.contains("_District", regex=False)
    df["District"] = area.where(has_district, "not recorded")
    df["Governorate"] = area.map(DISTRICT_TO_GOVERNORATE).fillna(area)

    for source, name in SOURCE_COLUMNS.items():
        df[name] = pd.to_numeric(raw[source], errors="coerce").fillna(0).astype(int)
    df["Tourism Index"] = pd.to_numeric(raw["Tourism Index"], errors="coerce").fillna(0).astype(int)
    df["Venues"] = df[VENUES].sum(axis=1)
    return df


def governorate_table(df: pd.DataFrame) -> pd.DataFrame:
    """Venue totals per governorate, largest first."""
    table = df.groupby("Governorate").agg(
        Towns=("Town", "size"),
        **{v: (v, "sum") for v in VENUES},
        Venues=("Venues", "sum"),
    )
    table["Venues per town"] = table["Venues"] / table["Towns"]
    return table.sort_values("Venues", ascending=False)


def top_share(frame: pd.DataFrame, n: int = 10) -> float:
    """Share of the venues in `frame` held by its n best-supplied towns."""
    total = frame["Venues"].sum()
    return frame["Venues"].nlargest(n).sum() / total if total else 0.0


def pct(x: float) -> str:
    return f"{x:.0%}"


def count(n: int, word: str, plural: str | None = None) -> str:
    """'1 hotel', '3 hotels', '1 guest house', '0 cafés'."""
    return f"{n} {word if n == 1 else (plural or word + 's')}"


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def base_layout(fig: go.Figure, height: int, left: int = 60) -> None:
    # Margins and automargin are set explicitly: inside Streamlit, Plotly's
    # default template only partly reaches the browser, and without these the
    # axis labels were cut off.
    fig.update_layout(
        height=height,
        margin=dict(l=left, r=16, t=40, b=56),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=14, color=INK),
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                    title_text="", font=dict(size=13), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="white", bordercolor=AXIS, font=dict(family=FONT, size=13, color=INK)),
    )


def bar_chart(frame: pd.DataFrame, labels: list[str], highlight: str | None,
              hover_extra: str, customdata: list[list], height: int) -> go.Figure:
    """Grouped horizontal bars: one group per row of `frame`, one bar per venue type."""
    fig = go.Figure()
    opacity = [1.0 if (highlight is None or lab == highlight) else 0.28 for lab in labels]
    for venue in VENUES:
        fig.add_bar(
            y=labels,
            x=frame[venue],
            name=venue,
            orientation="h",
            marker=dict(color=VENUE_COLORS[venue], opacity=opacity),
            customdata=customdata,
            hovertemplate=f"<b>%{{y}}</b><br>{venue}: <b>%{{x:,}}</b>{hover_extra}<extra></extra>",
        )
    base_layout(fig, height, left=120)
    # The legend sits inside the plot, bottom right: rows are sorted largest
    # first, so that corner is always empty, and long town names can't push it
    # onto two lines.
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.06, margin_t=12,
                      legend=dict(orientation="v", x=0.99, xanchor="right", y=0.02, yanchor="bottom",
                                  bgcolor="rgba(255,255,255,0.9)"))
    fig.update_xaxes(title_text="Number of venues", gridcolor=GRID, zeroline=False, automargin=True,
                     showline=True, linecolor=AXIS, tickformat=",", title_font=dict(size=13, color=MUTED))
    fig.update_yaxes(autorange="reversed", showgrid=False, ticks="", ticklabelstandoff=6, automargin=True)
    return fig


def scatter_chart(df: pd.DataFrame, gov: str, town_id: int | None) -> go.Figure:
    """Restaurants vs cafés, one dot per town, with the selection in focus."""
    in_scope = df["Governorate"].eq(gov) if gov != ALL else pd.Series(True, index=df.index)
    hover = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
             "Restaurants: %{x} · Cafés: %{y}<br>"
             "Hotels: %{customdata[2]} · Guest houses: %{customdata[3]}<br>"
             "Tourism Index %{customdata[4]}/10<extra></extra>")
    cols = ["Town", "Governorate", "Hotels", "Guest houses", "Tourism Index"]

    fig = go.Figure()
    # Reference diagonal: as many cafés as restaurants.
    fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", hoverinfo="skip",
                             showlegend=False, line=dict(color=AXIS, width=1.2)))

    if gov != ALL:  # the rest of Lebanon stays on screen, in grey, as context
        rest = df[~in_scope]
        fig.add_trace(go.Scatter(
            x=rest["Restaurants"], y=rest["Cafés"], mode="markers", name="Other towns",
            marker=dict(size=8, color=CONTEXT, opacity=0.55, line=dict(color="white", width=1)),
            customdata=rest[cols].to_numpy(), hovertemplate=hover))

    focus = df[in_scope]
    fig.add_trace(go.Scatter(
        x=focus["Restaurants"], y=focus["Cafés"], mode="markers",
        name=f"Towns in {gov}" if gov != ALL else "Towns",
        marker=dict(size=9, color=FOCUS, opacity=0.7, line=dict(color="white", width=1)),
        customdata=focus[cols].to_numpy(), hovertemplate=hover))

    # How many dots are hiding under the point (0, 0)?
    empty = int(((focus["Restaurants"] == 0) & (focus["Cafés"] == 0)).sum())
    where = "" if gov == ALL else f" in {gov}"
    # The label sits in the empty upper-left area (in data units) so it never
    # covers the diagonal or the dense cluster; its line points at the origin.
    fig.add_annotation(
        x=0, y=0, axref="x", ayref="y", ax=5, ay=56,
        text=f"<b>{empty:,} towns{where}</b><br>sit at 0, 0: no restaurant<br>and no café",
        showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=MUTED, align="left",
        font=dict(size=12.5, color=INK), bgcolor="rgba(255,255,255,0.9)", borderpad=3,
        xanchor="left", yanchor="bottom")

    # Region labels explain the diagonal without a legend entry.
    fig.add_annotation(x=3, y=101, text="More cafés than restaurants ↑", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(size=12, color=MUTED))
    fig.add_annotation(x=101, y=3, text="More restaurants than cafés →", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(size=12, color=MUTED))

    if town_id is not None:
        t = df.loc[town_id]
        fig.add_trace(go.Scatter(
            x=[t["Restaurants"]], y=[t["Cafés"]], mode="markers", name=t["Town"],
            marker=dict(size=17, color=HIGHLIGHT, line=dict(color="white", width=2.5)),
            customdata=[t[cols].to_list()], hovertemplate=hover))
        # Put the label on the side of the dot that has room.
        ax = -70 if t["Restaurants"] > 55 else 70
        ay = 60 if t["Cafés"] > 70 else -60
        if t["Restaurants"] < 15 and t["Cafés"] < 15:  # inside the dense cluster: step clear of it
            ax, ay = 115, -45
        fig.add_annotation(
            x=t["Restaurants"], y=t["Cafés"], ax=ax, ay=ay,
            text=f"<b>{t['Town']}</b><br>{count(t['Restaurants'], 'restaurant')} · {count(t['Cafés'], 'café')}",
            showarrow=True, arrowhead=0, arrowwidth=1.2, arrowcolor=HIGHLIGHT,
            font=dict(size=13, color=INK), bgcolor="rgba(255,255,255,0.95)",
            bordercolor=HIGHLIGHT, borderwidth=1, borderpad=4)

    base_layout(fig, 540)
    fig.update_layout(hovermode="closest", hoverdistance=24, showlegend=gov != ALL)
    axis = dict(range=[-4, 106], dtick=20, gridcolor=GRID, zeroline=False, showline=True,
                linecolor=AXIS, automargin=True, title_font=dict(size=13, color=MUTED))
    fig.update_xaxes(title_text="Restaurants in the town", **axis)
    fig.update_yaxes(title_text="Cafés in the town", scaleanchor="x", scaleratio=1, **axis)
    return fig


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
st.set_page_config(page_title="Lebanon's tourism supply", page_icon="🏨", layout="wide")

df = load_data()
govs = governorate_table(df)
N_TOWNS = len(df)
TOTAL = int(df["Venues"].sum())
NAT_PER_TOWN = TOTAL / N_TOWNS
food_share = (df["Restaurants"].sum() + df["Cafés"].sum()) / TOTAL
empty_towns = int((df["Venues"] == 0).sum())
neither = int(((df["Restaurants"] == 0) & (df["Cafés"] == 0)).sum())
r_value = df["Restaurants"].corr(df["Cafés"])
hotel_towns = int((df["Hotels"] > 0).sum())

# Numbers quoted in the two headline insights, computed from the data.
top_gov = govs.index[0]
best_avg = govs["Venues per town"].idxmax()
best_avg_rows = df[df["Governorate"] == best_avg]
cafe_heavy = govs[govs["Cafés"] > govs["Restaurants"]].sort_values("Cafés", ascending=False)
akkar_cafes, akkar_restaurants = (int(govs.at["Akkar", c]) for c in ("Cafés", "Restaurants"))

st.title("Lebanon's tourism supply: a few hubs, many empty towns")
st.caption(f"Hotels, restaurants, cafés and guest houses in {N_TOWNS:,} Lebanese towns · "
           f"MSBA 325 Streamlit activity · {AUTHOR}")

st.markdown(
    f"""
Each town in this dataset reports how many **restaurants, cafés, hotels and guest houses** it has,
plus a 0–10 **Tourism Index**. The data come from IMPACT Open Data (Lebanon's Central Inspection) through
AUB's CODEC portal: {N_TOWNS:,} towns in seven governorates, {TOTAL:,} venues in all. Food and drink make up
**{food_share:.0%}** of them; only {hotel_towns} towns have a hotel. Beirut is not in this extract.
"""
)

# ---- Two headline insights --------------------------------------------------
i1, i2 = st.columns(2, gap="medium")
with i1.container(border=True):
    st.markdown("**① Totals and averages tell different stories**")
    st.markdown(
        f"{top_gov} has the most venues ({govs.loc[top_gov, 'Venues']:,}, "
        f"{govs.loc[top_gov, 'Venues'] / TOTAL:.0%} of the total), mostly because it has the most towns "
        f"({govs.loc[top_gov, 'Towns']}). Per town, **{best_avg} leads** "
        f"({govs.loc[best_avg, 'Venues per town']:.1f} vs {govs.loc[top_gov, 'Venues per town']:.1f}). "
        f"Drill into {best_avg} and that average breaks down: its top 10 towns hold "
        f"**{pct(top_share(best_avg_rows))}** of its venues, and "
        f"**{pct((best_avg_rows['Venues'] == 0).mean())}** of its towns have none."
    )
with i2.container(border=True):
    st.markdown("**② Restaurants and cafés come together, or not at all**")
    st.markdown(
        f"Across towns the two rise together (r = {r_value:.2f}), yet **{neither} of {N_TOWNS:,} towns "
        f"({neither / N_TOWNS:.0%}) have neither**. Only "
        f"{' and '.join('the South' if g == 'South' else g for g in cafe_heavy.index)} have more cafés "
        f"than restaurants. In Akkar the gap is wide: **{akkar_cafes} cafés against "
        f"{akkar_restaurants} restaurants**."
    )

st.space("small")

# ---- The two linked interaction features ---------------------------------------
def reset_town() -> None:
    """A new governorate means a new list of towns, so clear the old town."""
    st.session_state["town"] = None


with st.container(border=True):
    st.markdown("**Drill down:** choose a governorate, then a town inside it. "
                "Both charts and the numbers below follow your choice.")
    gov = st.segmented_control(
        "① Governorate",
        options=[ALL, *govs.index],
        default=ALL,
        required=True,
        key="gov",
        on_change=reset_town,
        help="Ordered like the bars: most venues first.",
    )

    if gov == ALL:
        town_options: list[int] = []
        town_label = "② Town (pick a governorate first)"
        placeholder = "Choose a governorate above to unlock its towns"
    else:
        in_gov = df[df["Governorate"] == gov].sort_values(["Venues", "Town"], ascending=[False, True])
        town_options = in_gov.index.tolist()
        town_label = f"② Town in {gov}"
        placeholder = f"Search {len(town_options)} towns in {gov} (most venues first)…"

    town_id = st.selectbox(
        town_label,
        options=town_options,
        index=None,
        format_func=lambda i: f"{df.at[i, 'Town']}  ·  {count(int(df.at[i, 'Venues']), 'venue')}",
        placeholder=placeholder,
        key="town",
        disabled=gov == ALL,
        width=520,
        help="The list only contains towns of the governorate chosen above.",
    )

# ---- Numbers for the current selection -------------------------------------------
scope = df if gov == ALL else df[df["Governorate"] == gov]
scope_venues = int(scope["Venues"].sum())
scope_per_town = scope_venues / len(scope)
scope_empty = int((scope["Venues"] == 0).sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Tourism venues", f"{scope_venues:,}",
          delta=None if gov == ALL else f"{scope_venues / TOTAL:.0%} of Lebanon's total",
          delta_color="off", delta_arrow="off", border=True)
k2.metric("Venues per town", f"{scope_per_town:.1f}",
          delta=None if gov == ALL else f"{scope_per_town - NAT_PER_TOWN:+.1f} vs Lebanon ({NAT_PER_TOWN:.1f})",
          delta_color="off", border=True)
k3.metric("Towns with no venue", f"{scope_empty:,}",
          delta=f"{scope_empty / len(scope):.0%} of {len(scope):,} towns",
          delta_color="off", delta_arrow="off", border=True)
k4.metric("Held by the top 10 towns", pct(top_share(scope)),
          delta="of all venues in this selection",
          delta_color="off", delta_arrow="off", border=True,
          help="How concentrated the supply is: the share of venues found in the 10 best-supplied towns.")

if town_id is not None:
    t = df.loc[town_id]
    district = "" if t["District"] == "not recorded" else f", {t['District']} district"
    if t["Venues"] == 0:
        profile = (f"**{t['Town']}** ({gov}{district}) has **no tourism venues** recorded, like "
                   f"{scope_empty - 1} other towns in {gov}.")
    else:
        rank = int(scope["Venues"].rank(ascending=False, method="min").loc[town_id])
        tied = int((scope["Venues"] == t["Venues"]).sum()) > 1
        profile = (f"**{t['Town']}** ({gov}{district}) has **{count(t['Venues'], 'venue')}**: "
                   f"{count(t['Restaurants'], 'restaurant')}, {count(t['Cafés'], 'café')}, "
                   f"{count(t['Hotels'], 'hotel')} and {count(t['Guest houses'], 'guest house')}. "
                   f"That ranks {'tied ' if tied else ''}**#{rank} of {len(scope)}** towns in {gov}.")
    st.info(f"{profile} Tourism Index: {t['Tourism Index']}/10.", icon=":material/location_on:")

# ---- The two related visualisations -----------------------------------------------
left, right = st.columns(2, gap="large")

with left:
    if gov == ALL:
        st.markdown("#### Where the venues are: seven governorates")
        st.caption("Venues by type, most venues first. Hover a bar for the number per town.")
        frame = govs
        labels = frame.index.tolist()
        custom = [[towns, per] for towns, per in zip(frame["Towns"], frame["Venues per town"])]
        fig = bar_chart(frame, labels, None,
                        "<br>%{customdata[0]} towns · %{customdata[1]:.1f} venues per town", custom, 540)
        table = frame.assign(**{"Venues per town": frame["Venues per town"].round(1)})
    else:
        ranked = scope.assign(Rank=scope["Venues"].rank(ascending=False, method="min").astype(int))
        frame = ranked.sort_values(["Venues", "Town"], ascending=[False, True]).head(10)
        if town_id is not None and town_id not in frame.index:
            frame = pd.concat([frame, ranked.loc[[town_id]]])  # keep the chosen town visible
        labels = [f"{r}. {name}" for r, name in zip(frame["Rank"], frame["Town"])]
        highlight = None
        if town_id is not None:
            highlight = labels[frame.index.get_loc(town_id)]
            labels = [f"<b>{lab}</b>" if lab == highlight else lab for lab in labels]
            highlight = f"<b>{highlight}</b>"
        st.markdown(f"#### Inside {gov}: top 10 towns by venues")
        st.caption(f"These 10 of {len(scope)} towns hold {pct(top_share(scope))} of its {scope_venues:,} venues.")
        custom = [[v, ti] for v, ti in zip(frame["Venues"], frame["Tourism Index"])]
        fig = bar_chart(frame, labels, highlight,
                        "<br>Total venues: %{customdata[0]} · Tourism Index %{customdata[1]}/10", custom, 540)
        if town_id is not None and df.at[town_id, "Venues"] == 0:
            fig.add_annotation(x=0, y=highlight, text="  no venues recorded", showarrow=False,
                               xanchor="left", font=dict(size=12.5, color=MUTED))
        table = frame.set_index("Town")[["Rank", *VENUES, "Venues", "Tourism Index"]]
    st.plotly_chart(fig, theme=None, config=PLOTLY_CONFIG, key="bars")
    with st.expander("See the numbers behind this chart"):
        st.dataframe(table, width="stretch")

with right:
    st.markdown("#### Do restaurants and cafés go together?")
    if gov == ALL:
        st.caption("One dot per town. Dots above the diagonal have more cafés than restaurants.")
    else:
        st.caption(f"Violet: {gov}'s {len(scope)} towns. Grey: the rest of Lebanon, for context.")
    st.plotly_chart(scatter_chart(df, gov, town_id), theme=None, config=PLOTLY_CONFIG, key="scatter")
    with st.expander("See the numbers behind this chart"):
        st.dataframe(
            scope.sort_values("Venues", ascending=False)
                 .set_index("Town")[["Governorate", "District", *VENUES, "Venues", "Tourism Index"]],
            width="stretch", height=300)

# ---- What the current selection shows -------------------------------------------
if gov != ALL:
    cafes, restaurants = int(scope["Cafés"].sum()), int(scope["Restaurants"].sum())
    mix = "cafés outnumber restaurants" if cafes > restaurants else "restaurants outnumber cafés"
    st.markdown(
        f"**What {gov} shows:** {scope_venues:,} venues across {len(scope)} towns, "
        f"{scope_per_town:.1f} per town against {NAT_PER_TOWN:.1f} nationally. "
        f"The top 10 towns hold {pct(top_share(scope))} of them and {scope_empty} towns "
        f"({scope_empty / len(scope):.0%}) have none. Here {mix} "
        f"({cafes:,} cafés, {restaurants:,} restaurants)."
    )

# ---- Design justification (one per interaction feature) -------------------------
st.divider()
st.subheader("Why the page works this way")

with st.expander("Feature ① · Governorate control: why a row of buttons?", icon=":material/touch_app:"):
    st.markdown(
        """
**Question it helps answer.** *Which part of the country am I looking at, and how does it compare with
the rest of Lebanon?*

**Why this widget.** There are only eight choices (all of Lebanon plus seven governorates), so they are
all shown as one row of buttons. The reader sees how the country is divided before clicking, and one
click changes region. The buttons are in the same order as the bars (most venues first). I considered a
**dropdown**, but it hides the choices behind an extra click. I also considered a **multiselect** and
rejected it. With several governorates selected, the town list would mix regions and the bar chart would
have no single governorate to open up, so the drill-down would stop working.

**Course concepts.** *Overview first, then zoom and filter* (Shneiderman's mantra), plus *providing
context* and *focusing attention* (Knaflic, *Storytelling with Data*). *All of Lebanon* is the overview.
Choosing a governorate zooms both charts. The bar chart redraws that governorate's own towns, and the
scatter colours its towns violet while every other town stays **grey as context**. The axes never
rescale, so the reader can compare regions honestly. The single strong colour **focuses attention**.
It is the same violet as the selected button, so the control and the dots it controls are visibly
linked (the Gestalt principle of similarity).
"""
    )

with st.expander("Feature ② · Town search box: why a searchable dropdown?", icon=":material/search:"):
    st.markdown(
        """
**Question it helps answer.** *Is this particular town a hub or one of the empty towns, and how does it
compare with the rest of its governorate?*

**Why this widget.** A governorate has between 74 and 378 towns, far too many for buttons or radio
options. A dropdown you can type into finds any town in a few keystrokes. Towns are listed **most
venues first**, with their count, so the hubs sit at the top. I considered **clicking a dot on the
scatter** instead, but 528 towns sit on top of each other at (0, 0), so most towns could never be
clicked. A free-text box would fail silently on a typo.

**How it is linked to feature ①.** Its options come from the governorate control. It stays locked until
a governorate is chosen, then lists only that governorate's towns, and it clears itself when the
governorate changes. The reader therefore always drills down in one direction: Lebanon, then a
governorate, then a town.

**Course concepts.** *Details on demand* (the last step of Shneiderman's mantra), plus *reducing
clutter* and *focusing attention* (Knaflic). The charts never label 1,137 towns. They label only the one
the reader asks for. That town becomes the only black, labelled dot in the scatter and the only
full-colour group of bars (a town outside the top 10 is added with its rank), while everything else
fades. The page stays uncluttered, and attention goes to the town in question.
"""
    )

with st.expander("About the data and how it was cleaned", icon=":material/dataset:"):
    st.markdown(
        f"""
- **Source.** *Tourism* dataset, published by IMPACT Open Data (impact.cib.gov.lb) and served by AUB's CODEC
  linked-data platform (linked.aub.edu.lb). One row per town: counts of hotels, restaurants, cafés and guest
  houses, a 0–10 Tourism Index, and yes/no flags (the flags are not used here).
- **Mixed administrative levels.** The area column names a *district* for 689 towns but only a *governorate*
  for 448. Districts were mapped up to their governorate so the seven totals are complete and do not overlap.
  The same gap is why the page drills down by town rather than by district: 39% of towns have no district.
- **Broken characters.** Names such as Zahlé and Miniyeh–Danniyeh were double-encoded and have been repaired,
  and nine town names that started with a lower-case letter were capitalised.
- **Limits.** Beirut is missing. Large counts are often round numbers (50, 90, 100), so they are likely
  reported estimates rather than exact counts.
"""
    )

st.caption(f"Built with Streamlit and Plotly by {AUTHOR} · MSBA 325, American University of Beirut · "
           "Data: IMPACT Open Data via CODEC (linked.aub.edu.lb)")
