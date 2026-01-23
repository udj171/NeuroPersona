// ============================================================================
// CONFIGURATION & CONSTANTS
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://personality-assessment-api.onrender.com';

const CONFIG = {
    API_URL: API_BASE_URL,
    ASSESSMENT_TIMEOUT: 300000, // 5 minutes
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // milliseconds
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

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
 * Make API request with retry logic
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${CONFIG.API_URL}${endpoint}`;
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Origin': window.location.origin,
        },
        timeout: CONFIG.ASSESSMENT_TIMEOUT,
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
    
    for (let attempt = 0; attempt < CONFIG.MAX_RETRIES; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), mergedOptions.timeout);
            
            const response = await fetch(url, {
                ...mergedOptions,
                signal: controller.signal,
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            lastError = error;
            
            if (attempt < CONFIG.MAX_RETRIES - 1) {
                const delay = CONFIG.RETRY_DELAY * Math.pow(2, attempt);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw new Error(`API request failed after ${CONFIG.MAX_RETRIES} attempts: ${lastError.message}`);
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
 * Validate email address
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Validate age
 */
function isValidAge(age) {
    const ageNum = parseInt(age, 10);
    return ageNum >= 13 && ageNum <= 120;
}

/**
 * Validate sex/gender selection
 */
function isValidSex(sex) {
    return ['M', 'F', 'O'].includes(sex);
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

// ============================================================================
// PAGE NAVIGATION & INITIALIZATION
// ============================================================================

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
            const sectionHeight = section.clientHeight;
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
            trackEvent('start_assessment_click', {
                button_location: btn.closest('section')?.id || 'header',
                timestamp: new Date().toISOString(),
            });
        });
    });
}

/**
 * Check API connection on page load
 */
async function checkApiConnection() {
    try {
        const response = await apiRequest('/api/health');
        console.log('✓ API connection successful', response);
        return true;
    } catch (error) {
        console.warn('⚠ API connection check failed:', error.message);
        showToast('Backend service temporarily unavailable', 'warning', 5000);
        return false;
    }
}

/**
 * Initialize page on load
 */
function initializePage() {
    console.log('Initializing page...');
    
    initSmoothScroll();
    initActiveNavHighlight();
    initCtaTracking();
    checkApiConnection();
    
    console.log('Page initialization complete');
}

// ============================================================================
// QUESTIONNAIRE FUNCTIONALITY
// ============================================================================

/**
 * Initialize questionnaire page
 */
function initQuestionnaireForm() {
    const form = document.querySelector('form[data-form="demographics"]');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const age = document.querySelector('input[name="age"]')?.value;
        const sex = document.querySelector('select[name="sex"]')?.value;
        
        // Validation
        if (!isValidAge(age)) {
            showToast('Please enter a valid age (13-120)', 'error');
            return;
        }
        
        if (!isValidSex(sex)) {
            showToast('Please select a valid gender', 'error');
            return;
        }
        
        try {
            trackEvent('demographics_submitted', { age, sex });
            
            // Store demographics for later
            sessionStorage.setItem('demographics', JSON.stringify({ age, sex }));
            
            // Show questionnaire section
            const questionnaireSection = document.querySelector('[data-section="questions"]');
            if (questionnaireSection) {
                questionnaireSection.style.display = 'block';
                questionnaireSection.scrollIntoView({ behavior: 'smooth' });
            }
            
            showToast('Demographics saved! Start answering questions below.', 'success');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
        }
    });
}

/**
 * Submit assessment answers
 */
async function submitAssessment() {
    const demographicsStr = sessionStorage.getItem('demographics');
    if (!demographicsStr) {
        showToast('Please fill in demographics first', 'error');
        return;
    }
    
    const demographics = JSON.parse(demographicsStr);
    const responses = gatherResponses();
    
    if (!responses || Object.keys(responses).length === 0) {
        showToast('Please answer all questions', 'error');
        return;
    }
    
    try {
        showToast('Processing assessment...', 'info');
        
        trackEvent('assessment_submitted', {
            question_count: Object.keys(responses).length,
            timestamp: new Date().toISOString(),
        });
        
        // Show loading indicator
        const submitBtn = document.querySelector('button[data-action="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Processing...';
        }
        
        // Submit assessment
        const result = await apiRequest('/api/submit-assessment', {
            method: 'POST',
            body: JSON.stringify({
                ...demographics,
                responses: responses,
                user_agent: navigator.userAgent,
                ip_address: await getClientIP(),
            }),
        });
        
        if (result && result.assessment_id) {
            showToast('Assessment submitted successfully!', 'success');
            
            // Redirect to results page
            setTimeout(() => {
                window.location.href = `results.html?id=${result.assessment_id}`;
            }, 1500);
        }
    } catch (error) {
        showToast(`Submission failed: ${error.message}`, 'error');
        const submitBtn = document.querySelector('button[data-action="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Submit Assessment';
        }
    }
}

/**
 * Gather responses from questionnaire
 */
function gatherResponses() {
    const responses = {};
    const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
    
    inputs.forEach(input => {
        responses[input.name] = parseInt(input.value, 10);
    });
    
    return responses;
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
 * Display progress on questionnaire
 */
function updateProgressBar() {
    const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
    const answeredCount = Array.from(inputs).filter(i => i.value > 0).length;
    const progressPercent = (answeredCount / inputs.length) * 100;
    
    const progressBar = document.querySelector('[data-element="progress-bar"]');
    if (progressBar) {
        progressBar.style.width = `${progressPercent}%`;
    }
    
    const progressText = document.querySelector('[data-element="progress-text"]');
    if (progressText) {
        progressText.textContent = `${answeredCount} / ${inputs.length} answered`;
    }
}

// ============================================================================
// RESULTS PAGE FUNCTIONALITY
// ============================================================================

/**
 * Load and display results
 */
async function loadResults() {
    const params = new URLSearchParams(window.location.search);
    const assessmentId = params.get('id');
    
    if (!assessmentId) {
        showToast('No assessment ID provided', 'error');
        return;
    }
    
    try {
        showToast('Loading your results...', 'info');
        
        const result = await apiRequest(`/api/results/${assessmentId}`);
        
        if (result) {
            displayResults(result);
            trackEvent('results_loaded', {
                assessment_id: assessmentId,
                personality_type: result.personality_type,
            });
        }
    } catch (error) {
        showToast(`Failed to load results: ${error.message}`, 'error');
    }
}

/**
 * Display results on page
 */
function displayResults(result) {
    const resultsContainer = document.querySelector('[data-element="results-container"]');
    if (!resultsContainer) return;
    
    const personalityType = result.personality_type || 'Unknown';
    const confidence = formatNumber(result.confidence_score || 0);
    const interpretation = result.interpretation || 'Assessment processing...';
    
    resultsContainer.innerHTML = `
        <div class="results-card">
            <div class="personality-type">
                <span class="type-letter">${personalityType}</span>
                <h2>${getPersonalityDescription(personalityType)}</h2>
            </div>
            
            <div class="confidence-meter">
                <div class="confidence-label">Match Confidence</div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidence * 100}%"></div>
                </div>
                <div class="confidence-value">${(confidence * 100).toFixed(0)}%</div>
            </div>
            
            <div class="interpretation">
                <h3>Your Personality Profile</h3>
                <p>${interpretation}</p>
            </div>
            
            <div class="domain-scores">
                <h3>Domain Scores</h3>
                ${renderDomainScores(result.domain_scores || {})}
            </div>
            
            <div class="actions">
                <button onclick="exportResultsPDF('${result.assessment_id}')" class="btn btn-primary">
                    📥 Download PDF
                </button>
                <button onclick="shareResults('${result.assessment_id}')" class="btn btn-secondary">
                    📤 Share Results
                </button>
                <a href="index.html" class="btn btn-secondary">← Back Home</a>
            </div>
        </div>
    `;
}

/**
 * Render domain scores chart
 */
function renderDomainScores(scores) {
    const domains = ['R', 'S', 'C', 'A', 'O', 'E'];
    const domainNames = {
        'R': 'Resilience',
        'S': 'Stability',
        'C': 'Creativity',
        'A': 'Ambition',
        'O': 'Openness',
        'E': 'Empathy',
    };
    
    return domains.map(domain => {
        const score = scores[domain] || 0;
        const percentage = (score / 10) * 100;
        
        return `
            <div class="score-item">
                <label>${domainNames[domain]}</label>
                <div class="score-bar">
                    <div class="score-fill" style="width: ${percentage}%"></div>
                </div>
                <span class="score-value">${formatNumber(score)}/10</span>
            </div>
        `;
    }).join('');
}

/**
 * Export results as PDF
 */
async function exportResultsPDF(assessmentId) {
    try {
        trackEvent('pdf_download_clicked', { assessment_id: assessmentId });
        showToast('Generating PDF...', 'info');
        
        // In production, call backend endpoint to generate PDF
        const link = document.createElement('a');
        link.href = `${CONFIG.API_URL}/api/export/pdf/${assessmentId}`;
        link.download = `assessment-${assessmentId}.pdf`;
        link.click();
        
        showToast('PDF downloaded successfully!', 'success');
    } catch (error) {
        showToast(`PDF export failed: ${error.message}`, 'error');
    }
}

/**
 * Share results
 */
function shareResults(assessmentId) {
    try {
        const url = `${window.location.origin}/results.html?id=${assessmentId}`;
        
        if (navigator.share) {
            navigator.share({
                title: 'My Personality Assessment Results',
                text: 'I just took a personality assessment. Check out my results!',
                url: url,
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(url);
            showToast('Results link copied to clipboard!', 'success');
        }
        
        trackEvent('results_shared', { assessment_id: assessmentId });
    } catch (error) {
        showToast('Share failed', 'error');
    }
}

// ============================================================================
// EVENT LISTENERS & DOM INITIALIZATION
// ============================================================================

// Run on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    
    // Initialize based on page type
    const currentPage = window.location.pathname;
    
    if (currentPage.includes('index.html') || currentPage === '/') {
        initializePage();
    } else if (currentPage.includes('questionnaire.html')) {
        initQuestionnaireForm();
        
        // Update progress as user answers
        document.addEventListener('input', updateProgressBar);
        
        // Handle submission
        const submitBtn = document.querySelector('button[data-action="submit"]');
        if (submitBtn) {
            submitBtn.addEventListener('click', submitAssessment);
        }
    } else if (currentPage.includes('results.html')) {
        loadResults();
    }
});

// Export functions for use in HTML
window.submitAssessment = submitAssessment;
window.exportResultsPDF = exportResultsPDF;
window.shareResults = shareResults;
window.updateProgressBar = updateProgressBar;
window.showToast = showToast;
