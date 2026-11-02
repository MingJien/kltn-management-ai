# Hồ sơ giảng viên và duyệt cập nhật

Triển khai và kiểm chứng ngày **02/11/2026** trên nhánh `NV6`.

## Sản phẩm và cách dùng

- **Danh sách giảng viên**: bảng danh bạ có ảnh mặc định/ảnh đã duyệt, mã GV, bộ môn/Khoa, trình độ, chuyên môn, trạng thái hồ sơ và cột xem chi tiết. Tìm kiếm có hoặc không dấu, lọc bộ môn, phân trang 20 dòng. Người dùng đăng nhập tra cứu GV đang hoạt động; ADMIN xem thêm trạng thái tài khoản và email đăng nhập, sửa định danh theo căn cứ. Nhập Excel/kích hoạt giữ ở tab riêng, liên kết sang quản lý tài khoản cho thao tác mời, sửa email, khóa/mở tài khoản.
- **Tài khoản của tôi → Thông tin chuyên môn và ảnh đại diện**: GV tạo bản nháp, nhập học hàm, học vị, chức danh nghề nghiệp, giới thiệu, chuyên môn, hướng nghiên cứu, quá trình đào tạo/kinh nghiệm, email liên hệ, số điện thoại và lựa chọn công khai, phòng làm việc, giờ tiếp sinh viên và website. Mã GV, bộ môn, email đăng nhập và chức vụ/phân quyền do hệ thống quản lý riêng. Các trường chưa có được ghi rõ chưa cập nhật, không tự tạo thông tin.
- **Ảnh**: ảnh mặc định là biểu tượng người dùng. GV tải JPEG/PNG/WebP tĩnh tối đa 5 MB, 20 megapixel; backend kiểm nội dung thật, xoay theo EXIF, cắt vuông giữa ảnh và chuẩn hóa PNG 512×512, loại metadata. ClamAV quét trước khi cho gửi/duyệt/xem. SVG, ảnh động, ảnh lỗi hoặc vượt giới hạn bị chặn. Ảnh nháp riêng và chỉ công bố cùng hồ sơ được duyệt; có chọn trở về ảnh mặc định. Ảnh đã duyệt đồng bộ vào danh bạ, trang hồ sơ và góc tài khoản/sidebar của GV.
- **Gửi duyệt**: một GV có tối đa một nháp/yêu cầu đang chờ. Nháp riêng được lưu trên máy chủ, nội dung chưa bấm lưu được giữ tạm trong tab để tránh mất khi điều hướng. Khi gửi phải nêu nội dung/căn cứ đề nghị; hồ sơ đã công bố giữ nguyên. Thông báo tới TBM đang có thẩm quyền; với hồ sơ TBM hoặc khi không có TBM khác, gửi Trưởng khoa đúng Khoa. Không có người duyệt hợp lệ thì báo ADMIN kiểm tra chức vụ, không tự cho ADMIN duyệt nghiệp vụ.
- **Duyệt hồ sơ giảng viên**: danh sách chờ, lịch sử, tìm kiếm/phân trang và đường dẫn trực tiếp từ thông báo. So sánh trước–sau theo từng trường và ảnh; duyệt cần ghi căn cứ và xác nhận đã đối chiếu. Có trả lại kèm nội dung cần bổ sung, GV nhận thông báo và tạo phiên bản sửa từ nội dung bị trả lại. Rút yêu cầu giữ lịch sử. Đã gửi/đã xử lý không sửa đè. Kiểm phiên bản hồ sơ gốc và khóa khi ghi để tránh duyệt dữ liệu cũ. Không tự duyệt, kể cả TBM; Trưởng khoa có thể xử lý hồ sơ của TBM đúng Khoa.
- **Xem nhanh**: tên GV ở đề tài, đăng ký, GVHD và phân công phản biện mở hộp thoại hồ sơ. Bấm ngoài hoặc Esc đóng, giữ nguyên trang hiện tại. Giữ link mở tab riêng khi Ctrl/Command-click. Từ đề tài có thể mở hồ sơ trong hộp thoại chi tiết mà Esc chỉ đóng cửa sổ trên cùng. Danh bạ có nút xem toàn bộ thông tin ngoài các cột bảng. Link trực tiếp `/lecturers/{id}` vẫn hoạt động.

## Phân quyền và dữ liệu

