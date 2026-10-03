"""Design tokens, thresholds and small formatting helpers."""

from __future__ import annotations

# ---------------------------------------------------------------- palette ---
PAPER = "#F4F1EA"
CARD = "#FBFAF7"
INK = "#1A1712"
MUTED = "#6E6759"
RULE = "#D8D1C1"
ACCENT = "#126A5B"      # deep teal — primary data ink
ACCENT_SOFT = "#DDE8E4"
ALERT = "#B4462F"       # terracotta — anomaly / attention
WATCH = "#B8862F"       # ochre — watch state
SLATE = "#5B6B72"       # secondary series
GOOD = "#2F6B4F"

CURRENCY = "$"

# Series colours used across plotly + matplotlib
SERIES_COLORS = {
    "kept": ACCENT,
    "cancelled": WATCH,
    "no_show": ALERT,
    "rescheduled": SLATE,
}
SERIES_LABELS = {
    "kept": "Kept",
    "cancelled": "Cancelled",
    "no_show": "No-show",
    "rescheduled": "Rescheduled",
}

# Assumed clinical capacity used for utilisation (minutes per weekday).
AVAILABLE_MINUTES = {0: 420, 1: 420, 2: 420, 3: 420, 4: 420, 5: 240, 6: 0}

# PoC reference thresholds. Configurable per clinic in a later build.
BENCHMARKS = {
    "no_show_rate": 0.08,
    "cancel_rate": 0.10,
    "utilization": 0.80,
    "wait_median": 20.0,
    "wait_p90": 35.0,
}


# --------------------------------------------------------------- formatting -
def fmt_money(v: float | int | None, decimals: int = 0) -> str:
    if v is None:
        return "—"
    return f"{CURRENCY}{v:,.{decimals}f}"


def fmt_pct(v: float | None, decimals: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.{decimals}f}%"


def fmt_num(v: float | int | None, decimals: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:,.{decimals}f}"


def fmt_delta(v: float | None) -> tuple[str, str]:
    """Return (text, direction) where direction is up|down|flat."""
    if v is None:
        return "—", "flat"
    arrow = "▲" if v > 0.0005 else ("▼" if v < -0.0005 else "■")
    return f"{arrow} {abs(v) * 100:.1f}%", ("up" if v > 0 else ("down" if v < 0 else "flat"))


# ---------------------------------------------------------------------- CSS -
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --mv-paper:#F4F1EA; --mv-card:#FBFAF7; --mv-ink:#1A1712; --mv-muted:#6E6759;
  --mv-rule:#D8D1C1; --mv-accent:#126A5B; --mv-alert:#B4462F; --mv-watch:#B8862F;
}

html, body, .stApp, [class*="css"] { font-family:'IBM Plex Sans', Inter, system-ui, sans-serif; }

.stApp{
  background-color:#F4F1EA;
  background-image:
    linear-gradient(rgba(26,23,18,0.028) 1px, transparent 1px),
    linear-gradient(90deg, rgba(26,23,18,0.028) 1px, transparent 1px);
  background-size:28px 28px;
  color:#1A1712;
}

header[data-testid="stHeader"]{ background-color:transparent; }
.block-container{ max-width:1220px; padding:1.1rem 2.6rem 5rem 2.6rem; }

