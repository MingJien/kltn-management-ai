import {useEffect,useState} from "react";
import {Link,useParams} from "react-router-dom";
import {request} from "../api";
import {errorMessage} from "../errors";
import type {LecturerProfile} from "../lecturerProfiles";
import LecturerProfileView from "../components/domain/LecturerProfileView";
import PageHeader from "../components/layout/PageHeader";
export default function LecturerProfilePage({userId}:{userId:string}) {
  const {lecturerId}=useParams();const [data,setData]=useState<LecturerProfile|null>(null),[error,setError]=useState("");
  useEffect(()=>{const c=new AbortController();setData(null);setError("");void request<LecturerProfile>(`/lecturer-profiles/${lecturerId}`,userId,{signal:c.signal}).then(result=>{if(!c.signal.aborted)setData(result);}).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));});return()=>c.abort();},[lecturerId,userId]);
  return <div className="lecturer-page"><PageHeader title="Hồ sơ giảng viên" description="Thông tin định danh và hồ sơ chuyên môn đã được duyệt."/><Link className="btn btn-secondary" to="/lecturers">← Danh sách giảng viên</Link>{error?<p className="alert alert-danger" role="alert">{error}</p>:data?<div className="lecturer-profile-full"><LecturerProfileView profile={data}/></div>:<p role="status">Đang tải hồ sơ giảng viên…</p>}</div>;
}
