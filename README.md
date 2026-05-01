---
title: Amazon Spending Visualizer
emoji: 📦
colorFrom: blue
colorTo: yellow
sdk: docker
app_port: 8501
pinned: false
---

# Amazon Spending Visualizer

Streamlit dashboard that visualizes your personal Amazon spending month by month
from the official Amazon data export.

## Run it

- **Hosted:** <https://huggingface.co/spaces/sukiboo/amazon-spends> — upload
  your export and go. Nothing is stored server-side: the zip lives in per-tab
  session memory only and is gone when you close the tab.
- **Local:** clone the repo, then
  ```
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/streamlit run app.py
  ```
  Drop `Your Orders.zip` into `data/` for a persistent local setup, or use the
  in-app uploader.

## Get your Amazon export

Amazon doesn't expose an API for personal purchase history, so you need the
GDPR-style export:

1. Go to <https://amazon.com/gp/privacycentral/dsar/preview.html>
2. Select **Your Orders** and submit the request
3. Amazon emails a download link within a few hours to a few days

## What it shows

- Net spent, refunded, order count, and item count over the selected date range
- Monthly net spend bar chart with a 12-month rolling-average overlay
  (computed over full history so the line stays fixed as you slide the range)
- "Most expensive products" expander: top 20 line items by spend, listed as
  individual purchases (repeat buys of the same item appear multiple times)

## How refunds are handled

Refunds are subtracted from the **original order's month**, not the month the
refund was issued — so the chart reflects "what you actually kept" per purchase
month. In the top-products list, refunded line items are shown with a
strikethrough; matching is best-effort by amount, since the refund export has
no ASIN.

## Caveats

- USD only.
- Cancelled orders are excluded.
- Whole Foods and Amazon Go in-store purchases are excluded (set
  `EXCLUDED_WEBSITES` in `src/constants.py` to change).
- Spend is summed from the per-line `Total Amount` (includes per-line tax) —
  good for trends, not penny-accurate against bank statements.

## License

MIT -- open source, do whatever you want with it.
