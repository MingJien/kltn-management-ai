# Hệ thống quản lý khóa luận tốt nghiệp tích hợp chatbot AI

Repository này chứa sản phẩm phân tích và thiết kế NV4 cùng **prototype dùng tiếp được**: PostgreSQL, FastAPI, React và thử nghiệm truy xuất AI trên dữ liệu giả lập. Chưa phải hệ thống production; không có hồ sơ sinh viên hoặc 7 KLTN thật trong Git.

## Nên mở gì trước?

| Muốn xem | Tệp |
| --- | --- |
| Quyết định mới và điều chưa chốt | [Quyết định 25/09](docs/decisions/quyet-dinh-du-an-2026-09-25.md), [vấn đề còn mở](docs/requirements/open-issues.md), [18 câu hỏi GVHD](docs/requirements/18-cau-hoi-gvhd-mapping.md) |
| Nghiệp vụ, vai trò, use case, quyền | [Yêu cầu](docs/requirements/business-requirements.md), [quy tắc](docs/requirements/business-rules.md), [quy trình](docs/requirements/business-process.md), [use case](docs/requirements/use-case-catalog.md), [phân quyền](docs/requirements/permission-matrix.md) |
| CSDL và ý nghĩa bảng/cột | [ERD](docs/design/erd.md), [từ điển dữ liệu](docs/design/data-dictionary.md), [giải thích dễ đọc](docs/design/database-explained.md), [quy tắc dữ liệu](docs/design/database-rules.md), [đối chiếu quyết định với CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) |
| Tệp CSDL PostgreSQL | [Tạo database mới](database/kltn-init-empty.sql), [cách dùng](database/README.md). Hai tệp SQL thao tác pgAdmin (`kltn-ai-workbench.sql`, `kltn-ai-updates.sql`) chỉ lưu trên máy. |
| Cập nhật CSDL **đã có bảng** | [Alembic migrations](backend/migrations/versions/) từ 0001 đến 0005; **không chạy lại file SQL tạo mới** |
| API và giao diện | [FastAPI](backend/api/main.py), [OpenAPI runtime](docs/prototype/openapi-runtime.json), [thiết kế API toàn miền](docs/design/openapi.yaml), [React](frontend/src/App.tsx), [wireframe](docs/design/wireframes.md) |
| AI và biểu mẫu | [Prototype AI](docs/ai/prototype.md), [thiết kế tương đồng](docs/ai/similarity-design.md), [thiết kế xuất biểu mẫu](docs/design/xuat-bieu-mau.md) |
| Kiểm chứng | [Minh chứng prototype](docs/evidence/prototype-validation.md), [ma trận truy vết](docs/design/traceability-matrix.md) |

## Trạng thái thực tế

- CSDL có **62 bảng mô hình, 614 cột**; thêm `alembic_version` là **63 bảng, 615 cột vật lý**. `kltn_dev` trên máy kiểm tra ở revision `20260925_0005` và không có dòng `thesis` nghiệp vụ sau test. Các migration cũ 0001/0002 không sửa.
- Corpus giờ phân biệt KLTN đang quản lý, tài liệu học thuật nhập và nguồn chính thức. KLTN cũ không cần tạo Thesis/Sinh viên giả. Test DB-01..40 PASS, gồm COMMENT_ONLY cho góp ý chéo.
- Prototype API chạy luồng SV tự gửi nhóm 1–3 → giảng viên đề xuất chấp nhận/từ chối → TBM đúng bộ môn chốt để tạo Thesis/ThesisMember/AdvisorAssignment nguyên tử. Nhóm bị từ chối có thể đăng ký lại; đề tài đã chốt bị khóa. 8 pytest PASS, gồm kiểm luồng trên PostgreSQL và 5 tình huống similarity giả lập.
- React có màn đề tài, đăng ký/quyết định, chi tiết khóa luận và tìm đề tài/tra cứu nguồn. Build/typecheck PASS. Đã chạy trình duyệt với schema PostgreSQL tạm và tài khoản giả lập: SV gửi nhóm 2 người → GV chấp nhận → TBM chốt → React hiển thị Thesis ACTIVE; schema tạm đã xóa.
- FastEmbed pretrained + Qdrant local truy xuất được corpus giả lập có source_type/provenance; RAG trả citation ở chế độ RETRIEVAL_ONLY. **Không có Gemini key, không có kết luận chất lượng AI trên 7 KLTN, không có ngưỡng 90% đã chốt.**
- Mẫu 9 đã được thiết kế hai chữ ký Chủ tịch + Thư ký. Binary local là các biên bản đã điền dữ liệu thật, chưa phải mẫu trắng an toàn; **chưa PASS xuất đúng mẫu**. Mẫu 6 còn xung đột cơ cấu điểm với QĐ 2919. SSO thật, xuất biểu mẫu, similarity toàn văn và các use case còn lại là thiết kế/chưa chạy.
- Docker daemon hiện không chạy; Qdrant **local mode** đã chạy. Qdrant service trong compose chưa được kiểm tra.

