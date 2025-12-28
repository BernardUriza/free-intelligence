# AURITY Navigation Architecture

**Last Updated**: 2025-12-08  
**Status**: Production  
**Owner**: Frontend Team

---

## Table of Contents
1. [Overview](#overview)
2. [Navigation Hierarchy](#navigation-hierarchy)
3. [Route Categories](#route-categories)
4. [PageHeader Standards](#pageheader-standards)
5. [User Flows](#user-flows)
6. [Developer Guidelines](#developer-guidelines)

---

## Overview

AURITY uses a **hub-and-spoke** navigation model:
- **Hub**: `/` (SlimIndexHub for authenticated, redirects to `/chat` for anonymous)
- **Spokes**: Individual feature pages accessible via global menu or keyboard shortcuts
- **Back navigation**: All pages can return to hub via back button

### Core Principles
1. **Consistency**: All pages use `PageHeader` with standardized config
2. **Discoverability**: Global menu (`AppNavigation`) accessible from every page
3. **Accessibility**: Keyboard shortcuts (1-9, C, O, R) for power users
4. **Context**: Headers show relevant metrics and state
5. **Escape hatches**: Always provide a way back to the hub

---

## Navigation Hierarchy

```
/ (Root - SlimIndexHub)
├── /chat (Public - Free Intelligence Chat)
│   └── No auth required
│   └── Keyboard: C
│
├── /medical-ai (Protected - MEDICO/ADMIN only)
│   ├── Patient Selection View
│   └── Workflow View (after patient selected)
│   └── Keyboard: 1
│
├── /dashboard (Public)
│   ├── ?mode=tv (Fullscreen TV display)
│   ├── ?mode=recepcion (Receptionist preview)
│   └── Default: Doctor/Staff control panel
│   └── Keyboard: 2
│
├── /timeline (Public)
│   └── Unified longitudinal memory (chats + audio)
│   └── Keyboard: 3
│
├── /policy (Public)
│   └── Read-only policy viewer
│   └── Keyboard: 4
│
├── /audit (Public)
│   └── System audit log viewer
│   └── Keyboard: 5
│
├── /admin/personas (Protected - ADMIN only)
│   └── AI persona management
│   └── Keyboard: 8
│
├── /admin/clinics (Protected - ADMIN only)
│   └── Clinic, doctor, and check-in management
│   └── Keyboard: 9
│
├── /admin/appointments (Protected - ADMIN only)
│   └── Appointment calendar (Bryntum Scheduler)
│   └── Keyboard: 0
│
├── /onboarding (Hidden - Demo flow)
│   └── Workflow simulation for demos
│   └── Keyboard: O
│   └── Not in public menu
│
├── /checkin (Patient-facing - QR access only)
│   └── Form-based check-in flow
│   └── No header (kiosk mode)
│
├── /checkin/chat (Patient-facing - QR access only)
│   └── Conversational check-in with FI Receptionist
│   └── Keyboard: R (from /checkin)
│   └── Custom header (not using PageHeader)
│
├── /profile (Protected)
│   └── User profile and settings
│
├── /config (Protected - SUPERADMIN only)
│   └── System configuration
│
├── /infra/nas-installer (Protected)
│   └── Self-hosted deployment tools
│
├── /callback (Auth0 redirect)
│   └── No header (loading state)
│
└── /unauthorized (Error page)
    └── No header (error state)
```

---

## Route Categories

### Public Routes
Accessible to all users (authenticated or anonymous):
- `/chat` - Main chat interface (NEW: added to navigation 2025-12-08)
- `/dashboard` - Control panel and TV displays
- `/timeline` - Longitudinal memory viewer
- `/policy` - Policy configuration viewer
- `/audit` - Audit log viewer

### Protected Routes
Require specific roles:
- `/medical-ai` - Requires `MEDICO` or `ADMIN` role
- `/admin/*` - Requires `ADMIN` role
- `/config` - Requires `FI-superadmin` role

### Hidden Routes
Accessible but not in primary navigation:
- `/onboarding` - Demo/training flow
- `/checkin` - Patient check-in (QR code only)
- `/checkin/chat` - Conversational check-in (QR code only)

### Special Pages
No navigation (loading/error states):
- `/callback` - Auth0 OAuth callback
- `/unauthorized` - Access denied page

---

## PageHeader Standards

All pages **MUST** use the centralized `PageHeader` component with configs from `config/page-headers.ts`.

### Standard Pattern

```typescript
import { PageHeader } from '@/components/layout/PageHeader';
import { myPageHeader } from '@/config/page-headers';

export default function MyPage() {
  const headerConfig = myPageHeader({
    // Dynamic data
    metric: someValue,
  });

  return (
    <div className="min-h-screen bg-slate-950">
      <PageHeader {...headerConfig} />
      {/* Page content */}
    </div>
  );
}
```

### Required Header Props
All page headers include:
- `showBackButton: true` - Always provide back navigation
- `backPath: '/'` - Return to hub (SlimIndexHub)
- `icon` - Semantic icon from Lucide
- `iconColor` - Consistent color scheme
- `title` - Clear page title
- `subtitle` - Context or current state

### Optional Props
- `metrics` - Array of badges (icon + value)
- `actions` - Custom action buttons (right side)
- `showNavigation` - Show hamburger menu (default: true)

### Exceptions
Pages that **intentionally** don't use `PageHeader`:
1. `/checkin` - Kiosk mode for patients
2. `/checkin/chat` - Custom branded header
3. `/callback` - Loading redirect
4. `/unauthorized` - Error page
5. `/dashboard?mode=tv` - Fullscreen TV display

---

## User Flows

### Anonymous User Journey
1. Lands on `/` → Auto-redirected to `/chat`
2. Uses chat without authentication
3. Can navigate to public pages via menu
4. Cannot access protected routes

### Authenticated User Journey
1. Lands on `/` → Shows `SlimIndexHub`
2. Selects feature via:
   - Keyboard shortcut (1-9, C)
   - Click navigation card
   - Global menu (hamburger)
3. Works in feature page
4. Returns to hub via back button
5. Repeat

### Doctor Workflow (Medical AI)
1. `/` → `/medical-ai` (shortcut: 1)
2. Select patient from list
3. Record consultation
4. Review transcription
5. Export SOAP note
6. Return to hub or select next patient

### Admin Workflow (Clinic Management)
1. `/` → `/admin/clinics` (shortcut: 9)
2. Create/edit clinic
3. Manage doctors
4. View appointments
5. Generate QR codes for check-in
6. Return to hub

### Patient Workflow (Check-in)
1. Scan QR code in waiting room
2. Lands on `/checkin?clinic=xxx&t=xxx&n=xxx`
3. Choose flow:
   - Form-based: Stay on `/checkin`
   - Conversational: Navigate to `/checkin/chat`
4. Complete check-in
5. See success message
6. (Browser tab closes)

---

## Developer Guidelines

### Adding a New Page

1. **Create the page** in `app/[route]/page.tsx`

2. **Add header config** in `config/page-headers.ts`:
   ```typescript
   export const myPageHeader: PageHeaderFactory = (data) => ({
     showBackButton: true,
     backPath: '/',
     icon: 'iconName',
     iconColor: 'text-color-400',
     title: 'Page Title',
     subtitle: 'Description',
     metrics: data?.someMetric ? [...] : [],
   });
   ```

3. **Add to `PAGE_HEADERS`** object:
   ```typescript
   export const PAGE_HEADERS = {
     ...existing,
     'my-page': myPageHeader,
   } as const;
   ```

4. **Add route to navigation** in `lib/navigation.ts`:
   ```typescript
   {
     id: "my-page",
     title: "My Page",
     description: "What this page does",
     href: "/my-page",
     icon: MyIcon,
     shortcut: "X", // Pick unique key
     badge: "Optional",
   }
   ```

5. **Add icon to `PageHeader`** if new (in `components/layout/PageHeader.tsx`):
   ```typescript
   import { MyIcon } from 'lucide-react';
   
   const ICON_MAP: Record<string, LucideIcon> = {
     ...existing,
     myIcon: MyIcon,
   };
   ```

6. **Use in page**:
   ```typescript
   import { PageHeader } from '@/components/layout/PageHeader';
   import { myPageHeader } from '@/config/page-headers';
   
   export default function MyPage() {
     const headerConfig = myPageHeader({ /* data */ });
     return (
       <div className="min-h-screen bg-slate-950">
         <PageHeader {...headerConfig} />
         {/* content */}
       </div>
     );
   }
   ```

### Do's and Don'ts

✅ **DO**:
- Use centralized header configs
- Provide back navigation on all pages
- Add meaningful keyboard shortcuts
- Update this documentation when adding routes
- Test navigation flows manually

❌ **DON'T**:
- Hardcode `PageHeader` props inline
- Create orphaned pages with no navigation path
- Skip the back button (unless kiosk mode)
- Reuse keyboard shortcuts
- Break the hub-and-spoke model

### Testing Checklist

Before shipping a new page:
- [ ] PageHeader renders correctly
- [ ] Back button navigates to hub (`/`)
- [ ] Global menu (hamburger) works
- [ ] Keyboard shortcut works
- [ ] Header metrics update with state
- [ ] Protected routes enforce auth
- [ ] Page appears in navigation (if public)
- [ ] Mobile responsive
- [ ] Accessibility (screen reader + keyboard nav)

---

## Recent Changes

### 2025-12-08 - Navigation Standardization
- **Added**: `/chat` to public navigation (shortcut: C)
- **Added**: Centralized header configs for all pages
- **Fixed**: `/onboarding` now has PageHeader
- **Updated**: All admin pages use config-based headers
- **Added**: `messageCircle` icon to PageHeader
- **Documented**: Complete navigation hierarchy in this file

### 2025-11-XX - Initial Navigation System
- Created `PageHeader` component
- Created `AppNavigation` dropdown menu
- Defined keyboard shortcuts in `lib/navigation.ts`

---

## Support

Questions about navigation? Ask in #frontend channel or tag @frontend-team.

Found a bug? File an issue with tag `navigation`.
