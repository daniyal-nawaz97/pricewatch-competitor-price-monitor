# Case study: 56 products, 3 competitors, one morning report

> Built on a fictitious demo store (GadgetHub.pk) and fictitious competitor websites. After a real pilot, copy this page and replace the numbers with the client's measured results (template below).

## Problem
An online mobile-accessories store sells 56 products that three competitors also sell. Someone on the team opens competitor websites a few times a week to compare prices: 142 product pages, roughly 45 seconds each. Price cuts are noticed days late, stock-outs (chances to sell more) are missed, and nobody knows which competitor moves first.

## Solution
PriceWatch reads all 142 competitor pages every morning, compares them with the store's own prices, and sends one short report. The team sees where they're cheapest or most expensive, gets alerts when a competitor undercuts them by more than 5% or a top product goes out of stock, and can open a full price history for any product.

## Result (measured with `scripts/evaluate.py`)

| | Before | With PriceWatch |
|---|---|---|
| Time spent checking prices | ~12 hours a week (if done daily) | 0. It runs at 7 am, full check in seconds |
| Accuracy of collected prices | depends on the person | **142 of 142** live prices read exactly right; stock 100% |
| Price changes noticed in a week | a handful | **91** changes caught |
| Competitor behaviour | guesswork | "MobiMart cut prices on 43 products in one week"; "TechBazaar undercut 12 products in a price war" |
| Where you stand | unknown | cheapest on 18 products, middle on 30, most expensive on 7, every day |

## Screenshot
![Product price history](screenshots/product.png)

## Link
Live demo: *(your deployed URL)* → **View demo store**

---

### Template for a real client case study
- **Client:** type of store, number of products, competitors tracked (name only with permission)
- **Problem:** how they checked prices before, how long it took
- **Solution:** products and competitors tracked, alert rules, report recipients
- **Result:** data success rate · price changes detected per week · hours saved · one concrete insight · (if they acted on it) change in sales or margin, **measured only**
- **Quote** and **screenshot** of their morning report
