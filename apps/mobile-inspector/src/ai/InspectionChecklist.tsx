/**
 * Offline-capable inspection checklist for field inspectors.
 */

import React, { useState, useCallback } from "react";
import { View, Text, TouchableOpacity, StyleSheet, FlatList, TextInput } from "react-native";

interface ChecklistItem {
  id: string;
  label: string;
  checked: boolean;
  notes: string;
  photoUri?: string;
}

interface InspectionChecklistProps {
  title: string;
  items: ChecklistItem[];
  onComplete: (items: ChecklistItem[]) => void;
  offline?: boolean;
}

export function InspectionChecklist({ title, items: initialItems, onComplete, offline = false }: InspectionChecklistProps) {
  const [items, setItems] = useState<ChecklistItem[]>(initialItems);

  const toggleItem = useCallback((id: string) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, checked: !item.checked } : item))
    );
  }, []);

  const updateNotes = useCallback((id: string, notes: string) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, notes } : item))
    );
  }, []);

  const progress = items.length > 0 ? items.filter((i) => i.checked).length / items.length : 0;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.progress}>
        {Math.round(progress * 100)}% complete ({items.filter((i) => i.checked).length}/{items.length})
      </Text>
      {offline && <Text style={styles.offlineBadge}>Offline Mode</Text>}

      <FlatList
        data={items}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.item}>
            <TouchableOpacity
              onPress={() => toggleItem(item.id)}
              style={[styles.checkbox, item.checked && styles.checkboxChecked]}
              testID={`checklist-item-${item.id}`}
            >
              {item.checked && <Text style={styles.checkmark}>✓</Text>}
            </TouchableOpacity>
            <View style={styles.itemContent}>
              <Text style={[styles.itemLabel, item.checked && styles.itemLabelChecked]}>
                {item.label}
              </Text>
              <TextInput
                style={styles.notesInput}
                placeholder="Add notes..."
                value={item.notes}
                onChangeText={(text) => updateNotes(item.id, text)}
                multiline
                testID={`checklist-notes-${item.id}`}
              />
            </View>
          </View>
        )}
      />

      <TouchableOpacity
        style={[styles.completeButton, progress < 1 && styles.completeButtonDisabled]}
        onPress={() => onComplete(items)}
        disabled={progress < 1}
        testID="checklist-complete"
      >
        <Text style={styles.completeButtonText}>Complete Inspection</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  title: { fontSize: 20, fontWeight: "bold", marginBottom: 8 },
  progress: { fontSize: 14, color: "#666", marginBottom: 8 },
  offlineBadge: { fontSize: 12, color: "#d69e2e", fontWeight: "600", marginBottom: 16 },
  item: { flexDirection: "row", alignItems: "flex-start", marginBottom: 16 },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: "#3182ce",
    marginRight: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: { backgroundColor: "#3182ce" },
  checkmark: { color: "#fff", fontWeight: "bold" },
  itemContent: { flex: 1 },
  itemLabel: { fontSize: 16, marginBottom: 4 },
  itemLabelChecked: { textDecorationLine: "line-through", color: "#666" },
  notesInput: {
    borderWidth: 1,
    borderColor: "#e2e8f0",
    borderRadius: 4,
    padding: 8,
    fontSize: 14,
    minHeight: 60,
  },
  completeButton: {
    backgroundColor: "#38a169",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 16,
  },
  completeButtonDisabled: { backgroundColor: "#a0aec0" },
  completeButtonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
});
