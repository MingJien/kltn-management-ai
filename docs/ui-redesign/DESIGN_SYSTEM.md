# Design System — Academic Precision 2.0

> Tài liệu đặc tả hệ thống thiết kế cho đại cải cách giao diện KLTN.
> Phiên bản: 2.0-draft · Ngày: 23/11/2026 · Nhánh: `NV6`

---

## 1. Tầm nhìn thiết kế

### 1.1 Tinh thần

**"Editorial Academic"** — giao diện có cá tính của một ấn phẩm học thuật chuyên nghiệp: rõ ràng, chắc chắn, không trang trí thừa, nhưng có nhịp điệu và bản sắc riêng mà không hệ thống đại trà nào có.

Người dùng khi mở ứng dụng phải cảm nhận:
- **Tin cậy** — dữ liệu rõ ràng, thao tác an toàn, trạng thái luôn hiện.
- **Trật tự** — mỗi trang có thứ bậc rõ, biết ngay đâu là việc cần làm.
- **Tinh tế** — khoảng trắng, nhịp chữ, màu sắc được kiểm soát có hệ thống; không rối mắt, không buồn tẻ.

### 1.2 Điều khác biệt so với các đề tài khác

| Lối mòn đại trà | Academic Precision 2.0 |
|---|---|
| Xanh dương mặc định (`#1976D2`, `#2563EB`) | Teal học thuật (`#176b64` ↔ `#123e3b`), gợi chất liệu giấy và mực in |
| Thẻ số dashboard với biểu tượng tròn to | Welcome-spread editorial chia đôi; widget chữ gọn, action-first |
| Sidebar icon-label-list đều nhau | Sidebar có nhóm ngữ nghĩa, nhãn in hoa kiểu chương sách, active bar bên trái |
| Bảng dữ liệu xám đều | Bảng có nhịp zebra nhẹ, header 12px semibold in hoa, cột số dùng `tabular-nums` |
| Font mặc định hệ thống | Inter (variable) + JetBrains Mono cho mã; `font-feature-settings: "cv11","ss01"` |

### 1.3 Signature nhận diện (5 điểm)

1. **Welcome-spread** — hero editorial chia đôi (copy + panel teal đậm) trên Dashboard, có số liệu và hành động ngay.
2. **Code-chip mono** — mã đề tài, MSSV, mã đợt, phiên bản hiển thị bằng JetBrains Mono nền wash nhạt, border-radius nhỏ. Nhìn là biết "đây là mã hệ thống".
3. **Active-bar sidebar** — thanh dọc 2px teal ở lề trái mục đang chọn; chỉ cần 2px nhưng tạo nhịp điểm nhấn khi lướt.
4. **Page header + divider** — mỗi trang mở đầu bằng tiêu đề lớn `font-size: 25px; letter-spacing: -.04em` với đường kẻ dưới 1px; tạo nhịp "chương mới".
5. **Badge trạng thái ngữ nghĩa** — badge nhỏ gọn (5px radius, 11px semibold) với 7 cặp màu ngữ nghĩa cố định cho toàn hệ thống; không lẫn trạng thái nào.

---

## 2. Bảng màu — Semantic Token Layer

Mục tiêu: **một lớp token duy nhất**, mọi CSS chỉ dùng `var(--…)`, không bao giờ dùng mã hex trực tiếp.

### 2.1 Màu nền tảng (Foundation)

| Token | Giá trị | Mục đích |
|---|---|---|
| `--color-canvas` | `#f3f6f5` | Nền toàn ứng dụng |
| `--color-surface` | `#ffffff` | Card, dialog, bảng, input |
| `--color-surface-raised` | `#fbfcfb` | Sidebar, card header, tooltip |
| `--color-surface-sunken` | `#f0f4f2` | Empty state, placeholder, well |
| `--color-border` | `#dfe8e5` | Viền card, bảng, divider |
| `--color-border-strong` | `#c5d4cf` | Input focus ring, active border |
| `--color-border-muted` | `#eaf0ed` | Viền phụ, separator nhẹ |

### 2.2 Màu chữ (Ink)

