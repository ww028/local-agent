import type { ChatMessage } from "../store/useChatStore";
import CitationCard from "./CitationCard";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`bubble ${message.role}`}>
      <div className="bubble-content">{message.content}</div>
      {message.citations && message.citations.length > 0 && (
        <div className="citations">
          {message.citations.map((c) => (
            <CitationCard key={c.chunk_id} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}
