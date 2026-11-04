# Phản biện và điều kiện dự bảo vệ NV6 tuần 1

Phạm vi đã triển khai: giao và thu hồi phản biện, gia hạn gửi nhận xét, phiếu GVHD theo Mẫu 7, phiếu GVPB theo Mẫu 8, xét điều kiện cấp Trường cho từng sinh viên, thông báo và lịch sử quyết định. Mục vào UI: **Bảo vệ và đánh giá → Phản biện & điều kiện bảo vệ** (`/evaluation`). Hội đồng, lịch bảo vệ, điểm, biên bản, kho lưu trữ và chức năng AI tiếp theo nằm ngoài phần này.

## Quy trình bàn giao

1. Sau khi GV tiếp nhận đăng ký, khóa luận có nhóm và GVHD chính thức. Người điều phối đặt hạn loại `REPORT`; SV nộp Cuốn báo cáo KLTN tại Hồ sơ nộp & xét duyệt. Hệ thống giữ phiên bản và chỉ cho dùng tệp đã quét an toàn.
2. TBM mở hồ sơ NV6, chọn GV cùng bộ môn đang hoạt động, nhập hạn, lý do và căn cứ phân công. GVHD không nằm trong lựa chọn; tối đa hai phân công phản biện đang hiệu lực. Danh sách hiển thị khối lượng phân công hiện tại để người có thẩm quyền cân nhắc, không tự chọn GV.
3. GVPB nhận thông báo và đọc đúng cuốn báo cáo. GVHD lập Mẫu 7, GVPB lập Mẫu 8. Mỗi sinh viên có phiếu riêng gắn với phân công và bản báo cáo. Lưu nháp trên máy chủ để tiếp tục; TBM, sinh viên và người phản biện khác không xem được nháp.
4. Điền đủ các mục, lưu nháp rồi chọn **Xuất phiếu đã điền để ký**. Bản xuất dùng mẫu DOCX đã phát hành trong kho của đợt, hoặc mẫu gốc được cấp trên máy chủ khi chưa có danh mục quản lý. Nếu Khoa thay cấu trúc mẫu không còn khớp ánh xạ, hệ thống báo cần cập nhật và cho tải mẫu để điền theo quy trình, không tự dựng mẫu khác. Ngày ký để trống; footer ghi mã phiếu, bản báo cáo, thời điểm xuất và trạng thái bản để ký. Đây không phải chữ ký điện tử.
5. GV kiểm tra bản xuất, ký ngoài hệ thống và tải PDF/DOCX đã ký (tối đa 10 MB). Tệp chưa quét sạch bị chặn gửi và tải. Chỉ khi GV xác nhận bản đính kèm đã ký, khớp nội dung rồi bấm gửi, phiếu mới công bố cho đúng người. Sửa nội dung nháp làm gỡ liên kết bản ký cũ để tránh gửi nhầm; phiếu đã gửi phải lập phiên bản mới kèm lý do.
6. TBM chọn từng SV, đối chiếu tình trạng kỷ luật, nhập căn cứ/số văn bản và lý do rồi lưu xét điều kiện. Ba căn cứ là: không bị kỷ luật từ cảnh cáo toàn Trường; hoàn thành KLTN do GVHD xác nhận theo đúng bản báo cáo; GVHD đồng ý cho bảo vệ bằng văn bản đã ký. Hệ thống tính kết quả, không có nút bỏ qua điều kiện. Phản biện và tương đồng không tự trở thành điều kiện bổ sung.
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

## Một sinh viên xin rút sau khi đề cương đã duyệt

**Thành viên còn lại tiếp tục đề tài cũ và GVHD cũ, cập nhật đề cương mới để phê duyệt lại. Không buộc chọn đề tài khác vì số thành viên giảm.** Bản đề cương cũ và các xác nhận đã có được giữ làm lịch sử, không áp dụng cho nhóm mới.

