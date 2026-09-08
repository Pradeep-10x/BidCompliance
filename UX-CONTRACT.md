# PRAMAAN UX contract

This contract records observable frontend behavior. Backend authorization,
tender lifecycle, compliance rules, and audit integrity remain authoritative in
the FastAPI domain model and OpenAPI contract.

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Table Selection | `components/data-table.tsx` with TanStack Table | This contract | current-page selection | Keyboard and production build |
| Select/Listbox | Native select for simple audit filters; `components/ui/select.tsx` when authored popup behavior is required | `DESIGN.md` and this contract | native / authored | Keyboard, open popup, narrow viewport |
| Date | Native text display until an editable date workflow is implemented | This contract | typed / native | Locale and keyboard |
| Form | React Hook Form + Zod + shared field primitives; local state for credential-only login | This contract | login / create | Invalid, pending, server failure, keyboard |
| Scrollbar | Application document and browser defaults | `DESIGN.md` | platform | Keyboard and narrow viewport |
| Toast | Shared Sonner provider | This contract | success / warning / info / error | Live-region verification |
| CRUD | React Query mutations backed by server-authorized APIs | Backend OpenAPI and this contract | create / update / decision | Success, failure, retry, focus |

## Authentication

- `/` is the officer login route; authenticated routes redirect there when no
  access token is available.
- Login preserves the email after failure, keeps the password masked by default,
  blocks duplicate submission, and shows a persistent inline error.
- Successful login goes to `/dashboard`. “Log out” clears the local token and
  returns to `/`.
- The backend remains the authority for authentication and role checks; route
  protection in the browser is only a navigation aid.

## Async and failure behavior

- React Query owns request lifecycle and cache invalidation.
- Initial loads keep a stable content region. Failures remain visible in the
  owning screen and must provide enough context to retry.
- Mutations disable their initiating action while pending and never claim success
  before the server response.

## Navigation and accessibility

- The sidebar is the canonical authenticated navigation shell.
- Native controls keep platform keyboard behavior. Authored Radix controls keep
  focus management, Escape behavior, and accessible naming from shared owners.
- English (`en-IN`) is the current interface locale. Status, risk, identifiers,
  actor, and timestamps are exposed in text rather than color alone.
