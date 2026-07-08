/**
 * RemoteConversationLibrary — the cloud ConversationLibrary adapter.
 *
 * Implements the @free-intelligence/core contract over the server's
 * /conversations CRUD (og118 is the canary backend), so a signed-in account's
 * transcripts follow it across browsers/devices instead of living in one
 * browser's IndexedDB. Same dumb-store discipline as the IndexedDB adapter:
 * records arrive already sanitized (core helpers upstream) and are stored as
 * given; the server enforces ownership by the auth principal.
 *
 * Transport is injected, never assumed: `headers` supplies the Authorization
 * header per request (tokens rotate — read at call time, not construction),
 * and `fetchImpl` is overridable for tests/non-browser runtimes.
 */

import type {
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';

export interface RemoteConversationLibraryOptions {
  /** API origin, e.g. `https://api.example.com` (no trailing slash needed). */
  baseUrl: string;
  /** Per-request headers (Authorization). Read at call time so rotated tokens
   * are picked up. Default: none. */
  headers?: () => Record<string, string>;
  /** Fetch implementation. Default: the global `fetch`. */
  fetchImpl?: typeof fetch;
}

export class RemoteConversationLibrary implements ConversationLibrary {
  private readonly baseUrl: string;
  private readonly headers: () => Record<string, string>;
  private readonly fetchImpl: typeof fetch;

  constructor(options: RemoteConversationLibraryOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.headers = options.headers ?? (() => ({}));
    // Bound, not a bare reference: calling an unbound `window.fetch` through a
    // class field throws "Illegal invocation" (its `this` must be the window).
    this.fetchImpl = options.fetchImpl ?? fetch.bind(globalThis);
  }

  private async request(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<Response> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method,
      headers: {
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...this.headers(),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    return response;
  }

  private static async fail(operation: string, response: Response): Promise<never> {
    throw new Error(
      `RemoteConversationLibrary.${operation} failed: HTTP ${response.status}`,
    );
  }

  async list(): Promise<ConversationSummary[]> {
    const response = await this.request('GET', '/conversations');
    if (!response.ok) await RemoteConversationLibrary.fail('list', response);
    const data = (await response.json()) as { conversations: ConversationSummary[] };
    return data.conversations;
  }

  async get(id: string): Promise<ConversationRecord | null> {
    const response = await this.request(
      'GET',
      `/conversations/${encodeURIComponent(id)}`,
    );
    if (response.status === 404) return null;
    if (!response.ok) await RemoteConversationLibrary.fail('get', response);
    return (await response.json()) as ConversationRecord;
  }

  async put(record: ConversationRecord): Promise<void> {
    const response = await this.request(
      'PUT',
      `/conversations/${encodeURIComponent(record.id)}`,
      record,
    );
    if (!response.ok) await RemoteConversationLibrary.fail('put', response);
  }

  async delete(id: string): Promise<void> {
    const response = await this.request(
      'DELETE',
      `/conversations/${encodeURIComponent(id)}`,
    );
    if (!response.ok) await RemoteConversationLibrary.fail('delete', response);
  }

  async clear(): Promise<void> {
    const response = await this.request('DELETE', '/conversations');
    if (!response.ok) await RemoteConversationLibrary.fail('clear', response);
  }
}
