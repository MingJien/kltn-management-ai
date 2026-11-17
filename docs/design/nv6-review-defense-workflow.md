# Phản biện và điều kiện dự bảo vệ NV6 tuần 1

Phạm vi đã triển khai: giao và thu hồi phản biện, gia hạn gửi nhận xét, phiếu GVHD theo Mẫu 7, phiếu GVPB theo Mẫu 8, xét điều kiện cấp Trường cho từng sinh viên, thông báo và lịch sử quyết định. Mục vào UI: **Bảo vệ và đánh giá → Phản biện & điều kiện bảo vệ** (`/evaluation`). Hội đồng, lịch bảo vệ, điểm, biên bản, kho lưu trữ và chức năng AI tiếp theo nằm ngoài phần này.

## Quy trình bàn giao

1. Sau khi GV tiếp nhận đăng ký, khóa luận có nhóm và GVHD chính thức. Người điều phối đặt hạn loại `REPORT`; SV nộp Cuốn báo cáo KLTN tại Hồ sơ nộp & xét duyệt. Hệ thống giữ phiên bản và chỉ cho dùng tệp đã quét an toàn.
2. TBM mở hồ sơ NV6, chọn GV cùng bộ môn đang hoạt động, nhập hạn, lý do và căn cứ phân công. GVHD không nằm trong lựa chọn; tối đa hai phân công phản biện đang hiệu lực. Danh sách hiển thị khối lượng phân công hiện tại để người có thẩm quyền cân nhắc, không tự chọn GV.
3. GVPB nhận thông báo và đọc đúng cuốn báo cáo. GVHD lập Mẫu 7, GVPB lập Mẫu 8. Mỗi sinh viên có phiếu riêng gắn với phân công và bản báo cáo. Lưu nháp trên máy chủ để tiếp tục; TBM, sinh viên và người phản biện khác không xem được nháp.
4. Điền đủ nội dung và lưu nháp. GV tự kiểm tra đúng SV/bản báo cáo, tích xác nhận nội dung do mình lập và gửi trên hệ thống. Không cần xuất để ký, không tải bản ký lên và không tiếp nhận giấy. Người lập và thời điểm gửi được giữ; phiếu đã gửi muốn sửa phải tạo phiên bản mới kèm lý do.
5. Sau khi gửi, có thể tải phiếu DOCX điền từ mẫu của Khoa khi cần đối chiếu. Đây là thao tác tùy chọn, không tạo thêm điều kiện bảo vệ. Bản ký cũ đã lưu vẫn chỉ đọc theo quyền; các API tạo bản ký/biên nhận giấy đã bỏ.
6. TBM chọn từng SV, đối chiếu tình trạng kỷ luật, nhập căn cứ/số văn bản và lý do rồi lưu xét điều kiện. Ba căn cứ là: không bị kỷ luật từ cảnh cáo toàn Trường; hoàn thành KLTN do GVHD xác nhận theo đúng bản báo cáo; GVHD xác nhận đồng ý cho bảo vệ qua Mẫu 7 đã gửi trên tài khoản được phân công. Hệ thống tính kết quả, không có nút bỏ qua điều kiện. Ba căn cứ cấp Trường vẫn được xét riêng. Trước khi xếp lịch, hệ thống còn yêu cầu hoàn tất các Mẫu 8 đã phân công: hai phản biện thì đủ cả hai, mỗi người cho từng SV trên bản báo cáo hiện tại. TBM thu hồi phân công không còn áp dụng phải ghi lý do.
7. Khóa luận nhóm chỉ chuyển `READY_FOR_DEFENSE` khi mọi thành viên đều được xét đủ điều kiện. Kết quả và văn bản của một SV không áp dụng cho thành viên khác. TBM có thể mở xét lại kèm lý do, giữ kết quả cũ trong lịch sử; hồ sơ trở lại `IN_PROGRESS` để bổ sung rồi xét lại. GVPB vẫn được hoàn thiện nhận xét khi điều kiện cấp Trường đã chốt.

## Quyền và dữ liệu riêng tư

| Người dùng | Phạm vi |
| --- | --- |
| TBM đang giữ chức vụ | Phân công, gia hạn, thu hồi và xét điều kiện trong đúng bộ môn; chỉ xem phiếu đã gửi của người khác |
| GVHD hiệu lực | Viết Mẫu 7 của mình; xem phiếu đã gửi và căn cứ xét trong hồ sơ phụ trách |
| GVPB đang được phân công | Đọc cuốn báo cáo, viết/xem phiếu của mình; không xem tiến độ, tài liệu riêng khác, phiếu của GVPB khác hay căn cứ kỷ luật cá nhân |
| SV thành viên | Đọc cuốn báo cáo chung, nhận xét đã gửi và kết quả/lịch sử xét của chính mình |
| ADMIN hoặc tài khoản ngoài phạm vi | Không mặc nhiên được đọc hoặc duyệt hồ sơ NV6 |

Thu hồi phân công mất quyền mở hồ sơ và tải tệp ngay ở API, kể cả từ liên kết cũ. Phiếu đã gửi vẫn giữ cho người có quyền đọc lịch sử. Tài khoản bị thu hồi nhận thông báo thu hồi riêng, các thông báo dẫn tới nội dung không còn quyền xem bị lọc lại. Nhật ký xét điều kiện cá nhân không lộ cho thành viên nhóm khác.

## Xử lý tình huống

- Phân công trùng, quá hai GVPB hoặc GVHD tự phản biện: chặn trước khi ghi. Cùng một khóa luận được khóa khi ghi để chống hai người phân công đồng thời vượt giới hạn.
- Màn hình cũ: API từ chối `409`; người dùng tải dữ liệu hiện hành trước khi thao tác tiếp. Không tự ghi đè phiếu đã gửi.
- Hết hạn phản biện: đánh dấu quá hạn, vẫn nhận và giữ thời điểm gửi. Gia hạn cần lý do và căn cứ; không thay đổi thời điểm đã gửi.
- Báo cáo hoặc Mẫu 7 mới: kết quả xét gắn bản cũ chuyển thành cần xét lại khi đọc. TBM và GVPB nhận thông báo báo cáo mới; thông báo nộp của nhóm/GVHD dùng luồng tài liệu hiện có.
- Tệp bị thay đổi sau khi lưu: tải xuống đối chiếu kích thước và SHA-256, từ chối khi không khớp.

## Xử lý yêu cầu xin thôi và bàn giao bảo vệ

Xem [hướng dẫn NV6 tuần 2](nv6-defense-operations.md) cho luồng xin thôi trên hệ thống, thay đổi thành viên, hội đồng và kết quả.

## Cài đặt và kiểm chứng hiện hành

Dùng Alembic để nâng database hiện có lên `20261104_0021`; không chạy lại SQL init. Máy chủ cần PostgreSQL, ClamAV và hai mẫu DOCX chính thức do Khoa cung cấp (qua kho theo đợt hoặc `KLTN_OFFICIAL_TEMPLATE_DIR`). Mẫu nguồn, bản ký, tệp SV và cấu hình thật không thuộc repository. Xác nhận nhận xét hiện thực hiện bằng tài khoản có phân công, không phải chữ ký số bằng chứng thư.

Kết quả chạy thật, lệnh tái kiểm và giới hạn kiểm chứng được ghi tại [minh chứng NV6](../evidence/nv6-week1-validation.md).

Tái kiểm luồng thay đổi nhóm: [minh chứng tích hợp](../evidence/nv6-group-review-validation.md).
