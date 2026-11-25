import { NavLink, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1 className="brand">local-agent</h1>
        <nav>
          <NavLink to="/" end>
            对话
          </NavLink>
          <NavLink to="/documents">知识库</NavLink>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/documents" element={<div><h2>知识库</h2><p>阶段 2 将开放 Markdown 导入与索引；当前请使用纯聊天。</p></div>} />
        </Routes>
      </main>
    </div>
  );
}