| Token | Giá trị | Tương phản trên canvas | Tương phản trên surface | Dùng cho |
|---|---|---:|---:|---|
| `--color-ink` | `#162d2b` | 13,37:1 | 14,78:1 | Tiêu đề, nội dung chính |
| `--color-ink-secondary` | `#435752` | 7,50:1 | 8,29:1 | Nhãn form, phụ đề |
| `--color-ink-muted` | `#566965` | 5,36:1 | 5,83:1 | Caption, hint, breadcrumb root |
| `--color-ink-disabled` | `#8da4a0` | 2,64:1 (trên trắng) | — | Placeholder (chỉ kèm viền/label) |

> [!IMPORTANT]
> `--color-ink-muted` đã nâng từ `#637572` (4,47:1) lên `#566965` (5,36:1) để đạt AA trên nền canvas. Mọi chữ có nghĩa phải đạt ≥ 4,5:1 (AA normal) hoặc ≥ 3:1 (AA large text ≥ 18px bold).

### 2.3 Màu chủ đạo (Primary — Teal)

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--color-primary` | `#176b64` | Nút chính, link, active indicator, focus ring |
| `--color-primary-hover` | `#123e3b` | Nút chính hover, link hover |
| `--color-primary-subtle` | `#e8f3f1` | Badge primary bg, active sidebar bg, chip selected |
| `--color-primary-on-primary` | `#ffffff` | Chữ trên nền primary (6,32:1 ✓) |

### 2.4 Màu ngữ nghĩa (Semantic)

| Nhóm | Background | Text | Border | Dùng cho |
|---|---|---|---|---|
| Success | `#f0fdf4` | `#166534` | `#bbf7d0` | Thành công, đã duyệt, đã chốt |
| Warning | `#fffbeb` | `#92400e` | `#fde68a` | Cảnh báo, chờ xử lý, sắp hết hạn |
| Danger | `#fef2f2` | `#991b1b` | `#fecaca` | Lỗi, từ chối, hành động phá hủy |
| Info | `#eff6ff` | `#1e40af` | `#bfdbfe` | Thông tin, hướng dẫn, ghi chú |

### 2.5 Màu nút nguy hiểm

| Token | Giá trị |
|---|---|
| `--color-danger-btn` | `#b42318` |
| `--color-danger-btn-hover` | `#912018` |
| `--color-danger-btn-focus` | `rgba(180,35,24,.28)` |

---

## 3. Typography

### 3.1 Font stack

```css
--font-sans: "Inter", system-ui, -apple-system, sans-serif;
--font-mono: "JetBrains Mono", "Cascadia Code", monospace;
```

Font-feature-settings cho body: `"cv11", "ss01"` (Inter alternates: chữ `a` đơn nét, `l` có chân).

### 3.2 Thang chữ (7 bậc + 1 mono)

| Token | Weight | Size | Line-height | Letter-spacing | Dùng cho |
|---|---:|---:|---:|---|---|
| `--type-display` | 700 | 30px | 1.2 | -0.025em | Hero heading (welcome-spread) |
| `--type-h1` | 700 | 24px | 1.3 | -0.02em | Page header |
| `--type-h2` | 600 | 18px | 1.35 | -0.01em | Section heading, card title |
| `--type-h3` | 600 | 15px | 1.4 | 0 | Subsection, fieldset legend |
| `--type-body` | 400 | 14px | 1.6 | 0 | Nội dung chính, bảng, form |
| `--type-caption` | 500 | 12px | 1.4 | 0 | Nhãn form, timestamp, badge, hint |
| `--type-overline` | 700 | 11px | 1.3 | 0.08em | Nhóm sidebar, kicker, in hoa |
| `--type-mono` | 500 | 12px | 1.4 | 0 | Mã code-chip, số phiên bản |

> [!WARNING]
> Không dùng cỡ chữ dưới 11px cho bất kỳ nội dung nào. Overline 11px chỉ dùng in hoa + letter-spacing rộng. Nội dung đọc tối thiểu 14px. Control (nút, input) tối thiểu 14px; nút nhỏ (`btn-sm`) 13px.

### 3.3 Quy tắc dùng

