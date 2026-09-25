# Prototype AI và giới hạn bằng chứng

Nguồn nghiệp vụ SRC-PROJECT-DEC-20260925. Dữ liệu trong `data/` hoàn toàn giả lập và không đại diện cho 7 KLTN thật. Tài liệu thật chỉ được xử lý cục bộ khi có quyền, không commit Git.

## Pipeline đã có mã

`manifest (Pydantic) → extract TXT/MD/DOCX/text-PDF → normalize → biểu diễn riêng theo tác vụ → chunk → embedding → Qdrant`.

- `backend/ai/manifest.py` từ chối cặp origin/source_type sai, bắt buộc nguồn và provenance/version. File path phải nằm trong root cấu hình.
- `processing.py` dùng title+abstract+keywords+domain/major cho tìm đề tài; phần toàn văn chia chunk cho truy xuất bằng chứng. PDF không có text layer chưa được OCR.
- `FastEmbedProvider` dùng model pretrained `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, vector 384 chiều; **PROPOSED_MODEL**, cần đánh giá trên tiếng Việt và tập được phép. Chọn vì FastEmbed cung cấp bản ONNX cục bộ, nhẹ hơn cài PyTorch trong máy này; không fine-tune.
- Qdrant là index dẫn xuất. Mỗi point giữ source_id, source_type, origin_type, visibility, scope, version và provenance. Truy vấn lọc quyền trước khi trả kết quả. Backend prototype có thể dùng Qdrant local path; Docker Compose định hướng Qdrant service khi Docker khả dụng.
- Tìm đề tài trả Top-K và score chỉ để xếp hạng, không phải tỷ lệ đạo văn.
- `advisory_similarity` trả lexical overlap và semantic candidate score riêng, không verdict/chặn upload. Phiên bản metric thử nghiệm ghi rõ; chưa tính full-text coverage chính thức.
- RAG trước hết tìm evidence từ REGULATION/GUIDELINE/FORM trong phạm vi quyền. Khi chưa có Gemini key, trả RETRIEVAL_ONLY và citation; không sinh câu trả lời. `LLMProvider` là protocol cho tích hợp tương lai. Tài liệu retrieved là dữ liệu không đáng tin, không phải instruction.
- Gợi ý GVHD chỉ ở mức thiết kế: dùng expertise tự khai có provenance, không auto-assign và chỉ gọi VERIFIED sau khi TBM đúng Bộ môn hoặc Trưởng khoa/người được giao kiểm chứng bằng minh chứng; không tự verify.

## Thử nghiệm đã chạy

- Mô hình pretrained đã nạp được, index 1 đề tài giả lập + 1 hướng dẫn giả lập vào Qdrant local và truy vấn được hit có source_type, provenance.
- RAG trả RETRIEVAL_ONLY/citation trên câu hỏi thử; đó là kiểm tra kỹ thuật, **không** chứng minh quy định Trường đã trả lời đúng.
- Unit test dùng vector giả lập để kiểm scope, source_type, deindex/reindex và trạng thái retrieval-only. Vector giả lập không được gọi là kết quả AI.
- Chưa đánh giá precision/recall, paraphrase, false positive hoặc ngưỡng trên tập KLTN thật. Khoảng 7 mẫu là quá ít để kết luận tổng quát.

Nguồn thư viện kỹ thuật: [FastEmbed model list](https://qdrant.github.io/fastembed/examples/Supported_Models/), [Qdrant Python search/filter](https://qdrant.tech/documentation/tutorials-develop/neural-search/), [Sentence Transformers multilingual models](https://www.sbert.net/examples/sentence_transformer/training/multilingual/README.html).

`tools/index_corpus.py --persist-metadata` ghi RepositoryItem/SearchIndexMetadata vào PostgreSQL trước khi tạo index; manifest local chứa đường dẫn văn bản và được giữ ngoài Git nếu là tài liệu thật. Source ID ổn định nằm ở external_source_id, URL HTTPS ở source_url.
Khi nguồn chuyển sang `REVOKED`, lệnh index xóa toàn bộ point của `source_id` khỏi Qdrant và ghi `SearchIndexMetadata.state=REMOVED` nếu bật `--persist-metadata`; không giữ chunk của phiên bản cũ để tìm kiếm.
Năm tình huống giả lập trong `tests/test_similarity_cases.py` chỉ kiểm luồng và việc không tự phán đoán/chặn nộp. Test dùng embedding cố định; không phải số đo precision/recall của model hoặc kiểm tra tương đồng toàn văn.
