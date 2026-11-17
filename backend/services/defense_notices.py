"""Versioned internal schedules: no marks, discipline, birth dates or private reports."""
import hashlib,json
from io import BytesIO
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select,func
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment
from backend.db.models import entities as m
from backend.services import defense,workflow_notices
from backend.services.theses import now,primary_advisor,audit
from backend.services.defense_export import response

def can_view(session,user,council):
    lecturer=defense.lecturer_for(session,user)
    if lecturer:
        department=session.get(m.Department,lecturer.department_id)
        target=session.get(m.Department,council.department_id)
        return defense.manages(session,user,lecturer,council.round_id,council.department_id) or bool(department and target and defense.council_faculty_id(session,department)==defense.council_faculty_id(session,target))
    student=defense.student_for(session,user)
    if not student or student.department_id!=council.department_id:return False
    latest=session.scalar(select(m.EligibilitySnapshot).where(m.EligibilitySnapshot.student_id==student.id,m.EligibilitySnapshot.round_id==council.round_id).order_by(m.EligibilitySnapshot.version.desc()).limit(1))
    return bool(latest and latest.state=='CONFIRMED')

def draft(session,council):
    round_=session.get(m.ThesisRound,council.round_id);department=session.get(m.Department,council.department_id)
    rows=[]
    for index,slot in enumerate(session.scalars(select(m.DefenseSlot).where(m.DefenseSlot.council_id==council.id).order_by(m.DefenseSlot.starts_at,m.DefenseSlot.id)),1):
        thesis=session.get(m.Thesis,slot.thesis_id);topic=session.get(m.Topic,thesis.topic_id);advisor=primary_advisor(session,thesis.id)
        rows.append({'order':index,'topic_code':topic.code,'title':thesis.current_title,
            'students':[{'name':r['name'],'code':r['code'],'class_name':r.get('class_name','')} for r in slot.roster],
            'advisor':session.get(m.LecturerProfile,advisor.lecturer_id).display_name if advisor else '',
            'arrival_at':(slot.arrival_at or slot.starts_at).isoformat(),'starts_at':slot.starts_at.isoformat(),'ends_at':slot.ends_at.isoformat(),'room':slot.room})
    snapshot={'council':council.name,'round':round_.code,'department':department.name,'members':[{'name':p['name'],'role':defense.ROLES[p['role']]} for p in council.members],'rows':rows}
    return snapshot,hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def managed(session,user,identifier):
    council=session.get(m.DefenseCouncil,identifier)
    if not council or not defense.manages(session,user,defense.lecturer_for(session,user),council.round_id,council.department_id):raise HTTPException(403,'Bạn không quản lý hội đồng này')
    return council

def preview(session,user,identifier):
    council=managed(session,user,identifier);snapshot,fingerprint=draft(session,council)
    return {'snapshot':snapshot,'fingerprint':fingerprint}

def publish(session,user,identifier,data):
    session.execute(select(func.pg_advisory_xact_lock(66102)))
    council=managed(session,user,identifier);snapshot,fingerprint=draft(session,council)
    if not snapshot['rows']:raise HTTPException(409,'Cần xếp lịch cho đề tài trước khi công bố danh sách')
    if data.fingerprint!=fingerprint:raise HTTPException(409,'Lịch đã thay đổi. Xem lại danh sách trước khi công bố')
    latest=session.scalar(select(m.DefenseScheduleNotice).where(m.DefenseScheduleNotice.council_id==identifier).order_by(m.DefenseScheduleNotice.version.desc()).limit(1))
    if latest and latest.fingerprint==fingerprint:raise HTTPException(409,'Danh sách này đã được công bố; không cần gửi lại thông báo')
    item=m.DefenseScheduleNotice(council_id=identifier,version=latest.version+1 if latest else 1,snapshot=snapshot,fingerprint=fingerprint,published_by=user.id,published_at=now())
    session.add(item);session.flush()
    recipients={u.id for u in session.scalars(select(m.UserAccount).where(m.UserAccount.status=='ACTIVE',m.UserAccount.base_role.in_(['STUDENT','LECTURER']))) if can_view(session,u,council)}
    for recipient in recipients:workflow_notices.emit(session,user.id,{recipient},'DEFENSE_SCHEDULE_PUBLISHED','account',recipient,f'Danh sách bảo vệ {council.name} · bản {item.version} đã công bố. Xem giờ tập trung, thứ tự và địa điểm.','/defense?section=announcements')
    audit(session,user,'DEFENSE_SCHEDULE_PUBLISHED','defense_council',identifier,f'Phiên bản {item.version}',after_hash=fingerprint)
    session.commit();return {'id':item.id,'version':item.version}

