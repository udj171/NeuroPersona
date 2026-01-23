// ============================================================================
// QUESTIONNAIRE MANAGEMENT
// ============================================================================

// Global state
let globalState = {
    demographics: null,
    responses: {},
    currentPage: 'demographics', // 'demographics' or 'questions'
};

// Questions data
const QUESTIONS = [
    { id: 'q1', text: 'I am analytical and detail-oriented', category: 'R' },
    { id: 'q2', text: 'I prefer stability and predictability', category: 'S' },
    { id: 'q3', text: 'I enjoy creative and artistic pursuits', category: 'C' },
    { id: 'q4', text: 'I am ambitious and goal-driven', category: 'A' },
    { id: 'q5', text: 'I am open to new experiences and ideas', category: 'O' },
    { id: 'q6', text: 'I am empathetic and compassionate', category: 'E' },
    { id: 'q7', text: 'I can adapt to changing circumstances', category: 'R' },
    { id: 'q8', text: 'I prefer routine and structure', category: 'S' },
    { id: 'q9', text: 'I have a unique and original perspective', category: 'C' },
    { id: 'q10', text: 'I work hard to achieve my goals', category: 'A' },
    { id: 'q11', text: 'I enjoy learning new things', category: 'O' },
    { id: 'q12', text: 'I care deeply about others\' feelings', category: 'E' },
    { id: 'q13', text: 'I handle stress well', category: 'R' },
    { id: 'q14', text: 'I like things to be organized', category: 'S' },
    { id: 'q15', text: 'I express myself creatively', category: 'C' },
    { id: 'q16', text: 'I am competitive', category: 'A' },
    { id: 'q17', text: 'I explore unconventional ideas', category: 'O' },
    { id: 'q18', text: 'I enjoy helping others', category: 'E' },
    { id: 'q19', text: 'I recover quickly from setbacks', category: 'R' },
    { id: 'q20', text: 'I prefer familiar environments', category: 'S' },
    { id: 'q21', text: 'I have a vivid imagination', category: 'C' },
    { id: 'q22', text: 'I take initiative in projects', category: 'A' },
    { id: 'q23', text: 'I question traditional ways of doing things', category: 'O' },
    { id: 'q24', text: 'I understand people\'s motivations', category: 'E' },
    { id: 'q25', text: 'I remain calm under pressure', category: 'R' },
    { id: 'q26', text: 'I prefer consistency in my life', category: 'S' },
    { id: 'q27', text: 'I enjoy artistic or musical activities', category: 'C' },
    { id: 'q28', text: 'I strive for excellence', category: 'A' },
    { id: 'q29', text: 'I see possibilities others miss', category: 'O' },
    { id: 'q30', text: 'I am a good listener', category: 'E' },
    { id: 'q31', text: 'I face challenges head-on', category: 'R' },
    { id: 'q32', text: 'I find comfort in predictability', category: 'S' },
    { id: 'q33', text: 'I think outside the box', category: 'C' },
    { id: 'q34', text: 'I pursue my ambitions with determination', category: 'A' },
    { id: 'q35', text: 'I value diversity and different perspectives', category: 'O' },
];

// ============================================================================
// API HELPER - CONSISTENT ACROSS ALL CALLS
// ============================================================================

/**
 * Make API request with proper error handling
 * @param {string} endpoint - API endpoint (e.g., '/api/submit-assessment')
 * @param {object} options - fetch options
 */
async function makeApiRequest(endpoint, options = {}) {
    const baseUrl = window.API_CONFIG?.BASE_URL || 'https://neuropersona.onrender.com';
    const url = `${baseUrl}${endpoint}`;
    
    console.log(`[API] ${options.method || 'GET'} ${url}`);
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    const config = {
        method: options.method || 'GET',
        headers: {
            ...defaultHeaders,
            ...(options.headers || {}),
        },
        ...(options.body && { body: options.body }),
    };
    
    try {
        const response = await fetch(url, config);
        
        console.log(`[API] Response status: ${response.status}`);
        
        // Handle non-JSON responses
        const contentType = response.headers.get('content-type');
        const isJson = contentType && contentType.includes('application/json');
        const data = isJson ? await response.json() : await response.text();
        
        if (!response.ok) {
            const errorMsg = data.error || data.message || `HTTP ${response.status}`;
            throw new Error(`${response.status}: ${errorMsg}`);
        }
        
        return data;
    } catch (error) {
        console.error(`[API] Error:`, error);
        throw error;
    }
}

// ============================================================================
// UI HELPERS
// ============================================================================

function showError(message) {
    console.error(`[UI] Error: ${message}`);
    const errorEl = document.getElementById('error-message');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    } else {
        alert(`Error: ${message}`);
    }
}

function showSuccess(message) {
    console.log(`[UI] Success: ${message}`);
    const successEl = document.getElementById('success-message');
    if (successEl) {
        successEl.textContent = message;
        successEl.style.display = 'block';
    }
}

function clearMessages() {
    const errorEl = document.getElementById('error-message');
    const successEl = document.getElementById('success-message');
    if (errorEl) errorEl.style.display = 'none';
    if (successEl) successEl.style.display = 'none';
}

