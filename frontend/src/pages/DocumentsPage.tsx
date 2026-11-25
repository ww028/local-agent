import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "../api/client";
import type { DocumentMeta } from "../api/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const res = await listDocuments();
    setDocuments(res.documents);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onUpload = async (file: File) => {
    setBusy(true);
    try {
      await uploadDocument(file);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (id: string) => {
    await deleteDocument(id);
    await refresh();
  };

  return (
    <div className="documents">
      <h2>知识库</h2>
      <label className="upload">
        <input
          type="file"
          accept=".md,.markdown,.txt"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void onUpload(file);
            e.target.value = "";
          }}
        />
        上传 Markdown / 文本
      </label>
      <ul>
        {documents.map((doc) => (
          <li key={doc.document_id}>
            <span>{doc.title}</span>
            <button onClick={() => void onDelete(doc.document_id)}>删除</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
