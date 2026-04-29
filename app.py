import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
ORDERS_ZIP = DATA_DIR / "Your Orders.zip"
ORDERS_CSV_ENTRY = "Your Amazon Orders/Order History.csv"
REFUNDS_CSV_ENTRY = "Your Returns & Refunds/Refund Details.csv"

APP_NAME = "Amazon Spending Visualizer"

SMA_WINDOW_MONTHS = 12
DEFAULT_LOOKBACK_YEARS = 5
BAR_COLOR = "#7cc4ff"
SMA_COLOR = "#ff4b4b"
SMA_LINE_WIDTH = 4
TOOLTIP_FONT_SIZE = 16
TARGET_X_TICKS = 24


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


st.set_page_config(page_title=APP_NAME, layout="wide")
st.title(APP_NAME)

orders, refunds = load_data()

# Compute the rolling average over the full history once so it stays fixed
# as the user changes the date-range slider. Reindex to a contiguous monthly
# range first; otherwise empty months collapse and the rolling window would
# span more than SMA_WINDOW_MONTHS calendar months.
full_gross = orders.groupby("Month")["Total Amount"].sum()
full_refund = refunds.groupby("Month")["Refund Amount"].sum()
full_net = full_gross.subtract(full_refund, fill_value=0)
full_idx = pd.date_range(full_net.index.min(), full_net.index.max(), freq="MS")
full_net = full_net.reindex(full_idx, fill_value=0)
sma = full_net.rolling(window=SMA_WINDOW_MONTHS, min_periods=1).mean()

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

month_options = [d.strftime("%Y-%m") for d in full_idx]
default_start_month = pd.Timestamp(default_start).to_period("M").strftime("%Y-%m")
default_end_month = pd.Timestamp(max_date).to_period("M").strftime("%Y-%m")

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
sma_v = sma.loc[(sma.index >= start_month) & (sma.index <= end_month)]

# Slice the contiguous monthly net series so empty months render as 0-height
# bars rather than gaps. Use a string label as the x-value so the axis is
# categorical — otherwise the 28–31-day variation between month-starts shows
# up as uneven gaps on a continuous datetime axis.
monthly = full_net.loc[start_month:end_month].rename_axis("Month").reset_index(name="Net")
monthly["Label"] = monthly["Month"].dt.strftime("%b %Y")
sma_df = sma_v.rename_axis("Month").reset_index(name="Avg")
sma_df["Label"] = sma_df["Month"].dt.strftime("%b %Y")

fig = px.bar(monthly, x="Label", y="Net", custom_data=["Month"])
fig.update_traces(
    marker_color=BAR_COLOR,
    hovertemplate="<b>$%{y:,.2f}</b><br>%{customdata[0]|%B %Y}<extra></extra>",
)
fig.add_scatter(
    x=sma_df["Label"],
    y=sma_df["Avg"],
    mode="lines",
    name=f"{SMA_WINDOW_MONTHS}-mo avg",
    line=dict(color=SMA_COLOR, width=SMA_LINE_WIDTH),
    customdata=sma_df[["Month"]],
    hovertemplate=(
        f"<b>$%{{y:,.2f}}</b><br>%{{customdata[0]|%B %Y}}<br>"
        f"{SMA_WINDOW_MONTHS}-mo average<extra></extra>"
    ),
)
tick_step = max(1, -(-len(monthly) // TARGET_X_TICKS))
tick_labels = monthly["Label"].iloc[::tick_step].tolist()
tick_angle = -45 if len(tick_labels) > 12 else 0
fig.update_layout(
    xaxis_title=None,
    yaxis_title="USD",
    margin=dict(l=0, r=0, t=10, b=0),
    showlegend=False,
    hoverlabel=dict(font_size=TOOLTIP_FONT_SIZE),
)
fig.update_xaxes(
    tickmode="array",
    tickvals=tick_labels,
    tickangle=tick_angle,
)
chart_slot.plotly_chart(fig, width="stretch")
