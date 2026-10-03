"""CSV ingest: column mapping, type coercion and validation reporting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# canonical field -> accepted source column names
ALIASES: dict[str, list[str]] = {
    "date": ["date", "appointment_date", "appt_date", "visit_date", "scheduled_date", "day"],
    "provider": ["provider", "provider_name", "clinician", "dentist", "therapist", "staff", "doctor"],
    "status": ["status", "appointment_status", "appt_status", "outcome", "state"],
    "revenue": ["revenue", "amount", "charge", "fee", "paid", "total", "billed", "payment"],
    "duration_min": ["duration_min", "duration", "length_min", "length", "appointment_length", "minutes"],
    "wait_min": ["wait_min", "wait", "wait_time", "waiting_time", "waiting_min", "delay_min"],
    "service": ["service", "procedure", "treatment", "visit_type", "appointment_type", "type"],
    "patient_ref": ["patient_ref", "patient_id", "patient", "pid", "client_id"],
    "hour": ["hour", "start_hour", "slot_hour"],
    "start_time": ["start_time", "time", "slot", "start"],
}

REQUIRED = ["date", "provider", "status"]
OPTIONAL = ["revenue", "duration_min", "wait_min", "service", "patient_ref", "hour", "start_time"]

STATUS_MAP = [
    (r"no[\s_\-]?show|noshow|missed|dna|did not attend|non[\s\-]?attendance", "no_show"),
    (r"cancel|cancell?ed", "cancelled"),
    (r"resched|re[\s\-]?book|rebook|postpon", "rescheduled"),
    (r"complete|attended|attend|kept|show|checked[\s\-]?in|confirm|done|closed", "kept"),
]

KNOWN_STATUS = ["kept", "cancelled", "no_show", "rescheduled"]


def normalize_name(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    return re.sub(r"_+", "_", s).strip("_")


def suggest_mapping(columns) -> dict[str, str | None]:
    normed = {normalize_name(c): c for c in columns}
    out: dict[str, str | None] = {}
    for field_name, aliases in ALIASES.items():
        found = None
        for alias in aliases:
            if alias in normed:
                found = normed[alias]
                break
        if found is None:
            for n, orig in normed.items():
                if any(alias in n or n in alias for alias in aliases):
                    found = orig
                    break
        out[field_name] = found
    return out


def normalize_status(series: pd.Series) -> pd.Series:
    def one(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "other"
        s = str(v).strip().lower()
        for pattern, label in STATUS_MAP:
            if re.search(pattern, s):
                return label
        return "other"

    return series.map(one)


def _to_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(r"[^\d.\-]", "", regex=True)
    cleaned = cleaned.replace({"": np.nan, "nan": np.nan, "None": np.nan, "-": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


@dataclass
class Check:
    name: str
    status: str  # pass | warn | fail
    detail: str


@dataclass
class ValidationReport:
    checks: list[Check] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def score(self) -> str:
        if self.errors:
            return "fail"
        if self.warnings:
            return "warn"
        return "pass"

    def add(self, name: str, status: str, detail: str) -> None:
        self.checks.append(Check(name, status, detail))
        if status == "warn":
            self.warnings.append(detail)
        elif status == "fail":
            self.errors.append(detail)


def build_dataset(raw: pd.DataFrame, mapping: dict[str, str | None]) -> tuple[pd.DataFrame | None, ValidationReport]:
    report = ValidationReport()

    missing = [f for f in REQUIRED if not mapping.get(f)]
    if missing:
        report.add("Required columns", "fail", f"Not mapped: {', '.join(missing)}. A dashboard cannot be built without these.")
        return None, report
    report.add("Required columns", "pass", "date, provider and status are all mapped.")

    cols = {f: c for f, c in mapping.items() if c}
    df = pd.DataFrame({f: raw[c] for f, c in cols.items()})
    report.add("Row count", "pass", f"{len(df):,} rows read from the source file.")

    # ---- date ---------------------------------------------------------
    parsed = pd.to_datetime(df["date"], errors="coerce")
    ok_pct = float(parsed.notna().mean())
    if ok_pct < 0.98:
        report.add("Date parsing", "warn" if ok_pct > 0.8 else "fail",
                   f"{ok_pct * 100:.1f}% of dates parsed successfully. Unparseable rows are dropped.")
    else:
        report.add("Date parsing", "pass", f"{ok_pct * 100:.1f}% of dates parsed successfully.")
    df["date"] = parsed
    df = df[df["date"].notna()].copy()

    if df.empty:
        report.add("Usable rows", "fail", "No rows survived date parsing.")
        return None, report

    # ---- status -------------------------------------------------------
    raw_status = df["status"]
    df["status"] = normalize_status(raw_status)
    recognised = float((df["status"] != "other").mean())
    if recognised < 0.9:
        unknown = raw_status[df["status"] == "other"].astype(str).str.strip().unique()[:6]
        report.add("Status vocabulary", "warn",
                   f"{recognised * 100:.1f}% of status values recognised. Unmapped values: {', '.join(map(str, unknown)) or '—'}.")
    else:
        report.add("Status vocabulary", "pass",
                   f"{recognised * 100:.1f}% of status values mapped to kept / cancelled / no-show / rescheduled.")

    # ---- numeric fields ----------------------------------------------
    for name in ("revenue", "duration_min", "wait_min"):
        if name in df.columns:
            coerced = _to_numeric(df[name])
            before = coerced.notna().sum()
            df[name] = coerced
            pct = before / max(len(df), 1)
            if pct < 0.5:
                report.add(f"{name} numeric", "warn", f"Only {pct * 100:.1f}% of {name} values are numeric.")
            else:
                report.add(f"{name} numeric", "pass", f"{pct * 100:.1f}% of {name} values parsed as numbers.")
            if (coerced.dropna() < 0).any():
                report.add(f"{name} negatives", "warn", "Negative values found; they are excluded from averages.")
                df.loc[df[name] < 0, name] = np.nan

    for name in REQUIRED + OPTIONAL:
        if name not in df.columns:
            if name in REQUIRED:
                continue
            report.notes.append(f"'{name}' was not provided — related charts will be omitted.")
            df[name] = np.nan

    # ---- derived ------------------------------------------------------
    if df["hour"].isna().all() and df["start_time"].notna().any():
        df["hour"] = pd.to_datetime(df["start_time"].astype(str), format="%H:%M", errors="coerce").dt.hour
    elif df["hour"].notna().any():
        df["hour"] = pd.to_numeric(df["hour"], errors="coerce")

    if df["duration_min"].isna().all() is False:
        pass
    else:
        report.add("Duration", "warn", "No duration column — utilisation is estimated at 30 minutes per kept visit.")
        df["duration_min"] = np.where(df["status"] == "kept", 30.0, np.nan)

    # ---- integrity ----------------------------------------------------
    if "appointment_id" not in df.columns:
        df.insert(0, "appointment_id", [f"ROW-{i:06d}" for i in range(len(df))])
    dupes = int(df["appointment_id"].duplicated().sum())
    if dupes:
        report.add("Duplicate ids", "warn", f"{dupes:,} duplicate identifiers found.")
    else:
        report.add("Duplicate ids", "pass", "No duplicate row identifiers.")

    future = int((df["date"] > pd.Timestamp.now() + pd.Timedelta(days=365)).sum())
    if future:
        report.add("Future dates", "warn", f"{future:,} rows are dated more than a year ahead.")
    else:
        report.add("Future dates", "pass", "No implausible future dates.")

    report.add("Date coverage", "pass",
               f"{df['date'].min():%d %b %Y} → {df['date'].max():%d %b %Y} ({df['date'].nunique():,} distinct days).")

    if not mapping.get("revenue"):
        report.add("PHI check", "warn",
                   "Confirm this file contains no names, contact details or clinical notes before using it here.")
    else:
        report.add("PHI check", "pass",
                   "Structurally, the file looks de-identified. Confirm before using any real data.")

    return df.reset_index(drop=True), report