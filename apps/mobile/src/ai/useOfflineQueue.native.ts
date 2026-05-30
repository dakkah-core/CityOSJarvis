/**
 * Native offline queue for mobile apps.
 * Uses AsyncStorage for persistence.
 */

import { useState, useEffect, useCallback } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

interface QueuedMessage {
  id: string;
  content: string;
  timestamp: number;
  agentId: string;
}

const STORAGE_KEY = "@cityosjarvis:offline-queue";

export function useOfflineQueueNative() {
  const [queue, setQueue] = useState<QueuedMessage[]>([]);
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        setQueue(JSON.parse(stored));
      }
    } catch {
      // Ignore load errors
    }
  };

  const saveQueue = async (newQueue: QueuedMessage[]) => {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(newQueue));
    } catch {
      // Ignore save errors
    }
  };

  const enqueue = useCallback(async (content: string, agentId: string) => {
    const message: QueuedMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      content,
      timestamp: Date.now(),
      agentId,
    };
    setQueue((prev) => {
      const updated = [...prev, message];
      saveQueue(updated);
      return updated;
    });
    return message.id;
  }, []);

  const dequeue = useCallback(async (id: string) => {
    setQueue((prev) => {
      const updated = prev.filter((m) => m.id !== id);
      saveQueue(updated);
      return updated;
    });
  }, []);

  const clear = useCallback(async () => {
    setQueue([]);
    await AsyncStorage.removeItem(STORAGE_KEY);
  }, []);

  const sync = useCallback(
    async (sendFn: (msg: QueuedMessage) => Promise<boolean>) => {
      const successful: string[] = [];
      for (const message of queue) {
        try {
          const ok = await sendFn(message);
          if (ok) successful.push(message.id);
        } catch {
          // Keep in queue
        }
      }
      const updated = queue.filter((m) => !successful.includes(m.id));
      setQueue(updated);
      await saveQueue(updated);
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
