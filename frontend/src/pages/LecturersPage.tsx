import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Context } from "../api";
import { request } from "../api";
import { errorMessage } from "../errors";
import PageHeader from "../components/layout/PageHeader";
import LecturerImport from "../components/domain/LecturerImport";
export default function LecturersPage({context}:{context:Context}) {
  const [departments,setDepartments]=useState<{code:string;name:string}[]>([]);
  const [error,setError]=useState("");
  useEffect(()=>{const c=new AbortController();void request<typeof departments>("/admin/departments",context.user_id,{signal:c.signal}).then(setDepartments).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));});return()=>c.abort();},[context.user_id]);
  return <><PageHeader title="Danh sách giảng viên" description="Hồ sơ GV, bộ môn, email và trạng thái kích hoạt. Tạo tài khoản từ Excel rồi chủ động chọn người nhận link."><Link className="btn btn-secondary" to="/administration">Mời từng GV / quản lý quyền</Link></PageHeader>
    {error && <p role="alert" className="alert alert-danger">{error}</p>}
    <LecturerImport directoryMode userId={context.user_id} departments={departments} refreshVersion={0} onCreated={async()=>{}}/>
  </>;
}
