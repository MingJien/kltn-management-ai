# Minh chứng kiểm chứng prototype NV4

Ngày chạy: 25/09/2026. Môi trường local Windows; PostgreSQL 17.11, Python 3.12, SQLAlchemy 2.0.54, Alembic 1.20.0, FastAPI 0.141.1, Qdrant client 1.19.1, FastEmbed 0.8.1; Node 24.14.0, npm 11.9.0, Vite 7.3.6. Chỉ chứa dữ liệu giả lập.

| Kiểm tra thực chạy | Lệnh / cách chạy | Kết quả |
| --- | --- | --- |
| Migration hiện tại | `.\.venv\Scripts\python.exe -m alembic upgrade head` trên `kltn_dev` | PASS; head 20260925_0007 |
| Drift model/schema | `.\.venv\Scripts\python.exe -m alembic check` | PASS, “No new upgrade operations detected” |
| Kiểm thử ràng buộc | `.\.venv\Scripts\python.exe -m backend.db.validate_schema` | PASS DB-01..42; transaction rollback |
| Test API/AI | `.\.venv\Scripts\python.exe -m pytest tests -q` | 8 passed; 1 warning về TestClient/httpx của Starlette |
| Migration từ số 0 | `.\.venv\Scripts\python.exe -m tools.validate_migrations_disposable` | PASS upgrade/check/DB validation/seed giả/downgrade -1/upgrade/check trên schema ngẫu nhiên; chỉ schema đó được xóa |
| File SQL tạo mới | `.\.venv\Scripts\python.exe -m tools.validate_sql_snapshot` | PASS; 63 bảng, head 20260925_0007; 16 tiêu chí Mẫu 6 DRAFT và ba cột consent trên schema trống tạm |
| Cấu trúc vật lý `kltn_dev` | SQLAlchemy Inspector | 63 bảng/618 cột; `thesis` và `topic_registration` đều 0 row sau test |
| Build/typecheck React | `npm run build --prefix frontend` | PASS, Vite 7.3.6 |
| OpenAPI | `openapi_spec_validator.validate` cho design/runtime JSON | PASS cả hai |
| Draw.io | XML parse cho ERD/state/wireframe được sửa | PASS |
| Docker Compose syntax | `docker compose config --quiet` | PASS |
| Git whitespace | `git diff --check` | PASS |
| Browser end-to-end | agent-browser với API/React trên schema PostgreSQL ngẫu nhiên đã seed dữ liệu giả | PASS: SV chọn 2 người và gửi → SUBMITTED; GV đề xuất chấp nhận → LECTURER_ACCEPTED; TBM chốt → link Thesis ACTIVE có 2 thành viên và GVHD. Đã dừng server và xóa schema tạm. Browser console command bị treo nên chưa xác nhận log console; snapshot không có error overlay. |
| FastEmbed + Qdrant local | `.\.venv\Scripts\python.exe -m tools.index_corpus --manifest data/manifests/synthetic-corpus.json --root data --local-path tmp/qdrant-prototype` | PASS, 1 topic + 2 chunks hướng dẫn giả; model pretrained tải/nạp thành công |
| Truy vấn model thật | Qdrant local + model multilingual MiniLM | PASS kỹ thuật: topic hit SYN-TOPIC-001 score 0.715; RAG RETRIEVAL_ONLY trỏ SYN-GUIDE-001. Không suy ra chất lượng trên tài liệu thật. |

## Kiểm chứng bổ sung migration 0005

- Nâng `kltn_dev` từ 0004 → 0005: PASS. `alembic check`: không có drift. Database có 63 bảng; kiểm ràng buộc DB-01..40 PASS và rollback dữ liệu thử.
- `tools.validate_migrations_disposable`: PASS upgrade/check/DB validation/seed giả/downgrade 1 revision/re-upgrade/check trên schema tạm. `tools.validate_sql_snapshot`: PASS 63 bảng, head 0005 trên schema tạm.
- `pytest -q`: 8 passed (1 cảnh báo TestClient/httpx). `npm run build --prefix frontend`: PASS. OpenAPI design validator: PASS; 8 file Draw.io parse XML: PASS.
- DB-40 xác nhận `COMMENT_ONLY` lưu được cho GV góp ý chéo, còn giá trị decision ngoài tập bị từ chối. Quyền chỉ GVHD chính được `CONFIRM` là **hợp đồng service**, chưa có endpoint runtime tương ứng. Việc in lại Mẫu 9 trước chữ ký cũng là **thiết kế**, chưa có bản mẫu trắng để chạy thử.

