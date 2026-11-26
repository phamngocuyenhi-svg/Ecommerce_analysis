"""Dashboard tương tác Ecommerce_analysis (Plotly Dash).

Chạy từ thư mục gốc dự án:
    python dashboards/plotly_app/app.py            # mở http://127.0.0.1:8050
    python dashboards/plotly_app/app.py --port 8060 --debug

Bộ lọc chéo (thanh trên cùng): năm, quốc gia, nhóm hàng, kênh thu hút, hạng thành viên.
Có thể bấm trực tiếp vào cột quốc gia / nhóm hàng / kênh (hoặc ô heatmap) để lọc nhanh; nút "Xóa bộ lọc" để đặt lại.
Số liệu được tính lại từ data/cleaned/ bằng src/data_processor.py nên không cần chạy trước bước xuất marts.
"""
from __future__ import annotations

import argparse
import logging
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from dash import Dash, Input, Output, dcc, html, no_update  # noqa: E402

from src import chart_builders as cb  # noqa: E402
from src import config as cfg  # noqa: E402
from src import data_processor as dp  # noqa: E402
from src.config import CustomerCol as C  # noqa: E402
from src.config import OrderCol as O  # noqa: E402
from src.config import PALETTE as P  # noqa: E402

log = logging.getLogger("ecommerce_dashboard")

# ======================================================================
# 1. DỮ LIỆU (đọc một lần khi khởi động — có lọc NaN an toàn)
# ======================================================================
_DATA = dp.load_all()
CUSTOMERS = _DATA["customers"]
FACT = dp.build_fact_orders(_DATA["orders"], CUSTOMERS)

YEARS = sorted(FACT[O.YEAR].dropna().unique().tolist())
COUNTRIES = sorted(CUSTOMERS[C.COUNTRY].dropna().astype(str).unique())
CATEGORIES = sorted(FACT[O.CATEGORY].dropna().astype(str).unique())
CHANNELS = sorted(CUSTOMERS[C.ACQUISITION_CHANNEL].dropna().astype(str).unique())
TIERS = sorted(CUSTOMERS[C.MEMBERSHIP_TIER].dropna().astype(str).unique())


def _isin(series: pd.Series, values) -> pd.Series:
    """Bộ lọc nhiều lựa chọn; danh sách rỗng nghĩa là không lọc."""
    return series.isin(values) if values else pd.Series(True, index=series.index)


@lru_cache(maxsize=64)
def _filtered(years: tuple, countries: tuple, categories: tuple, channels: tuple, tiers: tuple):
    """Áp bộ lọc lên bảng đơn hàng (đủ 5 bộ lọc) và bảng khách hàng (chỉ thuộc tính khách: quốc gia, kênh, hạng)."""
    lo, hi = years
    fact = FACT[
        FACT[O.YEAR].between(lo, hi)
        & _isin(FACT[C.COUNTRY], countries)
        & _isin(FACT[O.CATEGORY], categories)
        & _isin(FACT[C.ACQUISITION_CHANNEL], channels)
        & _isin(FACT[C.MEMBERSHIP_TIER], tiers)
    ]
    cust = CUSTOMERS[
        _isin(CUSTOMERS[C.COUNTRY], countries)
        & _isin(CUSTOMERS[C.ACQUISITION_CHANNEL], channels)
        & _isin(CUSTOMERS[C.MEMBERSHIP_TIER], tiers)
    ]
    return fact, cust


def get_filtered(years, countries, categories, channels, tiers):
    years = tuple(years) if years else (YEARS[0], YEARS[-1])
    return _filtered(years, tuple(countries or ()), tuple(categories or ()), tuple(channels or ()), tuple(tiers or ()))


def safe(builder, *args, **kwargs):
    """Gọi hàm dựng biểu đồ; nếu bộ lọc làm dữ liệu rỗng/không đủ thì trả biểu đồ trống thay vì làm sập dashboard."""
    try:
        return builder(*args, **kwargs)
    except Exception:  # noqa: BLE001
        log.exception("Không dựng được biểu đồ %s", getattr(builder, "__name__", builder))
        return cb.empty_figure("Không đủ dữ liệu cho bộ lọc đã chọn")


