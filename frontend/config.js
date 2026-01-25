// ============================================================================
// API CONFIGURATION & ENVIRONMENT SETUP (FIXED)
// ============================================================================

// Determine backend URL based on environment
const getBackendURL = () => {
  // 1) Vercel/production: environment variable
  if (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // 2) Localhost/staging: allow manual override via localStorage helper
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      const stored = localStorage.getItem('API_URL');
      if (stored) {
        console.log('[CONFIG] Using API URL from localStorage:', stored);
        return stored;
      }
      return 'http://localhost:5000';
    }

    // 3) Frontend hosted elsewhere (e.g. Vercel production) – default to Render backend
    const productionBackendURL = 'https://neuropersona.onrender.com';
    console.log('[CONFIG] Using default production API URL:', productionBackendURL);
    return productionBackendURL;
  }

  // Fallback (non‑browser contexts)
  return 'https://neuropersona.onrender.com';
};

// Compute and cache API base URL
function getAPIURL() {
  const url = getBackendURL();
  console.log('[CONFIG] Final API URL:', url);
  return url;
}

// Global API configuration
window.API_CONFIG = {
  BASE_URL: getAPIURL(),
  TIMEOUT: 30000, // 30 seconds
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000, // milliseconds
};

console.log('[CONFIG] API Base URL:', window.API_CONFIG.BASE_URL);
console.log('[CONFIG] Environment:', {
  isProduction: typeof window !== 'undefined' && window.location.hostname !== 'localhost',
  isLocalhost: typeof window !== 'undefined' && window.location.hostname === 'localhost',
  hostname: typeof window !== 'undefined' ? window.location.hostname : 'unknown',
});

// ============================================================================
// UTILITIES FOR DEVELOPMENT
// ============================================================================

/**
 * Override API URL for testing (for development)
 * Example: window.setAPIURL('http://localhost:5000')
 */
window.setAPIURL = function(url) {
  if (!url) return;
  window.API_CONFIG.BASE_URL = url;
  localStorage.setItem('API_URL', url);
  console.log('[CONFIG] API URL changed to:', url);
  alert(`API URL set to: ${url}\nReload the page to apply changes.`);
};

/**
 * Reset API URL to default
 * Example: window.resetAPIURL()
 */
window.resetAPIURL = function() {
  localStorage.removeItem('API_URL');
  window.API_CONFIG.BASE_URL = getBackendURL();
  console.log('[CONFIG] API URL reset to default:', window.API_CONFIG.BASE_URL);
  alert('API URL reset to default.\nReload the page to apply changes.');
};

/**
 * Check API health
 */
window.checkAPIHealth = async function() {
  try {
    console.log('[CONFIG] Checking API health at:', window.API_CONFIG.BASE_URL);
    const response = await fetch(`${window.API_CONFIG.BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    console.log('[CONFIG] API Health Check - SUCCESS:', data);
    alert(`✓ API Health: ${JSON.stringify(data)}`);
    return true;
  } catch (error) {
    console.error('[CONFIG] API Health Check - FAILED:', error);
    alert(`✗ API Health Check Failed: ${error.message}\n\nAPI URL: ${window.API_CONFIG.BASE_URL}`);
    return false;
  }
};

// Auto-check API on page load (optional, non‑blocking)
document.addEventListener('DOMContentLoaded', () => {
  console.log('[CONFIG] Page loaded, API config ready');
});
