# Ecommerce_analysis

Phân tích dữ liệu thương mại điện tử **E-Commerce Customer Behavior & Sales (2020–2026)** (25.000 đơn hàng, 8.000 khách hàng, 20 quốc gia, 14 nhóm hàng) cho môn Trực quan hóa dữ liệu. Dự án đi từ làm sạch dữ liệu, phân tích theo 10 câu hỏi, đến ứng dụng Dashboard tương tác bằng **Plotly Dash** và bộ thành phẩm xuất sẵn trong thư mục `report/`.

## 1. Kiến trúc 3 tầng

```text
 TẦNG 1: DỮ LIỆU            TẦNG 2: XỬ LÝ                       TẦNG 3: TRÌNH BÀY & THÀNH PHẨM
 ┌─────────────────┐        ┌───────────────────────────┐       ┌────────────────────────────┐
 │ data/raw        │──────▶ │ notebooks/00_data_cleaning│       │ dashboards/plotly_app      │
 │ (dữ liệu gốc)   │        └────────────┬──────────────┘       │   app.py (lọc chéo động)   │
 └─────────────────┘                     ▼                      │   export_html.py           │
 ┌─────────────────┐        ┌───────────────────────────┐       ├────────────────────────────┤
 │ data/cleaned    │──────▶ │ notebooks/01..10 (phân    │──────▶│ report/                    │
 │ (dữ liệu sạch)  │   │    │ tích từng câu của nhóm)   │       │   dashboard.html (5 Tab)   │
 └─────────────────┘   │    ├───────────────────────────┤       │   *.png (26 ảnh tĩnh)      │
                       └──▶ │ src/ (lõi dùng chung)     │──────▶│   *.csv, *.txt (Câu 4,5,6) │
                            │  config, data_processor,  │       └────────────────────────────┘
                            │  chart_builders           │
                            └───────────────────────────┘
```

- **Tầng 1 – Dữ liệu:** `data/raw/` chỉ đọc; `data/cleaned/` là nguồn dữ liệu sạch duy nhất cho toàn bộ phân tích.
- **Tầng 2 – Xử lý:** `notebooks/` là bài làm gốc của nhóm (1 câu = 1 file `.ipynb`). `src/` là lõi dùng chung: đường dẫn, quy ước phân tích, bảng màu, hàm tổng hợp trong bộ nhớ và hàm dựng biểu đồ Plotly.
- **Tầng 3 – Trình bày & Thành phẩm:** `dashboards/plotly_app/app.py` chạy web app tương tác lọc chéo; toàn bộ thành phẩm xuất sẵn (1 file `report/dashboard.html` tổng hợp đủ 5 Tab + 26 ảnh `.png` tĩnh + các bảng phụ từ notebook) nằm gọn trong `report/`.

## 2. Cấu trúc thư mục

```text
Ecommerce_analysis/
├── data/
│   ├── raw/                     # customers, orders, monthly_revenue, product_summary (.csv gốc)
│   └── cleaned/                 # *_cleaned.csv và data_quality_report.csv (do notebook 00 tạo)
├── notebooks/
│   ├── 00_data_cleaning.ipynb
│   └── 01_cau_1.ipynb ... 10_cau_10.ipynb
├── src/
│   ├── config.py                # đường dẫn, tên cột, quy ước phân tích, Design System
│   ├── data_processor.py        # đọc data/cleaned/ và tính toán các bảng tổng hợp
│   └── chart_builders.py        # hàm vẽ biểu đồ Plotly dùng lại
├── dashboards/
│   └── plotly_app/              # app.py (dashboard lọc chéo), export_html.py (xuất dashboard.html)
├── report/
│   ├── dashboard.html           # thành phẩm Dashboard tương tác 5 Tab (mở trực tiếp bằng trình duyệt)
│   ├── *.png                    # 26 ảnh biểu đồ tĩnh xuất từ notebooks 00..10
│   └── *.csv, *.txt             # bảng thống kê & nhận xét xuất từ các Câu 4, 5, 6
├── README.md
└── requirements.txt
```