# ======================================================================
# 2. GIAO DIỆN
# ======================================================================
FONT = cfg.FONT_FAMILY
CARD = {"background": "white", "border": f"1px solid {P['grid']}", "borderRadius": "8px", "padding": "10px 14px"}
GRID = {"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(520px, 1fr))", "gap": "14px", "marginTop": "14px"}
NOTE = {"color": P["text_muted"], "fontSize": "12px", "margin": "4px 0 0 0"}


def card(title: str, graph_id: str, note: str | None = None, full: bool = False, show_title: bool = False) -> html.Div:
    """Thẻ chứa một biểu đồ. Tiêu đề và subtitle nằm trong chính biểu đồ; chỉ hiện tiêu đề ngoài khi biểu đồ không có (thẻ KPI)."""
    style = dict(CARD)
    if full:
        style["gridColumn"] = "1 / -1"
    children = []
    if show_title:
        children.append(html.H4(title, style={"margin": "0 0 4px 0", "color": P["primary"], "fontSize": "15px"}))
    children.append(dcc.Graph(id=graph_id, config={"displaylogo": False}))
    if note:
        children.append(html.P(note, style=NOTE))
    return html.Div(children, style=style)


def table_card(title: str, table_id: str, note: str | None = None) -> html.Div:
    children = [html.H4(title, style={"margin": "0 0 4px 0", "color": P["primary"], "fontSize": "15px"})]
    if note:
        children.append(html.P(note, style=NOTE))
    children.append(html.Div(id=table_id, style={"overflowX": "auto", "marginTop": "8px"}))
    return html.Div(children, style=CARD)


def html_table(df: pd.DataFrame, headers: dict[str, str], formats: dict[str, str] | None = None) -> html.Table:
    formats = formats or {}
    th = {"textAlign": "right", "padding": "6px 10px", "background": P["navy"], "color": "white", "fontSize": "12px", "whiteSpace": "nowrap"}
    td = {"textAlign": "right", "padding": "5px 10px", "borderBottom": f"1px solid {P['grid']}", "fontSize": "13px"}
    head = html.Tr([html.Th(headers[c], style={**th, "textAlign": "left" if i == 0 else "right"}) for i, c in enumerate(headers)])
    rows = []
    for _, r in df.iterrows():
        cells = []
        for i, c in enumerate(headers):
            v = r[c]
            text = "–" if pd.isna(v) else (format(v, formats[c]) if c in formats else str(v))
            cells.append(html.Td(text, style={**td, "textAlign": "left" if i == 0 else "right"}))
        rows.append(html.Tr(cells))
    return html.Table([html.Thead(head), html.Tbody(rows)], style={"borderCollapse": "collapse", "width": "100%"})


def dropdown(component_id: str, options: list, placeholder: str) -> dcc.Dropdown:
    return dcc.Dropdown(
        id=component_id, options=options, value=[], multi=True, placeholder=placeholder,
        style={"fontSize": "13px", "minWidth": "190px"}
    )


def filter_box(label_text: str, component) -> html.Div:
    return html.Div(
        [html.Label(label_text, style={"fontSize": "12px", "color": P["text_muted"], "fontWeight": 600}), component],
        style={"flex": "1 1 190px"}
    )


app = Dash(__name__, title="Ecommerce Analysis Dashboard", suppress_callback_exceptions=False)
server = app.server

filters_bar = html.Div(
    [
        filter_box("Năm", html.Div(dcc.RangeSlider(
            id="f-year", min=YEARS[0], max=YEARS[-1], step=1, value=[YEARS[0], YEARS[-1]],
            marks={y: str(y) for y in YEARS}, tooltip={"placement": "bottom"}), style={"padding": "6px 8px 0"})),
        filter_box("Quốc gia", dropdown("f-country", COUNTRIES, "Tất cả quốc gia")),
        filter_box("Nhóm hàng", dropdown("f-category", CATEGORIES, "Tất cả nhóm hàng")),
        filter_box("Kênh thu hút", dropdown("f-channel", CHANNELS, "Tất cả kênh")),
        filter_box("Hạng thành viên", dropdown("f-tier", TIERS, "Tất cả hạng")),
        html.Div(html.Button("Xóa bộ lọc", id="btn-reset", n_clicks=0, style={
            "background": P["primary"], "color": "white", "border": "none", "borderRadius": "6px",
            "padding": "8px 14px", "cursor": "pointer", "marginTop": "16px"}), style={"flex": "0 0 auto"}),
    ],
    style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "alignItems": "flex-start", **CARD,
           "position": "sticky", "top": "0", "zIndex": 20, "boxShadow": "0 2px 6px rgba(0,0,0,.08)"},
)

