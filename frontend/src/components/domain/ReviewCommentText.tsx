import { Fragment, type ReactNode } from "react";

/** Plain text only; links never become HTML or automatic external previews. */
export default function ReviewCommentText({text}: {text: string}) {
  const parts: ReactNode[] = []; let cursor = 0;
  for (const match of text.matchAll(/https?:\/\/[^\s<>"']+/g)) {
    const start = match.index!;
    let url = match[0].replace(/[.,;!?]+$/, "");
    while (url.endsWith(")") && (url.match(/\)/g)?.length || 0) > (url.match(/\(/g)?.length || 0)) url = url.slice(0,-1);
    parts.push(text.slice(cursor,start));
    parts.push(<a key={start} href={url} target="_blank" rel="noopener noreferrer" className="overflow-wrap-anywhere">{url}</a>);
    cursor = start + url.length;
  }
  parts.push(text.slice(cursor));
  return <>{parts.map((part,index)=><Fragment key={index}>{part}</Fragment>)}</>;
}
