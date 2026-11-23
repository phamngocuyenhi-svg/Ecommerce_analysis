"""
CAU 6 - PHAN TICH ANH HUONG CUA DISCOUNT
Du an: Ecommerce_analysis

Noi dung:
1. Phan tich Discount anh huong den Quantity va gia tri giao dich.
2. Phan nhom muc chiet khau.
3. Thong ke theo tung nhom.
4. Kiem dinh Spearman va Kruskal-Wallis.
5. Ve Boxplot va xuat ket qua.

Cach chay (tu thu muc goc Ecommerce_analysis):
    pip install -r requirements.txt
    python cau6_discount_analysis.py

Du lieu su dung: data_processed/orders_cleaned.csv
"""

from pathlib import Path
import pandas as pd
from scipy import stats
import plotly.express as px

# ======================= CAU HINH =======================
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data_processed" / "orders_cleaned.csv"
OUTPUT_DIR = BASE_DIR / "reports" / "cau6_discount"
DISCOUNT_COL = "discount_pct"
QUANTITY_COL = "quantity"
AMOUNT_COL = "total_amount_usd"
ORDER_ID_COL = "order_id"
# ========================================================


def load_data():
    """Doc du lieu va kiem tra cac cot can thiet."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Khong tim thay file: {DATA_FILE}\n"
            "Hay dat cau6_discount_analysis.py tai thu muc goc Ecommerce_analysis."
        )

    df = pd.read_csv(DATA_FILE)
    required = [DISCOUNT_COL, QUANTITY_COL, AMOUNT_COL]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Thieu cot trong orders_cleaned.csv: {missing}")

    # Chuyen cac cot phan tich ve dang so
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=required).copy()
    df = df[
        (df[DISCOUNT_COL] >= 0)
        & (df[DISCOUNT_COL] <= 100)
        & (df[QUANTITY_COL] >= 0)
        & (df[AMOUNT_COL] >= 0)
    ].copy()

    print(f"So dong du lieu ban dau: {before:,}")
    print(f"So dong hop le duoc su dung: {len(df):,}")
    print(f"So dong bi loai do thieu/sai du lieu: {before - len(df):,}")
    return df


def add_discount_groups(df):
    """Chia Discount thanh 5 nhom theo phan tram."""
    bins = [-0.001, 0, 10, 20, 30, 100]
    labels = [
        "0% (Khong giam)",
        "1-10%",
        "11-20%",
        "21-30%",
        "Tren 30%",
    ]
    df["discount_group"] = pd.cut(
        df[DISCOUNT_COL],
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=True,
    )
    return df, labels


def make_summary(df):
    """Tinh cac chi so thong ke theo nhom Discount."""
    summary = (
        df.groupby("discount_group", observed=False)
        .agg(
            so_giao_dich=(QUANTITY_COL, "size"),
            so_luong_trung_binh=(QUANTITY_COL, "mean"),
            so_luong_trung_vi=(QUANTITY_COL, "median"),
            gia_tri_trung_binh=(AMOUNT_COL, "mean"),
            gia_tri_trung_vi=(AMOUNT_COL, "median"),
            tong_gia_tri_giao_dich=(AMOUNT_COL, "sum"),
            discount_trung_binh=(DISCOUNT_COL, "mean"),
        )
        .round(2)
    )
    summary["ty_trong_giao_dich_pct"] = (
        summary["so_giao_dich"] / summary["so_giao_dich"].sum() * 100
    ).round(2)
    return summary


def run_tests(df):
    """Kiem dinh tuong quan Spearman va khac biet giua cac nhom."""
    rho_qty, p_qty = stats.spearmanr(df[DISCOUNT_COL], df[QUANTITY_COL])
    rho_amount, p_amount = stats.spearmanr(df[DISCOUNT_COL], df[AMOUNT_COL])

    qty_groups = [
        group[QUANTITY_COL].values
        for _, group in df.groupby("discount_group", observed=True)
        if len(group) > 0
    ]
    amount_groups = [
        group[AMOUNT_COL].values
        for _, group in df.groupby("discount_group", observed=True)
        if len(group) > 0
    ]

    kw_qty = stats.kruskal(*qty_groups) if len(qty_groups) >= 2 else None
    kw_amount = stats.kruskal(*amount_groups) if len(amount_groups) >= 2 else None

    return {
        "spearman_quantity": (rho_qty, p_qty),
        "spearman_amount": (rho_amount, p_amount),
        "kruskal_quantity": kw_qty,
        "kruskal_amount": kw_amount,
    }


def create_boxplots(df, labels):
    """Ve Boxplot bang Plotly (HTML) va luu PNG bang Matplotlib."""
    import matplotlib.pyplot as plt

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig_qty = px.box(
        df,
        x="discount_group",
        y=QUANTITY_COL,
        category_orders={"discount_group": labels},
        points="outliers",
        title="Phan phoi so luong san pham theo nhom Discount",
        labels={
            "discount_group": "Nhom chiet khau",
            QUANTITY_COL: "So luong san pham",
        },
    )
    fig_qty.update_layout(showlegend=False, template="plotly_white")
    fig_qty.write_html(OUTPUT_DIR / "boxplot_quantity.html")

    fig_amount = px.box(
        df,
        x="discount_group",
        y=AMOUNT_COL,
        category_orders={"discount_group": labels},
        points="outliers",
        title="Phan phoi gia tri giao dich theo nhom Discount",
        labels={
            "discount_group": "Nhom chiet khau",
            AMOUNT_COL: "Gia tri giao dich (USD)",
        },
    )
    fig_amount.update_layout(showlegend=False, template="plotly_white")
    fig_amount.write_html(OUTPUT_DIR / "boxplot_amount.html")

    # Luu them PNG bang Matplotlib de khong phu thuoc vao Kaleido.
    fig, ax = plt.subplots(figsize=(10, 6))
    qty_data = [df.loc[df["discount_group"] == label, QUANTITY_COL].dropna() for label in labels]
    ax.boxplot(qty_data, labels=labels, showfliers=True)
    ax.set_title("Phan phoi so luong san pham theo nhom Discount")
    ax.set_xlabel("Nhom chiet khau")
    ax.set_ylabel("So luong san pham")
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=15)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "boxplot_quantity.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    amount_data = [df.loc[df["discount_group"] == label, AMOUNT_COL].dropna() for label in labels]
    ax.boxplot(amount_data, labels=labels, showfliers=True)
    ax.set_title("Phan phoi gia tri giao dich theo nhom Discount")
    ax.set_xlabel("Nhom chiet khau")
    ax.set_ylabel("Gia tri giao dich (USD)")
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=15)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "boxplot_amount.png", dpi=180)
    plt.close(fig)


def save_and_print_results(df, summary, tests):
    """Luu bang ket qua va tao nhan xet dua tren so lieu."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(
        OUTPUT_DIR / "discount_summary.csv",
        encoding="utf-8-sig",
    )

    rho_qty, p_qty = tests["spearman_quantity"]
    rho_amount, p_amount = tests["spearman_amount"]
    kw_qty = tests["kruskal_quantity"]
    kw_amount = tests["kruskal_amount"]

    lines = [
        "KET QUA PHAN TICH CAU 6 - DISCOUNT",
        f"Tong so giao dich: {len(df):,}",
        "",
        "1. SPEARMAN",
        f"Discount - Quantity: rho={rho_qty:.4f}, p={p_qty:.6g}",
        f"Discount - Total amount: rho={rho_amount:.4f}, p={p_amount:.6g}",
        "",
        "2. KRUSKAL-WALLIS",
        f"Quantity: H={kw_qty.statistic:.4f}, p={kw_qty.pvalue:.6g}" if kw_qty else "Quantity: khong du nhom",
        f"Total amount: H={kw_amount.statistic:.4f}, p={kw_amount.pvalue:.6g}" if kw_amount else "Total amount: khong du nhom",
        "",
        "3. NHAN XET GOI Y",
    ]

    if p_qty < 0.05:
        lines.append("Discount co moi lien he don dieu co y nghia thong ke voi Quantity (Spearman p < 0.05).")
    else:
        lines.append("Chua co bang chung ve moi lien he don dieu co y nghia thong ke giua Discount va Quantity (Spearman p >= 0.05).")

    if rho_amount < 0:
        lines.append("He so Spearman am: Discount tang thi gia tri giao dich co xu huong giam.")
    elif rho_amount > 0:
        lines.append("He so Spearman duong: Discount tang thi gia tri giao dich co xu huong tang.")
    else:
        lines.append("He so Spearman bang 0: khong the hien xu huong tuong quan don dieu.")

    if p_amount < 0.05:
        lines.append("Moi lien he Discount - gia tri giao dich co y nghia thong ke (p < 0.05).")
    else:
        lines.append("Moi lien he Discount - gia tri giao dich khong co y nghia thong ke (p >= 0.05).")

    if kw_qty and kw_qty.pvalue < 0.05:
        lines.append("So luong giao dich co su khac biet co y nghia thong ke giua cac nhom Discount.")
    else:
        lines.append("Chua thay su khac biet co y nghia thong ke ve Quantity giua cac nhom Discount.")

    if kw_amount and kw_amount.pvalue < 0.05:
        lines.append("Gia tri giao dich co su khac biet co y nghia thong ke giua cac nhom Discount.")
    else:
        lines.append("Chua thay su khac biet co y nghia thong ke ve gia tri giao dich giua cac nhom Discount.")

    best = summary["gia_tri_trung_vi"].idxmax()
    lowest = summary["gia_tri_trung_vi"].idxmin()
    lines.append(f"Nhom co trung vi gia tri giao dich cao nhat: {best}.")
    lines.append(f"Nhom co trung vi gia tri giao dich thap nhat: {lowest}.")
    lines.append("")
    lines.append("Luu y: Ket qua the hien moi lien he/khac biet, khong tu dong chung minh Discount la nguyen nhan truc tiep.")

    result_text = "\n".join(lines)
    (OUTPUT_DIR / "cau6_nhan_xet.txt").write_text(result_text, encoding="utf-8")

    print("\n=== BANG THONG KE THEO NHOM DISCOUNT ===")
    print(summary.to_string())
    print("\n" + result_text)


def main():
    df = load_data()
    df, labels = add_discount_groups(df)
    summary = make_summary(df)
    tests = run_tests(df)
    save_and_print_results(df, summary, tests)
    create_boxplots(df, labels)

    print(f"\nDa xuat ket qua tai: {OUTPUT_DIR}")
    print("Bao gom: discount_summary.csv, cau6_nhan_xet.txt, 2 Boxplot HTML va PNG.")


if __name__ == "__main__":
    main()
