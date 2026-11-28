import {Check} from "lucide-react";
import "../../styles/workflow-steps.css";

export default function WorkflowSteps({steps,current,label="Tiến trình xử lý"}:{steps:string[];current:number;label?:string}) {
  return <ol className="workflow-steps" aria-label={label}>{steps.map((step,index)=><li key={step}
    className={index<current?"is-complete":index===current?"is-current":""} aria-current={index===current?"step":undefined}>
    <span className="workflow-steps__number" aria-hidden="true">{index<current?<Check size={15} strokeWidth={2.5}/>:index+1}</span>
    <span>{step}<small>{index<current?"Hoàn thành":index===current?"Đang thực hiện":"Chưa đến"}</small></span>
  </li>)}</ol>;
}
