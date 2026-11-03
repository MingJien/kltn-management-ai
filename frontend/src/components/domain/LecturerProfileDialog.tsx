import {useCallback,useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {request} from "../../api";
import {errorMessage} from "../../errors";
import type {LecturerProfile} from "../../lecturerProfiles";
import Dialog from "../ui/Dialog";
import LecturerProfileView from "./LecturerProfileView";

export function LecturerProfileDialog({lecturerId,userId,onClose}:{lecturerId:string;userId:string;onClose:()=>void}) {
  const [data,setData]=useState<LecturerProfile|null>(null),[error,setError]=useState("");
  const load=useCallback(async(signal?:AbortSignal)=>{setError("");const result=await request<LecturerProfile>(`/lecturer-profiles/${lecturerId}`,userId,{signal});if(!signal?.aborted)setData(result);},[lecturerId,userId]);
  useEffect(()=>{const c=new AbortController();setData(null);void load(c.signal).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));});return()=>c.abort();},[load]);
  return <Dialog open title="Hồ sơ giảng viên" size="lg" onClose={onClose}>
    {error?<div className="alert alert-danger" role="alert">{error}<button className="btn btn-secondary" onClick={()=>void load().catch(e=>setError(errorMessage(e)))}>Thử lại</button></div>:data?<LecturerProfileView profile={data}/>:<p role="status">Đang tải hồ sơ giảng viên…</p>}
  </Dialog>;
}

export default function LecturerProfileLink({lecturerId,name,userId,className="lecturer-link"}:{lecturerId:string|null|undefined;name:string|null|undefined;userId:string;className?:string}) {
  const [open,setOpen]=useState(false);
  if(!lecturerId||!name)return <span>{name||"Chưa phân công"}</span>;
  return <><Link className={className} to={`/lecturers/${lecturerId}`} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();e.stopPropagation();setOpen(true);}}>{name}</Link>
    {open&&<LecturerProfileDialog key={lecturerId} lecturerId={lecturerId} userId={userId} onClose={()=>setOpen(false)}/>}</>;
}
