# Quy trình nghiệp vụ tổng thể và các luồng con

Mỗi luồng dùng swimlane bằng `subgraph`. Nhánh `OPEN/PROPOSED` được ghi rõ; không tự thêm phê duyệt ngoài nguồn.

## Tổng thể

~~~mermaid
flowchart LR
  S(("Bắt đầu đợt")) --> A["A. Điều kiện, đề tài, đăng ký, GVHD"]
  A --> B["B. Đề cương, góp ý, chốt, ký"]
  B --> C["C. Thực hiện, tiến độ, đổi/rút/gia hạn"]
  C --> D["D. Nộp tài liệu, tương đồng, nộp lại"]
  D --> E["E. Quyết định Hội đồng, phiên, attendance"]
  E --> F["F. Chấm cá nhân, điểm, biên bản"]
  F --> G["G. Lưu trữ, tra cứu, chatbot RAG"]
  G --> E(("Kết thúc vòng đời KLTN"))
~~~

## A. Điều kiện + Đề tài + Đăng ký + Phân công GVHD

~~~mermaid
flowchart TB
  AS(("Bắt đầu"))
  subgraph SV["Sinh viên"]
    A1["Tự khai/đồng bộ dữ liệu điều kiện"]
    A6["Chọn đúng 1 đề tài hoặc đề xuất đề tài"]
    A7["Khai nhóm 1–3 SV; coordinator chỉ điều phối"]
  end
  subgraph GV["Giảng viên/GVHD"]
    A3["Tự khai expertise"]
    A4["Đề xuất topic + yêu cầu mong muốn"]
    A9{"Đồng ý đăng ký?"}
  end
  subgraph TBM["Trưởng Bộ môn"]
    A5["Duyệt/chỉnh tên/mở topic"]
    A10["Chốt topic và phân công GVHD"]
  end
  subgraph XNDK["Người xác nhận điều kiện theo assignment đợt — OPEN-11"]
    A2{"Snapshot đã đối chiếu, xác nhận đủ điều kiện chung?"}
  end
  subgraph SYS["Hệ thống"]
    A8{"Một đăng ký hoạt động/SV/đợt?\nSố SV ≤ 3?"}
    A11["Tạo Thesis, membership, AdvisorAssignment"]
  end
  AE(("Kết thúc"))
  AS --> A1 --> A2
  A2 -- Không --> AX["Không cho đăng ký; lưu lý do"] --> AE
  A2 -- Có --> A6
  A3 --> A4 --> A5
  A6 --> A7 --> A8
  A5 --> A8
  A8 -- Không --> AY["Từ chối vi phạm invariant"] --> AE
  A8 -- Có --> A9
  A9 -- Từ chối --> AZ["Trả kết quả/lý do"] --> AE
  A9 -- Đồng ý --> A10 --> A11 --> AE
~~~

Ghi chú: người xác nhận điều kiện phải có assignment `ELIGIBILITY_VERIFIER` theo đợt, chưa mặc định là TBM/Admin (`OPEN-11`). Expertise verifier là `OPEN-01`; ghép thêm SV sau đăng ký là `OPEN-02`. GPA mong muốn của topic không tự loại SV nếu SV đạt điều kiện chung.

## B. Đề cương + phản biện/góp ý + xác nhận/ký

~~~mermaid
flowchart TB
  BS(("Bắt đầu"))
  subgraph SV["Sinh viên"]
    B1["Upload ProposalVersion"]
    B5["Sửa và nộp version mới"]
    B10["In bản để ký trực tiếp"]
  end
  subgraph GVHD["GVHD"]
    B2["Nhận xét đúng version"]
    B6{"Xác nhận đạt?"}
  end
  subgraph PB["GVPB/Hội đồng đề cương"]
    B3["Góp ý + upload biểu mẫu"]
  end
  subgraph TBM["Trưởng Bộ môn"]
    B7{"Chốt nội dung nghiệp vụ?"}
  end
  subgraph TK["Trưởng khoa"]
    B9["Ký/xác nhận văn bản"]
  end
  BE(("Kết thúc: đề cương đã ký/xác nhận"))
  BS --> B1 --> B2 --> B3 --> B4{"Cần sửa?"}
  B4 -- Có --> B5 --> B6
  B4 -- Không --> B6
  B6 -- Chưa đạt --> B5
  B6 -- Đạt --> B7
  B7 -- Trả sửa --> B5
  B7 -- Chốt --> B9 --> B10 --> BE
~~~

Trưởng khoa ký sau khi TBM chốt; thao tác ký không thay việc xét nội dung của TBM.

## C. Thực hiện + tiến độ + đổi/rút/gia hạn

~~~mermaid
flowchart TB
  CS(("Bắt đầu chu kỳ tiến độ"))
  subgraph SV["Sinh viên/nhóm"]
    C1["Lập kế hoạch và work allocation"]
    C3["Nộp ProgressReport/evidence"]
    C6{"Yêu cầu phát sinh?"}
    C7["Gửi đổi đề tài trên hệ thống"]
    C8["Làm thủ tục rút/gia hạn bên ngoài"]
  end
  subgraph GVHD["GVHD"]
    C2["Duyệt kế hoạch/phân công"]
    C4["Nhận xét/xác nhận tiến độ"]
    C7A["Nhận xét yêu cầu đổi"]
  end
  subgraph TBM["Trưởng Bộ môn"]
    C5["Tổ chức checkpoint đề cương và khoảng 70%"]
    C7B{"Duyệt đổi?"}
    C9["Ghi kết quả rút/gia hạn chính thức"]
  end
  CE(("Kết thúc chu kỳ/đã cập nhật trạng thái"))
  CS --> C1 --> C2 --> C3 --> C4 --> C5 --> C6
  C6 -- Không --> C3
  C6 -- Đổi topic --> C7 --> C7A --> C7B
  C7B -- Đồng ý --> C10["Version topic/assignment"] --> CE
  C7B -- Từ chối --> C3
  C6 -- Rút/gia hạn --> C8 --> C9 --> CE
