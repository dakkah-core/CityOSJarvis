/**
 * Notification settings panel for desktop app.
 * Configures system notifications, sounds, and alerts.
 */

import { useState, useEffect } from "react";

interface NotificationSettings {
  enabled: boolean;
  soundEnabled: boolean;
  showPreview: boolean;
  doNotDisturb: boolean;
  quietHoursStart: number;
  quietHoursEnd: number;
}

const STORAGE_KEY = "cityosjarvis-notifications";

function loadSettings(): NotificationSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch {}
  return {
    enabled: true,
    soundEnabled: true,
    showPreview: true,
    doNotDisturb: false,
    quietHoursStart: 22,
    quietHoursEnd: 7,
  };
}

function saveSettings(settings: NotificationSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function useNotificationSettings() {
  const [settings, setSettings] = useState<NotificationSettings>(loadSettings);

  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  const update = (patch: Partial<NotificationSettings>) => {
    setSettings((prev) => ({ ...prev, ...patch }));
  };

  const isQuietHours = (): boolean => {
    if (!settings.doNotDisturb) return false;
    const hour = new Date().getHours();
    if (settings.quietHoursStart > settings.quietHoursEnd) {
      // Overnight range (e.g., 22-7)
      return hour >= settings.quietHoursStart || hour < settings.quietHoursEnd;
    }
    return hour >= settings.quietHoursStart && hour < settings.quietHoursEnd;
  };

  const shouldNotify = (): boolean => {
    return settings.enabled && !isQuietHours();
  };

  return { settings, update, isQuietHours, shouldNotify };
}

export function NotificationSettingsPanel() {
  const { settings, update } = useNotificationSettings();

  return (
    <div className="notification-settings" data-testid="notification-settings">
      <label className="setting-row">
        <input
          type="checkbox"
          checked={settings.enabled}
          onChange={(e) => update({ enabled: e.target.checked })}
          data-testid="notif-enabled"
        />
        Enable notifications
      </label>

      <label className="setting-row">
        <input
          type="checkbox"
          checked={settings.soundEnabled}
          onChange={(e) => update({ soundEnabled: e.target.checked })}
          data-testid="notif-sound"
        />
        Play sound
      </label>

      <label className="setting-row">
        <input
          type="checkbox"
          checked={settings.showPreview}
          onChange={(e) => update({ showPreview: e.target.checked })}
          data-testid="notif-preview"
        />
        Show message preview
      </label>

      <label className="setting-row">
        <input
          type="checkbox"
          checked={settings.doNotDisturb}
          onChange={(e) => update({ doNotDisturb: e.target.checked })}
          data-testid="notif-dnd"
        />
        Do not disturb
      </label>

      {settings.doNotDisturb && (
        <div className="quiet-hours" data-testid="quiet-hours">
          <label>
            From
            <input
              type="number"
              min={0}
              max={23}
              value={settings.quietHoursStart}
              onChange={(e) => update({ quietHoursStart: parseInt(e.target.value) })}
              data-testid="quiet-start"
            />
          </label>
          <label>
            To
            <input
              type="number"
              min={0}
              max={23}
              value={settings.quietHoursEnd}
              onChange={(e) => update({ quietHoursEnd: parseInt(e.target.value) })}
              data-testid="quiet-end"
            />
          </label>
        </div>
      )}
    </div>
  );
}
