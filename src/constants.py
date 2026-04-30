from pathlib import Path

APP_NAME = "Amazon Spending Visualizer"

DATA_DIR = Path(__file__).parent.parent / "data"
ORDERS_ZIP = DATA_DIR / "Your Orders.zip"
ORDERS_CSV_ENTRY = "Your Amazon Orders/Order History.csv"
REFUNDS_CSV_ENTRY = "Your Returns & Refunds/Refund Details.csv"
EXCLUDED_WEBSITES = {"panda01", "Amazon Go"}

DEFAULT_LOOKBACK_YEARS = 5

MONTH_KEY_FORMAT = "%Y-%m"
CHART_MARGIN = dict(l=0, r=0, t=10, b=0)
