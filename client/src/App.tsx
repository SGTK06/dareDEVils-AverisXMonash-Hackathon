import { useAuth } from './hooks/useAuth'
import { AuthPage } from './components/AuthPage'

function App() {
  const { user, loading, signOut } = useAuth()

  if (loading) {
    return (
      <main className="min-h-screen bg-black flex items-center justify-center">
        <svg
          className="h-5 w-5 animate-spin text-neutral-400"
          viewBox="0 0 24 24"
          fill="none"
          aria-label="Loading"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 0 1 8-8V0C5.37 0 0 5.37 0 12h4z"
          />
        </svg>
      </main>
    )
  }

  if (!user) {
    return <AuthPage />
  }

  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center gap-6 px-4">
      <div className="text-center">
        <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-white">
          Welcome back
        </h1>
        <p className="mt-2 text-[14px] text-neutral-400">
          {user.email}
        </p>
      </div>
      <button
        onClick={signOut}
        className="rounded-lg border border-neutral-800 bg-transparent px-5 py-2 text-[14px] font-medium text-white transition-colors hover:border-neutral-600 hover:bg-neutral-900 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white"
      >
        Sign out
      </button>
    </main>
  )
}

export default App
