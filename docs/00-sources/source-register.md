# Sổ đăng ký nguồn canonical

## Quy ước

- `READ_NORMALIZED`: đã đọc và chuẩn hóa, được dùng trong phạm vi thẩm quyền của nguồn.
- `OCR_REVIEWED_WITH_UNCERTAINTY_MARKERS`: đã OCR theo trang và hiệu đính; đoạn không chắc không được dùng làm căn cứ.
- `READ_NORMALIZED_REDACTED`: đã đọc, PII đã được khử.
- `READ_STRUCTURE_REDACTED`: chỉ giữ cấu trúc và logic, không lưu dữ liệu người thật.
- `READ_SCHEMA_ONLY_PII_REDACTED`: chỉ giữ schema cột, trường và vai trò.
- `ARCHIVED_NON_CANONICAL`: snapshot lịch sử, không phải nguồn nghiệp vụ chính.
- `DUPLICATE_BYTE_IDENTICAL_REMOVED`: bản trùng byte đã được ghi nhận và loại khỏi raw canonical.

Thứ tự xử lý khi có xung đột: P1 = góp ý/chỉ đạo GVHD mới nhất; P2 = quyết định, quy định, kế hoạch, đề cương và biểu mẫu chính thức của Trường/Khoa (văn bản sửa đổi mới hơn có hiệu lực trong phạm vi được sửa); P3 = quyết định đã chốt của chủ dự án, chỉ trong phạm vi thiết kế dự án; P4 = tài liệu chính thức của công nghệ; P5 = nguồn học thuật; P6 = kiến thức chung. Snapshot lịch sử mang nhãn `ARCHIVE`, không tham gia ưu tiên nghiệp vụ. Nếu các nguồn mâu thuẫn mà chưa có căn cứ phân xử, ghi vào `source-conflicts.md`, không tự hợp nhất.

Các bản trích và tài liệu gốc ở cột Bản xử lý nội bộ chỉ dùng để đối chiếu trên máy, không thuộc bộ source công bố. Bản nộp trên GitHub gồm kết quả phân tích, thiết kế và mã nguồn; có thể đối chiếu chúng theo ID nguồn trong bảng dưới.

## Danh mục nguồn

