# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Repository này chứa sản phẩm phân tích và thiết kế cùng mã nguồn phát triển: PostgreSQL, FastAPI, React và thử nghiệm truy xuất AI trên dữ liệu giả lập. PostgreSQL là nguồn dữ liệu nghiệp vụ chính; AI chỉ hỗ trợ tra cứu và tương đồng, không tự chấm đạo văn. Chưa phải hệ thống production; không có hồ sơ sinh viên hoặc 7 KLTN thật trong Git.

## Nên mở gì trước?

| Muốn xem | Tệp |
| --- | --- |
| Quyết định nghiệp vụ đã chốt | [Quyết định thiết kế 25/09](docs/decisions/quyet-dinh-du-an-2026-09-25.md), [giải đáp GVHD](docs/requirements/18-cau-hoi-gvhd-mapping.md) |
| Phạm vi ưu tiên sau góp ý GV 03/10 | [CSDL lõi 32 bảng và thứ tự triển khai](docs/design/database-scope-review.md) |
| Nghiệp vụ, vai trò, use case, quyền | [Yêu cầu](docs/requirements/business-requirements.md), [quy tắc](docs/requirements/business-rules.md), [quy trình](docs/requirements/business-process.md), [use case](docs/requirements/use-case-catalog.md), [phân quyền](docs/requirements/permission-matrix.md) |
| CSDL và ý nghĩa bảng/cột | [ERD tổng thể](docs/design/erd.md), [ERD theo 6 cụm](docs/design/erd-clusters/README.md), [từ điển dữ liệu](docs/design/data-dictionary.md), [rubric Mẫu 6](docs/design/rubric-mau-6.md), [quy tắc dữ liệu](docs/design/database-rules.md), [đối chiếu quyết định với CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) |
| Tệp CSDL PostgreSQL | [CSDL lõi 32 bảng để GV xem](database/core/kltn-core-schema.sql), [cách dựng riêng](database/core/README.md); [schema đầy đủ 62 bảng để tham khảo](database/kltn-schema-consolidated.sql), [baseline đầy đủ](database/kltn-db-baseline.sql), [cách phân biệt](database/README.md). Hai tệp SQL thao tác pgAdmin (`kltn-ai-workbench.sql`, `kltn-ai-updates.sql`) chỉ lưu trên máy. |
| Cập nhật CSDL **đã có bảng** | [Alembic migrations](backend/migrations/versions/) từ 0001 đến 0011; **không chạy lại file SQL tạo mới** |
| API và giao diện | [FastAPI](backend/api/main.py), [OpenAPI runtime](docs/prototype/openapi-runtime.json), [thiết kế API toàn miền](docs/design/openapi.yaml), [React](frontend/src/App.tsx), [wireframe](docs/design/wireframes.md), [quyết định đăng nhập email/mật khẩu](docs/design/local-auth.md) |
| AI và biểu mẫu | [Prototype AI](docs/ai/prototype.md), [thiết kế tương đồng](docs/ai/similarity-design.md), [thiết kế xuất biểu mẫu](docs/design/xuat-bieu-mau.md) |
| Kiểm chứng | [Minh chứng prototype](docs/evidence/prototype-validation.md), [ma trận truy vết](docs/design/traceability-matrix.md) |

## Trạng thái thực tế

