import { NavLink, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import RunsPage from "./pages/RunsPage";
import JobsPage from "./pages/JobsPage";
import TerminalPage from "./pages/TerminalPage";

const ICONS: Record<string, string> = {
  chat: "M4 4h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H8l-4 3V5a1 1 0 0 1 1-1Z",
  terminal: "M3 4h14v10H3zM3 4l14 10M6.5 14 5 15.5h6",
  jobs: "M5 3h11v14H5zM8 7h5M8 10h5M8 13h3",
  docs: "M4 3h8l3 3v11H4zM12 3v3h3",
  runs: "M9 3a6 6 0 1 1 0 12 6 6 0 0 1 0-12ZM9 6v4l3 2",
};

function Icon({ name }: { name: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" width="16" height="16" aria-hidden="true">
      <path d={ICONS[name]} fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <span className="brand">local-agent</span>
        <span className="brand-sub">本地优先 · 完全离线</span>
        <span className="side-section">工作区</span>
        <nav>
          <NavLink to="/" end><Icon name="chat" /><span>对话</span></NavLink>
          <NavLink to="/terminal"><Icon name="terminal" /><span>AI终端</span></NavLink>
          <NavLink to="/jobs"><Icon name="jobs" /><span>任务中心</span></NavLink>
          <NavLink to="/documents"><Icon name="docs" /><span>知识库</span></NavLink>
          <NavLink to="/runs"><Icon name="runs" /><span>执行记录</span></NavLink>
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
