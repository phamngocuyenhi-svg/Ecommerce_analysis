"""Hàm vẽ biểu đồ tương tác Plotly dùng lại cho dashboard (Plotly Dash/HTML) và export.

Mọi hàm nhận DataFrame có schema giống các bảng trong data/marts/ (xem data_processor.py)
và trả về ``plotly.graph_objects.Figure`` đã áp dụng Design System trong config.py:
nền trong suốt, bảng màu navy/teal/coral, tiêu đề kèm subtitle, lưới chấm mảnh,
số rút gọn K/M và hover card đầy đủ chỉ số. Zoom/pan do Plotly hỗ trợ sẵn.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config as cfg
from .config import PALETTE as P

R = cfg.BAR_CORNER_RADIUS


# ======================================================================
# 1. ĐỊNH DẠNG SỐ VÀ THEME CHUNG
# ======================================================================
def fmt_compact(value: float, prefix: str = "", suffix: str = "") -> str:
    """Rút gọn số: 1.234.567 -> '1.23M', 45.600 -> '45.6K', 820 -> '820'."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "–"
    sign = "-" if value < 0 else ""
    v = abs(float(value))
    if v >= 1e9:
        text = f"{v / 1e9:.2f}B"
    elif v >= 1e6:
        text = f"{v / 1e6:.2f}M"
    elif v >= 1e3:
        text = f"{v / 1e3:.1f}K"
    else:
        text = f"{v:,.0f}"
    text = text.replace(".00M", "M").replace(".00B", "B").replace(".0K", "K")
    return f"{sign}{prefix}{text}{suffix}"


def _nice_step(vmax: float, n_ticks: int = 5) -> float:
    raw = vmax / n_ticks if vmax > 0 else 1
    mag = 10 ** np.floor(np.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        if raw <= mult * mag:
            return mult * mag
    return 10 * mag


def compact_ticks(fig: go.Figure, vmax: float, prefix: str = "", axis: str = "y", secondary_y: bool | None = None) -> None:
    """Đặt nhãn trục dạng K/M ($0, $20K, $40K ...) dựa trên giá trị lớn nhất của dữ liệu."""
    if not vmax or np.isnan(vmax) or vmax <= 0:
        return
    step = _nice_step(vmax)
    vals = np.arange(0, vmax + step, step)
    kwargs = dict(tickvals=vals.tolist(), ticktext=[fmt_compact(v, prefix) for v in vals])
    if axis == "y":
        fig.update_yaxes(**kwargs, **({"secondary_y": secondary_y} if secondary_y is not None else {}))
    else:
        fig.update_xaxes(**kwargs)


def apply_theme(fig: go.Figure, title: str | None = None, height: int | None = None, subtitle: str | None = None) -> go.Figure:
    """Áp dụng nền trong suốt, font, tiêu đề + subtitle, lưới chấm, hover card và legend ngang phía trên."""
    title_text = None
    if title:
        title_text = f"<b>{title}</b>"
        if subtitle:
            title_text += (f"<br><span style='font-size:{cfg.SUBTITLE_FONT_SIZE}px;font-weight:400;"
                           f"color:{P['text_muted']}'>{subtitle}</span>")
    fig.update_layout(
        template="plotly_white",
        font=dict(family=cfg.FONT_FAMILY, size=cfg.FONT_SIZE, color=P["text"]),
        title=dict(text=title_text, x=0, xanchor="left", xref="paper", y=0.97, yanchor="top",
                   font=dict(size=cfg.TITLE_FONT_SIZE, color=P["navy"])) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height or cfg.DEFAULT_HEIGHT,
        margin=dict(l=64, r=32, t=(104 if subtitle else 84) if title else 40, b=64),
        colorway=cfg.CATEGORICAL_COLORS,
        hoverlabel=dict(bgcolor="white", bordercolor=P["axis"], align="left",
                        font=dict(family=cfg.FONT_FAMILY, size=13, color=P["navy"])),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=12, color=P["text_muted"]), bgcolor="rgba(0,0,0,0)"),
    )
    axis_common = dict(showline=True, linecolor=P["axis"], linewidth=1, ticks="outside", tickcolor=P["axis"],
                       tickfont=dict(size=12, color=P["text_muted"]), title_font=dict(size=12, color=P["text_muted"]),
                       zeroline=False)
    fig.update_xaxes(showgrid=False, **axis_common)
    fig.update_yaxes(showgrid=True, gridcolor=P["grid"], gridwidth=1, griddash="dot", **axis_common)
    return fig


