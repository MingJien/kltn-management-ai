"""Faculty-scoped academic choices and transparent, verified-profile suggestions."""
import re
import unicodedata
from fastapi import HTTPException
from sqlalchemy import select
from backend.db.models import entities as m

def department_ids(session, department_id):
    department=session.get(m.Department,department_id)
    if not department:
        return set()
    return set(session.scalars(select(m.Department.id).where(m.Department.faculty_id==department.faculty_id,
        m.Department.active.is_(True))))

def compatible(session, left, right):
    return right in department_ids(session,left)

def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.lower().replace('đ','d')) if unicodedata.category(c)!='Mn')

def suggestion(lecturer, text=''):
    matched=[]
    if lecturer.profile_verified_at:
        haystack=normalize(text)
        words=set(re.findall(r'[a-z0-9]{3,}',haystack))-{'khoa','luan','tot','nghiep','xay','dung','nghien','cuu','thong','thuc','hien'}
        for label in lecturer.profile_data.get('specializations',[])+lecturer.profile_data.get('research_interests',[]):
            phrase=normalize(label)
            terms=set(re.findall(r'[a-z0-9]{3,}',phrase))-{'khoa','luan','nghien','cuu'}
            if phrase and (phrase in haystack or len(terms & words)>=2):
                matched.append(label)
    return {'recommended':bool(matched),'recommendation_reasons':matched[:3],
        'profile_verified':bool(lecturer.profile_verified_at)}

def lecturer_choices(session,department_id,text=''):
    rows=session.scalars(select(m.LecturerProfile).join(m.UserAccount,m.UserAccount.id==m.LecturerProfile.user_id)
        .where(m.LecturerProfile.department_id.in_(department_ids(session,department_id)),
            m.UserAccount.status=='ACTIVE',m.UserAccount.base_role=='LECTURER')).all()
    rows.sort(key=lambda row:(-len(suggestion(row,text)['recommendation_reasons']),
        row.department_id!=department_id,normalize(row.display_name),str(row.id)))
    return rows
