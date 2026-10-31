# ⚾ LMB Scouting Intelligence

Free interactive LMB scouting dashboard for hitters and pitchers across the 2024–2026 seasons.

## Features

- Hitter finder: AVG, OBP, SLG, OPS, ISO, HR, RBI, stolen bases, BB% and K%
- Pitcher finder: ERA, WHIP, K/9, BB/9, HR/9, K%, BB%, K-BB%
- Head-to-head hitter and pitcher comparisons
- 2024–2026 player development trends
- Adjustable experimental scouting screen (not a proprietary scouting metric)
- CSV import and export; sample pitch-level movement/location analysis
- Exportable scouting notes (session-only; not persistent)

## Data coverage

**LMB-only historical selected records, not a complete league database or live data feed.**

| Season | Preloaded hitter-seasons | Preloaded pitcher-seasons |
| --- | ---: | ---: |
| 2024 | 20 | 9 |
| 2025 | 20 | 10 |
| 2026 | 19 | 42 |
| Total | **59** | **61** |

The initial data come from publicly available Mexican League batting and pitching leader pages. Multi-team player-season lines are combined at the published league level. Some 2024 player records omit plate appearances because these could not be verified from the available source; PA-dependent metrics remain blank.

**Sources**

- [2024 LMB batting and pitching](https://www.baseball-reference.com/register/league.cgi?id=83fa0ab3)
- [2025 LMB batting and pitching](https://www.baseball-reference.com/register/league.cgi?id=b5ba4b13)
- [2026 LMB batting and pitching](https://www.baseball-reference.com/register/league.cgi?id=f6efe3f3)
- [MiLB Mexican League leaderboards](https://www.milb.com/es/mexican/stats/player)

No LMP (Mexican Pacific Winter League) observations are included in the deployed dataset.

## Deployment

Community Cloud: **Main file:** `streamlit_app.py`

The app is connected to this GitHub repository. Editing code on the main branch normally updates the website automatically via Streamlit Community Cloud.

For local execution:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

On a phone, select a workspace using the dropdown near the top of the page. Historical sample data can be supplemented by uploading a properly formatted CSV.

## Data imports

- Hitting: `player,season,team,g,pa,ab,r,h,doubles,triples,hr,rbi,bb,so,sb,cs,avg,obp,slg,ops`
- Pitching: `pitcher,season,team,g,gs,ip_baseball,h,er,hr,bb,k,bf`
- Optional `league` column must equal `LMB`.
- Seasons accepted: 2024, 2025 or 2026.
- For unknown plate appearances, leave `pa` empty rather than inventing them.
- Pitcher innings use baseball notation, e.g. `10.2` is ten and two-thirds innings.

## Important limitations

Rankings cover the loaded **sample**, not all Mexican League players. Differences in role, park, team, strength of schedule and era aren't statistically adjusted. TrackMan data (velocity, spin, pitch movement) must come from a separately authorized file. No private uploads or scouting notes are permanently stored. Avoid entering confidential personnel information into a publicly hosted demonstration.
