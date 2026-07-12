import { useEffect, useState, useRef } from "react";
import type { TelemetrySnapshot, RobotConfiguration } from "./types/telemetry";
import { TelemetryTransport } from "./utils/telemetryTransport";
import type { ConnectionState } from "./utils/telemetryTransport";
import { StatusBadge } from "./components/StatusBadge";
import { CommandBar } from "./components/CommandBar";
import { ConfigurationForm } from "./components/ConfigurationForm";
import { StateTracker } from "./components/StateTracker";
import { GantryVisualizer } from "./components/GantryVisualizer";

const DEFAULT_BOUNDS = {
  x: { min: -1000, max: 1000 },
  y: { min: -1000, max: 1000 },
  z: { min: -1000, max: 1000 },
};

const INITIAL_TELEMETRY: TelemetrySnapshot = {
  timestamp: new Date().toISOString(),
  sequence_id: null,
  status: "ready",
  state: "ready",
  requires_homing: true,
  position: { x: 0, y: 0, z: 0 },
  velocity: { x: 0, y: 0, z: 0 },
  target_position: null,
  cube_position: { x: 100, y: 100, z: 0 },
  cube_current_position: { x: 100, y: 100, z: 0 },
  cube_status: "at_source",
  destination_position: { x: 800, y: 800, z: 0 },
  workspace_bounds: DEFAULT_BOUNDS,
  gripper_state: "OPEN",
  is_moving: false,
  last_error: null,
};

const INITIAL_CONFIG: RobotConfiguration = {
  cube_position: { x: 100, y: 100, z: 0 },
  destination_position: { x: 800, y: 800, z: 0 },
  safe_z: 500,
  home_position: { x: 0, y: 0, z: 0 },
  travel_speed: 90,
  home_speed: 50,
};

export function App() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot>(INITIAL_TELEMETRY);
  const [config, setConfig] = useState<RobotConfiguration>(INITIAL_CONFIG);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [isStale, setIsStale] = useState(false);
  const [pendingCommand, setPendingCommand] = useState<"start" | "home" | "reset" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const lastFrameTimeRef = useRef<number>(Date.now());

  // Connect to telemetry stream on mount
  useEffect(() => {
    const transport = new TelemetryTransport({
      onFrame: (frame) => {
        setTelemetry(frame);
        lastFrameTimeRef.current = Date.now();
        setIsStale(false);
      },
      onStatusChange: (status) => {
        setConnectionState(status);
      },
    });

    transport.connect();

    // Setup active watchdog to flag stale state if no frame arrives for > 1500ms
    const watchdog = setInterval(() => {
      if (Date.now() - lastFrameTimeRef.current > 1500) {
        setIsStale(true);
      }
    }, 500);

    // Initial fetch of saved configuration
    const fetchConfig = async () => {
      try {
        const res = await fetch("/api/configuration");
        if (res.ok) {
          const data = await res.json();
          setConfig(data);
        }
      } catch (err) {
        console.error("Failed to load initial configuration:", err);
      }
    };

    fetchConfig();

    return () => {
      transport.disconnect();
      clearInterval(watchdog);
    };
  }, []);

  // Sync telemetry-provided configuration with client form if it updates backend-side
  useEffect(() => {
    // If running, respect live backend coordinates
    if (telemetry.status === "running" || telemetry.status === "homing") {
      setConfig((prev) => ({
        ...prev,
        cube_position: telemetry.cube_position,
        destination_position: telemetry.destination_position,
      }));
    }
  }, [telemetry.cube_position, telemetry.destination_position, telemetry.status]);

  const handleStart = async () => {
    setActionError(null);
    setPendingCommand("start");
    try {
      const res = await fetch("/api/commands/start", { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error?.message || "Failed to start pick and place sequence");
      }
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setPendingCommand(null);
    }
  };

  const handleHome = async () => {
    setActionError(null);
    setPendingCommand("home");
    try {
      const res = await fetch("/api/commands/home", { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error?.message || "Failed to start homing operation");
      }
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setPendingCommand(null);
    }
  };

  const handleReset = async () => {
    setActionError(null);
    setPendingCommand("reset");
    try {
      const res = await fetch("/api/commands/reset", { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error?.message || "Failed to reset FSM fault state");
      }
    } catch (err: any) {
      setActionError(err.message);
    } finally {
      setPendingCommand(null);
    }
  };

  const handleSaveConfig = async (newConfig: RobotConfiguration) => {
    setActionError(null);
    const res = await fetch("/api/configuration", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newConfig),
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.error?.message || "Failed to update configuration");
    }

    const savedData = await res.json();
    setConfig(savedData);
  };

  const isRobotBusy = telemetry.status === "running" || telemetry.status === "homing";

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Master Top Bar */}
      <header
        className="glass-panel"
        style={{
          margin: "1.5rem 1.5rem 0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderRadius: "16px",
          padding: "1rem 2rem",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.5rem" }}>GANTRY CRANE ROBOTICS</h1>
          <span style={{ fontSize: "0.8rem", color: "var(--color-text-dim)" }}>
            Premium Multi-Axis PLC Sequencer Control App
          </span>
        </div>
        <StatusBadge
          status={telemetry.status}
          connectionState={connectionState}
          isStale={isStale}
        />
      </header>

      {/* Grid Dashboard */}
      <main className="dashboard-grid">
        {/* Left Hand: Operations & Configuration */}
        <section style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Action/Command Error Banner */}
          {actionError && (
            <div
              style={{
                background: "rgba(248, 113, 113, 0.1)",
                color: "var(--color-danger)",
                border: "1px solid rgba(248, 113, 113, 0.2)",
                borderRadius: "16px",
                padding: "1rem",
                fontSize: "0.9rem",
                fontWeight: "600",
              }}
            >
              Operation Error: {actionError}
            </div>
          )}

          {/* Active PLC Faults / Error Diagnostics */}
          {telemetry.last_error && (
            <div
              style={{
                background: "linear-gradient(135deg, rgba(248, 113, 113, 0.15) 0%, rgba(248, 113, 113, 0.05) 100%)",
                border: "1px solid rgba(248, 113, 113, 0.35)",
                borderRadius: "16px",
                padding: "1.25rem",
                boxShadow: "var(--glow-danger)",
              }}
            >
              <h3 style={{ color: "var(--color-danger)", marginTop: 0, marginBottom: "0.5rem", display: "flex", alignItems: "center" }}>
                ACTIVE STATE FAULT
              </h3>
              <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.7)", fontFamily: "monospace", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                <div>CODE: <strong>{telemetry.last_error.code}</strong></div>
                <div>STATE: <strong>{telemetry.last_error.state}</strong></div>
                <div style={{ marginTop: "0.5rem", color: "#fff", fontWeight: "600" }}>
                  MESSAGE: {telemetry.last_error.message}
                </div>
              </div>
            </div>
          )}

          <ConfigurationForm
            savedConfiguration={config}
            disabled={isRobotBusy || connectionState === "disconnected"}
            onSave={handleSaveConfig}
          />

          <CommandBar
            status={telemetry.status}
            connectionState={connectionState}
            isStale={isStale}
            requiresHoming={telemetry.requires_homing}
            pendingCommand={pendingCommand}
            onStart={handleStart}
            onHome={handleHome}
            onReset={handleReset}
          />
        </section>

        {/* Right Hand: Visualizer & Execution Checklist */}
        <section style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <GantryVisualizer telemetry={telemetry} safeZ={config?.safe_z} />
          <StateTracker state={telemetry.state} isStale={isStale} />
        </section>
      </main>
    </div>
  );
}
export default App;
