# Đăng nhập bằng tài khoản Trường

## Luồng hệ thống

1. Người dùng bấm **Đăng nhập bằng tài khoản Trường** trên giao diện.
2. Backend chuyển trình duyệt tới nhà cung cấp OIDC của Trường theo Authorization Code Flow.
3. Nhà cung cấp trả trình duyệt về callback HTTPS đã đăng ký. Backend dùng Authlib kiểm tra `state`, chữ ký và các claim OIDC của ID token.
4. Backend dùng claim `sub` tra `user_account.external_subject`, chỉ nhận tài khoản đang `ACTIVE`, rồi tạo session cookie `HttpOnly` có chữ ký.
5. Mọi quyền và hồ sơ SV/GV vẫn lấy từ PostgreSQL. Không lấy role từ form, không nhận UUID do người dùng nhập, không tự tạo account nếu chưa được liên kết.

`sub` là mã định danh do nhà cung cấp cấp. Quản trị phải liên kết `external_subject` của từng tài khoản KLTN tới đúng `sub` qua quy trình nội bộ được duyệt; không dùng email làm khóa thay thế vì email có thể đổi hoặc không duy nhất. Bản ghi thử nghiệm hiện có không tự được biến thành danh tính thật.

## Việc bộ phận CNTT của Trường cần cấp

- Xác nhận hệ thống đăng nhập hỗ trợ **OpenID Connect (OIDC)**. Nếu Trường chỉ cấp SAML/CAS thì cần adapter phù hợp, không thể điền cấu hình OIDC để thay thế.
- Discovery URL của môi trường tích hợp và production.
- Client ID, phương thức client authentication và client secret cho backend confidential client.
- Claim `sub` ổn định, quy tắc cấp `sub` giữa hai môi trường, và cách đối chiếu `sub` với mã SV/mã giảng viên để liên kết tài khoản đúng người.
- Redirect URI được đăng ký; production phải dùng HTTPS.
- Kiểm thử logout/session lifetime và chính sách MFA nếu có.

## Cấu hình môi trường

Cài phần mở rộng xác thực trong môi trường backend:

```powershell
python -m pip install -e ".[sso]"
```

Thiết lập các biến môi trường từ cấu hình được Trường cấp; không commit secret:

```text
KLTN_ENV=production
KLTN_DEV_AUTH=false
AUTH_SESSION_SECRET=<chuỗi ngẫu nhiên dài do môi trường vận hành quản lý>
OIDC_DISCOVERY_URL=<discovery URL>
OIDC_CLIENT_ID=<client ID>
OIDC_CLIENT_SECRET=<client secret>
OIDC_TOKEN_ENDPOINT_AUTH_METHOD=client_secret_basic
OIDC_REDIRECT_URI=https://<tên-miền-backend>/api/v1/auth/callback
OIDC_SCOPE=openid
KLTN_FRONTEND_URL=https://<tên-miền-giao-diện>
```

`AUTH_SESSION_SECRET` cần được lưu trong secret manager của môi trường, giữ ổn định qua lần khởi động và luân chuyển theo chính sách vận hành. Không ghi vào Git, log, ảnh chụp hay gửi trong hội thoại. Cookie phiên có cờ `HttpOnly`, `SameSite=Lax`, và `Secure` khi chạy production.

## Trạng thái kiểm chứng

Mã nguồn có callback OIDC tổng quát, liên kết account bằng `sub`, session cookie và chế độ DEV/TEST riêng. Chưa thể xác nhận đăng nhập thực tế cho đến khi có IdP của Trường, client đã đăng ký, account được liên kết đúng và kiểm thử end-to-end trên môi trường HTTPS. Khi chưa cấu hình, production không nhận UUID header và đăng nhập báo chưa sẵn sàng.
