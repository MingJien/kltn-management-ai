# Liên kết tới công cụ bên ngoài

Nguồn SRC-PROJECT-DEC-20260925. Hiện chưa có địa chỉ công cụ bên ngoài được duyệt, nên giao diện chưa hiển thị nút cụ thể.

`ExternalResourceProvider` là cấu hình phía server gồm `id`, `label`, `https_url`, `enabled`, `scope`, `source_ref`. API `GET /api/v1/external-resources` chỉ trả các mục được duyệt theo quyền; client mở URL nguyên gốc trong tab mới bằng `target="_blank" rel="noopener noreferrer"`. Server không nhận URL tùy ý từ người dùng, không có endpoint chuyển hướng `?next=...`. URL phải dùng HTTPS và host trong allowlist cấu hình; thay đổi URL cần review. Không iframe, scrape, copy dữ liệu hoặc tự gửi hồ sơ KLTN sang website ngoài khi chưa có hợp đồng/API và quyền dữ liệu. Không cần bảng CSDL mới khi danh mục ít và do vận hành cấu hình.
