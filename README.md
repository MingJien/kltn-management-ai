# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Repository này chứa sản phẩm phân tích và thiết kế NV4 cùng **prototype dùng tiếp được**: PostgreSQL, FastAPI, React và thử nghiệm truy xuất AI trên dữ liệu giả lập. PostgreSQL là nguồn dữ liệu nghiệp vụ chính; AI chỉ hỗ trợ tra cứu và tương đồng, không tự chấm đạo văn. Chưa phải hệ thống production; không có hồ sơ sinh viên hoặc 7 KLTN thật trong Git.

## Nên mở gì trước?

| Muốn xem | Tệp |
| --- | --- |
| Quyết định nghiệp vụ đã chốt | [Quyết định thiết kế 25/09](docs/decisions/quyet-dinh-du-an-2026-09-25.md), [18 câu hỏi GVHD](docs/requirements/18-cau-hoi-gvhd-mapping.md) |
| Nghiệp vụ, vai trò, use case, quyền | [Yêu cầu](docs/requirements/business-requirements.md), [quy tắc](docs/requirements/business-rules.md), [quy trình](docs/requirements/business-process.md), [use case](docs/requirements/use-case-catalog.md), [phân quyền](docs/requirements/permission-matrix.md) |
| CSDL và ý nghĩa bảng/cột | [ERD tổng thể](docs/design/erd.md), [ERD theo 6 cụm](docs/design/erd-clusters/README.md), [từ điển dữ liệu](docs/design/data-dictionary.md), [giải thích dễ đọc](docs/design/database-explained.md), [rubric Mẫu 6](docs/design/rubric-mau-6.md), [quy tắc dữ liệu](docs/design/database-rules.md), [đối chiếu quyết định với CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) |
| Tệp CSDL PostgreSQL | [Tạo database mới](database/kltn-db-baseline.sql), [cách dùng](database/README.md). Hai tệp SQL thao tác pgAdmin (`kltn-ai-workbench.sql`, `kltn-ai-updates.sql`) chỉ lưu trên máy. |
| Cập nhật CSDL **đã có bảng** | [Alembic migrations](backend/migrations/versions/) từ 0001 đến 0007; **không chạy lại file SQL tạo mới** |
| API và giao diện | [FastAPI](backend/api/main.py), [OpenAPI runtime](docs/prototype/openapi-runtime.json), [thiết kế API toàn miền](docs/design/openapi.yaml), [React](frontend/src/App.tsx), [wireframe](docs/design/wireframes.md) |
| AI và biểu mẫu | [Prototype AI](docs/ai/prototype.md), [thiết kế tương đồng](docs/ai/similarity-design.md), [thiết kế xuất biểu mẫu](docs/design/xuat-bieu-mau.md) |
| Kiểm chứng | [Minh chứng prototype](docs/evidence/prototype-validation.md), [ma trận truy vết](docs/design/traceability-matrix.md) |

## Trạng thái thực tế

- Hai database local cùng ở PostgreSQL 17.11, revision `20260925_0007`, **63 bảng vật lý/618 cột** (`62 bảng mô hình/617 cột` cộng `alembic_version`). `kltn_ai` là database chính để theo dõi schema; `kltn_dev` là database phát triển để chạy prototype với dữ liệu giả. Bộ seed tạo 5 tài khoản, 3 sinh viên, 2 giảng viên, 1 đợt, 3 snapshot điều kiện và 1 đề tài. Mỗi đăng ký nhóm bắt đầu ở `DRAFT`; API kiểm tra từng thành viên tự xác nhận bằng tài khoản của mình, rồi mới cho nhóm trưởng gửi.
- Corpus giờ phân biệt KLTN đang quản lý, tài liệu học thuật nhập và nguồn chính thức. KLTN cũ không cần tạo Thesis/Sinh viên giả. Test DB-01..42 PASS, gồm COMMENT_ONLY cho góp ý chéo và đầy đủ baseline Mẫu 6.
- Prototype API hỗ trợ lát cắt đề tài GV đã duyệt: SV tạo bản nháp nhóm 1–3 → từng SV tự xác nhận hoặc từ chối đúng một lần → nhóm trưởng gửi khi mọi người đồng ý → GV đề xuất chấp nhận/từ chối → TBM đúng bộ môn chốt để tạo Thesis/ThesisMember/AdvisorAssignment nguyên tử. Nhóm trưởng có thể hủy bản nháp để lập nhóm lại; từ `SUBMITTED` thành viên bị khóa. Bộ kiểm thử PostgreSQL xác nhận quyền, luồng chuyển trạng thái và rollback dữ liệu thử.
- React có màn đề tài, đăng ký nhóm/xác nhận từng thành viên/quyết định, chi tiết khóa luận và tìm đề tài/tra cứu nguồn. Build/typecheck giao diện PASS; browser end-to-end cho luồng xác nhận mới vẫn cần kiểm. Ngày 30/09, phiên bản trước đã đọc đề tài từ `kltn_dev`, tìm nguồn KLTN giả lập và trả citation tài liệu giả ở chế độ `RETRIEVAL_ONLY`; không gọi mô hình sinh câu trả lời.
- FastEmbed pretrained + Qdrant local truy xuất được corpus giả lập có source_type/provenance; RAG trả citation ở chế độ RETRIEVAL_ONLY. **Không có Gemini key, không có kết luận chất lượng AI trên 7 KLTN, không có ngưỡng 90% đã chốt.**
- Mẫu 9 đã được thiết kế hai chữ ký Chủ tịch + Thư ký. Binary local là các biên bản đã điền dữ liệu thật, chưa phải mẫu trắng an toàn; **chưa PASS xuất đúng mẫu**. Baseline rubric dự án đã chốt theo Mẫu 6: 2/4/4, thưởng tối đa 1, tổng không quá 10; CSDL vẫn DRAFT vì runtime chấm thật chưa triển khai. Khác biệt nguồn với QĐ 2919 được lưu để truy vết. SSO thật, xuất biểu mẫu, similarity toàn văn và các use case còn lại là thiết kế/chưa chạy.
- Docker daemon hiện không chạy; Qdrant **local mode** đã chạy. Qdrant service trong compose chưa được kiểm tra.

