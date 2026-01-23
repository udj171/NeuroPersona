// ============================================================================
// COMMON API & UTILITY FUNCTIONS
// ============================================================================

/**
 * Show toast notification
 */
function showToast(message, type = 'success', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.right = '20px';
  toast.style.padding = '12px 16px';
  toast.style.borderRadius = '8px';
  toast.style.zIndex = '9999';
  
  if (type === 'success') {
    toast.style.backgroundColor = '#27ae60';
  } else if (type === 'error') {
    toast.style.backgroundColor = '#e74c3c';
  } else if (type === 'warning') {
    toast.style.backgroundColor = '#f39c12';
  }
  
  toast.style.color = 'white';
  toast.style.animation = 'slideIn 0.3s ease-out';
  
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Make API request with retry logic and proper error handling
 */
async function apiRequest(endpoint, options = {}) {
  if (!window.API_CONFIG) {
    throw new Error('API_CONFIG not initialized. Ensure config.js is loaded first.');
  }

  const url = `${window.API_CONFIG.BASE_URL}${endpoint}`;
  console.log(`[API] ${options.method || 'GET'} ${url}`);

  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Origin': window.location.origin,
    },
    timeout: window.API_CONFIG.TIMEOUT,
  };

  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {}),
    },
  };

  let lastError;

  for (let attempt = 0; attempt < window.API_CONFIG.MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        console.log(`[API] Request timeout after ${mergedOptions.timeout}ms`);
        controller.abort();
      }, mergedOptions.timeout);

      const response = await fetch(url, {
        ...mergedOptions,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Log response status
      console.log(`[API] Response: ${response.status} ${response.statusText}`);

      // Check for error status codes
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[API] Error response:`, errorText);

        // 404 Not Found
        if (response.status === 404) {
          throw new Error(`Endpoint not found: ${endpoint}`);
        }
        // 500 Server Error
        if (response.status >= 500) {
          throw new Error(`Server error: ${response.statusText}`);
        }
        // 400 Bad Request
        if (response.status === 400) {
          throw new Error(`Invalid request: ${errorText}`);
        }

        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log(`[API] Success:`, data);
      return data;

    } catch (error) {
      lastError = error;
      console.warn(`[API] Attempt ${attempt + 1}/${window.API_CONFIG.MAX_RETRIES} failed:`, error.message);

      // Don't retry on 404 or 400 errors
      if (error.message.includes('not found') || error.message.includes('Invalid request')) {
        throw error;
      }

      // Retry with exponential backoff
      if (attempt < window.API_CONFIG.MAX_RETRIES - 1) {
        const delay = window.API_CONFIG.RETRY_DELAY * Math.pow(2, attempt);
        console.log(`[API] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw new Error(`API request failed after ${window.API_CONFIG.MAX_RETRIES} attempts: ${lastError?.message || 'Unknown error'}`);
}

/**
 * Validate age
 */
function isValidAge(age) {
  const ageNum = parseInt(age, 10);
  return !isNaN(ageNum) && ageNum >= 13 && ageNum <= 120;
}

/**
 * Validate sex/gender selection
 */
function isValidSex(sex) {
  return ['M', 'F', 'O'].includes(sex);
}

/**
 * Validate email address
 */
function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Format number to 2 decimal places
 */
function formatNumber(num) {
  return parseFloat(num).toFixed(2);
}

/**
 * Get personality type description
 */
function getPersonalityDescription(type) {
  const descriptions = {
    'A': 'The Analytical - Detail-oriented, logical, and systematic',
    'B': 'The Builder - Practical, goal-focused, and ambitious',
    'C': 'The Connector - Social, empathetic, and relationship-driven',
    'D': 'The Driver - Competitive, confident, and action-oriented',
    'E': 'The Explorer - Creative, curious, and open-minded',
    'F': 'The Facilitator - Collaborative, supportive, and harmony-seeking',
  };
  return descriptions[type] || 'Unknown Type';
}

/**
 * Track analytics event
 */
function trackEvent(eventName, eventData = {}) {
  if (window.gtag) {
    gtag('event', eventName, eventData);
  }
  console.log(`[Analytics] ${eventName}`, eventData);
}

/**
 * Scroll to element smoothly
 */
function smoothScrollTo(element) {
  element.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Initialize smooth scroll for anchor links
 */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href !== '#') {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          smoothScrollTo(target);
        }
      }
    });
  });
}
