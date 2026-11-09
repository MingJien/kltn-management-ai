# Rà soát UI và luồng hội đồng, bảo vệ ngày 09/11/2026

## Phạm vi và cách kiểm chứng

Rà mã phân hệ `/defense`, quyền truy cập báo cáo, tính điểm và xuất Mẫu 6/9/10/11. Kiểm thử trình duyệt dùng ứng dụng React thực tế với phản hồi API giả lập: một hội đồng năm người, hai sinh viên, vai trò thư ký, đủ 12 tiêu chí chấm. Không dùng tài khoản hoặc hồ sơ sinh viên thật.

Đã chạy lại:

- `.venv/Scripts/python.exe -m pytest tests/test_nv6_defense.py tests/test_nv6_evaluation.py -q --tb=short`: **23 passed**, có 6 cảnh báo thư viện/cấu hình. Các bài kiểm thử dùng schema PostgreSQL riêng.
- Ca trình duyệt local `local/defense-ui-audit.mjs`: tái hiện mất dữ liệu nháp, sai tổng điểm dự kiến và tìm kiếm theo MSSV không có kết quả. Script, kết quả JSON và ảnh chỉ giữ local, không đưa lên Git.
- Sau khi đợi hiệu ứng chuyển bố cục hoàn tất, không thấy tràn ngang ở 320/390/768/1024/1440 px. Axe WCAG 2A/2AA/2.1AA trên vùng `.defense-page` không báo vi phạm trong ca có dữ liệu này. Điều đó không thay thế kiểm thử bàn phím, trình đọc màn hình và toàn bộ phân hệ.
- Chưa chạy ca trình duyệt nối API thật đi hết buổi chấm, ca nhiều trình duyệt chấm đồng thời, hoặc đối chiếu bản in từng trang với mẫu Khoa. Các rủi ro liên quan được nhận diện từ mã, không ghi nhận là đã tái hiện end-to-end.

## Các điểm đã có nền tảng

Phân quyền theo vai trò hội đồng và phạm vi quản lý; hội đồng mới đúng năm người khác nhau; điểm danh đủ thành phần; kiểm tra điều kiện trên bản báo cáo hiện tại; ngăn trùng lịch theo phòng/giảng viên; không cho GVHD chấm đề tài mình; ngăn chấm sinh viên/người chấm vắng; giới hạn điểm; kiểm tra phiếu còn thiếu; chốt kết quả có snapshot; sửa bản chưa ký với lý do; xuất có mã phiên bản.

Các điểm này có mã và kiểm thử API nhưng chưa đủ để kết luận toàn bộ trải nghiệm đã sẵn sàng bàn giao.

## Phát hiện cần ưu tiên

### UI-01 — Mất dữ liệu đang soạn khi lưu thao tác khác (cao, đã tái hiện)

Nhập điểm tiêu chí và nội dung hai ô biên bản, chưa lưu. Bấm **Lưu điểm danh** của sinh viên thứ nhất. Sau phản hồi thành công, toàn bộ điểm đang nhập và hai ô biên bản trở thành rỗng; phần phiếu chấm tự đóng.

Nguyên nhân: `DefensePage.tsx` tải lại workspace sau mutation và dùng `key={slot.id+":"+slot.version}`, khiến React dựng lại toàn bộ cây biểu mẫu của phiên. Nhánh lỗi cũng tải lại dữ liệu. Điều này có thể ảnh hưởng khi có xung đột phiên bản.

Đề xuất: giữ định danh component ổn định; quản lý nháp riêng theo phiên/sinh viên/người chấm; chỉ cập nhật biểu mẫu vừa lưu; giữ nội dung khi gặp lỗi hoặc tải lại; cảnh báo khi đổi trang/người chấm nếu còn nội dung chưa lưu. Không chỉ bỏ `version` khỏi key vì các input `defaultValue` cũng cần được đồng bộ có kiểm soát.

### UI-02 — Tổng điểm dự kiến có thể khác tổng backend (cao, đã tái hiện)

Bộ điểm theo thứ tự 12 tiêu chí: `0.27, 0.01, 0.31, 0.10, 0.40, 0.73, 0.62, 0.28, 0.07, 0.29, 0.70, 0.07`; thưởng 0. Tổng chính xác là **3,85**, làm tròn một chữ số là **3,9**. UI hiện **3,8** vì cộng số thực JavaScript được `3.849999999999999`; backend dùng Decimal và ROUND_HALF_UP.

