import { create } from "zustand";
import type { Citation } from "../api/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  pushMessage: (message: ChatMessage) => void;
  appendAssistantToken: (token: string) => void;
  setAssistantCitations: (citations: Citation[]) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  loading: false,
  pushMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),
  appendAssistantToken: (token) =>
    set((s) => ({
      messages: s.messages.map((m, i) =>
        i === s.messages.length - 1 && m.role === "assistant"
          ? { ...m, content: m.content + token }
          : m,
      ),
    })),
  setAssistantCitations: (citations) =>
    set((s) => ({
      messages: s.messages.map((m, i) =>
        i === s.messages.length - 1 ? { ...m, citations } : m,
      ),
    })),
  setLoading: (loading) => set({ loading }),
  reset: () => set({ messages: [], loading: false }),
}));
