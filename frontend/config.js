
// ============================================================================
// API CONFIGURATION & ENVIRONMENT SETUP
// ============================================================================

// Determine API URL based on environment
function getAPIURL() {
  // Check for Vercel environment variable first (production)
  if (typeof process !== 'undefined' && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // Check for window variable (if set by HTML)
  if (window.API_BASE_URL) {
    return window.API_BASE_URL;
  }
  
  // Check localStorage for override (development)
  const storedURL = localStorage.getItem('API_URL');
  if (storedURL) {
    console.log('[CONFIG] Using API URL from localStorage:', storedURL);
    return storedURL;
  }
  
  // Default to Render backend
  const defaultURL = 'https://neuropersona.onrender.com';
  console.log('[CONFIG] Using default API URL:', defaultURL);
  return defaultURL;
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
  isProduction: window.location.hostname !== 'localhost',
  isLocalhost: window.location.hostname === 'localhost',
  hostname: window.location.hostname,
});

/**
 * Override API URL for testing (for development)
 * Example: window.setAPIURL('http://localhost:5000')
 */
window.setAPIURL = function(url) {
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
  window.API_CONFIG.BASE_URL = 'https://neuropersona.onrender.com';
  console.log('[CONFIG] API URL reset to default');
  alert('API URL reset to default.\nReload the page to apply changes.');
};

/**
 * Check API health
 */
window.checkAPIHealth = async function() {
  try {
    const response = await fetch(`${window.API_CONFIG.BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Origin': window.location.origin,
      },
    });
    const data = await response.json();
    console.log('[API HEALTH]', data);
    alert(`✓ API Health: ${JSON.stringify(data)}`);
    return true;
  } catch (error) {
    console.error('[API HEALTH ERROR]', error);
    alert(`✗ API Health Check Failed: ${error.message}`);
    return false;
  }
};



