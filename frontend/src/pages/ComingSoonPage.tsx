import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Bot, Compass } from "lucide-react";
import PageHeader from "../components/layout/PageHeader";
import EmptyState from "../components/ui/EmptyState";
import { plannedPages, type PlannedPageId } from "../plannedPages";

export default function ComingSoonPage() {
  const {feature} = useParams();
  const page = feature && Object.hasOwn(plannedPages, feature)
    ? plannedPages[feature as PlannedPageId] : null;
  if (!page) {
    return (
      <EmptyState icon={<Compass aria-hidden="true" />} title="Không tìm thấy mục này" description="Liên kết bạn truy cập không thuộc danh mục hiện có.">
        <Link className="btn btn-secondary" to="/"><ArrowLeft size={15} aria-hidden="true" />Về tổng quan</Link>
      </EmptyState>
    );
  }

  return <>
    <PageHeader title={page.title} description={page.description} />
    <EmptyState
      icon={<Compass aria-hidden="true" />}
      title="Đang phát triển"
      description="Chức năng này chưa được kết nối với quy trình và dữ liệu nghiệp vụ. Hiện chưa thể thực hiện thao tác tại đây."
    >
      <Link className="btn btn-primary" to="/ai"><Bot size={15} aria-hidden="true" />Mở Tra cứu AI</Link>
      <Link className="btn btn-secondary" to="/"><ArrowLeft size={15} aria-hidden="true" />Về tổng quan</Link>
    </EmptyState>
  </>;
}
