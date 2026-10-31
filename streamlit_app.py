from pathlib import Path
import unicodedata
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="LMB Scouting Intelligence", page_icon="⚾", layout="wide")
ROOT = Path(__file__).parent
YEARS = [2024, 2025, 2026]
SOURCES = {
    2024: "https://www.baseball-reference.com/register/league.cgi?id=83fa0ab3",
    2025: "https://www.baseball-reference.com/register/league.cgi?id=b5ba4b13",
    2026: "https://www.baseball-reference.com/register/league.cgi?id=f6efe3f3",
}
HITTING_FIELDS = ["player", "season", "team", "g", "pa", "ab", "r", "h",
                  "doubles", "triples", "hr", "rbi", "bb", "so", "sb", "cs",
                  "avg", "obp", "slg", "ops"]
PITCHING_FIELDS = ["pitcher", "season", "team", "g", "gs", "ip_baseball",
                   "h", "er", "hr", "bb", "k", "bf"]
BAT_METRICS = {"OPS": "ops", "OBP": "obp", "SLG": "slg", "AVG": "avg",
               "ISO": "iso", "HR": "hr", "RBI": "rbi", "SB": "sb",
               "BB%": "bb_pct", "K%": "k_pct", "BB/K": "bb_k"}
ARM_METRICS = {"ERA": "era", "WHIP": "whip", "K%": "k_pct", "BB%": "bb_pct",
               "K-BB%": "kbb_pct", "K/9": "k9", "BB/9": "bb9", "HR/9": "hr9"}
st.markdown("""<style>
.block-container {padding-top:1.0rem;max-width:1180px}
h1 {font-size:clamp(1.7rem,4vw,2.6rem)!important;line-height:1.14!important}
h2 {font-size:1.42rem!important}
[data-testid="stMetric"] {background:#14263A;padding:12px;border-radius:12px;border:1px solid #263F55}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px}
</style>""", unsafe_allow_html=True)

def norm(value):
    raw = unicodedata.normalize("NFKD", str(value).casefold().strip())
    return "".join(c for c in raw if not unicodedata.combining(c))

def innings(value):
    s = str(value).strip()
    part = s.split(".")
    if len(part) not in (1, 2) or (len(part) == 2 and part[1] not in ("0", "1", "2")):
        raise ValueError("Use baseball innings notation, e.g. 10.2 = 10 and two-thirds innings.")
    return int(part[0]) + (int(part[1]) if len(part) == 2 else 0) / 3

def safe_csv(frame):
    copy = frame.copy()
    for col in copy.select_dtypes(include="object").columns:
        copy[col] = copy[col].map(lambda x: ("'" + x) if isinstance(x, str) and x.startswith(("=", "+", "-", "@")) else x)
    return copy.to_csv(index=False).encode("utf-8-sig")

def download(frame, name, label="Download filtered CSV"):
    st.download_button(label, safe_csv(frame), name, mime="text/csv")

