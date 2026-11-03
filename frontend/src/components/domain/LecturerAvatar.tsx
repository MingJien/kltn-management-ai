import {useEffect,useState} from "react";
import {UserRound} from "lucide-react";
import {apiAssetUrl} from "../../api";

export default function LecturerAvatar({url,name,size="md"}:{url?:string|null;name?:string;size?:"xs"|"sm"|"md"|"lg"}) {
  const [failed,setFailed]=useState(false);
  useEffect(()=>setFailed(false),[url]);
  return <span className={`lecturer-avatar lecturer-avatar--${size}`}>
    {url&&!failed?<img src={apiAssetUrl(url)} alt={`Ảnh đại diện ${name||"giảng viên"}`} onError={()=>setFailed(true)} loading="lazy"/>:<UserRound role="img" aria-label="Ảnh đại diện mặc định"/>}
  </span>;
}
