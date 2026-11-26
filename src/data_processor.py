"""Đọc dữ liệu sạch trong data/cleaned/ và tính toán các bảng tổng hợp phục vụ Dashboard.

Các hàm tính toán là hàm thuần (nhận DataFrame, trả DataFrame) dùng trực tiếp
trong dashboard tương tác (app.py) và trình xuất dashboard tĩnh (export_html.py).
Logic tổng hợp bám sát notebook của nhóm (notebooks/01..10); quy ước loại đơn nằm ở config.py.
"""
from __future__ import annotations

from math import comb

import numpy as np
import pandas as pd
from scipy import stats

from . import config as cfg
from .config import CustomerCol as C
from .config import MonthlyCol as M
from .config import OrderCol as O


# ======================================================================
# 1. ĐỌC DỮ LIỆU
# ======================================================================
def _require(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Bảng {name} thiếu cột bắt buộc: {missing}")


def load_cleaned(name: str) -> pd.DataFrame:
    """Đọc một bảng trong data/cleaned/ (name: orders, customers, monthly_revenue, product_summary)."""
    if name not in cfg.CLEANED_FILES:
        raise KeyError(f"Không có bảng '{name}'. Hợp lệ: {list(cfg.CLEANED_FILES)}")
    path = cfg.DATA_CLEANED / cfg.CLEANED_FILES[name]
    if not path.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy {path}. Hãy chạy notebooks/00_data_cleaning.ipynb để tạo dữ liệu sạch."
        )
    df = pd.read_csv(path)
    if name == "orders":
        df[O.ORDER_DATE] = pd.to_datetime(df[O.ORDER_DATE])
    return df


def load_all() -> dict[str, pd.DataFrame]:
    """Đọc 4 bảng dữ liệu sạch."""
    return {name: load_cleaned(name) for name in cfg.CLEANED_FILES}


