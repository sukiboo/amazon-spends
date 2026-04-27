import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
ORDERS_ZIP = DATA_DIR / "Your Orders.zip"
ORDERS_CSV_REL = Path("Your Amazon Orders") / "Order History.csv"
ORDERS_CSV = DATA_DIR / ORDERS_CSV_REL


@st.cache_data
def load_orders() -> pd.DataFrame:
    if not ORDERS_CSV.exists():
        if not ORDERS_ZIP.exists():
            raise FileNotFoundError(
                f"Missing {ORDERS_CSV} and {ORDERS_ZIP}. "
                "Place the Amazon 'Your Orders.zip' export in data/."
            )
        with zipfile.ZipFile(ORDERS_ZIP) as z:
            z.extract(str(ORDERS_CSV_REL), DATA_DIR)

    df = pd.read_csv(ORDERS_CSV)
    df = df[df["Order Status"] != "Cancelled"].copy()
    df["Order Date"] = pd.to_datetime(df["Order Date"], utc=True)
    df["Total Amount"] = (
        df["Total Amount"].astype(str).str.replace(",", "", regex=False).astype(float)
    )
    df["Month"] = df["Order Date"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
    return df


st.set_page_config(page_title="Amazon Spending", layout="wide")
st.title("Amazon Spending")

df = load_orders()

min_date = df["Order Date"].min().date()
max_date = df["Order Date"].max().date()
start, end = st.slider(
    "Date range",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM",
)

mask = (df["Order Date"].dt.date >= start) & (df["Order Date"].dt.date <= end)
view = df.loc[mask]

c1, c2, c3 = st.columns(3)
c1.metric("Total spent", f"${view['Total Amount'].sum():,.2f}")
c2.metric("Orders", f"{view['Order ID'].nunique():,}")
c3.metric("Items", f"{len(view):,}")

monthly = view.groupby("Month", as_index=False)["Total Amount"].sum()
fig = px.bar(monthly, x="Month", y="Total Amount")
fig.update_layout(
    xaxis_title=None,
    yaxis_title="USD",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, width="stretch")
