const TOKEN_STORAGE_KEY = "queryshield_access_token";

function legacyLocalStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function sessionTokenStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage;
}

export function getStoredToken(): string | null {
  const sessionStorage = sessionTokenStorage();
  const token = sessionStorage?.getItem(TOKEN_STORAGE_KEY) ?? null;
  if (token) {
    return token;
  }

  const legacyToken = legacyLocalStorage()?.getItem(TOKEN_STORAGE_KEY) ?? null;
  if (legacyToken) {
    sessionStorage?.setItem(TOKEN_STORAGE_KEY, legacyToken);
    legacyLocalStorage()?.removeItem(TOKEN_STORAGE_KEY);
  }
  return legacyToken;
}

export function storeToken(token: string): void {
  sessionTokenStorage()?.setItem(TOKEN_STORAGE_KEY, token);
  legacyLocalStorage()?.removeItem(TOKEN_STORAGE_KEY);
}

export function clearStoredToken(): void {
  sessionTokenStorage()?.removeItem(TOKEN_STORAGE_KEY);
  legacyLocalStorage()?.removeItem(TOKEN_STORAGE_KEY);
}

export { TOKEN_STORAGE_KEY };