## Kiểm chứng bổ sung migration 0006

- Đối chiếu migration với `SRC-MAU-06`: cả 16 dòng mã, tên và điểm tối đa khớp biểu mẫu nguồn; 3 nhóm 2/4/4, 12 tiêu chí con, 1 thưởng ≤1. Dữ liệu nạp ở `DRAFT`, chưa có `RubricAssignment` thật. Tại thời điểm kiểm chứng ngày 25/09, quyết định chọn baseline Mẫu 6 cho dự án chưa được xác nhận.
- Nâng `kltn_dev` từ 0005 → 0006: PASS. `alembic check`: không có drift. DB-01..41 PASS, gồm DB-41 kiểm rubric thật; dữ liệu thử được rollback.
- `tools.validate_migrations_disposable`: PASS nâng từ đầu/check/DB validation/seed giả/hạ 0006/nâng lại/check. `tools.validate_sql_snapshot`: PASS trên schema trống, head 0006, 63 bảng và 16 dòng rubric Mẫu 6.
- `pytest -q`: 8 passed; build React và OpenAPI/Draw.io không đổi do đây là migration dữ liệu. Chưa kiểm runtime chấm thật; tại thời điểm kiểm chứng 25/09, baseline Mẫu 6 chưa được chốt trong dự án.

## Kiểm chứng bổ sung migration 0007

- Trước khi nâng, `kltn_dev` ở 0006 và không có đăng ký/thành viên thật. Nâng lên 0007: PASS; 63 bảng/618 cột vật lý, 0 `thesis` và 0 `topic_registration` sau test. Dữ liệu cũ nếu có sẽ mặc định `PENDING`, không bị coi là đã đồng ý.
- `tools.validate_migrations_disposable`: PASS nâng/check/DB validation/seed giả/hạ 0007/nâng lại/check. `tools.validate_sql_snapshot`: PASS trên schema trống, head 0007, 16 tiêu chí Mẫu 6 và đủ ba cột consent.
- DB-01..42 PASS; DB-42 chứng minh CHECK đòi actor/thời điểm cho `ACCEPTED` và default `PENDING`. `alembic check` không thấy drift. `pytest -q`: 8 passed; React build PASS; OpenAPI design được bổ sung operation `DESIGN_ONLY` và đã validate PASS; các sơ đồ Draw.io parse XML PASS.
- **Chưa được chứng minh bằng runtime:** đúng SV tự bấm xác nhận, không gửi khi còn PENDING/DECLINED, và nhánh SV đăng ký trước rồi TBM xét đề tài. Prototype cũ vẫn cho nhóm gửi trực tiếp với Topic GV APPROVED; không dùng endpoint đó để đăng ký thật.

## Điều được chứng minh và chưa được chứng minh

- Test tích hợp dùng PostgreSQL thật, kiểm SV tự gửi nhóm, trùng active registration bị từ chối, GV không được tạo/ghép, giảng viên khác không được quyết định, TBM khác không được chốt, tạo Thesis + 3 ThesisMember + AdvisorAssignment cùng transaction, reject giải phóng đăng ký, dev auth bị tắt ở production.
- DB-27..39 kiểm MANAGED_THESIS, imported THESIS/CAPSTONE_PROJECT/TERM_PROJECT/COURSE_PROJECT, REGULATION/FORM, cặp origin sai bị chặn, index metadata không cần DocumentVersion, SimilarityMatch trỏ RepositoryItem, hai row chữ ký Mẫu 9, source ID duy nhất và URL HTTPS. **Hai row chữ ký chỉ là khả năng dữ liệu; chưa chứng minh service chuyển SIGNED đúng role.**
- Qdrant unit test dùng vector giả lập để kiểm filter quyền, source type, revoke/deindex/reindex và citation. Thêm 5 ca kiểm chức năng: sao chép, sửa nhẹ, diễn đạt lại, cùng chủ đề khác nội dung, không liên quan; mọi ca vẫn advisory, không tự chặn hoặc phán đạo văn. Vector giả không phải kết quả đánh giá AI. Model thật chỉ chạy smoke trên 2 nguồn **giả lập**. Chưa nhập 7 KLTN thật, chưa đo precision/recall, chưa chọn threshold, chưa kiểm similarity toàn văn với 5 tình huống controlled.
- Docker daemon không chạy, nên Qdrant container chưa được thử; Qdrant local mode đã chạy. Gemini chưa có key, không có generation thật; FakeLLM chưa cần trong runtime.
- Mẫu 9 local là các biên bản đã điền thông tin thật. Hiện chưa có mẫu trắng được duyệt và đánh dấu field; chưa có runtime exact export, test layout hay service hai chữ ký. Trạng thái BLOCKED_SOURCE_TEMPLATE. Cập nhật quyết định thiết kế ngày 30/09: baseline Mẫu 6 của dự án là 2/4/4, thưởng tối đa 1, tổng không quá 10; khác biệt với QĐ2919 được lưu để truy vết, không còn là câu hỏi mở. Runtime chấm và gán rubric theo đợt vẫn chưa triển khai.
- React đã chạy browser toàn luồng bằng dữ liệu giả trên schema tạm; chưa có SSO production. Kiểm thị giác pixel và browser console vẫn chưa PASS. API design rộng hơn runtime; các operation `DESIGN_ONLY` chưa được coi là PASS.

