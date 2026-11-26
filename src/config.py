"""Cấu hình trung tâm: đường dẫn, tên cột, tham số phân tích và Design System.

Mọi module trong ``src/`` và ``dashboards/`` chỉ import hằng số từ file này,
không tự viết cứng đường dẫn hay mã màu.
"""
from __future__ import annotations

from pathlib import Path

# ======================================================================
# 1. ĐƯỜNG DẪN CHUẨN (tính từ vị trí file, chạy được từ bất kỳ thư mục nào)
# ======================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"          # dữ liệu gốc, chỉ đọc
DATA_CLEANED = DATA_DIR / "cleaned"  # dữ liệu sạch dạng bảng chi tiết
DATA_MARTS = DATA_DIR / "marts"      # bảng tổng hợp cho dashboard

NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"
PLOTLY_APP_DIR = DASHBOARDS_DIR / "plotly_app"

EXPORTS_DIR = PROJECT_ROOT / "exports"
EXPORTS_HTML = EXPORTS_DIR / "interactive_html"
EXPORTS_PNG = EXPORTS_DIR / "archive_static_png"


def ensure_dirs() -> None:
    """Tạo các thư mục đầu ra nếu chưa có."""
    for folder in (DATA_RAW, DATA_CLEANED, DATA_MARTS, EXPORTS_HTML, EXPORTS_PNG, PLOTLY_APP_DIR):
        folder.mkdir(parents=True, exist_ok=True)


# ======================================================================
# 2. TÊN FILE
# ======================================================================
CLEANED_FILES = {
    "orders": "orders_cleaned.csv",
    "customers": "customers_cleaned.csv",
    "monthly_revenue": "monthly_revenue_cleaned.csv",
    "product_summary": "product_summary_cleaned.csv",
}
QUALITY_REPORT_FILE = "data_quality_report.csv"

# Bảng tổng hợp do data_processor.py tạo ra (tiền tố mart_ để không ghi đè
# các file CSV mà notebook của nhóm xuất: cau4_*.csv, discount_summary.csv, q5_*.csv).
MART_FILES = {
    "fact_orders": "mart_fact_orders.csv",
    "kpi_overview": "mart_kpi_overview.csv",
    "monthly_trend": "mart_monthly_trend.csv",
    "monthly_seasonality": "mart_monthly_seasonality.csv",
    "revenue_by_country": "mart_revenue_by_country.csv",
    "revenue_by_category": "mart_revenue_by_category.csv",
    "country_category_revenue": "mart_country_category_revenue.csv",
    "churn_by_channel": "mart_churn_by_channel.csv",
    "customer_fm": "mart_customer_frequency_monetary.csv",
    "revenue_concentration": "mart_revenue_concentration.csv",
    "discount_groups": "mart_discount_groups.csv",
    "discount_tests": "mart_discount_tests.csv",
    "shipping_by_country": "mart_shipping_by_country.csv",
    "category_performance": "mart_category_performance.csv",
    "country_category_return": "mart_country_category_return.csv",
    "top_customers": "mart_top_customers.csv",
    "top_customers_summary": "mart_top_customers_summary.csv",
    "churn_by_recency": "mart_churn_by_recency.csv",
    "churn_by_order_count": "mart_churn_by_order_count.csv",
    "category_revenue_net": "mart_category_revenue_net.csv",
}
MART_ENCODING = "utf-8-sig"  # mở đúng tiếng Việt trong Excel


# ======================================================================
# 3. TÊN CỘT CHUẨN (khớp schema data/cleaned/)
# ======================================================================
class OrderCol:
    ORDER_ID = "order_id"
    CUSTOMER_ID = "customer_id"
    ORDER_DATE = "order_date"
    YEAR = "year"
    MONTH = "month"
    CATEGORY = "category"
    PRODUCT_NAME = "product_name"
    QUANTITY = "quantity"
    DISCOUNT_PCT = "discount_pct"
    SHIPPING_FEE = "shipping_fee_usd"
    TOTAL_AMOUNT = "total_amount_usd"
    DELIVERY_DAYS = "delivery_days"
    ORDER_STATUS = "order_status"
    RETURNED = "returned"
    RATING = "customer_rating"


class CustomerCol:
    CUSTOMER_ID = "customer_id"
    COUNTRY = "country"
    MEMBERSHIP_TIER = "membership_tier"
    ACQUISITION_CHANNEL = "acquisition_channel"
    TOTAL_ORDERS = "total_orders"
    TOTAL_SPEND = "total_spend_usd"
    DAYS_SINCE_LAST_PURCHASE = "days_since_last_purchase"
    CHURNED = "churned"


class MonthlyCol:
    YEAR = "year"
    MONTH = "month"
    REVENUE = "revenue_usd"


