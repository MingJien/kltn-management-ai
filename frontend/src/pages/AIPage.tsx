import { FormEvent, useState } from "react";
import type { SearchHit, ChatResult } from "../api";
import { request } from "../api";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import PageHeader from "../components/layout/PageHeader";
import { Bot, Search, HelpCircle, ExternalLink, AlertTriangle, Info } from "lucide-react";

interface AIPageProps {
  userId: string;
}

export default function AIPage({ userId }: AIPageProps) {
  const [activeTab, setActiveTab] = useState<"chat" | "similarity">("chat");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [message, setMessage] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    setSearchLoading(true);
    setMessage("");
    try {
      const result = await request<SearchHit[]>("/ai/similar-topics", userId, {
        method: "POST",
        body: JSON.stringify({ title: query, limit: 5 }),
      });
      setHits(result);
      setMessage(
        result.length
          ? "Điểm chỉ là tín hiệu xếp hạng, không phải tỉ lệ đạo văn."
          : "Không tìm thấy nguồn trong phạm vi được phép."
      );
    } catch (error) {
      setMessage(String(error));
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    setChatLoading(true);
    setMessage("");
    try {
      setChat(
        await request<ChatResult>("/ai/chat", userId, {
          method: "POST",
          body: JSON.stringify({ question }),
        })
      );
    } catch (error) {
      setMessage(String(error));
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Tra cứu AI"
        description="Tìm đề tài tương đồng và hỏi đáp tài liệu. Kết quả chỉ mang tính tham khảo."
      />

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tabs__tab ${activeTab === "chat" ? "tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          <Bot size={16} />
          Hỏi đáp
        </button>
        <button
          className={`tabs__tab ${activeTab === "similarity" ? "tabs__tab--active" : ""}`}
          onClick={() => setActiveTab("similarity")}
        >
          <Search size={16} />
          Tìm đề tài tương đồng
        </button>
      </div>

      {/* Chat tab */}
      {activeTab === "chat" && (
        <>
          <div className="card" style={{ marginBottom: "var(--space-4)" }}>
            <div className="card-body">
              <form onSubmit={handleAsk}>
                <div className="input-group" style={{ marginBottom: "var(--space-3)" }}>
                  <label htmlFor="rag-question">Câu hỏi</label>
                  <div className="input-inline">
                    <input
                      id="rag-question"
                      className="input"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="Hỏi về quy định hoặc biểu mẫu…"
                    />
                    <button
                      className="btn btn-primary"
                      disabled={question.trim().length < 3 || chatLoading}
                    >
                      {chatLoading ? "Đang xử lý…" : "Tra cứu"}
                    </button>
                  </div>
                </div>
              </form>
              <p className="text-caption text-muted">
                <Info size={12} style={{ display: "inline", verticalAlign: "-1px", marginRight: 4 }} />
                Chưa có Gemini key: hệ thống chỉ trả nguồn liên quan, không tự viết câu trả lời.
              </p>
            </div>
          </div>

          {chat && (
            <div className="card">
              <div className="card-body">
                <div className="flex items-center gap-3" style={{ marginBottom: "var(--space-4)" }}>
                  <Bot size={20} style={{ color: "var(--primary-600)" }} />
                  <span className="text-h3">Trả lời</span>
                  <ThesisStatusBadge state={chat.status} />
                </div>

                {chat.status === "NO_EVIDENCE" ? (
                  <div className="empty-state" style={{ padding: "var(--space-8) var(--space-6)" }}>
                    <HelpCircle />
                    <h3>Không tìm thấy nguồn phù hợp</h3>
                    <p>Thử diễn đạt lại câu hỏi hoặc liên hệ bộ phận quản lý tài liệu.</p>
                  </div>
                ) : (
                  <>
                    {chat.answer && (
                      <div
                        style={{
                          padding: "var(--space-4)",
                          background: "var(--neutral-50)",
                          borderRadius: "var(--radius-md)",
                          marginBottom: "var(--space-4)",
                          borderLeft: "3px solid var(--primary-200)",
                        }}
                      >
                        <p className="text-body">{chat.answer}</p>
                      </div>
                    )}

                    {chat.status === "RETRIEVAL_ONLY" && (
                      <div
                        className="alert alert-info"
                        style={{ marginBottom: "var(--space-4)" }}
                      >
                        <Info size={16} />
                        <span>
                          Chưa có mô hình sinh câu trả lời. Kết quả chỉ dựa trên truy xuất, không phải phân tích nội dung.
                        </span>
                      </div>
                    )}

                    {chat.citations.length > 0 && (
                      <>
                        <h3 style={{ marginBottom: "var(--space-3)", marginTop: "var(--space-4)" }}>
                          Nguồn tham khảo
                        </h3>
                        <div className="stack" style={{ gap: "var(--space-3)" }}>
                          {chat.citations.map((citation) => (
                            <div
                              key={citation.source_id}
                              style={{
                                padding: "var(--space-3) var(--space-4)",
                                background: "var(--neutral-50)",
                                borderRadius: "var(--radius-md)",
                                borderLeft: "3px solid var(--primary-200)",
                              }}
                            >
                              <div className="flex items-center gap-2" style={{ marginBottom: "var(--space-1)" }}>
                                <strong className="text-body-sm">{citation.title}</strong>
                                <span className="badge badge-neutral">{citation.source_type}</span>
                              </div>
                              <p className="text-caption text-muted">
                                {citation.provenance} · {citation.source_version}
                              </p>
                              {citation.source_url && (
                                <a
                                  href={citation.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="flex items-center gap-1 text-body-sm"
                                  style={{ marginTop: "var(--space-2)" }}
                                >
                                  Mở nguồn <ExternalLink size={12} />
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Similarity tab */}
      {activeTab === "similarity" && (
        <>
          <div className="card" style={{ marginBottom: "var(--space-4)" }}>
            <div className="card-body">
              <form onSubmit={handleSearch}>
                <div className="input-group" style={{ marginBottom: "var(--space-3)" }}>
                  <label htmlFor="ai-query">Tên / ý tưởng đề tài</label>
                  <div className="input-inline">
                    <input
                      id="ai-query"
                      className="input"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Nhập tên đề tài…"
                    />
                    <button
                      className="btn btn-primary"
                      disabled={query.trim().length < 3 || searchLoading}
                    >
                      {searchLoading ? "Đang tìm…" : "Tìm kiếm"}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>

          {message && (
            <div
              className="alert alert-warning"
              style={{ marginBottom: "var(--space-4)" }}
            >
              <AlertTriangle size={16} />
              <span>{message}</span>
            </div>
          )}

          {hits.length > 0 && (
            <div className="stack">
              {hits.map((hit, index) => (
                <article className="card" key={hit.source_id}>
                  <div className="card-body">
                    <div className="flex justify-between items-start" style={{ marginBottom: "var(--space-3)" }}>
                      <h3>
                        <span className="text-caption text-muted" style={{ marginRight: "var(--space-2)" }}>
                          {index + 1}.
                        </span>
                        {hit.title}
                      </h3>
                      <span className="badge badge-neutral">{hit.source_type}</span>
                    </div>

                    {hit.excerpt && (
                      <p
                        className="text-body-sm"
                        style={{
                          fontStyle: "italic",
                          color: "var(--neutral-600)",
                          marginBottom: "var(--space-3)",
                        }}
                      >
                        "{hit.excerpt}"
                      </p>
                    )}

                    <div className="flex items-center gap-4" style={{ marginBottom: "var(--space-3)" }}>
                      <span className="text-caption text-muted">
                        Nguồn: {hit.provenance} · v{hit.source_version}
                      </span>
                    </div>

                    {/* Score bar */}
                    <div className="flex items-center gap-3">
                      <div
                        style={{
                          flex: 1,
                          height: 6,
                          background: "var(--neutral-100)",
                          borderRadius: "var(--radius-full)",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(hit.score * 100, 100)}%`,
                            height: "100%",
                            background: `linear-gradient(90deg, var(--primary-200), var(--primary-600))`,
                            borderRadius: "var(--radius-full)",
                            transition: "width var(--duration-slow) var(--ease-standard)",
                          }}
                        />
                      </div>
                      <span className="text-caption" style={{ fontFamily: "var(--font-mono)", minWidth: 44 }}>
                        {hit.score.toFixed(3)}
                      </span>
                    </div>

                    {hit.source_url && (
                      <a
                        href={hit.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-link btn-sm"
                        style={{ marginTop: "var(--space-3)" }}
                      >
                        Mở nguồn <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
