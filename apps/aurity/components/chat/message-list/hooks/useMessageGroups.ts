'use client';

/**
 * useMessageGroups - Groups messages by date
 *
 * Memoized grouping for performance
 */

import { useMemo } from 'react';
import { format } from 'date-fns';
import type { FIMessage } from '@aurity-standalone/types/assistant';
import type { MessageGroup } from '../core/types';

export function useMessageGroups(messages: FIMessage[]): MessageGroup[] {
  return useMemo(() => {
    const groups: MessageGroup[] = [];

    messages.forEach(message => {
      const dateKey = format(new Date(message.timestamp), 'yyyy-MM-dd');
      const existingGroup = groups.find(g => g.date === dateKey);

      if (existingGroup) {
        existingGroup.messages.push(message);
      } else {
        groups.push({ date: dateKey, messages: [message] });
      }
    });

    return groups;
  }, [messages]);
}
