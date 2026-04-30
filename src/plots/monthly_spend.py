import pandas as pd
import plotly.express as px

from src.constants import CHART_MARGIN

SMA_WINDOW_MONTHS = 12
BAR_COLOR = "#7cc4ff"
SMA_COLOR = "#16a34a"
SMA_LINE_WIDTH = 4
TOOLTIP_FONT_SIZE = 16
TARGET_X_TICKS = 24
MONTH_LABEL_FORMAT = "%b %Y"
MONTH_FULL_FORMAT = "%B %Y"


def compute_full_net(orders: pd.DataFrame, refunds: pd.DataFrame) -> pd.Series:
    # Reindex onto a contiguous monthly range so empty months survive as zeros;
    # otherwise the rolling SMA would span more than SMA_WINDOW_MONTHS calendar
    # months and the bar chart would render gaps instead of 0-height bars.
    full_gross = orders.groupby("Month")["Total Amount"].sum()
    full_refund = refunds.groupby("Month")["Refund Amount"].sum()
    full_net = full_gross.subtract(full_refund, fill_value=0)
    full_idx = pd.date_range(full_net.index.min(), full_net.index.max(), freq="MS")
    return full_net.reindex(full_idx, fill_value=0)


def compute_sma(full_net: pd.Series) -> pd.Series:
    # Computed over full history (not the slider window) so the line stays
    # fixed as the user adjusts the date range.
    return full_net.rolling(window=SMA_WINDOW_MONTHS, min_periods=1).mean()


def render(
    container,
    full_net: pd.Series,
    sma: pd.Series,
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
) -> None:
    sma_v = sma.loc[(sma.index >= start_month) & (sma.index <= end_month)]

    # Use a string label as the x-value so the axis is categorical — otherwise
    # the 28–31-day variation between month-starts shows up as uneven gaps on
    # a continuous datetime axis.
    monthly = full_net.loc[start_month:end_month].rename_axis("Month").reset_index(name="Net")
    monthly["Label"] = monthly["Month"].dt.strftime(MONTH_LABEL_FORMAT)
    sma_df = sma_v.rename_axis("Month").reset_index(name="Avg")
    sma_df["Label"] = sma_df["Month"].dt.strftime(MONTH_LABEL_FORMAT)

    fig = px.bar(monthly, x="Label", y="Net", custom_data=["Month"])
    fig.update_traces(
        marker_color=BAR_COLOR,
        hovertemplate=(
            f"<b>$%{{y:,.2f}}</b><br>%{{customdata[0]|{MONTH_FULL_FORMAT}}}<extra></extra>"
        ),
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
    container.plotly_chart(fig, width="stretch")
