# Measured results (2026-10-01)

Demo store: 56 products, 3 fictitious competitor websites, 142 product pages tracked.

| Metric | Result |
|---|---|
| Prices read live today that match the page exactly | **142 of 142 (100.0%)** |
| Stock status read correctly | 100.0% |
| Pages read successfully today | 100.0% |
| Pages read successfully, last 7 days | 100.0% |
| Time for a full check of all pages | 4.0 s (demo shops, no delay; real sites are read 1.5 s apart per site) |
| Competitor price changes detected, last 7 days | 91 |
| Alerts raised, last 7 days | 54 (14 price drop, 14 price increase, 10 out of stock, 8 cheaper than you, 7 back in stock, 1 new product) |
| Example insight | MobiMart undercut or cut prices on 43 of your products in one week (2026-09-11 to 2026-09-17). |
| Manual checking avoided | about 12.4 hours per week (at 45 s per page, daily) |

**Honest notes**

- Today's prices were collected live over HTTP from the three demo shop websites by the real collector (JSON-LD, microdata and a custom CSS selector). History before today was simulated with the same price model, so weekly figures describe the demo market, not a real one.
- The collector was also tested on books.toscrape.com (a public site made for scraping practice): price, stock and title were read correctly with a custom selector.
- With real competitors, websites can change or block bots. The Competitors page shows success rates per site so problems are spotted the same day.