# Nhãn hiển thị tiếng Việt cho trục, tooltip và bảng
COLUMN_LABELS = {
    "country": "Quốc gia",
    "category": "Nhóm hàng",
    "acquisition_channel": "Kênh thu hút",
    "membership_tier": "Hạng thành viên",
    "revenue_usd": "Doanh thu (USD)",
    "orders": "Số đơn hàng",
    "avg_order_value_usd": "Giá trị đơn trung bình (USD)",
    "share_pct": "Tỷ trọng (%)",
    "cum_share_pct": "Tỷ trọng tích lũy (%)",
    "month": "Tháng",
    "frequency": "Frequency (số đơn)",
    "monetary": "Monetary (USD)",
    "churn_rate_pct": "Tỷ lệ rời bỏ (%)",
    "return_rate_pct": "Tỷ lệ hoàn trả (%)",
    "avg_rating": "Rating trung bình",
    "avg_delivery_days": "Thời gian giao hàng TB (ngày)",
    "avg_shipping_fee_usd": "Phí vận chuyển TB (USD)",
    "discount_group": "Nhóm chiết khấu",
    "quantity": "Số lượng sản phẩm",
    "total_amount_usd": "Giá trị giao dịch (USD)",
}


def label(column: str) -> str:
    """Nhãn tiếng Việt của một cột; nếu chưa khai báo thì trả lại tên cột."""
    return COLUMN_LABELS.get(column, column)


# ======================================================================
# 4. QUY ƯỚC PHÂN TÍCH (lấy từ các notebook của nhóm)
# ======================================================================
STATUS_DELIVERED = "Delivered"
# Câu 5 và Câu 10: loại đơn hủy và hoàn khỏi phân tích doanh thu thuần.
STATUS_EXCLUDED_NET = ("Cancelled", "Returned")

# Câu 2: các năm đủ 12 tháng để phân tích tính thời vụ.
SEASONALITY_YEARS = (2020, 2025)
MOVING_AVERAGE_WINDOW = 3  # Câu 2/10: đường trung bình trượt 3 tháng

# Câu 3: số phần tử trong Top N
TOP_N_RANKING = 10

# Câu 5
HIGH_FREQUENCY_THRESHOLD = 6
IQR_MULTIPLIER = 1.5
CONCENTRATION_PERCENTS = (1, 5, 10, 20)

# Câu 6: nhóm chiết khấu
DISCOUNT_BINS = [-0.001, 0, 10, 20, 30, 100]
DISCOUNT_LABELS = ["0% (Không giảm)", "1–10%", "11–20%", "21–30%", "Trên 30%"]

# Câu 9
TOP_N_CUSTOMERS = 10

# Câu 10: nhóm khách theo số ngày chưa mua và số đơn đã mua
RECENCY_BINS = [-1, 30, 60, 90, 180, 365, float("inf")]
RECENCY_LABELS = ["0–30", "31–60", "61–90", "91–180", "181–365", ">365"]
ORDER_COUNT_BINS = [0, 2, 5, 10, 20, float("inf")]
ORDER_COUNT_LABELS = ["1–2 đơn", "3–5 đơn", "6–10 đơn", "11–20 đơn", ">20 đơn"]
CHURN_ALERT_MULTIPLIER = 2  # cột đỏ nếu tỷ lệ rời bỏ > 2 lần mặt bằng chung


# ======================================================================
# 5. DESIGN SYSTEM (dùng chung cho toàn bộ biểu đồ Plotly)
# ======================================================================
PALETTE = {
    "navy": "#1E293B",           # tiêu đề, đường tham chiếu, nhấn mạnh phụ
    "primary": "#0D9488",        # teal: số liệu chính, mục dẫn đầu
    "primary_light": "#5EEAD4",  # teal nhạt: số liệu phụ
    "alert": "#F43F5E",          # coral: cảnh báo, rủi ro, ngoại lai
    "warning": "#F59E0B",        # hổ phách: điểm cần chú ý
    "positive": "#10B981",       # xanh lá: tích cực
    "neutral": "#CBD5E1",        # slate nhạt: phần còn lại
    "text": "#1E293B",
    "text_muted": "#64748B",     # slate: subtitle, nhãn phụ
    "grid": "#E2E8F0",           # đường lưới
    "axis": "#CBD5E1",           # đường trục
    "background": "#FFFFFF",
}

# Dãy màu phân loại (nhóm hàng, quốc gia...) - 10 màu hài hòa, tương phản cao
CATEGORICAL_COLORS = [
    "#0D9488", "#1E293B", "#F43F5E", "#F59E0B", "#6366F1",
    "#0EA5E9", "#84CC16", "#A855F7", "#EC4899", "#64748B",
]

# Thang màu liên tục (heatmap)
TEAL_SCALE = ["#F0FDFA", "#99F6E4", "#2DD4BF", "#0D9488", "#115E59"]    # tỷ trọng, doanh thu
CORAL_SCALE = ["#FFF1F2", "#FDA4AF", "#FB7185", "#F43F5E", "#9F1239"]   # tỷ lệ rủi ro (hoàn trả)
SEQUENTIAL_SCALE = TEAL_SCALE
HEAT_SCALE = TEAL_SCALE      # Câu 3: tỷ trọng doanh thu
DIVERGING_SCALE = "RdBu_r"   # tương quan

FONT_FAMILY = "Inter, Segoe UI, Arial, sans-serif"
FONT_SIZE = 13
TITLE_FONT_SIZE = 18
SUBTITLE_FONT_SIZE = 12
DEFAULT_HEIGHT = 480
BAR_CORNER_RADIUS = 6
