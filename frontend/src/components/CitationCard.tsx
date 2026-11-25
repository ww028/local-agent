import type { Citation } from "../api/types";

export default function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="citation">
      <div className="citation-title">
        {citation.document_title}
        {citation.heading ? ` — ${citation.heading}` : ""}
      </div>
      <div className="citation-snippet">{citation.snippet}</div>
    </div>
  );
}