def empty_figure(message: str = "Không có dữ liệu cho bộ lọc đã chọn") -> go.Figure:
    """Biểu đồ trống có thông báo (dùng khi bộ lọc trả về 0 dòng)."""
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=16, color=P["text_muted"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_theme(fig)


def save_html(fig: go.Figure, filename: str, folder: Path | None = None) -> Path:
    """Xuất biểu đồ thành HTML tương tác (mặc định vào exports/interactive_html/)."""
    folder = folder or cfg.EXPORTS_HTML
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (filename if filename.endswith(".html") else f"{filename}.html")
    fig.write_html(path, include_plotlyjs="cdn", config={"displaylogo": False})
    return path


def _hover(*lines: str) -> str:
    """Ghép các dòng hover thành một card gọn, bỏ tag trace thừa."""
    return "<br>".join(lines) + "<extra></extra>"


# ======================================================================
# 2. CÂU 1 - KPI TỔNG QUAN
# ======================================================================
def kpi_indicators(kpi: pd.DataFrame, subtitle: str | None = "Tất cả đơn hàng, mọi trạng thái") -> go.Figure:
    """Hàng thẻ KPI từ mart_kpi_overview (1 dòng)."""
    row = kpi.iloc[0]
    revenue = float(row["total_revenue_usd"])
    rev_scale, rev_suffix = (1e6, "M") if revenue >= 1e6 else ((1e3, "K") if revenue >= 1e3 else (1, ""))
    items = [
        ("Tổng số đơn hàng", float(row["total_orders"]), ",d", "", ""),
        ("Khách hàng có đơn", float(row["customers_with_orders"]), ",d", "", ""),
        ("Số quốc gia", float(row["countries"]), "d", "", ""),
        ("Số nhóm hàng", float(row["categories"]), "d", "", ""),
        ("Tổng doanh thu", revenue / rev_scale, ".2f", "$", rev_suffix),
    ]
    fig = make_subplots(rows=1, cols=len(items), specs=[[{"type": "indicator"}] * len(items)])
    for i, (title, value, fmt, prefix, suffix) in enumerate(items, start=1):
        fig.add_trace(
            go.Indicator(
                mode="number", value=value,
                title=dict(text=title, font=dict(size=13, color=P["text_muted"])),
                number=dict(valueformat=fmt, prefix=prefix, suffix=suffix,
                            font=dict(color=P["primary"] if i == len(items) else P["navy"], size=38)),
            ),
            row=1, col=i,
        )
    return apply_theme(fig, height=170)


# ======================================================================
# 3. CÂU 2 - XU HƯỚNG VÀ THỜI VỤ
# ======================================================================
def line_monthly_revenue(trend: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Doanh thu theo tháng kèm đường trung bình trượt (từ mart_monthly_trend)."""
    if trend.empty:
        return empty_figure()
    mom = trend["revenue_usd"].pct_change() * 100
    mom_text = ["–" if pd.isna(v) else f"{v:+.1f}%" for v in mom]
    ma_text = ["–" if pd.isna(v) else f"${v:,.0f}" for v in trend["revenue_ma"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["period"], y=trend["revenue_usd"], mode="lines+markers", name="Doanh thu tháng",
        line=dict(color=P["primary"], width=2.5), marker=dict(size=6, color="white", line=dict(color=P["primary"], width=2)),
        fill="tozeroy", fillcolor="rgba(13,148,136,0.08)",
        customdata=np.stack([ma_text, mom_text], axis=-1),
        hovertemplate=_hover("<b>%{x|%B %Y}</b>", "Doanh thu: <b>$%{y:,.0f}</b>",
                             f"TB trượt {cfg.MOVING_AVERAGE_WINDOW} tháng: %{{customdata[0]}}", "So với tháng trước: %{customdata[1]}"),
    ))
    fig.add_trace(go.Scatter(
        x=trend["period"], y=trend["revenue_ma"], mode="lines", name=f"Trung bình trượt {cfg.MOVING_AVERAGE_WINDOW} tháng",
        line=dict(color=P["navy"], width=3, dash="dash"), hoverinfo="skip",
    ))
    fig.update_yaxes(title_text="Doanh thu (USD)", rangemode="tozero")
    compact_ticks(fig, float(trend["revenue_usd"].max()), "$")
    fig.update_xaxes(title_text=None, rangeslider=dict(visible=True, thickness=0.06, bgcolor="rgba(226,232,240,0.4)"))
    return apply_theme(fig, "Doanh thu theo tháng và xu hướng",
                       subtitle=subtitle or "Đơn Delivered · USD · kéo thanh trượt để chọn khoảng thời gian")


def bar_seasonality(season: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Doanh thu trung bình theo tháng trong năm; tô đậm tháng cao nhất (từ mart_monthly_seasonality)."""
    if season.empty:
        return empty_figure()
    peak = season["avg_revenue_usd"].idxmax()
    colors = [P["primary"] if i == peak else P["primary_light"] for i in season.index]
    fig = go.Figure(go.Bar(
        x=season["month"], y=season["avg_revenue_usd"], marker=dict(color=colors, cornerradius=R),
        text=[fmt_compact(v, "$") for v in season["avg_revenue_usd"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=P["text_muted"]),
        hovertemplate=_hover("<b>Tháng %{x}</b>", "Doanh thu trung bình: <b>$%{y:,.0f}</b>"),
    ))
    fig.update_xaxes(title_text="Tháng trong năm", tickvals=list(range(1, 13)), ticktext=[f"T{m}" for m in range(1, 13)])
    fig.update_yaxes(title_text="Doanh thu trung bình (USD)", rangemode="tozero")
    compact_ticks(fig, float(season["avg_revenue_usd"].max()) * 1.1, "$")
    return apply_theme(fig, "Tính thời vụ: doanh thu trung bình theo tháng",
                       subtitle=subtitle or f"Đơn Delivered · năm {cfg.SEASONALITY_YEARS[0]}–{cfg.SEASONALITY_YEARS[1]} · tháng cao nhất tô đậm")


# ======================================================================
# 4. CÂU 3 - XẾP HẠNG DOANH THU (PARETO) VÀ HEATMAP
# ======================================================================
def pareto_chart(ranking: pd.DataFrame, label_col: str, top_n: int = cfg.TOP_N_RANKING,
                 title: str | None = None, subtitle: str | None = None) -> go.Figure:
    """Cột doanh thu Top N kèm đường tỷ trọng tích lũy (từ mart_revenue_by_country / by_category)."""
    if ranking.empty:
        return empty_figure()
    top = ranking.head(top_n)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=top[label_col], y=top["revenue_usd"], name=cfg.label("revenue_usd"),
        marker=dict(color=P["primary"], cornerradius=R), opacity=0.92,
        text=[fmt_compact(v, "$") for v in top["revenue_usd"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=P["text_muted"]),
        customdata=np.stack([top["orders"], top["avg_order_value_usd"], top["share_pct"], top["cum_share_pct"], top["rank"]], axis=-1),
        hovertemplate=_hover("<b>#%{customdata[4]} · %{x}</b>", "Doanh thu: <b>$%{y:,.0f}</b>", "Số đơn: %{customdata[0]:,}",
                             "Giá trị đơn TB: $%{customdata[1]:,.2f}", "Tỷ trọng: %{customdata[2]:.2f}%", "Tích lũy: %{customdata[3]:.2f}%"),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=top[label_col], y=top["cum_share_pct"], name=cfg.label("cum_share_pct"), mode="lines+markers",
        line=dict(color=P["alert"], width=3), marker=dict(size=8, color="white", line=dict(color=P["alert"], width=2)),
        hovertemplate=_hover("<b>%{x}</b>", "Tích lũy: <b>%{y:.2f}%</b>"),
    ), secondary_y=True)
    fig.update_yaxes(title_text=cfg.label("revenue_usd"), rangemode="tozero", secondary_y=False)
    compact_ticks(fig, float(top["revenue_usd"].max()) * 1.15, "$", secondary_y=False)
    fig.update_yaxes(title_text=cfg.label("cum_share_pct"), range=[0, 105], ticksuffix="%", showgrid=False, secondary_y=True)
    fig.update_xaxes(title_text=None, tickangle=-30)
    return apply_theme(fig, title or f"Top {len(top)} theo doanh thu",
                       subtitle=subtitle or "Đơn Delivered · USD · đường đỏ là tỷ trọng tích lũy")


def heatmap_matrix(
    long_df: pd.DataFrame, x: str, y: str, value: str, title: str,
    colorscale=cfg.HEAT_SCALE, value_title: str | None = None,
    text_format: str = ".1f", value_suffix: str = "%", row_order: list[str] | None = None,
    col_order: list[str] | None = None, zmid: float | None = None, subtitle: str | None = None,
) -> go.Figure:
    """Heatmap tổng quát từ bảng dạng dài (x, y, value). Dùng cho Câu 3 (tỷ trọng doanh thu) và Câu 8 (tỷ lệ hoàn trả).

    Các cột phụ `revenue_usd`, `orders` (nếu có) được đưa vào hover card.
    """
    if long_df.empty:
        return empty_figure()
    pivot = long_df.pivot_table(index=y, columns=x, values=value, aggfunc="mean")
    if row_order:
        pivot = pivot.reindex([r for r in row_order if r in pivot.index])
    if col_order:
        pivot = pivot.reindex(columns=[c for c in col_order if c in pivot.columns])
    extras = [(c, lab, fmt) for c, lab, fmt in (("revenue_usd", "Doanh thu", "$,.0f"), ("orders", "Số đơn", ",.0f"))
              if c in long_df.columns and c != value]
    customdata = None
    extra_lines = []
    if extras:
        layers = [long_df.pivot_table(index=y, columns=x, values=c, aggfunc="sum").reindex(index=pivot.index, columns=pivot.columns).to_numpy()
                  for c, _, _ in extras]
        customdata = np.stack(layers, axis=-1)
        extra_lines = [f"{lab}: %{{customdata[{i}]:{fmt}}}" for i, (_, lab, fmt) in enumerate(extras)]
    vtitle = value_title or cfg.label(value)
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index, colorscale=colorscale, zmid=zmid, xgap=2, ygap=2,
        colorbar=dict(title=dict(text=vtitle, font=dict(size=12, color=P["text_muted"])), ticksuffix=value_suffix,
                      thickness=12, outlinewidth=0),
        texttemplate="%{z:" + text_format + "}", textfont=dict(size=10),
        customdata=customdata,
        hovertemplate=_hover(f"<b>%{{y}} × %{{x}}</b>", f"{vtitle}: <b>%{{z:{text_format}}}{value_suffix}</b>", *extra_lines),
    ))
    fig.update_xaxes(tickangle=-40, title_text=None, showline=False, ticks="")
    fig.update_yaxes(autorange="reversed", title_text=None, showgrid=False, showline=False, ticks="")
    return apply_theme(fig, title, height=max(cfg.DEFAULT_HEIGHT, 28 * len(pivot) + 220),
                       subtitle=subtitle or "Màu càng đậm giá trị càng cao · di chuột vào ô để xem chi tiết")


