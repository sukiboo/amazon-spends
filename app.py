import textwrap
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
CHART_MARGIN = dict(l=0, r=0, t=10, b=0)
MONTH_KEY_FORMAT = "%Y-%m"
MONTH_LABEL_FORMAT = "%b %Y"
MONTH_FULL_FORMAT = "%B %Y"
DATE_LONG_FORMAT = "%d %B %Y"

TOP_N_PRODUCTS = 20
PRODUCT_LABEL_MAX = 32
PRODUCT_WRAP_WIDTH = 64
PRODUCT_ROW_HEIGHT = 24
PRODUCT_CHART_PAD = 60
PRODUCT_BAR_COLOR = "#a78bfa"
PRODUCT_BAR_GAP = 0.6
PRODUCT_LABEL_FONT_SIZE = 14
PRODUCT_TOOLTIP_FONT_SIZE = 16


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

month_options = [d.strftime(MONTH_KEY_FORMAT) for d in full_idx]
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
sma_v = sma.loc[(sma.index >= start_month) & (sma.index <= end_month)]

# Slice the contiguous monthly net series so empty months render as 0-height
# bars rather than gaps. Use a string label as the x-value so the axis is
# categorical — otherwise the 28–31-day variation between month-starts shows
# up as uneven gaps on a continuous datetime axis.
monthly = full_net.loc[start_month:end_month].rename_axis("Month").reset_index(name="Net")
monthly["Label"] = monthly["Month"].dt.strftime(MONTH_LABEL_FORMAT)
sma_df = sma_v.rename_axis("Month").reset_index(name="Avg")
sma_df["Label"] = sma_df["Month"].dt.strftime(MONTH_LABEL_FORMAT)

fig = px.bar(monthly, x="Label", y="Net", custom_data=["Month"])
fig.update_traces(
    marker_color=BAR_COLOR,
    hovertemplate=(f"<b>$%{{y:,.2f}}</b><br>%{{customdata[0]|{MONTH_FULL_FORMAT}}}<extra></extra>"),
)
fig.add_scatter(
    x=sma_df["Label"],
    y=sma_df["Avg"],
    mode="lines",
    name=f"{SMA_WINDOW_MONTHS}-mo avg",
    line=dict(color=SMA_COLOR, width=SMA_LINE_WIDTH),
    customdata=sma_df[["Month"]],
    hovertemplate=(
        f"<b>$%{{y:,.2f}}</b><br>%{{customdata[0]|{MONTH_FULL_FORMAT}}}<br>"
        f"{SMA_WINDOW_MONTHS}-mo average<extra></extra>"
    ),
)
tick_step = max(1, -(-len(monthly) // TARGET_X_TICKS))
tick_labels = monthly["Label"].iloc[::tick_step].tolist()
tick_angle = -45 if len(tick_labels) > 12 else 0
fig.update_layout(
    xaxis_title=None,
    yaxis_title="USD",
    margin=CHART_MARGIN,
    showlegend=False,
    hoverlabel=dict(font_size=TOOLTIP_FONT_SIZE),
)
fig.update_xaxes(
    tickmode="array",
    tickvals=tick_labels,
    tickangle=tick_angle,
)
chart_slot.plotly_chart(fig, width="stretch")

# Top products: gross spend per ASIN over the selected range. Refunds aren't
# netted here because Refund Details.csv has Order ID but no ASIN, so refunds
# on multi-item orders can't be cleanly attributed to a product.
with st.expander("Top products", expanded=False):
    top = (
        orders_v.groupby("ASIN", as_index=False)
        .agg(
            Spent=("Total Amount", "sum"),
            Product=("Product Name", "last"),
            LastDate=("Order Date", "max"),
        )
        .nlargest(TOP_N_PRODUCTS, "Spent")
        .iloc[::-1]
    )
    top["Label"] = top["Product"].where(
        top["Product"].str.len() <= PRODUCT_LABEL_MAX,
        top["Product"].str.slice(0, PRODUCT_LABEL_MAX - 1) + "…",
    )
    top["Wrapped"] = top["Product"].apply(
        lambda p: textwrap.fill(p, width=PRODUCT_WRAP_WIDTH).replace("\n", "<br>")
    )
    top["DateFmt"] = top["LastDate"].dt.strftime(DATE_LONG_FORMAT)
    top_fig = px.bar(top, x="Spent", y="ASIN", orientation="h", custom_data=["Wrapped", "DateFmt"])
    top_fig.update_traces(
        marker_color=PRODUCT_BAR_COLOR,
        hovertemplate=(
            "<b>$%{x:,.2f}</b>" "<br><i>%{customdata[1]}</i>" "<br>%{customdata[0]}<extra></extra>"
        ),
    )
    top_fig.update_layout(
        xaxis_title="USD",
        yaxis_title=None,
        margin=CHART_MARGIN,
        hoverlabel=dict(font_size=PRODUCT_TOOLTIP_FONT_SIZE, align="left"),
        height=len(top) * PRODUCT_ROW_HEIGHT + PRODUCT_CHART_PAD,
        bargap=PRODUCT_BAR_GAP,
    )
    top_fig.update_yaxes(
        tickmode="array",
        tickvals=top["ASIN"],
        ticktext=top["Label"],
        tickfont=dict(size=PRODUCT_LABEL_FONT_SIZE),
    )
    st.plotly_chart(top_fig, width="stretch")