def parse_hitters(frame):
    df = frame.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = set(HITTING_FIELDS) - set(df.columns)
    if missing:
        raise ValueError("Hitter CSV missing: " + ", ".join(sorted(missing)))
    if "league" in df.columns:
        if not df.league.astype(str).str.upper().eq("LMB").all():
            raise ValueError("This database accepts only LMB records.")
    df["season"] = pd.to_numeric(df.season, errors="raise").astype(int)
    if not df.season.isin(YEARS).all():
        raise ValueError("Only 2024, 2025 and 2026 records are supported.")
    for c in HITTING_FIELDS[3:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("g", "ab", "h", "doubles", "triples", "hr", "rbi", "bb", "so", "sb", "cs", "avg", "obp", "slg", "ops"):
        if df[c].isna().any():
            raise ValueError("Hitter file has invalid or missing " + c)
    if (df[["ab", "h", "hr", "bb", "so"]] < 0).any().any() or (df.h > df.ab).any() or (df.ab <= 0).any():
        raise ValueError("Invalid batting totals.")
    if ((df.pa.notna()) & (df.pa < df.ab)).any():
        raise ValueError("Plate appearances cannot be lower than at-bats.")
    df["league"] = "LMB"
    df["key"] = df.player.map(norm)
    df["iso"] = df.slg - df.avg
    df["xbh"] = df.doubles + df.triples + df.hr
    df["bb_pct"] = (100 * df.bb / df.pa).where(df.pa > 0)
    df["k_pct"] = (100 * df.so / df.pa).where(df.pa > 0)
    df["bb_k"] = (df.bb / df.so).where(df.so > 0)
    df["record"] = df.player + " • " + df.season.astype(str) + " • " + df.team
    return df

def parse_pitchers(frame):
    df = frame.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    missing = set(PITCHING_FIELDS) - set(df.columns)
    if missing:
        raise ValueError("Pitcher CSV missing: " + ", ".join(sorted(missing)))
    if "league" in df.columns:
        if not df.league.astype(str).str.upper().eq("LMB").all():
            raise ValueError("This database accepts only LMB records.")
    df["season"] = pd.to_numeric(df.season, errors="raise").astype(int)
    if not df.season.isin(YEARS).all():
        raise ValueError("Only 2024, 2025 and 2026 records are supported.")
    df["ip"] = df.ip_baseball.map(innings)
    for c in ("g", "gs", "h", "er", "hr", "bb", "k", "bf"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    if (df.ip <= 0).any() or (df.bf <= 0).any() or (df[["g", "gs", "h", "er", "hr", "bb", "k", "bf"]] < 0).any().any():
        raise ValueError("Invalid pitching totals.")
    df["league"] = "LMB"
    df["key"] = df.pitcher.map(norm)
    df["era"] = 9 * df.er / df.ip
    df["whip"] = (df.h + df.bb) / df.ip
    df["k9"] = 9 * df.k / df.ip
    df["bb9"] = 9 * df.bb / df.ip
    df["hr9"] = 9 * df.hr / df.ip
    df["k_pct"] = 100 * df.k / df.bf
    df["bb_pct"] = 100 * df.bb / df.bf
    df["kbb_pct"] = df.k_pct - df.bb_pct
    df["record"] = df.pitcher + " • " + df.season.astype(str) + " • " + df.team
    return df

@st.cache_data
def built_in():
    hit = parse_hitters(pd.read_csv(ROOT / "data/lmb_hitters_2024_2026_sample.csv"))
    old = pd.read_csv(ROOT / "data/lmb_pitchers_2024_2025_sample.csv", dtype={"ip_baseball":str})
    old["league"] = "LMB"
    curr = pd.read_csv(ROOT / "data/lmb_pitchers_2026_sample.csv", dtype={"ip_baseball":str})
    curr = curr[curr.league.eq("LMB")].copy()
    return hit, parse_pitchers(pd.concat([old, curr], ignore_index=True))

hitters, pitchers = built_in()
with st.sidebar:
    st.markdown("### ⚾ LMB Scout Lab")
    st.caption("Free · No trial · Selected verified player-season records")
    st.markdown("**2024 | 2025 | 2026**")
    file_type = st.radio("Import data for", ["Hitters", "Pitchers"], horizontal=True)
    extra = st.file_uploader("Add LMB season CSV", type=["csv"], key="extra")
    if extra:
        try:
            new = parse_hitters(pd.read_csv(extra)) if file_type == "Hitters" else parse_pitchers(pd.read_csv(extra, dtype={"ip_baseball":str}))
            if file_type == "Hitters":
                hitters = pd.concat([hitters, new], ignore_index=True).drop_duplicates(["key", "season", "team"], keep="last")
            else:
                pitchers = pd.concat([pitchers, new], ignore_index=True).drop_duplicates(["key", "season", "team"], keep="last")
            st.success(f"Loaded {len(new)} LMB record(s) for this session.")
        except Exception as e:
            st.error(f"CSV import failed: {e}")
    st.caption("Uploads are temporary. Download your results before leaving.")
    st.download_button("Download starter hitters CSV", (ROOT / "data/lmb_hitters_2024_2026_sample.csv").read_bytes(),
                       "lmb_hitters_2024_2026_sample.csv", mime="text/csv")
    st.download_button("Download pitcher sample CSV", safe_csv(pitchers[PITCHING_FIELDS]),
                       "lmb_pitchers_2024_2026_sample.csv", mime="text/csv")

st.title("⚾ LMB Scouting Intelligence")
st.caption("Liga Mexicana de Béisbol • 2024–2026 • Hitters + Pitchers • Historical sample, not a live or complete roster database")
mode = st.selectbox("Choose workspace", ["📍 Overview", "🏏 Hitter Finder", "⚾ Pitcher Finder",
    "⚔️ Head-to-Head", "📈 Three-Year Trends", "🎯 Scout Rankings",
    "🧪 Pitch Tracking", "📝 Scout Notes", "ℹ️ Sources & Limits"], label_visibility="collapsed")
yrs = st.multiselect("Seasons", YEARS, default=YEARS)
if not yrs:
    st.info("Select at least one season.")
    st.stop()
H = hitters[hitters.season.isin(yrs)].copy()
P = pitchers[pitchers.season.isin(yrs)].copy()

if mode == "📍 Overview":
    st.subheader("At a glance")
    a,b,c,d = st.columns(4)
    a.metric("Hitter-seasons", len(H))
    b.metric("Pitcher-seasons", len(P))
    c.metric("Unique hitters", H.key.nunique())
    d.metric("Unique pitchers", P.key.nunique())
    st.info("2024–2026 LMB ONLY. Built-in datasets are selected player-season records, not full league leaderboards.")
    choice = st.radio("Explore", ["Hitters", "Pitchers"], horizontal=True)
    frame = H if choice == "Hitters" else P
    metric = "ops" if choice == "Hitters" else "kbb_pct"
    if not frame.empty:
        fig = px.strip(frame, x="season", y=metric, color="season",
            hover_name="player" if choice == "Hitters" else "pitcher",
            hover_data=["team", "ab" if choice == "Hitters" else "ip"],
            title=("OPS across sampled hitters" if choice == "Hitters" else "K-BB% across sampled pitchers"))
        st.plotly_chart(fig, use_container_width=True)
    st.caption("Charts show the selected sample; changing the mix of players affects the distributions.")
    st.subheader("Built-in season coverage")
    cover = pd.DataFrame({"Season": YEARS,
       "Hitting records": [int((hitters.season == y).sum()) for y in YEARS],
       "Pitching records": [int((pitchers.season == y).sum()) for y in YEARS]})
    st.dataframe(cover, hide_index=True, use_container_width=True)

elif mode == "🏏 Hitter Finder":
    st.subheader("Hitter finder")
    text = st.text_input("Player / team search", key="battersearch")
    min_ab = st.slider("Minimum at-bats", 0, 450, 100, 10)
    view = H[H.ab >= min_ab]
    if text:
        view = view[view.player.str.contains(text, case=False, regex=False) |
                    view.team.str.contains(text, case=False, regex=False)]
    metric = st.selectbox("Sort by", list(BAT_METRICS))
    display = view.sort_values(BAT_METRICS[metric], ascending=(metric == "K%"), na_position="last")
    cols = ["player", "season", "team", "pa", "ab", "avg", "obp", "slg", "ops",
            "hr", "rbi", "sb", "bb", "so", "iso", "bb_pct", "k_pct"]
    st.caption("Rates BB%/K% require PA; missing 2024 PA values are left blank, never invented.")
    st.dataframe(display[cols], hide_index=True, use_container_width=True)
    download(display[cols], "lmb_hitter_search.csv", "⬇ Export selected hitters")
    if len(view):
        graphic = display.head(18).iloc[::-1]
        fig = px.bar(graphic, x=BAT_METRICS[metric], y="player", color="season", orientation="h",
                     hover_data=["team", "ab"], title=f"Top available hitter records by {metric}")
        st.plotly_chart(fig, use_container_width=True)

elif mode == "⚾ Pitcher Finder":
    st.subheader("Pitcher finder")
    text = st.text_input("Pitcher / team search", key="pitchsearch")
    min_ip = st.slider("Minimum innings", 0, 130, 25, 5)
    view = P[P.ip >= min_ip]
    if text:
        view = view[view.pitcher.str.contains(text, case=False, regex=False) |
                    view.team.str.contains(text, case=False, regex=False)]
    metric = st.selectbox("Sort by", list(ARM_METRICS))
    low = metric in ("ERA", "WHIP", "BB%", "BB/9", "HR/9")
    display = view.sort_values(ARM_METRICS[metric], ascending=low)
    cols = ["pitcher", "season", "team", "g", "gs", "ip", "era", "whip",
            "k9", "bb9", "k_pct", "bb_pct", "kbb_pct", "hr9"]
    st.dataframe(display[cols], hide_index=True, use_container_width=True)
    download(display[cols], "lmb_pitcher_search.csv", "⬇ Export selected pitchers")
    if len(view):
        graphic = display.head(18).iloc[::-1]
        st.plotly_chart(px.bar(graphic, x=ARM_METRICS[metric], y="pitcher",
            color="season", orientation="h", title=f"Available pitcher records by {metric}"), use_container_width=True)

elif mode == "⚔️ Head-to-Head":
    st.subheader("Compare two LMB player-seasons")
    category = st.radio("Position group", ["Hitters", "Pitchers"], horizontal=True)
    view = H if category == "Hitters" else P
    metrics = BAT_METRICS if category == "Hitters" else ARM_METRICS
    if len(view) < 2:
        st.warning("Select enough seasons to have two player records.")
    else:
        opts = sorted(view.record.unique())
        a,b = st.columns(2)
        first = a.selectbox("Player A", opts, index=0)
        second = b.selectbox("Player B", opts, index=min(1,len(opts)-1))
        choice = st.multiselect("Compare metrics", list(metrics),
            default=(["OPS", "OBP", "SLG"] if category == "Hitters" else ["K%", "BB%", "K-BB%"]))
        selected = view[view.record.isin([first, second])].drop_duplicates("record")
        if choice:
            graphic = selected.melt(id_vars=["record", "season"], value_vars=[metrics[m] for m in choice],
                                    var_name="Metric", value_name="Value")
            st.plotly_chart(px.bar(graphic, x="Metric", y="Value", color="record",
                barmode="group", text_auto=".2f"), use_container_width=True)
        st.dataframe(selected[["record", "season", "team"] + [metrics[m] for m in choice]],
                     hide_index=True, use_container_width=True)
        st.caption("Descriptive statistics only: no park, opposition, or league run-environment adjustment.")

elif mode == "📈 Three-Year Trends":
    st.subheader("Player development: 2024 → 2026")
    category = st.radio("Player type", ["Hitters", "Pitchers"], horizontal=True)
    all_view = hitters if category == "Hitters" else pitchers
    label = "player" if category == "Hitters" else "pitcher"
    metrics = BAT_METRICS if category == "Hitters" else ARM_METRICS
    multi = all_view.groupby("key").season.nunique()
    choices = all_view[all_view.key.isin(multi[multi >= 2].index)]
    if choices.empty:
        st.info("No multi-season players in the built-in sample. Import additional years to expand this view.")
    else:
        who = st.selectbox("Player", sorted(choices[label].unique()))
        metric = st.selectbox("Development metric", list(metrics), index=0)
        chosen = all_view[all_view.key.eq(norm(who))].sort_values("season")
        fig = px.line(chosen, x="season", y=metrics[metric], markers=True,
                      hover_data=["team"], title=f"{who} — {metric}")
        fig.update_xaxes(tickmode="array", tickvals=YEARS)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(chosen[["season", "team", label] +
            (["pa", "ab", "avg", "obp", "slg", "ops", "hr"] if category == "Hitters" else
             ["ip", "era", "whip", "k9", "bb9", "kbb_pct"])],
             hide_index=True, use_container_width=True)
        st.caption("Gaps mean no record in this sample, not that the player did not play in the LMB.")

elif mode == "🎯 Scout Rankings":
    st.subheader("Adjustable scouting screening index")
    category = st.radio("Evaluate", ["Hitters", "Pitchers"], horizontal=True)
    frame = H.copy() if category == "Hitters" else P.copy()
    opts = (["OPS", "ISO", "BB/K", "K%"] if category == "Hitters" else
            ["K-BB%", "K%", "WHIP", "BB%"])
    label = "player" if category == "Hitters" else "pitcher"
    metricmap = BAT_METRICS if category == "Hitters" else ARM_METRICS
    a,b,c,d = st.columns(4)
    weights = [s.slider(f"{metric} weight", 0, 100, default, 5)
               for s,metric,default in zip([a,b,c,d],opts,[40,25,20,15])]
    min_sample = st.slider("Minimum " + ("AB" if category=="Hitters" else "IP"),
                           0, 300 if category == "Hitters" else 130,
                           100 if category == "Hitters" else 25, 5)
    frame = frame[frame.ab >= min_sample] if category == "Hitters" else frame[frame.ip >= min_sample]
    if frame.empty:
        st.info("No player-seasons meet the selected minimum.")
    else:
        rankparts = []
        for metric in opts:
            key = metricmap[metric]
            pct = frame.groupby("season")[key].rank(pct=True, na_option="keep")*100
            if metric in ("K%",) and category == "Hitters":
                pct = 100-pct
            if metric in ("WHIP", "BB%") and category == "Pitchers":
                pct = 100-pct
            rankparts.append(pct.fillna(50))
        total = sum(weights)
        frame["screen"] = (sum(p*w for p,w in zip(rankparts,weights))/total) if total else 50.0
        view = frame.sort_values("screen", ascending=False)
        show = [label,"season","team","screen"] + (
            ["ab","ops","iso","hr","bb_pct","k_pct"] if category == "Hitters" else
            ["ip","era","whip","k_pct","bb_pct","kbb_pct"])
        st.dataframe(view[show], hide_index=True, use_container_width=True,
                     column_config={"screen":st.column_config.ProgressColumn("Sample score",min_value=0,max_value=100)})
        download(view[show], "lmb_custom_screen.csv", "⬇ Export scouting screen")
    st.warning("This is a user-defined within-sample ranking, NOT a validated scouting grade, Stuff+, wRC+, OPS+ or full-league percentile. Missing PA-based rates receive a neutral score of 50.")

elif mode == "🧪 Pitch Tracking":
    st.subheader("Pitch shape and location lab")
    st.info("LMB season statistics do not supply velocity, spin or pitch movement. Import actual authorized pitch-level data to activate the plots.")
    template = ROOT / "data/pitch_tracking_template.csv"
    st.download_button("⬇ Download pitch-tracking CSV template", template.read_bytes(),
                       "pitch_tracking_template.csv", mime="text/csv")
    track = st.file_uploader("Upload authorized pitch-level tracking file", type="csv", key="tracking")
    if track:
        try:
            t = pd.read_csv(track)
            t.columns = [c.strip().lower().replace(" ","_") for c in t.columns]
            if "pitcher" not in t.columns:
                raise ValueError("A pitcher column is required.")
            t = t[~t.pitcher.astype(str).str.contains("EXAMPLE ONLY",case=False,regex=False)]
            if t.empty:
                raise ValueError("Replace the example row with actual tracking observations.")
            for c in ["release_speed","spin_rate","ivb","hb","plate_x","plate_z"]:
                if c in t.columns:
                    t[c] = pd.to_numeric(t[c],errors="coerce")
            if "pitch_type" not in t.columns:
                t["pitch_type"] = "Unknown"
            name = st.selectbox("Pitcher", sorted(t.pitcher.astype(str).unique()))
            t = t[t.pitcher.astype(str).eq(name)]
            a,b,c = st.columns(3)
            a.metric("Tracked pitches", len(t))
            b.metric("Velocity", f"{t.release_speed.mean():.1f} mph" if "release_speed" in t.columns else "—")
            c.metric("Spin", f"{t.spin_rate.mean():.0f} rpm" if "spin_rate" in t.columns else "—")
            if {"hb","ivb"}.issubset(t.columns):
                st.plotly_chart(px.scatter(t,x="hb",y="ivb",color="pitch_type",
                    title="Horizontal and induced vertical break"),use_container_width=True)
                st.caption("Verify units and sign conventions with the data provider.")
            if {"plate_x","plate_z"}.issubset(t.columns):
                fig = px.scatter(t,x="plate_x",y="plate_z",color="pitch_type",title="Locations")
                fig.add_shape(type="rect",x0=-0.83,x1=0.83,y0=1.5,y1=3.5,
                              line=dict(dash="dash",color="#FEBB71"))
                st.plotly_chart(fig,use_container_width=True)
                st.caption("Strike zone is illustrative and does not account for individual batter height.")
            download(t,"authorized_tracking_analysis.csv","⬇ Export selected tracking pitches")
        except Exception as e:
            st.error(f"Tracking CSV could not be analyzed: {e}")

elif mode == "📝 Scout Notes":
    st.subheader("Scouting workbench")
    st.warning("Notes are temporary in this browser session. Download the CSV before closing. Do not submit confidential organization information to a publicly hosted demo.")
    category = st.radio("Evaluation type", ["Hitter", "Pitcher"], horizontal=True)
    name = st.selectbox("Player", sorted(hitters.player.unique()) if category == "Hitter" else sorted(pitchers.pitcher.unique()))
    grade = st.slider("Overall present 20–80 grade",20,80,50,5)
    priority = st.selectbox("Next action", ["Request video", "Follow", "Contact", "Invite", "Pass"])
    notes = st.text_area("Observations")
    if "scouting_notes" not in st.session_state:
        st.session_state.scouting_notes = []
    if st.button("Add note to session"):
        st.session_state.scouting_notes.append({"category":category,"player":name,
            "present_grade":grade,"action":priority,"notes":notes})
        st.success("Note added to session. Download to retain.")
    if st.session_state.scouting_notes:
        table = pd.DataFrame(st.session_state.scouting_notes)
        st.dataframe(table,hide_index=True,use_container_width=True)
        download(table,"lmb_scouting_notes.csv","⬇ Save scouting notes CSV")

else:
    st.subheader("Data sources, definitions and limitations")
    st.markdown("""
**Scope:** LMB regular-season statistics, 2024–2026 only. The preloaded datasets are **selected player-season scouting samples**, NOT full historical league records or automatic live feeds. Player/team information may refer to multiple teams in one year.

**Verified published sources:**
- [2024 LMB league and leaders](https://www.baseball-reference.com/register/league.cgi?id=83fa0ab3)
- [2025 LMB league and leaders](https://www.baseball-reference.com/register/league.cgi?id=b5ba4b13)
- [2026 LMB league and leaders](https://www.baseball-reference.com/register/league.cgi?id=f6efe3f3)
- [MiLB Mexican League statistical pages](https://www.milb.com/es/mexican/stats/player)

**Hitting:** AVG, OBP, SLG and OPS are published values. ISO = SLG − AVG; XBH = 2B + 3B + HR. K% and BB% use reported plate appearances. Where PA cannot be verified, percentages remain blank. Do not estimate unavailable plate appearances.

**Pitching:** Baseball innings are thirds, not decimals (10.2 = 10⅔). ERA = 9×ER/IP; WHIP=(H+BB)/IP; K% = K/BF; BB% = BB/BF. No TrackMan pitch shapes are fabricated.

**Comparisons:** Competition, ballpark, player roles, opponent quality and seasonal run environment have NOT been normalized. The custom screening index ranks only the loaded sample. Missing sample records are not evidence that players were inactive.

**Import:** Hitter CSV requires player, season, team, g, pa, ab, r, h, doubles, triples, hr, rbi, bb, so, sb, cs, avg, obp, slg, ops. Empty PA is allowed; the other statistical fields are required. Pitcher CSV requires pitcher, season, team, g, gs, ip_baseball, h, er, hr, bb, k, bf. If a league column is present it must equal LMB. Use only authorized datasets.
""")
    st.caption("Community Cloud is free-tier hosting; uploaded data and session notes are not persisted.")

st.divider()
st.caption("LMB SCOUT LAB • 2024–2026 • Selected historical scouting dataset • No proprietary tracking feed")
