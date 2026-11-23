# Add the "date last sold" metric to Copy Seller

Type: task
Status: open

## Summary

The Copy Seller pipeline originally included a **Days Since Last Sold** metric
(how recently a product sold). Deferred: there is no ungated eBay API for a
competitor listing's last-sold date.

- Finding API `findCompletedItems` was decommissioned Feb 5 2025.
- Marketplace Insights API (`item_sales/search`) returns `lastSoldDate` but is
  approval-gated (Limited Release + per-category whitelist; weeks, uncertain).
- Scraping the sold-search page (`?LH_Sold=1&LH_Complete=1`) via the signed-in
  browser works but is ToS-gray and bot-fragile.

Decision: ship Copy Seller without this metric for now.

## When revisited

Pick a source and wire it in as a new metric (the metric/weight model is built
to be extensible):

- **Marketplace Insights API** — sanctioned route; apply via eBay Partner Network.
- **Browser scrape of sold-search** — works now via `browseros-neo`, low volume,
  ToS-gray.

## Comments
