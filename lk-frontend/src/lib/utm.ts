/**
 * UTM tracking utilities.
 * Captures UTM parameters from URL, stores them in localStorage,
 * and attaches them to API requests.
 */

const UTM_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'gclid',
  'fbclid',
  'yclid',
] as const;

type UtmParams = Partial<Record<typeof UTM_KEYS[number], string>>;

export function extractUtmFromUrl(): UtmParams {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  const utm: UtmParams = {};
  UTM_KEYS.forEach(key => {
    const value = params.get(key);
    if (value) utm[key] = value;
  });
  return utm;
}

export function saveUtmToStorage(utm: UtmParams): void {
  if (typeof window === 'undefined') return;
  const stored = { ...utm, _timestamp: Date.now() };
  localStorage.setItem('bankruptcy_utm', JSON.stringify(stored));
}

export function loadUtmFromStorage(): UtmParams {
  if (typeof window === 'undefined') return {};
  const raw = localStorage.getItem('bankruptcy_utm');
  if (!raw) return {};
  try {
    const stored = JSON.parse(raw);
    const timestamp = stored._timestamp || 0;
    const age = Date.now() - timestamp;
    const maxAge = 30 * 24 * 60 * 60 * 1000;
    if (age > maxAge) {
      localStorage.removeItem('bankruptcy_utm');
      return {};
    }
    delete stored._timestamp;
    return stored;
  } catch {
    return {};
  }
}

export function getCurrentUtm(): UtmParams {
  const fromUrl = extractUtmFromUrl();
  const fromStorage = loadUtmFromStorage();
  const combined = { ...fromStorage, ...fromUrl };
  if (Object.keys(fromUrl).length > 0) {
    saveUtmToStorage(combined);
  }
  return combined;
}

export function attachUtmToFormData(formData: FormData): void {
  const utm = getCurrentUtm();
  Object.entries(utm).forEach(([key, value]) => {
    if (value) formData.append(key, value);
  });
}

export function attachUtmToJson<T extends Record<string, any>>(body: T): T & { utm?: UtmParams } {
  const utm = getCurrentUtm();
  if (Object.keys(utm).length === 0) return body;
  return { ...body, utm };
}

export function useUtm(): UtmParams {
  if (typeof window === 'undefined') return {};
  return getCurrentUtm();
}