# ======================================================================
# 2. BẢNG SỰ KIỆN (đơn hàng + thuộc tính khách hàng)
# ======================================================================
def build_fact_orders(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Ghép đơn hàng với quốc gia, kênh thu hút, hạng thành viên của khách hàng.

    Đây là bảng nguồn cho bộ lọc chéo trong dashboard: lọc bảng này rồi gọi lại
    các hàm tổng hợp bên dưới.
    """
    _require(orders, [O.ORDER_ID, O.CUSTOMER_ID, O.ORDER_DATE, O.ORDER_STATUS, O.TOTAL_AMOUNT], "orders")
    _require(customers, [C.CUSTOMER_ID, C.COUNTRY, C.ACQUISITION_CHANNEL, C.MEMBERSHIP_TIER], "customers")
    attrs = customers[[C.CUSTOMER_ID, C.COUNTRY, C.ACQUISITION_CHANNEL, C.MEMBERSHIP_TIER]]
    fact = orders.merge(attrs, on=C.CUSTOMER_ID, how="left", validate="many_to_one")
    unmatched = int(fact[C.COUNTRY].isna().sum())
    if unmatched:
        raise ValueError(f"{unmatched} đơn hàng không khớp khách hàng nào trong bảng customers.")
    fact[O.ORDER_DATE] = pd.to_datetime(fact[O.ORDER_DATE])
    fact["order_month"] = fact[O.ORDER_DATE].dt.to_period("M").dt.to_timestamp()
    fact["is_delivered"] = (fact[O.ORDER_STATUS] == cfg.STATUS_DELIVERED).astype(int)
    return fact


# ======================================================================
# 3. CÁC BẢNG TỔNG HỢP THEO TỪNG CÂU
# ======================================================================
# --- Câu 1: KPI tổng quan (tất cả đơn hàng) ---------------------------
def kpi_overview(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{
        "total_orders": orders[O.ORDER_ID].nunique(),
        "customers_with_orders": orders[O.CUSTOMER_ID].nunique(),
        "countries": customers[C.COUNTRY].nunique(),
        "categories": orders[O.CATEGORY].nunique(),
        "total_revenue_usd": round(orders[O.TOTAL_AMOUNT].sum(), 2),
    }])


# --- Câu 2: xu hướng và tính thời vụ (từ monthly_revenue, chỉ đơn Delivered) ---
def monthly_trend(monthly: pd.DataFrame) -> pd.DataFrame:
    _require(monthly, [M.YEAR, M.MONTH, M.REVENUE], "monthly_revenue")
    out = monthly.sort_values([M.YEAR, M.MONTH]).reset_index(drop=True).copy()
    out["period"] = pd.to_datetime(dict(year=out[M.YEAR], month=out[M.MONTH], day=1))
    out["revenue_ma"] = out[M.REVENUE].rolling(cfg.MOVING_AVERAGE_WINDOW).mean().round(2)
    return out


def monthly_revenue_from_fact(fact: pd.DataFrame) -> pd.DataFrame:
    """Doanh thu Delivered theo tháng tính lại từ bảng sự kiện (khớp monthly_revenue_cleaned khi chưa lọc).

    Dùng cho dashboard để doanh thu theo tháng phản ứng với bộ lọc quốc gia, nhóm hàng, kênh...
    Các tháng không có đơn Delivered trong khoảng dữ liệu được lấp bằng 0 để đường trung bình trượt không bị lệch.
    """
    cols = [M.YEAR, M.MONTH, M.REVENUE]
    if fact.empty:
        return pd.DataFrame(columns=cols)
    delivered = fact[fact[O.ORDER_STATUS] == cfg.STATUS_DELIVERED]
    by_month = delivered.groupby("order_month")[O.TOTAL_AMOUNT].sum()
    grid = pd.date_range(fact["order_month"].min(), fact["order_month"].max(), freq="MS")
    by_month = by_month.reindex(grid, fill_value=0.0)
    return pd.DataFrame({M.YEAR: grid.year, M.MONTH: grid.month, M.REVENUE: by_month.to_numpy().round(2)})


def monthly_seasonality(monthly: pd.DataFrame, years: tuple[int, int] = cfg.SEASONALITY_YEARS) -> pd.DataFrame:
    _require(monthly, [M.YEAR, M.MONTH, M.REVENUE], "monthly_revenue")
    data = monthly[monthly[M.YEAR].between(*years)]
    out = data.groupby(M.MONTH, as_index=False)[M.REVENUE].mean()
    return out.rename(columns={M.REVENUE: "avg_revenue_usd"}).round(2)


# --- Câu 3: xếp hạng doanh thu theo quốc gia / nhóm hàng (chỉ đơn Delivered) ---
def revenue_ranking(fact: pd.DataFrame, by: str) -> pd.DataFrame:
    """Doanh thu, số đơn, AOV, tỷ trọng và tỷ trọng tích lũy theo `by` (country hoặc category)."""
    delivered = fact[fact[O.ORDER_STATUS] == cfg.STATUS_DELIVERED]
    if delivered.empty:
        return pd.DataFrame(columns=["rank", by, "revenue_usd", "orders", "avg_order_value_usd", "share_pct", "cum_share_pct"])
    total = delivered[O.TOTAL_AMOUNT].sum()
    out = (
        delivered.groupby(by)
        .agg(
            revenue_usd=(O.TOTAL_AMOUNT, "sum"),
            orders=(O.ORDER_ID, "count"),
            avg_order_value_usd=(O.TOTAL_AMOUNT, "mean"),
        )
        .sort_values("revenue_usd", ascending=False)  # xếp giảm dần TRƯỚC khi cộng dồn
    )
    out["share_pct"] = (out["revenue_usd"] / total * 100) if total > 0 else 0.0
    out["cum_share_pct"] = out["share_pct"].cumsum()
    out.insert(0, "rank", range(1, len(out) + 1))
    return out.reset_index().round(2)


def country_category_revenue(fact: pd.DataFrame) -> pd.DataFrame:
    """Doanh thu Delivered theo cặp (quốc gia, nhóm hàng) và tỷ trọng trong tổng doanh thu của quốc gia."""
    delivered = fact[fact[O.ORDER_STATUS] == cfg.STATUS_DELIVERED]
    out = (
        delivered.groupby([C.COUNTRY, O.CATEGORY], as_index=False)
        .agg(revenue_usd=(O.TOTAL_AMOUNT, "sum"), orders=(O.ORDER_ID, "count"))
    )
    country_totals = out.groupby(C.COUNTRY)["revenue_usd"].transform("sum")
    out["share_in_country_pct"] = np.where(country_totals > 0, out["revenue_usd"] / country_totals * 100, 0.0)
    return out.round(2)


# --- Câu 4: churn theo kênh thu hút -----------------------------------
def churn_by_channel(customers: pd.DataFrame) -> pd.DataFrame:
    _require(customers, [C.ACQUISITION_CHANNEL, C.CHURNED], "customers")
    out = customers.groupby(C.ACQUISITION_CHANNEL).agg(
        total_customers=(C.CHURNED, "count"),
        churned_customers=(C.CHURNED, "sum"),
    )
    out["retained_customers"] = out["total_customers"] - out["churned_customers"]
    out["churn_rate_pct"] = (out["churned_customers"] / out["total_customers"] * 100).round(2)
    return out.reset_index()


def churn_channel_test(customers: pd.DataFrame) -> dict | None:
    """Kiểm định chi-bình phương: tỷ lệ churn có khác nhau giữa các kênh thu hút không (Câu 4).

    Trả về {"chi2", "p_value", "dof"}; None nếu không đủ dữ liệu (dưới 2 kênh hoặc dưới 2 giá trị churn).
    """
    _require(customers, [C.ACQUISITION_CHANNEL, C.CHURNED], "customers")
    table = pd.crosstab(customers[C.ACQUISITION_CHANNEL], customers[C.CHURNED])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None
    chi2, p_value, dof, _ = stats.chi2_contingency(table)
    return {"chi2": float(chi2), "p_value": float(p_value), "dof": int(dof)}


# --- Câu 5: Frequency / Monetary ở cấp khách hàng ---------------------
def customer_frequency_monetary(
    orders: pd.DataFrame, exclude_status: tuple[str, ...] = cfg.STATUS_EXCLUDED_NET
) -> pd.DataFrame:
    """Mỗi dòng = 1 khách hàng: frequency (số đơn), monetary (tổng chi tiêu), aov, cờ ngoại lai IQR của Monetary."""
    _require(orders, [O.ORDER_ID, O.CUSTOMER_ID, O.ORDER_STATUS, O.TOTAL_AMOUNT], "orders")
    valid = orders[~orders[O.ORDER_STATUS].isin(exclude_status)]
    if valid.empty:
        return pd.DataFrame(columns=[O.CUSTOMER_ID, "frequency", "monetary", "is_monetary_outlier", "aov"])
    out = valid.groupby(O.CUSTOMER_ID, as_index=False).agg(
        frequency=(O.ORDER_ID, "nunique"),
        monetary=(O.TOTAL_AMOUNT, "sum"),
    )
    q1, q3 = out["monetary"].quantile([0.25, 0.75])
    upper = q3 + cfg.IQR_MULTIPLIER * (q3 - q1)
    out["is_monetary_outlier"] = out["monetary"] > upper
    out["aov"] = (out["monetary"] / out["frequency"]).round(2)
    out["monetary"] = out["monetary"].round(2)
    return out


def revenue_concentration(customer_fm: pd.DataFrame) -> pd.DataFrame:
    """Tỷ trọng Monetary của top 1%, 5%, 10%, 20% khách chi tiêu cao nhất."""
    if customer_fm.empty:
        return pd.DataFrame(columns=["top_customer_pct", "customers", "revenue_share_pct"])
    sorted_m = customer_fm["monetary"].sort_values(ascending=False).reset_index(drop=True)
    total = sorted_m.sum()
    rows = []
    for pct in cfg.CONCENTRATION_PERCENTS:
        n = max(int(np.ceil(len(sorted_m) * pct / 100)), 1)
        share = round(sorted_m.head(n).sum() / total * 100, 2) if total > 0 else 0.0
        rows.append({
            "top_customer_pct": pct,
            "customers": n,
            "revenue_share_pct": share,
        })
    return pd.DataFrame(rows)


# --- Câu 6: ảnh hưởng của Discount ------------------------------------
def clean_discount_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Chuyển về dạng số và loại dòng thiếu/sai theo cách làm của notebook Câu 6."""
    cols = [O.DISCOUNT_PCT, O.QUANTITY, O.TOTAL_AMOUNT]
    _require(orders, cols, "orders")
    df = orders.copy()
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=cols)
    return df[
        df[O.DISCOUNT_PCT].between(0, 100) & (df[O.QUANTITY] >= 0) & (df[O.TOTAL_AMOUNT] >= 0)
    ].copy()