# ======================================================================
# 5. CÂU 4 / CÂU 10 - TỶ LỆ RỜI BỎ (CHURN)
# ======================================================================
def bar_rate(
    df: pd.DataFrame, x: str, rate_col: str, count_col: str | None = None, overall_rate_pct: float | None = None,
    alert_multiplier: float | None = None, title: str = "", x_title: str | None = None, y_title: str | None = None,
    subtitle: str | None = None,
) -> go.Figure:
    """Cột tỷ lệ (%) theo nhóm, kèm đường tỷ lệ chung. Cột chuyển coral nếu vượt `alert_multiplier` x tỷ lệ chung.

    Dùng cho churn theo kênh (Câu 4), theo số ngày chưa mua và theo số đơn (Câu 10).
    """
    if df.empty:
        return empty_figure()
    rates = df[rate_col]
    if overall_rate_pct is not None and alert_multiplier:
        colors = [P["alert"] if r > alert_multiplier * overall_rate_pct else P["primary"] for r in rates]
    else:
        colors = P["primary"]
    extra_cols = [c for c in (count_col, "churned_customers") if c and c in df.columns]
    custom = df[extra_cols].to_numpy() if extra_cols else None
    lines = ["<b>%{x}</b>", "Tỷ lệ rời bỏ: <b>%{y:.2f}%</b>"]
    for i, c in enumerate(extra_cols):
        lines.append(("Số khách: " if c == count_col else "Đã rời bỏ: ") + f"%{{customdata[{i}]:,}}")
    if overall_rate_pct is not None:
        lines.append(f"Mặt bằng chung: {overall_rate_pct:.2f}%")
    fig = go.Figure(go.Bar(
        x=df[x].astype(str), y=rates, marker=dict(color=colors, cornerradius=R), opacity=0.92, customdata=custom,
        text=[f"{r:.1f}%" for r in rates], textposition="outside", cliponaxis=False, textfont=dict(size=11, color=P["text_muted"]),
        hovertemplate=_hover(*lines),
    ))
    if overall_rate_pct is not None:
        fig.add_hline(y=overall_rate_pct, line_dash="dash", line_color=P["navy"], line_width=1.5,
                      annotation_text=f"Chung: {overall_rate_pct:.2f}%", annotation_position="top left",
                      annotation_font=dict(size=11, color=P["navy"]))
    fig.update_yaxes(title_text=y_title or cfg.label(rate_col), ticksuffix="%", rangemode="tozero")
    fig.update_xaxes(title_text=x_title or cfg.label(x))
    default_sub = "% khách hàng đã rời bỏ" + (f" · cột coral: cao hơn {alert_multiplier:g} lần mặt bằng chung" if alert_multiplier else "")
    return apply_theme(fig, title, subtitle=subtitle or default_sub)


