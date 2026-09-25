"""Seed the exact Faculty Mẫu 6 rubric as a draft design baseline.

The form conflicts with the scoring split in QĐ 2919, so this revision does
not activate or assign it for live evaluation.
"""

from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0006"
down_revision: Union[str, None] = "20260925_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATE_CODE = "MAU-06-HOIDONG"
TEMPLATE_ID = str(uuid5(NAMESPACE_URL, "kltn:rubric:mau-6-hoi-dong:v1"))
CRITERIA = [
    ("1", None, "Hình thức", "2.0", "GROUP"),
    ("1.1", "1", "Chuyên cần", "1.0", "NORMAL"),
    ("1.2", "1", "Cấu trúc khóa luận/đồ án hợp lý, bố cục chặt chẽ, rõ ràng, trình bày theo đúng quy định. Đúng kỹ thuật soạn thảo văn bản, không có dấu hiệu đạo văn.", "0.5", "NORMAL"),
    ("1.3", "1", "Trích dẫn và trình bày tài liệu tham khảo, hình vẽ, bảng biểu rõ ràng, đúng quy định, không có lỗi chính tả, không lỗi in ấn.", "0.5", "NORMAL"),
    ("2", None, "Nội dung", "4.0", "GROUP"),
    ("2.1", "2", "Nêu được tính cấp thiết của đề tài, làm rõ tổng quan các công trình nghiên cứu, xác định mục đích, nhiệm vụ, đối tượng, phạm vi, nghiên cứu rõ ràng, hợp lý.", "0.5", "NORMAL"),
    ("2.2", "2", "Nội dung nghiên cứu: Khối lượng công việc hợp lí; tư liệu phong phú, chính xác, phù hợp mục đích nghiên cứu.", "0.5", "NORMAL"),
    ("2.3", "2", "Phương pháp nghiên cứu: Biết vận dụng các phương pháp nghiên cứu phù hợp với nội dung nghiên cứu của đề tài; trình bày nội dung có hệ thống khoa học, logic.", "1.0", "NORMAL"),
    ("2.4", "2", "Khả năng áp dụng các giải thuật hiệu quả, số liệu chính xác; Khả năng giải quyết vấn đề, đầy đủ minh chứng khoa học; Khả năng suy luận, phân tích, tổng hợp tốt; có khả năng sáng tạo.", "1.0", "NORMAL"),
    ("2.5", "2", "Kết quả nghiên cứu: - Nêu được kết quả đạt được phù hợp với mục tiêu nghiên cứu của đề tài; - Kết quả có giá trị về mặt lý luận và thực tiễn khoa học; - Có đánh giá, nhận xét kết quả, dự đoán tương lai (nếu cần).", "0.5", "NORMAL"),
    ("2.6", "2", "Kết luận, kiến nghị phù hợp với nội dung nghiên cứu.", "0.5", "NORMAL"),
    ("3", None, "Demo và trả lời câu hỏi", "4.0", "GROUP"),
    ("3.1", "3", "Demo không có lỗi, không vi phạm luật an ninh mạng/luật sở hữu trí tuệ; Có quy trình sử dụng/hướng dẫn sử dụng rõ ràng; Có triển khai, có khả năng ứng dụng.", "1.0", "NORMAL"),
    ("3.2", "3", "Giao diện thân thiện, hợp lý; Các chức năng đáp ứng được yêu cầu của đề tài; Độ tin cậy, độ tương thích; Tốc độ, bảo mật, chi phí hợp lý.", "2.0", "NORMAL"),
    ("3.3", "3", "Thuyết trình lưu loát, slide trình chiếu rõ ràng, có sáng tạo; Trả lời đúng, đáp ứng được yêu cầu các câu hỏi đặt ra.", "1.0", "NORMAL"),
    ("4", None, "Điểm thưởng (nếu có công bố kết quả nghiên cứu trên tập chí khoa học hoặc hội thảo trong và ngoài nước). Tổng điểm là 10 (kể cả điểm thưởng)", "1.0", "BONUS"),
]


def _id(code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"kltn:rubric:mau-6-hoi-dong:v1:{code}"))


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    op.execute(sa.text(
        f"INSERT INTO rubric_template (id, code, name, version_no, source_ref, state) VALUES "
        f"('{TEMPLATE_ID}', '{TEMPLATE_CODE}', 'Mẫu 6 - Phiếu đánh giá Hội đồng', 1, 'SRC-MAU-06', 'DRAFT')"
    ))
    for order_no, (code, parent, label, maximum, kind) in enumerate(CRITERIA, 1):
        parent_sql = f"'{_id(parent)}'" if parent is not None else "NULL"
        op.execute(sa.text(
            "INSERT INTO rubric_criterion "
            "(id, rubric_template_id, parent_id, code, label, max_points, criterion_type, order_no) VALUES "
            f"('{_id(code)}', '{TEMPLATE_ID}', {parent_sql}, {_sql_string(code)}, "
            f"{_sql_string(label)}, {maximum}, '{kind}', {order_no})"
        ))


def downgrade() -> None:
    op.execute(sa.text(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM rubric_assignment WHERE rubric_template_id = "
        f"'{TEMPLATE_ID}') THEN RAISE EXCEPTION 'Mau 6 rubric is assigned; refusing downgrade'; "
        "END IF; END $$"
    ))
    op.execute(sa.text(f"DELETE FROM rubric_criterion WHERE rubric_template_id = '{TEMPLATE_ID}'"))
    op.execute(sa.text(f"DELETE FROM rubric_template WHERE id = '{TEMPLATE_ID}'"))