tab_overview = html.Div([
    card("Chỉ số tổng quan", "g-kpi", "Tất cả đơn hàng (mọi trạng thái), theo bộ lọc.", full=True, show_title=True),
    card("Doanh thu theo tháng", "g-trend", full=True),
    card("Tính thời vụ", "g-season"),
    card("Doanh thu thuần theo nhóm hàng", "g-catnet"),
], style=GRID)

tab_revenue = html.Div([
    card("Top 10 quốc gia", "g-pareto-country", "Bấm vào cột để lọc theo quốc gia."),
    card("Top 10 nhóm hàng", "g-pareto-category", "Bấm vào cột để lọc theo nhóm hàng."),
    card("Tỷ trọng doanh thu", "g-heat-rev",
         "Top 10 quốc gia × Top 10 nhóm hàng, tỷ trọng tính trong tổng doanh thu của quốc gia. Bấm vào ô để lọc cả quốc gia và nhóm hàng.", full=True),
], style=GRID)

tab_customers = html.Div([
    html.P("Các chỉ số tỷ lệ rời bỏ và Top khách hàng tính trên bảng khách hàng nên chỉ chịu tác động của bộ lọc quốc gia, kênh và hạng thành viên "
           "(không phụ thuộc năm và nhóm hàng). Frequency/Monetary tính từ đơn hàng đã lọc, loại Cancelled và Returned.",
           style={**NOTE, "gridColumn": "1 / -1"}),
    html.Div([card("Rời bỏ theo kênh", "g-churn-channel", "Bấm vào cột để lọc theo kênh."),
              html.Div(id="txt-churn-test", style={**NOTE, "padding": "0 14px 8px"})]),
    card("Rời bỏ theo số ngày chưa mua", "g-churn-recency"),
    card("Rời bỏ theo số đơn đã mua", "g-churn-orders"),
    html.Div([card("Top 10 khách chi tiêu cao nhất", "g-top-customers"),
              html.Div(id="txt-top-summary", style={**NOTE, "padding": "6px 14px"})]),
    card("Phân phối Frequency", "g-hist-freq"),
    card("Phân phối Monetary", "g-hist-mon"),
    card("Phân phối Monetary (log)", "g-hist-mon-log"),
    card("Mức độ tập trung doanh thu", "g-concentration"),
], style=GRID)

tab_operations = html.Div([
    card("Vận chuyển theo quốc gia", "g-ship", full=True),
    card("Hoàn trả và rating theo nhóm hàng", "g-catperf", "Rating chỉ gồm đơn có đánh giá."),
    card("Bubble nhóm hàng", "g-bubble"),
    card("Hoàn trả theo quốc gia và nhóm hàng", "g-heat-return", full=True),
], style=GRID)

tab_discount = html.Div([
    table_card("Thống kê theo nhóm chiết khấu", "tbl-discount-groups", "Gộp theo mức chiết khấu của đơn hàng (tất cả đơn hàng)."),
    table_card("Kiểm định thống kê", "tbl-discount-tests", "Spearman giữa Discount với Quantity/Amount; Kruskal–Wallis giữa các nhóm."),
    card("Số lượng sản phẩm theo nhóm Discount", "g-box-qty"),
    card("Giá trị giao dịch theo nhóm Discount", "g-box-amt"),
], style=GRID)

TAB_STYLE = {"padding": "8px 16px", "fontFamily": FONT}
TAB_SELECTED = {**TAB_STYLE, "borderTop": f"3px solid {P['primary']}", "fontWeight": 600, "color": P["primary"]}

