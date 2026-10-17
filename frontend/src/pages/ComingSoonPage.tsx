import { Link, useParams } from "react-router-dom";
import PageHeader from "../components/layout/PageHeader";
import { plannedPages, type PlannedPageId } from "../plannedPages";

export default function ComingSoonPage() {
  const {feature} = useParams();
  const page = feature && Object.hasOwn(plannedPages, feature)
    ? plannedPages[feature as PlannedPageId] : null;
  if (!page) return <div className="card"><div className="card-body"><p>Không tìm thấy mục này.</p><Link to="/">Về tổng quan</Link></div></div>;

  return <>
    <PageHeader title={page.title} description={page.description} />
    <section className="card" aria-labelledby="coming-soon-title">
      <div className="card-body stack">
        <h2 id="coming-soon-title">Đang phát triển</h2>
        <p>Chức năng này chưa được kết nối với quy trình và dữ liệu nghiệp vụ. Hiện chưa thể thực hiện thao tác tại đây.</p>
        <Link className="btn btn-secondary" to="/">Về tổng quan</Link>
      </div>
    </section>
  </>;
}
