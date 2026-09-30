import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useParams } from "react-router-dom";
import {
  AuthenticationMode, Context, EligibleStudent, Registration, SearchHit, Topic, Thesis, ChatResult,
  request, setDevelopmentAuthEnabled, universityLoginUrl,
} from "./api";

function App() {
  const [userId, setUserId] = useState(sessionStorage.getItem("kltn-dev-user") || "");
  const [authMode, setAuthMode] = useState<AuthenticationMode | "loading">("loading");
  const [context, setContext] = useState<Context | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const connect = useCallback(async (id: string) => {
    setError("");
    setLoading(true);
    try {
      const result = await request<Context>("/me/context", id);
      setContext(result);
      if (id) sessionStorage.setItem("kltn-dev-user", id);
    } catch (cause) {
      setContext(null);
      setError(String(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1/auth/config`, { credentials: "include" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const config = await response.json() as { mode: AuthenticationMode };
        setAuthMode(config.mode);
        setDevelopmentAuthEnabled(config.mode === "development");
        if (config.mode === "development" && userId) await connect(userId);
        if (config.mode === "university_oidc") {
          try { await connect(""); } catch { /* A signed-in session may not exist yet. */ }
        }
      } catch (cause) {
        setAuthMode("unavailable");
        setError(`Không kết nối được dịch vụ đăng nhập: ${String(cause)}`);
      }
    })();
  }, []);

  async function signOut() {
    try { await request<void>("/auth/logout", "", { method: "POST" }); }
    finally { setContext(null); setUserId(""); sessionStorage.removeItem("kltn-dev-user"); }
  }

  return (
    <div className="app">
      <header>
        <div className="brand"><span className="mark">K</span><div><strong>KLTN</strong><small>Prototype nghiệp vụ · NV4</small></div></div>
        <nav>
          <NavLink to="/topics">Đề tài</NavLink>
          <NavLink to="/registrations">Đăng ký</NavLink>
          <NavLink to="/ai">Thử nghiệm AI</NavLink>
        </nav>
      </header>
      <main>
        <section className="hero">
          <p className="eyebrow">NỀN TẢNG QUẢN LÝ KHÓA LUẬN</p>
          <h1>Đăng ký đề tài và theo dõi quyết định</h1>
          <p>{authMode === "university_oidc" ? "Đăng nhập bằng tài khoản Trường. Hệ thống tự tìm tài khoản KLTN tương ứng." : "Giao diện thử nghiệm nối với PostgreSQL qua FastAPI."}</p>
        </section>
        <section className="identity panel">
          <div><h2>Tài khoản</h2><p>{authMode === "university_oidc" ? "Đăng nhập tập trung qua hệ thống xác thực của Trường." : "Định danh chỉ để thử nghiệm trên máy phát triển."}</p></div>
          {authMode === "development" && <form onSubmit={(event) => { event.preventDefault(); void connect(userId); }}>
            <label htmlFor="dev-user">UUID thử nghiệm (chỉ DEV/TEST)</label>
            <div className="inline"><input id="dev-user" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="UUID tài khoản giả lập" /><button disabled={loading}>Kết nối</button></div>
          </form>}
          {authMode === "university_oidc" && !context && <div><a className="login-button" style={{ display: "inline-flex", alignItems: "center", minHeight: 44, padding: "10px 16px", borderRadius: 8, background: "#0b7380", color: "#fff", fontWeight: 700, textDecoration: "none" }} href={universityLoginUrl()}>Đăng nhập bằng tài khoản Trường</a></div>}
          {authMode === "unavailable" && <p role="status">Đăng nhập chưa được cấu hình. Liên hệ quản trị hệ thống.</p>}
          {loading && <p role="status">Đang tải…</p>}
          {error && <p className="error" role="alert">{error}</p>}
          {context && <div className="context"><span className="badge">{context.base_role}</span><span>Quyền: {context.actions.join(", ") || "Chỉ xem"}</span>{authMode === "university_oidc" && <button className="secondary" onClick={() => void signOut()}>Đăng xuất</button>}</div>}
        </section>
        {!context ? <section className="panel"><p>{authMode === "university_oidc" ? "Đăng nhập bằng tài khoản Trường để xem dữ liệu được cấp quyền." : "Hãy kết nối bằng tài khoản thử nghiệm để xem dữ liệu."}</p></section> : (
          <Routes>
            <Route path="/" element={<div className="panel">Chọn <Link to="/topics">Đề tài</Link> để bắt đầu.</div>} />
            <Route path="/topics" element={<Topics userId={context.user_id} context={context} />} />
            <Route path="/registrations" element={<Registrations userId={context.user_id} context={context} />} />
            <Route path="/ai" element={<AI userId={context.user_id} />} />
            <Route path="/theses/:thesisId" element={<ThesisView userId={context.user_id} />} />
          </Routes>
        )}
      </main>
      <footer>Prototype học thuật · Dữ liệu thật và tài liệu nguồn không lưu trong Git.</footer>
    </div>
  );
}

function Topics({ userId, context }: { userId: string; context: Context }) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [students, setStudents] = useState<EligibleStudent[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    request<Topic[]>("/topics", userId).then(setTopics).catch((error) => setMessage(String(error))).finally(() => setLoading(false));
  }, [userId]);
  useEffect(() => {
    if (!selectedTopic || !context.actions.includes("registration:create")) return;
    request<EligibleStudent[]>(`/eligible-students?round_id=${selectedTopic.round_id}`, userId)
      .then(setStudents).catch((error) => setMessage(String(error)));
    setSelectedMembers(context.student_id ? [context.student_id] : []);
  }, [selectedTopic, context, userId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedTopic) return;
    setMessage("");
    try {
      const result = await request<Registration>("/topic-registrations", userId, {
        method: "POST", body: JSON.stringify({ topic_id: selectedTopic.id, member_student_ids: selectedMembers }),
      });
      setMessage(`Đã gửi nhóm. Mã đăng ký: ${result.id}. Trạng thái: ${result.state}.`);
    } catch (error) { setMessage(String(error)); }
  }

  return <section>
    <div className="section-head"><h2>Đề tài đã duyệt</h2><p>Chọn đề tài và lập nhóm 1–3 sinh viên. Thành viên khóa khi gửi đăng ký.</p></div>
    {loading ? <p role="status">Đang tải…</p> : topics.length === 0 ? <div className="panel empty">Chưa có đề tài đã duyệt.</div> :
      <div className="grid">{topics.map((topic) => <button className={selectedTopic?.id === topic.id ? "card selected" : "card"} key={topic.id} onClick={() => setSelectedTopic(topic)}>
        <span className="badge">Tối đa {topic.max_students} SV</span><h3>{topic.title}</h3><p>{topic.description || "Chưa có mô tả"}</p><small>Đợt: {topic.round_id}</small>
      </button>)}</div>}
    {selectedTopic && <div className="panel form-panel">
      <h3>{selectedTopic.title}</h3>
      {context.actions.includes("registration:create") ? <form onSubmit={submit}>
        <fieldset><legend>Thành viên nhóm ({selectedMembers.length}/{selectedTopic.max_students})</legend>
          {students.length === 0 ? <p>Chưa có sinh viên đủ điều kiện đã xác nhận trong bộ môn.</p> : students.map((student) =>
            <label className="check" key={student.id}><input type="checkbox" checked={selectedMembers.includes(student.id)}
              disabled={student.id === context.student_id}
              onChange={(event) => setSelectedMembers(event.target.checked
                ? [...selectedMembers, student.id] : selectedMembers.filter((id) => id !== student.id))} />
              {student.display_name} <small>{student.student_code}</small>{student.id === context.student_id && " (bạn)"}</label>)}
        </fieldset>
        <button disabled={selectedMembers.length < 1 || selectedMembers.length > selectedTopic.max_students}>Gửi đăng ký nhóm</button>
      </form> : <p>Ngữ cảnh hiện tại chỉ xem đề tài.</p>}
    </div>}
    {message && <p className="notice" role="status">{message}</p>}
  </section>;
}

function Registrations({ userId, context }: { userId: string; context: Context }) {
  const [rows, setRows] = useState<Registration[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(() => {
    setLoading(true);
    request<Registration[]>("/topic-registrations", userId)
      .then(setRows).catch((error) => setMessage(String(error))).finally(() => setLoading(false));
  }, [userId]);
  useEffect(() => { reload(); }, [reload]);

  async function act(row: Registration, action: "accept" | "reject" | "finalize") {
    setMessage("");
    const path = action === "finalize" ? "department-finalization" : "lecturer-decision";
    try {
      await request<Registration>(`/topic-registrations/${row.id}/${path}`, userId, {
        method: "POST",
        headers: { "If-Match": String(row.row_version) },
        body: action === "finalize" ? undefined : JSON.stringify({
          decision: action === "accept" ? "ACCEPT" : "REJECT",
          reason: action === "reject" ? window.prompt("Lý do từ chối") : undefined,
        }),
      });
      setMessage("Đã cập nhật. Trạng thái được đọc lại từ server.");
      reload();
    } catch (error) { setMessage(String(error)); }
  }

  return <section><div className="section-head"><h2>Đăng ký và khóa luận</h2><p>Quyết định được kiểm tra quyền và trạng thái tại backend.</p></div>
    {loading ? <p role="status">Đang tải…</p> : rows.length === 0 ? <div className="panel empty">Chưa có đăng ký trong phạm vi của bạn.</div> :
      <div className="stack">{rows.map((row) => <article className="panel" key={row.id}>
        <div className="row-top"><h3>Đăng ký {row.id.slice(0, 8)}</h3><span className="badge">{row.state}</span></div>
        <dl><div><dt>Đề tài</dt><dd>{row.topic_id}</dd></div><div><dt>Thành viên</dt><dd>{row.member_student_ids.length} sinh viên</dd></div>
          {row.thesis_id && <div><dt>Khóa luận đã tạo</dt><dd><Link to={`/theses/${row.thesis_id}`}>{row.thesis_id}</Link></dd></div>}</dl>
        <div className="actions">
          {row.state === "SUBMITTED" && context.actions.includes("registration:lecturer_decide") && <>
            <button onClick={() => void act(row, "accept")}>Chấp nhận</button>
            <button className="secondary" onClick={() => void act(row, "reject")}>Từ chối</button>
          </>}
          {row.state === "LECTURER_ACCEPTED" && context.actions.includes("registration:department_finalize") &&
            <button onClick={() => void act(row, "finalize")}>TBM chốt đăng ký</button>}
        </div>
      </article>)}</div>}
    {message && <p className="notice" role="status">{message}</p>}
  </section>;
}

function ThesisView({ userId }: { userId: string }) {
  const { thesisId } = useParams();
  const [thesis, setThesis] = useState<Thesis | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (thesisId) request<Thesis>(`/theses/${thesisId}`, userId).then(setThesis).catch((cause) => setError(String(cause)));
  }, [thesisId, userId]);
  if (error) return <p className="error" role="alert">{error}</p>;
  if (!thesis) return <p role="status">Đang tải khóa luận…</p>;
  return <section className="panel">
    <Link to="/registrations">← Đăng ký</Link><h2>{thesis.title}</h2>
    <span className="badge">{thesis.state}</span>
    <p>Mã khóa luận: <code>{thesis.id}</code></p>
    <p>GVHD chính: <code>{thesis.advisor_lecturer_id}</code></p>
    <h3>Thành viên</h3><ul>{thesis.member_student_ids.map((id) => <li key={id}><code>{id}</code></li>)}</ul>
  </section>;
}

function AI({ userId }: { userId: string }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [message, setMessage] = useState("");
  async function search(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await request<SearchHit[]>("/ai/similar-topics", userId, {
        method: "POST", body: JSON.stringify({ title: query, limit: 5 }),
      });
      setHits(result);
      setMessage(result.length ? "Điểm chỉ là tín hiệu xếp hạng, không phải tỉ lệ đạo văn." : "Không tìm thấy nguồn trong phạm vi được phép.");
    } catch (error) { setMessage(String(error)); }
  }
  async function ask(event: FormEvent) {
    event.preventDefault();
    try {
      setChat(await request<ChatResult>("/ai/chat", userId, {
        method: "POST", body: JSON.stringify({ question }),
      }));
    } catch (error) { setMessage(String(error)); }
  }
  return <section><div className="section-head"><h2>Tìm đề tài tương tự</h2><p>Prototype trên corpus mẫu có nguồn rõ ràng. Không tự kết luận đạo văn.</p></div>
    <form className="panel" onSubmit={search}><label htmlFor="ai-query">Tên/ý tưởng đề tài</label><div className="inline">
      <input id="ai-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nhập tên đề tài…" />
      <button disabled={query.trim().length < 3}>Tìm kiếm</button></div></form>
    {message && <p className="notice" role="status">{message}</p>}
    <div className="stack">{hits.map((hit) => <article className="panel" key={hit.source_id}>
      <div className="row-top"><h3>{hit.title}</h3><span className="badge">{hit.source_type}</span></div>
      <p>{hit.excerpt}</p><small>Nguồn: {hit.provenance} · phiên bản {hit.source_version}</small>
      <p className="score">Điểm xếp hạng {hit.score.toFixed(3)}</p>
      {hit.source_url && <a href={hit.source_url} target="_blank" rel="noopener noreferrer">Mở nguồn</a>}
    </article>)}</div>
    <div className="section-head"><h2>Tra cứu tài liệu</h2><p>Chưa có Gemini key: hệ thống chỉ trả nguồn liên quan, không tự viết câu trả lời.</p></div>
    <form className="panel" onSubmit={ask}><label htmlFor="rag-question">Câu hỏi</label><div className="inline">
      <input id="rag-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Hỏi về quy định hoặc biểu mẫu…" />
      <button disabled={question.trim().length < 3}>Tra cứu</button></div></form>
    {chat && <div className="panel" style={{ marginTop: 16 }}>
      <span className="badge">{chat.status}</span>
      <p>{chat.answer || (chat.status === "NO_EVIDENCE" ? "Không tìm thấy nguồn phù hợp trong phạm vi quyền." : "Các nguồn có thể liên quan:")}</p>
      <ul>{chat.citations.map((citation) => <li key={citation.source_id}>
        <strong>{citation.title}</strong> ({citation.source_type}) — {citation.provenance}
        {citation.source_url && <a href={citation.source_url} target="_blank" rel="noopener noreferrer"> Mở nguồn</a>}
      </li>)}</ul>
    </div>}
  </section>;
}
export default App;
