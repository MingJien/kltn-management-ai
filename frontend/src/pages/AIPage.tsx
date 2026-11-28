import ReportSimilarity from "../components/domain/ReportSimilarity";
import { errorMessage } from "../errors";
import { FormEvent, useState } from "react";
import type { SearchHit, ChatResult } from "../api";
import { request } from "../api";
import ThesisStatusBadge from "../components/domain/ThesisStatusBadge";
import PageHeader from "../components/layout/PageHeader";
import Tabs from "../components/ui/Tabs";
import Badge from "../components/ui/Badge";
import EmptyState from "../components/ui/EmptyState";
import { AiKnowledgeArt } from "../components/ui/CampusArtwork";
import { ExternalLink, FileCheck2, HelpCircle, Info, Search, Send, Sparkles } from "lucide-react";

interface AIPageProps {
  userId: string;
  canCompareReports: boolean;
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  SCHOOL_FORM: "Biểu mẫu Khoa",
  FORM: "Biểu mẫu",
  GUIDELINE: "Hướng dẫn",
  TOPIC: "Đề tài",
  THESIS: "Khóa luận",
  CAPSTONE_PROJECT: "Đồ án tốt nghiệp",
  TERM_PROJECT: "Niên luận",
  COURSE_PROJECT: "Đồ án môn học",
  SYNTHETIC_TEST: "Dữ liệu kiểm thử",
  DOCUMENT: "Tài liệu",
  REGULATION: "Quy định",
};

const PROMPT_STARTERS = [
  "Quy trình đăng ký và bảo vệ KLTN gồm những bước nào?",
  "Hồ sơ cần nộp theo Mẫu 1–3 gồm những biểu mẫu gì?",
  "Điều kiện để sinh viên đủ điều kiện dự bảo vệ khóa luận?",
];

