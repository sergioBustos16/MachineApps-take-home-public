import React from "react";
import type { CommandBarProps } from "../types/telemetry";

export const CommandBar: React.FC<CommandBarProps> = ({
  status,
  requiresHoming,
  pendingCommand,
  onStart,
  onHome,
  onReset,
}) => {
  const isReady = status === "ready";
  const isFault = status === "fault";
  const isBusy = status === "running" || status === "homing";

  return (
    <div className="glass-panel" style={{ marginTop: "1rem" }}>
      <h2>Sequence Controls</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <button
          className="btn btn-primary"
          onClick={onStart}
          disabled={!isReady || requiresHoming || isBusy || pendingCommand !== null}
        >
          {pendingCommand === "start" ? "Starting..." : "Start Sequence"}
        </button>

        <button
          className="btn btn-secondary"
          onClick={onHome}
          disabled={!isReady || isBusy || pendingCommand !== null}
        >
          {pendingCommand === "home" ? "Homing..." : "Home Gantry"}
        </button>

        {isFault && (
          <button
            className="btn btn-danger"
            onClick={onReset}
            disabled={pendingCommand !== null}
            style={{ width: "100%" }}
          >
            {pendingCommand === "reset" ? "Resetting..." : "Reset Fault"}
          </button>
        )}

        {isReady && requiresHoming && (
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--color-warning)",
              textAlign: "center",
              marginTop: "0.25rem",
              fontWeight: "600",
            }}
          >
            ⚠️ Safe homing is mandatory before starting sequence
          </div>
        )}
      </div>
    </div>
  );
};
export default CommandBar;
