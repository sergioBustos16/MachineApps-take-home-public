import type { TelemetrySnapshot } from "../types/telemetry";

export type ConnectionState = "connecting" | "streaming" | "polling" | "disconnected";

export interface TelemetryTransportCallbacks {
  onFrame(frame: TelemetrySnapshot): void;
  onStatusChange(state: ConnectionState): void;
}

export class TelemetryTransport {
  private callbacks: TelemetryTransportCallbacks;
  private state: ConnectionState = "disconnected";
  private abortController: AbortController | null = null;
  private pollingTimer: number | null = null;
  private reconnectTimer: number | null = null;
  private reconnectDelay = 500; // ms
  private maxReconnectDelay = 10000; // ms

  constructor(callbacks: TelemetryTransportCallbacks) {
    this.callbacks = callbacks;
  }

  public connect(): void {
    this.disconnect();
    this.updateState("connecting");
    this.startStreaming();
  }

  public disconnect(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    if (this.pollingTimer !== null) {
      window.clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.updateState("disconnected");
  }

  private updateState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.callbacks.onStatusChange(newState);
    }
  }

  private async startStreaming(): Promise<void> {
    this.abortController = new AbortController();
    const url = "/rpc/vention.app.v1.GantryRobotService/telemetry";

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`Streaming request rejected with HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Streaming response has empty body");
      }

      this.updateState("streaming");
      this.reconnectDelay = 500; // Reset reconnection backoff on success

      const reader = response.body.getReader();
      let buffer = new Uint8Array(0);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // Append new chunk to current buffer
        const nextBuffer = new Uint8Array(buffer.length + value.length);
        nextBuffer.set(buffer, 0);
        nextBuffer.set(value, buffer.length);
        buffer = nextBuffer;

        // Process all complete envelopes in buffer
        // Frame format: 1 byte (flag) + 4 bytes (big-endian length) + body
        while (buffer.length >= 5) {
          const flag = buffer[0];
          const view = new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
          const bodyLength = view.getUint32(1, false); // big-endian

          if (buffer.length < 5 + bodyLength) {
            // Incomplete frame, wait for more chunks
            break;
          }

          // Extract frame payload
          const bodyBytes = buffer.subarray(5, 5 + bodyLength);
          buffer = buffer.subarray(5 + bodyLength);

          if (flag === 0x80) {
            // Trailer frame - indicates end of stream or error
            console.warn("FSM Stream trailer encountered");
            break;
          }

          try {
            const bodyStr = new TextDecoder().decode(bodyBytes);
            const snapshot = JSON.parse(bodyStr) as TelemetrySnapshot;
            this.callbacks.onFrame(snapshot);
          } catch (err) {
            console.error("Failed to parse telemetry JSON frame:", err);
          }
        }
      }

      // Stream closed gracefully
      this.scheduleReconnect();
    } catch (err: any) {
      if (err.name === "AbortError") {
        return;
      }
      console.warn("FastAPI stream failed or disconnected. Falling back to HTTP polling:", err);
      this.startPollingFallback();
    }
  }

  private startPollingFallback(): void {
    this.disconnect();
    this.updateState("polling");

    const poll = async () => {
      try {
        const res = await fetch("/api/telemetry", { method: "GET" });
        if (res.ok) {
          const snapshot = await res.json() as TelemetrySnapshot;
          this.callbacks.onFrame(snapshot);
        } else {
          console.warn(`HTTP Polling failed with HTTP ${res.status}`);
        }
      } catch (err) {
        console.error("HTTP Polling network error:", err);
      }
    };

    // Immediate first fetch
    poll();
    this.pollingTimer = window.setInterval(poll, 250); // poll at 4Hz
  }

  private scheduleReconnect(): void {
    this.updateState("disconnected");
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }
}
