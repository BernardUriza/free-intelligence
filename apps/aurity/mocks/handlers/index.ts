import { auditHandlers } from '@/mocks/handlers/audit';
import { adminHandlers } from '@/mocks/handlers/admin';
import { assistantHandlers } from '@/mocks/handlers/assistant';
import { checkinHandlers } from '@/mocks/handlers/checkin';
import { clinicHandlers } from '@/mocks/handlers/clinics';
import { exportHandlers } from '@/mocks/handlers/exports';
import { miscHandlers } from '@/mocks/handlers/misc';
import { workflowHandlers } from '@/mocks/handlers/workflow';

export const handlers = [
  ...workflowHandlers,
  ...assistantHandlers,
  ...checkinHandlers,
  ...clinicHandlers,
  ...adminHandlers,
  ...exportHandlers,
  ...auditHandlers,
  ...miscHandlers,
];
