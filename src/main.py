import pandas as pd
import streamlit as st

from src.constants import APP_NAME, DEFAULT_LOOKBACK_YEARS, MONTH_KEY_FORMAT
from src.data import load_data
from src.plots import monthly_spend, top_products


def run() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)

    orders, refunds = load_data()

    full_net = monthly_spend.compute_full_net(orders, refunds)
    sma = monthly_spend.compute_sma(full_net)

    min_date = orders["Order Date"].min().date()
    max_date = orders["Order Date"].max().date()
    default_start = max(
        min_date, (pd.Timestamp(max_date) - pd.DateOffset(years=DEFAULT_LOOKBACK_YEARS)).date()
    )

    c1, c2, c3, c4 = st.columns(4)
    net_slot = c1.empty()
    refunded_slot = c2.empty()
    orders_slot = c3.empty()
    items_slot = c4.empty()

    chart_slot = st.empty()

    month_options = [d.strftime(MONTH_KEY_FORMAT) for d in full_net.index]
    default_start_month = pd.Timestamp(default_start).to_period("M").strftime(MONTH_KEY_FORMAT)
    default_end_month = pd.Timestamp(max_date).to_period("M").strftime(MONTH_KEY_FORMAT)

    start_label, end_label = st.select_slider(
        "Date range",
        options=month_options,
        value=(default_start_month, default_end_month),
    )
    start = pd.Timestamp(start_label).date()
    end = (pd.Timestamp(end_label) + pd.offsets.MonthEnd(0)).date()

    orders_v = orders.loc[
        (orders["Order Date"].dt.date >= start) & (orders["Order Date"].dt.date <= end)
    ]
    refunds_v = refunds.loc[
        (refunds["Order Date"].dt.date >= start) & (refunds["Order Date"].dt.date <= end)
    ]

    gross = orders_v["Total Amount"].sum()
    refunded = refunds_v["Refund Amount"].sum()
    net = gross - refunded

    net_slot.metric("Net spent", f"${net:,.2f}")
    refunded_slot.metric("Refunded", f"${refunded:,.2f}")
    orders_slot.metric("Orders", f"{orders_v['Order ID'].nunique():,}")
    items_slot.metric("Items", f"{len(orders_v):,}")

    # Snap the slider's date bounds to month-starts so the SMA, which is indexed
    # by month-start timestamps, doesn't get its first/last point filtered out.
    start_month = pd.Timestamp(start).to_period("M").to_timestamp()
    end_month = pd.Timestamp(end).to_period("M").to_timestamp()

    monthly_spend.render(chart_slot, full_net, sma, start_month, end_month)
    top_products.render(orders_v)
