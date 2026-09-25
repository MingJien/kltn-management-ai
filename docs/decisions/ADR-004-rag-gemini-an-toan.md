# ADR-004 — Gemini chỉ dùng ở backend cho RAG có kiểm soát

## Trạng thái

CONFIRMED_PROJECT_DECISION.

## Bối cảnh

Thiết kế của đề tài cho phép dùng Gemini cho RAG trên dữ liệu nội bộ. Nguồn nghiệp vụ không quy định đây là dịch vụ của Trường, vì vậy không được diễn giải quyết định này thành quy định chính thức.

## Phương án

1. Gửi toàn bộ kho tài liệu hoặc prompt từ trình duyệt sang Gemini.
2. Backend authorize trước retrieval, chỉ gửi chunks cần thiết.
3. Không dùng Gemini.

## Quyết định

Backend kiểm tra authorization trước retrieval, lọc payload Qdrant theo visibility, giảm PII và gửi tối thiểu retrieved chunks cần thiết cho Gemini. Key chỉ ở backend; log không lưu nội dung chunk/prompt mặc định. Kết quả phải có citation/link nguồn và không được tự thay đổi workflow.

## Lý do

- Giảm rủi ro lộ dữ liệu và bypass quyền.
- Gemini hoặc Qdrant lỗi không được làm dừng workflow nghiệp vụ.
- Giữ được provenance để người dùng kiểm chứng câu trả lời.

## Hệ quả

- AI chỉ là hỗ trợ đọc/tra cứu, không có tool duyệt/chấm/sửa state.
- Prompt injection trong tài liệu được coi là dữ liệu không tin cậy.
- Similarity semantic chỉ dùng candidate discovery; không tự suy ra phần trăm hoặc kết luận đạo văn.

## Tham chiếu

- [Kiến trúc hệ thống](../design/architecture.md)
- [Thiết kế similarity/RAG](../ai/similarity-design.md)
- [Yêu cầu nghiệp vụ](../requirements/business-requirements.md)
