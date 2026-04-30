import zipfile

import pandas as pd
import streamlit as st

from src.constants import (
    EXCLUDED_WEBSITES,
    ORDERS_CSV_ENTRY,
    ORDERS_ZIP,
    REFUNDS_CSV_ENTRY,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not ORDERS_ZIP.exists():
        raise FileNotFoundError(
            f"Missing {ORDERS_ZIP}. Place the Amazon 'Your Orders.zip' export in data/."
        )
    with zipfile.ZipFile(ORDERS_ZIP) as z:
        with z.open(ORDERS_CSV_ENTRY) as f:
            orders = pd.read_csv(f)
        with z.open(REFUNDS_CSV_ENTRY) as f:
            refunds = pd.read_csv(f)

    orders = orders[orders["Order Status"] != "Cancelled"]
    # Exclude in-store / grocery channels (Whole Foods is `panda01`, plus the
    # cashier-less `Amazon Go`) — they're physical-store scans, not Amazon
    # online orders, and Whole Foods produce in particular collapses badly
    # under groupby because most rows share the `_ASINLESS_` sentinel ASIN.
    orders = orders[~orders["Website"].isin(EXCLUDED_WEBSITES)].copy()
    orders["Order Date"] = pd.to_datetime(orders["Order Date"], utc=True)
    orders["Total Amount"] = (
        orders["Total Amount"].astype(str).str.replace(",", "", regex=False).astype(float)
    )
    orders["Month"] = orders["Order Date"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()

    # The export emits multiple `Creation Date` rows per actual refund event (8x in
    # observed data); dedup on the natural key before summing or amounts inflate ~2x.
    refunds = refunds.drop_duplicates(subset=["Order ID", "Refund Date", "Refund Amount"]).copy()

    # Attribute each refund to its original order's date so net spend is shown
    # in the month the purchase was made (option b), not the month of the refund.
    order_date = orders.drop_duplicates("Order ID").set_index("Order ID")["Order Date"]
    refunds["Refund Amount"] = refunds["Refund Amount"].astype(float)
    refunds["Order Date"] = refunds["Order ID"].map(order_date)
    refunds = refunds.dropna(subset=["Order Date"])
    refunds["Month"] = refunds["Order Date"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()

    return orders, refunds
