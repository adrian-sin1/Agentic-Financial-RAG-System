# Financial analytics

A standalone analysis of the `financial_metrics` data the main RAG pipeline
ingests — not part of the live app, just an offline script producing two
charts from the same Snowflake warehouse.

## Run it

```bash
pip install -r analytics/requirements.txt   # separate from the main app's deps
python analytics/financial_analysis.py
```

Outputs two PNGs to `analytics/output/`.

## What it does, and why the data shapes the approach

**Regression** — net income vs. revenue, across all 5 companies x 2 fiscal
years (10 observations). This is intentionally cross-sectional, not a
per-company time trend: with only FY2024 and FY2025 ingested so far, a
time-series regression per company would just be a line through 2 points
(R²=1 by construction, not a meaningful result).

**Clustering** — K-means (k=3) on each company-year's standardized financial
profile (revenue, net income, total assets, diluted EPS), visualized via PCA
projected to 2D.

## What it actually found

The regression comes back with R² ≈ 0 — revenue essentially doesn't predict
net income across this set of companies. That's a real result, not a bug:
Amazon has by far the highest revenue but only mid-tier profit (thin retail
margins), while Meta has the lowest revenue but comparable profit to Amazon
(high-margin advertising business). Company size alone doesn't explain
profitability here — margin structure does.

The clustering reflects that split cleanly: Apple, Microsoft, and Alphabet
group together (similar high-margin, large-cap profile), while Amazon and
Meta each form their own singleton cluster — consistent with the regression
finding, from an unsupervised angle instead of a supervised one.
