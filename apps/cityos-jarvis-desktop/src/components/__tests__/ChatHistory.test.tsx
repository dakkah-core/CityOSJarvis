import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatHistory } from "../ChatHistory";

const mockConversations = [
  { id: "1", title: "Weather query", lastMessage: "It's sunny today", timestamp: Date.now(), agentId: "citizen" },
  { id: "2", title: "Product search", lastMessage: "Found 3 results", timestamp: Date.now() - 86400000, agentId: "merchant" },
  { id: "3", title: "Permit status", lastMessage: "Under review", timestamp: Date.now() - 172800000, agentId: "government" },
];

describe("ChatHistory", () => {
  const mockSelect = vi.fn();
  const mockDelete = vi.fn();

  it("renders all conversations", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    expect(screen.getByText("Weather query")).toBeInTheDocument();
    expect(screen.getByText("Product search")).toBeInTheDocument();
    expect(screen.getByText("Permit status")).toBeInTheDocument();
  });

  it("filters by search term", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    const search = screen.getByTestId("history-search");
    fireEvent.change(search, { target: { value: "weather" } });

    expect(screen.getByText("Weather query")).toBeInTheDocument();
    expect(screen.queryByText("Product search")).not.toBeInTheDocument();
  });

  it("filters by agent", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    const filter = screen.getByTestId("history-agent-filter");
    fireEvent.change(filter, { target: { value: "merchant" } });

    expect(screen.queryByText("Weather query")).not.toBeInTheDocument();
    expect(screen.getByText("Product search")).toBeInTheDocument();
  });

  it("calls onSelect when conversation clicked", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    fireEvent.click(screen.getByTestId("history-item-1"));
    expect(mockSelect).toHaveBeenCalledWith("1");
  });

  it("calls onDelete when delete clicked", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    fireEvent.click(screen.getByTestId("history-delete-1"));
    expect(mockDelete).toHaveBeenCalledWith("1");
  });

  it("shows empty state when no matches", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    const search = screen.getByTestId("history-search");
    fireEvent.change(search, { target: { value: "xyznonexistent" } });

    expect(screen.getByTestId("history-empty")).toBeInTheDocument();
  });

  it("sorts by newest first", () => {
    render(<ChatHistory conversations={mockConversations} onSelect={mockSelect} onDelete={mockDelete} />);
    const items = screen.getAllByTestId(/history-item-/);
    expect(items[0]).toHaveAttribute("data-testid", "history-item-1");
  });
});