// ============================================================================
// INITIALIZE PAGE
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[QUESTIONNAIRE] Initializing...');
    initializeDemographicsForm();
    initializeQuestionnaireForm();
    initializeButtons();
    console.log('[QUESTIONNAIRE] Ready');
});

// ============================================================================
// DEMOGRAPHICS FORM
// ============================================================================

function initializeDemographicsForm() {
    const form = document.getElementById('demographics-form');
    if (!form) return;
    
    form.addEventListener('submit', handleDemographicsSubmit);
}

function handleDemographicsSubmit(e) {
    e.preventDefault();
    clearMessages();
    
    const age = document.getElementById('age').value;
    const sex = document.getElementById('sex').value;
    
    // Validation
    const ageError = validateAge(age);
    if (ageError) {
        showError(ageError);
        return;
    }
    
    const sexError = validateSex(sex);
    if (sexError) {
        showError(sexError);
        return;
    }
    
    // Save demographics
    globalState.demographics = {
        age: parseInt(age),
        sex
    };
    sessionStorage.setItem('demographics', JSON.stringify(globalState.demographics));
    console.log('[QUESTIONNAIRE] Demographics saved:', globalState.demographics);
    
    // Show questions section
    document.getElementById('demographics-section').classList.add('hidden');
    document.getElementById('questions-section').classList.remove('hidden');
    globalState.currentPage = 'questions';
    
    // Scroll to top
    window.scrollTo(0, 0);
}

function validateAge(age) {
    const ageNum = parseInt(age, 10);
    if (!age || isNaN(ageNum)) return 'Please enter your age';
    if (ageNum < 13 || ageNum > 120) return 'Age must be between 13 and 120';
    return null;
}

function validateSex(sex) {
    if (!sex) return 'Please select a gender';
    if (!['M', 'F', 'O'].includes(sex)) return 'Invalid gender selection';
    return null;
}

// ============================================================================
// QUESTIONNAIRE FORM
// ============================================================================

function initializeQuestionnaireForm() {
    const form = document.getElementById('assessment-form');
    if (!form) return;
    
    // Generate question HTML
    const html = QUESTIONS.map((q, index) => `
        <div class="question-item" data-question-id="${q.id}">
            <label>${index + 1}. ${q.text}</label>
            <input 
                type="range" 
                id="${q.id}" 
                name="${q.id}" 
                min="0" 
                max="5" 
                value="0"
                class="question-slider"
                data-category="${q.category}"
            />
            <div class="slider-labels">
                <span>Strongly Disagree</span>
                <span>Neutral</span>
                <span>Strongly Agree</span>
            </div>
        </div>
    `).join('');
    
    form.innerHTML = html;
    
    // Add progress tracking
    const inputs = form.querySelectorAll('input[type="range"]');
    inputs.forEach(input => {
        input.addEventListener('change', updateProgress);
        input.addEventListener('input', updateProgress);
    });
}

function updateProgress() {
    const inputs = document.querySelectorAll('input[type="range"][id^="q"]');
    const answered = Array.from(inputs).filter(i => i.value > 0).length;
    const total = inputs.length;
    const percent = (answered / total) * 100;
    
    const progressBar = document.querySelector('[data-element="progress-bar"]');
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
    }
    
    const progressText = document.querySelector('[data-element="progress-text"]');
    if (progressText) {
        progressText.textContent = `${answered} / ${total} answered`;
    }
}

function gatherResponses() {
    const responses = {};
    const inputs = document.querySelectorAll('input[type="range"][id^="q"]');
    
    inputs.forEach(input => {
        const value = parseInt(input.value, 10);
        // Only include answers that aren't 0 (default)
        if (value > 0) {
            responses[input.id] = value;
        }
    });
    
    return responses;
}

// ============================================================================
// SUBMIT ASSESSMENT
// ============================================================================

function initializeButtons() {
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', handleSubmitAssessment);
    }
}

async function handleSubmitAssessment() {
    console.log('[SUBMIT] Starting submission...');
    clearMessages();
    
    if (!globalState.demographics) {
        showError('Please fill in demographics first');
        return;
    }
    
    const responses = gatherResponses();
    if (Object.keys(responses).length === 0) {
        showError('Please answer all questions');
        return;
    }
    
    const submitBtn = document.getElementById('submit-btn');
    
    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
        }
        
        const payload = {
            age: globalState.demographics.age,
            sex: globalState.demographics.sex,
            responses: responses,
            timestamp: new Date().toISOString()
        };
        
        console.log('[SUBMIT] Sending payload:', payload);
        
        // FIXED: Use makeApiRequest for consistent error handling
        const data = await makeApiRequest('/api/submit-assessment', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        
        console.log('[SUBMIT] Success response:', data);
        
        if (data.assessment_id) {
            showSuccess('Assessment submitted successfully! Redirecting...');
            setTimeout(() => {
                window.location.href = `results.html?id=${data.assessment_id}`;
            }, 1500);
        } else {
            showError('No assessment ID returned');
        }
    } catch (error) {
        console.error('[SUBMIT] Error:', error);
        showError(`Submission failed: ${error.message}`);
        
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Assessment';
        }
    }
}
