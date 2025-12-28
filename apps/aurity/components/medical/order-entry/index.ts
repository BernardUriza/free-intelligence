/**
 * OrderEntry Module
 *
 * Medical orders and prescriptions management.
 *
 * Modular structure:
 * - types.ts: TypeScript interfaces
 * - constants.ts: ORDER_TYPES configuration
 * - hooks/: useOrderManagement, useOrderChatbot
 * - components/: OrderTypeSelector, OrderStats, OrdersList, OrderChatbot
 */

export { OrderEntry, default } from './OrderEntry';
export type { OrderEntryProps, OrderType, ChatMessage } from './types';