def add_discount_group(df: pd.DataFrame) -> pd.DataFrame:
    """Thêm cột discount_group (5 nhóm chiết khấu)."""
    out = df.copy()
    out["discount_group"] = pd.cut(
        out[O.DISCOUNT_PCT], bins=cfg.DISCOUNT_BINS, labels=cfg.DISCOUNT_LABELS,
        include_lowest=True, right=True,
    )
    return out


def discount_group_summary(orders: pd.DataFrame) -> pd.DataFrame:
    df = add_discount_group(clean_discount_orders(orders))
    out = df.groupby("discount_group", observed=False).agg(
        orders=(O.QUANTITY, "size"),
        avg_quantity=(O.QUANTITY, "mean"),
        median_quantity=(O.QUANTITY, "median"),
        avg_amount_usd=(O.TOTAL_AMOUNT, "mean"),
        median_amount_usd=(O.TOTAL_AMOUNT, "median"),
        total_amount_usd=(O.TOTAL_AMOUNT, "sum"),
        avg_discount_pct=(O.DISCOUNT_PCT, "mean"),
    )
    total_orders = out["orders"].sum()
    out["order_share_pct"] = (out["orders"] / total_orders * 100) if total_orders > 0 else 0.0
    return out.round(2).reset_index()


def discount_tests(orders: pd.DataFrame) -> pd.DataFrame:
    """Kiểm định Spearman (Discount với Quantity/Amount) và Kruskal–Wallis giữa các nhóm Discount."""
    df = add_discount_group(clean_discount_orders(orders))
    rows = []
    for variable, col in (("Quantity", O.QUANTITY), ("Amount", O.TOTAL_AMOUNT)):
        rho = stats.spearmanr(df[O.DISCOUNT_PCT], df[col])
        rows.append({"test": "Spearman rho", "variable": variable,
                     "statistic": rho.statistic, "p_value": rho.pvalue})
    for variable, col in (("Quantity", O.QUANTITY), ("Amount", O.TOTAL_AMOUNT)):
        groups = [g[col].to_numpy() for _, g in df.groupby("discount_group", observed=True) if len(g)]
        if len(groups) >= 2:
            kw = stats.kruskal(*groups)
            rows.append({"test": "Kruskal-Wallis H", "variable": variable,
                         "statistic": kw.statistic, "p_value": kw.pvalue})
        else:
            rows.append({"test": "Kruskal-Wallis H", "variable": variable,
                         "statistic": np.nan, "p_value": np.nan})
    return pd.DataFrame(rows).round(6)


