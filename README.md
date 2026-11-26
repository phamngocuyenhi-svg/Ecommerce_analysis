# Ecommerce_analysis

Phân tích dữ liệu thương mại điện tử **E-Commerce Customer Behavior & Sales (2020–2026)** (25.000 đơn hàng, 8.000 khách hàng, 20 quốc gia, 14 nhóm hàng) cho môn Trực quan hóa dữ liệu. Dự án đi từ làm sạch dữ liệu, phân tích theo 10 câu hỏi, đến một dashboard tương tác bằng **Plotly Dash** cùng bộ biểu đồ HTML xuất sẵn.

## 1. Kiến trúc 3 tầng

```
 TẦNG 1: DỮ LIỆU            TẦNG 2: XỬ LÝ                       TẦNG 3: TRÌNH BÀY
 ┌─────────────────┐        ┌───────────────────────────┐       ┌────────────────────────────┐
 │ data/raw        │──────▶ │ notebooks/00_data_cleaning│       │ dashboards/plotly_app      │
 │ (dữ liệu gốc)   │        └────────────┬──────────────┘       │   app.py (lọc chéo)        │
 └─────────────────┘                     ▼                      │   export_html.py           │
 ┌─────────────────┐        ┌───────────────────────────┐       ├────────────────────────────┤
 │ data/cleaned    │──────▶ │ notebooks/01..10 (phân    │       │ exports/                   │
 │ (dữ liệu sạch)  │   │    │ tích từng câu của nhóm)   │       │   interactive_html (HTML)  │
 └─────────────────┘   │    ├───────────────────────────┤       │   archive_static_png (PNG) │
 ┌─────────────────┐   └──▶ │ src/ (lõi dùng chung)     │──────▶└────────────────────────────┘
 │ data/marts      │◀────── │  config, data_processor,  │
 │ (bảng tổng hợp) │        │  chart_builders           │
 └─────────────────┘        └───────────────────────────┘
```

- **Tầng 1 – Dữ liệu:** `data/raw/` chỉ đọc; `data/cleaned/` là nguồn sạch duy nhất; `data/marts/` chứa bảng tổng hợp.
- **Tầng 2 – Xử lý:** `notebooks/` là bài làm của nhóm (logic gốc giữ nguyên, 1 câu = 1 file). `src/` là lõi dùng chung: đường dẫn, quy ước phân tích, bảng màu, hàm tổng hợp và hàm vẽ biểu đồ.
- **Tầng 3 – Trình bày:** dashboard Plotly đọc trực tiếp `data/cleaned/` qua `src/`; biểu đồ xuất sẵn nằm trong `exports/`.

## 2. Cấu trúc thư mục

```text
Ecommerce_analysis/
├── data/
│   ├── raw/                     # customers, orders, monthly_revenue, product_summary (.csv gốc)
│   ├── cleaned/                 # *_cleaned.csv và data_quality_report.csv (do notebook 00 tạo)
│   └── marts/                   # bảng tổng hợp (notebook xuất và mart_*.csv do src xuất)
├── notebooks/
│   ├── 00_data_cleaning.ipynb
│   └── 01_cau_1.ipynb ... 10_cau_10.ipynb
├── src/
│   ├── config.py                # đường dẫn, tên cột, quy ước phân tích, Design System
│   ├── data_processor.py        # đọc data/cleaned/ và tạo các bảng tổng hợp
│   └── chart_builders.py        # hàm vẽ biểu đồ Plotly dùng lại
├── dashboards/
│   └── plotly_app/              # app.py (dashboard), export_html.py
├── exports/
│   ├── interactive_html/        # biểu đồ HTML tương tác
│   └── archive_static_png/      # ảnh tĩnh do notebook xuất
├── README.md
└── requirements.txt
```

## 3. Bắt đầu nhanh

```bash
# 1. Cài thư viện (Python 3.10 trở lên)
pip install -r requirements.txt

# 2. Đặt 4 file gốc vào data/raw/ rồi chạy notebooks/00_data_cleaning.ipynb
#    (nếu data/cleaned/ đã có sẵn thì bỏ qua bước này)

# 3. Chạy dashboard tương tác (chạy từ thư mục gốc dự án)
python dashboards/plotly_app/app.py        # mở http://127.0.0.1:8050

# 4. (Tùy chọn) xuất biểu đồ HTML và bảng tổng hợp
python dashboards/plotly_app/export_html.py
python -m src.data_processor
```

Các lệnh Python phải chạy **từ thư mục gốc** `Ecommerce_analysis/`. Notebook thì mở và chạy trong thư mục `notebooks/` (đường dẫn trong notebook dùng `../`).

## 4. Notebook

Chạy `00_data_cleaning` trước, các câu còn lại độc lập với nhau và chỉ cần `data/cleaned/`.

| Notebook | Nội dung | File xuất |
|---|---|---|
| `00_data_cleaning` | Làm sạch 4 bảng gốc, báo cáo chất lượng | `data/cleaned/*.csv`, ảnh EDA vào `exports/archive_static_png/` |
| `01_cau_1` | Tổng quan KPI | `kpi_overview.png` |
| `02_cau_2` | Doanh thu theo tháng, tính thời vụ | `monthly_revenue_trend.png`, `monthly_revenue_seasonality.png` |
| `03_cau_3` | Top quốc gia, nhóm hàng theo doanh thu | `top10_country.png`, `top10_category.png`, `heatmap_country_category.png` |
| `04_cau_4` | Churn theo kênh thu hút, kèm kiểm định chi-bình phương | `data/marts/cau4_churn_by_channel.csv`, `cau4_churn_by_channel.png` |
| `05_cau_5` | Phân phối Frequency và Monetary | `data/marts/q5_*.csv`, `q5_hist_*.png`, `q5_revenue_concentration.png` |
| `06_cau_6` | Ảnh hưởng của Discount | `data/marts/discount_summary.csv`, `cau6_nhan_xet.txt`, `boxplot_*.png`, `boxplot_*.html` |
| `07_cau_7` | Chi phí và thời gian vận chuyển theo quốc gia | `cau7_shipping_by_country.png` |
| `08_cau_8` | Return rate, rating theo nhóm hàng; Heatmap, Bubble | `cau8_return_rate_rating_by_category.png`, `cau8_heatmap_*.png`, `cau8_bubble_category.png` |
| `09_cau_9` | Top 10 khách chi tiêu cao nhất | `cau9_top10_customers.png` |
| `10_cau_10` | Dashboard bán hàng và giữ chân khách hàng | `dashboard_ban_hang.png` |

