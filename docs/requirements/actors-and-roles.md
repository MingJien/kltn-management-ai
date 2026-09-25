# Tác nhân, vai trò và phạm vi

## Nguyên tắc

Một tài khoản không đổi theo chức vụ. Quyền được xác định từ base role, vị trí tổ chức, assignment trên hồ sơ/tài nguyên và trạng thái workflow.

| Tác nhân/ngữ cảnh | Cách biểu diễn | Trách nhiệm chính | Không được mặc định |
| --- | --- | --- | --- |
| Sinh viên | Base role `STUDENT`; `ThesisMember`, có thể `isCoordinator` | Tự khai điều kiện, đăng ký, đề xuất topic, nộp/sửa đề cương/tài liệu, báo cáo tiến độ, xem kết quả của mình | Không tự duyệt điều kiện, đề tài, đề cương, điểm |
| Giảng viên | Base role `LECTURER` | Khai expertise, đề xuất topic; tham gia theo assignment | Không có quyền trên mọi KLTN chỉ vì là giảng viên |
| GVHD | `AdvisorAssignment` | Accept/reject đăng ký đúng đề tài được phân công, không thêm/ghép thành viên; duyệt phân công công việc, nhận xét đề cương/tiến độ, xác nhận cho bảo vệ | Không thay TBM chốt đề tài/đề cương |
| GVPB đề cương/KLTN | `ReviewerAssignment` hoặc `CouncilMember.role=REVIEWER` | Góp ý đề cương, nhận xét phản biện, đánh giá theo phân công | Không sửa nội dung SV hoặc điểm người khác |
| Trưởng Bộ môn | `OrganizationalPosition` theo Bộ môn và thời gian | Duyệt/chỉnh tên topic, chốt phân công GVHD, chốt đề cương, cập nhật kết quả thủ tục ngoài | Không ký thay Trưởng khoa/Chủ tịch khi nguồn quy định khác |
| Trưởng khoa | `OrganizationalPosition` theo Khoa và thời gian | Ký/xác nhận văn bản/danh sách sau bước nghiệp vụ | Không xét nội dung thay TBM theo project decision |
| Chủ tịch Hội đồng | `CouncilMember.role=CHAIR` lấy từ quyết định | Chủ trì phiên, kết luận và ký/xác nhận Mẫu 9 cùng Thư ký | Hệ thống không tự chọn |
| Thư ký Hội đồng | `CouncilMember.role=SECRETARY` | Chuẩn bị, lập/version/void sau in nếu giấy chưa có chữ ký nào, xuất và ký/xác nhận Mẫu 9, tổng hợp | Không nhập/sửa điểm thay thành viên |
| Thành viên Hội đồng | `CouncilMember` | Tham dự, tự nhập điểm từng SV, ký khi cần | Không sửa điểm của người khác |
| Phòng Đào tạo/đơn vị quản lý | Nguồn quyết định hoặc actor tích hợp | Cung cấp quyết định/danh sách chính thức | Không phải base role mới nếu chưa cần tài khoản riêng |
| Người xác nhận điều kiện | `ResourceAssignment.type=ELIGIBILITY_VERIFIER` theo đợt | Đối chiếu nguồn, xác nhận hoặc từ chối snapshot điều kiện | Người Khoa được giao theo round sau đối chiếu nguồn Phòng Đào tạo; không mặc định Admin/TBM |
| Quản trị hệ thống | Base role `ADMIN` | Tài khoản, cấu hình kỹ thuật, giám sát vận hành | Không tự duyệt nghiệp vụ |
| Chatbot/RAG | Dịch vụ backend, không phải người dùng | Retrieval đã lọc quyền, trả kết quả + link | Không duyệt, chấm, ký, đổi trạng thái nghiệp vụ |

## Phạm vi tổ chức

- KLTN thuộc Bộ môn/chuyên ngành; chức vụ có `scope` và thời hạn.
- Assignment gắn đúng `Thesis`, `Proposal`, `Council` hoặc `DefenseSession`.
- Một người có thể đồng thời mang nhiều ngữ cảnh nhưng mỗi hành động phải kiểm tra conflict-of-interest và assignment cụ thể.
- Quan hệ thân thuộc và GVHD chấm chính KLTN mình hướng dẫn bị cấm theo QĐ 2919.

- Điều phối KLTN là `ResourceAssignment(assignment_type=KLTN_COORDINATOR, round_id=...)`, không đồng nhất với Hội đồng Secretary; quản lý mốc đợt theo nguồn chính thức. Cùng một người có thể giữ cả hai assignment nhưng API kiểm scope riêng.
