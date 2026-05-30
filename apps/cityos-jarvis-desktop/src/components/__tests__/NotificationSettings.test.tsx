import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { NotificationSettingsPanel, useNotificationSettings } from "../NotificationSettings";
import { renderHook, act } from "@testing-library/react";

describe("useNotificationSettings", () => {
  it("loads default settings", () => {
    const { result } = renderHook(() => useNotificationSettings());
    expect(result.current.settings.enabled).toBe(true);
    expect(result.current.settings.soundEnabled).toBe(true);
  });

  it("updates settings", () => {
    const { result } = renderHook(() => useNotificationSettings());
    act(() => {
      result.current.update({ enabled: false });
    });
    expect(result.current.settings.enabled).toBe(false);
  });

  it("detects quiet hours overnight", () => {
    const { result } = renderHook(() => useNotificationSettings());
    act(() => {
      result.current.update({ doNotDisturb: true, quietHoursStart: 22, quietHoursEnd: 7 });
    });

    // Mock current hour to 23
    const originalGetHours = Date.prototype.getHours;
    Date.prototype.getHours = () => 23;
    expect(result.current.isQuietHours()).toBe(true);
    Date.prototype.getHours = originalGetHours;
  });

  it("allows notifications outside quiet hours", () => {
    const { result } = renderHook(() => useNotificationSettings());
    act(() => {
      result.current.update({ doNotDisturb: true, quietHoursStart: 22, quietHoursEnd: 7 });
    });

    const originalGetHours = Date.prototype.getHours;
    Date.prototype.getHours = () => 12;
    expect(result.current.isQuietHours()).toBe(false);
    expect(result.current.shouldNotify()).toBe(true);
    Date.prototype.getHours = originalGetHours;
  });

  it("persists to localStorage", () => {
    renderHook(() => useNotificationSettings());
    const stored = localStorage.getItem("cityosjarvis-notifications");
    expect(stored).toBeTruthy();
  });
});

describe("NotificationSettingsPanel", () => {
  it("renders all settings", () => {
    render(<NotificationSettingsPanel />);
    expect(screen.getByTestId("notif-enabled")).toBeInTheDocument();
    expect(screen.getByTestId("notif-sound")).toBeInTheDocument();
    expect(screen.getByTestId("notif-preview")).toBeInTheDocument();
    expect(screen.getByTestId("notif-dnd")).toBeInTheDocument();
  });

  it("shows quiet hours when DND enabled", () => {
    render(<NotificationSettingsPanel />);
    fireEvent.click(screen.getByTestId("notif-dnd"));
    expect(screen.getByTestId("quiet-hours")).toBeInTheDocument();
  });

  it("hides quiet hours when DND disabled", () => {
    render(<NotificationSettingsPanel />);
    fireEvent.click(screen.getByTestId("notif-dnd"));
    fireEvent.click(screen.getByTestId("notif-dnd"));
    expect(screen.queryByTestId("quiet-hours")).not.toBeInTheDocument();
  });
});
