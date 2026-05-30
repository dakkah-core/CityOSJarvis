/**
 * Offline message queue for desktop app.
 * Stores messages locally when network is unavailable,
 * then syncs when connection is restored.
 */

import { useState, useEffect, useCallback } from "react";

interface QueuedMessage {
  id: string;
  content: string;
  timestamp: number;
  agentId: string;
}

const STORAGE_KEY = "cityosjarvis-offline-queue";

export function useOfflineQueue() {
  const [queue, setQueue] = useState<QueuedMessage[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [isOnline, setIsOnline] = useState(() => {
    return typeof navigator !== "undefined" ? navigator.onLine : true;
  });

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(queue));
  }, [queue]);

  const enqueue = useCallback((content: string, agentId: string) => {
    const message: QueuedMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      content,
      timestamp: Date.now(),
      agentId,
    };
    setQueue((prev) => [...prev, message]);
    return message.id;
  }, []);

  const dequeue = useCallback((id: string) => {
    setQueue((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const clear = useCallback(() => {
    setQueue([]);
  }, []);

  const sync = useCallback(
    async (sendFn: (msg: QueuedMessage) => Promise<boolean>) => {
      const successful: string[] = [];
      for (const message of queue) {
        try {
          const ok = await sendFn(message);
          if (ok) successful.push(message.id);
        } catch {
          // Keep in queue if send fails
        }
      }
      setQueue((prev) => prev.filter((m) => !successful.includes(m.id)));
      return successful.length;
    },
    [queue]
  );

  return {
    queue,
    isOnline,
    enqueue,
    dequeue,
    clear,
    sync,
    queueLength: queue.length,
  };
}
