# Khảo sát & Đối chiếu Nguồn Thiết kế (DThU UI Kit + Lovable UX Reference)

> **Nguồn 1 — DThU UI Kit:** `https://dthu-kit.anhdev99.com/` (tuyến đã khảo sát: `/`, `/components`, `/templates`, `/blocks/faculty`, `/theme`, `/r/theme.json`)  
> **Nguồn 2 — Lovable Interactive UX Reference:** `https://prompt-to-polished-interface.lovable.app/` (khảo sát trực tiếp qua 4 vai trò: Sinh viên, Giảng viên, Trưởng bộ môn, Quản trị viên và các tuyến `/`, `/de-tai`, `/khoa-luan`, `/tro-ly-ai`, `/dang-nhap`)  
> **Ngày cập nhật:** `25/11/2026` · **Phiên bản áp dụng:** `DThU Academic Blue V3` · **Nhánh:** `NV6`

---

## 1. Chiến lược kế thừa kép & Nguyên tắc kỹ thuật

1. **Giữ vững nền tảng kỹ thuật của dự án:** Không cài Tailwind CSS v4, `@radix-ui/*` hay `vaul` từ DThU UI Kit/Lovable; kế thừa CSS custom properties thuần (`23` tệp CSS) + `lucide-react` trong [`frontend/package.json`](file:///d:/KLTN/frontend/package.json) để đảm bảo ổn định tuyệt đối và tương thích 100% bộ E2E.
2. **Chuẩn hóa component & quy trình từ DThU UI Kit (MIT):** Kế thừa phân cấp Button, Badge, Stepper (`ThesisJourney`), Timeline (`ActivityTimeline`), Tabs, FilterBar, FileDropzone, Table, EmptyState, Skeleton và ngữ cảnh hành chính học vụ *Khoa Công nghệ và Kỹ thuật — ĐHĐT*.
3. **Tinh gọn trải nghiệm & nhịp điệu thị giác theo Lovable V3 Reference:**
   - Thanh bên xanh đậm có gradient đáy nhẹ `#143B59 → #246B96` với đồ họa campus + hoa sen ghim gọn trên chân footer.
   - Bề mặt làm việc `#FFFFFF` đặt trên nền sáng gần trắng `#F7FAFC`, màu xanh `#1976B8` tập trung vào CTA chính và vùng có ý nghĩa.
   - Dashboard 2 cột bất đối xứng theo ngữ cảnh vai trò thật: Hero chào theo giai đoạn (hiển thị CTA động `Mở hồ sơ nộp lưu` khi `DEFENDED`, `Xem bản lưu trữ` khi `COMPLETED`), danh sách việc cần xử lý bên trái, lối tắt tra cứu + hộp gọi **Trợ lý tra cứu AI** bên phải.
   - **Topics Explorer tinh gọn + Right Side Drawer:** Giảm mật độ thẻ đề tài xuống thông tin cốt lõi (mã, nguồn, trạng thái, tiêu đề bấm mở, mô tả 2 dòng, chip yêu cầu tối đa, metadata footer gọn gồm GV tiếp nhận/GV được SV đề xuất, năm học, sĩ số), kèm nút chuyển **Dạng thẻ / Dạng danh sách** đặt gọn trên thanh `.topics-subbar` đối diện Tabs, và **Right Side Drawer `600px`** (`Dialog` `variant="drawer"`) mở chi tiết/duyệt/chỉnh sửa ngay tại trang `/topics` mà không mất ngữ cảnh danh sách.
   - **Thesis Workspace 2 cột (`1.5fr / 0.85fr`):** Thẻ nhận diện đề tài + `ThesisJourney` nổi bật ở trên; điều hướng tab, phân công công việc, nhật ký hoạt động bên trái; nhóm sinh viên thực hiện + GVHD chính thức gọn nhẹ bên phải.
4. **Kỷ luật dữ liệu thật:** Tuyệt đối **không** đưa dữ liệu giả, `%` tiến độ giả, nút lưu bookmark giả hay bộ chuyển theme mẫu từ prototype vào mã nguồn sản phẩm.

---

## 2. Bảng đối chiếu chi tiết Component DThU Kit & Lovable UX ↔ KLTN V3

| Hạng mục | Nguồn chuẩn tham chiếu | Ánh xạ & Triển khai thực tế tại KLTN V3 |
|---|---|---|
| **Button & Action Hierarchy** | DThU Kit `/components/button` (`primary`, `secondary`, `soft`, `outline`, `ghost`, `danger`) | [`Button.tsx`](file:///d:/KLTN/frontend/src/components/ui/Button.tsx) + `.btn*` trong [`components.css`](file:///d:/KLTN/frontend/src/styles/components.css) & [`signature.css`](file:///d:/KLTN/frontend/src/styles/signature.css) với bảng màu V3 `#1976B8` / `#EAF4FB` / `#B42318`. |
| **Badge trạng thái** | DThU Kit `/components/badge` | [`Badge.tsx`](file:///d:/KLTN/frontend/src/components/ui/Badge.tsx) + [`ThesisStatusBadge.tsx`](file:///d:/KLTN/frontend/src/components/domain/ThesisStatusBadge.tsx) (`#EAF5EE`/`#166534`, `#EAF4FB`/`#185B80`, `#FFF7E8`/`#92400E`, `#FDECEC`/`#991B1B`). |
| **Stepper & Timeline** | DThU Kit `/components/stepper`, `/components/timeline` | `ThesisJourney` (5 chặng ngang) & `ActivityTimeline` trong [`Timeline.tsx`](file:///d:/KLTN/frontend/src/components/ui/Timeline.tsx); [`WorkflowSteps.tsx`](file:///d:/KLTN/frontend/src/components/domain/WorkflowSteps.tsx) biến thể gọn 3 cột bên trong Side Drawer. |
| **Right Side Drawer (`vaul`/`Sheet` UX)** | DThU Kit (`Drawer`/`Sheet`) + Lovable `/de-tai` Drawer `576px` | Mở rộng [`Dialog.tsx`](file:///d:/KLTN/frontend/src/components/ui/Dialog.tsx) với `variant="drawer"`, `headerMeta`, footer dính theo vai trò (SV/GV/TBM), `topic-drawer-meta` 2 cột và `.topic-drawer-students` chia dòng gọn. |
| **Topics Explorer & Subbar** | Lovable `/de-tai` + DThU Kit `InputGroup`/`Tabs` | [`TopicsPage.tsx`](file:///d:/KLTN/frontend/src/pages/TopicsPage.tsx) kết hợp [`FilterBar.tsx`](file:///d:/KLTN/frontend/src/components/ui/FilterBar.tsx), `.topics-subbar` chứa [`Tabs.tsx`](file:///d:/KLTN/frontend/src/components/ui/Tabs.tsx) và nút chuyển **Dạng thẻ / Dạng danh sách** (`.topic-view-toggle`). |
| **Dashboard & Workspace Layout** | Lovable `/` & `/khoa-luan` | [`WorkspacePage.tsx`](file:///d:/KLTN/frontend/src/pages/WorkspacePage.tsx) (CTA Hero theo trạng thái thật, 2 cột bất đối xứng + callout Tra cứu AI) & [`ThesisViewPage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisViewPage.tsx) (Hero Banner + overview `1.5fr / 0.85fr`). |
| **Sidebar & Campus Identity** | Lovable Sidebar + DThU Kit `/blocks/faculty` | [`Sidebar.tsx`](file:///d:/KLTN/frontend/src/components/layout/Sidebar.tsx) nền `#143B59 → #246B96`, footer `#10334E`, `.sidebar__art-dock` đặt trên footer chứa [`SidebarLotusArt`](file:///d:/KLTN/frontend/src/components/ui/CampusArtwork.tsx). |
| **Table / DataGrid** | DThU Kit `/components/table`, `/components/data-grid` | `.table-container` cuộn ngang độc lập (`overflow-x: auto; overflow-y: hidden`) trong [`workflow-clarity.css`](file:///d:/KLTN/frontend/src/styles/workflow-clarity.css). |
| **FileUpload / Pagination / Skeleton / EmptyState** | DThU Kit `/components/file-upload`, `pagination`, `empty-state`, `avatar` | [`FileDropzone.tsx`](file:///d:/KLTN/frontend/src/components/ui/FileDropzone.tsx), `.pagination`, [`Skeleton.tsx`](file:///d:/KLTN/frontend/src/components/ui/Skeleton.tsx), [`EmptyState.tsx`](file:///d:/KLTN/frontend/src/components/ui/EmptyState.tsx). |
| **Biểu mẫu, Hội đồng, Kho lưu trữ** | DThU Kit `/templates/hanh-chinh-so`, `quan-ly-van-ban` | Bảo toàn và làm sạch bề mặt V3 trên [`SchoolFormsPage.tsx`](file:///d:/KLTN/frontend/src/pages/SchoolFormsPage.tsx), [`DefensePage.tsx`](file:///d:/KLTN/frontend/src/pages/DefensePage.tsx), [`ThesisArchivePage.tsx`](file:///d:/KLTN/frontend/src/pages/ThesisArchivePage.tsx), [`RosterPage.tsx`](file:///d:/KLTN/frontend/src/pages/RosterPage.tsx), [`AdministrationPage.tsx`](file:///d:/KLTN/frontend/src/pages/AdministrationPage.tsx). |
