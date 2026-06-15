import streamlit as st

st.set_page_config(page_title="NSW Price", page_icon="💲", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from downloader import (
    download_latest_predispatch, get_latest_predispatch_local,
    download_latest_dispatchis, get_latest_dispatchis_local,
    download_latest_p5min, get_latest_p5min_local,
)
from parser import load_predispatch_region, load_dispatch_price, load_p5min_regionsolution

REGION = "NSW"
REGION_ID = "NSW1"
COLOUR = "#0ea5e9"

PRICE_PERIODS = [
    ("ON", "Overnight",    "12am–6am",  "Wind-weighted, lower-demand period",      0,  6),
    ("MP", "Morning Peak", "6am–10am",  "Demand ramp and system tightening",        6,  10),
    ("MD", "Midday",       "10am–4pm",  "Solar oversupply and negative price risk", 10, 16),
    ("EP", "Evening Peak", "4pm–8pm",   "Highest demand and price risk",            16, 20),
    ("LE", "Late Evening", "8pm–12am",  "Post-peak residual volatility",            20, 24),
]

PERIOD_COLOURS = {
    "ON": "#94a3b8",
    "MP": "#fbbf24",
    "MD": "#10b981",
    "EP": "#ef4444",
    "LE": "#8b5cf6",
}


def _hex_to_rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


refresh_count = st_autorefresh(interval=300_000, key="nsw_price_autorefresh")
_last = st.session_state.get("_nsw_last_refresh", -1)
_is_autorefresh = refresh_count != _last
st.session_state["_nsw_last_refresh"] = refresh_count


def _snapshot() -> dict:
    return {
        "pd":  (get_latest_predispatch_local() or "").name if get_latest_predispatch_local() else "",
        "dis": (get_latest_dispatchis_local()  or "").name if get_latest_dispatchis_local() else "",
        "p5":  (get_latest_p5min_local()        or "").name if get_latest_p5min_local() else "",
    }


def _fetch_all(spinner: bool = False):
    ctx = st.spinner("Checking NEMWEB...") if spinner else _null()
    with ctx:
        try:
            _, msg = download_latest_predispatch()
        except Exception as e:
            msg = f"Failed: {e}"
        for fn in (download_latest_dispatchis, download_latest_p5min):
            try:
                fn()
            except Exception:
                pass
    return msg


class _null:
    def __enter__(self): return self
    def __exit__(self, *_): pass


@st.cache_data(show_spinner=False)
def _load_pd(path: str) -> pd.DataFrame:
    from pathlib import Path
    df = load_predispatch_region(Path(path))
    return df[df["REGION_LABEL"] == REGION].sort_values("PERIODID")

@st.cache_data(show_spinner=False)
def _load_p5(path: str) -> pd.DataFrame:
    from pathlib import Path
    df = load_p5min_regionsolution(Path(path))
    return df[df["REGION_LABEL"] == REGION].sort_values("INTERVAL_DATETIME")

@st.cache_data(show_spinner=False)
def _load_dis(path: str) -> pd.DataFrame:
    from pathlib import Path
    return load_dispatch_price(Path(path))


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("NSW Price")
    st.caption("Pre-Dispatch spot price — NSW only")
    st.divider()

    if "nsw_status" not in st.session_state:
        msg = _fetch_all(spinner=True)
        st.session_state["nsw_status"] = msg
        st.session_state["_nsw_files"] = _snapshot()
    elif _is_autorefresh:
        old = st.session_state.get("_nsw_files", {})
        msg = _fetch_all(spinner=False)
        new = _snapshot()
        if new != old:
            st.cache_data.clear()
            st.session_state["_nsw_files"] = new
        st.session_state["nsw_status"] = msg

    st.info(st.session_state["nsw_status"])

    if st.button("Refresh now"):
        st.session_state.pop("nsw_status", None)
        st.cache_data.clear()
        msg = _fetch_all(spinner=True)
        st.session_state["nsw_status"] = msg
        st.session_state["_nsw_files"] = _snapshot()

    st.divider()

    def _ts(path) -> str:
        import re
        from pathlib import Path
        if path is None:
            return "—"
        m = re.search(r"_(\d{12})_", path.name)
        if not m:
            return path.name
        try:
            return pd.to_datetime(m.group(1), format="%Y%m%d%H%M").strftime("%d %b %H:%M")
        except Exception:
            return m.group(1)

    pd_path  = get_latest_predispatch_local()
    dis_path = get_latest_dispatchis_local()
    p5_path  = get_latest_p5min_local()

    st.markdown("**Data sources**")
    st.markdown(
        f"| Source | Latest |\n|---|---|\n"
        f"| Pre-Dispatch 30min | {_ts(pd_path)} |\n"
        f"| DispatchIS (actual) | {_ts(dis_path)} |\n"
        f"| P5MIN (5min) | {_ts(p5_path)} |"
    )
    st.divider()
    st.caption("Auto-refreshes every 5 minutes")


# ── Load data ─────────────────────────────────────────────────────────────────
if pd_path is None:
    st.error("No Pre-Dispatch file found.")
    st.stop()

df_pd  = _load_pd(str(pd_path))
df_p5  = _load_p5(str(p5_path))  if p5_path  else pd.DataFrame()
df_dis = _load_dis(str(dis_path)) if dis_path else pd.DataFrame()

actual_rrp = None
actual_dt  = ""
if not df_dis.empty:
    latest_dt = df_dis["SETTLEMENTDATE"].max()
    row = df_dis[(df_dis["SETTLEMENTDATE"] == latest_dt) & (df_dis["REGION_LABEL"] == REGION)]
    if not row.empty:
        actual_rrp = float(row.iloc[0]["RRP"])
        actual_dt  = latest_dt.strftime("%d %b %H:%M")

run_dt = df_pd["PREDISPATCHSEQNO"].dropna().max() if not df_pd.empty else None
run_label = run_dt.strftime("%d %b %Y %H:%M") if run_dt and pd.notna(run_dt) else "—"


# ── Header ────────────────────────────────────────────────────────────────────
st.title("NSW — Spot Price Forecast")
st.caption(f"Pre-Dispatch run: **{run_label}** | Actual price source: DispatchIS {actual_dt}")

st.divider()


# ── Metric cards ──────────────────────────────────────────────────────────────
def _period_avg(start_h: int, end_h: int):
    now = pd.Timestamp.now()
    if end_h == 24:
        hmask = df_pd["PERIODID"].dt.hour >= start_h
    else:
        hmask = (df_pd["PERIODID"].dt.hour >= start_h) & (df_pd["PERIODID"].dt.hour < end_h)
    sub = df_pd.loc[(df_pd["PERIODID"] >= now) & hmask].dropna(subset=["RRP"])
    if sub.empty:
        return None, None
    d = sub["PERIODID"].dt.date.min()
    avg = sub[sub["PERIODID"].dt.date == d]["RRP"].mean()
    return avg, d


col_act, col_on, col_mp, col_md, col_ep, col_le = st.columns(6)

with col_act:
    val = f"${actual_rrp:,.2f}" if actual_rrp is not None else "—"
    st.markdown(
        f'<div style="background:#0f172a;color:#fff;border-radius:8px;padding:14px 16px;text-align:center;height:100%">'
        f'<div style="font-size:11px;opacity:0.7;text-transform:uppercase;letter-spacing:1px">Actual</div>'
        f'<div style="font-size:11px;opacity:0.5;margin-top:2px">{actual_dt}</div>'
        f'<div style="font-size:26px;font-weight:700;margin-top:6px">{val}</div>'
        f'<div style="font-size:11px;opacity:0.6">$/MWh</div>'
        f'</div>', unsafe_allow_html=True
    )

period_cols = [col_on, col_mp, col_md, col_ep, col_le]
for col, (code, label, hours, desc, sh, eh) in zip(period_cols, PRICE_PERIODS):
    avg, date = _period_avg(sh, eh)
    val  = f"${avg:,.2f}" if avg is not None else "—"
    dstr = date.strftime("%d %b") if date else ""
    clr  = PERIOD_COLOURS[code]
    bg   = _hex_to_rgba(clr, 0.10)
    bdr  = _hex_to_rgba(clr, 0.35)
    with col:
        st.markdown(
            f'<div style="background:{bg};border:1px solid {bdr};'
            f'border-left:4px solid {clr};border-radius:8px;padding:14px 16px;text-align:center">'
            f'<div style="font-size:12px;font-weight:700;color:{clr};text-transform:uppercase;letter-spacing:1px">'
            f'{code} · {label}</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:2px">{hours}</div>'
            f'<div style="font-size:22px;font-weight:700;color:#0f172a;margin-top:6px">{val}</div>'
            f'<div style="font-size:11px;color:#94a3b8;margin-top:2px">avg $/MWh · {dstr}</div>'
            f'<div style="font-size:11px;color:#64748b;margin-top:6px;font-style:italic;border-top:1px solid {bdr};padding-top:6px">'
            f'{desc}</div>'
            f'</div>', unsafe_allow_html=True
        )

st.divider()


# ── Price chart ───────────────────────────────────────────────────────────────
st.subheader("Forecast Spot Price — NSW")
st.caption("Solid = 30-min pre-dispatch | Dotted = P5MIN (5-min)")

fig = go.Figure()

df_rrp = df_pd.dropna(subset=["RRP"])
if not df_rrp.empty:
    fig.add_trace(go.Scatter(
        x=df_rrp["PERIODID"], y=df_rrp["RRP"],
        name="RRP 30min",
        line=dict(color=COLOUR, width=2.5),
        hovertemplate="%{x|%d %b %H:%M}<br>$%{y:,.2f}/MWh<extra>30min</extra>",
    ))

if not df_p5.empty:
    df_p5_rrp = df_p5.dropna(subset=["RRP"])
    if not df_p5_rrp.empty:
        fig.add_trace(go.Scatter(
            x=df_p5_rrp["INTERVAL_DATETIME"], y=df_p5_rrp["RRP"],
            name="RRP 5min",
            mode="lines",
            line=dict(color=COLOUR, width=1.5, dash="dot"),
            hovertemplate="%{x|%d %b %H:%M}<br>$%{y:,.2f}/MWh<extra>5min</extra>",
        ))

if actual_rrp is not None:
    fig.add_hline(
        y=actual_rrp,
        line=dict(color="#0f172a", width=1, dash="dash"),
        annotation_text=f"Actual {actual_dt}: ${actual_rrp:,.2f}/MWh",
        annotation_position="top left",
        annotation_font_size=11,
    )

now = pd.Timestamp.now()
_shade_colours = {code: _hex_to_rgba(clr, 0.12) for code, clr in PERIOD_COLOURS.items()}
if not df_pd.empty:
    _min_x = df_pd["PERIODID"].min()
    _max_x = df_pd["PERIODID"].max()
    _day = _min_x.normalize()
    while _day <= _max_x:
        for code, _, _hours, _desc, sh, eh in PRICE_PERIODS:
            _s = _day + pd.Timedelta(hours=sh)
            _e = _day + pd.Timedelta(hours=eh)
            if _e <= now or _s >= _max_x:
                continue
            fig.add_vrect(
                x0=_s, x1=_e,
                fillcolor=_shade_colours.get(code, "rgba(0,0,0,0.03)"),
                layer="below", line_width=0,
            )
        _day += pd.Timedelta(days=1)

fig.update_layout(
    yaxis_title="Spot Price ($/MWh)",
    xaxis_title=None,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=0, r=0, t=30, b=0),
    height=460,
    hovermode="x unified",
    plot_bgcolor="#f8fafc",
    paper_bgcolor="#ffffff",
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(gridcolor="#e2e8f0")

st.plotly_chart(fig, width="stretch")

st.divider()
st.caption("Source: AEMO NEMWEB — Predispatch Reports + P5MIN + DispatchIS | NSW1 physical run (INTERVENTION=0)")
