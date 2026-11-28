# Tiến độ & Danh mục triển khai — DThU Academic Blue V3 Transformation

> **Phạm vi thực thi:** Thực hiện cuộc đại tu UI/UX toàn diện trong `d:\KLTN\frontend\src` (kế thừa và nâng cấp từ nền V2 lên **DThU Academic Blue V3 — Fresh Campus Identity**) mà không thay đổi backend, cơ sở dữ liệu hay thêm phụ thuộc npm.  
> **Cập nhật lần cuối:** `25/11/2026` · **Trạng thái:** Hoàn thành toàn bộ nâng cấp V3, Pilot refinements, QA trực tiếp (`87/87`) và `9/9` spec E2E cô lập.

---

## Giai đoạn 1 — Nền tảng V1/V2 kế thừa (Đã bảo toàn)

1. **Modular hóa Stylesheet (`23` tệp CSS trong `frontend/src/styles/`):** Thiết lập [`tokens.css`](file:///d:/KLTN/frontend/src/styles/tokens.css) cùng `22` tệp style phân lớp gọn nhẹ (`reset.css`, `typography.css`, `layout.css`, `components.css`, `signature.css`, `login.css`, `admin.css`, `assignment-tabs.css`, `content-polish.css`, `defense.css`, `evaluation.css`, `lecturer-profile.css`, `positions.css`, `review-workspace.css`, `roster.css`, `rounds.css`, `school-forms.css`, `thesis-changes.css`, `version-timeline.css`, `withdrawals.css`, `workflow-clarity.css`, `workflow-steps.css`), nhập tập trung tại [`main.tsx`](file:///d:/KLTN/frontend/src/main.tsx).
2. **Thư viện Shared UI (`13` tệp `frontend/src/components/ui/`) & Layout (`9` tệp `frontend/src/components/layout/`):** `Button`, `Badge`, `Timeline`, `Tabs`, `FilterBar`, `FileDropzone`, `EmptyState`, `Skeleton`, `ConfirmDialog`, `Dialog`, `Toast`, `PasswordField`, `CampusArtwork` cùng `Sidebar`, `Header`, `PageHeader`, `NotificationsBell`, `ProfilePopup`, `AssignmentTabs`, `AppShell`.
3. **29 trang nghiệp vụ & 44 domain components:** Toàn bộ màn hình cho `4` vai trò (`Sinh viên`, `Giảng viên`, `Trưởng bộ môn`, `Quản trị viên`) hoạt động trên dữ liệu và phân quyền thật.

---

## Giai đoạn 2 — Change Request V3 (Fresh Campus Identity & UX Redesign)

1. **Khảo sát tham chiếu trực tiếp & Chuyển bảng màu V3 ([`tokens.css`](file:///d:/KLTN/frontend/src/styles/tokens.css), [`login.css`](file:///d:/KLTN/frontend/src/styles/login.css)):**
   - Khảo sát trực tiếp [`prompt-to-polished-interface.lovable.app`](https://prompt-to-polished-interface.lovable.app/) và [`dthu-kit.anhdev99.com`](https://dthu-kit.anhdev99.com/).
   - Thay thế toàn bộ bảng màu V2 sang V3: sidebar xanh đậm có chiều sâu `#143B59 → #246B96` + footer `#10334E`, nền trang gần trắng `#F7FAFC`, bề mặt `#FFFFFF`, hành động chính `#1976B8`, hover `#135F93`, active sidebar `#E3F1FA` / `#174A6D`, accent vàng `#D7A348`, chỉnh `--color-ink-muted: #566E80` để mọi cỡ chữ đạt WCAG 2.2 AA (`≥ 4.87:1`).
   - Nâng cấp gradient màn hình đăng nhập [`login.css`](file:///d:/KLTN/frontend/src/styles/login.css) sang `#10334E → #143B59 → #246B96`.
2. **Nâng cấp Đồ họa Khuôn viên & Sidebar Dock ([`CampusArtwork.tsx`](file:///d:/KLTN/frontend/src/components/ui/CampusArtwork.tsx), [`Sidebar.tsx`](file:///d:/KLTN/frontend/src/components/layout/Sidebar.tsx), [`signature.css`](file:///d:/KLTN/frontend/src/styles/signature.css)):**
   - Vẽ lại 4 SVG bản sắc chi tiết hơn: kiến trúc giảng đường 2 tầng + hoa sen Đồng Tháp + đường cong Mekong điểm vàng `#D7A348`.
   - Đưa `SidebarLotusArt` vào `.sidebar__art-dock` cố định ngay phía trên `.sidebar__footer` (hiển thị trên `min-height: 740px` khi không thu gọn), tinh chỉnh nhịp sidebar desktop để đồ họa luôn hiện diện rõ mà không che nav hay phải cuộn mới thấy.
3. **Mở rộng Container Widths & Loại bỏ cảm giác bị bó giữa màn hình:**
   - Mở rộng `.app-shell__content > *` lên `1400px`, `.admin-page` / `.roster-page` lên `1440px`, `.withdrawal-page` lên `1320px`, `.notification-history` lên `1200px`, `.registration-card` và `.topic-card` `100%`.
4. **Đại tu Topics Explorer & Right Side Drawer ([`Dialog.tsx`](file:///d:/KLTN/frontend/src/components/ui/Dialog.tsx), [`TopicsPage.tsx`](file:///d:/KLTN/frontend/src/pages/TopicsPage.tsx), [`content-polish.css`](file:///d:/KLTN/frontend/src/styles/content-polish.css), [`workflow-steps.css`](file:///d:/KLTN/frontend/src/styles/workflow-steps.css)):**
   - Bổ sung biến thể `variant="drawer"` + `headerMeta` vào [`Dialog.tsx`](file:///d:/KLTN/frontend/src/components/ui/Dialog.tsx) (width `600px` desktop `border-radius: 0`, full-screen mobile, `dialog__close-btn` viền nổi rõ `36px`/`44px`, footer dính theo quyền).
   - Đặt thanh chuyển chế độ **Dạng thẻ / Dạng danh sách** (`.topic-view-toggle`) vào `.topics-subbar` đối diện `Tabs` để trả lại chiều rộng thoáng cho thanh tìm kiếm `FilterBar`.
   - Tinh gọn thẻ đề tài (tiêu đề bấm mở drawer, giữ nhãn vai trò `GV được SV đề xuất` / `GV tiếp nhận` bên cạnh liên kết GV), chuẩn hóa mô tả đa đoạn/danh sách (`renderDescriptionContent`), lưới metadata 2 cột `.topic-drawer-meta`, 3 bước `WorkflowSteps` trên 1 hàng, và danh sách sinh viên đã đăng ký dạng dòng chia sạch `.topic-drawer-students`.
5. **Nâng cấp Role Dashboards & Thesis Workspace ([`WorkspacePage.tsx`](file:///d:/KLTN/frontend/src/pages/WorkspacePage.tsx), [`ThesisViewPage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisViewPage.tsx), [`workflow-clarity.css`](file:///d:/KLTN/frontend/src/styles/workflow-clarity.css)):**
   - Student Hero tự đổi CTA theo trạng thái khóa luận thật (`DEFENDED` → *Mở hồ sơ nộp lưu*, `COMPLETED` → *Xem bản lưu trữ*); bố cục 2 cột bất đối xứng kèm khối gọi **Trợ lý tra cứu AI** nối thẳng `/ai`.
   - [`ThesisViewPage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisViewPage.tsx) nâng cấp Hero Card `.thesis-identity` với `CampusBannerArt` + `ThesisJourney` và lưới overview 2 cột (`1.5fr / 0.85fr`).
6. **Đồng bộ sạch toàn hệ thống & Sửa hồi quy kiểm chứng:**
   - Làm sạch màu teal/slate cũ trong [`ReviewTextDocument.tsx`](file:///d:/KLTN/frontend/src/components/domain/ReviewTextDocument.tsx) (Shadow DOM pins chuyển sang `#1976B8`/`#EAF4FB`/`#D7A348`), [`components.css`](file:///d:/KLTN/frontend/src/styles/components.css) (mũi tên select, nút đăng xuất, bỏ `opacity: 0` trong `@keyframes drawer-slide-in`/`dialog-content-in` để Axe đo đúng màu khi drawer vừa mở) và [`roster.css`](file:///d:/KLTN/frontend/src/styles/roster.css).
   - Đồng bộ 2 selector heading trong [`four-roles-audit.spec.ts`](file:///d:/KLTN/frontend/e2e/four-roles-audit.spec.ts) (`"Giao nhiệm vụ theo đợt"`) khớp với thay đổi tiêu đề có từ trước phiên ở commit `03d0e16` ([`AdministrationPage.tsx:368`](file:///d:/KLTN/frontend/src/pages/AdministrationPage.tsx#L368)) và [`school-forms.spec.ts:84`](file:///d:/KLTN/frontend/e2e/school-forms.spec.ts#L84).