# --- Câu 7: vận chuyển theo quốc gia (tất cả đơn hàng) ----------------
def shipping_by_country(fact: pd.DataFrame) -> pd.DataFrame:
    _require(fact, [C.COUNTRY, O.SHIPPING_FEE, O.DELIVERY_DAYS], "fact_orders")
    out = (
        fact.groupby(C.COUNTRY, as_index=False)
        .agg(
            orders=(O.ORDER_ID, "count"),
            avg_shipping_fee_usd=(O.SHIPPING_FEE, "mean"),
            avg_delivery_days=(O.DELIVERY_DAYS, "mean"),
        )
        .sort_values("avg_shipping_fee_usd", ascending=False)
    )
    return out.round(3).reset_index(drop=True)


# --- Câu 8: return rate và rating theo nhóm hàng (tất cả đơn hàng) ----
def category_performance(fact: pd.DataFrame) -> pd.DataFrame:
    _require(fact, [O.CATEGORY, O.RETURNED, O.RATING, O.DELIVERY_DAYS, O.SHIPPING_FEE], "fact_orders")
    out = (
        fact.groupby(O.CATEGORY, as_index=False)
        .agg(
            orders=(O.ORDER_ID, "count"),
            revenue_usd=(O.TOTAL_AMOUNT, "sum"),
            return_rate_pct=(O.RETURNED, lambda x: x.mean() * 100),
            avg_rating=(O.RATING, "mean"),
            avg_delivery_days=(O.DELIVERY_DAYS, "mean"),
            avg_shipping_fee_usd=(O.SHIPPING_FEE, "mean"),
        )
        .sort_values("return_rate_pct", ascending=False)
    )
    return out.round(3).reset_index(drop=True)