app.layout = html.Div(
    [
        html.Div([
            html.H2("Ecommerce Analysis Dashboard", style={"margin": 0, "color": "white", "fontSize": "22px"}),
            html.Div(id="status-text", style={"color": "#CBD5E1", "fontSize": "13px", "marginTop": "2px"}),
        ], style={"background": P["navy"], "padding": "14px 24px"}),
        html.Div([
            filters_bar,
            dcc.Tabs(id="tabs", value="overview", style={"marginTop": "14px"}, children=[
                dcc.Tab(label="Tổng quan", value="overview", children=tab_overview, style=TAB_STYLE, selected_style=TAB_SELECTED),
                dcc.Tab(label="Doanh thu", value="revenue", children=tab_revenue, style=TAB_STYLE, selected_style=TAB_SELECTED),
                dcc.Tab(label="Khách hàng", value="customers", children=tab_customers, style=TAB_STYLE, selected_style=TAB_SELECTED),
                dcc.Tab(label="Vận hành", value="operations", children=tab_operations, style=TAB_STYLE, selected_style=TAB_SELECTED),
                dcc.Tab(label="Khuyến mãi", value="discount", children=tab_discount, style=TAB_STYLE, selected_style=TAB_SELECTED),
            ]),
        ], style={"padding": "14px 24px 30px"}),
    ],
    style={"fontFamily": FONT, "background": "#F1F5F9", "minHeight": "100vh", "color": P["text"]},
)

FILTERS = [Input("f-year", "value"), Input("f-country", "value"), Input("f-category", "value"),
           Input("f-channel", "value"), Input("f-tier", "value")]


# ======================================================================
# 3. CALLBACK TÍNH LẠI BIỂU ĐỒ THEO BỘ LỌC
# ======================================================================
@app.callback(Output("status-text", "children"), FILTERS)
def update_status(years, countries, categories, channels, tiers):
    fact, cust = get_filtered(years, countries, categories, channels, tiers)
    return f"Đang xem {len(fact):,}/{len(FACT):,} đơn hàng · {len(cust):,}/{len(CUSTOMERS):,} khách hàng"


@app.callback(Output("g-kpi", "figure"), Output("g-trend", "figure"), Output("g-season", "figure"),
              Output("g-catnet", "figure"), FILTERS)
def update_overview(years, countries, categories, channels, tiers):
    fact, cust = get_filtered(years, countries, categories, channels, tiers)
    if fact.empty:
        empty = cb.empty_figure()
        return empty, empty, empty, empty
    monthly = dp.monthly_revenue_from_fact(fact)
    return (
        safe(lambda: cb.kpi_indicators(dp.kpi_overview(fact, cust))),
        safe(lambda: cb.line_monthly_revenue(dp.monthly_trend(monthly))),
        safe(lambda: cb.bar_seasonality(dp.monthly_seasonality(monthly))),
        safe(lambda: cb.barh_category_revenue(dp.category_revenue_net(fact))),
    )


@app.callback(Output("g-pareto-country", "figure"), Output("g-pareto-category", "figure"),
              Output("g-heat-rev", "figure"), FILTERS)
def update_revenue(years, countries, categories, channels, tiers):
    fact, _ = get_filtered(years, countries, categories, channels, tiers)
    if fact.empty:
        empty = cb.empty_figure()
        return empty, empty, empty
    by_country = dp.revenue_ranking(fact, C.COUNTRY)
    by_category = dp.revenue_ranking(fact, O.CATEGORY)

    def heat():
        long_df = dp.country_category_revenue(fact)
        top_c = by_country.head(cfg.TOP_N_RANKING)[C.COUNTRY].tolist()
        top_k = by_category.head(cfg.TOP_N_RANKING)[O.CATEGORY].tolist()
        long_df = long_df[long_df[C.COUNTRY].isin(top_c) & long_df[O.CATEGORY].isin(top_k)]
        return cb.heatmap_matrix(long_df, O.CATEGORY, C.COUNTRY, "share_in_country_pct",
                                 "Tỷ trọng doanh thu của nhóm hàng trong từng quốc gia (%)",
                                 value_title="Tỷ trọng (%)", row_order=top_c, col_order=top_k)

    return (
        safe(cb.pareto_chart, by_country, C.COUNTRY, title="Top 10 quốc gia theo doanh thu"),
        safe(cb.pareto_chart, by_category, O.CATEGORY, title="Top 10 nhóm hàng theo doanh thu"),
        safe(heat),
    )