| ID | Nguồn / thẩm quyền | Nhóm | Vị trí gốc | Bản xử lý nội bộ (lưu trên máy) | Trạng thái và cách dùng |
| --- | --- | --- | --- | --- | --- |
| SRC-PROJECT-MASTER-001 | Chỉ đạo chủ dự án ngày 19/09/2026 | P3 | User attachment | Không áp dụng | Đã đọc; là quyết định dự án, không giả thành quy định Trường. |
| SRC-PROJECT-DB-001 | Chỉ đạo hoàn thành NV4 Tuần 1–2 đến hết CSDL ngày 20/09/2026 | P3 | User attachment | `docs/00-sources/project-context-baseline.md` | Đã đọc; chốt phạm vi dừng sau PostgreSQL schema/migration/validation, không triển khai API/UI/AI. |
| SRC-PROJECT-GIT-001 | Quy tắc quản lý nguồn, tài liệu và Git ngày 21/09/2026 | P3 | User attachment | docs/adr/ | Đã đọc; xác nhận GitHub Flow gọn: main canonical, Issue/checklist, nhánh ngắn, PR review; không dùng branch theo tuần. |
| SRC-GVHD-NV4-001 | `giải đáp NV4 tuần 1.docx`, GVHD; Drive sửa 18/09/2026 04:44 UTC | P1 | Drive `1dgRI_9XXwIk0E2eG-xHvWHbTI0jn21Xo`; `source/raw/NghiepVu/giải đáp NV4 tuần 1.drive-20260918.docx` | `source/markdown/NghiepVu/giai-dap-nv4-tuan-1.md` | `READ_NORMALIZED_REDACTED`; bản Drive mới nhất là canonical; tên cá nhân không cần thiết đã được khử. |
| SRC-LOCAL-NV4-001 | Hai snapshot local ngày 17/09/2026 | ARCHIVE | `source/raw/_archive/NghiepVu/` | `source/markdown/NghiepVu/nv4-tuan-1-local-snapshot-manifest.md` | `ARCHIVED_NON_CANONICAL`; chỉ đối chiếu lịch sử. |
| SRC-QD-2919 | QĐ 2919/QĐ-ĐHĐT ngày 15/11/2022 | P2 | Drive `1dQvfF2ZXisBEwvqidmQAkG9wtFqQ3Zcp`; `source/raw/QuyDinh/QD-2919-KLTN-2022.drive.pdf` | `source/markdown/QuyDinh/qd-2919-kltn.md` | `OCR_REVIEWED_WITH_UNCERTAINTY_MARKERS`; 8 trang, Điều 2 đã bị QĐ 5964 sửa. |
| SRC-QD-2919-DUP | `QĐ_ KLTN.pdf` | P2 | Drive `1AoE7O26Y35xnNVoBN-9f3frs4hMaY4iK` | Tham chiếu SRC-QD-2919 | `DUPLICATE_BYTE_IDENTICAL_REMOVED`. |
| SRC-QD-5964 | QĐ 5964/QĐ-ĐHĐT ngày 16/08/2024 | P2 | Drive `12Azwk8tiP9KAlQupUph7vKLBuMcph82q` | `source/markdown/QuyDinh/qd-5964-sua-doi-kltn.md` | `READ_NORMALIZED_REDACTED`; nguồn hiện hành cho điều kiện học vụ. |
| SRC-HP-IN4299N | Đề cương học phần IN4299N ngày 05/09/2026 | P2 | Drive `1Wyj2RASereW0qyB9U4Xigbms9waJNUIb` | `source/markdown/QuyDinh/in4299n-khoa-luan-tot-nghiep.md` | `READ_NORMALIZED_REDACTED`. |
| SRC-KH-2026 | Kế hoạch KLTN 2026–2027, Khoa CN&KT | P2 | Drive `1sCjTUJvFA1LakG2_aJgA3m_L7zUFIHdq` | `source/markdown/KeHoach/ke-hoach-trien-khai-kltn-2026-2027.md` | `READ_NORMALIZED_REDACTED`; không hard-code ngày có xung đột. |
| SRC-MAU-01A | Mẫu 1a đăng ký cá nhân | P2 | Drive `1S_AaUZgxUJT7IVuUUzWZjpziUvGVqU9T` | `source/markdown/BieuMau/mau-1a-don-dang-ky-kltn.md` | `READ_NORMALIZED_REDACTED`. |
| SRC-MAU-01B | Mẫu 1b đăng ký nhóm | P2 | Drive `1aj7yisvXtR-hrEMUtJadD1VCcSK4_DUn` | `source/markdown/BieuMau/mau-1b-don-dang-ky-kltn-nhom.md` | `READ_NORMALIZED_REDACTED`; bố cục 2 SV là mẫu cũ, rule hiện hành tối đa 3. |
| SRC-MAU-02 | Mẫu 2 kế hoạch thực hiện | P2 | Drive `1QwtdevNhZnS19kLHTYtuU6w5Yda05QiO` | `source/markdown/BieuMau/mau-2-ke-hoach-thuc-hien.md` | `READ_NORMALIZED_REDACTED`; ngày là ví dụ. |
| SRC-MAU-03 | Mẫu 3 đề cương | P2 | Drive `1VOP2z5qC-aSMnmsWcjUIdBVZh_3VJu_R` | `source/markdown/BieuMau/mau-3-de-cuong-thuc-hien-de-tai.md` | `READ_NORMALIZED_REDACTED`; DOCX là mẫu canonical. |
| SRC-MAU-03-PDF | PDF Mẫu 3 local/Drive | P2 | `source/raw/DeCuong/3.De cuong thuc hien de tai.local-snapshot-20260915.pdf` | `source/markdown/DeCuong/mau-3-pdf-duplicate-manifest.md` | Giữ một snapshot; bản Drive trùng byte đã loại. |
| SRC-MAU-04 | Mẫu 4 danh sách SV/GVHD | P2 | Drive `1HlmIPtEBogmFOrfRZpZbTUEoFMoh1QFq` | `source/markdown/BieuMau/mau-4-danh-sach-sv-schema.md` | `READ_SCHEMA_ONLY_PII_REDACTED`; giữ 3 sheet và cột nghiệp vụ. |
| SRC-MAU-05 | Mẫu 5 quy định trình bày/bìa | P2 | Drive `1c3wchKAg3a-hprvMR85jW7g1ks8ALlb0` | `source/markdown/BieuMau/mau-5-quy-dinh-trinh-bay-bao-cao-bia-kltn.md` | `READ_NORMALIZED`; đầy đủ quy định trình bày, không có hồ sơ người thật. |
| SRC-MAU-06 | Mẫu 6 phiếu đánh giá Hội đồng | P2 | Drive `1uWL7QEjdOlLdpAjclWFRerZoqv8T0Ohz` | `source/markdown/BieuMau/mau-6-phieu-danh-gia-hoi-dong.md` | `READ_NORMALIZED_REDACTED`; nguồn rubric/điểm thưởng. |
| SRC-MAU-07 | Mẫu 7 nhận xét GVHD | P2 | Drive `1yhQqVycIPPPKk_Ke1q5cd700KAdRD-B3` | `source/markdown/BieuMau/mau-7-nhan-xet-kltn-gvhd.md` | `READ_NORMALIZED_REDACTED`; mẫu trống. |
| SRC-MAU-08 | Mẫu 8 nhận xét GVPB | P2 | Drive `1DVMrXprsN8l8OLdSo7tu37WLDiuYopWB` | `source/markdown/BieuMau/mau-8-nhan-xet-kltn-gvpb.md` | `READ_NORMALIZED_REDACTED`; mẫu trống. |
| SRC-MAU-09 | Mẫu 9 biên bản Hội đồng | P2 | Drive `1SUbqsu_ucRqIdxARY4ou79_gXamgelHv` | `source/markdown/BieuMau/mau-9-bien-ban-hoi-dong-redacted.md` | `READ_STRUCTURE_REDACTED`; không chép dữ liệu hồ sơ thật. |
| SRC-MAU-10 | Mẫu 10 bảng điểm tổng hợp | P2 | Drive `1g7jr1KKr1NxzU3uhS3pAnb0cef7QDbb1` | `source/markdown/BieuMau/mau-10-bang-diem-tong-hop-schema.md` | `READ_SCHEMA_ONLY_PII_REDACTED`. |
| SRC-MAU-11 | Mẫu 11 bảng điểm chính thức | P2 | Drive `1OxX9NfyLczCMkXUgLFfcYNZLd8V4kBxM` | `source/markdown/BieuMau/mau-11-bang-diem-chinh-thuc-schema.md` | `READ_SCHEMA_ONLY_PII_REDACTED`. |
| SRC-DS-KYSO-001 | Danh sách SV KLTN ký số | P2 | Drive `1AIG0Yx6lMDR7iQgsuL92C-RFUbDcSEL5` | Không nhập nội dung | `RESTRICTED_PII_NOT_TRANSCRIBED`; Mẫu 4 đã đủ schema. |
| SRC-QD-TLTK-011 | QĐ 885/QĐ-ĐHĐT về trích dẫn/TLTK ngày 22/04/2021 | P2 | Drive `1VS_1CmgecFFYCT3NJOmEJ4Ljiyd0GSBV` | `source/markdown/QuyDinh/quy-dinh-trich-dan-tltk11.md` | `OCR_REVIEWED_WITH_UNCERTAINTY_MARKERS`; 7 trang; phạm vi trực tiếp là sau đại học. |

## Bản trùng đã xác minh

| ID | SHA-256 | Xử lý |
| --- | --- | --- |
| DUP-001 | `2B372039260B7F71201058AEE3D4D9541BE9E8CB63D1CCA669297EDEE7ED3AEA` | Giữ SRC-QD-2919; bỏ raw duplicate. |
| DUP-002 | `AC4AE914CC4BE1F5F000B8FF57C36CAD9FADB2E4111D86C2137A00E244044086` | Giữ một PDF local snapshot Mẫu 3; bỏ bản Drive candidate và bản top-level trùng byte. |

## Cổng sử dụng nguồn

Các nguồn thiết yếu Tuần 1 đã được đọc/chuẩn hóa hoặc trích schema an toàn. `SRC-DS-KYSO-001` không cần sao chép vì không bổ sung cấu trúc ngoài Mẫu 4. Đoạn OCR không chắc, ngày mẫu có xung đột và dữ liệu PII không được dùng xác lập rule.

Project Context Baseline canonical: `docs/00-sources/project-context-baseline.md`; baseline đã được đối chiếu với sổ nguồn, 18 câu hỏi và các xung đột trước khi thiết kế CSDL.
