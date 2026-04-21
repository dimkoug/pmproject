# Frontend - React + TypeScript

## Development

```bash
npm install
npm run dev      # Start dev server on port 3000
npm run build    # Production build
npm test         # Run tests (vitest)
npm run test:watch  # Watch mode
```

## Project Structure

```
src/
  app/            # Redux store configuration, typed hooks
  components/     # Reusable UI components
    charts/       # Recharts wrappers (Burndown, EVM, Histogram, Velocity)
    dnd/          # Drag-and-drop components (Board, Column, Card)
    Spinner.tsx   # Loading spinner
    EmptyState.tsx
    ErrorBoundary.tsx
    Toast.tsx     # Toast notification system
    ProtectedRoute.tsx
  pages/          # 30+ page components (one per route)
  services/       # State management
    api.ts        # RTK Query API slice (all endpoints)
    authSlice.ts  # Auth state (token, user, localStorage)
    wsSlice.ts    # WebSocket event state
    useWebSocket.ts  # WebSocket hook with auto-reconnect
  test/           # Test infrastructure
    handlers.ts   # MSW request handlers (mock API)
    server.ts     # MSW server setup
    setup.ts      # Vitest setup (cleanup, jest-dom)
    test-utils.tsx  # renderWithProviders helper
    *.test.tsx    # Test files
```

## Key Libraries

- **React Router 7** - Client-side routing with nested layouts
- **Redux Toolkit** - State management with RTK Query for API caching
- **Recharts** - Charts (burndown, EVM, Monte Carlo, velocity)
- **react-select** - Searchable dropdowns (task predecessors)
- **MSW** - API mocking for tests