h1,h2,h3,h4{ font-family:'Fraunces', Georgia, serif !important; color:#1A1712; letter-spacing:-0.018em; }
h1{ font-size:3.15rem !important; line-height:0.98 !important; font-weight:600 !important; }
h2{ font-size:1.85rem !important; font-weight:600 !important; }
h3{ font-size:1.18rem !important; font-weight:600 !important; }
p, li, label, span{ color:#2B2620; }
a{ color:#126A5B !important; }

/* ---- sidebar ---- */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#EDE7DB 0%,#E6DFD1 100%);
  border-right:1px solid #D8D1C1;
}
[data-testid="stSidebar"] .block-container{ padding:1.7rem 1.5rem 2rem 1.5rem; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{ font-size:1.02rem !important; }
[data-testid="stSidebar"] .stRadio label{ font-size:0.86rem; }

/* ---- controls ---- */
.stButton>button, .stDownloadButton>button{
  border-radius:2px; border:1px solid #1A1712; background:#1A1712; color:#F7F4ED;
  font-family:'IBM Plex Sans',sans-serif; font-size:0.74rem; font-weight:500;
  letter-spacing:0.11em; text-transform:uppercase; padding:0.56rem 1.15rem;
  transition:background .18s ease, color .18s ease, border-color .18s ease, transform .18s ease;
  width:100%;
}
.stButton>button:hover{ background:#126A5B; border-color:#126A5B; color:#F7F4ED; transform:translateY(-1px); }
.stDownloadButton>button{ background:transparent; color:#1A1712; }
.stDownloadButton>button:hover{ background:#1A1712; color:#F7F4ED; border-color:#1A1712; }
div[data-testid="stWidgetLabel"] p{ font-size:0.72rem; letter-spacing:0.13em; text-transform:uppercase; color:#6E6759; }

.stSelectbox [data-baseweb="select"], .stMultiSelect [data-baseweb="select"],
.stTextInput [data-baseweb="input"], .stDateInput [data-baseweb="input"],
.stNumberInput [data-baseweb="input"]{
  border-radius:2px; background:#FBFAF7; border-color:#D8D1C1;
}

/* ---- hero ---- */
.mv-hero{ padding:1.4rem 0 2.1rem 0; border-bottom:2px solid #1A1712; }
.mv-eyebrow{
  font-family:'IBM Plex Mono',monospace; font-size:0.68rem; letter-spacing:0.32em;
  text-transform:uppercase; color:#6E6759; margin-bottom:1.15rem;
}
.mv-kicker{ font-family:'Fraunces',serif; font-style:italic; font-size:1.22rem; color:#126A5B; margin:0.25rem 0 1.15rem 0; }
.mv-lede{ font-size:1.02rem; line-height:1.72; color:#3A342B; max-width:47rem; }
.mv-stamp-wrap{ display:flex; justify-content:flex-end; align-items:flex-start; }
.mv-stamp{
  border:2px solid #B4462F; color:#B4462F; padding:0.72rem 1.15rem 0.62rem 1.15rem;
  transform:rotate(-6deg); text-align:center; line-height:1.15; border-radius:3px;
  box-shadow:0 0 0 3px rgba(180,70,47,0.10); opacity:0.92;
}
.mv-stamp .big{ font-family:'IBM Plex Mono',monospace; font-weight:600; font-size:0.95rem; letter-spacing:0.16em; }
.mv-stamp .small{ font-family:'IBM Plex Mono',monospace; font-size:0.62rem; letter-spacing:0.19em; margin-top:0.28rem; }

/* ---- status strip ---- */
.mv-strip{
  background:#1A1712; color:#F2EEE5; padding:0.72rem 1.15rem; border-radius:2px;
  font-family:'IBM Plex Mono',monospace; font-size:0.715rem; letter-spacing:0.11em;
  text-transform:uppercase; display:flex; flex-wrap:wrap; gap:1.35rem; margin-top:1.15rem;
}
.mv-strip b{ color:#E7B58A; font-weight:500; }

/* ---- exhibits ---- */
.mv-exhibit{ border-top:2px solid #1A1712; margin-top:2.65rem; padding-top:0.72rem; }
.mv-exhibit .num{
  font-family:'IBM Plex Mono',monospace; font-size:0.68rem; letter-spacing:0.3em;
  color:#6E6759; text-transform:uppercase;
}
.mv-exhibit h2{ margin:0.32rem 0 0.28rem 0; }
.mv-exhibit .sub{ font-family:'Fraunces',serif; font-style:italic; color:#6E6759; font-size:0.98rem; margin-bottom:1.15rem; }

/* ---- ledger rows ---- */
.mv-ledger{ background:#FBFAF7; border:1px solid #D8D1C1; border-radius:2px; padding:0.35rem 1.15rem 0.2rem 1.15rem; }
.mv-row{ display:flex; align-items:baseline; justify-content:space-between; gap:1.25rem; padding:0.72rem 0; border-bottom:1px solid #E3DCCD; }
.mv-row:last-child{ border-bottom:none; }
.mv-row .lbl{ font-size:0.79rem; letter-spacing:0.13em; text-transform:uppercase; color:#6E6759; flex:1 1 auto; }
.mv-row .val{ font-family:'IBM Plex Mono',monospace; font-variant-numeric:tabular-nums; font-size:1.42rem; color:#1A1712; font-weight:500; }
.mv-row .cmp{ font-family:'IBM Plex Mono',monospace; font-size:0.78rem; min-width:8.6rem; text-align:right; }
.mv-up{ color:#B4462F; } .mv-down{ color:#2F6B4F; } .mv-flat{ color:#6E6759; }

/* ---- flags / marginalia ---- */
.mv-flag{ background:#FBFAF7; border:1px solid #D8D1C1; border-left:3px solid #B4462F; padding:0.95rem 1.15rem 1rem 1.15rem; margin-bottom:0.85rem; border-radius:2px; }
.mv-flag.watch{ border-left-color:#B8862F; }
.mv-flag.ok{ border-left-color:#2F6B4F; }
.mv-flag .tag{ font-family:'IBM Plex Mono',monospace; font-size:0.64rem; letter-spacing:0.22em; text-transform:uppercase; }
.mv-flag h4{ margin:0.32rem 0 0.34rem 0; font-size:1.02rem !important; }
.mv-flag p{ font-size:0.885rem; line-height:1.62; color:#4A4438; margin:0; }

/* ---- insight cards ---- */
.mv-insight{ background:#FBFAF7; border:1px solid #D8D1C1; border-radius:2px; padding:1.25rem 1.35rem; height:100%; }
.mv-insight .idx{ font-family:'IBM Plex Mono',monospace; font-size:0.66rem; letter-spacing:0.26em; color:#126A5B; text-transform:uppercase; }
.mv-insight h4{ margin:0.42rem 0 0.52rem 0; font-size:1.06rem !important; line-height:1.28; }
.mv-insight p{ font-size:0.875rem; line-height:1.68; color:#4A4438; }
.mv-insight .act{ border-top:1px solid #E3DCCD; margin-top:0.85rem; padding-top:0.75rem; font-size:0.845rem; color:#1A1712; }
.mv-insight .act b{ font-family:'IBM Plex Mono',monospace; font-size:0.645rem; letter-spacing:0.21em; text-transform:uppercase; color:#B4462F; display:block; margin-bottom:0.28rem; }

/* ---- misc ---- */
.mv-note{ font-family:'Fraunces',serif; font-style:italic; font-size:1.02rem; line-height:1.78; color:#2B2620; background:#FBFAF7; border-left:3px solid #126A5B; padding:1.15rem 1.35rem; }
.mv-warn{ background:#B4462F; color:#FBF3EE; padding:0.85rem 1.15rem; border-radius:2px; font-size:0.86rem; line-height:1.62; }
.mv-quiet{ font-size:0.795rem; line-height:1.72; color:#6E6759; }
.mv-kv{ font-family:'IBM Plex Mono',monospace; font-size:0.785rem; line-height:1.95; color:#4A4438; }
.mv-pill{ display:inline-block; border:1px solid #D8D1C1; border-radius:2px; padding:0.18rem 0.55rem; font-family:'IBM Plex Mono',monospace; font-size:0.685rem; letter-spacing:0.13em; text-transform:uppercase; color:#6E6759; margin-right:0.42rem; }
.mv-pill.pass{ color:#2F6B4F; border-color:#B7CEC0; }
.mv-pill.warn{ color:#B8862F; border-color:#E2CFA4; }
.mv-pill.fail{ color:#B4462F; border-color:#E3BDB1; }

[data-testid="stExpander"]{ border:1px solid #D8D1C1; border-radius:2px; background:#FBFAF7; }
hr{ border-color:#D8D1C1; }
</style>
"""