## 3. Bắt đầu nhanh

```bash
# 1. Cài thư viện (Python 3.10 trở lên)
pip install -r requirements.txt

# 2. Đặt 4 file gốc vào data/raw/ rồi chạy notebooks/00_data_cleaning.ipynb
#    (nếu data/cleaned/ đã có sẵn thì bỏ qua bước này)

# 3. Chạy Dashboard tương tác lọc chéo (chạy từ thư mục gốc dự án)
python dashboards/plotly_app/app.py        # mở http://127.0.0.1:8050

# 4. Xuất file thành phẩm report/dashboard.html (5 Tab tổng hợp)
python dashboards/plotly_app/export_html.py
```

Các lệnh Python chạy **từ thư mục gốc** `Ecommerce_analysis/`. Notebook mở và chạy trong thư mục `notebooks/` (đường dẫn trong notebook dùng `../`).

## 4. Notebook

Chạy `00_data_cleaning` trước; các câu còn lại độc lập với nhau, đọc dữ liệu từ `data/cleaned/` và xuất toàn bộ hình ảnh/bảng kết quả vào `report/`:

| Notebook | Nội dung | File xuất vào `report/` |
|---|---|---|
| `00_data_cleaning` | Làm sạch 4 bảng gốc, báo cáo chất lượng | `data/cleaned/*.csv`, `missing_values_bar.png`, `duplicate_records.png`, `numerical_distributions.png`, `outlier_boxplots.png`, `categorical_distributions.png`, `before_after_quality.png` |
| `01_cau_1` | Tổng quan KPI | `kpi_overview.png` |
| `02_cau_2` | Doanh thu theo tháng, tính thời vụ | `monthly_revenue_trend.png`, `monthly_revenue_seasonality.png` |
| `03_cau_3` | Top quốc gia, nhóm hàng theo doanh thu | `top10_country.png`, `top10_category.png`, `heatmap_country_category.png` |
| `04_cau_4` | Churn theo kênh thu hút, kèm kiểm định chi-bình phương | `cau4_churn_by_channel.csv`, `cau4_churn_by_channel.png` |
| `05_cau_5` | Phân phối Frequency và Monetary | `q5_*.csv`, `q5_hist_frequency.png`, `q5_hist_monetary.png`, `q5_hist_monetary_log.png`, `q5_revenue_concentration.png` |
| `06_cau_6` | Ảnh hưởng của Discount | `discount_summary.csv`, `cau6_nhan_xet.txt`, `boxplot_quantity.png`, `boxplot_amount.png` |
| `07_cau_7` | Chi phí và thời gian vận chuyển theo quốc gia | `cau7_shipping_by_country.png` |
| `08_cau_8` | Return rate, rating theo nhóm hàng; Heatmap, Bubble | `cau8_return_rate_rating_by_category.png`, `cau8_heatmap_correlation.png`, `cau8_heatmap_return_country_category.png`, `cau8_bubble_category.png` |
| `09_cau_9` | Top 10 khách chi tiêu cao nhất | `cau9_top10_customers.png` |
| `10_cau_10` | Dashboard bán hàng và giữ chân khách hàng | `dashboard_ban_hang.png` |

## 5. Dashboard Plotly & Thành phẩm `report/dashboard.html`

```bash
python dashboards/plotly_app/app.py --port 8050      # chạy ứng dụng web lọc chéo
python dashboards/plotly_app/export_html.py          # xuất thành phẩm tĩnh 5 Tab vào report/dashboard.html
```

- **5 Tab:** Tổng quan, Doanh thu, Khách hàng, Vận hành, Khuyến mãi (bao phủ trọn vẹn Câu 1–10).
- **Khi chạy trực tiếp `app.py`:** hỗ trợ thanh **Bộ lọc chéo** (năm, quốc gia, nhóm hàng, kênh thu hút, hạng thành viên) và bấm trực tiếp vào cột/ô heatmap để lọc toàn bộ biểu đồ theo thời gian thực.
- **Khi mở `report/dashboard.html`:** mở trực tiếp bằng trình duyệt mà không cần chạy Python; giữ nguyên giao diện 5 Tab, bảng kiểm định, hover chi tiết, zoom/pan và thanh trượt chọn khoảng thời gian.