- **Tiêu đề trang:** `--type-h1`, không kèm mô tả dài hơn 90 ký tự.
- **Nhãn form:** `--type-caption`, `font-weight: 600`, `color: --color-ink-secondary`.
- **Dữ liệu bảng:** `--type-body`, cột số dùng `font-variant-numeric: tabular-nums`.
- **Header bảng:** `--type-caption` + `text-transform: uppercase` + `letter-spacing: 0.04em`.
- **Badge:** `--type-mono` hoặc `--type-caption`, `font-weight: 600`.
- **Mã hệ thống:** `--font-mono`, nền `--color-primary-subtle`, padding 2px 6px, border-radius 4px.

---

## 4. Spacing

### 4.1 Thang khoảng cách (base 4px)

| Token | px | Dùng cho |
|---|---:|---|
| `--space-0` | 0 | — |
| `--space-1` | 4 | Khoảng cách icon-text, padding badge |
| `--space-2` | 8 | Gap nhỏ, margin giữa items |
| `--space-3` | 12 | Padding card compact, gap form row |
| `--space-4` | 16 | Padding input, card body compact |
| `--space-5` | 20 | Gap giữa section, padding card body |
| `--space-6` | 24 | Padding content area, card body rộng |
| `--space-8` | 32 | Margin giữa các nhóm section |
| `--space-10` | 40 | Margin page-header → content |
| `--space-12` | 48 | Margin lớn |
| `--space-16` | 64 | Padding bottom trang |

### 4.2 Quy tắc

- **Giữa nhãn và input:** `--space-1` (4px).
- **Giữa các trường trong form:** `--space-5` (20px).
- **Padding card body:** `--space-5` (20px) đến `--space-6` (24px).
- **Content area padding:** `--space-6` desktop, `--space-4` mobile.
- **Page header margin-bottom:** `--space-6`.

---

## 5. Border radius

| Token | px | Dùng cho |
|---|---:|---|
| `--radius-xs` | 4 | Badge, code-chip, tooltip |
| `--radius-sm` | 6 | Nút, input, select, card compact |
| `--radius-md` | 10 | Card, dialog body |
| `--radius-lg` | 14 | Dialog, welcome-spread |
| `--radius-full` | 9999px | Avatar, pill |

> Không dùng giá trị ngoài thang. Nút và input thống nhất `--radius-sm` (6px).

---

## 6. Shadow

| Token | Giá trị | Dùng cho |
|---|---|---|
| `--shadow-xs` | `0 1px 2px rgba(22,45,43,.04)` | Card mặc định |
| `--shadow-sm` | `0 1px 3px rgba(22,45,43,.06)` | Card hover, dropdown |
| `--shadow-md` | `0 4px 12px rgba(22,45,43,.08)` | Dialog, popover |
| `--shadow-lg` | `0 8px 32px rgba(22,45,43,.12)` | Toast, modal overlay |
| `--shadow-focus` | `0 0 0 3px rgba(23,107,100,.18)` | Focus ring (primary) |
| `--shadow-focus-danger` | `0 0 0 3px rgba(180,35,24,.18)` | Focus ring (danger) |

---

## 7. Responsive breakpoints (chuẩn hóa)

| Token | px | Tên | Dùng cho |
|---|---:|---|---|
| `--bp-sm` | 640 | Mobile | Bảng → thẻ, 1 cột, sidebar ẩn |
| `--bp-md` | 768 | Tablet nhỏ | 2 cột grid, bảng thu gọn |
| `--bp-lg` | 1024 | Desktop | Sidebar hiện, layout đầy đủ |
| `--bp-xl` | 1280 | Desktop rộng | Content max-width cap |

```css
/* Mobile-first conventions */
@media (min-width: 640px) { /* sm and up */ }
@media (min-width: 768px) { /* md and up */ }
@media (min-width: 1024px) { /* lg and up: sidebar visible */ }
@media (min-width: 1280px) { /* xl: max-width content */ }
```

> [!IMPORTANT]
> Chỉ dùng 4 breakpoint trên. Tuyệt đối không thêm breakpoint tùy ý (hiện đang có ~40 breakpoint khác nhau). Dưới 640px bảng chuyển thành danh sách thẻ.

---

## 8. Z-index

