"""Synthetic clinic dataset generator.

Produces realistic-but-fake appointment-level data for demos and testing.
No real patient information is used or intended. Run as a module:

    python -m medvisor.synth --out sample_clinic.csv
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

PROVIDERS = [
    ("Dr. Almeida", "Dental", 1.00, (0, 1, 2, 3, 4)),
    ("Dr. Benitez", "Dental", 0.92, (0, 1, 2, 3, 4)),
    ("Dr. Chandra", "Dental", 0.78, (0, 1, 3, 4)),
    ("K. Duarte, PT", "Physio", 1.00, (0, 1, 2, 3, 4, 5)),
    ("M. Ellis, PT", "Physio", 0.72, (1, 2, 3, 4, 5)),
    ("Dr. Faber", "Dental", 0.46, (2, 3, 4)),
]

SERVICES = [
    ("Hygiene recall", 45, 135, 0.30),
    ("Exam & imaging", 25, 95, 0.20),
    ("Filling", 45, 215, 0.14),
    ("Root canal", 80, 640, 0.05),
    ("Crown fit", 65, 910, 0.05),
    ("Physio assessment", 55, 155, 0.10),
    ("Physio session", 40, 105, 0.13),
    ("Follow-up consult", 20, 70, 0.03),
]

PAYERS = ["Private", "Insurance", "Corporate plan", "Public scheme"]
PAYER_WEIGHTS = [0.34, 0.41, 0.16, 0.09]
PAYER_FACTOR = {"Private": 1.00, "Insurance": 0.86, "Corporate plan": 0.78, "Public scheme": 0.62}

WEEKDAY_FACTOR = np.array([1.14, 1.06, 1.02, 1.05, 0.90, 0.52, 0.0])
HOUR_WEIGHTS = np.array([0.03, 0.10, 0.13, 0.12, 0.08, 0.05, 0.11, 0.13, 0.11, 0.06])
HOURS = np.arange(8, 18)


def generate(
    start: str = "2025-01-06",
    days: int = 260,
    appts_per_day: int = 42,
    n_patients: int = 2200,
    seed: int = 7,
) -> pd.DataFrame:
    """Generate an appointment-level DataFrame for one demo clinic."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=days, freq="D")
    weekday = dates.weekday

    # gentle growth + noise in daily volume
    trend = np.linspace(1.0, 1.16, days)
    counts = rng.poisson(appts_per_day * WEEKDAY_FACTOR[weekday] * trend)

    day_index, provider_names, services, payers = [], [], [], []
    hours, minutes, patients = [], [], []

    prov_names = [p[0] for p in PROVIDERS]
    prov_weights = np.array([p[2] for p in PROVIDERS])
    prov_weights = prov_weights / prov_weights.sum()
    svc_names = [s[0] for s in SERVICES]
    svc_weights = np.array([s[3] for s in SERVICES])
    svc_weights = svc_weights / svc_weights.sum()

    for d, (date, n) in enumerate(zip(dates, counts)):
        if n == 0:
            continue
        open_providers = [i for i, p in enumerate(PROVIDERS) if weekday[d] in p[3]]
        if not open_providers:
            continue
        w = prov_weights[open_providers]
        w = w / w.sum()
        p_idx = rng.choice(open_providers, size=n, p=w)
        s_idx = rng.choice(len(svc_names), size=n, p=svc_weights)

        day_index.extend([d] * n)
        provider_names.extend([prov_names[i] for i in p_idx])
        services.extend([svc_names[i] for i in s_idx])
        payers.extend(rng.choice(PAYERS, size=n, p=PAYER_WEIGHTS))

        h = rng.choice(HOURS, size=n, p=HOUR_WEIGHTS / HOUR_WEIGHTS.sum())
        hours.extend(h.tolist())
        minutes.extend(rng.integers(0, 60, size=n).tolist())
        # returning patients are common
        patients.extend(rng.integers(1000, 1000 + n_patients, size=n).tolist())

    n_total = len(day_index)
    day_index = np.array(day_index)
    hours_arr = np.array(hours)

    # ---- status model -------------------------------------------------
    p_noshow = np.full(n_total, 0.061)
    p_noshow += 0.021 * ((hours_arr >= 15).astype(float))       # late slots riskier
    p_noshow += 0.014 * ((hours_arr <= 9).astype(float))         # early slots too

    # injected operational regression used to demo anomaly detection
    spike_a, spike_b = int(days * 0.56), int(days * 0.71)
    in_spike = (day_index >= spike_a) & (day_index <= spike_b)
    p_noshow = p_noshow + in_spike * 0.082

    p_cancel = np.full(n_total, 0.082)
    p_resched = np.full(n_total, 0.041)
    p_cancel += 0.018 * ((day_index == 0).astype(float))

    u = rng.random(n_total)
    cum1 = p_noshow
    cum2 = cum1 + p_cancel
    cum3 = cum2 + p_resched
    status = np.where(
        u < cum1, "no_show",
        np.where(u < cum2, "cancelled", np.where(u < cum3, "rescheduled", "kept")),
    )

    # ---- duration, wait, revenue -------------------------------------
    svc_duration = {s[0]: s[1] for s in SERVICES}
    svc_price = {s[0]: s[2] for s in SERVICES}
    base_duration = np.array([svc_duration[s] for s in services], dtype=float)
    duration = np.clip(base_duration + rng.normal(0, 7, n_total), 8, None)

    afternoon = (hours_arr >= 13).astype(float)
    creep = np.clip((day_index - days * 0.62) / (days * 0.38), 0, 1) * 9.0
    wait = np.clip(
        6.5 + 5.2 * afternoon + creep + rng.gamma(1.7, 3.1, n_total) - 4.0, 0, None
    )

    price = np.array([svc_price[s] for s in services], dtype=float)
    payer_mult = np.array([PAYER_FACTOR[p] for p in payers])
    noise = rng.normal(1.0, 0.075, n_total)
    revenue = price * payer_mult * noise
    revenue = np.where(status == "kept", revenue, np.where(status == "cancelled", revenue * 0.12, 0.0))

    day_of = dates[day_index]
    start_ts = [
        pd.Timestamp(d) + pd.Timedelta(hours=int(h), minutes=int(m))
        for d, h, m in zip(day_of, hours_arr, minutes)
    ]

    df = pd.DataFrame(
        {
            "appointment_id": [f"APT-{i:06d}" for i in range(n_total)],
            "date": day_of,
            "start_time": [ts.strftime("%H:%M") for ts in start_ts],
            "hour": hours_arr,
            "provider": provider_names,
            "service": services,
            "status": status,
            "duration_min": np.round(duration, 1),
            "wait_min": np.round(wait, 1),
            "revenue": np.round(revenue, 2),
            "payer": payers,
            "patient_ref": [f"PT-{p}" for p in patients],
        }
    )
    return df.sort_values(["date", "start_time"]).reset_index(drop=True)


def generate_csv(path: str, **kwargs) -> pd.DataFrame:
    df = generate(**kwargs)
    df.to_csv(path, index=False)
    return df


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description="Generate a synthetic clinic CSV.")
    ap.add_argument("--out", default="sample_clinic.csv")
    ap.add_argument("--days", type=int, default=260)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--appts-per-day", type=int, default=42)
    args = ap.parse_args()
    df = generate_csv(args.out, days=args.days, seed=args.seed, appts_per_day=args.appts_per_day)
    print(f"wrote {len(df):,} rows to {args.out}")


if __name__ == "__main__":
    main()