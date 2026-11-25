"""Xuất toàn bộ biểu đồ tương tác (dữ liệu đầy đủ, chưa lọc) thành file HTML độc lập vào exports/interactive_html/.

Chạy từ thư mục gốc dự án:
    python dashboards/plotly_app/export_html.py
Mỗi file mở được bằng trình duyệt (cần internet để tải thư viện plotly.js từ CDN), có hover và zoom.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import chart_builders as cb  # noqa: E402
from src import config as cfg  # noqa: E402
from src import data_processor as dp  # noqa: E402
from src.config import CustomerCol as C  # noqa: E402
from src.config import OrderCol as O  # noqa: E402


def build_figures() -> dict:
    data = dp.load_all()
    customers, orders = data["customers"], data["orders"]
    fact = dp.build_fact_orders(orders, customers)
    marts = dp.build_marts(data)
    fm = marts["customer_fm"]
    q1, q3 = fm["monetary"].quantile([0.25, 0.75])
    upper = q3 + cfg.IQR_MULTIPLIER * (q3 - q1)
    churn_all = customers[C.CHURNED].mean() * 100
    k = cfg.CHURN_ALERT_MULTIPLIER
    disc = dp.add_discount_group(dp.clean_discount_orders(orders))

    top_c = marts["revenue_by_country"].head(cfg.TOP_N_RANKING)[C.COUNTRY].tolist()
    top_k = marts["revenue_by_category"].head(cfg.TOP_N_RANKING)[O.CATEGORY].tolist()
    heat = marts["country_category_revenue"]
    heat = heat[heat[C.COUNTRY].isin(top_c) & heat[O.CATEGORY].isin(top_k)]

    return {
        "cau01_kpi": cb.kpi_indicators(marts["kpi_overview"]),
        "cau02_xu_huong": cb.line_monthly_revenue(marts["monthly_trend"]),
        "cau02_thoi_vu": cb.bar_seasonality(marts["monthly_seasonality"]),
        "cau03_top_quoc_gia": cb.pareto_chart(marts["revenue_by_country"], C.COUNTRY, title="Top 10 quốc gia theo doanh thu"),
        "cau03_top_nhom_hang": cb.pareto_chart(marts["revenue_by_category"], O.CATEGORY, title="Top 10 nhóm hàng theo doanh thu"),
        "cau03_heatmap": cb.heatmap_matrix(heat, O.CATEGORY, C.COUNTRY, "share_in_country_pct",
                                           "Tỷ trọng doanh thu của nhóm hàng trong từng quốc gia (%)",
                                           value_title="Tỷ trọng (%)", row_order=top_c, col_order=top_k),
        "cau04_churn_kenh": cb.bar_rate(marts["churn_by_channel"], C.ACQUISITION_CHANNEL, "churn_rate_pct", "total_customers",
                                        churn_all, None, "Tỷ lệ rời bỏ theo kênh thu hút"),
        "cau05_hist_frequency": cb.histogram_distribution(fm, "frequency", "Phân phối Frequency", "Số đơn hàng (Frequency)", discrete=True),
        "cau05_hist_monetary": cb.histogram_distribution(fm, "monetary", "Phân phối Monetary", "Tổng chi tiêu (USD)", show_outlier_threshold=upper),
        "cau05_hist_monetary_log": cb.histogram_distribution(fm, "monetary", "Phân phối Monetary (log)", "Tổng chi tiêu (USD, log)", log_x=True),
        "cau05_tap_trung": cb.bar_revenue_concentration(marts["revenue_concentration"]),
        "cau06_boxplot_quantity": cb.box_by_discount_group(disc, O.QUANTITY, "Số lượng sản phẩm theo nhóm Discount"),
        "cau06_boxplot_amount": cb.box_by_discount_group(disc, O.TOTAL_AMOUNT, "Giá trị giao dịch theo nhóm Discount"),
        "cau07_van_chuyen": cb.dual_axis_shipping(marts["shipping_by_country"]),
        "cau08_hoan_tra_rating": cb.bar_category_performance(marts["category_performance"]),
        "cau08_bubble": cb.bubble_category(marts["category_performance"]),
        "cau08_heatmap_hoan_tra": cb.heatmap_matrix(marts["country_category_return"], O.CATEGORY, C.COUNTRY, "return_rate_pct",
                                                    "Tỷ lệ hoàn trả theo quốc gia và nhóm hàng (%)", colorscale=cfg.CORAL_SCALE, value_title="Hoàn trả (%)"),
        "cau09_top_khach_hang": cb.bar_top_customers(marts["top_customers"]),
        "cau10_churn_recency": cb.bar_rate(marts["churn_by_recency"], "segment", "churn_rate_pct", "customers", churn_all, k,
                                           "Tỷ lệ rời bỏ theo số ngày kể từ lần mua cuối", "Số ngày kể từ lần mua cuối"),
        "cau10_churn_so_don": cb.bar_rate(marts["churn_by_order_count"], "segment", "churn_rate_pct", "customers", churn_all, k,
                                          "Tỷ lệ rời bỏ theo số đơn hàng đã mua", "Số đơn hàng đã mua"),
        "cau10_doanh_thu_nhom_hang": cb.barh_category_revenue(marts["category_revenue_net"]),
    }


def main() -> None:
    cfg.EXPORTS_HTML.mkdir(parents=True, exist_ok=True)
    figures = build_figures()
    for name, fig in figures.items():
        cb.save_html(fig, name)
    print(f"Đã xuất {len(figures)} file HTML vào {cfg.EXPORTS_HTML}")


if __name__ == "__main__":
    main()