## Còn phải hoàn thiện trước bản nộp cuối

| Phần việc | Trạng thái hiện tại | Việc cần có để gọi là đã chạy hoàn chỉnh |
| --- | --- | --- |
| Đăng ký nhóm và đề tài SV đề xuất | Nhánh đề tài GV đã duyệt có luồng bản nháp, tự xác nhận từng thành viên và nhóm trưởng gửi; 9 test PostgreSQL, TypeScript và Vite build PASS. Chưa kiểm browser trực tiếp sau cập nhật; nhánh đề tài SV đề xuất chưa có runtime. | Kiểm tra trực quan luồng mới; xây nhánh SV đề xuất và TBM xét sau đăng ký, GVHD được phân công đồng ý rồi TBM chốt; kiểm thử hai nhánh. |
| Điều kiện, chấm điểm, Mẫu 9 | Có mô hình; baseline Mẫu 6 đã chốt (2/4/4, thưởng ≤1, tổng ≤10), rubric DB đang DRAFT; hợp đồng hai chữ ký. | Xây quyền xác nhận, runtime chấm và khóa từ chữ ký đầu; xuất đúng Mẫu 9 trắng đã kiểm; gán version rubric/policy cho đợt thật. |
| AI và kho tài liệu | Đã nạp/truy xuất corpus giả bằng FastEmbed + Qdrant local; similarity chỉ advisory. | Kiểm thử có phép trên tập tài liệu phù hợp, đánh giá sai số và quyền; chỉ bật chính sách ngưỡng nếu Khoa phê duyệt. |
| Đăng nhập và vận hành | Định danh UUID chỉ chạy DEV/TEST; chưa có SSO hoặc triển khai production. | Tích hợp đăng nhập thật, kiểm thử phân quyền và luồng đầy đủ, cấu hình triển khai/khôi phục. |

Danh sách này mô tả **chức năng chưa được kiểm chứng**, không phải câu hỏi nghiệp vụ chưa quyết định. Khi có mã nguồn và kết quả test cho một mục, cập nhật README cùng [minh chứng](docs/evidence/prototype-validation.md); không giữ nhãn “chưa chạy” sau khi đã chứng minh xong.

## Chạy trên máy phát triển

**1. Cấu hình riêng trên máy.** PostgreSQL 17 cần có database trống hoặc database dự án hiện có. Sao chép `.env.example` thành `.env` rồi điền mật khẩu/cổng thực tế; `.env` bị Gitignore. Trên máy này, `DATABASE_URL` hiện kết nối `kltn_ai` tại `127.0.0.1:5432`; Docker Compose mẫu dùng cổng **5433**. Khi cần seed hoặc bật đăng nhập UUID cho prototype, đặt `KLTN_ENV=development` (và `KLTN_DEV_AUTH=true` khi chạy API) trong đúng terminal, không cần ghi hai biến này vào `.env`. Không bật cơ chế này ở production.

