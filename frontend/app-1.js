// ============================================================================
// CONFIGURATION & CONSTANTS - NOW USES window.API_CONFIG
// ============================================================================

// Removed duplicate CONFIG - now uses window.API_CONFIG from config.js

// ============================================================================
// PAGE INITIALIZATION
// ============================================================================

function initializePage() {
  console.log('[APP] Initializing page...');
  console.log('[APP] API Config:', window.API_CONFIG);
  
  initSmoothScroll();
  initActiveNavHighlight();
  initCtaTracking();
  checkApiConnection();
  
  console.log('[APP] Page initialization complete');
}

/**
 * Smooth scroll for navigation links
 */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const href = this.getAttribute('href');
      if (href !== '#') {
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });
}

/**
 * Highlight active navigation link on scroll
 */
function initActiveNavHighlight() {
  window.addEventListener('scroll', () => {
    let current = '';
    const sections = document.querySelectorAll('section[id]');
    
    sections.forEach(section => {
      const sectionTop = section.offsetTop;
      if (window.scrollY >= sectionTop - 200) {
        current = section.getAttribute('id');
      }
    });
    
    document.querySelectorAll('.nav-links a[href^="#"]').forEach(link => {
      link.style.color = '';
      if (link.getAttribute('href').slice(1) === current) {
        link.style.color = 'var(--color-primary)';
      }
    });
  });
}

/**
 * Initialize CTA button tracking
 */
function initCtaTracking() {
  document.querySelectorAll('a[href="questionnaire.html"]').forEach(btn => {
    btn.addEventListener('click', () => {
      console.log('[APP] Start assessment clicked');
    });
  });
}

/**
 * Check API connection on page load
 */
async function checkApiConnection() {
  try {
    const response = await makeApiRequest('/api/health');
    console.log('✓ API connection successful', response);
    return true;
  } catch (error) {
    console.warn('⚠ API connection check failed:', error.message);
    showToast('Backend service temporarily unavailable', 'warning', 5000);
    return false;
  }
}

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', initializePage);