### Design System

Mọi biểu đồ lấy màu, font và quy tắc trình bày từ `src/config.py` và `src/chart_builders.py`:

- Nền trong suốt; bảng màu Navy `#1E293B`, Teal `#0D9488`, Coral `#F43F5E`; chữ phụ slate `#64748B`; lưới chấm `#E2E8F0`.
- Mỗi biểu đồ có tiêu đề kèm subtitle (ngữ cảnh, đơn vị), số rút gọn `K`/`M`, cột bo góc, legend ngang phía trên.

## 6. Quy ước loại đơn hàng

Mỗi câu của nhóm dùng một quy ước khác nhau về trạng thái đơn, nên số liệu giữa các biểu đồ có thể khác nhau. Đây là chủ ý, đã ghi trong `src/config.py`:

| Quy ước | Áp dụng |
|---|---|
| Chỉ đơn `Delivered` | Câu 2 (`monthly_revenue`), Câu 3 |
| Loại `Cancelled` và `Returned` | Câu 5, Câu 10 (doanh thu thuần) |
| Tất cả đơn hàng | Câu 1, 6, 7, 8 |

## 7. Bảng đối chiếu Trực quan hóa dữ liệu (Slide ↔ Code ↔ File trong `report/`)

Bảng dưới đây dùng để ghi chú và đối chiếu từng phần trực quan hóa trên Slide thuyết trình với mã nguồn và thành phẩm trong `report/`:

