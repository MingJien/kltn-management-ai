# UI/UX Audit — Hệ thống quản lý KLTN

> Phạm vi: toàn bộ frontend `frontend/src` trên nhánh `NV6` (sau commit `7d9e938`).
> Ngày kiểm toán: 22/11/2026. Giai đoạn: **Phase 1 — kiểm toán và lập kế hoạch**, chưa triển khai đại cải cách.

## 0. Phương pháp và giới hạn bằng chứng

| Nguồn bằng chứng | Đã dùng | Ghi chú |
|---|---|---|
| Đọc mã nguồn TSX/CSS | Có | `App.tsx`, toàn bộ layout shell, `DefensePage.tsx` (510 dòng), các trang chính, toàn bộ CSS |
| Đo định lượng bằng script | Có | Đếm màu hex, cỡ chữ, radius, breakpoint, z-index, `window.confirm`, `<details>`, inline style… trên 96 tệp TSX và 24 tệp CSS |
| Build và type check | Có | `npx tsc --noEmit` thoát 0; `npm run build` thành công (cảnh báo chunk > 500 kB) |
| Kết quả Playwright cũ (`local/*.json`) | Có, tham khảo | Dữ liệu của lượt kiểm thử trước, chưa chạy lại trong phiên này |
| Duyệt ứng dụng thật bằng trình duyệt | **Chưa** | Backend/PostgreSQL không truy cập được từ sandbox trong phiên này. Mọi nhận định về hiển thị thực tế phải xác nhận lại bằng ảnh chụp ở Phase 2 |
| DThU UI Kit | **Chưa kiểm chứng trực tiếp** | Chỉ có thông tin tìm kiếm web (React 19, Tailwind v4, Radix, màu chủ `#00568c`). Chưa xác minh giấy phép và chất lượng từng component |

> [!IMPORTANT]
> Các điểm 8.5–9.5/10 do AI trước tự chấm **không được dùng làm cơ sở**. Điểm hiện trạng ở mục 6 chấm lại theo thang tiêu chí có bằng chứng.

## 1. Kiến trúc giao diện hiện tại

