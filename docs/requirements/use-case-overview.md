# Tổng quan Use Case

Tài liệu này chỉ là bản đồ phạm vi. Đặc tả canonical nằm tại `use-case-catalog.md`.

~~~mermaid
flowchart LR
  SV["Sinh viên"] --> ELIG["UC-ELIG-001\nĐiều kiện"]
  SV --> REG["UC-REG-001/002\nĐăng ký"]
  SV --> PROP["UC-PROP-001..004\nĐề cương"]
  SV --> PROG["UC-PROG-001/002\nTiến độ"]
  SV --> DOC["UC-DOC-001 / UC-SIM-001"]
  SV --> REPO["UC-REPO-001 / UC-AI-001"]

  GV["Giảng viên/GVHD/GVPB"] --> TOPIC["UC-TOPIC-001/002/003"]
  GV --> ASSIGN["UC-ASSIGN-001"]
  GV --> PROP
  GV --> PROG
  GV --> REVIEW["UC-EVAL-001"]

  TBM["Trưởng Bộ môn"] --> ROUND["UC-ROUND-001"]
  TBM --> TOPIC
  TBM --> ASSIGN
  TBM --> PROP
  TBM --> CHANGE["UC-CHANGE-001 / UC-EXT-001"]

  HD["Hội đồng"] --> COUNCIL["UC-COUNCIL-001 / UC-SESSION-001"]
  HD --> EVAL["UC-EVAL-002/003"]
  TK["Thư ký"] --> MIN["UC-MIN-001/002"]
  CT["Chủ tịch"] --> MIN

  SYSTEM["Hệ thống"] --> REPORT["UC-RPT-001"]
~~~

## Ranh giới

- `ADMIN` không là actor duyệt nghiệp vụ.
- AI/RAG chỉ đọc theo quyền và trả citation/link.
- Rút/gia hạn được giải quyết ngoài hệ thống; hệ thống ghi kết quả.
- Có use case sửa phiếu và in lại biên bản khi giấy chưa ai ký; từ chữ ký đầu không sửa điểm/nội dung.
