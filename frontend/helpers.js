/**
 * Make API request with proper error handling and retry logic
 */
async function makeApiRequest(endpoint, options = {}) {
  const url = `${window.API_CONFIG.BASE_URL}${endpoint}`;
  
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Origin': window.location.origin,
    },
  };
  
  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options.headers || {}),
    },
  };
  
  console.log(`[API] ${mergedOptions.method} ${url}`);
  
  for (let attempt = 0; attempt < window.API_CONFIG.MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), window.API_CONFIG.TIMEOUT);
      
      const response = await fetch(url, {
        ...mergedOptions,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      console.log(`[API] Response status: ${response.status}`);
      
      // Handle HTTP errors
      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorData;
        
        try {
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
          } else {
            errorData = await response.text();
          }
        } catch (e) {
          errorData = `HTTP ${response.status}`;
        }
        
        console.error(`[API] Error:`, errorData);
        throw new Error(`${response.status}: ${errorData?.message || errorData || response.statusText}`);
      }
      
      // Parse successful response
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        console.log(`[API] Success:`, data);
        return data;
      } else {
        const text = await response.text();
        console.log(`[API] Success (text):`, text);
        return { data: text };
      }
      
    } catch (error) {
      console.error(`[API] Attempt ${attempt + 1} failed:`, error.message);
      
      if (error.name === 'AbortError') {
        throw new Error(`Request timeout after ${window.API_CONFIG.TIMEOUT}ms`);
      }
      
      if (attempt < window.API_CONFIG.MAX_RETRIES - 1) {
        const delay = window.API_CONFIG.RETRY_DELAY * Math.pow(2, attempt);
        console.log(`[API] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw error;
      }
    }
  }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease-out reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/**
 * Get client IP address
 */
async function getClientIP() {
  try {
    const response = await fetch('https://api.ipify.org?format=json');
    const data = await response.json();
    return data.ip;
  } catch {
    return 'unknown';
  }
}

/**
 * Validate age
 */
function validateAge(age) {
  const ageNum = parseInt(age, 10);
  if (!age) return 'Age is required';
  if (isNaN(ageNum)) return 'Age must be a number';
  if (ageNum < 13) return 'You must be at least 13 years old';
  if (ageNum > 120) return 'Please enter a valid age';
  return null;
}

/**
 * Validate sex/gender
 */
function validateSex(sex) {
  if (!sex) return 'Gender is required';
  if (!['M', 'F', 'O'].includes(sex)) return 'Please select a valid gender';
  return null;
}

/**
 * Get assessment ID from URL parameters
 */
function getAssessmentIdFromURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

/**
 * Show error message
 */
function showError(message) {
  const errorContainer = document.getElementById('error-state') || document.body;
  errorContainer.innerHTML = `<div class="error-message" style="padding: 20px; background-color: #fee; color: #c33; border-radius: 8px; margin: 20px;"><strong>Error:</strong> ${message}</div>`;
  showToast(message, 'error', 5000);
}
