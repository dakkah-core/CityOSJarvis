/**
 * Photo upload + AI analysis for field inspectors.
 * Supports offline capture with deferred upload.
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from "react-native";

interface PhotoUploadAnalysisProps {
  onAnalyze: (uri: string) => Promise<{ findings: string[]; severity: "low" | "medium" | "high" | "critical" }>;
  onUpload: (uri: string) => Promise<void>;
  offline?: boolean;
}

export function PhotoUploadAnalysis({ onAnalyze, onUpload, offline = false }: PhotoUploadAnalysisProps) {
  const [photos, setPhotos] = useState<{ uri: string; status: "pending" | "uploading" | "analyzing" | "done" | "error"; analysis?: any }[]>([]);

  const simulateCapture = useCallback(() => {
    const mockUri = `file:///mock/photo_${Date.now()}.jpg`;
    setPhotos((prev) => [...prev, { uri: mockUri, status: offline ? "pending" : "uploading" }]);

    if (!offline) {
      handleUploadAndAnalyze(mockUri);
    }
  }, [offline]);

  const handleUploadAndAnalyze = async (uri: string) => {
    setPhotos((prev) => prev.map((p) => (p.uri === uri ? { ...p, status: "uploading" } : p)));

    try {
      await onUpload(uri);
      setPhotos((prev) => prev.map((p) => (p.uri === uri ? { ...p, status: "analyzing" } : p)));

      const analysis = await onAnalyze(uri);
      setPhotos((prev) =>
        prev.map((p) => (p.uri === uri ? { ...p, status: "done", analysis } : p))
      );
    } catch {
      setPhotos((prev) => prev.map((p) => (p.uri === uri ? { ...p, status: "error" } : p)));
    }
  };

  const flushPending = () => {
    photos.filter((p) => p.status === "pending").forEach((p) => handleUploadAndAnalyze(p.uri));
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Photo Analysis</Text>
      {offline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>Offline Mode — {photos.filter((p) => p.status === "pending").length} pending</Text>
          <TouchableOpacity style={styles.flushButton} onPress={flushPending} testID="flush-pending">
            <Text style={styles.flushButtonText}>Sync Now</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.captureButton} onPress={simulateCapture} testID="capture-photo">
        <Text style={styles.captureButtonText}>+ Capture Photo</Text>
      </TouchableOpacity>

      {photos.map((photo, index) => (
        <View key={photo.uri} style={styles.photoCard} testID={`photo-${index}`}>
          <View style={styles.thumbnail}>
            <Text style={styles.thumbnailText}>📷</Text>
          </View>
          <View style={styles.photoInfo}>
            <Text style={styles.photoUri} numberOfLines={1}>
              {photo.uri.split("/").pop()}
            </Text>
            <View style={styles.statusRow}>
              <StatusBadge status={photo.status} />
              {photo.status === "analyzing" && <ActivityIndicator size="small" color="#3182ce" />}
            </View>
            {photo.analysis && (
              <View style={styles.analysisBox}>
                <Text style={styles.severityText}>Severity: {photo.analysis.severity}</Text>
                {photo.analysis.findings.map((f: string, i: number) => (
                  <Text key={i} style={styles.findingText}>• {f}</Text>
                ))}
              </View>
            )}
          </View>
        </View>
      ))}
    </ScrollView>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "#d69e2e",
    uploading: "#3182ce",
    analyzing: "#805ad5",
    done: "#38a169",
    error: "#e53e3e",
  };
  return (
    <View style={[styles.badge, { backgroundColor: colors[status] || "#666" }]}>
      <Text style={styles.badgeText}>{status.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  title: { fontSize: 20, fontWeight: "bold", marginBottom: 16 },
  offlineBanner: {
    backgroundColor: "#fef3c7",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  offlineText: { color: "#92400e", fontWeight: "600" },
  flushButton: { backgroundColor: "#d97706", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 4 },
  flushButtonText: { color: "#fff", fontWeight: "600" },
  captureButton: {
    backgroundColor: "#3182ce",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 16,
  },
  captureButtonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  photoCard: {
    flexDirection: "row",
    backgroundColor: "#f7fafc",
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  thumbnail: {
    width: 60,
    height: 60,
    backgroundColor: "#e2e8f0",
    borderRadius: 4,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 12,
  },
  thumbnailText: { fontSize: 24 },
  photoInfo: { flex: 1 },
  photoUri: { fontSize: 12, color: "#666", marginBottom: 4 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4, alignSelf: "flex-start" },
  badgeText: { color: "#fff", fontSize: 10, fontWeight: "bold" },
  analysisBox: { marginTop: 8, padding: 8, backgroundColor: "#fff", borderRadius: 4 },
  severityText: { fontWeight: "bold", marginBottom: 4 },
  findingText: { fontSize: 13, color: "#4a5568" },
});
