"""MedVisor Dashboard — Streamlit proof of concept."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from medvisor import synth
from medvisor import anomalies, charts, config, export, insights, metrics, schema
from medvisor.config import CSS, fmt_delta, fmt_money, fmt_num, fmt_pct

st.set_page_config(
    page_title="MedVisor Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------- helpers --
def hero() -> None:
    st.markdown(
        """
        <div class="mv-hero">
          <div class="mv-eyebrow">MedVisor &nbsp;/&nbsp; Clinic operations intelligence</div>
          <div class="mv-stamp-wrap">
            <div class="mv-stamp">
              <div class="big">PROOF OF CONCEPT</div>
              <div class="small">NOT PRODUCTION · NOT A MEDICAL DEVICE</div>
            </div>
          </div>
          <h1>Messy clinic data,<br>turned into decisions.</h1>
          <div class="mv-kicker">Two layers: a dashboard that answers real questions, and a consulting layer that says what to do next.</div>
          <p class="mv-lede">
            Small and mid-size clinics run on spreadsheets, exported CSVs and gut feeling. Everyone knows something is
            wrong with no-shows, utilisation or revenue — but nobody has time to clean the data, let alone read a dashboard.
            MedVisor is the lightweight pipeline in between: drop in a CSV, get the metrics, the anomalies and the notes.
          </p>
        </div>
        <div class="mv-strip">
          <span><b>Status</b> Proof of concept</span>
          <span><b>Data</b> Synthetic / de-identified only</span>
          <span><b>Compliance</b> No HIPAA / GDPR / LGPD claim</span>
          <span><b>Next gate</b> Paid pilot</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def exhibit(num: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="mv-exhibit"><div class="num">{num}</div><h2>{title}</h2><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def ledger(rows: list[tuple[str, str, str, str]]) -> None:
    html = ['<div class="mv-ledger">']
    for label, value, cmp_text, direction in rows:
        cls = {"up": "mv-up", "down": "mv-down", "flat": "mv-flat"}[direction]
        html.append(
            f'<div class="mv-row"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>'
            f'<div class="cmp {cls}">{cmp_text}</div></div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def set_window(days: int) -> None:
    df = st.session_state.get("mv_df")
    if df is None:
        return
    max_d = df["date"].max().date()
    min_d = df["date"].min().date()
    start = max(min_d, max_d - timedelta(days=days - 1))
    st.session_state["period"] = (start, max_d)


@st.cache_data(show_spinner=False)
def load_demo(seed: int, days: int, appts: int) -> pd.DataFrame:
    return synth.generate(seed=seed, days=days, appts_per_day=appts)


# ------------------------------------------------------------- session init --
if "mv_df" not in st.session_state:
    st.session_state["mv_df"] = load_demo(7, 260, 42)
    st.session_state["mv_report"] = None
    st.session_state["mv_source"] = "Synthetic demo data"
    st.session_state["mv_raw"] = None

hero()
st.markdown("")


# ------------------------------------------------------------------ sidebar --
with st.sidebar:
    st.markdown("### Data source")
    source = st.radio("Choose", ["Synthetic demo data", "Upload a CSV"], label_visibility="collapsed")

    if source == "Synthetic demo data":
        with st.expander("Generator settings", expanded=False):
            seed = st.number_input("Random seed", min_value=1, max_value=9999, value=7, step=1)
            days = st.slider("Days of history", min_value=90, max_value=400, value=260, step=10)
            appts = st.slider("Appointments / day", min_value=10, max_value=120, value=42, step=2)
            if st.button("Regenerate dataset"):
                st.session_state["mv_df"] = load_demo(int(seed), int(days), int(appts))
                st.session_state["mv_report"] = None
                st.session_state["mv_source"] = "Synthetic demo data"
                st.session_state["mv_raw"] = None
                st.session_state.pop("period", None)
                st.rerun()
        st.caption("All rows are fabricated. No patient information is used or intended.")
    else:
        uploaded = st.file_uploader("CSV file", type=["csv"], help="Do not upload real patient data.")
        if uploaded is not None:
            st.session_state["mv_raw"] = pd.read_csv(uploaded)

        raw = st.session_state.get("mv_raw")
        if raw is not None:
            st.caption(f"{len(raw):,} rows · {raw.shape[1]} columns detected")
            suggested = schema.suggest_mapping(raw.columns)
            st.markdown("#### Column mapping")
            options = ["— not mapped —"] + list(map(str, raw.columns))
            mapping: dict[str, str | None] = {}
            for field in schema.REQUIRED + schema.OPTIONAL:
                guess = suggested.get(field)
                index = options.index(guess) if guess in options else 0
                choice = st.selectbox(field, options, index=index, key=f"map_{field}")
                mapping[field] = None if choice == "— not mapped —" else choice

            if st.button("Build dashboard from file"):
                df, report = schema.build_dataset(raw, mapping)
                if df is None:
                    st.session_state["mv_report"] = report
                else:
                    st.session_state["mv_df"] = df
                    st.session_state["mv_report"] = report
                    st.session_state["mv_source"] = "Uploaded CSV"
                    st.session_state.pop("period", None)
                    st.rerun()
        else:
            st.info("Upload a CSV to replace the demo dataset. Required columns: date, provider, status.")

    st.markdown("---")
    st.markdown("### Period")
    df_all = st.session_state["mv_df"]
    min_d = df_all["date"].min().date()
    max_d = df_all["date"].max().date()

    c1, c2, c3 = st.columns(3)
    c1.button("30d", on_click=set_window, args=(30,), use_container_width=True)
    c2.button("90d", on_click=set_window, args=(90,), use_container_width=True)
    c3.button("180d", on_click=set_window, args=(180,), use_container_width=True)

    raw_period = st.date_input("Window", value=(min_d, max_d), min_value=min_d, max_value=max_d, key="period")
    if isinstance(raw_period, (list, tuple)) and len(raw_period) == 2 and all(raw_period):
        p_start, p_end = raw_period
    else:
        p_start, p_end = min_d, max_d

    providers = sorted(df_all["provider"].dropna().astype(str).unique())
    selected = st.multiselect("Providers", providers, default=providers)

    st.markdown("---")
    st.markdown("### Export")
    st.caption("The report below is rendered to PDF and PNG locally. Nothing leaves this machine.")
    st.markdown(
        f'<div class="mv-kv">Source<br>{st.session_state["mv_source"]}<br><br>Rows loaded<br>{len(df_all):,}</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------- data --
current = metrics.filter_period(st.session_state["mv_df"], p_start, p_end, selected)
span = (pd.Timestamp(p_end) - pd.Timestamp(p_start)).days + 1
prev_end = pd.Timestamp(p_start) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=span - 1)
previous = metrics.filter_period(st.session_state["mv_df"], prev_start, prev_end, selected)

if current.empty:
    st.markdown('<div class="mv-warn">No rows fall inside this window. Widen the period or re-enable a provider.</div>', unsafe_allow_html=True)
    st.stop()

now = metrics.summary(current)
prev = metrics.summary(previous) if not previous.empty else {k: 0 for k in now}
delta = metrics.compare(
    now,
    prev,
    ["appointments", "kept", "no_show_rate", "cancel_rate", "revenue", "revenue_per_visit", "wait_median"],
)

weekly = metrics.weekly_metrics(current)
volume = metrics.volume_by_week(current)
util = metrics.utilization(current)
rev = metrics.revenue_by_provider(current) if now["has_revenue"] else pd.DataFrame()
rev_week = metrics.revenue_by_week(current) if now["has_revenue"] else pd.DataFrame()
flow = metrics.flow_matrix(current)
wait = metrics.wait_by_hour(current) if now["has_wait"] else pd.DataFrame()
busiest = metrics.busiest_hours(current)
mix = metrics.service_mix(current) if "service" in current.columns else pd.DataFrame()

flags = anomalies.run_all(now, prev, weekly, util)
top_service = mix if not mix.empty else None
findings = insights.build(now, prev, delta, flags, util, flow, busiest, top_service)
exec_summary = insights.executive_summary(now, prev, flags, findings)

window_label = f"{pd.Timestamp(p_start):%d %b %Y} – {pd.Timestamp(p_end):%d %b %Y} ({span} days)"


# ------------------------------------------------------------------ exports --
def build_context() -> export.ReportContext:
    return export.ReportContext(
        clinic="Demo clinic (synthetic)",
        window_label=window_label,
        generated_at=export.now_label(),
        summary=now,
        prev_summary=prev,
        volume=volume,
        rates=weekly,
        utilization=util,
        revenue=rev,
        revenue_weekly=rev_week,
        flags=flags,
        insights=findings,
        exec_summary=exec_summary,
        validation=st.session_state.get("mv_report"),
    )


ctx = build_context()
pages = export.build_pages(ctx)
pdf_bytes = export.to_pdf(list(pages))
png_bytes = export.to_png(pages[0])
pages = None

st.sidebar.download_button("Download PDF report", data=pdf_bytes,
                           file_name="medvisor_report.pdf", mime="application/pdf")
st.sidebar.download_button("Download summary PNG", data=png_bytes,
                           file_name="medvisor_summary.png", mime="image/png")


# ------------------------------------------------------------- glance block --
exhibit("Section 01", "Period at a glance", "The five numbers a clinic owner actually asks for.")

rows = [
    ("Scheduled appointments", fmt_num(now["appointments"]), f"{fmt_delta(delta['appointments'])[0]} vs previous", fmt_delta(delta["appointments"])[1]),
    ("Kept visits", fmt_num(now["kept"]), f"{fmt_delta(delta['kept'])[0]} vs previous", fmt_delta(delta["kept"])[1]),
    ("No-show rate", fmt_pct(now["no_show_rate"]), f"{fmt_delta(delta['no_show_rate'])[0]} vs previous", "up" if (delta.get("no_show_rate") or 0) > 0 else "down"),
    ("Cancellation rate", fmt_pct(now["cancel_rate"]), f"{fmt_delta(delta['cancel_rate'])[0]} vs previous", "up" if (delta.get("cancel_rate") or 0) > 0 else "down"),
    ("Median wait (kept visits)", f"{fmt_num(now['wait_median'])} min", f"p90 {fmt_num(now.get('wait_p90'))} min", "flat"),
]
if now["has_revenue"]:
    rows += [
        ("Revenue from kept visits", fmt_money(now["revenue"]), f"{fmt_delta(delta['revenue'])[0]} vs previous", fmt_delta(delta["revenue"])[1]),
        ("Revenue per visit", fmt_money(now["revenue_per_visit"]), f"{fmt_delta(delta['revenue_per_visit'])[0]} vs previous", fmt_delta(delta["revenue_per_visit"])[1]),
    ]
ledger(rows)

c1, c2, c3, c4 = st.columns(4)
c1.caption(f"Providers in scope — {now['providers']}")
c2.caption(f"Active days — {fmt_num(now['days'])}")
c3.caption(f"Appointments / active day — {fmt_num(now['per_day'], 1)}")
c4.caption(f"Comparison window — {prev_start:%d %b} – {prev_end:%d %b}")


# --------------------------------------------------------------- exhibit 01 --
exhibit("Exhibit 01", "Appointment volume over time",
        "Weekly, stacked by outcome. The dotted line is the trailing three-week kept-visit trend.")
st.plotly_chart(charts.chart_volume(volume), use_container_width=True, config={"displayModeBar": False})


# --------------------------------------------------------------- exhibit 02 --
exhibit("Exhibit 02", "No-show and cancellation rate",
        "Share of scheduled appointments, against the 8% reference for this clinic type.")
lc, rc = st.columns([2, 1])
with lc:
    st.plotly_chart(charts.chart_rates(weekly), use_container_width=True, config={"displayModeBar": False})
with rc:
    st.markdown(
        f"""
        <div class="mv-ledger">
          <div class="mv-row"><div class="lbl">No-show rate</div><div class="val">{fmt_pct(now['no_show_rate'])}</div><div class="cmp mv-flat">ref 8.0%</div></div>
          <div class="mv-row"><div class="lbl">Cancellation rate</div><div class="val">{fmt_pct(now['cancel_rate'])}</div><div class="cmp mv-flat">ref 10.0%</div></div>
          <div class="mv-row"><div class="lbl">Missed appointments</div><div class="val">{fmt_num(now['no_show'])}</div><div class="cmp mv-flat">this window</div></div>
          <div class="mv-row"><div class="lbl">Released by cancellation</div><div class="val">{fmt_num(now['cancelled'])}</div><div class="cmp mv-flat">slot freed</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------- exhibit 03 --
exhibit("Exhibit 03", "Provider utilisation",
        "Booked clinical minutes divided by assumed availability — 7h weekdays, 4h Saturday.")
if not util.empty:
    lc, rc = st.columns([2, 1])
    with lc:
        st.plotly_chart(charts.chart_utilization(util), use_container_width=True, config={"displayModeBar": False})
    with rc:
        avg_u = float(util["utilization"].mean())
        best = util.iloc[-1]
        worst = util.iloc[0]
        st.markdown(
            f"""
            <div class="mv-ledger">
              <div class="mv-row"><div class="lbl">Clinic average</div><div class="val">{fmt_pct(avg_u)}</div><div class="cmp mv-flat">target 80%</div></div>
              <div class="mv-row"><div class="lbl">Highest</div><div class="val">{fmt_pct(best['utilization'])}</div><div class="cmp mv-flat">{best['provider']}</div></div>
              <div class="mv-row"><div class="lbl">Lowest</div><div class="val">{fmt_pct(worst['utilization'])}</div><div class="cmp mv-flat">{worst['provider']}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------- exhibit 04 --
if now["has_revenue"] and not rev.empty:
    exhibit("Exhibit 04", "Revenue per visit and per provider",
            "Bars are total billings from kept visits. The diamond line is revenue per visit.")
    lc, rc = st.columns(2)
    with lc:
        st.plotly_chart(charts.chart_revenue(rev), use_container_width=True, config={"displayModeBar": False})
    with rc:
        st.plotly_chart(charts.chart_revenue_trend(rev_week), use_container_width=True, config={"displayModeBar": False})


# --------------------------------------------------------------- exhibit 05 --
exhibit("Exhibit 05", "Patient flow and wait patterns",
        "Where the day fills up, and where patients end up waiting.")
lc, rc = st.columns(2)
with lc:
    if not flow.empty:
        st.plotly_chart(charts.chart_flow(flow), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No start-time information in this file.")
with rc:
    if not wait.empty:
        st.plotly_chart(charts.chart_wait(wait), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No wait-time information in this file.")

if not mix.empty:
    with st.expander("Service mix (kept visits)"):
        st.dataframe(
            mix.assign(
                revenue=mix["revenue"].map(lambda v: fmt_money(v)),
                revenue_per_visit=mix["revenue_per_visit"].map(lambda v: fmt_money(v)),
            ),
            use_container_width=True,
            hide_index=True,
        )


# ------------------------------------------------------------------- flags --
exhibit("Section 02", "Automatic anomaly flags",
        "Period-over-period movement, checked against each metric's own recent range.")

if not flags:
    st.markdown('<div class="mv-flag ok"><div class="tag" style="color:#2F6B4F">All clear</div>'
                "<h4>Nothing moved far enough to flag</h4>"
                "<p>Every tracked metric stayed inside its recent range for this window. That is a result, not an absence of one.</p></div>",
                unsafe_allow_html=True)
else:
    cols = st.columns(2)
    for i, f in enumerate(flags):
        tone = "mv-flag" if f.severity == "alert" else ("mv-flag watch" if f.severity == "watch" else "mv-flag ok")
        color = "#B4462F" if f.severity == "alert" else ("#B8862F" if f.severity == "watch" else "#2F6B4F")
        html = (
            f'<div class="{tone}"><div class="tag" style="color:{color}">{f.severity} · {f.window}</div>'
            f"<h4>{f.title}</h4><p>{f.detail}"
            + (f" {f.benchmark_note}" if f.benchmark_note else "")
            + "</p></div>"
        )
        cols[i % 2].markdown(html, unsafe_allow_html=True)


# --------------------------------------------------------------- consulting --
exhibit("Section 03", "Insight summary and recommended actions",
        "The consulting layer: what changed, why it matters, and the next move.")

st.markdown(f'<div class="mv-note">{exec_summary}</div>', unsafe_allow_html=True)
st.markdown("")

cols = st.columns(2)
for i, ins in enumerate(findings):
    html = (
        f'<div class="mv-insight"><div class="idx">Finding {i + 1:02d} · {ins["tag"]}</div>'
        f'<h4>{ins["headline"]}</h4><p>{ins["body"]}</p>'
        f'<div class="act"><b>Recommended action</b>{ins["action"]}</div></div>'
    )
    cols[i % 2].markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------- quality --
report = st.session_state.get("mv_report")
exhibit("Section 04", "Data quality and validation", "What the ingest layer found in the file it was given.")

if report is None:
    st.markdown(
        '<div class="mv-quiet">This dataset was produced by the built-in synthetic generator, so it is internally consistent '
        'by construction. Upload a CSV to see the validation report — column mapping, type coercion, status vocabulary and '
        "PHI screening.</div>",
        unsafe_allow_html=True,
    )
else:
    if report.errors:
        st.markdown(f'<div class="mv-warn"><b>Build failed.</b> {" ".join(report.errors)}</div>', unsafe_allow_html=True)
    badges = "".join(
        f'<span class="mv-pill {c.status}">{c.status} · {c.name}</span>' for c in report.checks
    )
    st.markdown(badges, unsafe_allow_html=True)
    st.markdown("")
    lines = [f"**{c.name}** — {c.detail}" for c in report.checks]
    st.markdown('<div class="mv-kv">' + "<br>".join(lines) + "</div>", unsafe_allow_html=True)
    if report.notes:
        st.markdown("")
        st.markdown('<div class="mv-quiet">' + "<br>".join(report.notes) + "</div>", unsafe_allow_html=True)


# ------------------------------------------------------------- compliance --
exhibit("Section 05", "Compliance & PHI policy", "Read this before using any real data.")
st.markdown(
    """
<div class="mv-warn">
<b>This is an early proof of concept built to validate one question:</b> will clinics pay for dashboards plus consulting
that turn their messy operational data into decisions? It is not ready for real patient data. It ships with synthetic and
de-identified sample data only. No HIPAA, GDPR or LGPD compliance is claimed, and nothing here should be treated as a
medical device. Do not upload real patient data into this build.
</div>
""",
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Current features")
    st.markdown(
        """
- CSV ingest with column mapping and validation
- Appointment volume over time
- No-show and cancellation rate
- Provider utilisation
- Revenue per visit / per provider
- Patient flow and wait patterns
- Automatic anomaly flags
- Auto-generated insight summary per period
- Export to PDF / PNG for clinic owners
- Synthetic data generator for demos and testing
"""
    )
with c2:
    st.markdown("#### Not built yet (intentionally)")
    st.markdown(
        """
- EHR integrations (Epic, Cerner, Athena)
- Multi-tenant auth / user accounts
- Real PHI handling
- Any ML forecasting

*These are expensive. They come after someone pays for a pilot.*
"""
    )

st.markdown("---")
st.markdown(
    '<div class="mv-quiet">MedVisor PoC 0.1.0 · Built with Streamlit, pandas, plotly and matplotlib · '
    "All figures on this page are derived from synthetic or de-identified sample data.</div>",
    unsafe_allow_html=True,
)