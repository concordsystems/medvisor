# MedVisor Dashboard

> Turns messy clinic data into clear dashboards and consulting insights.

**Status: Proof of Concept.** Not production software. Not a medical device.
See [Compliance & PHI Policy](#compliance--phi-policy) before using any real data.

---

## ⚠️ Read this first

This is an early PoC built to validate one question:

> *Will clinics pay for dashboards plus consulting that turn their messy
> operational data into decisions?*

It is **not** ready for real patient data. It ships with **synthetic and
de-identified sample data only**. No HIPAA/GDPR/LGPD compliance is claimed.

---

## The problem

Small and mid-size clinics (dental, physio, private practice) run on
spreadsheets, exported CSVs, and gut feeling. They know something is wrong
with no-shows, utilization, or revenue — but nobody has time to clean the
data, let alone read a dashboard.

Existing tools are either:
- **Too heavy** — full EHR suites, months of onboarding
- **Too shallow** — generic BI tools that don't understand clinics

## What this does

A lightweight pipeline with two layers:

1. **Dashboard layer** — drop in a CSV, get charts that answer real questions
2. **Consulting layer** — the dashboard highlights *what changed* and *what to do about it*

### Current features

- 📥 **CSV ingest** with column mapping and validation
- 📊 **Core clinic metrics**
  - Appointment volume over time
  - No-show and cancellation rate
  - Provider utilization
  - Revenue per visit / per provider
  - Patient flow and wait patterns
- 🔍 **Automatic anomaly flags** — "no-shows up 40% vs last month"
- 📝 **Auto-generated insight summary** — plain-English notes per period
- 📤 **Export** to PDF/PNG for sharing with clinic owners
- 🧪 **Synthetic data generator** for demos and testing

### Not built yet (intentionally)

- EHR integrations (Epic, Cerner, Athena)
- Multi-tenant auth / user accounts
- Real PHI handling
- Any ML forecasting

These are expensive. They come **after** someone pays for a pilot.

---
## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
---