Quy tắc khi sửa notebook: giữ nguyên logic của nhóm; mọi đường dẫn đọc/ghi phải trỏ vào `../data/...` và `../exports/...`.

## 5. Dashboard Plotly

```bash
python dashboards/plotly_app/app.py --port 8050      # thêm --debug khi phát triển
python dashboards/plotly_app/export_html.py          # xuất 21 biểu đồ HTML vào exports/interactive_html/
```

- 5 tab: Tổng quan, Doanh thu, Khách hàng, Vận hành, Khuyến mãi (bao phủ Câu 1–10).
- **Lọc chéo:** thanh trên cùng gồm năm, quốc gia, nhóm hàng, kênh thu hút, hạng thành viên. Bấm vào cột quốc gia, nhóm hàng, kênh hoặc ô heatmap để lọc nhanh; nút **Xóa bộ lọc** đặt lại.
- Hover hiển thị đủ chỉ số của từng điểm; kéo để phóng to, thanh trượt dưới biểu đồ doanh thu để chọn khoảng thời gian.
- App tính trực tiếp từ `data/cleaned/` nên không phụ thuộc bước xuất marts.
- Tỷ lệ rời bỏ và Top khách hàng tính trên bảng khách hàng nên chỉ chịu tác động của quốc gia, kênh, hạng thành viên (không phụ thuộc năm và nhóm hàng); trên tab có ghi chú.

### Design System

Mọi biểu đồ lấy màu, font và quy tắc trình bày từ `src/config.py` và `src/chart_builders.py`, nên đổi một chỗ là đổi cả dashboard:

- Nền trong suốt; bảng màu Navy `#1E293B`, Teal `#0D9488`, Coral `#F43F5E`; chữ phụ slate `#64748B`; lưới chấm `#E2E8F0`.
- Mỗi biểu đồ có tiêu đề kèm subtitle (ngữ cảnh, đơn vị), số rút gọn `K`/`M`, cột bo góc, legend ngang phía trên.
- Muốn thêm biểu đồ mới: viết hàm trong `chart_builders.py` và kết thúc bằng `apply_theme(...)`.

## 6. Bảng tổng hợp (`data/marts/`)

`python -m src.data_processor` xuất 20 file `mart_*.csv` (UTF-8 có BOM, mở đúng tiếng Việt trong Excel). Tên file khai báo trong `src/config.py` (`MART_FILES`). Dashboard không bắt buộc cần các file này, chúng phục vụ tra cứu, kiểm tra số liệu và dùng lại ở công cụ khác. Các nhóm chính:

| Nhóm | Mart |
|---|---|
| Bảng sự kiện | `mart_fact_orders` (đơn hàng ghép quốc gia, kênh, hạng thành viên) |
| Doanh thu | `mart_kpi_overview`, `mart_monthly_trend`, `mart_monthly_seasonality`, `mart_revenue_by_country`, `mart_revenue_by_category`, `mart_country_category_revenue`, `mart_category_revenue_net` |
| Khách hàng | `mart_churn_by_channel`, `mart_churn_by_recency`, `mart_churn_by_order_count`, `mart_customer_frequency_monetary`, `mart_revenue_concentration`, `mart_top_customers`, `mart_top_customers_summary` |
| Vận hành | `mart_shipping_by_country`, `mart_category_performance`, `mart_country_category_return` |
| Khuyến mãi | `mart_discount_groups`, `mart_discount_tests` |

Tiền tố `mart_` giúp không ghi đè các file do notebook xuất (`cau4_*.csv`, `discount_summary.csv`, `q5_*.csv`).

## 7. Quy ước loại đơn hàng

Mỗi câu của nhóm dùng một quy ước khác nhau về trạng thái đơn, nên số liệu giữa các biểu đồ có thể khác nhau. Đây là chủ ý, đã ghi trong `src/config.py`:

| Quy ước | Áp dụng |
|---|---|
| Chỉ đơn `Delivered` | Câu 2 (`monthly_revenue`), Câu 3 |
| Loại `Cancelled` và `Returned` | Câu 5, Câu 10 (doanh thu thuần) |
| Tất cả đơn hàng | Câu 1, 6, 7, 8 |

## 8. Xử lý sự cố

- **`FileNotFoundError ... orders_cleaned.csv`:** chưa có dữ liệu sạch. Chạy `notebooks/00_data_cleaning.ipynb` (cần 4 file trong `data/raw/`).
- **`ModuleNotFoundError: src`:** đang chạy lệnh ngoài thư mục gốc. Dùng `python -m src.data_processor` từ `Ecommerce_analysis/`.
- **Notebook Câu 6 báo lỗi `tick_labels`:** matplotlib cũ hơn 3.9, chạy `pip install -U matplotlib`.
- **Cổng 8050 đang bận:** chạy `python dashboards/plotly_app/app.py --port 8060`.