export default function AIPage({ userId, canCompareReports }: AIPageProps) {
  const [activeTab, setActiveTab] = useState<"chat" | "similarity" | "reports">("chat");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [similarityNotice, setSimilarityNotice] = useState("");
  const [searched, setSearched] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (searchLoading || trimmed.length < 3) return;
    setSearchLoading(true);
    setErrorMsg("");
    setSimilarityNotice("");
    setSearched(false);
    try {
      const result = await request<SearchHit[]>("/ai/similar-topics", userId, {
        method: "POST",
        body: JSON.stringify({ title: trimmed, limit: 5 }),
      });
      setHits(result);
      setSearched(true);
      setSimilarityNotice(
        result.length
          ? "Điểm chỉ là tín hiệu xếp hạng tham khảo, không phải tỉ lệ đạo văn."
          : "Không tìm thấy nguồn phù hợp trong phạm vi được phép."
      );
    } catch (error) {
      setHits([]);
      setErrorMsg(errorMessage(error));
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (chatLoading || trimmed.length < 3) return;
    setChatLoading(true);
    setErrorMsg("");
    try {
      setChat(
        await request<ChatResult>("/ai/chat", userId, {
          method: "POST",
          body: JSON.stringify({ question: trimmed }),
        })
      );
    } catch (error) {
      setChat(null);
      setErrorMsg(errorMessage(error));
    } finally {
      setChatLoading(false);
    }
  }

  const tabs = [
    { id: "chat", label: "Hỏi đáp", icon: <Sparkles size={15} aria-hidden="true" /> },
    { id: "similarity", label: "Tìm đề tài tương đồng", icon: <Search size={15} aria-hidden="true" /> },
    ...(canCompareReports ? [{ id: "reports", label: "Đối chiếu báo cáo", icon: <FileCheck2 size={15} aria-hidden="true" /> }] : []),
  ];

  return (
    <>
      <PageHeader
        title="Tra cứu AI"
        description="Tìm đề tài tương đồng và hỏi đáp tài liệu. Kết quả chỉ mang tính tham khảo."
      />

      <section className="ai-hero-card" aria-label="Giới thiệu không gian tra cứu tri thức KLTN">
        <div className="ai-hero-card__copy">
          <span className="welcome-kicker">TRỢ LÝ NGHIÊN CỨU HỌC THUẬT · KHOA CÔNG NGHỆ VÀ KỸ THUẬT</span>
          <h2>Không gian tra cứu quy định, biểu mẫu và đề tài DThU</h2>
          <p>
            Mọi phản hồi và kết quả xếp hạng đều gắn trích dẫn nguồn trong phạm vi được cấp quyền, hỗ trợ sinh viên
            và giảng viên đối chiếu trước khi nộp hoặc xét duyệt chính thức.
          </p>
        </div>
        <AiKnowledgeArt className="ai-hero-card__art" />
      </section>

      <Tabs
        asButtons
        variant="underline"
        idPrefix="ai-workspace"
        ariaLabel="Chế độ tra cứu AI"
        items={tabs}
        activeId={activeTab}
        onChange={(next) => {
          setErrorMsg("");
          setSimilarityNotice("");
          setActiveTab(next as "chat" | "similarity" | "reports");
        }}
      />

      {errorMsg ? <p className="alert alert-danger mt-4" role="alert">{errorMsg}</p> : null}

      <div className="mt-4">
        {activeTab === "reports" && <ReportSimilarity userId={userId} />}

        {/* Chat tab */}
        {activeTab === "chat" && (
          <>
            <div className="card mb-4">
              <div className="card-body stack">
                <form onSubmit={handleAsk}>
                  <div className="input-group mb-3">
                    <label htmlFor="rag-question">Câu hỏi</label>
                    <div className="input-inline">
                      <input
                        id="rag-question"
                        className="input"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Hỏi về quy định, quy trình hoặc biểu mẫu…"
                      />
                      <button
                        className="btn btn-primary"
                        disabled={question.trim().length < 3 || chatLoading}
                      >
                        <Send size={15} aria-hidden="true" />
                        {chatLoading ? "Đang xử lý…" : "Tra cứu"}
                      </button>
                    </div>
                  </div>
                </form>

                <div className="ai-prompt-starters">
                  <span className="text-caption">Gợi ý nhanh:</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {PROMPT_STARTERS.map((starter) => (
                      <button
                        key={starter}
                        type="button"
                        className="btn btn-soft btn-sm"
                        onClick={() => setQuestion(starter)}
                      >
                        {starter}
                      </button>
                    ))}
                  </div>
                </div>

                {(!chat || chat.provider_status === "NOT_CONFIGURED") && (
                  <p className="text-caption text-muted m-0">
                    <Info size={12} className="ai-hint-icon" aria-hidden="true" />
                    Chưa có Gemini key: hệ thống chỉ trả nguồn liên quan, không tự viết câu trả lời.
                  </p>
                )}
              </div>
            </div>

            {chat && (
              <div className="card">
                <div className="card-body">
                  <div className="flex items-center gap-3 mb-4">
                    <Sparkles size={20} className="ai-bot-icon" aria-hidden="true" />
                    <span className="text-h3">Trả lời</span>
                    <ThesisStatusBadge state={chat.status} />
                  </div>

                  {chat.status === "NO_EVIDENCE" ? (
                    <EmptyState
                      icon={<HelpCircle aria-hidden="true" />}
                      title="Không tìm thấy nguồn phù hợp"
                      description="Thử diễn đạt lại câu hỏi hoặc liên hệ bộ phận quản lý tài liệu."
                    />
                  ) : (
                    <>
                      {chat.answer && (
                        <div className="ai-answer-block">
                          <p className="text-body">{chat.answer}</p>
                        </div>
                      )}

                      {chat.status === "RETRIEVAL_ONLY" && (
                        <div className="alert alert-info mb-4">
                          <Info size={16} aria-hidden="true" />
                          <span>
                            Chưa có mô hình sinh câu trả lời. Kết quả chỉ dựa trên truy xuất, không phải phân tích nội dung.
                          </span>
                        </div>
                      )}

                      {chat.citations.length > 0 && (
                        <>
                          <h3 className="ai-section-heading">
                            Nguồn tham khảo
                          </h3>
                          <div className="stack gap-3">
                            {chat.citations.map((citation, index) => (
                              <div
                                key={`${citation.source_id}-${index}`}
                                className="ai-citation-card"
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <strong className="text-body-sm">{citation.title}</strong>
                                  <Badge variant="info">{SOURCE_TYPE_LABELS[citation.source_type] || citation.source_type}</Badge>
                                </div>
                                {citation.excerpt && (
                                  <p className="text-body-sm ai-hit-excerpt mb-2">
                                    “{citation.excerpt}”
                                  </p>
                                )}
                                <p className="text-caption text-muted">
                                  {citation.provenance}
                                  {citation.source_ref ? ` · ${citation.source_ref}` : ""}
                                  {citation.source_version ? ` · v${citation.source_version}` : ""}
                                </p>
                                {citation.source_url && (
                                  <a
                                    href={citation.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-body-sm mt-2"
                                  >
                                    Mở nguồn <ExternalLink size={12} aria-hidden="true" />
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
            <div className="card mb-4">
              <div className="card-body">
                <form onSubmit={handleSearch}>
                  <div className="input-group mb-3">
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
                        <Search size={15} aria-hidden="true" />
                        {searchLoading ? "Đang tìm…" : "Tìm kiếm"}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>

            {similarityNotice && (
              <div className="alert alert-info mb-4" role="status">
                <Info size={16} aria-hidden="true" />
                <span>{similarityNotice}</span>
              </div>
            )}

            {hits.length > 0 ? (
              <div className="stack">
                {hits.map((hit, index) => (
                  <article className="card" key={`${hit.source_id}-${index}`}>
                    <div className="card-body">
                      <div className="flex justify-between items-start mb-3">
                        <h3>
                          <span className="text-caption text-muted mr-2">
                            {index + 1}.
                          </span>
                          {hit.title}
                        </h3>
                        <Badge variant="info">{SOURCE_TYPE_LABELS[hit.source_type] || hit.source_type}</Badge>
                      </div>

                      {hit.excerpt && (
                        <p className="text-body-sm ai-hit-excerpt">
                          "{hit.excerpt}"
                        </p>
                      )}

                      <div className="flex items-center gap-4 mb-3">
                        <span className="text-caption text-muted">
                          Nguồn: {hit.provenance} · v{hit.source_version}
                        </span>
                      </div>

                      {/* Score bar */}
                      <div className="flex items-center gap-3">
                        <div className="ai-score-track">
                          <div
                            className="ai-score-fill"
                            style={{ width: `${Math.max(0, Math.min(hit.score * 100, 100))}%` }}
                          />
                        </div>
                        <span className="text-caption ai-score-value">
                          {hit.score.toFixed(3)}
                        </span>
                      </div>

                      {hit.source_url && (
                        <a
                          href={hit.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-link btn-sm mt-3"
                        >
                          Mở nguồn <ExternalLink size={12} aria-hidden="true" />
                        </a>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            ) : searched && !searchLoading && !errorMsg ? (
              <EmptyState
                icon={<Search aria-hidden="true" />}
                title="Không tìm thấy nguồn tương đồng"
                description="Thử từ khóa khác hoặc mở rộng tên đề tài để tra cứu trong kho đề tài và khóa luận đã công bố."
              />
            ) : null}
          </>
        )}
      </div>
    </>
  );
}