~~~

Milestone chi tiết và deadline theo round là cấu hình `OPEN-03/06`, không hard-code từ mẫu.

## D. Nộp tài liệu + tương đồng + sửa/nộp lại

~~~mermaid
flowchart TB
  DS(("Bắt đầu: có bản nộp"))
  subgraph SV["Sinh viên"]
    D1["Nộp DocumentVersion"]
    D7["Xem bằng chứng, sửa và nộp version mới"]
  end
  subgraph SYS["Hệ thống tương đồng"]
    D2["Lexical matching"]
    D3["Semantic candidate discovery"]
    D4["Tính coverage theo SimilarityPolicy version"]
    D5{"Vượt business threshold đã duyệt?"}
  end
  subgraph GVHD["GVHD"]
    D6["Xem report; yêu cầu sửa hoặc xác nhận"]
  end
  DE(("Kết thúc: bản được GVHD xác nhận"))
  DS --> D1 --> D2 --> D3 --> D4 --> D5
  D5 -- "Policy chưa duyệt" --> D6
  D5 -- Có --> DH["Đánh dấu tương đồng cao; chặn finalize\nKhông kết luận đạo văn"] --> D6
  D5 -- Không --> D6
  D6 -- Sửa --> D7 --> D1
  D6 -- Xác nhận --> D8["Cho đi tiếp bước đủ điều kiện"] --> DE
~~~

`90%` không được hiểu là cosine 0,9. Exact metric là `OPEN-05`.

## E. Quyết định Hội đồng + phiên bảo vệ + attendance

~~~mermaid
flowchart TB
  ES(("Bắt đầu: có quyết định"))
  subgraph PDT["Quyết định chính thức"]
    E1["Quyết định Hội đồng"]
  end
  subgraph SYS["Người được phân quyền/Hệ thống"]
    E2["Import Council + 5 CouncilMember đúng role"]
    E3["Tạo một hoặc nhiều DefenseSession"]
    E4["Gắn nhiều KLTN/SV vào phiên"]
  end
  subgraph TK["Thư ký"]
    E5["Ghi attendance"]
  end
  subgraph CT["Chủ tịch"]
    E6{"Chair và Secretary có mặt?\nVắng không quá 2/5?"}
    E7["Mở phiên bảo vệ"]
  end
  EE(("Kết thúc kiểm tra phiên"))
  ES --> E1 --> E2 --> E3 --> E4 --> E5 --> E6
  E6 -- Không --> EX["Không tổ chức/chấm; ghi lý do"] --> EE
  E6 -- Có --> E7 --> EE
~~~

Hệ thống không tự chọn Chủ tịch. Attendance chỉ tạo quyền chấm cho thành viên thực sự có mặt.

## F. Chấm cá nhân + tổng hợp điểm + biên bản

~~~mermaid
flowchart TB
  FS(("Bắt đầu: phiên đủ quorum"))
  subgraph TV["Từng thành viên Hội đồng hiện diện"]
    F1["Nhập Evaluation cho từng SV"]
    F2{"Cần sửa trước khóa?"}
    F3["Chính người nhập sửa điểm mình"]
  end
  subgraph SYS["Hệ thống"]
    F4["Tính trung bình phiếu hợp lệ; làm tròn 1 chữ số"]
    F5["Mỗi phiếu: bonus ≤1, total ≤10\nFinal = trung bình total; không cộng bonus lần hai"]
  end
  subgraph TK["Thư ký"]
    F6["Tạo/xuất CouncilMinute"]
    F7{"Sai trước in?"}
    F8["Void version sai; tạo replacement"]
    F9["In biên bản"]
  end
  subgraph CT["Chủ tịch"]
    F10["Ký/xác nhận biên bản"]
  end
  FE(("Kết thúc: hồ sơ bị khóa"))
  FS --> F1 --> F2
  F2 -- Có --> F3 --> F1
  F2 -- Không --> F4 --> F5 --> F6 --> F7
  F7 -- Có --> F8 --> F6
  F7 -- Không --> F9 --> F10 --> F11["Khóa PRINTED/SIGNED"] --> FE
~~~

Sau in/ký không có đường sửa; thủ tục hậu ký là `OPEN-07`.

## G. Lưu trữ + tra cứu + chatbot RAG

~~~mermaid
flowchart TB
  GS(("Bắt đầu: có bản cuối"))
  subgraph QL["Khoa/Bộ môn"]
    G1["Xác nhận bản cuối và visibility"]
  end
  subgraph REPO["Kho KLTN"]
    G2["Lưu file + metadata Bộ môn/chuyên ngành/năm"]
    G3["Lập search/index metadata theo quyền"]
  end
  subgraph USER["Người dùng"]
    G4["Tìm kiếm/xem/tải trên web"]
    G5["Đặt câu hỏi chatbot"]
  end
  subgraph RAG["Backend RAG"]
    G6["Authorization trước retrieval"]
    G7["Lấy chunks tối thiểu, giảm PII"]
    G8["Gọi Gemini bằng key backend-only"]
    G9["Trả câu trả lời + citation + link"]
  end
  GE(("Kết thúc: người dùng mở nguồn"))
  GS --> G1 --> G2 --> G3
  G3 --> G4 --> GE
  G5 --> G6 --> G7 --> G8 --> G9 --> G4
~~~

Gemini là quyết định dự án; không ghi thành quy định Trường. Download luôn qua web endpoint có authorization.