| Token | Giá trị | Dùng cho |
|---|---:|---|
| `--z-base` | 0 | Nội dung thường |
| `--z-sticky` | 10 | Header bảng sticky, toolbar |
| `--z-dropdown` | 20 | Select popup, combobox, popover |
| `--z-sidebar` | 30 | Sidebar mobile drawer |
| `--z-overlay` | 40 | Dialog overlay, drawer overlay |
| `--z-modal` | 50 | Dialog content |
| `--z-toast` | 60 | Toast notification |
| `--z-tooltip` | 70 | Tooltip |

---

## 9. Component patterns

### 9.1 Button

| Variant | Dùng khi | Nền | Viền | Chữ |
|---|---|---|---|---|
| `btn-primary` | Hành động chính duy nhất trên trang/dialog | `--color-primary` | transparent | white |
| `btn-secondary` | Hành động phụ, bộ lọc, tải xuống | `--color-surface` | `--color-border` | `--color-ink-secondary` |
| `btn-danger` | Xóa, hủy, thu hồi | `--color-danger-btn` | transparent | white |
| `btn-ghost` | Hành động tinh tế: đóng, bỏ qua | transparent | transparent | `--color-ink-muted` |

Kích thước: `btn-sm` (32px), `btn` (38px), `btn-lg` (44px). Touch target ≥ 44px trên mobile.
Font: 14px 600 cho `btn`; 13px 600 cho `btn-sm`.

### 9.2 Input / Select / Textarea

- Min-height: 40px.
- Font: 14px (nâng từ 13px hiện tại).
- Border: `--color-border`; focus: `--color-primary` + `--shadow-focus`.
- Label: 12px 600 `--color-ink-secondary`, đặt trên input, gap 4px.
- Error state: border `--color-danger-btn` + text lỗi dưới input, `--type-caption`, `color: --danger-text`.

### 9.3 Card

- Border: 1px `--color-border`; radius `--radius-md`.
- Shadow: `--shadow-xs` mặc định, `--shadow-sm` hover (nếu clickable).
- Padding body: `--space-5`.
- Không lồng card.

### 9.4 Table

- Wrapper `.table-scroll`: border 1px `--color-border`, radius `--radius-sm`, `overflow-x: auto`.
- Header: `--type-caption`, uppercase, `--color-ink-muted`, bg `--color-surface-sunken`.
- Row: `--type-body`, bg transparent, hover `--color-surface-sunken`.
- Dưới 640px: bảng chuyển danh sách thẻ (giữ 3 cột quan trọng + badge trạng thái).

### 9.5 Badge

7 cặp ngữ nghĩa cố định:

| Nhóm | Bg | Text | Dùng cho |
|---|---|---|---|
| `badge-active` | `#e8f3f1` | `#14544f` | Đang thực hiện, hoạt động |
| `badge-success` | `#f0fdf4` | `#166534` | Đã duyệt, đã chốt, hoàn thành |
| `badge-warning` | `#fffbeb` | `#92400e` | Chờ duyệt, sắp hết hạn |
| `badge-danger` | `#fef2f2` | `#991b1b` | Từ chối, quá hạn, lỗi |
| `badge-info` | `#eff6ff` | `#1e40af` | Thông tin, mới |
| `badge-neutral` | `#f1f5f9` | `#475569` | Nháp, chưa bắt đầu |
| `badge-muted` | `#f0f4f2` | `#566965` | Đã kết thúc, lưu trữ |

### 9.6 Alert

4 variant: `success`, `warning`, `danger`, `info`. Dùng token semantic ở §2.4. Radius `--radius-sm`. Padding `--space-3 --space-4`.

### 9.7 Dialog (Modal)

- Overlay: `rgba(15,23,42,.4)`, `backdrop-filter: blur(2px)`.
- Body: `--color-surface`, radius `--radius-lg`, shadow `--shadow-md`.
- Size: `sm` (420px), `md` (560px), `lg` (720px).
- Focus trap, Escape đóng, `aria-modal="true"`.

### 9.8 Empty State

- Nền: `--color-surface-sunken`, viền: 1px dashed `--color-border`.
- Icon: Lucide 24px `--color-ink-disabled`.
- Chữ: `--type-body`, `--color-ink-muted`.
- Action: `btn-secondary` hoặc link.

