"""Metric computation. Every function takes the canonical appointment DataFrame."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AVAILABLE_MINUTES

WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def filter_period(df, start, end, providers=None) -> pd.DataFrame:
    out = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
    if providers:
        out = out[out["provider"].isin(providers)]
    return out


def summary(df: pd.DataFrame) -> dict:
    n = len(df)
    status = df["status"]
    kept = int((status == "kept").sum())
    no_show = int((status == "no_show").sum())
    cancelled = int((status == "cancelled").sum())
    rescheduled = int((status == "rescheduled").sum())
    scheduled = kept + no_show + cancelled + rescheduled

    kept_mask = status == "kept"
    revenue = float(pd.to_numeric(df.loc[kept_mask, "revenue"], errors="coerce").fillna(0).sum())
    wait = pd.to_numeric(df.loc[kept_mask, "wait_min"], errors="coerce").dropna()
    days = max(int(df["date"].nunique()), 1)

    return {
        "rows": n,
        "appointments": scheduled,
        "kept": kept,
        "no_show": no_show,
        "cancelled": cancelled,
        "rescheduled": rescheduled,
        "no_show_rate": (no_show / scheduled) if scheduled else 0.0,
        "cancel_rate": (cancelled / scheduled) if scheduled else 0.0,
        "kept_rate": (kept / scheduled) if scheduled else 0.0,
        "revenue": revenue,
        "revenue_per_visit": (revenue / kept) if kept else 0.0,
        "wait_median": float(wait.median()) if len(wait) else None,
        "wait_p90": float(wait.quantile(0.90)) if len(wait) else None,
        "providers": int(df["provider"].nunique()),
        "days": days,
        "per_day": scheduled / days,
        "has_revenue": bool(pd.to_numeric(df["revenue"], errors="coerce").notna().any()) if "revenue" in df else False,
        "has_wait": bool(len(wait) > 0),
        "has_duration": bool(pd.to_numeric(df["duration_min"], errors="coerce").notna().any()) if "duration_min" in df else False,
        "has_hour": bool(pd.to_numeric(df["hour"], errors="coerce").notna().any()) if "hour" in df else False,
    }


def compare(current: dict, previous: dict, keys: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for k in keys:
        a, b = current.get(k), previous.get(k)
        if a is None or b is None or b == 0:
            out[k] = None
        else:
            out[k] = (a - b) / abs(b)
    return out


def volume_by_week(df: pd.DataFrame) -> pd.DataFrame:
    x = df.set_index("date")
    g = x.groupby([pd.Grouper(freq="W-MON"), "status"]).size().unstack(fill_value=0)
    for c in ("kept", "cancelled", "no_show", "rescheduled"):
        if c not in g.columns:
            g[c] = 0
    g = g[["kept", "cancelled", "no_show", "rescheduled"]]
    g["total"] = g.sum(axis=1)
    return g[g["total"] > 0]


def rates_by_week(df: pd.DataFrame) -> pd.DataFrame:
    g = volume_by_week(df).copy()
    g["no_show_rate"] = np.where(g["total"] > 0, g["no_show"] / g["total"], 0.0)
    g["cancel_rate"] = np.where(g["total"] > 0, g["cancelled"] / g["total"], 0.0)
    g["kept_rate"] = np.where(g["total"] > 0, g["kept"] / g["total"], 0.0)
    return g


def utilization(df: pd.DataFrame) -> pd.DataFrame:
    days = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    avail_minutes = float(sum(AVAILABLE_MINUTES.get(d.weekday(), 0) for d in days))
    kept = df[df["status"] == "kept"]
    booked = kept.groupby("provider")["duration_min"].sum(min_count=1).fillna(0)
    visits = kept.groupby("provider").size()

    rows = []
    for provider in sorted(df["provider"].dropna().unique()):
        b = float(booked.get(provider, 0.0))
        rows.append(
            {
                "provider": provider,
                "booked_hours": b / 60.0,
                "available_hours": avail_minutes / 60.0,
                "utilization": (b / avail_minutes) if avail_minutes else 0.0,
                "visits": int(visits.get(provider, 0)),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values("utilization").reset_index(drop=True) if not out.empty else out


def revenue_by_provider(df: pd.DataFrame) -> pd.DataFrame:
    kept = df[df["status"] == "kept"].copy()
    kept["revenue"] = pd.to_numeric(kept["revenue"], errors="coerce").fillna(0)
    g = kept.groupby("provider").agg(revenue=("revenue", "sum"), visits=("revenue", "size"))
    g["revenue_per_visit"] = np.where(g["visits"] > 0, g["revenue"] / g["visits"], 0.0)
    total = float(g["revenue"].sum())
    g["share"] = np.where(total > 0, g["revenue"] / total, 0.0)
    return g.reset_index().sort_values("revenue", ascending=False).reset_index(drop=True)


def revenue_by_week(df: pd.DataFrame) -> pd.DataFrame:
    kept = df[df["status"] == "kept"].copy()
    kept["revenue"] = pd.to_numeric(kept["revenue"], errors="coerce").fillna(0)
    kept = kept.set_index("date")
    g = kept.groupby(pd.Grouper(freq="W-MON")).agg(revenue=("revenue", "sum"), visits=("revenue", "size"))
    g["revenue_per_visit"] = np.where(g["visits"] > 0, g["revenue"] / g["visits"], 0.0)
    return g[g["visits"] > 0]


def flow_matrix(df: pd.DataFrame) -> pd.DataFrame:
    kept = df[df["status"] == "kept"].copy()
    if kept["hour"].isna().all():
        return pd.DataFrame()
    kept["hour"] = pd.to_numeric(kept["hour"], errors="coerce")
    kept = kept.dropna(subset=["hour"])
    kept["weekday"] = pd.Categorical(kept["date"].dt.strftime("%a"), categories=WEEKDAY_ORDER, ordered=True)
    m = kept.pivot_table(index="hour", columns="weekday", values="appointment_id", aggfunc="count", fill_value=0)
    return m


def wait_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    kept = df[df["status"] == "kept"].copy()
    if kept["hour"].isna().all():
        return pd.DataFrame()
    kept["hour"] = pd.to_numeric(kept["hour"], errors="coerce")
    w = pd.to_numeric(kept["wait_min"], errors="coerce")
    kept = kept.assign(wait_min=w).dropna(subset=["hour", "wait_min"])
    if kept.empty:
        return pd.DataFrame()
    g = kept.groupby("hour").agg(median_wait=("wait_min", "median"), visits=("wait_min", "size"))
    return g.reset_index()


def busiest_hours(df: pd.DataFrame, top: int = 3) -> list[int]:
    m = flow_matrix(df)
    if m.empty:
        return []
    totals = m.sum(axis=1).sort_values(ascending=False)
    return [int(h) for h in totals.head(top).index.tolist()]


def service_mix(df: pd.DataFrame, top: int = 6) -> pd.DataFrame:
    kept = df[df["status"] == "kept"].copy()
    kept["revenue"] = pd.to_numeric(kept["revenue"], errors="coerce").fillna(0)
    g = kept.groupby("service").agg(visits=("revenue", "size"), revenue=("revenue", "sum"))
    g["revenue_per_visit"] = np.where(g["visits"] > 0, g["revenue"] / g["visits"], 0.0)
    return g.reset_index().sort_values("revenue", ascending=False).head(top).reset_index(drop=True)


def weekly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly frame with volumes, rates, revenue and wait -- the anomaly engine's input."""
    g = rates_by_week(df)

    kept = df[df["status"] == "kept"].copy()
    if kept.empty:
        g["revenue"] = 0.0
        g["visits"] = 0.0
        g["revenue_per_visit"] = 0.0
        g["wait_median"] = float("nan")
        return g

    kept["revenue"] = pd.to_numeric(kept["revenue"], errors="coerce").fillna(0.0)
    kept["wait_min"] = pd.to_numeric(kept["wait_min"], errors="coerce")
    kept = kept.set_index("date")
    r = kept.groupby(pd.Grouper(freq="W-MON")).agg(
        revenue=("revenue", "sum"), visits=("revenue", "size")
    )
    w = kept.groupby(pd.Grouper(freq="W-MON"))["wait_min"].median()

    g["revenue"] = r["revenue"].reindex(g.index).fillna(0.0)
    g["visits"] = r["visits"].reindex(g.index).fillna(0.0)
    g["revenue_per_visit"] = np.where(g["visits"] > 0, g["revenue"] / g["visits"], 0.0)
    g["wait_median"] = w.reindex(g.index).astype(float)
    return g
