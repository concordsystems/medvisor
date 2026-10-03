"""Consulting layer — plain-English findings and recommended actions.

Rule-based and deliberately conservative: the value is the operational
reasoning, not a prediction.
"""
from __future__ import annotations

from .config import BENCHMARKS, fmt_money, fmt_num, fmt_pct


def executive_summary(now: dict, prev: dict, flags: list, insights: list) -> str:
    bits = [
        f"Across the selected window the clinic ran {fmt_num(now['appointments'])} scheduled appointments "
        f"({fmt_num(now['kept'])} kept) over {fmt_num(now['days'])} active days.",
        f"The no-show rate came in at {fmt_pct(now['no_show_rate'])} against a reference of {fmt_pct(BENCHMARKS['no_show_rate'], 0)}, "
        f"with a median wait of {fmt_num(now['wait_median'], 0)} minutes.",
    ]
    if now.get("has_revenue"):
        bits.append(
            f"Kept visits produced {fmt_money(now['revenue'])} of billings, or {fmt_money(now['revenue_per_visit'])} per visit."
        )
    alert_n = sum(1 for f in flags if f.severity == "alert")
    watch_n = sum(1 for f in flags if f.severity == "watch")
    if alert_n or watch_n:
        bits.append(
            f"{alert_n} item(s) need attention and {watch_n} are worth watching; the three highest-leverage moves are listed below."
        )
    else:
        bits.append("No metric moved far enough from its recent range to warrant an intervention this period.")
    return " ".join(bits)


def build(now: dict, prev: dict, delta: dict, flags: list, util, flow, busiest: list[int], top_service) -> list[dict]:
    out: list[dict] = []
    ns_delta = delta.get("no_show_rate")
    ns_rate = now["no_show_rate"]
    missed = now["no_show"]
    lost_value = missed * max(now.get("revenue_per_visit", 0.0), 1.0)

    # 1 — no-shows
    if ns_rate > BENCHMARKS["no_show_rate"] * 0.9:
        direction = "up" if (ns_delta or 0) > 0 else "down"
        out.append(
            {
                "tag": "Retention of booked capacity",
                "headline": f"No-shows are running at {fmt_pct(ns_rate)} — {direction} on the previous window.",
                "body": (
                    f"{fmt_num(missed)} appointments were missed outright. At the current revenue per visit "
                    f"({fmt_money(now['revenue_per_visit'])}) that is roughly {fmt_money(lost_value)} of billings that never happened. "
                    f"Cancellations add another {fmt_pct(now['cancel_rate'])}, though at least those release the slot."
                ),
                "action": (
                    "Run a two-step confirmation (24h + 2h) on the highest-risk slots first — late afternoon and early morning. "
                    "Hold two overbookable slots per provider per afternoon rather than overbooking the whole day."
                ),
            }
        )
    else:
        out.append(
            {
                "tag": "Retention of booked capacity",
                "headline": f"No-shows are under control at {fmt_pct(ns_rate)}.",
                "body": (
                    f"That is below the {fmt_pct(BENCHMARKS['no_show_rate'], 0)} reference for this clinic type. "
                    "The confirmation routine appears to be holding; the risk now is complacency rather than leakage."
                ),
                "action": "Keep the current confirmation flow and audit the few remaining miss patterns by slot time before changing anything.",
            }
        )

    # 2 — utilisation
    if util is not None and not util.empty:
        lowest = util.iloc[0]
        highest = util.iloc[-1]
        gap = BENCHMARKS["utilization"] - float(util["utilization"].mean())
        if gap > 0.02:
            out.append(
                {
                    "tag": "Capacity",
                    "headline": f"{fmt_pct(max(gap, 0))} of clinical capacity is going unused.",
                    "body": (
                        f"{highest['provider']} is carrying {fmt_pct(highest['utilization'])} utilisation while {lowest['provider']} "
                        f"sits at {fmt_pct(lowest['utilization'])}. Both are on the same booking rules, so the difference is scheduling "
                        "practice rather than demand."
                    ),
                    "action": (
                        f"Rebalance two recurring blocks from {lowest['provider']} toward the hours where the clinic is already full, "
                        f"and protect the busiest window ({', '.join(str(h) + ':00' for h in busiest) or 'n/a'}) for higher-value services."
                    ),
                }
            )
        else:
            out.append(
                {
                    "tag": "Capacity",
                    "headline": f"Capacity is well used at {fmt_pct(float(util['utilization'].mean()))} average utilisation.",
                    "body": (
                        f"Spread across {int(util.shape[0])} providers, booked time is close to the "
                        f"{fmt_pct(BENCHMARKS['utilization'], 0)} reference. There is little idle clinical time to reclaim."
                    ),
                    "action": "Shift attention from filling the diary to raising revenue per visit — the next unit of growth is mix, not volume.",
                }
            )

    # 3 — wait & flow
    if now.get("wait_median") is not None:
        w_med, w_p90 = now["wait_median"], now.get("wait_p90") or 0
        if w_med > BENCHMARKS["wait_median"]:
            out.append(
                {
                    "tag": "Patient flow",
                    "headline": f"Median wait is {fmt_num(w_med)} minutes, with a tail at {fmt_num(w_p90)} minutes.",
                    "body": (
                        f"Arrivals cluster at {', '.join(str(h) + ':00' for h in busiest) or 'the same window'} and the queue is a "
                        "scheduling artefact rather than a staffing shortfall: the workload is front-loaded into a narrow band."
                    ),
                    "action": (
                        "Stagger start times by 10 minutes across providers in the peak band and move paperwork to a pre-visit digital form. "
                        "Re-measure p90, not just the median — the tail is what patients remember."
                    ),
                }
            )
        else:
            out.append(
                {
                    "tag": "Patient flow",
                    "headline": f"Wait times are within tolerance at {fmt_num(w_med)} minutes median.",
                    "body": f"The p90 sits at {fmt_num(w_p90)} minutes, inside the {fmt_num(BENCHMARKS['wait_p90'])} minute reference.",
                    "action": "Hold current slotting rules. Any compression here should come from the no-show work, not from tighter scheduling.",
                }
            )

    # 4 — revenue mix
    if now.get("has_revenue"):
        rpv_delta = delta.get("revenue_per_visit") or 0.0
        svc = top_service.iloc[0] if top_service is not None and not top_service.empty else None
        svc_txt = f"{svc['service']} is the largest revenue block at {fmt_money(svc['revenue'])}." if svc is not None else ""
        out.append(
            {
                "tag": "Revenue mix",
                "headline": f"Revenue per visit is {fmt_money(now['revenue_per_visit'])} ({'up' if rpv_delta > 0 else 'down'} {abs(rpv_delta) * 100:.1f}%).",
                "body": (
                    f"Total billings from kept visits were {fmt_money(now['revenue'])}. {svc_txt} "
                    "Mix moves this number far more than volume does at this size of clinic."
                ),
                "action": (
                    "Publish a one-page service mix target for the front desk — which services to fill first when a slot opens — "
                    "and re-check the payer split before assuming the price list is the problem."
                ),
            }
        )

    return out[:4]


def recommended_actions(insights: list[dict]) -> list[str]:
    return [f"{i['tag']}: {i['action']}" for i in insights]
