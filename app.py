import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
ORDERS_ZIP = DATA_DIR / "Your Orders.zip"
ORDERS_CSV_ENTRY = "Your Amazon Orders/Order History.csv"
REFUNDS_CSV_ENTRY = "Your Returns & Refunds/Refund Details.csv"


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

    orders = orders[orders["Order Status"] != "Cancelled"].copy()
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


st.set_page_config(page_title="Amazon Spending", layout="wide")
st.title("Amazon Spending")

orders, refunds = load_data()

min_date = orders["Order Date"].min().date()
max_date = orders["Order Date"].max().date()
start, end = st.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM",
)

orders_v = orders.loc[
    (orders["Order Date"].dt.date >= start) & (orders["Order Date"].dt.date <= end)
]
refunds_v = refunds.loc[
    (refunds["Order Date"].dt.date >= start) & (refunds["Order Date"].dt.date <= end)
]

gross = orders_v["Total Amount"].sum()
refunded = refunds_v["Refund Amount"].sum()
net = gross - refunded

c1, c2, c3, c4 = st.columns(4)
c1.metric("Net spent", f"${net:,.2f}")
c2.metric("Refunded", f"${refunded:,.2f}")
c3.metric("Orders", f"{orders_v['Order ID'].nunique():,}")
c4.metric("Items", f"{len(orders_v):,}")

monthly_gross = orders_v.groupby("Month")["Total Amount"].sum()
monthly_refund = refunds_v.groupby("Month")["Refund Amount"].sum()
monthly = monthly_gross.subtract(monthly_refund, fill_value=0).reset_index(name="Net")

fig = px.bar(monthly, x="Month", y="Net")
fig.update_layout(
    xaxis_title=None,
    yaxis_title="USD",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, width="stretch")
