# Ma trận truy vết yêu cầu

| Nhóm | Nguồn chính | Requirement | Business Rule | Use Case | Open/conflict |
| --- | --- | --- | --- | --- | --- |
| Tài khoản và ngữ cảnh | GVHD, quyết định dự án | REQ-AUTH-001..003 | BR-AUTH-001..002 | UC-AUTH-001 | — |
| Năm học/đợt | GVHD, QĐ 2919 | REQ-ROUND-001 | BR-ROUND-001 | UC-ROUND-001 | lịch theo round |
| Điều kiện | QĐ 5964, QĐ 2919 | REQ-ELIG-001..002, REQ-DEF-001 | BR-ELIG-001..002 | UC-ELIG-001, UC-DEF-001 | Người Khoa được giao; CONFLICT-006 |
| Expertise | GVHD | REQ-EXP-001 | safe label self-declared | UC-EXP-001 | TBM/Trưởng khoa theo scope |
| Topic/yêu cầu GVHD | GVHD, QĐ 2919, quyết định dự án | REQ-TOPIC-001..003 | BR-TOPIC-001..002 | UC-TOPIC-001..003 | — |
| Đăng ký/nhóm | GVHD, QĐ 2919, Mẫu 1a/1b | REQ-REG-001..006 | BR-REG-001..006 | UC-REG-001/002, UC-ASSIGN-001 | Mỗi SV tự tham gia trước hạn/chỉ tiêu; bổ sung thì GV xét lại; đề tài SV xét sau đăng ký cá nhân |
| Phân công cá nhân | GVHD, Mẫu 2 | REQ-REG-004 | BR-REG-004 | UC-WORK-001 | — |
| Đề cương | GVHD, QĐ 2919, Mẫu 3 | REQ-PROP-001..003 | BR-PROP-001..002 | UC-PROP-001..004 | — |
| Tiến độ | GVHD, Mẫu 2, IN4299N | REQ-PROG-001..002 | BR-PROG-001..002 | UC-PROG-001/002 | Ngày theo round; CONFLICT-002/004 |
| Đổi/rút/gia hạn | QĐ 2919, GVHD | REQ-CHANGE-001..003 | BR-CHANGE-001 | UC-CHANGE-001, UC-EXT-001 | lịch theo round |
| Tài liệu/version | QĐ 2919, Mẫu 3 | REQ-DOC-001 | BR-DOC-001 | UC-DOC-001 | — |
| Tương đồng | GVHD, quyết định dự án | REQ-SIM-001..003 | BR-SIM-001..003 | UC-SIM-001 | Baseline advisory |
| Hội đồng/phiên/attendance | QĐ 2919, GVHD, Mẫu 4/9 | REQ-COUNCIL-001..003 | BR-COUNCIL-001..002 | UC-COUNCIL-001, UC-SESSION-001 | — |
| Nhận xét/rubric/chấm | Mẫu 6/7/8, QĐ 2919, IN4299N | REQ-EVAL-001..003 | BR-EVAL-001..003 | UC-EVAL-001..003, UC-RUBRIC-001 | Baseline Mẫu 6 của dự án đã chốt; runtime chấm thật chưa triển khai |
| Biên bản | QĐ 2919, GVHD, Mẫu 9 | REQ-MIN-001..002 | BR-MIN-001..002 | UC-MIN-001/002 | Sửa sau in trước chữ ký đầu; CONFLICT-009 đã chốt Mẫu 9 |
| Kho và AI | GVHD, QĐ 2919, quyết định dự án | REQ-REPO-001, REQ-AI-001..002 | BR-REPO-001, BR-AI-001..002 | UC-REPO-001, UC-AI-001 | chính sách Trường về Gemini chưa có nhưng không cản design |
| Báo cáo | Mẫu 4/10/11, IN4299N | REQ-RPT-001 | BR-AUDIT-001 | UC-RPT-001 | — |

## Kiểm tra bao phủ bắt buộc

- 18 câu hỏi GVHD: đối chiếu đủ tại `18-cau-hoi-gvhd-mapping.md`.
- Bảy luồng A–G: có trong `business-process.md` và `business-process.drawio`.
- Mỗi requirement có ít nhất một nguồn; mỗi use case có requirement; mọi điều kiện chưa có nguồn áp dụng có giá trị mặc định an toàn.
- Không có base role hoặc use case “cán bộ KLTN”; không có Admin bypass; không có use case AI duyệt/chấm/ký.
