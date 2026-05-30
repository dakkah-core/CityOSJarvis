/**
 * AI assistant settings screen for mobile app.
 */

import React, { useState } from "react";
import { View, Text, Switch, TouchableOpacity, StyleSheet, ScrollView } from "react-native";

interface SettingsScreenProps {
  onLanguageChange: (lang: string) => void;
  onVoiceToggle: (enabled: boolean) => void;
  onOfflineModeToggle: (enabled: boolean) => void;
  onClearCache: () => void;
}

export function SettingsScreen({
  onLanguageChange,
  onVoiceToggle,
  onOfflineModeToggle,
  onClearCache,
}: SettingsScreenProps) {
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [offlineMode, setOfflineMode] = useState(false);
  const [language, setLanguage] = useState("en");

  const languages = [
    { code: "en", label: "English" },
    { code: "ar", label: "العربية" },
  ];

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>AI Assistant Settings</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Language</Text>
        {languages.map((lang) => (
          <TouchableOpacity
            key={lang.code}
            style={[styles.langButton, language === lang.code && styles.langButtonActive]}
            onPress={() => {
              setLanguage(lang.code);
              onLanguageChange(lang.code);
            }}
            testID={`lang-${lang.code}`}
          >
            <Text style={[styles.langText, language === lang.code && styles.langTextActive]}>
              {lang.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Voice</Text>
        <View style={styles.row}>
          <Text>Enable Voice Input</Text>
          <Switch
            value={voiceEnabled}
            onValueChange={(val) => {
              setVoiceEnabled(val);
              onVoiceToggle(val);
            }}
            testID="voice-switch"
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Offline</Text>
        <View style={styles.row}>
          <Text>Offline Mode</Text>
          <Switch
            value={offlineMode}
            onValueChange={(val) => {
              setOfflineMode(val);
              onOfflineModeToggle(val);
            }}
            testID="offline-switch"
          />
        </View>
      </View>

      <TouchableOpacity style={styles.clearButton} onPress={onClearCache} testID="clear-cache">
        <Text style={styles.clearButtonText}>Clear Conversation Cache</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#fff" },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 24 },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: "600", color: "#718096", marginBottom: 12, textTransform: "uppercase" },
  langButton: {
    padding: 12,
    borderRadius: 8,
    backgroundColor: "#edf2f7",
    marginBottom: 8,
  },
  langButtonActive: { backgroundColor: "#3182ce" },
  langText: { fontSize: 16, color: "#2d3748" },
  langTextActive: { color: "#fff", fontWeight: "600" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 8 },
  clearButton: {
    backgroundColor: "#e53e3e",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 16,
  },
  clearButtonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
});