Hồ sơ công bố không chứa email đăng nhập hay điện thoại GV không đồng ý công khai. Nháp/ảnh nháp chỉ chủ hồ sơ được đọc; sau gửi, người duyệt theo chức vụ và phạm vi mới đọc được. Thông báo kiểm lại quyền hiện hành, không cấp quyền nhờ biết đường dẫn. Nhật ký gửi/duyệt/trả lại/rút và sửa định danh được ghi. Cập nhật học hàm/chức danh không làm thay đổi chức vụ hoặc quyền nghiệp vụ. Sửa bộ môn bị chặn nếu GV đã có liên kết nghiệp vụ, cần quy trình điều chuyển thay vì thay quyền ngầm.

Schema nâng qua Alembic `20261102_0018`: **42 bảng nghiệp vụ**, thêm `lecturer_profile_change` và thuộc tính hồ sơ trên `lecturer_profile`. Không chạy lại SQL init. Tệp ảnh thật ở kho local bị Git bỏ qua; mã nguồn, migration và kiểm thử dùng dữ liệu giả.

## Kiểm chứng

- `tests/test_lecturer_profiles.py`: 18 ca kiểm thử đạt trên PostgreSQL schema riêng, gồm nháp riêng, duyệt/công bố, trả lại/rút, phạm vi chức vụ hết hiệu lực, chống tự duyệt, Trưởng khoa xử lý TBM, dữ liệu cũ, ảnh cách ly/chỉ công bố sau duyệt, ảnh không hợp lệ/vượt dung lượng, trường sai định dạng, tìm không dấu và bảo vệ thông tin liên hệ. Các ca dịch vụ này mô phỏng máy quét không khả dụng rồi đặt trạng thái có chủ đích để kiểm nhánh nghiệp vụ; không tuyên bố đó là bằng chứng quét thật.
- `frontend/e2e/lecturer-profiles.spec.ts`: luồng đăng nhập GV/TBM/SV/ADMIN, sửa thông tin/ảnh, nháp riêng, thông báo, trả lại–gửi lại–duyệt, công bố ảnh, bảo vệ số điện thoại/email đăng nhập, danh bạ/xem nhanh từ đề tài/bấm ngoài/Esc và đồng bộ tên GV đạt trên Chromium, API, PostgreSQL và **ClamAV thật**. Dùng ảnh canvas và tài khoản giả; không mock route.
- Kiểm tra mobile 390×844: không cuộn ngang; axe WCAG 2 A/AA và 2.1 AA không báo vi phạm trong vùng hồ sơ được kiểm. Đã xem ảnh render giao diện desktop và mobile; ảnh thao tác chỉ giữ trong `tmp/`.
- TypeScript và production frontend build đạt; Vite còn cảnh báo bundle xem tài liệu dùng chung lớn. OpenAPI được sinh lại, kiểm khớp route; SQL snapshot/từ điển/ERD cập nhật theo metadata. Schema drift kiểm đạt: 112 FK, 96 CHECK, 35 UNIQUE, 28 index tường minh.

Lượt chạy gộp hồ sơ GV và NV6 đạt **4/4 kịch bản UI**. Bộ backend trong workspace local đạt **206/206** (bao gồm kiểm thử của các thay đổi local đã có trước tác vụ); không coi đây là xác nhận các thay đổi local đó đã được commit cùng hồ sơ GV.

Đã kiểm riêng bản source đúng nội dung stage (tách khỏi sửa local khác): **26/26** kiểm thử hồ sơ/schema/OpenAPI đạt, frontend build đạt và **1/1** kịch bản hồ sơ GV qua API/PostgreSQL/ClamAV thật đạt. OpenAPI giao GitHub được sinh từ chính bản source này để không lẫn endpoint local ngoài tác vụ.

Lệnh tái kiểm:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m tools.validate_official_database
.\.venv\Scripts\python.exe -m pytest tests/test_lecturer_profiles.py -q
npm run build --prefix frontend
$env:KLTN_E2E_ALLOW_ISOLATED_SCHEMA='true'
.\.venv\Scripts\python.exe -m tools.run_e2e lecturer-profiles.spec.ts nv6-evaluation.spec.ts
```

Phạm vi kiểm chứng này dành cho hồ sơ GV và hồi quy NV6 liên quan, không thay kết quả/giới hạn bộ UI cũ tại [minh chứng NV6 tuần 1](nv6-week1-validation.md). Không đọc ChatGPT Project hoặc Google Drive cho tác vụ này.