def country_category_return(fact: pd.DataFrame) -> pd.DataFrame:
    """Tỷ lệ hoàn trả theo cặp (quốc gia, nhóm hàng) - dữ liệu cho Heatmap Câu 8."""
    out = fact.groupby([C.COUNTRY, O.CATEGORY], as_index=False).agg(
        orders=(O.ORDER_ID, "count"),
        return_rate_pct=(O.RETURNED, lambda x: x.mean() * 100),
    )
    return out.round(2)


# --- Câu 9: khách chi tiêu cao nhất -----------------------------------
def top_customers(customers: pd.DataFrame, n: int = cfg.TOP_N_CUSTOMERS) -> pd.DataFrame:
    cols = [C.CUSTOMER_ID, C.COUNTRY, C.MEMBERSHIP_TIER, C.TOTAL_ORDERS, C.TOTAL_SPEND, C.CHURNED]
    _require(customers, cols, "customers")
    out = customers.sort_values(C.TOTAL_SPEND, ascending=False).head(n).reset_index(drop=True)[cols]
    out.insert(0, "rank", out.index + 1)
    return out


def top_customers_summary(customers: pd.DataFrame, n: int = cfg.TOP_N_CUSTOMERS) -> pd.DataFrame:
    """So sánh tỷ lệ rời bỏ của Top N với toàn bộ khách (kèm xác suất nhị thức P(X >= k))."""
    top = top_customers(customers, n)
    churn_all = float(customers[C.CHURNED].mean())
    k = int(top[C.CHURNED].sum())
    size = len(top)
    p_value = sum(comb(size, i) * churn_all**i * (1 - churn_all) ** (size - i) for i in range(k, size + 1))
    churn_top = float(top[C.CHURNED].mean()) if size > 0 else 0.0
    total_spend_all = float(customers[C.TOTAL_SPEND].sum())
    top_spend = float(top[C.TOTAL_SPEND].sum())
    return pd.DataFrame([{
        "top_n": size,
        "churned_in_top": k,
        "churn_rate_top_pct": round(churn_top * 100, 2),
        "churn_rate_all_pct": round(churn_all * 100, 2),
        "churn_ratio_vs_all": round(churn_top / churn_all, 2) if churn_all > 0 else np.nan,
        "top_spend_usd": round(top_spend, 2),
        "spend_share_pct": round(top_spend / total_spend_all * 100, 2) if total_spend_all > 0 else 0.0,
        "binomial_p_value": round(p_value, 4),
    }])