# ======================================================================
# 6. CÂU 5 - PHÂN PHỐI FREQUENCY / MONETARY
# ======================================================================
def histogram_distribution(
    df: pd.DataFrame, column: str, title: str, x_title: str | None = None, nbins: int = 40,
    discrete: bool = False, log_x: bool = False, show_outlier_threshold: float | None = None,
    subtitle: str | None = None,
) -> go.Figure:
    """Histogram một biến, kèm đường trung bình và trung vị.

    - ``discrete=True``: biến đếm nguyên (Frequency), mỗi cột là một giá trị.
    - ``log_x=True``: biến đổi dữ liệu bằng log1p(x) = ln(1 + x) để thấy hình dạng khi co đuôi phải.
    """
    if df.empty:
        return empty_figure()
    series = df[column].dropna()
    if log_x:
        series = np.log1p(series[series >= 0])
    if series.empty:
        return empty_figure()

    mean, median = float(series.mean()), float(series.median())

    if discrete:
        counts = series.value_counts().sort_index()
        share = counts / counts.sum() * 100
        fig = go.Figure(go.Bar(
            x=counts.index, y=counts.values, marker=dict(color=P["primary"], cornerradius=R), opacity=0.92,
            text=[f"{v:,}" for v in counts.values], textposition="outside", cliponaxis=False,
            textfont=dict(size=11, color=P["text_muted"]), customdata=share.round(1).to_numpy(),
            hovertemplate=_hover("<b>%{x} đơn hàng</b>", "Số khách: <b>%{y:,}</b>", "Tỷ lệ: %{customdata:.1f}%"),
        ))
        fig.update_xaxes(dtick=1)
    else:
        fig = px.histogram(series.to_frame(name=column), x=column, nbins=nbins, color_discrete_sequence=[P["primary"]])
        fig.update_traces(marker=dict(line=dict(color="white", width=1)), opacity=0.9,
                          hovertemplate=_hover("Khoảng: <b>%{x}</b>", "Số khách: <b>%{y:,}</b>"))

    fig.add_vline(x=mean, line_dash="dash", line_color=P["alert"], line_width=2,
                  annotation_text=f"Trung bình {mean:,.2f}", annotation_position="top right",
                  annotation_font=dict(size=11, color=P["alert"]))
    fig.add_vline(x=median, line_dash="dashdot", line_color=P["navy"], line_width=2,
                  annotation_text=f"Trung vị {median:,.2f}", annotation_position="top left",
                  annotation_font=dict(size=11, color=P["navy"]))
    if show_outlier_threshold is not None and (not log_x or show_outlier_threshold >= 0):
        thresh = float(np.log1p(show_outlier_threshold)) if log_x else show_outlier_threshold
        thresh_fmt = f"{thresh:,.2f}" if log_x else f"{thresh:,.0f}"
        fig.add_vline(x=thresh, line_dash="dot", line_color=P["text_muted"], line_width=1.5,
                      annotation_text=f"Ngưỡng ngoại lai {thresh_fmt}", annotation_position="top right",
                      annotation_font=dict(size=11, color=P["text_muted"]))

    fig.update_xaxes(title_text=x_title or cfg.label(column))
    fig.update_yaxes(title_text="Số khách hàng", rangemode="tozero")
    fig.update_layout(bargap=0.06)
    default_sub = "Số khách hàng theo " + ("số đơn" if discrete else ("log1p(tổng chi tiêu)" if log_x else "tổng chi tiêu"))
    return apply_theme(fig, title, subtitle=subtitle or default_sub)


