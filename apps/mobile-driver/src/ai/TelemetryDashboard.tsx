/**
 * Fleet vehicle telemetry dashboard for mobile drivers.
 */

import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";

interface TelemetryMetric {
  label: string;
  value: string;
  unit: string;
  status: "normal" | "warning" | "critical";
}

interface TelemetryDashboardProps {
  vehicleId: string;
  metrics: TelemetryMetric[];
  lastUpdated: string;
}

export function TelemetryDashboard({ vehicleId, metrics, lastUpdated }: TelemetryDashboardProps) {
  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Vehicle {vehicleId}</Text>
      <Text style={styles.timestamp}>Updated: {lastUpdated}</Text>

      <View style={styles.grid}>
        {metrics.map((metric, index) => (
          <View
            key={index}
            style={[styles.card, styles[metric.status]]}
            testID={`telemetry-metric-${index}`}
          >
            <Text style={styles.label}>{metric.label}</Text>
            <Text style={styles.value}>
              {metric.value}
              <Text style={styles.unit}> {metric.unit}</Text>
            </Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: "#f7fafc" },
  header: { fontSize: 24, fontWeight: "bold", marginBottom: 4 },
  timestamp: { fontSize: 12, color: "#718096", marginBottom: 16 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  card: {
    width: "47%",
    backgroundColor: "#fff",
    padding: 16,
    borderRadius: 8,
    borderLeftWidth: 4,
  },
  normal: { borderLeftColor: "#38a169" },
  warning: { borderLeftColor: "#d69e2e" },
  critical: { borderLeftColor: "#e53e3e" },
  label: { fontSize: 12, color: "#718096", marginBottom: 4, textTransform: "uppercase" },
  value: { fontSize: 24, fontWeight: "bold", color: "#2d3748" },
  unit: { fontSize: 14, fontWeight: "normal", color: "#718096" },
});