- **Stack:** React + TypeScript + Vite, React Router, Lucide icons, CSS thuần (không Tailwind, không thư viện component).
- **CSS:** 24 tệp trong `styles/` (6.176 dòng). 12 tệp nạp toàn cục trong [main.tsx](file:///d:/KLTN/frontend/src/main.tsx); 10 tệp nạp theo trang lazy. Vite gộp CSS thành toàn cục sau khi tải nên **thứ tự cascade phụ thuộc vào lịch sử điều hướng** của người dùng. `defense.css` được 3 trang nạp; `review-workspace.css` được 4 nơi nạp.
- **Lớp theme kép:** [tokens.css](file:///d:/KLTN/frontend/src/styles/tokens.css) định nghĩa thang Slate + Teal kiểu Tailwind (`--primary-700: #0f766e`). [signature.css](file:///d:/KLTN/frontend/src/styles/signature.css) định nghĩa bảng màu thứ hai (`--signature-teal: #176b64`, `--signature-deep: #123e3b`) và ghi đè lại component. Hiện có hai màu teal chủ đạo cùng tồn tại.
- **Tệp chết:** `frontend/src/style.css` (2 dòng minified, 49 mã hex, font Segoe UI, màu xanh `#125f83`) không được import ở đâu.
- **Component dùng chung:** `PageHeader`, `EmptyState`, `Dialog`, `PasswordField`, `ThesisStatusBadge`, `WorkflowSteps`, `VersionTimeline`. Chưa có primitive cho Tabs, ConfirmDialog, Toast, Skeleton, FilterBar, DataTable, Field.

### 1.1 Danh mục route theo vai trò (từ `App.tsx` + `Sidebar.tsx`)

| Nhóm | Route | Điều kiện truy cập |
|---|---|---|
| Chung | `/`, `/account`, `/notifications`, `/activity`, `/forms`, `/lecturers`, `/lecturers/:id` | Mọi tài khoản đăng nhập |
| Admin | `/administration`, `/administration/assignments`, `/positions`, `/rounds`, `/topics` (chỉ tra cứu), `/reports` | `ADMIN` hoặc `account:manage` |
| Sinh viên | `/topics`, `/registrations`, `/theses`, `/theses/:id`, `/proposals`, `/progress`, `/documents`, `/submissions`, `/evaluation`, `/evaluation/:id`, `/defense`, `/repository`, `/changes`, `/withdrawals`, `/ai` | `STUDENT` |
| Giảng viên | Như SV + `/reports`, `/review-records` (`evaluation:record`), `/roster` (`eligibility:*`) | `LECTURER` |
| Trưởng bộ môn | Như GV + duyệt đề tài (`topic:department_decide`), `/lecturer-profile-reviews`, lập hội đồng/xếp lịch trong `/defense` | `LECTURER` + chức vụ TBM |
| Tài khoản | `/account/activation-request`, `/account/forgot-password`, `/account/activate`, `/account/reset-password` | Không cần đăng nhập |
| Dự kiến | `/planned/:feature` (chatbot, similarity…) | Hiển thị “Đang phát triển” trong sidebar |

## 2. Chỉ số định lượng (đo ngày 22/11/2026)

| Chỉ số | Hiện trạng | Ý nghĩa |
|---|---:|---|
| Mã hex ngoài `tokens.css` | **696 lần / 420 màu khác nhau** | Token bị bỏ qua phần lớn; khó đồng bộ |
| Cỡ chữ px khác nhau (ngoài tokens) | **22 giá trị** (9 → 36px) | Token chỉ có 8 bậc; nhịp chữ không nhất quán |
| Chữ 9px / 10px | 5 / 15 lần | Dưới ngưỡng dễ đọc (brand eyebrow, kicker, nhãn mono) |
| Border-radius khác nhau | **17 giá trị** (2 → 24, 99, 999) | Token chỉ có 6/10/14 |
| Breakpoint khác nhau | **~40 biểu thức** (480, 520, 560, 600, 639, 640, 700, 720, 760, 768, 800, 820, 850, 860, 900, 960, 1000, 1023, 1100, 1150…) | Responsive vá theo từng tệp |
| Giá trị z-index | 0 → 9999 (30, 31, 35, 40, 45, 50, 2000, 9999) | Không có thang lớp |
| `!important` | 35 | Dấu hiệu tranh chấp specificity |
| Inline `style={{}}` | 94 (AIPage 24, AdministrationPage 12, ThesisViewPage 12) | Style nằm ngoài hệ thống |
| `window.confirm` / `window.alert` | 9 / 1 (DefensePage 6) | Hộp thoại trình duyệt không cùng ngôn ngữ thiết kế, không mô tả hậu quả |
| `<details>` | 71 (DefensePage 16, SchoolFormsPage 6, EvaluationPage 5) | Thao tác quan trọng bị giấu sau tiêu đề thu gọn |
| Trạng thái tải dạng chữ “Đang tải…” | 42 lần / 32 tệp | Không giữ khung bố cục; gây nhảy layout |
| `<EmptyState>` | 4 lần | Đa số trạng thái rỗng là `<p>` trơn |
| Dòng JSX > 300 ký tự | 240 (DefensePage 34, EvaluationPage 21) | Khó bảo trì; tỷ lệ thuận với độ rối giao diện |
| Chunk JS chính | **724,89 kB** (198 kB gzip) | Vượt khuyến nghị 500 kB của Vite |

## 3. Đối chiếu với báo cáo AI trước

| Hạng mục báo cáo cũ | Trạng thái kiểm chứng | Bằng chứng |
|---|---|---|
| Chuẩn hóa font-weight về 400/500/600/700 | **Chưa hoàn tất → đã sửa trong phiên này** | Còn 5 chỗ (`defense.css` 650×2, `lecturer-profile.css` 650×2, `withdrawals.css` 750); đã đổi về 600/700 |
| Loại bỏ cỡ chữ lẻ | **Chưa hoàn tất → đã sửa** | Còn `11.5px` và `12.5px` trong `roster.css`, `signature.css`; đã làm tròn về 12/13px |
| Checkbox “quan hệ thân nhân” hiện khi chưa chọn đề tài | **Đã sửa từ trước** | [DefensePage.tsx:192](file:///d:/KLTN/frontend/src/pages/DefensePage.tsx#L192) chỉ hiện khi `checkedTheses.length>0` |
| Không tìm thấy nút Mẫu 9 | **Không phải lỗi, là lỗi khả năng khám phá** | [DefensePage.tsx:406](file:///d:/KLTN/frontend/src/pages/DefensePage.tsx#L406) chỉ hiện cho Thư ký sau khi phiên đã chốt; người khác không thấy lý do |
| Thiếu tài khoản demo Admin | **Vẫn đúng, ngoài phạm vi UI** | `_DEMO_ACCOUNTS` trong `backend/api/auth.py` chỉ có `sv1–3`, `gv`, `tbm`, `gv2`. Sửa sẽ chạm vào auth nên không làm trong cải cách giao diện |
| Nút đăng xuất | **Đã xử lý** | Có trong ProfilePopup; nút riêng chỉ hiện trên mobile (`header__logout-standalone`) |
| `.btn-danger` | **Lỗi mới, đã sửa** | Được dùng ở `AdministrationPage.tsx:576` và `ThesisReviewEditor.tsx:39` nhưng không có CSS nên nút xóa trông như nút thường; đã bổ sung kiểu nút nguy hiểm |
| Empty state lồng trong card | **Lỗi mới, đã sửa** | `ThesesPage` đặt `EmptyState` (viền nét đứt) trong `card` (viền liền) → hai lớp khung; đã bỏ lớp card |
| Skeleton, toast, breadcrumb sâu, filter chip, kéo thả | **Chưa có** | Phân loại triển khai ở mục 7 |

## 4. Danh mục vấn đề

Mức ưu tiên: **P0** chặn chất lượng toàn hệ thống · **P1** ảnh hưởng rõ đến nghiệp vụ · **P2** tinh chỉnh.

### 4.1 Cấp hệ thống

| ID | Ưu tiên | Vấn đề | Bằng chứng | Tác động | Hướng sửa |
|---|---|---|---|---|---|
| S-01 | P0 | Hai hệ màu teal song song và 420 mã hex rời rạc | `tokens.css` vs `signature.css`; script đo | Màu hover/active/badge lệch nhau giữa các trang | Một tầng semantic token duy nhất (DESIGN_SYSTEM §2); codemod hex → token |
| S-02 | P0 | Tên trang có 4 nguồn khác nhau | Sidebar, `BREADCRUMB_MAP` trong `Header.tsx`, `labels` trong `App.tsx`, tiêu đề `PageHeader` | Người dùng không chắc đang ở đâu (bảng S-02a) | Tạo `routes.ts` (route manifest) làm nguồn duy nhất cho nhãn, icon, quyền, breadcrumb, `document.title` |
| S-03 | P0 | Không có thang cỡ chữ thực tế | 22 cỡ chữ; 9px ở brand và kicker | Thứ bậc mờ, chữ nhỏ khó đọc trên màn 1080p | Thang 7 bậc, tối thiểu 12px (11px chỉ cho mã mono in hoa) |
| S-04 | P1 | Hộp thoại xác nhận dùng trình duyệt | 9 `window.confirm`, 1 `window.alert` | Không nêu hậu quả, không đúng thương hiệu, không kiểm soát focus | `ConfirmDialog` với tiêu đề, hậu quả, nút nguy hiểm |
| S-05 | P1 | Lạm dụng `<details>` cho thao tác chính | 71 lần; Defense 16 | Hủy lịch, hủy phiếu, mở lại phiên… bị giấu; khó quét | Chỉ dùng `<details>` cho giải thích phụ. Thao tác chuyển vào action zone, Tabs hoặc Drawer |
| S-06 | P1 | CSS theo trang rò rỉ toàn cục | 10 tệp nạp lazy | Giao diện có thể khác nhau tùy trang mở trước | Đặt tiền tố phạm vi (`.defense-page …`) hoặc CSS Modules cho CSS theo trang |
| S-07 | P1 | Trạng thái tải dạng chữ | 42 chỗ | Nhảy layout, cảm giác chậm | `Skeleton` cho bảng, dashboard và danh sách phiên; còn lại dùng spinner trong nút |
| S-08 | P1 | Breakpoint và z-index tùy tiện | ~40 breakpoint; z-index tới 9999 | Lỗi ở kích thước trung gian, chồng lớp sai | 4 breakpoint chuẩn, thang z-index 8 bậc |
| S-09 | P2 | Tệp CSS chết `src/style.css` | Không có import | Gây nhầm khi bảo trì | Xóa ở Phase 2, sau khi kiểm tra lại |
| S-10 | P2 | Chunk chính 725 kB | Kết quả build | Lần tải đầu chậm trên mạng trường | Tách `pdfjs`/viewer review, lazy hóa `AdministrationPage`, `RosterPage`, `TopicsPage` |

**S-02a — Ví dụ lệch tên đã đối chiếu trong mã:**

| Route | Sidebar | Breadcrumb | H1 trang |
|---|---|---|---|
| `/roster` | Danh sách sinh viên | Danh sách sinh viên | Danh sách đủ điều kiện |
| `/ai` | Tra cứu tài liệu | Tra cứu thử nghiệm | Tra cứu AI |
| `/administration/assignments` | Phân công và chức vụ | Phân công theo đợt | Phân công theo đợt |
| `/registrations` (SV) | Đăng ký của tôi | Đăng ký | Đăng ký đề tài |
| `/account` | Thông tin của tôi | Tài khoản | Tài khoản của tôi |
| `/rounds` | Đợt KLTN | Đợt KLTN | Quản lý đợt KLTN |
| `/withdrawals` | Xin thôi KLTN | Xin thôi KLTN | Xin thôi thực hiện KLTN |

### 4.2 Cấp app shell

| ID | Ưu tiên | Vấn đề | Bằng chứng | Hướng sửa |
|---|---|---|---|---|
| A-01 | P1 | Icon sidebar không phân biệt được | `ClipboardList` dùng 6 lần, `FileText` 5 lần ([Sidebar.tsx](file:///d:/KLTN/frontend/src/components/layout/Sidebar.tsx)) | Mỗi mục một icon (bảng icon trong DESIGN_SYSTEM §8) |
| A-02 | P1 | Thiếu `title` khi sidebar thu gọn | `/lecturers`, `/withdrawals`, `/review-records`, `/topics` (admin), `/lecturer-profile-reviews`, “Hồ sơ chuyên môn” | Sinh từ manifest: luôn có `title` + `aria-label` khi thu gọn |
| A-03 | P1 | “Hồ sơ chuyên môn của tôi” không bao giờ active | `className="sidebar__item"` tĩnh, [Sidebar.tsx:159](file:///d:/KLTN/frontend/src/components/layout/Sidebar.tsx#L159) | Active theo `?section=lecturer-profile`; bỏ active của “Thông tin của tôi” khi đó |
| A-04 | P1 | Mục “Đang phát triển” nằm trong điều hướng chính | `PlannedLink` chatbot, similarity | Ẩn khỏi nav chính; nếu cần trình diễn, gom vào nhóm “Sắp có” cuối sidebar với badge |
| A-05 | P2 | Khối brand cao 148px | `signature.css:30` | Gọn còn ~88px (logo 32px + 2 dòng); trả chiều cao cho menu |
| A-06 | P2 | Breadcrumb chỉ 2 cấp, gốc “KLTN” không bấm được | `Header.tsx` | 3 cấp trên trang chi tiết (`Khóa luận › {mã} › Tiến độ`), cấp cha có link |
| A-07 | P2 | “Danh sách giảng viên” đặt trong nhóm “Đề tài và đăng ký” | Sidebar dòng 110 | Chuyển sang nhóm “Tra cứu” cùng Kho biểu mẫu, Kho khóa luận |
| A-08 | P2 | Fallback lazy là chữ trơn | `App.tsx:181` | Skeleton của page header + vùng nội dung |

### 4.3 Cấp trang

| ID | Trang | Ưu tiên | Vấn đề | Hướng sửa |
|---|---|---|---|---|
| P-01 | Hội đồng & bảo vệ | **P0** | Hai tầng tab dùng cùng kiểu `btn-primary/secondary` (`defense-tabs`) nên tab trang và tab phiên không phân biệt được; không dùng `role="tablist"` | Tab trang = underline tabs; bước trong phiên = process rail có trạng thái hoàn thành |
| P-02 | Hội đồng & bảo vệ | **P0** | Danh sách phiên là `<details>`; tiêu đề chỉ có “giờ · phòng · tên đề tài”, không có trạng thái | Danh sách dạng bảng/thẻ có cột Trạng thái (Đã xếp, Đang họp, Chờ chốt, Đã chốt), số SV, hội đồng; mở chi tiết trong trang hoặc drawer |
| P-03 | Hội đồng & bảo vệ | P1 | Form lập hội đồng trong dialog `lg`: 5 `<select>` với option nối chuỗi “Tên · mã · bộ môn · Ngoài Khoa · chuyên môn · lý do” | Combobox có tìm kiếm, mỗi option 2 dòng (tên + metadata), lý do bị khóa hiển thị bằng nhãn |
| P-04 | Hội đồng & bảo vệ | P1 | Thao tác phá hủy dùng `btn-secondary` (Hủy lịch, Hủy hiệu lực phiếu, Mở lại phiên) + `window.confirm` | Nút nguy hiểm + ConfirmDialog nêu hậu quả và yêu cầu lý do |
| P-05 | Hội đồng & bảo vệ | P1 | Đang có bản nháp thì ô tìm kiếm bị chặn, chỉ báo bằng banner lỗi đầu trang | Vẫn cho gõ; nếu kết quả lọc làm ẩn form đang sửa thì giữ phiên đó ghim đầu danh sách |
| P-06 | Hội đồng & bảo vệ | P1 | Mẫu 9 chỉ xuất hiện với Thư ký sau khi chốt; vai trò khác không thấy lý do | Hiện ô tài liệu bị khóa: “Biên bản Mẫu 9 · có sau khi chốt kết quả (Thư ký xuất)” |
| P-07 | Hội đồng & bảo vệ | P2 | Thông báo “Đã lưu thay đổi.” là banner đầu trang, xa chỗ thao tác | Toast ngắn + trạng thái tại form (`defense-form-status` đã có) |
| P-08 | Đề tài / Khóa luận / Hồ sơ nộp / Biểu mẫu | P1 | Mô tả PageHeader quá dài: 343, 278, 242, 207 ký tự | Tối đa 1 câu ≤ 90 ký tự; hướng dẫn chi tiết chuyển vào “Hướng dẫn” thu gọn hoặc empty state |
| P-09 | Tra cứu AI | P1 | 24 inline style | Chuyển sang class; dùng chung layout card/field |
| P-10 | Quản trị tài khoản | P1 | Tệp 1.258 dòng, 12 inline style, hai section dùng chung một component | Tách `AccountsSection`, `AssignmentsSection`; giữ nguyên API |
| P-11 | Chi tiết khóa luận | P1 | 12 inline style; tiêu đề lặp tên khóa luận trong description | Header chi tiết: mã + trạng thái + GVHD + process rail; tab Tổng quan / Hồ sơ nộp / Tiến độ |
| P-12 | Danh sách (Đề tài, Đăng ký, SV đủ điều kiện, Tài khoản, Phiên bảo vệ) | P1 | Bộ lọc mỗi trang một kiểu; không thấy bộ lọc đang áp dụng | `FilterBar` chuẩn: tìm kiếm + ≤3 bộ lọc + chip bộ lọc đang bật + “Xóa lọc” |
| P-13 | Bảng | P1 | Trên mobile chỉ có cuộn ngang (`table-scroll`) | Dưới 640px: bảng chuyển thành danh sách thẻ, giữ 3 cột quan trọng |
| P-14 | Dashboard | P2 | Welcome-spread tốt nhưng các widget chỉ là danh sách; chưa có “việc cần làm tiếp theo” theo vai trò | “Next action” card theo vai trò (SV: bước tiếp theo trong quy trình; GV: hồ sơ chờ duyệt; TBM: đề tài/hội đồng chờ; Admin: đợt đang mở và cảnh báo) |
| P-15 | Đăng nhập | P2 | Khối demo cạnh form chính; không có Admin demo | Giữ form email là hành động chính; khối demo thu gọn có nhãn “Môi trường thử nghiệm” |

### 4.4 Cấp vi mô

| ID | Ưu tiên | Vấn đề | Bằng chứng | Hướng sửa |
|---|---|---|---|---|
| M-01 | P1 | Chữ phụ chưa đạt AA trên nền canvas | `--signature-muted #637572` trên `#f3f6f5` ≈ **4,47:1** (< 4,5) | Đổi thành `#566965` (5,36:1 trên canvas, 5,83:1 trên trắng — đã tính theo công thức WCAG) |
| M-02 | P1 | Chữ 9px | brand eyebrow, faculty, welcome-kicker (`signature.css:32,34,114`) | Tối thiểu 11px mono in hoa, letter-spacing 0,08em |
| M-03 | P1 | Nút và input 13px | `signature.css:57,69` | Control 14px; nút nhỏ 13px |
| M-04 | P2 | Radius 7px cho nút/input lệch token | `signature.css:57,69` | 6px (`--radius-sm`) |
| M-05 | P2 | Header bảng 11px in hoa, chữ dữ liệu 13px | `signature.css:81` | Header 12px semibold, giữ in hoa nhẹ; dữ liệu 14px, số dùng `tabular-nums` |
| M-06 | P2 | `Dialog` đặt `role="dialog"` trên overlay | `Dialog.tsx` | Đặt `role`/`aria-modal` trên khung `.dialog` |

## 5. Điều đang làm tốt (phải giữ)

1. **Welcome-spread**: bố cục editorial chia đôi với panel teal đậm — có cá tính, khác dashboard thẻ số đại trà.
2. **Code-chip mono** cho mã đề tài, MSSV, phiên bản — rõ ràng, phù hợp tính chất hồ sơ học vụ.
3. **Bảng màu teal học thuật** — khác hẳn các đề tài dùng xanh dương mặc định.
4. **Sidebar theo vai trò và quyền** (`context.actions`) — đúng nghiệp vụ, không hiện chức năng thừa.
5. **Bảo vệ bản nháp** (`DraftForm`, `beforeunload`, chặn link khi chưa lưu) — trải nghiệm an toàn dữ liệu đáng giá.
6. **Kiểm soát xung đột phiên bản** (`If-Match`, `context_token`, cảnh báo dữ liệu đã đổi trong phiếu chấm).
7. **Dialog có focus trap, Escape, khóa cuộn, xếp chồng nhiều lớp.**
8. **Skip link, `aria-current` qua NavLink, drawer mobile có `inert`.**
9. **Workspace review PDF** với chú thích theo trang.

## 6. Điểm hiện trạng (chấm lại theo tiêu chí)

Thang 10, mỗi tiêu chí chấm theo bằng chứng ở trên. Chưa có kiểm thử trực quan trong phiên này nên các tiêu chí “thẩm mỹ” để biên độ ±0,5.

| Tiêu chí | Trọng số | Điểm | Căn cứ chính |
|---|---:|---:|---|
| Bản sắc thị giác | 10% | 7,5 | Welcome-spread, teal, mono chip; nhưng chưa phủ hết các trang nghiệp vụ |
| Nhất quán hệ thống | 15% | 5,0 | 420 màu, 22 cỡ chữ, 17 radius, 4 nguồn tên trang |
| Typography & khả năng đọc | 10% | 6,5 | Inter tốt; chữ 9–10px và control 13px |
| Màu & tương phản | 10% | 6,5 | Chữ muted sát ngưỡng AA; nút nguy hiểm thiếu kiểu (đã sửa) |
| Bố cục & mật độ | 10% | 6,5 | Trang thường ổn; Defense dày đặc, nhiều tầng thu gọn |
| Điều hướng & IA | 15% | 6,0 | Theo vai trò tốt; icon trùng, nhãn lệch, mục “đang phát triển” |
| Luồng thao tác nghiệp vụ | 15% | 6,0 | An toàn dữ liệu tốt; thao tác chính bị giấu, xác nhận bằng trình duyệt |
| Phản hồi trạng thái (loading/empty/error) | 5% | 5,5 | Chữ “Đang tải”, empty state ít |
| Responsive | 5% | 6,5 | Drawer, target 44px; bảng chỉ cuộn ngang, breakpoint rời rạc |
| Accessibility | 5% | 7,0 | Skip link, focus trap, label; tabs thiếu ARIA, chữ nhỏ |
| **Tổng có trọng số** | 100% | **≈ 6,2 / 10** | |

> [!NOTE]
> Mục tiêu 9,5+/10 chỉ được công nhận khi đạt toàn bộ tiêu chí định lượng trong [ACCEPTANCE_CRITERIA.md](file:///d:/KLTN/docs/ui-redesign/ACCEPTANCE_CRITERIA.md) **và** có ảnh chụp, kết quả axe, kết quả Playwright đi kèm.

## 7. Phân loại các đề xuất trong checklist cũ

| Đề xuất | Quyết định | Lý do / cách làm |
|---|---|---|
| Skeleton shimmer | **Điều chỉnh** | Chỉ cho dashboard widgets, bảng và danh sách phiên bảo vệ; hiện sau 300 ms; tắt hiệu ứng khi `prefers-reduced-motion` |
| Breadcrumb | **Điều chỉnh** | Sinh từ route manifest; 3 cấp chỉ cho trang chi tiết; cấp cha có link |
| Filter chips | **Triển khai** | Trong `FilterBar` cho 5 trang danh sách lớn |
| Kéo thả tải tệp | **Điều chỉnh** | Dropzone bọc input gốc (giữ khả năng dùng bàn phím) chỉ ở nộp hồ sơ/tài liệu; không áp dụng cho ảnh đại diện |
| Toast | **Triển khai có giới hạn** | Chỉ cho thông báo thành công thoáng qua (`role="status"`, 4 s, dừng khi hover); lỗi vẫn hiển thị tại form |
| Nút đăng xuất trên sidebar | **Không triển khai** | Đã có trong ProfilePopup và trên mobile; thêm nữa là trùng lặp |
| Tài khoản demo Admin | **Không triển khai trong đợt UI** | Chạm vào auth/backend, ngoài phạm vi |
| Checkbox thân nhân ở Defense | **Đã xong** | Xem mục 3 |
| Vị trí nút Mẫu 9 | **Điều chỉnh** | Ô tài liệu bị khóa có lý do, thay vì “không có nút” |
| Preset màu xanh DThU `#00568c` | **Không triển khai** | Làm mất bản sắc teal. Chỉ tham khảo cấu trúc component sau khi kiểm chứng giấy phép |
| Thay `window.confirm` | **Triển khai** | ConfirmDialog (S-04) |

## 8. Sửa nhỏ đã thực hiện trong Phase 1

Chỉ gồm sửa lỗi an toàn, không đổi nghiệp vụ. Đã kiểm tra bằng `npx tsc --noEmit` và `npm run build`.

- Bổ sung kiểu `.btn-danger` (trước đó class được dùng nhưng chưa có CSS).
- Chuẩn hóa 5 font-weight lẻ và 2 cỡ chữ lẻ còn sót.
- Bỏ lớp card lồng ngoài `EmptyState` ở `ThesesPage`; `.overview-empty` dùng token thay cho mã hex.
- Chuẩn hóa ký tự xuống dòng cho các tệp bị lẫn CRLF/LF từ phiên trước để diff chỉ còn nội dung thật.
