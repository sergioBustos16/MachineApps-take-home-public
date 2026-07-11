import type { TelemetrySnapshot } from "../types/telemetry";

export type ConnectionState = "connecting" | "streaming" | "polling" | "disconnected";

export interface TelemetryTransportCallbacks {
  onFrame(frame: TelemetrySnapshot): void;
  onStatusChange(state: ConnectionState): void;
}

export class TelemetryTransport {
  private callbacks: TelemetryTransportCallbacks;
  private state: ConnectionState = "disconnected";
  private pollingTimer: number | null = null;

  constructor(callbacks: TelemetryTransportCallbacks) {
    this.callbacks = callbacks;
  }

  public connect(): void {
    this.disconnect();
    this.updateState("connecting");
    this.startPolling();
  }

  public disconnect(): void {
    if (this.pollingTimer !== null) {
      window.clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
    this.updateState("disconnected");
  }

  private updateState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.callbacks.onStatusChange(newState);
    }
  }

  private startPolling(): void {
    this.updateState("polling");

    const poll = async () => {
      try {
        const res = await fetch("/api/telemetry", { method: "GET" });
        if (!res.ok) {
          throw new Error(`Telemetry polling failed with HTTP ${res.status}`);
        }

        const snapshot = await res.json() as TelemetrySnapshot;
        this.callbacks.onFrame(snapshot);
        this.updateState("polling");
      } catch (err) {
        console.error("HTTP telemetry polling failed:", err);
        this.updateState("disconnected");
      }
    };

    void poll();
    this.pollingTimer = window.setInterval(() => {
      void poll();
    }, 250);
  }
}