| Phần / Câu | Nội dung trực quan hóa trên Slide | Notebook bài làm (`notebooks/`) | Code dùng chung & Dashboard (`src/`, `dashboards/`) | File thành phẩm trong `report/` |
|---|---|---|---|---|
| **Làm sạch dữ liệu (EDA)** | Missing values, Duplicate, Phân phối biến số, Boxplot Outlier, Biến phân loại, Chất lượng Trước/Sau | `00_data_cleaning.ipynb` (Cell 9, 12, 17, 22, 24) | *(Chỉ nằm ở Notebook tiền xử lý, không đưa lên Dashboard)* | `missing_values_bar.png`, `duplicate_records.png`, `numerical_distributions.png`, `outlier_boxplots.png`, `categorical_distributions.png`, `before_after_quality.png` |
| **Câu 1** | 5 chỉ số KPI tổng quan | `01_cau_1.ipynb` (Mục 3.1, Cell 12) | `src/chart_builders.py` → `kpi_indicators()` · `app.py` / `dashboard.html` (Tab **Tổng quan**) | `kpi_overview.png` · `dashboard.html` (Tab Tổng quan) |
| **Câu 2** | Xu hướng doanh thu tháng (kèm MA3) & Tính thời vụ (T1–T12) | `02_cau_2.ipynb` (Mục 4.1 Cell 12, Mục 4.2 Cell 16) | `src/chart_builders.py` → `line_monthly_revenue()`, `bar_seasonality()` · `app.py` / `dashboard.html` (Tab **Tổng quan**) | `monthly_revenue_trend.png`, `monthly_revenue_seasonality.png` · `dashboard.html` (Tab Tổng quan) |
| **Câu 3** | Pareto Top 10 quốc gia, Top 10 nhóm hàng & Heatmap tỷ trọng doanh thu | `03_cau_3.ipynb` (Mục 3.2 Cell 9, Mục 4.2 Cell 14, Mục 5 Cell 17) | `src/chart_builders.py` → `pareto_chart()`, `heatmap_matrix()` · `app.py` / `dashboard.html` (Tab **Doanh thu**) | `top10_country.png`, `top10_category.png`, `heatmap_country_category.png` · `dashboard.html` (Tab Doanh thu) |
| **Câu 4** | Tỷ lệ rời bỏ (Churn) theo kênh thu hút & Kiểm định Chi-bình phương | `04_cau_4.ipynb` (Cell 3) | `src/chart_builders.py` → `bar_rate()`, `src/data_processor.py` → `churn_channel_test()` · `app.py` / `dashboard.html` (Tab **Khách hàng**) | `cau4_churn_by_channel.png`, `cau4_churn_by_channel.csv` · `dashboard.html` (Tab Khách hàng) |
| **Câu 5** | Histogram Frequency, Monetary (gốc & log) & Mức độ tập trung doanh thu | `05_cau_5.ipynb` (Mục 6.1 Cell 18, Mục 7 Cell 20) | `src/chart_builders.py` → `histogram_distribution()`, `bar_revenue_concentration()` · `app.py` / `dashboard.html` (Tab **Khách hàng**) | `q5_hist_frequency.png`, `q5_hist_monetary.png`, `q5_hist_monetary_log.png`, `q5_revenue_concentration.png`, `q5_*.csv` · `dashboard.html` (Tab Khách hàng) |
| **Câu 6** | Boxplot Số lượng & Giá trị giao dịch theo 5 nhóm Discount; Kiểm định Spearman & Kruskal–Wallis | `06_cau_6.ipynb` (Mục 7–10, Mục 12 Cell 28) | `src/chart_builders.py` → `box_by_discount_group()` · `app.py` / `dashboard.html` (Tab **Khuyến mãi**) | `boxplot_quantity.png`, `boxplot_amount.png`, `discount_summary.csv`, `cau6_nhan_xet.txt` · `dashboard.html` (Tab Khuyến mãi) |
| **Câu 7** | Trục kép Chi phí & Thời gian vận chuyển theo quốc gia | `07_cau_7.ipynb` (Mục 3, Cell 7) | `src/chart_builders.py` → `dual_axis_shipping()` · `app.py` / `dashboard.html` (Tab **Vận hành**) | `cau7_shipping_by_country.png` · `dashboard.html` (Tab Vận hành) |
| **Câu 8** | Hoàn trả & Rating theo nhóm hàng; Heatmap tương quan biến; Heatmap hoàn trả Quốc gia × Nhóm hàng; Bubble Chart | `08_cau_8.ipynb` (Mục 4 Cell 7, Mục 5 Cell 9) | `src/chart_builders.py` → `bar_category_performance()`, `bubble_category()`, `heatmap_matrix()` · `app.py` / `dashboard.html` (Tab **Vận hành**) *(riêng `cau8_heatmap_correlation.png` chỉ có ở Notebook)* | `cau8_return_rate_rating_by_category.png`, `cau8_heatmap_correlation.png`, `cau8_heatmap_return_country_category.png`, `cau8_bubble_category.png` · `dashboard.html` (Tab Vận hành) |
| **Câu 9** | Top 10 khách hàng chi tiêu cao nhất & Trạng thái rời bỏ | `09_cau_9.ipynb` (Phần 1, Cell 9) | `src/chart_builders.py` → `bar_top_customers()` · `app.py` / `dashboard.html` (Tab **Khách hàng**) | `cau9_top10_customers.png` · `dashboard.html` (Tab Khách hàng) |
| **Câu 10 & Dashboard** | Dashboard bán hàng & giữ chân khách hàng (Churn theo Recency/Số đơn, Doanh thu thuần nhóm hàng + Hệ thống 5 Tab) | `10_cau_10.ipynb` (Phần 2, Cell 12) | `src/chart_builders.py` → `bar_rate()`, `barh_category_revenue()` · Toàn bộ `dashboards/plotly_app/app.py` & `export_html.py` | `dashboard_ban_hang.png` · `dashboard.html` (trọn bộ 5 Tab) |

## 8. Xử lý sự cố

- **`FileNotFoundError ... orders_cleaned.csv`:** chưa có dữ liệu sạch. Chạy `notebooks/00_data_cleaning.ipynb` (cần 4 file trong `data/raw/`).
- **Notebook Câu 6 báo lỗi `tick_labels`:** matplotlib cũ hơn 3.9, chạy `pip install -U matplotlib`.
- **Cổng 8050 đang bận:** chạy `python dashboards/plotly_app/app.py --port 8060`.
