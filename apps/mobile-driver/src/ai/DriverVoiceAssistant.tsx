/**
 * Hands-free voice assistant for fleet drivers.
 * Optimized for in-vehicle use with large touch targets and voice-only interaction.
 */

import React, { useState, useCallback } from "react";
import { View, Text, TouchableOpacity, StyleSheet, Vibration } from "react-native";

interface DriverVoiceAssistantProps {
  onRouteRequest: (destination: string) => void;
  onTelemetryQuery: () => void;
  onEmergency: () => void;
  language?: string;
}

export function DriverVoiceAssistant({
  onRouteRequest,
  onTelemetryQuery,
  onEmergency,
  language = "en",
}: DriverVoiceAssistantProps) {
  const [state, setState] = useState<"idle" | "listening" | "processing">("idle");
  const [lastCommand, setLastCommand] = useState<string>("");

  const labels = {
    en: {
      tapToSpeak: "Tap to Speak",
      listening: "Listening...",
      processing: "Processing...",
      route: "Route",
      telemetry: "Status",
      emergency: "Emergency",
    },
    ar: {
      tapToSpeak: "اضغط للتحدث",
      listening: "جاري الاستماع...",
      processing: "جاري المعالجة...",
      route: "الطريق",
      telemetry: "الحالة",
      emergency: "طوارئ",
    },
  };

  const t = labels[language as keyof typeof labels] || labels.en;

  const handleVoice = useCallback(() => {
    if (state !== "idle") return;

    setState("listening");
    Vibration.vibrate(100);

    setTimeout(() => {
      setState("processing");
      setTimeout(() => {
        const mockCommands = [
          { text: "Navigate to warehouse", action: () => onRouteRequest("warehouse") },
          { text: "Show vehicle status", action: () => onTelemetryQuery() },
        ];
        const cmd = mockCommands[Math.floor(Math.random() * mockCommands.length)];
        setLastCommand(cmd.text);
        cmd.action();
        setState("idle");
      }, 1000);
    }, 2000);
  }, [state, onRouteRequest, onTelemetryQuery]);

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={[styles.mainButton, state !== "idle" && styles.mainButtonActive]}
        onPress={handleVoice}
        activeOpacity={0.8}
        testID="driver-voice-button"
      >
        <Text style={styles.mainButtonText}>
          {state === "listening" ? t.listening : state === "processing" ? t.processing : t.tapToSpeak}
        </Text>
      </TouchableOpacity>

      {lastCommand && (
        <Text style={styles.lastCommand} testID="last-command">
          {lastCommand}
        </Text>
      )}

      <View style={styles.quickActions}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => onRouteRequest("home")}
          testID="driver-route-home"
        >
          <Text style={styles.actionText}>{t.route}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={onTelemetryQuery}
          testID="driver-telemetry"
        >
          <Text style={styles.actionText}>{t.telemetry}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionButton, styles.emergencyButton]}
          onPress={onEmergency}
          testID="driver-emergency"
        >
          <Text style={styles.emergencyText}>{t.emergency}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
  },
  mainButton: {
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: "#3182ce",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
  },
  mainButtonActive: {
    backgroundColor: "#e53e3e",
  },
  mainButtonText: {
    color: "#fff",
    fontSize: 24,
    fontWeight: "bold",
    textAlign: "center",
  },
  lastCommand: {
    fontSize: 16,
    color: "#666",
    marginBottom: 20,
    textAlign: "center",
  },
  quickActions: {
    flexDirection: "row",
    gap: 16,
  },
  actionButton: {
    backgroundColor: "#edf2f7",
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 12,
    minWidth: 100,
    alignItems: "center",
  },
  actionText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#2d3748",
  },
  emergencyButton: {
    backgroundColor: "#fed7d7",
  },
  emergencyText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#c53030",
  },
});