def bar_revenue_concentration(conc: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Tỷ trọng doanh thu của top X% khách hàng (từ mart_revenue_concentration)."""
    if conc.empty:
        return empty_figure()
    n = len(conc)
    shades = [P["primary_light"], "#2DD4BF", P["primary"], "#0F766E", "#115E59"][-n:] if n <= 5 else cfg.CATEGORICAL_COLORS[:n]
    fig = go.Figure(go.Bar(
        x=[f"Top {int(p)}%" for p in conc["top_customer_pct"]], y=conc["revenue_share_pct"],
        marker=dict(color=shades, cornerradius=R), opacity=0.95,
        text=[f"{v:.1f}%" for v in conc["revenue_share_pct"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=P["text_muted"]), customdata=conc["customers"],
        hovertemplate=_hover("<b>%{x} khách chi tiêu cao nhất</b>", "Số khách: %{customdata:,}", "Đóng góp: <b>%{y:.2f}%</b> tổng Monetary"),
    ))
    fig.update_yaxes(title_text="Tỷ trọng Monetary (%)", ticksuffix="%", range=[0, max(conc["revenue_share_pct"]) * 1.2])
    return apply_theme(fig, "Mức độ tập trung doanh thu theo nhóm khách chi tiêu cao",
                       subtitle=subtitle or "% tổng Monetary do top X% khách đóng góp")


# ======================================================================
# 7. CÂU 6 - DISCOUNT
# ======================================================================
def box_by_discount_group(df: pd.DataFrame, y: str, title: str, y_title: str | None = None, subtitle: str | None = None) -> go.Figure:
    """Boxplot theo nhóm chiết khấu. `df` cần có cột `discount_group` (xem data_processor.add_discount_group)."""
    if df.empty:
        return empty_figure()
    fig = px.box(
        df, x="discount_group", y=y, points="outliers", category_orders={"discount_group": cfg.DISCOUNT_LABELS},
        color="discount_group", color_discrete_sequence=cfg.CATEGORICAL_COLORS,
    )
    fig.update_traces(line=dict(width=1.5), marker=dict(size=4, opacity=0.45), opacity=0.9)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text=cfg.label("discount_group"))
    fig.update_yaxes(title_text=y_title or cfg.label(y), rangemode="tozero")
    if y == "total_amount_usd":
        compact_ticks(fig, float(df[y].max()), "$")
    return apply_theme(fig, title, subtitle=subtitle or "Hộp: Q1–Q3 · vạch giữa: trung vị · chấm: ngoại lai · di chuột để xem thống kê")


# ======================================================================
# 8. CÂU 7 / CÂU 8 - VẬN CHUYỂN VÀ CHẤT LƯỢNG NHÓM HÀNG
# ======================================================================
def dual_axis_shipping(ship: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Cột phí vận chuyển TB (trục trái) và đường thời gian giao TB (trục phải) theo quốc gia (từ mart_shipping_by_country)."""
    if ship.empty:
        return empty_figure()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=ship["country"], y=ship["avg_shipping_fee_usd"], name=cfg.label("avg_shipping_fee_usd"),
        marker=dict(color=P["primary_light"], cornerradius=R), customdata=np.stack([ship["orders"], ship["avg_delivery_days"]], axis=-1),
        hovertemplate=_hover("<b>%{x}</b>", "Phí vận chuyển TB: <b>$%{y:.2f}</b>", "Giao hàng TB: %{customdata[1]:.2f} ngày", "Số đơn: %{customdata[0]:,}"),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=ship["country"], y=ship["avg_delivery_days"], name=cfg.label("avg_delivery_days"),
        mode="lines+markers", line=dict(color=P["alert"], width=3), marker=dict(size=7, color="white", line=dict(color=P["alert"], width=2)),
        customdata=ship["avg_shipping_fee_usd"],
        hovertemplate=_hover("<b>%{x}</b>", "Giao hàng TB: <b>%{y:.2f} ngày</b>", "Phí vận chuyển TB: $%{customdata:.2f}"),
    ), secondary_y=True)
    fig.update_yaxes(title_text=cfg.label("avg_shipping_fee_usd"), tickprefix="$", rangemode="tozero", secondary_y=False)
    fig.update_yaxes(title_text=cfg.label("avg_delivery_days"), showgrid=False, rangemode="tozero", secondary_y=True)
    fig.update_xaxes(tickangle=-40, title_text=None)
    return apply_theme(fig, "Chi phí và thời gian vận chuyển theo quốc gia",
                       subtitle=subtitle or "Tất cả đơn hàng · cột: phí vận chuyển (USD) · đường: số ngày giao")


