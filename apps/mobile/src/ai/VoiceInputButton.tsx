/**
 * Voice input button for mobile apps.
 * Uses React Native's native speech recognition where available,
 * falls back to recording + STT upload.
 */

import React, { useState, useCallback } from "react";
import { TouchableOpacity, StyleSheet, Text, ActivityIndicator } from "react-native";

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  language?: string;
}

type VoiceState = "idle" | "listening" | "processing" | "error";

export function VoiceInputButton({ onTranscript, language = "en" }: VoiceInputButtonProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);

  const startListening = useCallback(async () => {
    setState("listening");
    setError(null);

    try {
      // TODO: Integrate with expo-speech-recognition or native module
      // For now, simulate with timeout
      await new Promise((resolve) => setTimeout(resolve, 2000));

      setState("processing");
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock transcript
      const mockTranscripts: Record<string, string> = {
        en: "What's the weather today?",
        ar: "ما هو الطقس اليوم؟",
      };
      onTranscript(mockTranscripts[language] || mockTranscripts.en);
      setState("idle");
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "Speech recognition failed");
    }
  }, [onTranscript, language]);

  const getLabel = () => {
    switch (state) {
      case "listening":
        return language === "ar" ? "جاري الاستماع..." : "Listening...";
      case "processing":
        return language === "ar" ? "جاري المعالجة..." : "Processing...";
      case "error":
        return language === "ar" ? "خطأ" : "Error";
      default:
        return language === "ar" ? "صوت" : "Voice";
    }
  };

  return (
    <TouchableOpacity
      onPress={startListening}
      disabled={state !== "idle"}
      style={[styles.button, state === "listening" && styles.listening]}
      accessibilityLabel={getLabel()}
      testID="voice-input-button"
    >
      {state === "processing" ? (
        <ActivityIndicator size="small" color="#fff" />
      ) : (
        <Text style={styles.text}>{getLabel()}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: "#3182ce",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 80,
  },
  listening: {
    backgroundColor: "#e53e3e",
  },
  text: {
    color: "#fff",
    fontWeight: "600",
  },
});
