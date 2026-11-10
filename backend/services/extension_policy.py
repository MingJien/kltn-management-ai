"""One date policy for approved extensions and actual faculty defense schedules."""
from calendar import monthrange
from fastapi import HTTPException


def maximum_until(starts_at):
    month = starts_at.month - 1 + 5
    year, month = starts_at.year + month // 12, month % 12 + 1
    return starts_at.replace(year=year, month=month,
        day=min(starts_at.day, monthrange(year, month)[1]))


def validate_defense_window(starts_at, until_at, meeting_start, meeting_end):
    if meeting_end <= meeting_start:
        raise HTTPException(422, "Giờ kết thúc phải sau giờ bắt đầu")
    if starts_at and meeting_start < starts_at:
        raise HTTPException(409, "Lịch bảo vệ chưa nằm trong thời gian gia hạn theo quyết định")
    if meeting_end > until_at:
        raise HTTPException(409, "Lịch bảo vệ vượt hạn gia hạn được duyệt; cần chọn kỳ bảo vệ thực tế của Khoa còn nằm trong hạn")
