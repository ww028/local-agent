import { NavLink, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";

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
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </main>
    </div>
  );
}
