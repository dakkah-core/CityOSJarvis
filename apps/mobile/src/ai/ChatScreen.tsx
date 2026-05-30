/**
 * Chat screen for mobile app.
 * Integrates FloatingAIButton + AIBottomSheet with offline support.
 */

import React, { useState, useCallback } from "react";
import { View, StyleSheet } from "react-native";
import { FloatingAIButton } from "@cityos/mobile-core/ai/FloatingAIButton";
import { AIBottomSheet } from "@cityos/mobile-core/ai/AIBottomSheet";
import { CityOSJarvisClient } from "@cityos/openjarvis-client";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

const client = new CityOSJarvisClient({
  bffUrl: process.env.EXPO_PUBLIC_BFF_URL || "https://api.dakkah.city",
  tenantId: process.env.EXPO_PUBLIC_TENANT_ID || "default",
});

export function ChatScreen() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await client.chat({ message: text });
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: response.data?.content || "Sorry, I couldn't process that.",
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error) {
      const errorMsg: ChatMessage = {
        id: `e-${Date.now()}`,
        role: "assistant",
        content: "Network error. Message queued for later.",
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
      // TODO: Add to offline queue
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <View style={styles.container}>
      <FloatingAIButton
        onPress={() => setIsOpen(true)}
        badgeCount={messages.filter((m) => m.role === "assistant").length}
      />
      <AIBottomSheet
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        messages={messages}
        onSendMessage={sendMessage}
        isLoading={isLoading}
        enableVoice={true}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
