import { NavLink, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import RunsPage from "./pages/RunsPage";
import JobsPage from "./pages/JobsPage";
import TerminalPage from "./pages/TerminalPage";

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <span className="brand">local-agent</span>
        <span className="brand-sub">本地优先 · 完全离线</span>
        <span className="side-section">工作区</span>
        <nav>
          <NavLink to="/" end>
            对话
          </NavLink>
          <NavLink to="/terminal">AI终端</NavLink>
          <NavLink to="/jobs">任务中心</NavLink>
          <NavLink to="/documents">知识库</NavLink>
          <NavLink to="/runs">执行记录</NavLink>
        </nav>
        <p className="side-foot">只连本机模型与本地索引<br/>不外发任何数据</p>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/terminal" element={<TerminalPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/runs" element={<RunsPage />} />
        </Routes>
      </main>
    </div>
  );
}