def bubble_category(perf: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Bubble chart nhóm hàng: X = thời gian giao, Y = rating, kích thước = doanh thu, màu = nhóm hàng (từ mart_category_performance)."""
    if perf.empty:
        return empty_figure()
    fig = px.scatter(
        perf, x="avg_delivery_days", y="avg_rating", size="revenue_usd", color="category", size_max=55,
        custom_data=["return_rate_pct", "orders", "revenue_usd"], color_discrete_sequence=cfg.CATEGORICAL_COLORS,
    )
    fig.update_traces(marker=dict(opacity=0.8, line=dict(color="white", width=1.5)),
                      hovertemplate=_hover("<b>%{fullData.name}</b>", "Giao hàng TB: %{x:.2f} ngày", "Rating TB: %{y:.2f}",
                                           "Hoàn trả: %{customdata[0]:.2f}%", "Số đơn: %{customdata[1]:,}", "Doanh thu: <b>$%{customdata[2]:,.0f}</b>"))
    fig.add_vline(x=perf["avg_delivery_days"].mean(), line_dash="dot", line_color=P["text_muted"], line_width=1)
    fig.add_hline(y=perf["avg_rating"].mean(), line_dash="dot", line_color=P["text_muted"], line_width=1)
    fig.update_xaxes(title_text=cfg.label("avg_delivery_days"), showgrid=True, gridcolor=P["grid"], griddash="dot")
    fig.update_yaxes(title_text=cfg.label("avg_rating"))
    return apply_theme(fig, "Nhóm hàng: thời gian giao, rating và doanh thu", height=560,
                       subtitle=subtitle or "Kích thước bong bóng = doanh thu · đường chấm = mức trung bình các nhóm")


def bar_category_performance(perf: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Return rate (cột) và rating TB (đường, trục phải) theo nhóm hàng."""
    if perf.empty:
        return empty_figure()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=perf["category"], y=perf["return_rate_pct"], name=cfg.label("return_rate_pct"),
        marker=dict(color=P["alert"], cornerradius=R), opacity=0.9,
        customdata=np.stack([perf["avg_rating"], perf["orders"]], axis=-1),
        hovertemplate=_hover("<b>%{x}</b>", "Hoàn trả: <b>%{y:.2f}%</b>", "Rating TB: %{customdata[0]:.2f}", "Số đơn: %{customdata[1]:,}"),
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=perf["category"], y=perf["avg_rating"], name=cfg.label("avg_rating"), mode="lines+markers",
        line=dict(color=P["navy"], width=3), marker=dict(size=7, color="white", line=dict(color=P["navy"], width=2)),
        customdata=perf["return_rate_pct"],
        hovertemplate=_hover("<b>%{x}</b>", "Rating TB: <b>%{y:.2f}</b>", "Hoàn trả: %{customdata:.2f}%"),
    ), secondary_y=True)
    fig.update_yaxes(title_text=cfg.label("return_rate_pct"), ticksuffix="%", rangemode="tozero", secondary_y=False)
    fig.update_yaxes(title_text=cfg.label("avg_rating"), showgrid=False, secondary_y=True)
    fig.update_xaxes(tickangle=-40, title_text=None)
    return apply_theme(fig, "Tỷ lệ hoàn trả và rating theo nhóm hàng",
                       subtitle=subtitle or "Tất cả đơn hàng · cột: tỷ lệ hoàn trả (%) · đường: rating trung bình")


