/**
 * Icons Module Index
 *
 * Centralized icon exports for the application.
 * All icon mappings use Lucide React icons for consistency.
 */

// Medical/clinical icons
export {
  MEDICAL_SERVICE_ICONS,
  HEALTH_CATEGORY_ICONS,
  CONTENT_TYPE_ICONS,
  CLINICAL_ICONS,
  AI_ICONS,
  getMedicalServiceIcon,
  getHealthCategoryIcon,
  getContentTypeIcon,
  getClinicalIcon,
  getAIIcon,
} from './medical-icons';

// Check-in action icons
export {
  CHECKIN_ACTION_ICONS,
  CHECKIN_STATUS_ICONS,
  getCheckinActionIcon,
  getCheckinStatusIcon,
} from './checkin-icons';

// UI/general icons
export {
  USER_ROLE_ICONS,
  CLINIC_TYPE_ICONS,
  VOLUME_ICONS,
  EXPERIENCE_ICONS,
  VOICE_ICONS,
  FILTER_ICONS,
  PERSONA_ICONS,
  getUserRoleIcon,
  getClinicTypeIcon,
  getExperienceIcon,
  getPersonaIcon,
  getFilterIcon,
} from './ui-icons';

// Dynamic icon mapping (for config objects with iconKey)
export {
  DYNAMIC_ICONS,
  getDynamicIcon,
  hasIconKey,
} from './dynamic-icons';

// Status icons (replaces emojis like ✅❌⚠️)
export {
  STATUS_ICONS,
  STATUS_COLORS,
  getStatusIcon,
  getStatusColor,
  hasStatusIcon,
  LOG_PREFIXES,
} from './status-icons';
