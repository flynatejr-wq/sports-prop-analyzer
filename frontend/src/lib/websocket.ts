import type { Prop } from "./types";

type WSMessage =
  | { type: "snapshot"; data: Prop[] }
  | { type: "props_update"; data: Prop[] }
  | { type: "alert"; data: { title: string; message: string } }
  | { type: "pong" }
  | { type: "heartbeat" };

type Listener = (msg: WSMessage) => void;

class PropWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Set<Listener> = new Set();
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private url: string;
  private shouldReconnect = true;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    if (typeof window === "undefined") return;
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[WS] Connected");
        this.pingInterval = setInterval(() => {
          this.ws?.send("ping");
        }, 25000);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          this.listeners.forEach((l) => l(msg));
        } catch {
          // ignore malformed messages
        }
      };

      this.ws.onclose = () => {
        console.log("[WS] Disconnected");
        this._cleanup();
        if (this.shouldReconnect) {
          this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
        }
      };

      this.ws.onerror = (err) => {
        console.warn("[WS] Error", err);
      };
    } catch (err) {
      console.warn("[WS] Failed to connect:", err);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this._cleanup();
    this.ws?.close();
    this.ws = null;
  }

  subscribe(listener: Listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private _cleanup() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

// Derive WebSocket URL from the API URL env var if WS_URL not explicit.
// In production this will typically be: wss://backend-xxx.up.railway.app/ws/live
function buildWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL + "/ws/live";
  }
  const api = process.env.NEXT_PUBLIC_API_URL;
  if (api) {
    return api.replace(/^https?/, (s) => (s === "https" ? "wss" : "ws")) + "/ws/live";
  }
  return "ws://localhost:8000/ws/live";
}

const WS_URL = buildWsUrl();

export const propSocket = new PropWebSocket(WS_URL);
export type { WSMessage, Listener };