# --- Câu 10: churn theo hành vi, doanh thu thuần theo nhóm hàng -------
def _churn_by_segment(customers: pd.DataFrame, source_col: str, bins: list, labels: list[str]) -> pd.DataFrame:
    _require(customers, [source_col, C.CHURNED], "customers")
    segment = pd.cut(customers[source_col], bins, labels=labels)
    out = customers.groupby(segment, observed=True)[C.CHURNED].agg(
        customers="count", churned_customers="sum"
    )
    out["churn_rate_pct"] = (out["churned_customers"] / out["customers"] * 100).round(2)
    return out.rename_axis("segment").reset_index()


def churn_by_recency(customers: pd.DataFrame) -> pd.DataFrame:
    return _churn_by_segment(customers, C.DAYS_SINCE_LAST_PURCHASE, cfg.RECENCY_BINS, cfg.RECENCY_LABELS)


def churn_by_order_count(customers: pd.DataFrame) -> pd.DataFrame:
    return _churn_by_segment(customers, C.TOTAL_ORDERS, cfg.ORDER_COUNT_BINS, cfg.ORDER_COUNT_LABELS)


def category_revenue_net(
    orders: pd.DataFrame, exclude_status: tuple[str, ...] = cfg.STATUS_EXCLUDED_NET
) -> pd.DataFrame:
    """Doanh thu thuần (loại đơn hủy và hoàn) theo nhóm hàng và tỷ trọng."""
    net = orders[~orders[O.ORDER_STATUS].isin(exclude_status)]
    if net.empty:
        return pd.DataFrame(columns=[O.CATEGORY, "revenue_usd", "share_pct"])
    out = net.groupby(O.CATEGORY, as_index=False)[O.TOTAL_AMOUNT].sum()
    out = out.rename(columns={O.TOTAL_AMOUNT: "revenue_usd"}).sort_values("revenue_usd", ascending=False)
    total = out["revenue_usd"].sum()
    out["share_pct"] = (out["revenue_usd"] / total * 100) if total > 0 else 0.0
    return out.round(2).reset_index(drop=True)


# ======================================================================
# 4. TỔNG HỢP TOÀN BỘ BẢNG TRONG BỘ NHỚ CHO DASHBOARD
# ======================================================================
def build_summaries(data: dict[str, pd.DataFrame] | None = None) -> dict[str, pd.DataFrame]:
    """Tính toàn bộ bảng tổng hợp từ dữ liệu sạch trong bộ nhớ."""
    data = data or load_all()
    orders, customers, monthly = data["orders"], data["customers"], data["monthly_revenue"]
    fact = build_fact_orders(orders, customers)
    customer_fm = customer_frequency_monetary(orders)
    return {
        "fact_orders": fact,
        "kpi_overview": kpi_overview(orders, customers),
        "monthly_trend": monthly_trend(monthly),
        "monthly_seasonality": monthly_seasonality(monthly),
        "revenue_by_country": revenue_ranking(fact, C.COUNTRY),
        "revenue_by_category": revenue_ranking(fact, O.CATEGORY),
        "country_category_revenue": country_category_revenue(fact),
        "churn_by_channel": churn_by_channel(customers),
        "customer_fm": customer_fm,
        "revenue_concentration": revenue_concentration(customer_fm),
        "discount_groups": discount_group_summary(orders),
        "discount_tests": discount_tests(orders),
        "shipping_by_country": shipping_by_country(fact),
        "category_performance": category_performance(fact),
        "country_category_return": country_category_return(fact),
        "top_customers": top_customers(customers),
        "top_customers_summary": top_customers_summary(customers),
        "churn_by_recency": churn_by_recency(customers),
        "churn_by_order_count": churn_by_order_count(customers),
        "category_revenue_net": category_revenue_net(orders),
    }