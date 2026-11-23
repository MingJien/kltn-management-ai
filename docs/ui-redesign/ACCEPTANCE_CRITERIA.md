# Acceptance Criteria — Academic Precision 2.0

> Tiêu chí nghiệm thu cho đại cải cách giao diện KLTN.
> Mỗi tiêu chí phải có **bằng chứng kiểm chứng được** (đo tự động, ảnh chụp, hoặc checklist thủ công).
> Chỉ chấm 9,5+/10 khi **tất cả tiêu chí P0 và P1 đạt**, và ≥ 90% tiêu chí P2 đạt.

---

## 1. Tiêu chí hệ thống

### 1.1 Design token coverage (P0)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| T-01 | Mã hex trực tiếp trong CSS (trừ `tokens.css`) | `grep -c '#[0-9a-fA-F]' styles/*.css` (trừ tokens) | **0** |
| T-02 | Giá trị `border-radius` ngoài thang 5 bậc | Script quét | **0** |
| T-03 | Giá trị `font-size` ngoài thang 7 bậc + mono | Script quét | **0** |
| T-04 | Giá trị `font-weight` ngoài 400/500/600/700 | Script quét | **0** |
| T-05 | Giá trị `z-index` ngoài thang 8 bậc | Script quét | **0** |
| T-06 | Breakpoint ngoài 4 chuẩn (640, 768, 1024, 1280) + `prefers-reduced-motion` + `print` | Script quét | **0** |
| T-07 | `!important` trong CSS | `grep -c '!important' styles/*.css` | **0** |

### 1.2 Consistency (P0)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| C-01 | Tên trang thống nhất (sidebar = breadcrumb = page header = document.title) | Playwright chụp 4 vị trí cho mọi route, so sánh label | **100% khớp** |
| C-02 | Icon sidebar không trùng lặp | Kiểm tra `routes.ts` | Mỗi mục 1 icon khác biệt |
| C-03 | Thao tác phá hủy dùng `ConfirmDialog` | `grep -c 'window.confirm\|window.alert' *.tsx` | **0** |
| C-04 | CSS theo trang có prefix phạm vi | Review thủ công | 100% |
| C-05 | Badge trạng thái dùng đúng 7 cặp ngữ nghĩa | Review toàn bộ `ThesisStatusBadge` + badge custom | 100% |

### 1.3 Build health (P0)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| B-01 | TypeScript error | `npx tsc --noEmit` | **0 error** |
| B-02 | Build success | `npm run build` | Exit code 0 |
| B-03 | Chunk chính | Build output | **< 500 kB** (hiện 725 kB) |
| B-04 | Inline `style={{}}` | `grep -c 'style={{' *.tsx` | **≤ 10** (hiện 94; giữ lại cho vị trí tính toán động) |

---

## 2. Tiêu chí typography & readability (P1)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| R-01 | Cỡ chữ nhỏ nhất hiển thị | Quét CSS: `font-size` min | **≥ 11px** (chỉ cho overline in hoa) |
| R-02 | Nội dung đọc (body, bảng, form) | Quét CSS | **≥ 14px** |
| R-03 | Control (nút, input) | Quét CSS | **≥ 14px** (13px cho `btn-sm`) |
| R-04 | Mô tả PageHeader | Đo chiều dài chuỗi | **≤ 90 ký tự** mọi trang |
| R-05 | Dòng JSX > 300 ký tự | Script đếm | **≤ 50** (hiện 240) |

---

## 3. Tiêu chí tương phản & màu sắc (P1)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| X-01 | Chữ thường trên nền | Tính tỷ lệ WCAG từ token | **≥ 4,5:1** (AA) |
| X-02 | Chữ lớn (≥ 18px bold) trên nền | Tính tỷ lệ WCAG | **≥ 3:1** |
| X-03 | UI component (viền input, icon hành động) | Tính tỷ lệ WCAG | **≥ 3:1** |
| X-04 | Nút primary chữ trắng trên teal | `#ffffff` trên `#176b64` | **6,32:1 ✓** |
| X-05 | Nút danger chữ trắng trên đỏ | `#ffffff` trên `#b42318` | **6,57:1 ✓** |
| X-06 | Chữ muted trên canvas | `#566965` trên `#f3f6f5` | **5,36:1 ✓** |

---

## 4. Tiêu chí accessibility (P1)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| A-01 | axe-core violations | Chạy axe trên mọi route | **0 critical, 0 serious** |
| A-02 | Skip link hoạt động | Tab vào trang, nhấn Enter | Nhảy đến `#main-content` |
| A-03 | Focus trap trong Dialog | Mở dialog, Tab liên tục | Focus quay vòng trong dialog |
| A-04 | Tabs có ARIA | Kiểm tra DOM | `role="tablist"`, `role="tab"`, `aria-selected` |
| A-05 | Toast có `role="status"` | Kiểm tra DOM | Có |
| A-06 | Keyboard navigation cho filter, combobox | Thao tác bàn phím | Mở/chọn/đóng bằng phím |
| A-07 | Touch target | Đo kích thước nút/link trên mobile | **≥ 44 × 44 px** |

---

## 5. Tiêu chí responsive (P1)

