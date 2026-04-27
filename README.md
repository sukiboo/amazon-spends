# amazon-spends

Streamlit dashboard that visualizes your personal Amazon spending month by month from
the official Amazon data export.

## Why an export instead of an API

Amazon does not expose a public OAuth API for personal purchase history, so the only
sanctioned way to get the data is the GDPR-style "Request My Data" export.

## Setup

1. Request your Amazon order history:
   - Go to <https://amazon.com/gp/privacycentral/dsar/preview.html>
   - Select **Your Orders** and submit the request
   - Amazon emails a download link within a few hours to a few days
2. Drop the resulting `Your Orders.zip` into `data/`. The app extracts
   `Your Amazon Orders/Order History.csv` automatically on first run.
3. Install deps:
   ```
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

## Run

```
.venv/bin/streamlit run app.py
```

Opens at <http://localhost:8501>.

## What it shows

- Total spent, order count, item count over the selected date range
- Bar chart of monthly spend (USD)

## Caveats

- Spend is summed from the per-line `Total Amount` column. This includes per-line tax
  but does not net out refunds or precisely allocate order-level shipping/discounts —
  good enough for trends, not penny-accurate against bank statements.
- Cancelled orders are excluded; refunds are not (yet) subtracted.
- Currency is assumed to be USD (the export confirms this for the current dataset).
