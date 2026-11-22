# Programmatically Counting SOLD eBay Listings in a Time Window

Research date: 2026-11-21. All claims cite official eBay developer documentation (developer.ebay.com), retrieved directly or via the Internet Archive Wayback Machine where the live page is login-gated or removed.

## The 4 hard constraints

1. **No special partner approval** — must use APIs a normal developer account already has.
2. **Standard APIs used cleverly** are allowed.
3. **Must work for ALL sellers** (not just the user's own sales).
4. **No long-term indexing** — on-demand query only.

---

## TL;DR / Recommendation

**There is currently NO officially-supported eBay API that satisfies all four constraints.** Every API that returns cross-seller SOLD history is gated behind eBay partner/business approval. The two "clever" workarounds that historically satisfied the constraints are now broken:

- **findCompletedItems + soldItems filter + paginationOutput.totalEntries** — the classic count-without-downloading trick — is **no longer viable** for two independent reasons: (a) the call is **deprecated and access-restricted** as of Oct 15, 2020, and (b) the `SoldItemsOnly` item filter is documented by eBay as **"Reserved for future use"** (i.e., it never actually filtered). Sources below.

**Best available options, ranked:**

| Option | Meets all 4 constraints? | Why / why not |
|---|---|---|
| **Marketplace Insights API** `item_sales/search` | No (violates #1) | The correct tool for the job — real sold history, all sellers, on-demand, date filterable — but it is **Limited Release / partner-approved only**. |
| **Finding API** `findCompletedItems` | No (violates #1, sold filter is a no-op) | Deprecated + access-restricted; `SoldItemsOnly` reserved/unimplemented. |
| **Browse API** `item_summary/search` | No (no sold data) | Active/purchasable listings only; no completed/sold items at all. |
| **Feed API** | No (violates #1) | Limited Release; and it is an *active-item* feed, not a sold-history feed. |
| **Sell Analytics API** | No (violates #3) | Returns only the authenticated seller's OWN metrics. |
| **Terapeak / Product Research** | No API | UI-only; no public programmatic API. |

**Practical recommendation:** If the "no partner approval" constraint is truly hard, there is **no compliant on-demand API path** to an exact cross-seller sold count. The realistic routes are:

1. **Apply for Marketplace Insights API access** (the only real sold-history API). This drops constraint #1 but is the *intended* eBay mechanism. It returns `totalSoldQuantity` per item and supports a `lastSoldDate` filter — exactly a sold-count-in-window.
2. **Approximate with active-listing data** from the open Browse API (e.g., active supply, sell-through signals) — but this is **not** a sold count and cannot produce one.
3. Accept that an **exact sold count across all sellers without approval is not offered by eBay** and use a third-party data provider (outside the scope of "official eBay APIs").

---

## Candidate APIs

### 1. Marketplace Insights API — `item_sales/search` (the real "sold history" API)

- **What it is:** Part of the eBay **Buy APIs**. "Provides the ability to search for sold items on eBay by keyword, GTIN, category, and product and returns the sales history of those items." Resource: `item_sales` — "Retrieves the sales history of eBay items that have been sold up to 90 days in the past." ([Marketplace Insights API Overview](https://developer.ebay.com/api-docs/buy/marketplace-insights/overview.html), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/overview.html))
- **Access requirements — THIS IS THE BLOCKER:** "**This is a (Limited Release) API available only to select developers approved by business units.** For information on how to obtain access to this API in production, see the Buy APIs Requirements." ([item_sales/search reference](https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search)). The Buy APIs Requirements page states production use "is intended for eBay partners only. You must apply for production access through the eBay Partner Network... There is no guarantee that your application... will be approved." ([Buy APIs Requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html)). Additionally, "Partner allowed categories need to be vetted by business and then whitelisted for that partner." ([Overview](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/overview.html))
- **Meets the constraints?**
  - #1 No special approval: **FAILS** — explicitly Limited Release / partner-approved, plus per-category whitelisting.
  - #3 All sellers: Yes — searches sold items marketplace-wide.
  - #4 On-demand: Yes — a single GET.
- **Endpoint:** `GET https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search`
- **Key params:** `q` (keywords), `category_ids` (**required**, max 4; top-level L1 categories also require `q`/`epid`/`gtin`), `epid`, `gtin`, `filter`, `sort`, `limit` (max 200, default 50), `offset` (max 9,999), `fieldgroups`, `aspect_filter`. OAuth scope `https://api.ebay.com/oauth/api_scope/buy.marketplace.insights` (client-credentials grant). Header `X-EBAY-C-MARKETPLACE-ID` required. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search))
- **Sold-count relevance:** Each result returns **`itemSales.totalSoldQuantity`** ("The total number of this item that have been sold") and **`itemSales.lastSoldDate`** ("The date the last item was purchased within the last 90 days"). The response also has a top-level **`total`** ("The total number of items retrieved in the result set") — though eBay warns `total` is "just an indicator... It is strongly recommended that `total` not be used in pagination use cases." There is a **`lastSoldDate`** field filter for windowing. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search))
- **Limits:** "This method can return a maximum of **10,000 items** in one results set" (limit <= 200, offset <= 9,999). Sales history range: **up to 90 days**. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search), [Overview](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/overview.html)). Note: the default call-limits table does **not** list Marketplace Insights separately (it is not in the standard Buy API limit list), consistent with it being approval-gated rather than self-serve. ([API Call Limits](https://developer.ebay.com/support/api-call-limits), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/support/api-call-limits))

### 2. Finding API — `findCompletedItems`

- **What it is:** Legacy ("Traditional Searching") API. "Searches for items whose listings are completed and are no longer available for sale by category... by keywords... or a combination of the two." ([findCompletedItems reference](https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html))
- **Access requirements — BLOCKER:** "**This call is deprecated as of October 15, 2020, and access is restricted.** An alternative to findCompletedItems call is the Marketplace Insights API, but please note that this API is also restricted and requires eBay Business approval for access." ([findCompletedItems reference](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html)). eBay explicitly points you to Marketplace Insights — which is itself restricted.
- **Meets the constraints?**
  - #1 No special approval: **FAILS** — access is restricted post-deprecation.
  - #3 All sellers: Yes (when accessible) — searches completed listings marketplace-wide.
  - #4 On-demand: Yes.
- **The "clever count" workaround — and why it fails:** The classic trick is to call `findCompletedItems` with a sold filter and read **`paginationOutput.totalEntries`** ("The total number of items found that match the search criteria") to get a COUNT without downloading results. ([findCompletedItems reference](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html)). **Two problems:**
  1. The call is deprecated/restricted (above).
  2. The sold filter does not actually work. The item filter **`SoldItemsOnly`** is documented as: "**Reserved for future use.** If true, excludes all completed items which are not ended by being sold." ([ItemFilterType reference](https://developer.ebay.com/Devzone/finding/CallRef/types/ItemFilterType.html), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/Devzone/finding/CallRef/types/ItemFilterType.html)). "Reserved for future use" means it is not a functional filter. Sold status is instead only available per-item in the response via **`searchResult.item.sellingStatus.sellingState`**, whose values include `EndedWithSales` and `EndedWithoutSales` — i.e., you must **fetch items and count client-side**, you cannot get a filtered sold COUNT from `totalEntries`. ([findCompletedItems reference](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html))
- **Date filters:** The Finding API item filters include `EndTimeFrom` / `EndTimeTo` ("Limits the results to items ending on or after/before the specified time... Specify a time in the future") and `ModTimeFrom`. Note these are oriented to end-time; there is no "soldDate" filter. ([ItemFilterType reference](https://web.archive.org/web/2023/https://developer.ebay.com/Devzone/finding/CallRef/types/ItemFilterType.html))
- **Limits:** "There is a **5,000 limit on the number of findCompletedItems calls an application can make in a single day** (even if the application has completed an app check)." Pagination: `entriesPerPage` max **100**, `pageNumber` max **100** (at most ~10,000 items retrievable per query). Completed items only go back ~90 days. ([findCompletedItems reference](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html), [API Call Limits](https://web.archive.org/web/2023/https://developer.ebay.com/support/api-call-limits)). Also note eBay's ToS warning: "Ensure that you do not store the results retrieved from this call or **use the results for market research purposes**." ([findCompletedItems reference](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html))

### 3. Browse API — `item_summary/search` (Buy APIs)

- **What it is:** "Lets shoppers search eBay listings by keyword, category, GTIN, product, charity, compatibility criteria, or image, and refine results with filters." All methods require an Application access token (client-credentials grant). ([Browse API overview](https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/search))
- **Sold/completed data?** **No.** The search method returns *purchasable/active* listings: "Only listings where FIXED_PRICE (Buy It Now) is a buying option are returned by default... use the buyingOptions filter to retrieve those listings." It discusses checking `itemEndDate` / `estimatedAvailabilityStatus` to know if "the listing is available for purchase." There is **no sold, completed, or sales-history field or filter**. ([search reference](https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search); [Browse API static guide](https://developer.ebay.com/api-docs/buy/static/api-browse.html))
- **Meets the constraints?**
  - #1 No special approval: Yes for sandbox; **but** note the Buy APIs broadly are Limited Release for *production* ("The use of eBay's Buy APIs in production is intended for eBay partners only"). ([Buy APIs Requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html))
  - #3 All sellers: Active listings span all sellers — but **not sold** data.
  - #4 On-demand: Yes.
  - **Verdict:** Cannot produce a sold count at all (no sold data exposed).
- **Limits:** max **10,000 items** per query; default **5,000 calls/day** for Browse API. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search), [API Call Limits](https://web.archive.org/web/2023/https://developer.ebay.com/support/api-call-limits))

### 4. Feed API / Item feeds (Buy APIs)

- **What it is:** "Download an entire category of items... Download all the items listed in a specific day, category, and marketplace... Keep the item information up-to-date using hourly feed files." ([Feed Beta API overview](https://developer.ebay.com/api-docs/buy/feed/overview.html))
- **Completed-items feed?** **No.** The feeds are *active-item* / inventory feeds (category snapshots, daily new listings, item-group variations, hourly updates). There is **no sold/completed-items feed**. ([Feed Beta API overview](https://developer.ebay.com/api-docs/buy/feed/overview.html))
- **Access — BLOCKER:** "**This is a (Limited Release) API available only to select developers approved by business units.**" ([Feed Beta API overview](https://developer.ebay.com/api-docs/buy/feed/overview.html))
- **Meets the constraints?** Fails #1 (Limited Release) **and** provides no sold data anyway. Also it is a bulk-download model, closer to indexing than an on-demand count.

### 5. Sell Analytics API (traffic report, seller metrics)

- **What it is:** "Provides information about **an individual seller's business**... Traffic reports gives you insight in how buyers engage with **your listings**." ([Analytics API Overview](https://developer.ebay.com/api-docs/sell/analytics/overview.html), via [Wayback](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/sell/analytics/overview.html))
- **Meets the constraints?** **Fails #3** — it returns only the **authenticated seller's OWN** data, not all sellers. Not a cross-seller sold count. (Default 100 calls/day.) ([API Call Limits](https://web.archive.org/web/2023/https://developer.ebay.com/support/api-call-limits))

### 6. Terapeak / Product Research

- **What it is:** eBay's built-in product-research tool (sold-history charts, sell-through, average price) surfaced in Seller Hub.
- **API access?** **None found in the official API catalog.** eBay exposes no public Terapeak/Product-Research REST API; the only sanctioned programmatic sold-history access is the Marketplace Insights API (Section 1), which is partner-gated. Terapeak is effectively **UI-only**. (No developer.ebay.com API reference exists for it; the Buy/Sell API catalogs list no such resource — see [API Call Limits](https://web.archive.org/web/2023/https://developer.ebay.com/support/api-call-limits) for the full list of APIs, which contains no Terapeak/product-research entry.)

---

## What does NOT work, and why

- **findCompletedItems + SoldItemsOnly + read totalEntries for an instant count** — Fails twice: the call is **deprecated and access-restricted** (Oct 15, 2020), and **`SoldItemsOnly` is "Reserved for future use"** (a no-op), so `totalEntries` is the count of *all* completed items, not sold ones. Sold status is only per-item (`sellingStatus.sellingState = EndedWithSales`), forcing client-side fetching/counting. ([findCompletedItems](https://web.archive.org/web/2023/https://developer.ebay.com/DevZone/finding/CallRef/findCompletedItems.html), [ItemFilterType](https://web.archive.org/web/2023/https://developer.ebay.com/Devzone/finding/CallRef/types/ItemFilterType.html))
- **Browse API `search`** — returns **active/purchasable listings only**; no sold/completed data exists in the API. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search))
- **Feed API** — Limited Release (partner approval) **and** only active-item feeds; no completed-items feed. ([Feed overview](https://developer.ebay.com/api-docs/buy/feed/overview.html))
- **Sell Analytics / Order / Fulfillment APIs** — return **your own** sales/metrics only; cannot see other sellers. ([Analytics overview](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/sell/analytics/overview.html))
- **Marketplace Insights API** — the only true cross-seller sold-history API, but **Limited Release / partner-approved with per-category whitelisting**, so it violates the "no special partner approval" constraint. ([search reference](https://web.archive.org/web/2023/https://developer.ebay.com/api-docs/buy/marketplace-insights/resources/item_sales/methods/search), [Buy APIs Requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html))
- **Terapeak / Product Research** — no public API; UI-only.

## Bottom line

An **exact, on-demand, cross-seller SOLD count for an arbitrary product, using only a normal developer account with no eBay approval, is not available from any official eBay API.** The capability exists (Marketplace Insights API) but is deliberately gated behind eBay partner/business approval. The legacy self-serve path (`findCompletedItems`) was deprecated/restricted and its sold filter never worked. To get real sold counts you must either **obtain Marketplace Insights approval** (dropping constraint #1) or use a **third-party sold-data provider** (outside official eBay APIs).
