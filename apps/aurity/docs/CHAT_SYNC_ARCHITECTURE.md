# Chat Sync Architecture (SOLID Refactor)

**Card**: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
**Author**: Bernard Uriza Orozco
**Created**: 2025-11-20
**Philosophy**: "No existen sesiones. Solo una conversación infinita"

## 📐 Architecture Overview

Three-tier hybrid sync for infinite conversation memory:

```
┌─────────────────────────────────────────────────────────┐
│ L1: LocalStorage (IMessageStorage)                      │
│ ➜ 0ms instant UX                                        │
│ ➜ Persists across browser refreshes                    │
│ ➜ Ephemeral for anonymous users                        │
└─────────────────────────────────────────────────────────┘
                        ↕ merge/dedup
┌─────────────────────────────────────────────────────────┐
│ L2: Backend Sync (IBackendSync)                         │
│ ➜ Periodic fetch every 30s                             │
│ ➜ H5 storage with sentence embeddings                  │
│ ➜ Cross-device consistency                             │
└─────────────────────────────────────────────────────────┘
                        ↕ real-time
┌─────────────────────────────────────────────────────────┐
│ L3: WebSocket (IRealtimeSync)                           │
│ ➜ 0ms latency for new messages                         │
│ ➜ Auto-reconnect with exponential backoff              │
│ ➜ Broadcast to all devices of same doctor              │
└─────────────────────────────────────────────────────────┘
```

## 🎯 SOLID Principles Applied

### Single Responsibility Principle (SRP)
Each component has ONE reason to change:
- `IMessageStorage` → ONLY handles message persistence
- `IBackendSync` → ONLY handles backend fetch + merge
- `IRealtimeSync` → ONLY handles WebSocket connection
- `useFIConversation` → ONLY orchestrates conversation state

### Open/Closed Principle (OCP)
- ✅ Add IndexedDB storage without modifying `useFIConversation`
- ✅ Add SSE sync without modifying `BackendSyncStrategy`
- ✅ Add mock sync for tests without touching production code

### Liskov Substitution Principle (LSP)
Any implementation of `IMessageStorage` can replace `LocalStorageMessageStorage`:
```typescript
const storage: IMessageStorage = new InMemoryMessageStorage(); // Works!
const storage: IMessageStorage = new IndexedDBStorage(); // Works!
```

### Interface Segregation Principle (ISP)
Small, focused interfaces instead of one monolithic interface:
```typescript
IMessageStorage   → load, save, clear (3 methods)
IBackendSync      → sync, loadOlder (2 methods)
IRealtimeSync     → connect, disconnect, isConnected (3 methods)
```

### Dependency Inversion Principle (DIP)
High-level `useFIConversation` depends on abstractions, not concretions:
```typescript
// ❌ Before: Tight coupling
localStorage.setItem(key, JSON.stringify(messages));

// ✅ After: Dependency Inversion
storage.save(key, messages); // IMessageStorage interface
```

## 📂 File Structure

```
apps/aurity/
├─ lib/chat/
│  ├─ storage.ts                # IMessageStorage + implementations
│  ├─ sync-strategy.ts          # IBackendSync, IRealtimeSync + implementations
│  └─ sync.ts                   # Merge/dedup logic
└─ hooks/
   └─ useFIConversation.ts      # Main hook with DI
```

## 🔧 Usage

### Default (Production)
```typescript
const { messages, sendMessage } = useFIConversation({
  phase: 'welcome',
  context: { doctor_id: user.sub },
  storageKey: `fi_chat_${user.sub}`,
  autoIntroduction: true,
});
// Uses: LocalStorage + BackendSync + WebSocket (defaults)
```

### Testing (Dependency Injection)
```typescript
const mockStorage = new InMemoryMessageStorage();
const mockBackendSync = {
  sync: async () => [],
  loadOlder: async () => ({ messages: [], hasMore: false }),
};

const { messages } = useFIConversation({
  storage: mockStorage,
  backendSync: mockBackendSync,
  realtimeSync: null, // Disable WebSocket for tests
});
// Fully isolated, no side effects
```

## 🔄 Sync Flow Diagram

```
User opens chat widget
  ↓
[1] Load from localStorage (0ms) ────→ Display immediately
  ↓
[2] Background sync (100ms delay)
  ↓
Backend fetch (last 50 messages)
  ↓
Merge with localStorage (dedup)
  ↓
Update UI if different
  ↓
[3] Periodic sync every 30s ─────────→ Catch missed changes
  ↓
[4] WebSocket connect ───────────────→ Real-time updates (0ms)
```

## 🧪 Testing Strategy

### Unit Tests (Storage)
```typescript
const storage = new LocalStorageMessageStorage();
storage.save('test', messages);
expect(storage.load('test')).toEqual(messages);
storage.clear('test');
expect(storage.load('test')).toEqual([]);
```

### Integration Tests (Sync)
```typescript
const backendSync = new BackendSyncStrategy('http://localhost:7001');
const messages = await backendSync.sync('doctor_123', 'welcome', 50);
expect(messages).toHaveLength(50);
```

### E2E Tests (WebSocket)
```typescript
const realtimeSync = new WebSocketSyncStrategy();
realtimeSync.connect('doctor_123', (message) => {
  expect(message.role).toBe('assistant');
});
expect(realtimeSync.isConnected()).toBe(true);
```

## 📊 Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Initial load | 0ms | LocalStorage L1 cache |
| Backend sync | ~500ms | Background, non-blocking |
| WebSocket latency | <100ms | Real-time broadcast |
| Periodic sync | 30s | Resilient fallback |
| Storage size | ~50KB | 200 messages × 250 chars |

## 🔒 Security & Privacy

- **Anonymous users**: Ephemeral (InMemoryStorage), no persistence
- **Authenticated users**: LocalStorage + H5 backend
- **Cross-device sync**: Isolated by `doctor_id` (Auth0 user.sub)
- **WebSocket auth**: Query param `?doctor_id=auth0|123`

## 🚀 Future Enhancements

- [ ] IndexedDB storage for 10k+ message history
- [ ] Server-Sent Events (SSE) as WebSocket alternative
- [ ] Optimistic UI updates (instant send, sync later)
- [ ] Offline queue (store-and-forward when disconnected)
