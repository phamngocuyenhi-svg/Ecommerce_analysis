"""Xuất toàn bộ Dashboard (5 Tab, đầy đủ biểu đồ và bảng kiểm định từ Câu 1–10) thành 1 file HTML duy nhất: report/dashboard.html.

Chạy từ thư mục gốc dự án:
    python dashboards/plotly_app/export_html.py
File report/dashboard.html mở trực tiếp bằng trình duyệt (cần kết nối Internet để tải thư viện plotly.js từ CDN),
hỗ trợ chuyển đổi giữa 5 Tab, hover xem chi tiết chỉ số, zoom/pan và kéo thanh trượt thời gian.
"""
from __future__ import annotations

import html as html_lib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import chart_builders as cb  # noqa: E402
from src import config as cfg  # noqa: E402
from src import data_processor as dp  # noqa: E402
from src.config import CustomerCol as C  # noqa: E402
from src.config import OrderCol as O  # noqa: E402
from src.config import PALETTE as P  # noqa: E402


def _render_table(df: pd.DataFrame, headers: dict[str, str], formats: dict[str, str] | None = None) -> str:
    formats = formats or {}
    ths = []
    for i, col in enumerate(headers):
        align = "left" if i == 0 else "right"
        ths.append(f'<th style="text-align:{align}">{html_lib.escape(headers[col])}</th>')
    rows_html = []
    for _, row in df.iterrows():
        tds = []
        for i, col in enumerate(headers):
            align = "left" if i == 0 else "right"
            val = row[col]
            text = "–" if pd.isna(val) else (format(val, formats[col]) if col in formats else str(val))
            tds.append(f'<td style="text-align:{align}">{html_lib.escape(text)}</td>')
        rows_html.append("<tr>" + "".join(tds) + "</tr>")
    return (
        '<div class="table-wrap"><table class="data-table">'
        f"<thead><tr>{''.join(ths)}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
    )


def _fig_card(
    fig,
    *,
    include_js: bool = False,
    title: str | None = None,
    note: str | None = None,
    extra_footer: str | None = None,
    full: bool = False,
) -> str:
    cls = "card card-full" if full else "card"
    parts = [f'<div class="{cls}">']
    if title:
        parts.append(f'<h4 class="card-title">{html_lib.escape(title)}</h4>')
    fig_html = fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if include_js else False,
        config={"displaylogo": False, "responsive": True},
    )
    parts.append(fig_html)
    if note:
        parts.append(f'<p class="card-note">{html_lib.escape(note)}</p>')
    if extra_footer:
        parts.append(f'<p class="card-note card-stat">{html_lib.escape(extra_footer)}</p>')
    parts.append("</div>")
    return "\n".join(parts)


def _table_card(title: str, table_html: str, note: str | None = None) -> str:
    parts = ['<div class="card">', f'<h4 class="card-title">{html_lib.escape(title)}</h4>']
    if note:
        parts.append(f'<p class="card-note">{html_lib.escape(note)}</p>')
    parts.append(table_html)
    parts.append("</div>")
    return "\n".join(parts)


