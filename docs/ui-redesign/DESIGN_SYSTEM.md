# Design System — DThU Academic Blue V3 (Fresh Campus Identity)

> Tài liệu đặc tả hệ thống thiết kế chính thức cho đợt cải cách toàn diện giao diện Hệ thống Quản lý Khóa luận Tốt nghiệp tích hợp Chatbot AI — **Khoa Công nghệ và Kỹ thuật, Trường Đại học Đồng Tháp (DThU)**.  
> **Phiên bản:** `v3.1` (`DThU Academic Blue V3 — Fresh Campus Identity`) · **Ngày cập nhật:** `25/11/2026` · **Nhánh:** `NV6`

---

## 1. Kiến trúc 3 lớp thống nhất & Định hướng thị giác V3

Bản V3 nâng cấp triệt để định hướng màu sắc và bố cục từ V2 (giảm xám đục, mở rộng nhịp thở không gian làm việc, tăng độ sắc nét của thanh điều hướng và tinh gọn luồng thao tác):

1. **Brand Identity (DThU Academic Blue V3 — Fresh Campus Identity):**
   - **Navigation sâu có chiều sâu:** Thanh điều hướng xanh đậm `#143B59` chuyển sắc mềm xuống `#246B96` ở vùng chân (`#10334E` cho footer người dùng), chữ phụ `#D6E6F3`, mục đang chọn `#E3F1FA` với chữ `#174A6D` và vạch nhấn vàng `#D7A348`.
   - **Canvas & Bề mặt sáng trung tính:** Nền trang gần trắng `#F7FAFC`, card và vùng làm việc `#FFFFFF`, vùng nhấn phụ/nổi `#FAFCFE`, vùng trũng `#F1F5F9`, vùng highlight `#EAF4FB`, đường viền `#DFE7EE` và đường chia đậm `#CFDCE6`.
   - **Sắc xanh hành động tươi (`#1976B8`):** Rõ điểm nhấn tương tác trên nền trắng trung tính (`hover #135F93`, `pressed #104D78`, nút phụ `#EAF4FB` / `#174A6D`).
   - **Bản sắc khuôn viên DThU:** Bộ minh họa SVG kiến trúc giảng đường hai tầng, cánh sen Đồng Tháp nở nhiều lớp và dòng chảy Mekong điểm vàng học thuật `#D7A348` trong [`CampusArtwork.tsx`](file:///d:/KLTN/frontend/src/components/ui/CampusArtwork.tsx).
2. **Component & UX Standards (DThU UI Kit + Lovable UX Patterns):**
   - Chuẩn hóa phân cấp nút bấm, badge, card, tabs, `FilterBar`, `FileDropzone`, `Dialog` (`modal` + `drawer` trượt phải `600px` trên desktop / full-screen sheet trên mobile) và mật độ thông tin trong hệ stylesheet CSS thuần của dự án (xem chi tiết tại [`DTHU_KIT_MAPPING.md`](file:///d:/KLTN/docs/ui-redesign/DTHU_KIT_MAPPING.md)).
3. **KLTN Domain Components (Nghiệp vụ chuyên biệt):**
   - [`Timeline.tsx`](file:///d:/KLTN/frontend/src/components/ui/Timeline.tsx) (`ThesisJourney` 5 chặng + `ActivityTimeline`), [`ThesisStatusBadge.tsx`](file:///d:/KLTN/frontend/src/components/domain/ThesisStatusBadge.tsx), [`WorkflowSteps.tsx`](file:///d:/KLTN/frontend/src/components/domain/WorkflowSteps.tsx), [`TopicsPage.tsx`](file:///d:/KLTN/frontend/src/pages/TopicsPage.tsx) (Card/List view + Side Drawer chi tiết đề tài), [`WorkspacePage.tsx`](file:///d:/KLTN/frontend/src/pages/WorkspacePage.tsx) & [`ThesisViewPage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisViewPage.tsx).

---

## 2. Hệ thống Design Tokens V3 ([`tokens.css`](file:///d:/KLTN/frontend/src/styles/tokens.css))

Toàn bộ `23` tệp CSS trong `frontend/src/styles/` dùng token từ `:root` trong [`tokens.css`](file:///d:/KLTN/frontend/src/styles/tokens.css); rà soát tĩnh ghi nhận `0` mã hex cũ thời V1/V2/teal còn sót lại.

### 2.1 Navigation (Sidebar V3)

| Token | Giá trị | Vai trò |
|---|---|---|
| `--sidebar-bg` | `#143B59` | Nền chính thanh điều hướng bên |
| `--sidebar-gradient-end` | `#246B96` | Điểm chuyển sắc phần chân thanh điều hướng |
| `--sidebar-footer-bg` | `#10334E` | Nền vùng thông tin tài khoản ở đáy sidebar |
| `--sidebar-text` | `#FFFFFF` | Chữ và icon điều hướng chính |
| `--sidebar-text-secondary` | `#D6E6F3` | Nhãn phụ, tên khoa và tiêu đề nhóm |
| `--sidebar-active-bg` | `#E3F1FA` | Nền mục điều hướng đang chọn |
| `--sidebar-active-text` | `#174A6D` | Chữ & icon mục đang chọn |
| `--sidebar-hover-bg` | `rgba(255, 255, 255, 0.09)` | Nền hover trên nền xanh đậm |
| `--sidebar-border` | `rgba(214, 230, 243, 0.14)` | Đường phân cách trong sidebar |

### 2.2 Action & Interactive Variants

| Token | Giá trị | Vai trò |
|---|---|---|
| `--color-primary` | `#1976B8` | Nút chính, tab đang chọn, liên kết, focus ring |
| `--color-primary-hover` | `#135F93` | Hover nút chính & tiêu điểm nhấn |
| `--color-primary-active` | `#104D78` | Trạng thái nhấn (`:active`) |
| `--color-secondary-action-text` | `#174A6D` | Chữ nút phụ/soft và nhãn học thuật nổi bật |
| `--color-primary-subtle` | `#EAF4FB` | Nền hành động phụ (`btn-soft`), pill nhấn, highlight |
| `--color-primary-wash` | `#F2F8FD` | Nền dải chuyển nhẹ trong Hero Banner & giai đoạn hiện tại |
| `--primary-50` .. `--primary-900` | `#F2F8FD` .. `#10334E` | Thang sắc độ 10 bậc V3 |

### 2.3 Background, Surface & Borders

| Token | Giá trị | Vai trò |
|---|---|---|
| `--color-canvas` | `#F7FAFC` | Nền trang tổng thể sáng sạch gần trắng |
| `--color-surface` | `#FFFFFF` | Bề mặt card, bảng dữ liệu, Side Drawer, dialog, ô nhập |
| `--color-surface-raised` | `#FAFCFE` | Hover hàng bảng & card phụ nhẹ |
| `--color-surface-sunken` | `#F1F5F9` | Đầu bảng, chip yêu cầu, segmented control, trạng thái rỗng |
| `--color-surface-highlight` | `#EAF4FB` | Panel nhấn có ý nghĩa học vụ & banner ngữ cảnh |
| `--color-border` | `#DFE7EE` | Đường viền card, khung nhập, drawer |
| `--color-border-strong` | `#CFDCE6` | Đường chia mạnh & viền hover/select |
| `--color-border-muted` | `#EDF2F7` | Đường chia ngang bên trong danh sách & bảng |

### 2.4 Typography (Ink Scale)

| Token | Giá trị | Ghi chú WCAG 2.2 AA |
|---|---|---|
| `--color-ink` | `#182F43` | Chữ chính (`13.76:1` trên `#FFFFFF`) |
| `--color-ink-secondary` | `#526B80` | Chữ phụ, nhãn metadata (`5.57:1` trên `#FFFFFF`) |
| `--color-ink-muted` | `#566E80` | Token chữ mờ được tinh chỉnh nhẹ từ `#647B8D` để đạt `5.33:1` trên `#FFFFFF` và `4.87:1` trên `#F1F5F9` (tránh lỗi nhỏ `< 4.5:1` khi `axe-core` kiểm chữ 12px) |
| `--neutral-400` | `#647B8D` | Giá trị tham chiếu V3 gốc — chỉ giữ cho viền/icon phi văn bản |

### 2.5 Accent & Semantic Colors

| Nhóm | Nền (`-bg`) | Chữ (`-text`) | Biến phụ |
|---|---|---|---|
| **Academic Gold** | `--color-accent-gold-subtle: #FFF7E8` | Ornament / Border (`#D7A348`) | `--color-accent-gold-border: #EDD39C` |
| **Success** | `--success-bg: #EAF5EE` | `--success-text: #166534` | `--success-border: #B7DFC5`, `--success-solid: #258552` |
| **Info** | `--info-bg: #EAF4FB` | `--info-text: #185B80` | `--info-border: #BFE0F5` |
| **Warning** | `--warning-bg: #FFF7E8` | `--warning-text: #92400E` | `--warning-border: #F5DCAB` |
| **Danger** | `--danger-bg: #FDECEC` | `--danger-text: #991B1B` | `--danger-border: #F5C2C2`, `--color-danger-btn: #B42318` |
| **Neutral** | `--neutral-badge-bg: #F1F5F9` | `--neutral-badge-text: #475569` | `--neutral-badge-border: #CBD5E1` |

---

## 3. Bảng kiểm chứng độ tương phản WCAG 2.2 AA (Đo trực tiếp)

| Cặp màu (Chữ trên Nền) | Tỷ lệ đo được | Chuẩn |
|---|---:|---|
| `#182F43` trên `#FFFFFF` / `#F7FAFC` | **13.76:1** / **13.12:1** | WCAG AAA |
| `#526B80` trên `#FFFFFF` / `#F7FAFC` | **5.57:1** / **5.31:1** | WCAG AA |
| `#566E80` trên `#FFFFFF` / `#F1F5F9` | **5.33:1** / **4.87:1** | WCAG AA |
| `#FFFFFF` trên `#1976B8` / `#135F93` / `#104D78` | **4.86:1** / **6.81:1** / **8.92:1** | WCAG AA → AAA |
| `#174A6D` trên `#EAF4FB` / `#E3F1FA` | **8.42:1** / **8.15:1** | WCAG AAA |
| `#FFFFFF` trên `#143B59` / `#10334E` | **11.67:1** / **13.08:1** | WCAG AAA |
| `#D6E6F3` trên `#143B59` / `#246B96` | **9.15:1** / **4.55:1** | WCAG AAA / AA |
| `#166534` trên `#EAF5EE` · `#FFFFFF` trên `#258552` | **6.38:1** · **4.61:1** | WCAG AA |
| `#185B80` trên `#EAF4FB` | **6.61:1** | WCAG AA |
| `#92400E` trên `#FFF7E8` | **6.66:1** | WCAG AA |
| `#991B1B` trên `#FDECEC` · `#FFFFFF` trên `#B42318` | **7.28:1** · **6.57:1** | WCAG AAA / AA |
| `#475569` trên `#F1F5F9` | **6.92:1** | WCAG AA |
| `#D7A348` trên `#FFFFFF` | **2.28:1** | Khóa riêng cho ornament / đường viền vàng, tuyệt đối không làm màu chữ |

---

## 4. Layout, Container Widths, Side Drawer & Đồ họa V3

### 4.1 Thang chữ & Container Widths mở rộng
- Font chuẩn `--font-sans: "Inter"`, `--font-mono: "JetBrains Mono"` (`tabular-nums`); cỡ chữ tối thiểu toàn hệ thống là **11px** (`0` quy tắc CSS dưới `11px`).
- Mở rộng độ rộng vùng làm việc để tận dụng màn hình `1440px` thay vì bó hẹp ở giữa:
  - `.app-shell__content > *`: `max-width: 1400px` ([`layout.css`](file:///d:/KLTN/frontend/src/styles/layout.css), [`signature.css`](file:///d:/KLTN/frontend/src/styles/signature.css))
  - `.admin-page`, `.roster-page`: `max-width: 1440px` ([`admin.css`](file:///d:/KLTN/frontend/src/styles/admin.css), [`roster.css`](file:///d:/KLTN/frontend/src/styles/roster.css))
  - `.withdrawal-page`: `max-width: 1320px` ([`withdrawals.css`](file:///d:/KLTN/frontend/src/styles/withdrawals.css))
  - `.notification-history`: `max-width: 1200px` ([`components.css`](file:///d:/KLTN/frontend/src/styles/components.css))
  - `.registration-card`: `max-width: 100%` ([`content-polish.css`](file:///d:/KLTN/frontend/src/styles/content-polish.css))

### 4.2 Side Drawer chi tiết Đề tài (`Dialog` `variant="drawer"`)
- [`Dialog.tsx`](file:///d:/KLTN/frontend/src/components/ui/Dialog.tsx) hỗ trợ `variant?: "modal" | "drawer"` và `headerMeta?: ReactNode`, dùng chung `dialogStack`, bẫy Tab, đóng bằng `Escape` hoặc bấm overlay ngoài, và trả focus về nút kích hoạt sau khi đóng.
- Desktop: trượt từ cạnh phải rộng `600px` (`width: min(600px, 100vw); border-radius: 0`), tiêu đề + metadata dính trên (`headerMeta`), nút đóng `36×36px` viền rõ (`aria-label="Đóng"` duy nhất trong drawer), thanh `WorkflowSteps` 3 chặng gọn trên 1 hàng, lưới `<dl className="topic-drawer-meta">` 2 cột, danh sách sinh viên đã đăng ký chia hàng gọn `.topic-drawer-students` (tránh tràn bảng 5 cột), và thanh thao tác dính dưới đáy (`Duyệt đề tài`, `Trả lại để sửa`, `Từ chối đề tài`, `Gửi bộ môn duyệt`, `Đăng ký` / `Tham gia`).
- Mobile (`≤ 639px`): biến thành full-screen sheet (`width: 100%; height: 100dvh;`), nút đóng `44×44px` đạt chuẩn chạm.
- Hiệu ứng mở `.dialog--drawer` dịch ngang `translateX(24px) → 0` với `opacity: 1` cố định ngay từ khung hình đầu để vừa mượt thị giác vừa không làm sai lệch kiểm tra tương phản tức thời.

### 4.3 Đồ họa bản sắc DThU V3 ([`CampusArtwork.tsx`](file:///d:/KLTN/frontend/src/components/ui/CampusArtwork.tsx))
- **`CampusBannerArt`**: Minh họa kiến trúc giảng đường 2 tầng + hoa sen Đồng Tháp nở nhiều lớp + quỹ đạo sông Mekong điểm vàng `#D7A348` cho Hero Banner ở [`WorkspacePage.tsx`](file:///d:/KLTN/frontend/src/pages/WorkspacePage.tsx) và [`ThesisViewPage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisViewPage.tsx).
- **`SidebarLotusArt` trong `.sidebar__art-dock` ([`Sidebar.tsx`](file:///d:/KLTN/frontend/src/components/layout/Sidebar.tsx))**: Gắn cố định ngay phía trên `.sidebar__footer` (trên dải gradient `#246B96`, `pointer-events: none`, hiển thị ở viewport cao `≥ 740px` khi không thu gọn), đảm bảo luôn hiện diện đẹp và không chìm dưới vùng cuộn nav hay che chữ menu.
- **`LoginCampusArt` & `AiKnowledgeArt`**: Trang trí phân hệ đăng nhập xanh đậm `#10334E → #143B59 → #246B96` ([`login.css`](file:///d:/KLTN/frontend/src/styles/login.css)) và trang Tra cứu AI (`/ai`).