- Ngày 04/10, hai database local ở PostgreSQL 17.11 đang ở revision `20261004_0011`, **63 bảng vật lý/622 cột** (`62 bảng mô hình/621 cột` cộng `alembic_version`). `kltn_ai` là database mô hình đầy đủ; `kltn_dev` là database phát triển có dữ liệu giả. `eligibility_snapshot` giữ tỷ lệ tín chỉ và GPA khi có nguồn đối chiếu, cùng kết quả theo đợt/người xác nhận; không lưu tình trạng kỷ luật hoặc án tích chi tiết. Đăng nhập email/mật khẩu với Argon2id và cookie phiên đã có runtime cho năm tài khoản giả trong `kltn_dev`; chưa có đăng ký tài khoản và email xác minh dùng thật.
- Theo góp ý GV, đã tách [file CSDL lõi 32 bảng](database/core/kltn-core-schema.sql): 25 bảng nền, 4 bảng giữ FK/góp ý, 2 bảng lịch sử tên/audit và 1 bảng yêu cầu bổ sung của luồng đã chạy. File đã chạy trong schema PostgreSQL tạm và được đối chiếu bằng `pg_dump --schema-only`: **32 PK/69 FK**; schema tạm đã xóa. **Database `kltn_core` chưa được tạo trên máy**. Runtime vẫn chạy trên `kltn_dev` có mô hình đầy đủ 62 bảng. [Phạm vi mới](docs/design/database-scope-review.md) phân biệt bản lõi và bản đầy đủ; chưa có migration riêng cho database lõi. Mã đề tài theo năm, yêu cầu bổ sung và minh chứng đã nối vào runtime.
- Corpus giờ phân biệt KLTN đang quản lý, tài liệu học thuật nhập và nguồn chính thức. KLTN cũ không cần tạo Thesis/Sinh viên giả. Test DB-01..45 PASS, gồm COMMENT_ONLY, baseline Mẫu 6, giới hạn tín chỉ/GPA và ràng buộc tài khoản local.
- API và React hiện có luồng GV tạo/sửa/gửi đề tài → TBM đúng bộ môn duyệt/trả/từ chối → SV lập nhóm 1–3 → từng thành viên tự xác nhận → nhóm trưởng gửi → GV tiếp nhận chấp nhận/từ chối. Quyền, trạng thái, phiên bản khi quyết định, lịch sử tên đề tài và audit được kiểm ở backend. Từ `SUBMITTED` thành viên bị khóa. API chốt thành Thesis/AdvisorAssignment do TBM vẫn có từ prototype trước nhưng ngoài mốc triển khai này.
- React có màn đăng nhập email, đề tài, đăng ký nhóm/xác nhận từng thành viên/quyết định, chi tiết khóa luận và tìm đề tài/tra cứu nguồn. TypeScript/Vite build và 24 test backend PASS ngày 04/10; test dữ liệu giả trong transaction rollback trên PostgreSQL. Browser đã kiểm GV tạo → TBM sửa tên/duyệt → SV1 lập nhóm → SV2 tự xác nhận → SV1 gửi → GV chấp nhận, có tải minh chứng PDF. AI trả nguồn dữ liệu giả ở chế độ `RETRIEVAL_ONLY`, chưa gọi Gemini.
- FastEmbed pretrained + Qdrant local truy xuất được corpus giả lập có source_type/provenance; RAG trả citation ở chế độ RETRIEVAL_ONLY. **Gemini bị khóa ở backend** cho đến khi có bộ lọc chỉ gửi câu hỏi đã lọc và quy định/tài liệu đã công bố. Không có kết luận chất lượng AI trên 7 KLTN hoặc ngưỡng 90% đã chốt.
- Mẫu 9 đã được thiết kế hai chữ ký Chủ tịch + Thư ký; **chưa PASS xuất đúng mẫu** vì chưa có mẫu trắng. Baseline rubric dự án theo Mẫu 6: 2/4/4, thưởng tối đa 1, tổng không quá 10; CSDL vẫn DRAFT vì runtime chấm thật chưa triển khai. Đăng nhập demo local đã chạy nhưng chưa có cấp tài khoản từ danh sách Khoa, xác minh email hay khôi phục mật khẩu. OIDC scaffold cũ chưa kết nối Trường; xuất biểu mẫu, similarity toàn văn và các use case còn lại chưa chạy hoàn chỉnh.
- Docker daemon hiện không chạy; Qdrant **local mode** đã chạy. Qdrant service trong compose chưa được kiểm tra.

## Còn phải hoàn thiện trước bản nộp cuối

| Phần việc | Trạng thái hiện tại | Việc cần có để gọi là đã chạy hoàn chỉnh |
| --- | --- | --- |
| Đề tài và đăng ký | GV tạo/duyệt/đăng ký/chấp nhận đã kiểm browser. Có thêm SV tự đề xuất → TBM xác nhận GV → GV quyết định; kiểm tự động và browser trên dữ liệu giả. | Runtime vẫn dùng `kltn_dev` đầy đủ; nếu chuyển sang database lõi riêng cần migration/configuration riêng. |
| Điều kiện, chấm điểm, Mẫu 9 | Có mô hình; baseline Mẫu 6 đã chốt (2/4/4, thưởng ≤1, tổng ≤10), rubric DB đang DRAFT; hợp đồng hai chữ ký. | Xây quyền xác nhận, runtime chấm và khóa từ chữ ký đầu; xuất đúng Mẫu 9 trắng đã kiểm; gán version rubric/policy cho đợt thật. |
| AI và kho tài liệu | Đã nạp/truy xuất corpus giả bằng FastEmbed + Qdrant local; similarity chỉ advisory. | Kiểm thử có phép trên tập tài liệu phù hợp, đánh giá sai số và quyền; chỉ bật chính sách ngưỡng nếu Khoa phê duyệt. |
| Đăng nhập và vận hành | Demo có login email/mật khẩu Argon2id, cookie phiên, logout và kiểm quyền backend. Năm tài khoản giả nằm ở `kltn_dev`. | Cấp tài khoản từ danh sách SV/GV đã xác thực, gửi xác minh email, khôi phục mật khẩu, giới hạn thử sai dùng chung nhiều tiến trình trước khi vận hành thật. |

Danh sách này mô tả **chức năng chưa được kiểm chứng**, không phải câu hỏi nghiệp vụ chưa quyết định. Khi có mã nguồn và kết quả test cho một mục, cập nhật README cùng [minh chứng](docs/evidence/prototype-validation.md); không giữ nhãn “chưa chạy” sau khi đã chứng minh xong.

## Chạy trên máy phát triển

