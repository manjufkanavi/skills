# SPA "Wrong Page" Diagnosis

## Symptom

The frontend SPA loads but shows the wrong page by default — e.g., a settings/dashboard page with "No Project Selected" instead of a landing page. No errors in the browser console.

## Root Cause

The most common cause: `App.tsx` has **no routing at all**. It unconditionally renders a single component:

```typescript
// WRONG — no routing, renders the same thing for every URL
const App = () => (
  <div>
    <GeneratorUI />
  </div>
);
```

The app may have page components (`LandingPage`, `SignInPage`, etc.) defined, but they are **never imported or rendered** by `App.tsx`.

## Diagnosis Steps

1. **Open `App.tsx`** — does it have any conditional rendering, `<Route>` elements, or `useLocation()` hooks?
2. **Check URL** — is the browser showing `/`, `/signin`, `/settings`? Does changing the URL change the content?
3. **If URL doesn't matter** (always shows same content) → no routing exists
4. **If URL changes and content changes** → routing exists but may be misconfigured (wrong default route, auth redirect loop)

## Common Fixes

### Fix 1: Add React Router

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

const App = () => (
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/signin" element={<SignInPage />} />
      <Route path="/signup" element={<SignUpPage />} />
      <Route path="/dashboard" element={<AuthenticatedApp />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </BrowserRouter>
);
```

### Fix 2: Add Zustand Store Conditional Rendering

If the app already uses Zustand for state management:

```typescript
const App = () => {
  const currentView = useAppStore(state => state.currentView);
  
  const viewMap = {
    landing: <LandingPage onNavigate={...} />,
    signin: <SignInPage onSignIn={...} onNavigate={...} />,
    dashboard: <AuthenticatedApp />,
    settings: <AuthenticatedApp />,
  };
  
  return <>{viewMap[currentView] || <LandingPage />}</>;
};
```

### Fix 3: Add Auth Guard Redirect

```typescript
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/signin" replace />;
  return children;
};

// Usage:
<Route path="/dashboard" element={
  <ProtectedRoute><DashboardPage /></ProtectedRoute>
} />
```

## Why It Happens

1. **Migration from a different framework** — The old app used a different routing mechanism (e.g., angular routing, express middleware, file-based routing) that didn't translate to React Router
2. **GeneratorUI was the "only view"** — During development, GeneratorUI was the sole page; routing was never added when additional pages were created
3. **Migration from monorepo** — When splitting a monorepo into subpackages, `App.tsx` may not have been updated to reflect the new directory structure
4. **Placeholder `App.tsx`** — A minimal `App.tsx` was created during scaffolding but the router setup was never completed

## Prevention

- Always start with routing in `App.tsx` — even if all routes currently render the same component
- Define route constants in a central file so they can be shared with API client base URL logic
- Add an "Unknown Route" fallback (`path="*"`) to catch navigation errors early