Đề xuất: tính trên số nguyên đơn vị 0,01 điểm hoặc thư viện decimal và áp dụng cùng quy tắc backend. Phân biệt tổng đang nhập với tổng đã lưu, hiển thị số tiêu chí còn thiếu thay vì làm người dùng hiểu các ô trống là điểm 0.

### FLOW-03 — Nhiều giảng viên chấm chung phiên dễ gặp xung đột (cao, phân tích mã)

Mọi thay đổi điểm danh, thưởng, biên bản và tất cả phiếu dùng chung `slot.row_version`. Hai giảng viên mở cùng phiên bản; người đầu lưu làm phiên bản tăng, người sau lưu sẽ bị 409 dù sửa hai phiếu khác nhau. UI hiện tải lại sau lỗi và có thể mất nháp như UI-01. Kiểm thử API hiện tuần tự lấy phiên bản mới trước mỗi mutation nên chưa kiểm tình huống này.

Đề xuất: kiểm soát phiên bản theo từng phiếu cho thao tác độc lập, vẫn khóa phiên khi chốt. Khi hai người sửa cùng phiếu, giữ nháp và hiển thị phiên bản đã thay đổi để đối chiếu; không ghi đè hoặc tự gửi lại âm thầm. Tách thông báo "đã lưu nhưng chưa tải lại được" khỏi "lưu thất bại".

### FLOW-04 — Chưa in được phiếu chấm trước khi chốt (cao, UI và mã)

Nút tải Mẫu 6 chỉ xuất hiện sau chốt, API cũng chặn mọi bản xuất phiên trước chốt. Luồng này chưa đáp ứng việc thư ký in phiếu để hội đồng chấm giấy ngoài buổi họp khi không dùng mạng.

Đề xuất: có **In phiếu chấm trống** trước buổi bảo vệ, tự điền SV/đề tài/người chấm và ghi rõ là phiếu chưa có kết quả; có bản xem trước riêng. Bản kết quả dùng ký vẫn chỉ xuất từ dữ liệu đã chốt, có mã phiên bản.

### FLOW-05 — Thiếu đường vào báo cáo dành cho thành viên hội đồng (cao, phân tích mã)

Trang bảo vệ chưa có nút mở báo cáo. Endpoint tải báo cáo của phân hệ phản biện kiểm quyền GVHD/TBM/phản biện trước hội đồng; thành viên chỉ được phân công vào hội đồng không tự có quyền đó.

Đề xuất: nút **Xem báo cáo dùng để bảo vệ** trên từng phiên, kiểm quyền hội đồng tại server và tải đúng `report_version_id` đã gắn lịch. Không mở rộng quyền đọc hồ sơ khác. Hiện rõ khi bản báo cáo hoặc điều kiện bảo vệ thay đổi và hướng dẫn người quản lý xử lý trước buổi họp.

## Các khoảng trống nghiệp vụ và sửa sai

Các mục sau nhận diện từ mã, chưa tái hiện trình duyệt nối API thật:

- **Nhập nhầm rồi điểm danh vắng:** hiện không cho chuyển SV/người chấm thành vắng nếu đã có phiếu, nhưng chưa có thao tác hủy phiếu nhập nhầm. Cần thao tác có thẩm quyền trước chốt, lý do và lưu phiên bản cũ; không xóa lịch sử.
- **Điểm thưởng:** hiện chủ tịch nhập số điểm và chuỗi căn cứ; chưa có luồng SV nộp minh chứng, xem minh chứng và xác nhận gắn phiên bản như yêu cầu đã trao đổi. Cần liên kết hồ sơ minh chứng với từng SV, công khai mức đã duyệt trên phiếu, kiểm soát sửa thưởng sau khi đã chấm.
- **Sửa hội đồng trước buổi họp:** có tạo nhưng chưa có endpoint/UI sửa hoặc hủy bản lập nhầm. Nên cho sửa trước khi có dữ liệu chấm, kiểm lại xung đột lịch và GVHD, ghi lý do và thông báo. Không sửa âm thầm thành phần đã dùng để lập phiếu.
- **SV vắng:** hiện lưu ABSENT và điểm null. Một đề tài chỉ có một `defense_slot` duy nhất, nên chưa có xử lý kết quả học vụ hoặc buổi bổ sung theo từng SV. Cần trạng thái xử lý riêng, không tự cấp điểm cho người vắng, không thay điểm của bạn đã bảo vệ. Nếu áp dụng không đạt vì vắng, cần căn cứ và người có thẩm quyền ghi nhận; không tự đặt quy tắc cho phép bảo vệ lại.
- **Khóa hội đồng:** nút khóa hiện sẵn dù còn thiếu phiên chốt, đến lúc bấm backend mới từ chối. Chưa có bảng tổng hợp để người quản lý đối chiếu trước khi khóa; Mẫu 10/11 chỉ tải được sau khóa. Nên có bảng xem trước, số phiên đã chốt/tổng, lỗi cần xử lý và xác nhận ghi rõ phạm vi khóa.
- **Mở sửa bản chưa ký:** có snapshot lịch sử nhưng UI chưa có màn hình đối chiếu bản cũ/mới; chưa gửi thông báo cho người đã nhận kết quả khi mở lại. Nhật ký theo phạm vi hội đồng cũng chưa được bổ sung đầy đủ vào dịch vụ activity (người tạo sự kiện vẫn xem được sự kiện của chính mình).
- **Mẫu 11:** cột ngày sinh hiện luôn để trống. Cần đối chiếu dữ liệu đầu vào và mẫu thực tế trước khi tuyên bố xuất đủ nội dung/đúng định dạng, không tạo ngày sinh giả.

