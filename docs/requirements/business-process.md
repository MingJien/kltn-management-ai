# Quy trình nghiệp vụ tổng thể và các luồng con

Mỗi luồng dùng swimlane bằng `subgraph`. Điều kiện cấu hình hoặc xác nhận trước vận hành được ghi rõ; không tự thêm phê duyệt ngoài nguồn.

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
  subgraph XNDK["Cán bộ Khoa được giao xác nhận theo đợt"]
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

Ghi chú: người xác nhận điều kiện là cán bộ Khoa được giao `ELIGIBILITY_VERIFIER` theo đợt sau đối chiếu nguồn Phòng Đào tạo, không mặc định TBM/Admin. Expertise do TBM đúng Bộ môn kiểm hoặc Trưởng khoa/người được giao khi TBM tự khai. SV tự bổ sung vào nhóm khi còn hạn/chỉ tiêu; GV xét lại nếu đã nhận nhóm. GPA mong muốn của topic không tự loại SV nếu SV đạt điều kiện chung.

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
  subgraph DIEUPHOI["Người điều phối KLTN theo đợt"]
    C5["Sắp lịch góp ý đề cương và báo cáo nội bộ khoảng 70%"]
  end
  subgraph GVCHEO["GVHD được phân công góp ý chéo"]
    C5A["Góp ý báo cáo nội bộ lần 2"]
  end
  subgraph TBM["Trưởng Bộ môn"]
    C7B{"Duyệt đổi?"}
    C9["Ghi kết quả rút/gia hạn chính thức"]
  end
  CE(("Kết thúc chu kỳ/đã cập nhật trạng thái"))
  CS --> C1 --> C2 --> C3 --> C4 --> C5 --> C5A --> C6
  C6 -- Không --> C3
  C6 -- Đổi topic --> C7 --> C7A --> C7B
  C7B -- Đồng ý --> C10["Version topic/assignment"] --> CE
  C7B -- Từ chối --> C3
  C6 -- Rút/gia hạn --> C8 --> C9 --> CE
~~~

GVHD quản lý tiến độ Thesis của mình; hai checkpoint đã biết là góp ý đề cương và báo cáo nội bộ lần 2 khoảng 70% trong tháng 12. Người điều phối nhập ngày từ kế hoạch đợt đã duyệt; GVHD khác chỉ góp ý khi được phân công. Không dùng Council bảo vệ để cấp quyền cho buổi nội bộ. Ngày cụ thể không hard-code từ mẫu có năm sai (CONFLICT-002).

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

`90%` không được hiểu là cosine 0,9. Baseline chỉ báo cáo tham khảo, không có ngưỡng tự chặn.

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
  FS(("Phiên đủ quorum")) --> F1["Mỗi thành viên hiện diện chấm từng SV"]
  F1 --> F2["Hệ thống tính tổng từng phiếu: thưởng ≤1, tổng ≤10"]
  F2 --> F3["Tính trung bình phiếu hợp lệ, làm tròn 1 chữ số"]
  F3 --> F4["Thư ký xuất và in Mẫu 9 phiên bản hiện tại"]
  F4 --> F5{"Thư ký đối chiếu bản giấy: sai và chưa ai ký?"}
  F5 -- Có --> F6["Thư ký ghi lý do, xác nhận giấy chưa ký; VOID bản in cũ"]
  F6 --> F7["Chính người chấm sửa phiếu của mình; ghi audit"]
  F7 --> F3
  F5 -- Không --> F8["Chủ tịch hoặc Thư ký ký bản đúng"]
  F8 --> F9["Từ chữ ký đầu: khóa điểm, nội dung, version"]
  F9 --> F10["Người còn lại ký cùng version; state SIGNED"]
  F10 --> FE(("Hồ sơ đã ký, bất biến"))
~~~

Nếu bản in sai trước chữ ký đầu, bản cũ và tệp/hash vẫn lưu; bản mới có `minute_no` + `version_no`, thời gian tạo và `replacement_for_id`. Sau chữ ký đầu tiên, kể cả ký trên giấy nhưng chưa nhập vào hệ thống, **không sửa điểm/nội dung**; chỉ cấp lại bản sao đúng version đã ký và lưu lần xuất. Thư ký đối chiếu thực tế, không được nhập điểm thay thành viên Hội đồng.

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

## Quy trình làm rõ ngày 25/09/2026

- Đăng ký: mỗi SV đủ điều kiện tự tham gia đề tài/nhóm khi còn hạn và chỉ tiêu 1–3. Đại diện được gửi nhóm một người; bổ sung sau khi gửi hoặc GV nhận thì GV phải xét lại. Đề tài SV tự đề xuất đăng ký cá nhân trước, TBM xét sau. GV tiếp nhận đồng ý/từ chối, rồi TBM đúng bộ môn chốt trong một transaction tạo Thesis, ThesisMember và AdvisorAssignment. Hai nhánh đề tài GV/SV đã có API/UI và kiểm thử trên dữ liệu giả.
- Điều phối KLTN theo round nhận lịch chính thức và sắp hai buổi góp ý nội bộ; GVHD xác nhận progress của Thesis được phân công, GVHD khác có assignment chỉ góp ý chéo. Không suy ra quyền Secretary Hội đồng.
- Nộp tài liệu: lưu DocumentVersion trước; kiểm tương đồng chạy sau và trả bằng chứng advisory; sinh viên có thể nộp version sửa. Chỉ policy được duyệt sau này mới xem xét gate ở finalization.
- Mẫu 9: Thư ký đối chiếu bản giấy. Bản in sai trước chữ ký đầu được VOID và in lại với version/mã/thời gian mới; người chấm tự sửa điểm. Từ chữ ký đầu khóa sửa dù state còn PRINTED; khi đủ Chair và Secretary mới SIGNED. Không có bypass TBM.
- Chatbot: phân quyền → lọc corpus/nguồn → retrieval → citation; thiếu Gemini key trả RETRIEVAL_ONLY, không chế tạo câu trả lời. Văn bản nguồn là dữ liệu.