def build_dashboard_html() -> str:
    data = dp.load_all()
    customers, orders = data["customers"], data["orders"]
    summaries = dp.build_summaries(data)

    fm = summaries["customer_fm"]
    q1, q3 = fm["monetary"].quantile([0.25, 0.75])
    upper = q3 + cfg.IQR_MULTIPLIER * (q3 - q1)
    churn_all = float(customers[C.CHURNED].mean() * 100)
    k = cfg.CHURN_ALERT_MULTIPLIER
    disc = dp.add_discount_group(dp.clean_discount_orders(orders))

    top_c = summaries["revenue_by_country"].head(cfg.TOP_N_RANKING)[C.COUNTRY].tolist()
    top_k = summaries["revenue_by_category"].head(cfg.TOP_N_RANKING)[O.CATEGORY].tolist()
    heat = summaries["country_category_revenue"]
    heat = heat[heat[C.COUNTRY].isin(top_c) & heat[O.CATEGORY].isin(top_k)]

    # Ghi chú kiểm định thống kê Câu 4 & Câu 9 (giống app.py)
    res = dp.churn_channel_test(customers)
    test_text = ""
    if res:
        verdict = (
            "khác biệt giữa các kênh có ý nghĩa thống kê"
            if res["p_value"] < 0.05
            else "chưa có bằng chứng thống kê cho thấy các kênh khác nhau"
        )
        test_text = f"Kiểm định chi-bình phương: p = {res['p_value']:.3f} → {verdict}."

    s = summaries["top_customers_summary"].iloc[0]
    top_summary_text = (
        f"Top {int(s.top_n)}: {int(s.churned_in_top)} khách đã rời bỏ ({s.churn_rate_top_pct:.1f}%) so với "
        f"{s.churn_rate_all_pct:.2f}% toàn bộ khách; tổng chi tiêu ${s.top_spend_usd:,.0f} "
        f"({s.spend_share_pct:.1f}% tổng chi tiêu). Xác suất nhị thức P(X ≥ {int(s.churned_in_top)}) = {s.binomial_p_value:.1%}."
    )

    # Bảng thống kê Câu 6 (giống app.py)
    groups_table = _render_table(
        summaries["discount_groups"],
        {
            "discount_group": "Nhóm",
            "orders": "Số đơn",
            "avg_quantity": "SL TB",
            "median_quantity": "SL trung vị",
            "avg_amount_usd": "Giá trị TB ($)",
            "median_amount_usd": "Giá trị trung vị ($)",
            "total_amount_usd": "Tổng giá trị ($)",
            "order_share_pct": "Tỷ trọng đơn (%)",
        },
        {
            "orders": ",.0f",
            "avg_quantity": ".2f",
            "median_quantity": ".1f",
            "avg_amount_usd": ",.2f",
            "median_amount_usd": ",.2f",
            "total_amount_usd": ",.0f",
            "order_share_pct": ".2f",
        },
    )
    tests_table = _render_table(
        summaries["discount_tests"],
        {"test": "Kiểm định", "variable": "Biến", "statistic": "Thống kê", "p_value": "p-value"},
        {"statistic": ".4f", "p_value": ".4g"},
    )

    # 5 Tab nội dung
    tab_overview = "\n".join([
        _fig_card(
            cb.kpi_indicators(summaries["kpi_overview"]),
            include_js=True,
            title="Chỉ số tổng quan",
            note="Tất cả đơn hàng (mọi trạng thái).",
            full=True,
        ),
        _fig_card(cb.line_monthly_revenue(summaries["monthly_trend"]), full=True),
        _fig_card(cb.bar_seasonality(summaries["monthly_seasonality"])),
        _fig_card(cb.barh_category_revenue(summaries["category_revenue_net"])),
    ])

    tab_revenue = "\n".join([
        _fig_card(cb.pareto_chart(summaries["revenue_by_country"], C.COUNTRY, title="Top 10 quốc gia theo doanh thu")),
        _fig_card(cb.pareto_chart(summaries["revenue_by_category"], O.CATEGORY, title="Top 10 nhóm hàng theo doanh thu")),
        _fig_card(
            cb.heatmap_matrix(
                heat,
                O.CATEGORY,
                C.COUNTRY,
                "share_in_country_pct",
                "Tỷ trọng doanh thu của nhóm hàng trong từng quốc gia (%)",
                value_title="Tỷ trọng (%)",
                row_order=top_c,
                col_order=top_k,
            ),
            note="Top 10 quốc gia × Top 10 nhóm hàng, tỷ trọng tính trong tổng doanh thu của từng quốc gia.",
            full=True,
        ),
    ])

    tab_customers = "\n".join([
        '<p class="tab-banner-note">Các chỉ số tỷ lệ rời bỏ và Top khách hàng tính trên bảng khách hàng. '
        "Frequency/Monetary tính từ đơn hàng hợp lệ (loại Cancelled và Returned).</p>",
        _fig_card(
            cb.bar_rate(
                summaries["churn_by_channel"],
                C.ACQUISITION_CHANNEL,
                "churn_rate_pct",
                "total_customers",
                churn_all,
                None,
                "Tỷ lệ rời bỏ theo kênh thu hút",
            ),
            extra_footer=test_text,
        ),
        _fig_card(
            cb.bar_rate(
                summaries["churn_by_recency"],
                "segment",
                "churn_rate_pct",
                "customers",
                churn_all,
                k,
                "Tỷ lệ rời bỏ theo số ngày kể từ lần mua cuối",
                "Số ngày kể từ lần mua cuối",
            )
        ),
        _fig_card(
            cb.bar_rate(
                summaries["churn_by_order_count"],
                "segment",
                "churn_rate_pct",
                "customers",
                churn_all,
                k,
                "Tỷ lệ rời bỏ theo số đơn hàng đã mua",
                "Số đơn hàng đã mua",
            )
        ),
        _fig_card(cb.bar_top_customers(summaries["top_customers"]), extra_footer=top_summary_text),
        _fig_card(
            cb.histogram_distribution(
                fm, "frequency", "Phân phối Frequency", "Số đơn hàng (Frequency)", discrete=True
            )
        ),
        _fig_card(
            cb.histogram_distribution(
                fm, "monetary", "Phân phối Monetary", "Tổng chi tiêu (USD)", show_outlier_threshold=upper
            )
        ),
        _fig_card(
            cb.histogram_distribution(
                fm, "monetary", "Phân phối Monetary (log)", "Tổng chi tiêu (USD, log)", log_x=True
            )
        ),
        _fig_card(cb.bar_revenue_concentration(summaries["revenue_concentration"])),
    ])

    tab_operations = "\n".join([
        _fig_card(cb.dual_axis_shipping(summaries["shipping_by_country"]), full=True),
        _fig_card(
            cb.bar_category_performance(summaries["category_performance"]),
            note="Rating chỉ gồm đơn có đánh giá.",
        ),
        _fig_card(cb.bubble_category(summaries["category_performance"])),
        _fig_card(
            cb.heatmap_matrix(
                summaries["country_category_return"],
                O.CATEGORY,
                C.COUNTRY,
                "return_rate_pct",
                "Tỷ lệ hoàn trả theo quốc gia và nhóm hàng (%)",
                colorscale=cfg.CORAL_SCALE,
                value_title="Hoàn trả (%)",
            ),
            full=True,
        ),
    ])

    tab_discount = "\n".join([
        _table_card(
            "Thống kê theo nhóm chiết khấu",
            groups_table,
            "Gộp theo mức chiết khấu của đơn hàng (tất cả đơn hàng).",
        ),
        _table_card(
            "Kiểm định thống kê",
            tests_table,
            "Spearman giữa Discount với Quantity/Amount; Kruskal–Wallis giữa các nhóm.",
        ),
        _fig_card(cb.box_by_discount_group(disc, O.QUANTITY, "Số lượng sản phẩm theo nhóm Discount")),
        _fig_card(cb.box_by_discount_group(disc, O.TOTAL_AMOUNT, "Giá trị giao dịch theo nhóm Discount")),
    ])

    status_line = (
        f"Tổng hợp dữ liệu toàn bộ: {len(orders):,} đơn hàng · {len(customers):,} khách hàng · "
        f"{customers[C.COUNTRY].nunique()} quốc gia · {orders[O.CATEGORY].nunique()} nhóm hàng (Câu 1–10)"
    )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Ecommerce Analysis Dashboard</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: {cfg.FONT_FAMILY};
      background: #F1F5F9;
      color: {P['text']};
      min-height: 100vh;
    }}
    .header {{
      background: {P['navy']};
      padding: 16px 24px;
      color: white;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
      font-weight: 700;
    }}
    .header .subtitle {{
      color: #CBD5E1;
      font-size: 13px;
      margin-top: 4px;
    }}
    .container {{
      padding: 16px 24px 36px;
      max-width: 1680px;
      margin: 0 auto;
    }}
    .tabs-bar {{
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
      border-bottom: 1px solid {P['grid']};
      background: white;
      border-radius: 8px 8px 0 0;
      padding: 0 8px;
      position: sticky;
      top: 0;
      z-index: 20;
      box-shadow: 0 2px 6px rgba(0,0,0,.05);
    }}
    .tab-btn {{
      appearance: none;
      background: transparent;
      border: none;
      border-top: 3px solid transparent;
      padding: 12px 20px;
      font-family: inherit;
      font-size: 14px;
      color: {P['text_muted']};
      cursor: pointer;
      transition: color 0.15s, border-color 0.15s;
    }}
    .tab-btn:hover {{
      color: {P['navy']};
    }}
    .tab-btn.active {{
      border-top-color: {P['primary']};
      color: {P['primary']};
      font-weight: 600;
    }}
    .tab-panel {{
      display: none;
      grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .tab-panel.active {{
      display: grid;
    }}
    .card {{
      background: white;
      border: 1px solid {P['grid']};
      border-radius: 8px;
      padding: 10px 14px;
      overflow: hidden;
    }}
    .card-full {{
      grid-column: 1 / -1;
    }}
    .card-title {{
      margin: 0 0 4px 0;
      color: {P['primary']};
      font-size: 15px;
    }}
    .card-note {{
      color: {P['text_muted']};
      font-size: 12px;
      margin: 4px 0 0 0;
    }}
    .card-stat {{
      margin-top: 6px;
      font-weight: 500;
    }}
    .tab-banner-note {{
      grid-column: 1 / -1;
      color: {P['text_muted']};
      font-size: 12px;
      margin: 2px 0;
    }}
    .table-wrap {{
      overflow-x: auto;
      margin-top: 8px;
    }}
    .data-table {{
      border-collapse: collapse;
      width: 100%;
    }}
    .data-table th {{
      padding: 7px 10px;
      background: {P['navy']};
      color: white;
      font-size: 12px;
      white-space: nowrap;
    }}
    .data-table td {{
      padding: 6px 10px;
      border-bottom: 1px solid {P['grid']};
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <header class="header">
    <h1>Ecommerce Analysis Dashboard</h1>
    <div class="subtitle">{html_lib.escape(status_line)}</div>
  </header>
  <main class="container">
    <nav class="tabs-bar" role="tablist">
      <button class="tab-btn active" data-tab="overview" onclick="switchTab('overview', this)">Tổng quan</button>
      <button class="tab-btn" data-tab="revenue" onclick="switchTab('revenue', this)">Doanh thu</button>
      <button class="tab-btn" data-tab="customers" onclick="switchTab('customers', this)">Khách hàng</button>
      <button class="tab-btn" data-tab="operations" onclick="switchTab('operations', this)">Vận hành</button>
      <button class="tab-btn" data-tab="discount" onclick="switchTab('discount', this)">Khuyến mãi</button>
    </nav>
    <section id="tab-overview" class="tab-panel active">{tab_overview}</section>
    <section id="tab-revenue" class="tab-panel">{tab_revenue}</section>
    <section id="tab-customers" class="tab-panel">{tab_customers}</section>
    <section id="tab-operations" class="tab-panel">{tab_operations}</section>
    <section id="tab-discount" class="tab-panel">{tab_discount}</section>
  </main>
  <script>
    function switchTab(tabId, btn) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('tab-' + tabId);
      panel.classList.add('active');
      if (window.Plotly) {{
        panel.querySelectorAll('.js-plotly-plot').forEach(el => Plotly.Plots.resize(el));
      }}
    }}
  </script>
</body>
</html>
"""


def main() -> Path:
    cfg.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = cfg.DASHBOARD_HTML_FILE
    out_path.write_text(build_dashboard_html(), encoding="utf-8")
    print(f"Đã xuất Dashboard tổng hợp (5 Tab) vào: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