### 9.9 ConfirmDialog (MỚI)

- Kế thừa Dialog `sm`.
- Header có icon cảnh báo + tiêu đề hành động (vd: "Hủy lịch bảo vệ?").
- Body: 1-2 câu mô tả hậu quả.
- Footer: `btn-ghost` "Không, giữ lại" + `btn-danger` "Hủy lịch".
- Nếu cần lý do: input bắt buộc giữa body và footer.

### 9.10 Toast (MỚI)

- Xuất hiện từ trên bên phải, dưới header.
- 4 giây, dừng khi hover; `role="status"`, `aria-live="polite"`.
- Chỉ dùng cho thông báo thành công thoáng qua. Lỗi vẫn hiển thị inline tại form.
- Radius `--radius-sm`, shadow `--shadow-lg`.

### 9.11 Skeleton (MỚI)

- Hình chữ nhật tròn góc, nền `--color-surface-sunken`, animation shimmer (`@keyframes shimmer` gradient di chuyển).
- Tắt animation khi `prefers-reduced-motion: reduce`.
- Chỉ áp dụng cho: dashboard widgets, bảng dữ liệu, danh sách phiên bảo vệ.
- Hiện sau 300ms (tránh flash trên kết nối nhanh).

### 9.12 FilterBar (MỚI)

- Hàng ngang: ô tìm kiếm (mở rộng) + ≤ 3 select/filter + nút "Xóa lọc".
- Chip hiện bên dưới khi có bộ lọc active.
- Responsive: dưới 640px xếp dọc, chip cuộn ngang.

### 9.13 Tabs (chuẩn hóa)

- Dùng `role="tablist"`, `role="tab"`, `aria-selected`.
- Kiểu: underline (đường 2px dưới tab active, màu primary).
- Phân biệt rõ với nhóm nút: tabs không có viền, nút có.

---

## 10. Layout — App Shell

