import { useState } from 'react'
import { supabase } from '../lib/supabaseClient'

export function AuthPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'error' | 'success' } | null>(null)

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage(null)

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.origin,
      },
    })

    if (error) {
      setMessage({ text: error.message, type: 'error' })
    } else {
      setMessage({ text: 'Check your email for the magic link.', type: 'success' })
      setEmail('')
    }

    setLoading(false)
  }

  const handleGoogleAuth = async () => {
    setLoading(true)
    setMessage(null)

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin,
      },
    })

    if (error) {
      setMessage({ text: error.message, type: 'error' })
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-black flex items-center justify-center px-4">
      <div className="w-full max-w-[360px]">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-white">
            Sign in
          </h1>
          <p className="mt-2 text-[14px] text-neutral-400">
            Enter your email to receive a magic link.
          </p>
        </div>

        {/* Google OAuth */}
        <button
          type="button"
          onClick={handleGoogleAuth}
          disabled={loading}
          style={{ color: '#fff' }}
          className="flex w-full items-center justify-center gap-2.5 rounded-lg border border-neutral-800 bg-transparent px-4 py-2.5 text-[14px] font-medium text-white transition-colors hover:border-neutral-600 hover:bg-neutral-900 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white disabled:pointer-events-none disabled:opacity-40"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Continue with Google
        </button>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-800" />
          <span className="text-[12px] font-medium uppercase tracking-[0.08em] text-neutral-500">
            or
          </span>
          <div className="h-px flex-1 bg-neutral-800" />
        </div>

        {/* Email form */}
        <form onSubmit={handleMagicLink} className="space-y-3">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-[13px] font-medium text-neutral-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
              disabled={loading}
              className="w-full rounded-lg border border-neutral-800 bg-transparent px-3 py-2 text-[14px] text-white placeholder-neutral-600 transition-colors focus:border-white focus:outline-none disabled:opacity-40"
            />
          </div>

          {/* Message */}
          {message && (
            <p
              className={`text-[13px] ${
                message.type === 'error' ? 'text-red-400' : 'text-emerald-400'
              }`}
            >
              {message.text}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="mt-1 flex w-full items-center justify-center rounded-lg bg-white px-4 py-2.5 text-[14px] font-semibold text-black transition-colors hover:bg-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black disabled:pointer-events-none disabled:opacity-40"
          >
            {loading ? (
              <svg
                className="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
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
            ) : (
              'Send magic link'
            )}
          </button>
        </form>

      </div>
    </main>
  )
}