**1. Cấu hình riêng trên máy.** PostgreSQL 17 cần có database trống hoặc database dự án hiện có. Sao chép `.env.example` thành `.env` rồi điền mật khẩu/cổng thực tế; `.env` bị Gitignore. Trên máy này, `DATABASE_URL` hiện kết nối `kltn_ai` tại `127.0.0.1:5432`; Docker Compose mẫu dùng cổng **5433**. Lệnh seed đặt `KLTN_ENV=development` chỉ cho tiến trình đó; `tools.run_demo_api` tự chọn `kltn_dev` và dùng đăng nhập email. Không bật `KLTN_DEV_AUTH` trong vận hành thật.

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
    .\.venv\Scripts\python.exe -m tools.seed_demo --execute --database kltn_dev --create-credentials
} finally {
    Remove-Item Env:KLTN_ENV -ErrorAction SilentlyContinue
}
```

`KLTN_ENV` chỉ tồn tại trong lần chạy này. Lần đầu clone dùng `--create-credentials` tạo tệp tài khoản ngẫu nhiên nếu tệp chưa có; không ghi đè tệp hiện có. Seed **đọc** năm email/mật khẩu từ `database/tai-khoan-demo.local.csv` chỉ có trên máy, bị Gitignore; chạy lại sẽ áp dụng đúng nội dung file và làm mới thời gian đợt, không tự tạo mật khẩu khác. Mở file này để sao chép tài khoản demo. Bộ test tự tạo dữ liệu giả trong transaction rồi rollback.

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

Chạy API và giao diện ở hai terminal riêng. Tiến trình API tự chọn `kltn_dev`, tắt UUID header cho demo và dùng `tmp/qdrant-prototype` nếu chưa cấu hình Qdrant service. Trước lần thử AI đầu tiên, chạy bước 5 để tạo chỉ mục corpus giả. Mở `http://localhost:5173` hoặc `http://127.0.0.1:5173`; giao diện mặc định gọi API bằng **cùng hostname** với tab đang mở để cookie đăng nhập hoạt động. Nhập email và mật khẩu trong [file demo chỉ lưu trên máy](database/tai-khoan-demo.local.csv). Lần lượt đăng nhập GV đề xuất, TBM và SV1/SV2 để đi hết luồng. Bộ test tự động bật UUID header riêng trong môi trường TEST; giao diện không dùng UUID.

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

UUID trong truy vấn là khóa nội bộ để đối chiếu khi cần, không dùng đăng nhập. [Trạng thái vòng đời tài khoản](docs/design/local-auth.md) phân biệt demo đã chạy với phần cần có trước khi cấp tài khoản thật. Swagger ở `http://localhost:8000/docs`. Header UUID chỉ được backend chấp nhận trong DEV/TEST.

**5. Thử AI không có Docker.** Đặt `QDRANT_LOCAL_PATH=tmp/qdrant-prototype` và bỏ/để trống `QDRANT_URL` trong `.env`, rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m tools.index_corpus --manifest data/manifests/synthetic-corpus.json --root data --local-path tmp/qdrant-prototype
```

Đây là corpus **giả lập**. Với corpus được phép dùng thật, giữ file/manifest ngoài Git và dùng `--persist-metadata` để đồng bộ RepositoryItem/SearchIndexMetadata vào PostgreSQL trước khi index Qdrant. Không đưa tài liệu thật, key, mật khẩu, dữ liệu cá nhân lên Git.

## Cấu trúc để nộp

`backend/`: API, service, AI, model và migrations; `frontend/`: React; `database/`: SQL dựng mới; `docs/requirements,design,ai,decisions,references,evidence,prototype/`: sản phẩm phân tích, thiết kế và minh chứng; `tests/`: kiểm tra tự động; `data/sample,manifests/`: dữ liệu **giả**. `source/raw/` và file thao tác cá nhân luôn ở máy, không thuộc bộ source nộp.

Các quyết định nghiệp vụ hiện tại nằm trong [tài liệu quyết định](docs/decisions/quyet-dinh-du-an-2026-09-25.md); [đối chiếu CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) cho biết mỗi quyết định được lưu ở đâu. Prototype runtime chỉ chạy các luồng đã nêu trên; quyền xác nhận, chấm thật, Mẫu 9 và similarity toàn văn vẫn cần triển khai/kiểm chứng. Khi Khoa ban hành chính sách mới, cập nhật bằng revision, không sửa lịch sử.

### Đăng ký theo loại đề tài

- Đề tài GV: chọn trong danh sách đã duyệt, mở form cá nhân/nhóm theo sức chứa. Một SV đại diện lập nhóm; mọi thành viên phải tự xác nhận trước khi gửi.
- Đề tài SV: chọn **Tự đề xuất đề tài**, điền đề xuất và GV mong muốn, lập đăng ký rồi gửi bộ môn. TBM sửa tên nếu cần và xác nhận/chọn GV cùng bộ môn; GV được từ chối có lý do.
- Minh chứng từng thành viên: PDF/PNG/JPEG ≤5 MB, tải trước khi gửi; chỉ người được phép truy cập hồ sơ mới tải được. Tệp giữ trên máy, không gửi AI; chưa có antivirus nên lưu trạng thái QUARANTINED và chỉ tải dạng attachment.
