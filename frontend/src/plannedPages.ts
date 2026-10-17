export const plannedPages = {
  changes: {title: "Đổi đề tài, rút và gia hạn", description: "Theo dõi yêu cầu điều chỉnh khóa luận và quyết định có căn cứ."},
  reports: {title: "Báo cáo và thống kê", description: "Tổng hợp số liệu theo đợt, tiến độ, bảo vệ và kết quả."},
  expertise: {title: "Chuyên môn giảng viên", description: "Khai báo chuyên môn và ghi nhận kết quả xác minh theo thẩm quyền."},
  council: {title: "Hội đồng bảo vệ", description: "Quản lý thành viên hội đồng và phân công khóa luận bảo vệ."},
  defense: {title: "Lịch bảo vệ", description: "Lập lịch, địa điểm và phiên bảo vệ khóa luận."},
  evaluation: {title: "Phản biện và chấm điểm", description: "Nhận xét phản biện và đánh giá theo biểu mẫu của Khoa."},
  results: {title: "Kết quả và biên bản", description: "Tổng hợp kết quả bảo vệ và lập biên bản theo quy trình chính thức."},
  repository: {title: "Kho khóa luận", description: "Tra cứu khóa luận đã được phép công bố và lưu trữ."},
  chatbot: {title: "Chatbot AI", description: "Hỏi đáp dựa trên tài liệu và quy định được phép sử dụng."},
  similarity: {title: "Kiểm tra tương đồng", description: "Đối chiếu nội dung với nguồn được phép và xem kết quả tham khảo."},
} as const;

export type PlannedPageId = keyof typeof plannedPages;
