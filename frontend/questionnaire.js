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
    
    const age = document.getElementById('age').value;
    const sex = document.getElementById('sex').value;
    
    // Validation
    const ageError = validateAge(age);
    if (ageError) {
        document.getElementById('age-error').textContent = ageError;
        return;
    }
    
    const sexError = validateSex(sex);
    if (sexError) {
        document.getElementById('sex-error').textContent = sexError;
        return;
    }
    
    // Clear errors
    document.getElementById('age-error').textContent = '';
    document.getElementById('sex-error').textContent = '';
    
    // Save demographics
    globalState.demographics = { age: parseInt(age), sex };
    sessionStorage.setItem('demographics', JSON.stringify(globalState.demographics));
    
    console.log('[QUESTIONNAIRE] Demographics saved:', globalState.demographics);
    
    // Show questions section
    document.getElementById('demographics-section').classList.add('hidden');
    document.getElementById('questions-section').classList.remove('hidden');
    globalState.currentPage = 'questions';
    
    // Scroll to top
    window.scrollTo(0, 0);
}

// ============================================================================
// QUESTIONNAIRE FORM
// ============================================================================

function initializeQuestionnaireForm() {
    const form = document.getElementById('assessment-form');
    if (!form) return;
    
    // Generate question HTML
    const html = QUESTIONS.map((q, index) => `
        <div class="slider-container">
            <div class="question-text">${index + 1}. ${q.text}</div>
            <div class="slider-labels">
                <span>Strongly Disagree</span>
                <span>Strongly Agree</span>
            </div>
            <input type="range" id="${q.id}" name="${q.id}" min="0" max="10" value="0">
        </div>
    `).join('');
    
    form.innerHTML = html;
    
    // Add change listeners
    const inputs = form.querySelectorAll('input[type="range"]');
    inputs.forEach(input => {
        input.addEventListener('change', handleQuestionChange);
        input.addEventListener('input', handleQuestionChange);
    });
}

function handleQuestionChange() {
    // Update global state
    const inputs = document.querySelectorAll('#assessment-form input[type="range"]');
    inputs.forEach(input => {
        globalState.responses[input.name] = parseInt(input.value, 10);
    });
    
    // Update progress
    updateProgress();
    
    // Enable submit if all questions answered
    updateSubmitButton();
}

function updateProgress() {
    const inputs = document.querySelectorAll('#assessment-form input[type="range"]');
    const answered = Array.from(inputs).filter(i => i.value > 0).length;
    const total = inputs.length;
    const percentage = (answered / total) * 100;
    
    document.getElementById('progress-fill').style.width = `${percentage}%`;
    document.getElementById('progress-text').textContent = `${answered} / ${total} answered`;
}

function updateSubmitButton() {
    const inputs = document.querySelectorAll('#assessment-form input[type="range"]');
    const allAnswered = Array.from(inputs).every(i => i.value > 0);
    
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = !allAnswered;
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

function validateAge(age) {
    const ageNum = parseInt(age, 10);
    if (!age) return 'Age is required';
    if (isNaN(ageNum)) return 'Age must be a number';
    if (ageNum < 13) return 'Must be at least 13 years old';
    if (ageNum > 120) return 'Please enter a valid age';
    return null;
}

function validateSex(sex) {
    if (!sex) return 'Gender is required';
    if (!['M', 'F', 'O'].includes(sex)) return 'Please select a valid option';
    return null;
}

// ============================================================================
// BUTTON HANDLERS
// ============================================================================

function initializeButtons() {
    const submitBtn = document.getElementById('submit-btn');
    const backBtn = document.getElementById('back-btn');
    
    if (submitBtn) {
        submitBtn.addEventListener('click', handleSubmitAssessment);
    }
    
    if (backBtn) {
        backBtn.addEventListener('click', handleBackToDemographics);
    }
}

function handleBackToDemographics() {
    document.getElementById('questions-section').classList.add('hidden');
    document.getElementById('demographics-section').classList.remove('hidden');
    globalState.currentPage = 'demographics';
    window.scrollTo(0, 0);
}

async function handleSubmitAssessment() {
    const submitBtn = document.getElementById('submit-btn');
    
    if (!globalState.demographics) {
        showToast('Please fill in demographics first', 'error');
        return;
    }
    
    const inputs = document.querySelectorAll('#assessment-form input[type="range"]');
    if (Array.from(inputs).some(i => i.value === '0')) {
        showToast('Please answer all questions', 'error');
        return;
    }
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Submitting...';
        
        showToast('Submitting your assessment...', 'success');
        
        const payload = {
            age: globalState.demographics.age,
            sex: globalState.demographics.sex,
            responses: globalState.responses,
            user_agent: navigator.userAgent,
            timestamp: new Date().toISOString(),
        };
        
        console.log('[SUBMISSION] Payload:', payload);
        
        const response = await fetch(`${window.API_CONFIG.BASE_URL}/api/submit-assessment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Origin': window.location.origin,
            },
            body: JSON.stringify(payload),
            timeout: window.API_CONFIG.TIMEOUT,
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('[SUBMISSION] Success:', result);
        
        showToast('Assessment submitted! Redirecting to results...', 'success');
        
        // Redirect to results
        setTimeout(() => {
            window.location.href = `results.html?id=${result.assessment_id || result.id}`;
        }, 1000);
        
    } catch (error) {
        console.error('[SUBMISSION ERROR]', error);
        showToast(`Error: ${error.message}`, 'error');
        
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Submit Assessment';
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
