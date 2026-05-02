import pandas as pd
import streamlit as st

from src import onboarding
from src.constants import APP_NAME, DEFAULT_LOOKBACK_YEARS, MONTH_KEY_FORMAT, ORDERS_ZIP
from src.data import load_data
from src.plots import monthly_spend, top_products


def _resolve_zip_bytes() -> bytes | None:
    # Disk wins so local users keep the "drop once into data/" UX. Session-state
    # is the upload path used on Hugging Face Spaces (and any other hosted
    # deployment) where there's no persistent filesystem.
    if ORDERS_ZIP.exists():
        return ORDERS_ZIP.read_bytes()
    return st.session_state.get("uploaded_zip")


# (divisor, suffix) tiers, smallest first. The loop tries each tier in order
# and bails out at the first one whose formatted representation fits the
# 3-digit budget — so 999,999 falls through K (would round to "1000") and
# lands cleanly in M as "1.0M".
_TIERS = ((1_000, "K"), (1_000_000, "M"), (1_000_000_000, "B"))


def _compact(value: float) -> str:
    """Format a number to ≤3 digits with K/M/B suffixes (≤4 below 10,000)."""
    if abs(value) < 10_000:
        return f"{value:,.0f}"
    for divisor, suffix in _TIERS:
        scaled = value / divisor
        if abs(scaled) >= 100:
            text = f"{round(scaled):d}"
        else:
            text = f"{round(scaled, 1):.1f}".rstrip("0").rstrip(".")
        if sum(c.isdigit() for c in text) <= 3:
            return f"{text}{suffix}"
    divisor, suffix = _TIERS[-1]
    return f"{value / divisor:.0f}{suffix}"


def run() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)

    zip_bytes = _resolve_zip_bytes()
    if zip_bytes is None:
        onboarding.render()
        return

    orders, refunds = load_data(zip_bytes)

    full_net = monthly_spend.compute_full_net(orders, refunds)
    sma = monthly_spend.compute_sma(full_net)

    min_date = orders["Order Date"].min().date()
    max_date = orders["Order Date"].max().date()
    default_start = max(
        min_date, (pd.Timestamp(max_date) - pd.DateOffset(years=DEFAULT_LOOKBACK_YEARS)).date()
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    net_slot = c1.empty()
    avg_slot = c2.empty()
    refunded_slot = c3.empty()
    orders_slot = c4.empty()
    items_slot = c5.empty()

    chart_slot = st.empty()

    # Slider options append one sentinel month past the last data month so
    # the right handle is exclusive — a single-month selection still spans a
    # tick instead of collapsing both handles onto the same point.
    month_options = [d.strftime(MONTH_KEY_FORMAT) for d in full_net.index]
    month_options.append(
        (full_net.index.max() + pd.offsets.MonthBegin(1)).strftime(MONTH_KEY_FORMAT)
    )
    default_start_month = pd.Timestamp(default_start).to_period("M").strftime(MONTH_KEY_FORMAT)
    default_end_month = month_options[-1]

    # Sync slider to chart's box-selection. Chart x uses MONTH_LABEL_FORMAT
    # ("Apr 2024"); convert to match month_options. _last_chart_selection
    # prevents the still-present selection from clobbering manual slider moves.
    points = (st.session_state.get("monthly_chart") or {}).get("selection", {}).get("points", [])
    selected_keys = sorted({pd.Timestamp(p["x"]).strftime(MONTH_KEY_FORMAT) for p in points})
    if selected_keys != st.session_state.get("_last_chart_selection"):
        if selected_keys:
            end_idx = month_options.index(selected_keys[-1]) + 1
            st.session_state["date_range"] = (selected_keys[0], month_options[end_idx])
        st.session_state["_last_chart_selection"] = selected_keys

    # Enforce a 1-month minimum span — st.select_slider lets the user drag
    # both handles onto the same tick, which would collapse the range and
    # produce empty queries. Nudge the right handle out by one (or the left
    # in, if we're already at the sentinel).
    rng = st.session_state.get("date_range")
    if rng and rng[0] == rng[1]:
        idx = month_options.index(rng[0])
        if idx + 1 < len(month_options):
            st.session_state["date_range"] = (rng[0], month_options[idx + 1])
        else:
            st.session_state["date_range"] = (month_options[idx - 1], rng[1])

    start_label, end_label = st.select_slider(
        "Date range",
        options=month_options,
        value=(default_start_month, default_end_month),
        key="date_range",
    )
    start = pd.Timestamp(start_label).date()
    end_exclusive = pd.Timestamp(end_label).date()

    orders_v = orders.loc[
        (orders["Order Date"].dt.date >= start) & (orders["Order Date"].dt.date < end_exclusive)
    ]
    refunds_v = refunds.loc[
        (refunds["Order Date"].dt.date >= start) & (refunds["Order Date"].dt.date < end_exclusive)
    ]

    gross = orders_v["Total Amount"].sum()
    refunded = refunds_v["Refund Amount"].sum()
    net = gross - refunded
    n_months = month_options.index(end_label) - month_options.index(start_label)

    net_slot.metric("Net spent", f"${_compact(net)}")
    refunded_slot.metric("Refunded", f"${_compact(refunded)}")
    orders_slot.metric("Orders", _compact(orders_v["Order ID"].nunique()))
    items_slot.metric("Items", _compact(len(orders_v)))
    avg_slot.metric("Avg/month", f"${_compact(net / n_months)}")

    start_month = pd.Period(start_label, freq="M").to_timestamp()
    end_month = (pd.Period(end_label, freq="M") - 1).to_timestamp()

    monthly_spend.render(chart_slot, full_net, sma, start_month, end_month)
    top_products.render(orders_v)