@app.callback(
    Output("g-churn-channel", "figure"), Output("g-churn-recency", "figure"), Output("g-churn-orders", "figure"),
    Output("g-top-customers", "figure"), Output("txt-top-summary", "children"), Output("txt-churn-test", "children"),
    Output("g-hist-freq", "figure"), Output("g-hist-mon", "figure"), Output("g-hist-mon-log", "figure"),
    Output("g-concentration", "figure"), FILTERS,
)
def update_customers(years, countries, categories, channels, tiers):
    fact, cust = get_filtered(years, countries, categories, channels, tiers)
    empty = cb.empty_figure()
    if cust.empty:
        return empty, empty, empty, empty, "", "", empty, empty, empty, empty
    churn_all = cust[C.CHURNED].mean() * 100
    k = cfg.CHURN_ALERT_MULTIPLIER

    summary_text = ""
    try:
        s = dp.top_customers_summary(cust).iloc[0]
        summary_text = (f"Top {int(s.top_n)}: {int(s.churned_in_top)} khách đã rời bỏ ({s.churn_rate_top_pct:.1f}%) so với "
                        f"{s.churn_rate_all_pct:.2f}% toàn bộ khách; tổng chi tiêu ${s.top_spend_usd:,.0f} "
                        f"({s.spend_share_pct:.1f}% tổng chi tiêu). Xác suất nhị thức P(X ≥ {int(s.churned_in_top)}) = {s.binomial_p_value:.1%}.")
    except Exception:  # noqa: BLE001
        log.exception("Không tính được top_customers_summary")

    test_text = ""
    try:
        res = dp.churn_channel_test(cust)
        if res:
            verdict = ("khác biệt giữa các kênh có ý nghĩa thống kê" if res["p_value"] < 0.05
                       else "chưa có bằng chứng thống kê cho thấy các kênh khác nhau")
            test_text = f"Kiểm định chi-bình phương: p = {res['p_value']:.3f} → {verdict}."
    except Exception:  # noqa: BLE001
        log.exception("Không tính được kiểm định churn theo kênh")

    fm = dp.customer_frequency_monetary(fact) if not fact.empty else pd.DataFrame(columns=["frequency", "monetary"])
    upper = None
    if len(fm) >= 4:
        q1, q3 = fm["monetary"].quantile([0.25, 0.75])
        if q3 > q1:
            upper = q3 + cfg.IQR_MULTIPLIER * (q3 - q1)

    return (
        safe(cb.bar_rate, dp.churn_by_channel(cust), C.ACQUISITION_CHANNEL, "churn_rate_pct", "total_customers",
             churn_all, None, "Tỷ lệ rời bỏ theo kênh thu hút"),
        safe(cb.bar_rate, dp.churn_by_recency(cust), "segment", "churn_rate_pct", "customers", churn_all, k,
             "Tỷ lệ rời bỏ theo số ngày kể từ lần mua cuối", "Số ngày kể từ lần mua cuối"),
        safe(cb.bar_rate, dp.churn_by_order_count(cust), "segment", "churn_rate_pct", "customers", churn_all, k,
             "Tỷ lệ rời bỏ theo số đơn hàng đã mua", "Số đơn hàng đã mua"),
        safe(cb.bar_top_customers, dp.top_customers(cust)),
        summary_text,
        test_text,
        safe(cb.histogram_distribution, fm, "frequency", "Phân phối Frequency", "Số đơn hàng (Frequency)", discrete=True),
        safe(cb.histogram_distribution, fm, "monetary", "Phân phối Monetary", "Tổng chi tiêu (USD)", show_outlier_threshold=upper),
        safe(cb.histogram_distribution, fm, "monetary", "Phân phối Monetary (log)", "Tổng chi tiêu (USD, log)", log_x=True),
        safe(lambda: cb.bar_revenue_concentration(dp.revenue_concentration(fm))) if not fm.empty else empty,
    )


@app.callback(Output("g-ship", "figure"), Output("g-catperf", "figure"), Output("g-bubble", "figure"),
              Output("g-heat-return", "figure"), FILTERS)
def update_operations(years, countries, categories, channels, tiers):
    fact, _ = get_filtered(years, countries, categories, channels, tiers)
    if fact.empty:
        empty = cb.empty_figure()
        return empty, empty, empty, empty
    perf = dp.category_performance(fact)
    ret = dp.country_category_return(fact)
    return (
        safe(lambda: cb.dual_axis_shipping(dp.shipping_by_country(fact))),
        safe(cb.bar_category_performance, perf),
        safe(cb.bubble_category, perf),
        safe(cb.heatmap_matrix, ret, O.CATEGORY, C.COUNTRY, "return_rate_pct", "Tỷ lệ hoàn trả theo quốc gia và nhóm hàng (%)",
             colorscale=cfg.CORAL_SCALE, value_title="Hoàn trả (%)"),
    )


