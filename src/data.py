import io
import zipfile

import pandas as pd
import streamlit as st

from src.constants import EXCLUDED_WEBSITES, ORDERS_CSV_ENTRY, REFUNDS_CSV_ENTRY

# Tolerance (USD) for matching a refund row to a specific line item by amount.
# Refund Details.csv has Order ID but no ASIN, so to flag the actual returned
# line in a multi-item order we match on Refund Amount ≈ line Total Amount.
# Set generously enough to absorb rounding/tax variation; tight enough to avoid
# matching cheaper items in the same order. Refunds outside this tolerance
# (partial refunds, restocking fees, shipping-only) are left un-flagged.
REFUND_MATCH_TOLERANCE = 0.5


def _match_refunds_to_lines(orders: pd.DataFrame, refunds: pd.DataFrame) -> set:
    refunded_idx: set = set()
    orders_by_id = {oid: g for oid, g in orders.groupby("Order ID")}
    for order_id, group in refunds.groupby("Order ID"):
        if order_id not in orders_by_id:
            continue
        unmatched = {idx: amt for idx, amt in orders_by_id[order_id]["Total Amount"].items()}
        # Greedy largest-first: bigger refunds are less ambiguous, so match them
        # before they get stolen by a near-tie smaller line.
        for refund_amt in sorted(group["Refund Amount"], reverse=True):
            best_idx, best_diff = None, REFUND_MATCH_TOLERANCE
            for idx, amt in unmatched.items():
                d = abs(amt - refund_amt)
                if d <= best_diff:
                    best_diff, best_idx = d, idx
            if best_idx is not None:
                refunded_idx.add(best_idx)
                del unmatched[best_idx]
    return refunded_idx


@st.cache_data
def load_data(zip_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
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
    # Drop $0 lines: item-level cancellations within a multi-item order
    # (Original Quantity = 0, order itself stayed Closed), free replacements
    # for damaged/missing goods, fully-discounted promos, and Prime
    # Try-Before-You-Buy returns. None reflect real spending and they pollute
    # the "Most expensive products" tail when the date window is narrow.
    orders = orders[orders["Total Amount"] > 0]
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

    orders["Refunded"] = False
    orders.loc[list(_match_refunds_to_lines(orders, refunds)), "Refunded"] = True

    return orders, refunds
