import React from "react";
import type { StatusBadgeProps } from "../types/telemetry";

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  connectionState,
  isStale,
}) => {
  const getStatusClass = () => {
    switch (status) {
      case "ready":
        return "status-ready";
      case "running":
        return "status-running";
      case "homing":
        return "status-homing";
      case "completed":
        return "status-completed";
      case "fault":
        return "status-fault";
      default:
        return "";
    }
  };

  const getConnectionClass = () => {
    switch (connectionState) {
      case "streaming":
        return "connection-streaming";
      case "polling":
        return "connection-polling";
      case "connecting":
        return "connection-connecting";
      case "disconnected":
        return "connection-disconnected";
      default:
        return "";
    }
  };

  return (
    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
      <span className={`status-badge ${getStatusClass()}`}>
        {isStale ? "stale" : status}
      </span>
      <span className={`connection-badge ${getConnectionClass()}`}>
        {connectionState === "streaming" ? "Live Stream" : connectionState}
      </span>
    </div>
  );
};
export default StatusBadge;