## Chạy trên máy phát triển

**1. Cấu hình riêng trên máy.** PostgreSQL 17 cần có database trống hoặc database dự án hiện có. Sao chép `.env.example` thành `.env` rồi điền mật khẩu/cổng thực tế; `.env` bị Gitignore. Đối với PostgreSQL native trên máy kiểm tra này, server ở cổng **5432**, còn Docker Compose mẫu dùng **5433**. Không nhầm hai kết nối. Chỉ ở database thử nghiệm, đặt `KLTN_ENV=development` và `KLTN_DEV_AUTH=true` để dùng UUID demo. Không bật cơ chế này ở production.

**2. Cài và nâng CSDL.** Tại thư mục gốc dự án:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.db.validate_schema
```

Để dựng database mới, mở `database/kltn-init-empty.sql` và chạy toàn bộ file trên **database mới, trống**. Để xem bảng/cột/khóa, dùng các truy vấn chỉ đọc trong `database/kltn-ai-workbench.sql`. Với database đã có bảng, dùng Alembic migration trong `backend/migrations/versions/`; không chạy lại file init.

**3. Tạo dữ liệu demo tùy chọn.** Chỉ chạy trên database phát triển mà bạn cho phép chứa dữ liệu **giả lập**:

```powershell
.\.venv\Scripts\python.exe -m tools.seed_demo --execute
```

Lệnh in ra UUID của SV1, GV đề xuất và TBM để nhập vào giao diện. Không chạy trên database chứa dữ liệu thật. Test tự động tạo dữ liệu giả trong transaction và rollback.

**4. Chạy API và React** trong hai terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000
npm ci --prefix frontend
npm run dev --prefix frontend
```

Mở `http://127.0.0.1:5173`, nhập UUID demo để chọn đề tài, gửi nhóm, đổi sang UUID GV để chấp nhận, rồi UUID TBM để chốt. Swagger của API ở `http://127.0.0.1:8000/docs`. Prototype dùng header phát triển; production trả 503 cho header này cho tới khi tích hợp SSO.

**5. Thử AI không có Docker.** Đặt `QDRANT_LOCAL_PATH=tmp/qdrant-prototype` và bỏ/để trống `QDRANT_URL` trong `.env`, rồi chạy:

```powershell
.\.venv\Scripts\python.exe -m tools.index_corpus --manifest data/manifests/synthetic-corpus.json --root data --local-path tmp/qdrant-prototype
```

Đây là corpus **giả lập**. Với corpus được phép dùng thật, giữ file/manifest ngoài Git và dùng `--persist-metadata` để đồng bộ RepositoryItem/SearchIndexMetadata vào PostgreSQL trước khi index Qdrant. Không đưa tài liệu thật, key, mật khẩu, dữ liệu cá nhân lên Git.

## Cấu trúc để nộp

`backend/`: API, service, AI, model và migrations; `frontend/`: React; `database/`: SQL dựng mới; `docs/requirements,design,ai,decisions,references,evidence,prototype/`: sản phẩm phân tích, thiết kế và minh chứng; `tests/`: kiểm tra tự động; `data/sample,manifests/`: dữ liệu **giả**. `source/raw/` và file thao tác cá nhân luôn ở máy, không thuộc bộ source nộp.

Bộ phân tích, thiết kế và schema CSDL cho phạm vi NV4 hiện tại đã chốt ở [quyết định dự án](docs/decisions/quyet-dinh-du-an-2026-09-25.md), [đối chiếu CSDL](docs/design/doi-chieu-quyet-dinh-csdl.md) và [điểm kiểm soát khi vận hành](docs/requirements/open-issues.md). Prototype runtime chỉ chạy các luồng đã nêu trên; quyền xác nhận, chấm thật, Mẫu 9 và similarity toàn văn vẫn cần triển khai/kiểm chứng. Khi Khoa ban hành chính sách mới, cập nhật bằng revision, không sửa lịch sử.
