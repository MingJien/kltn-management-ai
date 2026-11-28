# Báo cáo Kiểm thử & Nghiệm thu QA — DThU Academic Blue V3

> **Ngày kiểm chứng cuối cùng (sau lần sửa mã nguồn cuối):** `25/11/2026`  
> **Phạm vi:** Kiểm định độc lập toàn phần UI/UX, hợp đồng Backend-First, biên dịch tĩnh, quét mã nguồn CSS/TSX, kiểm thử trình duyệt trực tiếp **`102/102`** lượt trên **`9`** kích thước màn hình (`320×568` → `1920×1080`) kèm `@axe-core/playwright` + xác minh token V3, làm mới **`23`** ảnh chụp V3 `AFTER` (giữ nguyên **`12`** ảnh `BEFORE`), và chạy hồi quy đầy đủ toàn bộ **`33/33`** spec Playwright E2E (`71/71` test case) trên schema PostgreSQL cô lập + ClamAV thật.  
> **Tài liệu chi tiết truy vết & nhật ký khắc phục:** [`QA_TRACEABILITY_MATRIX.md`](file:///d:/KLTN/docs/ui-redesign/QA_TRACEABILITY_MATRIX.md).

---

## 1. Tổng hợp kết quả xác minh sau lần chỉnh sửa cuối cùng

| Hạng mục kiểm tra | Lệnh / Công cụ thực thi | Kết quả xác minh thực tế |
|---|---|---|
| **TypeScript Typecheck** | `npm --prefix d:\KLTN\frontend run qa:typecheck` | **ĐẠT (`exit 0`)**, `0` lỗi kiểu dữ liệu |
| **Production Vite Build** | `npm --prefix d:\KLTN\frontend run qa:build` | **ĐẠT (`exit 0`)**, `2044 modules transformed`, hoàn tất trong `5.41s` (`dist/assets/index-wYBuOyxv.css 190.22 kB │ gzip: 31.72 kB`) |
| **Quét tĩnh CSS/TSX** | Node audit toàn bộ `d:\KLTN\frontend\src` | **`23`** tệp CSS · **`29`** trang · **`44`** tệp `components/domain` (`42` `.tsx` + `2` `.ts`) · **`33`** spec E2E · **`0`** `font-size < 11px` · **`0`** hex V1/V2 xanh đậm/teal · **`6`** `style={{}}` động hợp lệ theo kích thước/tọa độ/tỷ lệ · **`1`** mã nền trung tính `#f8fafc` tiền tồn tại tại [`roster.css:359`](file:///d:/KLTN/frontend/src/styles/roster.css#L359) |
| **Kiểm thử trình duyệt 9 viewport + WCAG + Token V3** | `full_qa_verify.mjs` (`tools.run_demo_api` + Vite + Playwright + `@axe-core/playwright`) | **`102/102` lượt ĐẠT**: `v3TokensOk: true` (khớp 7 token V3 chính), `failedOverflowCount: 0`, `failedMainLeftCount: 0`, **`failedAxeCount: 0` (WCAG 2.0/2.1 A/AA)**, `pageErrorCount: 0`, `non401ConsoleErrorCount: 0` (`15` log `401` thăm dò trước đăng nhập theo hành vi Chromium), `serverErrorCount: 0`, **`23`** ảnh `AFTER` |
| **Hồi quy E2E Đợt 1/5 (Cô lập)** | `tools.run_e2e --isolate-specs` (`7` spec) | **`7/7` spec · `17/17` test cases ĐẠT**: `account-roster` (`1`, `13.7s`), `activity` (`1`, `11.1s`), `admin-pagination` (`1`, `7.8s`), `ai-workspace` (`1`, `11.6s`), `archive-live` (`2`, `31.6s`), `archive-workspace` (`2`, `6.0s`), `defense-drafts` (`9`, `20.8s`) |
| **Hồi quy E2E Đợt 2/5 (Cô lập)** | `tools.run_e2e --isolate-specs` (`7` spec) | **`7/7` spec · `15/15` test cases ĐẠT**: `defense-workspace` (`2`, `10.0s`), `four-roles-audit` (`3`, `42.2s`), `lecturer-import` (`1`, `10.0s`), `lecturer-profiles` (`1`, `20.9s`), `mau04-export` (`1`, `5.7s`), `mobile-layout` (`6`, `2.6m`), `nv5-completion` (`1`, `1.0m`) |
| **Hồi quy E2E Đợt 3/5 (Cô lập)** | `tools.run_e2e --isolate-specs` (`7` spec) | **`7/7` spec · `17/17` test cases ĐẠT**: `nv5-official-roster` (`1`, `8.0s`), `nv6-evaluation` (`4`, `29.6s`), `positions` (`1`, `7.7s`), `progress-annotations` (`1`, `19.2s`), `qa-contracts-and-rbac` (`1`, `11.7s`), `registration-forms` (`1`, `27.8s`), `registration` (`8`, `1.3m`) |
| **Hồi quy E2E Đợt 4/5 (Cô lập)** | `tools.run_e2e --isolate-specs` (`6` spec) | **`6/6` spec · `7/7` test cases ĐẠT**: `review-feedback` (`1`, `21.5s`), `school-form-create-upload` (`2`, `11.4s`), `school-forms` (`1`, `51.3s`), `staff-email` (`1`, `6.9s`), `student-activation-selection` (`1`, `12.8s`), `student-withdrawal-demo` (`1`, `24.7s`) |
| **Hồi quy E2E Đợt 5/5 (Cô lập)** | `tools.run_e2e --isolate-specs` (`6` spec) | **`6/6` spec · `15/15` test cases ĐẠT**: `submission-ui` (`1`, `39.2s`), `thesis-changes` (`3`, `35.3s`), `ui-feedback` (`6`, `13.8s`), `withdrawals` (`1`, `25.6s`), `workflow-clarity` (`3`, `21.2s`), `workflow-notices` (`1`, `21.7s`) |
| **Tổng cộng E2E Cô lập (Sau sửa cuối)** | Toàn bộ 5 đợt với `KLTN_E2E_ALLOW_ISOLATED_SCHEMA=true` + ClamAV thật | **`33/33` spec files · `71/71` test cases ĐẠT 100%** |
| **Backend Pytest Suite** | `d:\KLTN\.venv\Scripts\python.exe -m pytest -q` | **`280 passed, 1 failed`** (`107.52s`): chỉ thất bại ở [`tests/test_openapi_contract.py`](file:///d:/KLTN/tests/test_openapi_contract.py) do lệch `docs/design/openapi.yaml` tiền tồn tại với [`backend/api/school_forms.py`](file:///d:/KLTN/backend/api/school_forms.py) |

### Lệnh QA tái sử dụng trong `frontend/package.json` & công cụ dự án
- Kiểm tra kiểu: `npm --prefix d:\KLTN\frontend run qa:typecheck`
- Đóng gói sản phẩm: `npm --prefix d:\KLTN\frontend run qa:build`
- Chạy riêng 2 spec hợp đồng & AI (kèm runner cô lập): `d:\KLTN\.venv\Scripts\python.exe -m tools.run_e2e --isolate-specs ai-workspace.spec.ts qa-contracts-and-rbac.spec.ts` (hoặc `npm --prefix d:\KLTN\frontend run qa:e2e:contracts` trong phiên `playwright`)

---

## 2. Kết quả chi tiết `102` lượt Kiểm thử Trực tiếp, 9 Viewport & Side Drawer V3

Thực thi trên **`9` độ phân giải** (`320×568`, `360×800`, `390×844`, `768×1024`, `844×390` ngang di động, `1024×768`, `1280×800`, `1440×900`, `1920×1080`) tại các tuyến trụ cột và `1440×900` + `390×844` tại các tuyến chuyên sâu:

- **Công khai (`public`):** `/`, `/account/activation-request`, `/account/forgot-password` — `0` overflow, `0` vi phạm Axe.
- **Sinh viên (`sv1`):** `/` (`9` viewport + kiểm trạng thái drawer điều hướng mobile `390×844`), `/topics` + **Right Side Drawer `/topics (drawer)`** (`1440×900` rộng `600px`, `border-radius: 0px`; `390×844` khớp overlay, `.workflow-steps__number` tròn đều `28×28px`, đóng sạch bằng `Escape`), `/registrations`, `/theses`, `/submissions`, `/progress`, `/forms`, `/ai`, `/changes`, `/withdrawals`, `/evaluation`, `/defense`, `/repository`, `/notifications`, `/activity`, `/account`, `/lecturers`, `/planned/expertise` — `0` overflow, `0` vi phạm Axe.
- **Giảng viên (`gv`):** `/` (`9` viewport), `/evaluation`, `/account`, `/reports`, `/ai` — `0` overflow, `0` vi phạm Axe.
- **Trưởng bộ môn (`tbm`):** `/` (`9` viewport), `/defense` (`9` viewport), `/repository`, `/lecturer-profile-reviews`, `/roster`, `/review-records` — `0` overflow, `0` vi phạm Axe.
- **Token V3 xác minh runtime tại `:root`:** `--sidebar-bg: #143b59`, `--sidebar-gradient-end: #246b96`, `--color-primary: #1976b8`, `--color-canvas: #f7fafc`, `--color-surface: #ffffff`, `--color-surface-highlight: #eaf4fb`, `--color-accent-gold: #d7a348`.
- **Chi tiết `6` `style={{}}` động hợp lệ:** [`DefensePrintPreview.tsx:55`](file:///d:/KLTN/frontend/src/components/domain/DefensePrintPreview.tsx#L55) (kích thước ô bảng mẫu in), [`ReviewPdfPage.tsx:75`](file:///d:/KLTN/frontend/src/components/domain/ReviewPdfPage.tsx#L75), `L85`, `L89` (kích thước trang PDF và tọa độ ghim nhận xét), [`Skeleton.tsx:17`](file:///d:/KLTN/frontend/src/components/ui/Skeleton.tsx#L17) (props `width`/`height`), [`AIPage.tsx:344`](file:///d:/KLTN/frontend/src/pages/AIPage.tsx#L344) (tỷ lệ phần trăm thanh tương đồng đã kẹp `[0..100%]`).

### Ghi chú trung thực về phạm vi kiểm chứng & điều chỉnh kiểm thử
- **Admin giữa `run_demo_api` và E2E cô lập:** Kịch bản nhanh `full_qa_verify.mjs` ghi nhận `adminStatus: "unverified_no_demo_credentials"` trên `tools.run_demo_api`, nhưng vai trò Admin đã được kiểm chứng đầy đủ trên dữ liệu thật trong schema cô lập qua 11 spec E2E (`four-roles-audit`, `workflow-clarity`, `mobile-layout`, `account-roster`, `positions`, `school-forms`, `admin-pagination`, `staff-email`, `student-activation-selection`, `ai-workspace`, `qa-contracts-and-rbac`).
- **Đồng bộ selector & mô phỏng có kiểm soát:** Các đồng bộ E2E (`four-roles-audit.spec.ts`, `nv5-completion.spec.ts`, `withdrawals.spec.ts`, `student-withdrawal-demo.spec.ts`, `school-form-create-upload.spec.ts`) giữ nguyên toàn bộ khẳng định nghiệp vụ; các mô phỏng `page.route()` có kiểm soát trong `ai-workspace.spec.ts` và `qa-contracts-and-rbac.spec.ts` cùng 7 phát hiện backend cần phê duyệt riêng được liệt kê đầy đủ trong [`QA_TRACEABILITY_MATRIX.md`](file:///d:/KLTN/docs/ui-redesign/QA_TRACEABILITY_MATRIX.md).

---

## 3. Danh mục Ảnh chụp Bằng chứng (`12` BEFORE vs `23` V3 AFTER)

- **Ảnh BEFORE (`12` tệp giữ nguyên nguyên trạng tại `d:\KLTN\docs\evidence\screenshots\before\`):**  
  `head-dashboard-1440.png`, `head-defense-1440.png`, `head-defense-390.png`, `lecturer-account-1440.png`, `lecturer-evaluation-1440.png`, `login-1440.png`, `login-390.png`, `student-dashboard-1440.png`, `student-dashboard-390.png`, `student-forms-1440.png`, `student-registrations-1440.png`, `student-topics-1440.png`.
- **Ảnh AFTER V3 (`23` tệp làm mới sau chỉnh sửa cuối cùng tại `d:\KLTN\docs\evidence\screenshots\`):**  
  `ai-workspace-1440.png`, `archive-1440.png`, `head-dashboard-1440.png`, `head-defense-1440.png`, `head-defense-390.png`, `lecturer-account-1440.png`, `lecturer-dashboard-1440.png`, `lecturer-evaluation-1440.png`, `login-1440.png`, `login-390.png`, `reports-1440.png`, `student-dashboard-1920.png`, `student-dashboard-1440.png`, `student-dashboard-844x390.png`, `student-dashboard-390.png`, `student-dashboard-320.png`, `student-drawer-390.png`, `student-forms-1440.png`, `student-registrations-1440.png`, `student-topics-1440.png`, `thesis-workspace-1440.png`, `topic-drawer-1440.png`, `topic-drawer-390.png`.
