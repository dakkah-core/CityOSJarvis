/**
 * Chat history panel for desktop app.
 * Shows past conversations with search and filtering.
 */

import { useState, useMemo } from "react";

interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: number;
  agentId: string;
}

interface ChatHistoryProps {
  conversations: Conversation[];
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function ChatHistory({ conversations, onSelect, onDelete }: ChatHistoryProps) {
  const [search, setSearch] = useState("");
  const [filterAgent, setFilterAgent] = useState<string>("all");

  const filtered = useMemo(() => {
    return conversations
      .filter((c) => {
        const matchesSearch =
          search === "" ||
          c.title.toLowerCase().includes(search.toLowerCase()) ||
          c.lastMessage.toLowerCase().includes(search.toLowerCase());
        const matchesAgent = filterAgent === "all" || c.agentId === filterAgent;
        return matchesSearch && matchesAgent;
      })
      .sort((a, b) => b.timestamp - a.timestamp);
  }, [conversations, search, filterAgent]);

  const agents = useMemo(() => {
    const ids = new Set(conversations.map((c) => c.agentId));
    return ["all", ...Array.from(ids)];
  }, [conversations]);

  return (
    <div className="chat-history">
      <div className="chat-history-header">
        <input
          type="text"
          placeholder="Search conversations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          data-testid="history-search"
        />
        <select
          value={filterAgent}
          onChange={(e) => setFilterAgent(e.target.value)}
          data-testid="history-agent-filter"
        >
          {agents.map((a) => (
            <option key={a} value={a}>
              {a === "all" ? "All Agents" : a}
            </option>
          ))}
        </select>
      </div>
      <ul className="chat-history-list" data-testid="history-list">
        {filtered.map((conv) => (
          <li key={conv.id} className="chat-history-item">
            <button onClick={() => onSelect(conv.id)} data-testid={`history-item-${conv.id}`}>
              <div className="chat-history-title">{conv.title}</div>
              <div className="chat-history-preview">{conv.lastMessage}</div>
              <time dateTime={new Date(conv.timestamp).toISOString()}>
                {new Date(conv.timestamp).toLocaleDateString()}
              </time>
            </button>
            <button
              onClick={() => onDelete(conv.id)}
              className="chat-history-delete"
              data-testid={`history-delete-${conv.id}`}
              aria-label="Delete conversation"
            >
              ×
            </button>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="chat-history-empty" data-testid="history-empty">
            No conversations found
          </li>
        )}
      </ul>
    </div>
  );
}
