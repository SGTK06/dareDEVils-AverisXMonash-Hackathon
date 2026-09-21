/**
 * Direct Supabase helpers for user preferences and comparison results.
 * Uses the supabase-js client (authenticated via Supabase Auth session).
 */
import { supabase } from './supabaseClient'

// ── Types ────────────────────────────────────────────────────

export type UserPreferences = {
  theme: 'light' | 'dark' | 'system'
  last_view: string
  filters: Record<string, unknown>
}

const DEFAULT_PREFS: UserPreferences = {
  theme: 'light',
  last_view: 'inbox',
  filters: {},
}

// ── User Preferences ─────────────────────────────────────────

export async function loadPreferences(userId: string): Promise<UserPreferences> {
  try {
    const { data, error } = await supabase
      .from('user_preferences')
      .select('theme, last_view, filters')
      .eq('user_id', userId)
      .single()

    if (error || !data) return DEFAULT_PREFS
    return {
      theme: data.theme ?? 'light',
      last_view: data.last_view ?? 'inbox',
      filters: data.filters ?? {},
    }
  } catch {
    return DEFAULT_PREFS
  }
}

export async function savePreferences(
  userId: string,
  prefs: Partial<UserPreferences>
): Promise<void> {
  try {
    const { error } = await supabase
      .from('user_preferences')
      .upsert(
        {
          user_id: userId,
          ...prefs,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'user_id' }
      )
    if (error) console.error("Supabase upsert error:", error)
  } catch (err) {
    console.error("Supabase upsert exception:", err)
    // Best-effort — don't crash the UI if DB is unavailable
  }
}

// ── Debounced preference save ────────────────────────────────

let _prefTimer: ReturnType<typeof setTimeout> | null = null

export function savePreferencesDebounced(
  userId: string,
  prefs: Partial<UserPreferences>,
  delayMs = 1000
): void {
  if (_prefTimer) clearTimeout(_prefTimer)
  _prefTimer = setTimeout(() => {
    savePreferences(userId, prefs)
    _prefTimer = null
  }, delayMs)
}
