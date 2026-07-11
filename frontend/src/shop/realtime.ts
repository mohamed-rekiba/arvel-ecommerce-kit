// A tiny typed native-WebSocket client for K9's order/stock live-update relay
// (the framework relay `arvel.routing.broadcast_websocket`). Connects to `/ws`; a private channel first exchanges
// arvel's own POST /broadcasting/auth for a signed token (a cross-user/guest request is denied
// there — this client never decides ownership), a public channel needs none.
import { apiFetch } from '../api/http'

// The typed contract mirrors each event's `broadcast_with()` (backend) — no `any`.
export interface OrderPaidEvent {
  order_id: number
  status: 'paid'
  paid_at: string | null
}

export interface StockChangedEvent {
  variant_id: number
  stock: number
  in_stock: boolean
}

type ConnectedFrame = { event: 'connected'; socket_id: string }
type SubscribeErrorFrame = { event: 'subscribe_error'; channel: string }
type EventFrame<T> = { event: string; data: T }
type RelayFrame<T> = ConnectedFrame | SubscribeErrorFrame | EventFrame<T>

function relayUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

async function broadcastingAuth(socketId: string, channel: string): Promise<string | null> {
  try {
    const body = new URLSearchParams({ socket_id: socketId, channel_name: channel })
    const res = await apiFetch<{ auth: string }>('/broadcasting/auth', { method: 'POST', body })
    return res.auth
  } catch {
    return null // 401 (guest, no session) or 403 (not the channel's owner) — the caller falls back
  }
}

/**
 * Subscribe to `channel` (a bare or `private-`-prefixed wire name, e.g. `stock.9` /
 * `private-order.5`) over the relay. `onEvent` fires per pushed `{event, data}`. `onUnavailable`
 * fires **at most once**, only if the socket never delivers an event (connect failure, denied
 * auth, or a drop before any event) — never after a real event has already arrived, and never as
 * an unhandled rejection. Returns an unsubscribe function.
 */
export function subscribe<T>(
  channel: string,
  onEvent: (event: string, data: T) => void,
  onUnavailable: () => void
): () => void {
  let closed = false
  let settled = false

  function settle() {
    if (settled || closed) return
    settled = true
    onUnavailable()
  }

  let socket: WebSocket
  try {
    socket = new WebSocket(relayUrl())
  } catch {
    settle()
    return () => {}
  }

  socket.onerror = () => settle()
  socket.onclose = () => settle()
  socket.onmessage = (message: MessageEvent<string>) => {
    void handle(message).catch(() => settle())
  }

  async function handle(message: MessageEvent<string>): Promise<void> {
    let frame: RelayFrame<T>
    try {
      frame = JSON.parse(message.data) as RelayFrame<T>
    } catch {
      return
    }
    if ('socket_id' in frame) {
      // ConnectedFrame — structural narrowing (`in`), not a literal `event ===` compare: every
      // frame shares the wide `event: string` field, so a literal check alone can't discriminate.
      if (channel.startsWith('private-')) {
        const auth = await broadcastingAuth(frame.socket_id, channel)
        if (closed) return
        if (auth === null) {
          settle()
          return
        }
        socket.send(JSON.stringify({ event: 'subscribe', channel, auth }))
      } else {
        socket.send(JSON.stringify({ event: 'subscribe', channel }))
      }
      return
    }
    if ('channel' in frame) {
      // SubscribeErrorFrame
      settle()
      return
    }
    settled = true // a real event arrived — a later drop is not "unavailable" anymore
    onEvent(frame.event, frame.data)
  }

  return () => {
    closed = true
    socket.close()
  }
}