| # | Tiêu chí | Viewport | Cách đo | Ngưỡng đạt |
|---|---|---|---|---|
| V-01 | Không overflow ngang | 375px | Playwright scroll check | **Không** có thanh cuộn ngang trên `<body>` |
| V-02 | Bảng chuyển card | 375px | Ảnh chụp | Bảng lớn hiển thị dạng thẻ |
| V-03 | Sidebar drawer | < 1024px | Click hamburger | Sidebar hiện/ẩn, overlay che content |
| V-04 | Content padding mobile | 375px | Ảnh chụp | 16px hai bên |
| V-05 | Dialog full-width mobile | 375px | Ảnh chụp | Dialog `sm` chiếm ≥ 90% màn |
| V-06 | Defense page usable | 375px | Thao tác thử | Tabs cuộn, form field full-width |

---

## 6. Tiêu chí UX luồng nghiệp vụ (P1)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| U-01 | Lập hội đồng: select GV có tìm kiếm | Thao tác thử | Gõ tên → lọc, option 2 dòng |
| U-02 | Chốt kết quả: blocker rõ ràng | Thao tác thử | Hiện checklist blocker, nút disable + tooltip lý do |
| U-03 | Mẫu 9: vai trò khác thấy giải thích | Kiểm tra giao diện khi role ≠ SECRETARY | Ô tài liệu khóa có chú thích |
| U-04 | Thao tác phá hủy: hậu quả rõ | ConfirmDialog | Tiêu đề + mô tả hậu quả + nút nguy hiểm |
| U-05 | Trạng thái loading: giữ layout | Skeleton / spinner | Không nhảy layout khi dữ liệu tải |
| U-06 | Trạng thái rỗng: có hướng dẫn | EmptyState | Có icon + mô tả + action |
| U-07 | Lọc/tìm kiếm: thấy bộ lọc active | FilterBar | Chip hiện, nút "Xóa lọc" |
| U-08 | Dashboard: biết việc tiếp theo | "Next action" card | Hiện cho đúng vai trò |

---

## 7. Tiêu chí performance (P2)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| F-01 | LCP (Largest Contentful Paint) | Lighthouse trên localhost | **< 2,5s** |
| F-02 | CLS (Cumulative Layout Shift) | Lighthouse | **< 0,1** |
| F-03 | Total Blocking Time | Lighthouse | **< 300ms** |
| F-04 | CSS total lines | `wc -l styles/*.css` | **< 5.500** (hiện 6.176, giảm sau codemod + hợp nhất) |

---

## 8. Tiêu chí visual polish (P2)

| # | Tiêu chí | Cách đo | Ngưỡng đạt |
|---|---|---|---|
| W-01 | Welcome-spread giữ nguyên bản sắc | Ảnh chụp | Có, với token mới |
| W-02 | Code-chip mono nhất quán | Quét class `code-chip` / `topic-code` | Tất cả dùng `--font-mono`, nền `--color-primary-subtle` |
| W-03 | Active-bar sidebar 2px teal | Ảnh chụp | Có |
| W-04 | Page header divider 1px | Ảnh chụp | Có, mọi trang |
| W-05 | Badge nhất quán | Review toàn bộ | 7 cặp cố định, không có badge tùy ý |
| W-06 | Không có tệp CSS chết | Kiểm tra import | Mọi tệp CSS đều được import |
| W-07 | Tệp `style.css` đã xóa | `ls src/style.css` | Không tồn tại |

---

## 9. Quy trình nghiệm thu

### Bước 1: Automated checks
Chạy script `tools/acceptance_check.py` (tạo kèm trong Phase E) để kiểm tra T-01 → T-07, B-01 → B-04, R-01 → R-05.

### Bước 2: Playwright screenshots
Chạy Playwright trên 4 viewport cho mọi route. So sánh với ảnh BEFORE. Lưu vào `docs/evidence/screenshots/`.

### Bước 3: axe-core
Chạy axe-core cho mọi route. Lưu kết quả JSON vào `docs/evidence/axe-results/`.

### Bước 4: Lighthouse
Chạy Lighthouse cho 5 route chính (Dashboard, Defense, Topics, Administration, Login). Lưu báo cáo HTML.

### Bước 5: Manual review
Duyệt 15 trang chính theo checklist U-01 → U-08 và W-01 → W-07.

### Bước 6: Chấm điểm

Tính điểm tổng hợp:

| Nhóm | Trọng số | Tiêu chí |
|---|---:|---|
| Token & consistency | 20% | T-01→07, C-01→05 |
| Typography & readability | 10% | R-01→05 |
| Contrast & color | 10% | X-01→06 |
| Accessibility | 15% | A-01→07 |
| Responsive | 10% | V-01→06 |
| UX luồng nghiệp vụ | 20% | U-01→08 |
| Performance | 5% | F-01→04 |
| Visual polish | 5% | W-01→07 |
| Build health | 5% | B-01→04 |

**Quy đổi:** Mỗi tiêu chí đạt = 10/10 cho tiêu chí đó. Tổng có trọng số phải **≥ 9,5** để đạt mục tiêu.

> [!IMPORTANT]
> Điểm do script và bằng chứng quyết định, không tự đánh giá cảm tính. Nếu bất kỳ tiêu chí P0 nào chưa đạt, tổng bị cap tại 7,0 bất kể các tiêu chí khác.