def listing(session,user):
    found=set();rows=[]
    for item in session.scalars(select(m.DefenseScheduleNotice).order_by(m.DefenseScheduleNotice.published_at.desc())):
        if item.council_id in found:continue
        found.add(item.council_id);council=session.get(m.DefenseCouncil,item.council_id)
        if not can_view(session,user,council):continue
        _,fingerprint=draft(session,council)
        rows.append({'id':item.id,'version':item.version,'published_at':item.published_at,'snapshot':item.snapshot,'current':fingerprint==item.fingerprint})
    return rows

def download(session,user,identifier):
    item=session.get(m.DefenseScheduleNotice,identifier)
    if not item or not can_view(session,user,session.get(m.DefenseCouncil,item.council_id)):raise HTTPException(404,'Không tìm thấy danh sách trong phạm vi được xem')
    book=Workbook();sheet=book.active;sheet.title='Danh sách bảo vệ'
    data=item.snapshot
    sheet.append([f"DANH SÁCH BẢO VỆ KLTN · {data['round']}"]);sheet.merge_cells('A1:J1')
    council=session.get(m.DefenseCouncil,item.council_id)
    latest=session.scalar(select(m.DefenseScheduleNotice.id).where(m.DefenseScheduleNotice.council_id==item.council_id).order_by(m.DefenseScheduleNotice.version.desc()).limit(1))
    stale=latest!=item.id or draft(session,council)[1]!=item.fingerprint
    sheet.append([data['council']+(' · BẢN CŨ / LỊCH ĐANG CHỜ CẬP NHẬT' if stale else '')]);sheet.merge_cells('A2:J2')
    sheet.append(['Thứ tự','MSSV','Họ tên','Lớp','Mã đề tài','Tên đề tài','GVHD','Giờ tập trung','Giờ bảo vệ dự kiến','Phòng'])
    for row in data['rows']:
        for student in row['students']:
            sheet.append([row['order'],student['code'],student['name'],student['class_name'],row['topic_code'],row['title'],row['advisor'],defense_date(row['arrival_at']),defense_date(row['starts_at']),row['room']])
    for row in sheet:
        for cell in row:
            if isinstance(cell.value,str):cell.data_type='s'
            cell.font=Font(name='Times New Roman',size=12,bold=cell.row<=3);cell.alignment=Alignment(wrap_text=True,vertical='top')
    for column,width in zip('ABCDEFGHIJ',[9,16,27,20,24,55,28,24,24,20]):sheet.column_dimensions[column].width=width
    for row in range(4,sheet.max_row+1):sheet.row_dimensions[row].height=48
    sheet.freeze_panes='A4';sheet.auto_filter.ref=f'A3:J{sheet.max_row}';sheet.print_title_rows='1:3';sheet.page_setup.orientation='landscape';sheet.page_setup.paperSize=sheet.PAPERSIZE_A4;sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0;sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.oddFooter.left.text=f'Danh sách công bố v{item.version} · {item.published_at.astimezone(defense.VN):%d/%m/%Y %H:%M}'
    out=BytesIO();book.save(out)
    from backend.services.download_names import filename
    label=data['council'].split(' · ')[0].replace('Hội đồng bảo vệ KLTN','HD').strip()
    return response(out,filename('Lich-bao-ve-'+label,data['round'],item.version),'xlsx')

def defense_date(value):
    from datetime import datetime
    return datetime.fromisoformat(value).astimezone(defense.VN).strftime('%d/%m/%Y %H:%M')