Các giới hạn này được giữ trong README/thiết kế để người xem không nhầm thiết kế với phần đã chạy.

## Kiểm chứng bổ sung ngày 30/09/2026

Lần chạy này kết nối trực tiếp tới `kltn_ai` trên PostgreSQL 17.11 tại `127.0.0.1:5432`, bằng `kltn_app`; Alembic revision là `20260925_0007`. CSDL có 63 bảng vật lý/618 cột. Trước khi seed, các bảng nghiệp vụ đăng ký và người dùng demo còn rỗng; rubric Mẫu 6 đã có 1 template DRAFT và 16 tiêu chí do migration tạo.

| Kiểm tra thực chạy | Kết quả |
| --- | --- |
| `alembic current` | PASS, `20260925_0007 (head)` trên `kltn_ai` |
| `alembic check` | PASS, không có upgrade operation mới |
| `backend.db.validate_schema` | PASS, DB-01..42; dữ liệu kiểm tra được rollback |
| `pytest tests -q --basetemp .\tmp\pytest-run-20260930-nv4demo-01 -p no:cacheprovider` | PASS, 8 test; 1 cảnh báo tương thích `TestClient/httpx` |
| `tools.seed_demo --execute` | PASS khi đặt `KLTN_ENV=development` trong phiên PowerShell; sinh 5 tài khoản, 3 hồ sơ SV, 2 GV, 1 đợt, 3 snapshot đủ điều kiện và 1 đề tài giả. Chạy lại không nhân đôi bản ghi; thời gian mở/đóng của đợt demo được làm mới. |
| API smoke test sau seed | PASS: tài khoản SV/GV/TBM giả đều lấy được ngữ cảnh (HTTP 200); SV thấy 1 đề tài và 0 đăng ký nhóm. Chỉ chạy GET, không ghi thêm dữ liệu. |
| `git diff --check` | PASS |

Seed không ghi `KLTN_ENV` vào `.env`; biến chỉ áp dụng cho lệnh hiện tại. Lần chạy đầu transaction đã commit nhưng phần in UUID kết thúc lỗi do Python Windows không mã hóa được nhãn tiếng Việt trong console cp1258. Nhãn đầu ra đã đổi sang ASCII, sau đó lệnh chạy lại thành công và xác nhận không tạo bản ghi trùng. Bộ kiểm tra cũng được sửa để dùng lại mã chức danh chuẩn đã có hoặc tạo chúng trong transaction rollback; trước đó test chèn trùng `DEPARTMENT_HEAD` trên CSDL đã seed. Thư mục pytest mặc định của Windows bị từ chối quyền truy cập, nên lần kiểm tra dùng thư mục tạm mới bên trong `D:\KLTN\tmp` và tắt pytest cache.

Seed mới chỉ tạo dữ liệu thử cho prototype trên CSDL local. Chưa chạy lại browser end-to-end sau seed; chưa có luồng từng thành viên tự xác nhận, đề tài do SV đề xuất, SSO thật, tiến độ, chấm điểm runtime hoặc xuất Mẫu 9 đúng biểu mẫu.