# ======================================================================
# 9. CÂU 9 / CÂU 10 - KHÁCH HÀNG TOP VÀ DOANH THU THUẦN THEO NHÓM HÀNG
# ======================================================================
def bar_top_customers(top: pd.DataFrame, subtitle: str | None = None) -> go.Figure:
    """Top khách chi tiêu cao nhất; cột coral = đã rời bỏ (từ mart_top_customers)."""
    if top.empty:
        return empty_figure()
    d = top.sort_values("total_spend_usd")
    colors = [P["alert"] if c == 1 else P["primary"] for c in d["churned"]]
    fig = go.Figure(go.Bar(
        x=d["total_spend_usd"], y=d["customer_id"], orientation="h", marker=dict(color=colors, cornerradius=R), opacity=0.92,
        text=[fmt_compact(v, "$") for v in d["total_spend_usd"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=P["text_muted"]),
        customdata=np.stack([d["country"], d["membership_tier"], d["total_orders"], np.where(d["churned"] == 1, "Đã rời bỏ", "Còn hoạt động")], axis=-1),
        hovertemplate=_hover("<b>%{y}</b>", "Tổng chi tiêu: <b>$%{x:,.0f}</b>", "Quốc gia: %{customdata[0]}", "Hạng: %{customdata[1]}",
                             "Số đơn: %{customdata[2]}", "Trạng thái: %{customdata[3]}"),
    ))
    fig.update_xaxes(title_text="Tổng chi tiêu (USD)", showgrid=True, gridcolor=P["grid"], griddash="dot")
    compact_ticks(fig, float(d["total_spend_usd"].max()) * 1.12, "$", axis="x")
    fig.update_yaxes(title_text=None, type="category", showgrid=False)
    return apply_theme(fig, f"Top {len(d)} khách chi tiêu cao nhất",
                       subtitle=subtitle or "Tổng chi tiêu tích lũy (USD) · cột coral = khách đã rời bỏ")


def barh_category_revenue(cat_rev: pd.DataFrame, title: str = "Doanh thu thuần theo nhóm hàng", subtitle: str | None = None) -> go.Figure:
    """Cột ngang doanh thu theo nhóm hàng, tô đậm nhóm dẫn đầu (từ mart_category_revenue_net)."""
    if cat_rev.empty:
        return empty_figure()
    d = cat_rev.sort_values("revenue_usd")
    colors = [P["neutral"]] * len(d)
    colors[-1] = P["primary"]
    fig = go.Figure(go.Bar(
        x=d["revenue_usd"], y=d["category"], orientation="h", marker=dict(color=colors, cornerradius=R),
        text=[fmt_compact(v, "$") for v in d["revenue_usd"]], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=P["text_muted"]), customdata=d["share_pct"],
        hovertemplate=_hover("<b>%{y}</b>", "Doanh thu: <b>$%{x:,.0f}</b>", "Tỷ trọng: %{customdata:.2f}%"),
    ))
    fig.update_xaxes(title_text=cfg.label("revenue_usd"), showgrid=True, gridcolor=P["grid"], griddash="dot")
    compact_ticks(fig, float(d["revenue_usd"].max()) * 1.15, "$", axis="x")
    fig.update_yaxes(title_text=None, showgrid=False)
    return apply_theme(fig, title, height=max(cfg.DEFAULT_HEIGHT, 30 * len(d) + 160),
                       subtitle=subtitle or "Loại đơn Cancelled và Returned · USD · nhóm dẫn đầu tô đậm")