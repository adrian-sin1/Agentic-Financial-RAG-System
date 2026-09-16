"""Standalone analytics on financial_metrics: does profitability scale with
company size (regression), and which company-years look financially similar
(clustering)? Not part of the live app -- a offline analysis script that
reads from the same Snowflake warehouse the RAG pipeline writes to.

Run from the project root: python analytics/financial_analysis.py
Requires analytics/requirements.txt installed separately from the main app.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib

matplotlib.use("Agg")  # headless -- we only save PNGs, never show a window
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from src.db.connection import get_snowflake_connection  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
FEATURES = ["revenue", "net_income", "total_assets", "eps_diluted"]


def load_financials() -> pd.DataFrame:
    """One row per (company, year), one column per metric -- 10 observations
    across 5 companies x 2 fiscal years."""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    cur.execute("SELECT company, year, metric_name, metric_value FROM financial_metrics")
    rows = cur.fetchall()
    conn.close()

    long_df = pd.DataFrame(rows, columns=["company", "year", "metric_name", "metric_value"])
    wide_df = long_df.pivot(index=["company", "year"], columns="metric_name", values="metric_value")
    return wide_df.reset_index()


def plot_regression(df: pd.DataFrame):
    """Does net income scale with revenue across companies? Cross-sectional
    (10 company-year points), not a time trend -- a per-company time series
    here would just be a line through 2 points, which isn't a meaningful
    regression.
    """
    x = df[["revenue"]].values
    y = df["net_income"].values

    model = LinearRegression().fit(x, y)
    r_squared = model.score(x, y)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df["revenue"], df["net_income"], s=80, color="#2a78d6", zorder=3)
    for _, row in df.iterrows():
        ax.annotate(f"{row['company']} {int(row['year'])}", (row["revenue"], row["net_income"]), fontsize=8, xytext=(6, 6), textcoords="offset points")

    x_line = np.linspace(x.min(), x.max(), 100).reshape(-1, 1)
    ax.plot(x_line, model.predict(x_line), color="#c0392b", linewidth=2, label=f"OLS fit (R²={r_squared:.2f})")

    billions = matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1e9:.0f}B")
    ax.xaxis.set_major_formatter(billions)
    ax.yaxis.set_major_formatter(billions)
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Net income")
    ax.set_title("Net income vs. revenue across 5 companies (FY2024–FY2025)")
    ax.legend()
    fig.tight_layout()

    path = os.path.join(OUTPUT_DIR, "regression_revenue_vs_net_income.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Regression: R²={r_squared:.3f}, slope={model.coef_[0]:.4f}  ->  {path}")


def plot_clustering(df: pd.DataFrame, n_clusters: int = 3):
    """K-means on standardized financial profile (revenue, net income, total
    assets, diluted EPS) -- which company-years group together? Visualized
    via PCA down to 2D since we can't plot 4 dimensions directly.
    """
    X = df[FEATURES].values
    X_scaled = StandardScaler().fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(X_scaled)
    labels = kmeans.labels_

    coords = PCA(n_components=2, random_state=0).fit_transform(X_scaled)

    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10", s=90, zorder=3)
    for i, row in df.iterrows():
        ax.annotate(f"{row['company']} {int(row['year'])}", (coords[i, 0], coords[i, 1]), fontsize=8, xytext=(6, 6), textcoords="offset points")

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(f"K-means clusters (k={n_clusters}) on financial profile, PCA-projected")
    legend = ax.legend(*scatter.legend_elements(), title="Cluster")
    ax.add_artist(legend)
    fig.tight_layout()

    path = os.path.join(OUTPUT_DIR, "clustering_financial_profile.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Clustering: {n_clusters} clusters  ->  {path}")
    for cluster_id in sorted(set(labels)):
        members = df.loc[labels == cluster_id, ["company", "year"]]
        names = ", ".join(f"{r.company} {int(r.year)}" for r in members.itertuples())
        print(f"  cluster {cluster_id}: {names}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_financials()
    print(f"Loaded {len(df)} company-year observations\n")
    plot_regression(df)
    plot_clustering(df)


if __name__ == "__main__":
    main()
