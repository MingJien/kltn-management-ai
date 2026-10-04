import PageHeader from "../components/layout/PageHeader";
import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

/**
 * Scaffold page for routes that will be implemented in later phases.
 * Provides a consistent empty state so navigation works immediately.
 */
export default function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <div className="card">
        <div className="empty-state">
          <Construction />
          <h3>Đang phát triển</h3>
          <p>Trang "{title}" sẽ được triển khai trong giai đoạn tiếp theo.</p>
        </div>
      </div>
    </>
  );
}