```
┌────────────────────────────────────────────────────┐
│ [Sidebar 256px / 64px collapsed]  [Main area]      │
│ ┌─────────┐ ┌──────────────────────────────────┐   │
│ │ Brand    │ │ [Header 56px: breadcrumb + actions]│  │
│ │ Nav      │ │ [Content padding:24px max:1240px] │  │
│ │ Footer   │ │                                    │  │
│ └─────────┘ └──────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

- **Sidebar:** 256px mở, 64px thu gọn (icon-only), ẩn trên mobile (drawer).
- **Brand:** 88px (giảm từ 148px): logo 32px + 2 dòng chữ.
- **Header:** 56px, sticky top. Breadcrumb ≤ 3 cấp. Actions bên phải: notifications + profile.
- **Content:** padding 24px desktop / 16px mobile. `max-width: 1240px`.
- **Page header:** tiêu đề + mô tả ngắn + action buttons. Divider 1px dưới.

### 10.1 Vùng thao tác (Action zones)

Mỗi trang có tối đa 3 vùng action:
1. **Page-level:** trong PageHeader (nút Tạo mới, Làm mới, Tải xuống).
2. **Section-level:** đầu card hoặc tab panel (nút Lưu, Hủy, Thêm).
3. **Row-level:** cuối dòng bảng hoặc thẻ (icon button hoặc menu 3 chấm).

> Thao tác phá hủy (xóa, hủy, thu hồi) luôn dùng `btn-danger` + `ConfirmDialog`, không bao giờ dùng `window.confirm`.

---

## 11. Icon system

- **Thư viện:** Lucide React, 20px mặc định, 16px trong nút nhỏ, 24px trong empty state.
- **Màu:** `currentColor` (kế thừa từ parent).
- **Quy tắc sidebar:** mỗi mục một icon duy nhất, không trùng lặp.

Đề xuất icon sidebar (thay cho 6× ClipboardList, 5× FileText hiện tại):

| Mục | Icon hiện tại | Icon đề xuất |
|---|---|---|
| Tổng quan | LayoutDashboard | LayoutDashboard ✓ |
| Báo cáo & thống kê | ClipboardList | BarChart3 |
| Lịch sử hoạt động | History | History ✓ |
| Danh sách giảng viên | UsersRound | GraduationCap (nếu ở mục Tra cứu) |
| Chọn / Duyệt đề tài | FileText | Lightbulb |
| Đăng ký | ClipboardList | FilePlus |
| Xin thôi KLTN | FileText | FileX |
| Đổi đề tài & gia hạn | FileText | RefreshCw |
| Khóa luận & GVHD | GraduationCap | BookOpen |
| Hồ sơ nộp & xét duyệt | FolderOpen | FolderCheck |
| Báo cáo tiến độ | ClipboardList | TrendingUp |
| Phản biện & điều kiện | ClipboardList | FileSearch |
| Hội đồng và bảo vệ | CalendarDays | Shield |
| Tra cứu AI | Bot | Bot ✓ |
| Kho khóa luận | BookOpen | Archive |
| Kho biểu mẫu | FolderOpen | FileStack |
| Tài khoản quản trị | UsersRound | UsersRound ✓ |
| Phân công & chức vụ | ClipboardList | UserCog |
| Đợt KLTN | CalendarDays | CalendarRange |
| Danh sách SV | ShieldCheck | ListChecks |
| Thông tin của tôi | UserRound | UserRound ✓ |

---

## 12. Motion & Animation

### 12.1 Nguyên tắc

- Chỉ dùng animation cho **phản hồi trạng thái**, không trang trí.
- Tắt hoàn toàn khi `prefers-reduced-motion: reduce`.
- Transition mặc định: `150ms ease` cho hover/active; `200ms ease` cho dialog/dropdown mở/đóng.

### 12.2 Hiệu ứng cho phép

| Hiệu ứng | Duration | Easing | Dùng cho |
|---|---|---|---|
| Hover bg/color | 150ms | ease | Nút, link, hàng bảng |
| Dialog open | 200ms | ease-out | Fade in + translateY(-8px → 0) |
| Dialog close | 150ms | ease-in | Fade out |
| Toast enter | 300ms | ease-out | Slide in từ phải |
| Toast exit | 200ms | ease-in | Fade out |
| Skeleton shimmer | 1.5s | linear | Gradient di chuyển (loop) |
| Sidebar collapse | 200ms | ease | Width transition |
| Spinner (loading) | 600ms | linear | Rotate 360° (loop) |

---

## 13. Accessibility

### 13.1 Tiêu chuẩn

- WCAG 2.1 AA cho toàn bộ nội dung.
- Tương phản chữ ≥ 4,5:1 (normal text), ≥ 3:1 (large text ≥ 18px bold hoặc ≥ 24px).
- Tương phản UI component ≥ 3:1 (viền input, icon hành động).

### 13.2 Checklist

- [x] Skip link (`Đến nội dung chính`) — đã có.
- [x] Focus trap trong Dialog — đã có.
- [x] `aria-label` trên navigation — đã có.
- [x] `role="alert"` cho thông báo lỗi — đã có.
- [ ] `role="tablist"` + `role="tab"` + `aria-selected` cho tabs — **cần bổ sung**.
- [ ] `aria-busy` trên vùng đang tải — **cần bổ sung**.
- [ ] `aria-live="polite"` trên toast — **cần bổ sung**.
- [ ] `font-size` ≥ 11px cho mọi nội dung — **cần sửa chữ 9px**.
- [ ] Touch target ≥ 44×44px trên mobile — kiểm tra lại.
- [ ] Keyboard navigation cho dropdown/combobox — **cần bổ sung**.

---

## 14. Quy tắc áp dụng (cho đội triển khai)

1. **Không hex trực tiếp** — tất cả màu qua token. Linting rule: `no-literal-color`.
2. **Không inline style** — trừ giá trị tính toán động (vd: vị trí tooltip).
3. **Không `!important`** — sửa specificity bằng cách đặt đúng lớp selector.
4. **Không breakpoint tùy ý** — chỉ 4 breakpoint chuẩn.
5. **Không cỡ chữ ngoài thang** — 7 bậc + 1 mono.
6. **Không border-radius ngoài thang** — 5 giá trị.
7. **CSS theo trang phải có prefix phạm vi** — `.defense-page .defense-…`.
8. **Mỗi lần thêm component mới** — cập nhật tài liệu này trước khi code.
