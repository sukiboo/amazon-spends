import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

from src.constants import CHART_MARGIN

TOP_N_PRODUCTS = 20
PRODUCT_LABEL_MAX = 32
PRODUCT_WRAP_WIDTH = 64
PRODUCT_ROW_HEIGHT = 24
PRODUCT_CHART_PAD = 60
PRODUCT_BAR_COLOR = "#a78bfa"
PRODUCT_BAR_GAP = 0.6
PRODUCT_LABEL_FONT_SIZE = 16
PRODUCT_TOOLTIP_FONT_SIZE = 14
DATE_LONG_FORMAT = "%d %B %Y"


def render(orders_v: pd.DataFrame) -> None:
    # Top single purchases over the selected range. Each row is one line item — so
    # repeat buys of the same product show up multiple times. Not aggregated by
    # ASIN because Amazon rotates listing titles for the same SKU over time, which
    # made the grouped view show one variant name for a sum of purchases that
    # actually had several different display names (confusing when reading the
    # tooltip). Refunds aren't netted here either: Refund Details.csv has Order ID
    # but no ASIN, so refunds on multi-item orders can't be cleanly attributed.
    with st.expander("Most expensive products", expanded=False):
        top = (
            orders_v.nlargest(TOP_N_PRODUCTS, "Total Amount")
            .rename(
                columns={
                    "Total Amount": "Spent",
                    "Product Name": "Product",
                    "Order Date": "Date",
                }
            )
            .iloc[::-1]
            .reset_index(drop=True)
        )
        top["Key"] = top.index.astype(str)
        top["Label"] = top["Product"].where(
            top["Product"].str.len() <= PRODUCT_LABEL_MAX,
            top["Product"].str.slice(0, PRODUCT_LABEL_MAX - 1) + "…",
        )
        top["Wrapped"] = top["Product"].apply(
            lambda p: textwrap.fill(p, width=PRODUCT_WRAP_WIDTH).replace("\n", "<br>")
        )
        top["DateFmt"] = top["Date"].dt.strftime(DATE_LONG_FORMAT)
        top_fig = px.bar(
            top, x="Spent", y="Key", orientation="h", custom_data=["Wrapped", "DateFmt"]
        )
        top_fig.update_traces(
            marker_color=PRODUCT_BAR_COLOR,
            hovertemplate=(
                "<b>$%{x:,.2f}</b>"
                "<br><i>%{customdata[1]}</i>"
                "<br>%{customdata[0]}<extra></extra>"
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
            tickvals=top["Key"],
            ticktext=top["Label"],
            tickfont=dict(size=PRODUCT_LABEL_FONT_SIZE),
        )
        st.plotly_chart(top_fig, width="stretch")
