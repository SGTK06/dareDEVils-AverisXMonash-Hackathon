import { useAuth } from "./hooks/useAuth";
import { AuthPage } from "./components/AuthPage";
import Dashboard from "./Dashboard.tsx";

function App() {
  const { user, loading, signOut } = useAuth();

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
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return <Dashboard userEmail={user.email ?? ""} onSignOut={signOut} />;
}

export default App;
