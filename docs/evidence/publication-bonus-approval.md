# Kiểm chứng xét minh chứng điểm thưởng

Ngày kiểm chứng: 11/11/2026. Migration `20261111_0026` bổ sung hồ sơ xét duyệt riêng, giữ nguyên tệp minh chứng và lịch sử.

## Hành vi đã kiểm chứng

- SV nộp thông tin công bố, đóng góp, danh sách SV đề nghị và phiên bản minh chứng đã quét an toàn.
- GVHD xác nhận trước khi TBM duyệt; SV và GV không được phân công không thể duyệt thay. TBM nhập mức 0–1 cho đúng từng SV được đề nghị và ghi căn cứ.
- Nộp trùng SV đang chờ/đã duyệt, cập nhật bằng phiên bản cũ, điểm vượt giới hạn và tệp không an toàn bị chặn. Yêu cầu bổ sung giữ hồ sơ cũ, SV gửi hồ sơ mới.
- Khi TBM duyệt sau khi đã lập lịch, mức thưởng tự đồng bộ vào lịch và Mẫu 6; người khác trong nhóm không tự hưởng cùng mức. Phiếu xuất điền đúng ô F28, tổng F29 tối đa 10.
- Hội đồng không được tự nhập mức khác mức đã duyệt. Hồ sơ đang chờ GVHD/TBM chặn chấm; khi đã chấm, không được sửa căn cứ thưởng.
- Người liên quan nhận thông báo, đường dẫn đến đúng loại hồ sơ; lịch sử lưu người thao tác, thời điểm, nhận xét/căn cứ.

## Kết quả chạy

- `python -m pytest tests/test_publication_claims.py tests/test_nv6_defense.py tests/test_nv6_evaluation.py tests/test_core_workspace.py tests/test_print_history.py tests/test_school_forms.py -q`: **65 passed**, PostgreSQL với schema kiểm thử riêng. Quét an toàn của tệp PDF giả lập được mô phỏng trong bộ test này.
- `python -m tools.run_e2e e2e/submission-ui.spec.ts`: **1 passed**. Trình duyệt thật, API/PostgreSQL thật và ClamAV thật; tài khoản SV, GVHD, TBM thao tác trên schema giả lập. Kiểm tra không tràn ngang ở chiều rộng 600 px.
- `npm run build`: **PASS**; còn cảnh báo kích thước bundle lớn của Vite.
- `python -m tools.validate_official_database`: **PASS**, head `20261111_0026`, 51 bảng nghiệp vụ.

Không tự duyệt hay cấp thưởng cho dữ liệu demo đang có. Tệp bổ sung cũ cần được SV gắn vào hồ sơ xét thưởng và đi qua hai bước xác nhận. Thẩm quyền TBM dùng phân công trưởng bộ môn đang hiệu lực; quy trình này triển khai theo lựa chọn của dự án, không tự khẳng định là quy định bắt buộc của Trường.