**2. Cài và nâng CSDL.** Tại thư mục gốc dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.db.validate_schema
```

Để dựng database mới, mở `database/kltn-db-baseline.sql` và chạy toàn bộ file trên **database mới, trống**. Để xem bảng/cột/khóa, dùng các truy vấn chỉ đọc trong `database/kltn-ai-workbench.sql`. Với database đã có bảng, dùng Alembic migration trong `backend/migrations/versions/`; không chạy lại file baseline.

**3. Tạo dữ liệu demo tùy chọn.** Lệnh dưới đây luôn nhắm `kltn_dev`, kể cả khi `.env` đang trỏ `kltn_ai`. Chỉ chạy trên database phát triển:

```powershell
$env:KLTN_ENV = 'development'
try {
    .\.venv\Scripts\python.exe -m tools.seed_demo --execute --database kltn_dev
} finally {
    Remove-Item Env:KLTN_ENV -ErrorAction SilentlyContinue
}
```

`KLTN_ENV` chỉ tồn tại trong lần chạy này. Lệnh in UUID của SV1–SV3, GV đề xuất và TBM. Chạy lại không tạo bản ghi trùng, nhưng sẽ làm mới thời gian mở/đóng của đợt demo. Bộ test tự động tạo dữ liệu giả riêng trong transaction rồi rollback.

**4. Chạy API và React** trong hai terminal riêng.

Terminal 1 — backend API dùng dữ liệu demo từ `kltn_dev` (không đổi `.env`):

```powershell
.\.venv\Scripts\python.exe -m tools.run_demo_api
```

Terminal 2 — giao diện React (chạy `npm ci` lần đầu hoặc khi lockfile đổi):

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Chạy API và giao diện ở hai terminal riêng. Tiến trình API tự chọn `kltn_dev`, bật UUID giả lập và dùng `tmp/qdrant-prototype` nếu chưa cấu hình Qdrant service. Trước lần thử AI đầu tiên, chạy bước 5 để tạo chỉ mục corpus giả. Mở `http://127.0.0.1:5173`, nhập UUID demo để xem đề tài và thử tra cứu AI. Lấy UUID SV trong Query Tool đã kết nối `kltn_dev` bằng:

```sql
SELECT ua.id AS uuid_dev,
       ua.base_role,
       COALESCE(sp.student_code, lp.lecturer_code) AS ma_nguoi_dung,
       COALESCE(sp.display_name, lp.display_name) AS ho_ten
FROM user_account AS ua
LEFT JOIN student_profile AS sp ON sp.user_id = ua.id
LEFT JOIN lecturer_profile AS lp ON lp.user_id = ua.id
WHERE ua.external_subject LIKE 'synthetic-demo-%'
ORDER BY ua.base_role, ma_nguoi_dung;
```

UUID là khóa nội bộ tự sinh, không phải mật khẩu hay mã SV. Khi chạy thật, đăng nhập SSO của Trường sẽ xác định tài khoản rồi backend ánh xạ subject đăng nhập sang UUID nội bộ; người dùng không nhập UUID. Swagger ở `http://127.0.0.1:8000/docs`. Prototype dùng header phát triển; production trả 503 cho header này cho tới khi tích hợp SSO.

**5. Thử AI không có Docker.** Đặt `QDRANT_LOCAL_PATH=tmp/qdrant-prototype` và bỏ/để trống `QDRANT_URL` trong `.env`, rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m tools.index_corpus --manifest data/manifests/synthetic-corpus.json --root data --local-path tmp/qdrant-prototype
```

Đây là corpus **giả lập**. Với corpus được phép dùng thật, giữ file/manifest ngoài Git và dùng `--persist-metadata` để đồng bộ RepositoryItem/SearchIndexMetadata vào PostgreSQL trước khi index Qdrant. Không đưa tài liệu thật, key, mật khẩu, dữ liệu cá nhân lên Git.

## Cấu trúc để nộp

`backend/`: API, service, AI, model và migrations; `frontend/`: React; `database/`: SQL dựng mới; `docs/requirements,design,ai,decisions,references,evidence,prototype/`: sản phẩm phân tích, thiết kế và minh chứng; `tests/`: kiểm tra tự động; `data/sample,manifests/`: dữ liệu **giả**. `source/raw/` và file thao tác cá nhân luôn ở máy, không thuộc bộ source nộp.

Các quyết định nghiệp vụ hiện tại nằm trong [tài liệu quyết định](docs/decisions/quyet-dinh-du-an-2026-09-25.md); [đối chiếu CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) cho biết mỗi quyết định được lưu ở đâu. Prototype runtime chỉ chạy các luồng đã nêu trên; quyền xác nhận, chấm thật, Mẫu 9 và similarity toàn văn vẫn cần triển khai/kiểm chứng. Khi Khoa ban hành chính sách mới, cập nhật bằng revision, không sửa lịch sử.
