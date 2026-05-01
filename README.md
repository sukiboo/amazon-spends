---
title: Amazon Spending Visualizer
emoji: 📦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
---

# Amazon Spending Visualizer

Have you ever wondered how much you spend on Amazon? Wonder no more!

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
2. Drop the resulting `Your Orders.zip` into `data/`. The app reads
   `Your Amazon Orders/Order History.csv` straight out of the zip, so the zip is
   always the source of truth — replace it to refresh the data. (You can also
   skip this step and upload the zip through the in-app uploader at runtime,
   which is how the hosted Hugging Face Space works.)
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

- Net spent, refunded, order count, and item count over the selected date range
- Bar chart of net monthly spend (USD), with a 12-month rolling-average overlay
  computed over the full history (so the line stays fixed as you adjust the range)
- "Most expensive products" expander (collapsed by default): top 20 single line
  items by spend, listed as individual purchases rather than aggregated per
  product (so repeat buys of the same item show up multiple times).

## How refunds are handled

Refunds (from `Your Returns & Refunds/Refund Details.csv`) are subtracted from the
month of the **original order**, not the month the refund was issued. This gives a
"what did I actually keep this month" view rather than matching bank-statement
timing. If you'd rather see refunds in the month they hit your card, that's a
one-line change in the loader.

In the "Most expensive products" view, returned items are kept in the list but
rendered with a strikethrough label and a muted bar (with an `↩ Refunded` note in
the tooltip). Attribution is tricky here because the refund file has `Order ID` but
no ASIN, so on a multi-item order the export doesn't say which line was returned.
The loader works around this by matching each refund to the line in that order
whose `Total Amount` is closest to the `Refund Amount` within $0.50 (Amazon
typically refunds the full item including tax, so amounts line up exactly). About
85% of refunds match cleanly this way; the remaining ~15% are partial refunds,
restocking fees, or shipping-only credits that don't equal any single line — those
leave their lines un-flagged on purpose, since flagging the whole order would
strike out kept items too. The dollar totals in the bar chart and "Net spent"
metric still subtract **every** refund regardless of match status, so monetary
accuracy is unaffected — only the per-line flag is best-effort.

## Caveats

- Spend is summed from the per-line `Total Amount` column. This includes per-line tax
  but does not precisely allocate order-level shipping/discounts — good enough for
  trends, not penny-accurate against bank statements.
- Cancelled orders are excluded.
- **Whole Foods and Amazon Go purchases are excluded** (filtered by `Website` —
  `panda01` is Amazon's internal marketplace ID for Whole Foods). Rationale:
  these are physical-store scans, not "real" Amazon online orders, and Whole
  Foods produce in particular has no real ASINs (Amazon stamps them with a
  shared `_ASINLESS_` sentinel), so groupings collapse misleadingly. Edit
  `EXCLUDED_WEBSITES` in `src/constants.py` to change this.
- Currency is assumed to be USD (the export confirms this for the current dataset).
