import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOfflineQueue } from "../OfflineQueue";

describe("useOfflineQueue", () => {
  it("initializes empty queue", () => {
    const { result } = renderHook(() => useOfflineQueue());
    expect(result.current.queue).toEqual([]);
    expect(result.current.isOnline).toBe(true);
  });

  it("enqueues a message", () => {
    const { result } = renderHook(() => useOfflineQueue());

    act(() => {
      result.current.enqueue("Hello", "default");
    });

    expect(result.current.queueLength).toBe(1);
    expect(result.current.queue[0].content).toBe("Hello");
    expect(result.current.queue[0].agentId).toBe("default");
  });

  it("dequeues a message", () => {
    const { result } = renderHook(() => useOfflineQueue());

    let id: string;
    act(() => {
      id = result.current.enqueue("Hello", "default");
    });

    act(() => {
      result.current.dequeue(id);
    });

    expect(result.current.queueLength).toBe(0);
  });

  it("clears all messages", () => {
    const { result } = renderHook(() => useOfflineQueue());

    act(() => {
      result.current.enqueue("Hello", "default");
      result.current.enqueue("World", "default");
    });

    act(() => {
      result.current.clear();
    });

    expect(result.current.queueLength).toBe(0);
  });

  it("syncs queued messages", async () => {
    const { result } = renderHook(() => useOfflineQueue());

    act(() => {
      result.current.enqueue("Hello", "default");
      result.current.enqueue("World", "default");
    });

    const mockSend = vi.fn().mockResolvedValue(true);

    let synced: number;
    await act(async () => {
      synced = await result.current.sync(mockSend);
    });

    expect(synced!).toBe(2);
    expect(result.current.queueLength).toBe(0);
    expect(mockSend).toHaveBeenCalledTimes(2);
  });

  it("keeps failed messages in queue", async () => {
    const { result } = renderHook(() => useOfflineQueue());

    act(() => {
      result.current.enqueue("Hello", "default");
    });

    const mockSend = vi.fn().mockResolvedValue(false);

    await act(async () => {
      await result.current.sync(mockSend);
    });

    expect(result.current.queueLength).toBe(1);
  });

  it("persists queue to localStorage", () => {
    const { result } = renderHook(() => useOfflineQueue());

    act(() => {
      result.current.enqueue("Persist me", "default");
    });

    const stored = localStorage.getItem("cityosjarvis-offline-queue");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed[0].content).toBe("Persist me");
  });
});