| Vai trò | Thao tác trên UI | Kết quả |
| --- | --- | --- |
| ADMIN, khi cần thiết lập ban đầu | Quản trị hệ thống → Phân công theo đợt → giao Điều phối KLTN, có căn cứ | Tài khoản được giao mới ghi nhận kế hoạch và kết quả xin rút; TBM không tự có quyền điều phối nếu chưa được giao |
| Điều phối đúng đợt | Đề tài và đăng ký → Xin thôi KLTN → Ngày bắt đầu theo kế hoạch Khoa | Ghi ngày bắt đầu và căn cứ; hệ thống tính 14 ngày theo giờ Việt Nam, gồm ngày bắt đầu. Có đơn rồi không sửa ngày để thay đổi hạn của hồ sơ |
| SV xin rút | Xin thôi KLTN → Lập yêu cầu → nhập lý do và xác nhận hệ quả → Gửi đơn đến GVHD | Chỉ gửi đơn cá nhân; nhóm và quyền tham gia chưa thay đổi. Có thể hủy trước khi GVHD xác nhận |
| GVHD chính | Mở thông báo hoặc Xin thôi KLTN → xem đơn → xác nhận hoặc trả lại, kèm ý kiến | Xác nhận trên hệ thống chưa phải quyết định cho thôi; SV thực hiện đơn và ký theo hướng dẫn Khoa. Chức năng xuất mẫu đang chờ Khoa duyệt |
| Điều phối đúng đợt | Mở đơn → Ghi nhận hồ sơ đã được tiếp nhận → nhập ngày, đơn vị, số hoặc căn cứ tiếp nhận | Ghi nhận tiếp nhận thực tế; có thể cập nhật và giữ lịch sử. Không tự cho thôi và không thay quyết định của đơn vị có thẩm quyền |
| Điều phối đúng đợt | Mở đơn → đối chiếu bản có xác nhận đã quét sạch → Ghi nhận kết quả đã xử lý bên ngoài → nhập căn cứ, ngày và nội dung, tích xác nhận | Chỉ kết quả cho thôi đã ghi nhận mới ngừng quyền thành viên; không chấp thuận thì SV tiếp tục. Có kiểm phiên bản và ghi lịch sử |
| Thành viên còn lại | Mở thông báo thay đổi nhóm → Mở đề cương để cập nhật / duyệt lại → nộp PDF/DOCX mới | Giữ mã khóa luận, đề tài, GVHD; chuyển người đại diện nếu cần. Cập nhật danh sách SV, phạm vi và phân công trong nội dung mới |
| GVHD và TBM | Hồ sơ nộp & xét duyệt → Đề cương → GVHD xem tệp và xác nhận bản mới → TBM chốt | Mỗi xác nhận gắn đúng phiên bản. Không có thao tác xác nhận lại bản cũ thay cho nộp mới |
| Thành viên còn lại | Cập nhật Cuốn báo cáo KLTN trong cùng hồ sơ | Nếu đã có bản cũ, hệ thống mở một lần nộp sửa kể cả khi bản cũ đã tiếp nhận hoặc hạn đã đóng; không tạo hồ sơ tài liệu thứ hai |
| GVHD/GVPB, rồi TBM | Phản biện & điều kiện bảo vệ → lập phiếu theo bản báo cáo mới → xét điều kiện SV còn thực hiện | Tạm chặn lập/gửi phiếu và lưu xét điều kiện trong lúc thiếu đề cương được duyệt lại hoặc báo cáo cập nhật. Kết quả cũ chuyển cần xét lại, không bị xóa |

Khi nhóm không còn thành viên, khóa luận chuyển Đã rút, đăng ký chuyển Đã hủy, phân công nhận xét kết thúc. Người đã rút vẫn xem đơn của mình nhưng mất quyền hồ sơ nhóm; thành viên còn lại và GVPB không đọc được đơn/lý do riêng của người xin rút.

Thông báo ở biểu tượng chuông và trang **Thông báo**, có liên kết đến đúng đơn/hồ sơ; chỉ tài khoản còn quyền mới mở được nội dung. Đây là thông báo trong tài khoản, không phải email hay lời nhắc được lập lịch. Mẫu xin thôi đang chờ Khoa duyệt nên hệ thống chưa cho xuất phiếu; nội dung đề xuất tại [mẫu xin thôi](withdrawal-form-proposal.md).

Nếu không có nút thao tác: kiểm tra phân công còn hiệu lực, ngày bắt đầu, thời hạn, quyền của tài khoản và trạng thái hồ sơ. Hồ sơ đã chốt đủ điều kiện phải được TBM **Mở xét lại hồ sơ** trước khi xử lý thay đổi nhóm. Quá 02 tuần đầu thì UI hướng dẫn liên hệ đơn vị phụ trách, không tự hủy đăng ký, đổi điểm hoặc tự tạo ngoại lệ hành chính. Việc ghi nhận kết quả dựa trên hồ sơ đã được đơn vị có thẩm quyền xử lý bên ngoài.

## Cài đặt và kiểm chứng hiện hành

Dùng Alembic để nâng database hiện có lên `20261102_0019`; không chạy lại SQL init. Máy chủ cần PostgreSQL, ClamAV và hai mẫu DOCX chính thức do Khoa cung cấp (qua kho theo đợt hoặc `KLTN_OFFICIAL_TEMPLATE_DIR`). Mẫu nguồn, bản ký, tệp SV và cấu hình thật không thuộc repository. Hệ thống chưa xác thực chữ ký bằng chứng thư số; GV xác nhận bản đã ký theo quy trình ngoài hệ thống.

Kết quả chạy thật, lệnh tái kiểm và giới hạn kiểm chứng được ghi tại [minh chứng NV6](../evidence/nv6-week1-validation.md).

Tái kiểm luồng thay đổi nhóm: [minh chứng tích hợp](../evidence/nv6-group-review-validation.md).
