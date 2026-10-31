from pathlib import Path
import io
import unicodedata
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "mexican_pitchers_2026_snapshot.csv"
TEMPLATE = ROOT / "data" / "pitch_tracking_template.csv"
REQUIRED = ["pitcher","league","season","team","g","gs","ip_baseball","h","er","hr","bb","k","bf"]
METRICS = {"K%":"k_pct","BB%":"bb_pct","K-BB%":"kbb_pct","ERA":"era","WHIP":"whip","K/9":"k9","BB/9":"bb9","HR/9":"hr9"}
st.set_page_config(page_title="MEX | Pitching Intelligence", page_icon="⚾", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.8rem}
h1,h2,h3{letter-spacing:-.03em}
[data-testid="stMetric"]{background:#13263A;border:1px solid #284257;border-radius:12px;padding:12px}
</style>""",unsafe_allow_html=True)

def innings(x):
    s=str(x).strip()
    a,_,b=s.partition(".")
    if b not in ("","0","1","2"):
        raise ValueError("Innings must use baseball notation such as 10.2 for ten and two-thirds")
    return int(a)+int(b or "0")/3

def normalize(x):
    return "".join(c for c in unicodedata.normalize("NFKD",str(x).casefold()) if not unicodedata.combining(c))

def load(df):
    df=df.copy()
    df.columns=[str(c).strip().lower().replace(" ","_") for c in df.columns]
    missing=set(REQUIRED)-set(df)
    if missing: raise ValueError("Missing CSV fields: "+", ".join(sorted(missing)))
    df["ip"] = df.ip_baseball.map(innings)
    for c in ["g","gs","h","er","hr","bb","k","bf"]:
        df[c]=pd.to_numeric(df[c],errors="raise")
    if (df["ip"]<=0).any() or (df["bf"]<=0).any() or (df[["g","gs","h","er","hr","bb","k","bf"]]<0).any().any():
        raise ValueError("Invalid negative or zero innings/batters-faced value")
    if (df.k+df.bb>df.bf).any(): raise ValueError("K + BB cannot exceed batters faced")
    df["era"]=9*df.er/df.ip
    df["whip"]=(df.h+df.bb)/df.ip
    df["k9"]=9*df.k/df.ip
    df["bb9"]=9*df.bb/df.ip
    df["hr9"]=9*df.hr/df.ip
    df["k_pct"]=100*df.k/df.bf
    df["bb_pct"]=100*df.bb/df.bf
    df["kbb_pct"]=df.k_pct-df.bb_pct
    df["key"]=df.pitcher.map(normalize)
    df["record"]=df.pitcher+" | "+df.league+" "+df.season.astype(str)+" | "+df.team
    return df

@st.cache_data
def base():
    return load(pd.read_csv(CSV,dtype={"ip_baseball":str,"season":str}))

def download(df,name,label):
    data=df.copy()
    for c in data.select_dtypes(include="object").columns:
        data[c]=data[c].map(lambda x: "'"+x if isinstance(x,str) and x.startswith(("=","+","-","@")) else x)
    st.download_button(label,data.to_csv(index=False).encode("utf-8-sig"),name,mime="text/csv")

with st.sidebar:
    st.title("⚾ MEX / INTEL")
    st.caption("MEXICAN BASEBALL • PITCHING WORKBENCH")
    st.success("FREE OPEN-SOURCE PROTOTYPE")
    st.info("53 selected records: LMB 2026 and early LMP 2026–27. Not a complete or live league database.")
    upload=st.file_uploader("Import pitcher-season CSV",type="csv",key="season")
    mode=st.radio("Import mode",["Add/replace matching records","Only my uploaded file"])
    st.download_button("⬇ Download source data",CSV.read_bytes(),"mexican_pitcher_snapshot.csv",mime="text/csv")
    st.caption("Uploaded data and notes are temporary for this browser session.")

try:
    all_data=base()
    if upload:
        new=load(pd.read_csv(upload,dtype={"ip_baseball":str,"season":str}))
        if mode=="Only my uploaded file": all_data=new
        else:
            all_data=pd.concat([all_data,new],ignore_index=True).drop_duplicates(["key","league","season","team"],keep="last")
except Exception as ex:
    st.error(f"Data could not be loaded: {ex}")
    st.stop()

st.title("MEXICAN BASEBALL | PITCHING INTELLIGENCE")
st.caption("Raul González scouting workbench • LMB and LMP • Selected historical 2026 data • No proprietary feed")
a,b,c=st.columns(3)
leagues=a.multiselect("Leagues",sorted(all_data.league.unique()),default=sorted(all_data.league.unique()))
min_ip=b.slider("Minimum IP",0,150,5,5)
query=c.text_input("Search pitcher / team")
data=all_data[all_data.league.isin(leagues)&(all_data.ip>=min_ip)].copy()
if query:
    data=data[data.pitcher.str.contains(query,case=False,regex=False)|data.team.str.contains(query,case=False,regex=False)]
m1,m2,m3,m4=st.columns(4)
m1.metric("Pitching records",len(data))
m2.metric("Unique pitchers",data.key.nunique())
m3.metric("Leagues",data.league.nunique())
m4.metric("IP in selection",f"{data.ip.sum():,.1f}")
tabs=st.tabs(["📊 Landscape","🔎 Pitcher Finder","⚔️ Head-to-Head","🔁 League Bridge","🧪 Tracking Lab","📝 Scout Desk","ℹ️ Sources"])

with tabs[0]:
    st.subheader("Strikeout and walk landscape")
    if len(data):
        fig=px.scatter(data,x="k_pct",y="bb_pct",size="ip",color="league",hover_name="pitcher",
                       hover_data=["team","season","era","whip"],labels={"k_pct":"K% of batters faced","bb_pct":"BB% of batters faced"})
        st.plotly_chart(fig,use_container_width=True)
        st.caption("Right = more strikeouts. Lower = fewer walks. Bubble size = innings.")
        metric=st.selectbox("Rank pitchers by",list(METRICS))
        key=METRICS[metric]
        low=key in ("bb_pct","era","whip","bb9","hr9")
        best=data.sort_values(key,ascending=low).head(15)
        st.plotly_chart(px.bar(best.iloc[::-1],x=key,y="pitcher",orientation="h",color="league",
                        labels={key:metric,"pitcher":""}),use_container_width=True)
    else: st.info("No pitchers match these filters.")

with tabs[1]:
    st.subheader("Adjustable statistical scouting screen")
    st.caption("This is a custom screening index—not Stuff+, Pitching+, a forecast or official league percentile.")
    w1,w2,w3,w4=st.columns(4)
    weights=[w1.slider("K% weight",0,100,30,5),w2.slider("K-BB% weight",0,100,35,5),
             w3.slider("WHIP weight",0,100,25,5),w4.slider("HR/9 weight",0,100,10,5)]
    if len(data):
        score=data.copy()
        keys=["k_pct","kbb_pct","whip","hr9"]
        terms=[]
        for i,key in enumerate(keys):
            pct=score.groupby(["league","season"])[key].rank(pct=True)*100
            terms.append(pct if i<2 else 100-pct)
        total=sum(weights)
        raw=sum(w*v for w,v in zip(weights,terms))/total if total else 50
        score["screen"]=50+(raw-50)*(score.ip/40).clip(upper=1)
        screen=score.sort_values("screen",ascending=False)[
            ["pitcher","league","season","team","ip","era","whip","k9","bb9","k_pct","bb_pct","kbb_pct","screen"]]
        st.dataframe(screen,use_container_width=True,hide_index=True,
            column_config={"screen":st.column_config.ProgressColumn("Sample screen / 100",min_value=0,max_value=100)})
        download(screen,"mexican_pitcher_screen.csv","⬇ Export screening table")
        st.warning("Rankings are computed within the *selected sample* by league and season, and shrink records under 40 IP toward 50. They are not full-league rankings.")
    else: st.info("Adjust filters to see results.")

with tabs[2]:
    st.subheader("Compare any two pitcher records")
    options=sorted(all_data.record.unique())
    if len(options)>=2:
        x,y=st.columns(2)
        a=x.selectbox("Pitcher A",options,index=0)
        b=y.selectbox("Pitcher B",options,index=1)
        pa=all_data[all_data.record==a].iloc[0]
        pb=all_data[all_data.record==b].iloc[0]
        if pa.league!=pb.league or pa.season!=pb.season:
            st.warning("Cross-league or cross-season stats are descriptive, not translated performance projections.")
        metrics=st.multiselect("Metrics",list(METRICS),default=["K%","BB%","K-BB%"])
        if metrics:
            vals=[{"Pitcher":p.pitcher,"Metric":m,"Value":p[METRICS[m]]} for p in (pa,pb) for m in metrics]
            st.plotly_chart(px.bar(pd.DataFrame(vals),x="Metric",y="Value",color="Pitcher",barmode="group",text_auto=".1f"),
                            use_container_width=True)
        compare=pd.DataFrame([{"Pitcher":p.pitcher,"League":p.league,"Season":p.season,"Team":p.team,
            "IP":round(p.ip,1),"ERA":round(p.era,2),"WHIP":round(p.whip,2),
            "K%":round(p.k_pct,1),"BB%":round(p.bb_pct,1),"K-BB%":round(p.kbb_pct,1)} for p in (pa,pb)])
        st.dataframe(compare,hide_index=True,use_container_width=True)
    else: st.info("At least two records required.")

with tabs[3]:
    st.subheader("Summer ↔ Winter pitching")
    counts=all_data.groupby("key").league.nunique()
    matched=all_data[all_data.key.isin(counts[counts>1].index)]
    if len(matched):
        st.dataframe(matched[["pitcher","league","season","team","ip","era","whip","k_pct","bb_pct"]],
                     hide_index=True,use_container_width=True)
        who=st.selectbox("Follow pitcher",sorted(matched.pitcher.unique()))
        selected=matched[matched.pitcher==who]
        st.plotly_chart(px.bar(selected,x="league",y="kbb_pct",color="season",hover_data=["ip","team"],
                        title="K-BB% across leagues"),use_container_width=True)
        st.caption("Different opposition, parks and sample sizes; no park or league adjustment is applied.")
    else: st.info("No overlapping players in the currently loaded league datasets.")

with tabs[4]:
    st.subheader("Authorized pitch-level CSV analysis")
    st.info("Pitch tracking data are NOT included in the public league statistics. Upload real authorized data; no velocity, spin or movement is fabricated.")
    st.download_button("⬇ Tracking CSV template (EXAMPLE ONLY)",TEMPLATE.read_bytes(),"pitch_tracking_template.csv",mime="text/csv")
    tracking=st.file_uploader("Pitch-level tracking CSV",type="csv",key="tracking")
    if tracking:
        try:
            t=pd.read_csv(tracking)
            t.columns=[str(k).strip().lower().replace(" ","_") for k in t.columns]
            if "pitcher" not in t: raise ValueError("A pitcher column is required")
            t=t[~t.pitcher.astype(str).str.contains("EXAMPLE ONLY",case=False,regex=False)]
            if not len(t):raise ValueError("Replace the example row with actual observations")
            for k in ("release_speed","spin_rate","ivb","hb","plate_x","plate_z"):
                if k in t:t[k]=pd.to_numeric(t[k],errors="coerce")
            who=st.selectbox("Tracked pitcher",sorted(t.pitcher.unique()))
            t=t[t.pitcher==who]
            if "pitch_type" not in t:t["pitch_type"]="Unknown"
            p1,p2,p3=st.columns(3)
            p1.metric("Tracked pitches",len(t))
            p2.metric("Avg velocity",f"{t.release_speed.mean():.1f} mph" if "release_speed" in t else "—")
            p3.metric("Avg spin",f"{t.spin_rate.mean():,.0f} rpm" if "spin_rate" in t else "—")
            if {"hb","ivb"}.issubset(t.columns):
                st.plotly_chart(px.scatter(t,x="hb",y="ivb",color="pitch_type",
                    labels={"hb":"Horizontal break (in)","ivb":"Induced vertical break (in)"},
                    title="Pitch shape"),use_container_width=True)
                st.caption("Confirm vendor-specific movement sign conventions.")
            if {"plate_x","plate_z"}.issubset(t.columns):
                fig=px.scatter(t,x="plate_x",y="plate_z",color="pitch_type",title="Pitch locations")
                fig.add_shape(type="rect",x0=-.83,x1=.83,y0=1.5,y1=3.5,line=dict(color="#FFB45E",dash="dash"))
                st.plotly_chart(fig,use_container_width=True)
                st.caption("Dashed strike zone is illustrative, not personalized to batter height.")
            download(t,"pitch_tracking_analysis.csv","⬇ Export analyzed pitches")
        except Exception as ex: st.error(f"Tracking import error: {ex}")

with tabs[5]:
    st.subheader("Scout notes — save as CSV")
    st.warning("Notes exist only for your current browser session. Download before leaving. Do not enter confidential scouting information into a public prototype.")
    who=st.selectbox("Pitcher",sorted(all_data.pitcher.unique()))
    priority=st.selectbox("Priority",["Follow up","Needs video","Watchlist","Invite/contact","Pass"])
    role=st.selectbox("Projected role",["Unknown","Starter","Multi-inning relief","Late-inning relief"])
    present=st.slider("Present grade (20–80)",20,80,50,5)
    command=st.slider("Command grade (20–80)",20,80,50,5)
    note=st.text_area("Observation and next steps")
    if "notes" not in st.session_state:st.session_state.notes=[]
    if st.button("Add session note"):
        st.session_state.notes.append(dict(pitcher=who,priority=priority,role=role,
                                           present_grade=present,command_grade=command,note=note))
        st.success("Added. Download notes to preserve them.")
    if st.session_state.notes:
        notes=pd.DataFrame(st.session_state.notes)
        st.dataframe(notes,use_container_width=True,hide_index=True)
        download(notes,"raul_scout_notes.csv","⬇ Download scouting notes")

with tabs[6]:
    st.subheader("Data methodology and privacy")
    st.markdown("""
**Historical selection, not a full league or current live feed.** Base dataset contains 42 selected LMB 2026 pitching lines and 11 early-season 2026–27 LMP lines. Verify transactions, roster status and updated figures before scouting decisions.

**Published record references**
- [LMB season statistical reference](https://www.baseball-reference.com/register/leader.cgi?id=f6efe3f3&type=pitch)
- [LMP winter statistical reference](https://www.baseball-reference.com/register/leader.cgi?id=f92a5aa1&type=pitch)

**Calculations:** Innings use baseball notation (10.2 = 10⅔). ERA = 9×ER/IP; WHIP=(H+BB)/IP; K% =100×K/BF; BB%=100×BB/BF. The screening index is a user-adjustable composite of within-loaded-sample ranks for K%, K-BB%, WHIP and HR/9, shrunk toward 50 below 40 IP.

**Limitations:** League competition, park and opponent differences are unadjusted. Public season stats do not contain TrackMan pitch shape, spin or locations. Data uploads and notes are not persistently saved. Do not publish proprietary tracking exports or private scout information in a public repository.
""")
    st.code("pitcher,league,season,team,g,gs,ip_baseball,h,er,hr,bb,k,bf")
st.divider()
st.caption("MEX / PITCHING INTELLIGENCE • FREE STREAMLIT PROTOTYPE • NO PAID DATA FEEDS")