## Bố cục và thao tác nên cải thiện

- Với fixture chỉ một hội đồng, hai SV, mở một phiếu, trang đã cao khoảng 3.708 px ở desktop 1440 và 5.221 px ở mobile 390. Nên dùng danh sách lịch gọn, mở một phiên để làm việc; trong phiên có các mục **Tổng quan / Điểm danh / Phiếu chấm / Biên bản / Kết quả & xuất** cùng trạng thái đã lưu/chưa hoàn tất. Giữ ngữ cảnh phiên, SV và người chấm ở đầu vùng làm việc.
- Trên desktop, 12 mô tả tiêu chí dài đang chia hai cột label/input; ô điểm không thẳng hàng khi mô tả có độ dài khác nhau. Nên chia ba nhóm 2/4/4 điểm, dùng bảng mô tả–điểm tối đa–điểm nhập ở desktop và card từng tiêu chí trên điện thoại. Nút lưu nằm cùng tổng điểm, ghi rõ phiếu/SV đang lưu.
- Tìm theo MSSV `0023412345` không ra lịch dù SV có trong phiên giả lập; thông báo lại là "Chưa có lịch trong phạm vi của bạn". Nên tìm thêm tên/MSSV, hiển thị "Không có kết quả phù hợp" khi đang lọc và có nút xóa bộ lọc. Tách trạng thái rỗng thật khỏi kết quả tìm rỗng.
- Nút **Xem lịch hội đồng này** hiện chỉ đổi filter, chưa đưa người dùng tới vùng lịch và chưa có nhãn hội đồng đang lọc. Nên điều hướng/cuộn tới kết quả và đặt bộ lọc ngay cạnh danh sách.
- Lỗi và thông báo thành công đặt đầu toàn trang, dễ ngoài màn hình khi lưu ở cuối; nội dung thành công chung chung. Nên báo ngay ở biểu mẫu tương ứng, chỉ rõ đã lưu điểm danh/phiếu/biên bản và có trạng thái đang lưu.
- Select lập hội đồng chưa ngăn chọn trùng người ngay trên UI; chọn người nhập hộ cũng còn hiển thị cả người vắng. Nên loại/khóa lựa chọn không hợp lệ, giải thích tại ô và đưa focus tới lỗi; backend tiếp tục kiểm tra.
- Breadcrumb trang bảo vệ hiện là **Trang**, nên sửa thành **Hội đồng và bảo vệ**. Dùng cách thể hiện riêng cho thao tác hủy/khóa và nút lưu thông thường; không dùng cùng trọng tâm thị giác cho tất cả hành động.

## Thứ tự đề xuất triển khai

1. Bảo toàn nháp, đồng nhất làm tròn, xử lý xung đột chấm; thêm ca hồi quy đã tái hiện.
2. In phiếu trước họp, quyền mở đúng báo cáo; xử lý nhập nhầm và minh chứng thưởng.
3. Bố cục từng phiên/từng SV, bảng đối chiếu trước khóa, sửa hội đồng trước họp và kết quả SV vắng.
4. Kiểm thử trình duyệt với các vai trò, hai người chấm đồng thời, mobile có dữ liệu và đối chiếu bản in thực tế. Chỉ cập nhật kết luận bàn giao khi các kiểm chứng này đạt.

Tài liệu này ghi nhận kết quả rà soát và đề xuất; các lỗi nêu trên chưa được sửa trong lượt rà soát này.
