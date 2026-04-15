import type { StreamEvent } from '@/types/messages';

type MessageHandler = (event: StreamEvent) => void;
type StatusHandler = (status: 'connecting' | 'connected' | 'disconnected' | 'error') => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private url: string = '';
  private shouldReconnect = false;

  connect(sessionId: string, token?: string): void {
    this.disconnect();
    this.shouldReconnect = true;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const tokenParam = token ? `?token=${token}` : '';
    this.url = `${protocol}//${host}/ws/${sessionId}${tokenParam}`;

    this.notifyStatus('connecting');
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.notifyStatus('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent;
        this.messageHandlers.forEach((handler) => handler(data));
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    this.ws.onclose = () => {
      this.notifyStatus('disconnected');
    };

    this.ws.onerror = () => {
      this.notifyStatus('error');
    };
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter((h) => h !== handler);
    };
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter((h) => h !== handler);
    };
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  getShouldReconnect(): boolean {
    return this.shouldReconnect;
  }

  getUrl(): string {
    return this.url;
  }

  private notifyStatus(status: 'connecting' | 'connected' | 'disconnected' | 'error'): void {
    this.statusHandlers.forEach((handler) => handler(status));
  }
}

export const wsService = new WebSocketService();