@app.callback(Output("tbl-discount-groups", "children"), Output("tbl-discount-tests", "children"),
              Output("g-box-qty", "figure"), Output("g-box-amt", "figure"), FILTERS)
def update_discount(years, countries, categories, channels, tiers):
    fact, _ = get_filtered(years, countries, categories, channels, tiers)
    empty = cb.empty_figure()
    if fact.empty:
        return "Không có dữ liệu cho bộ lọc đã chọn.", "", empty, empty
    try:
        groups = dp.discount_group_summary(fact)
        groups_table = html_table(
            groups,
            {"discount_group": "Nhóm", "orders": "Số đơn", "avg_quantity": "SL TB", "median_quantity": "SL trung vị",
             "avg_amount_usd": "Giá trị TB ($)", "median_amount_usd": "Giá trị trung vị ($)",
             "total_amount_usd": "Tổng giá trị ($)", "order_share_pct": "Tỷ trọng đơn (%)"},
            {"orders": ",.0f", "avg_quantity": ".2f", "median_quantity": ".1f", "avg_amount_usd": ",.2f",
             "median_amount_usd": ",.2f", "total_amount_usd": ",.0f", "order_share_pct": ".2f"},
        )
        tests = dp.discount_tests(fact)
        tests_table = html_table(
            tests, {"test": "Kiểm định", "variable": "Biến", "statistic": "Thống kê", "p_value": "p-value"},
            {"statistic": ".4f", "p_value": ".4g"},
        )
    except Exception:  # noqa: BLE001
        log.exception("Không tính được thống kê Discount")
        groups_table = tests_table = "Không đủ dữ liệu cho bộ lọc đã chọn."
    disc = dp.add_discount_group(dp.clean_discount_orders(fact))
    return (
        groups_table, tests_table,
        safe(cb.box_by_discount_group, disc, O.QUANTITY, "Số lượng sản phẩm theo nhóm Discount"),
        safe(cb.box_by_discount_group, disc, O.TOTAL_AMOUNT, "Giá trị giao dịch theo nhóm Discount"),
    )


# ======================================================================
# 4. LỌC CHÉO BẰNG CÁCH BẤM VÀO BIỂU ĐỒ
# ======================================================================
def _clicked(click_data, key: str):
    try:
        return click_data["points"][0][key]
    except (TypeError, KeyError, IndexError):
        return None


@app.callback(Output("f-country", "value", allow_duplicate=True), Input("g-pareto-country", "clickData"), prevent_initial_call=True)
def click_country(click):
    country = _clicked(click, "x")
    return [country] if country in COUNTRIES else no_update


@app.callback(Output("f-category", "value", allow_duplicate=True), Input("g-pareto-category", "clickData"), prevent_initial_call=True)
def click_category(click):
    category = _clicked(click, "x")
    return [category] if category in CATEGORIES else no_update


@app.callback(Output("f-channel", "value", allow_duplicate=True), Input("g-churn-channel", "clickData"), prevent_initial_call=True)
def click_channel(click):
    channel = _clicked(click, "x")
    return [channel] if channel in CHANNELS else no_update


@app.callback(Output("f-country", "value", allow_duplicate=True), Output("f-category", "value", allow_duplicate=True),
              Input("g-heat-rev", "clickData"), prevent_initial_call=True)
def click_heatmap(click):
    country, category = _clicked(click, "y"), _clicked(click, "x")
    if country in COUNTRIES and category in CATEGORIES:
        return [country], [category]
    return no_update, no_update


@app.callback(
    Output("f-year", "value", allow_duplicate=True), Output("f-country", "value", allow_duplicate=True),
    Output("f-category", "value", allow_duplicate=True), Output("f-channel", "value", allow_duplicate=True),
    Output("f-tier", "value", allow_duplicate=True), Input("btn-reset", "n_clicks"), prevent_initial_call=True,
)
def reset_filters(_):
    return [YEARS[0], YEARS[-1]], [], [], [], []


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy dashboard Plotly Dash của dự án Ecommerce_analysis.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    print(f"Dashboard: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()