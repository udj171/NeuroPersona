// ============================================================================
// FRONTEND: questionnaire.js - COMPLETE UPDATED SCRIPT (Range 1-10)
// ============================================================================

// Global state
let globalState = {
  demographics: null,
  responses: {},
  currentPage: 'demographics',
  assessmentId: null,
  backendReady: false,
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
// UTILITY: API REQUEST (FIXED CONFIG + LOGGING + COLD START HANDLING)
// ============================================================================

async function apiRequest(endpoint, options = {}) {
  const baseURL = window.API_CONFIG?.BASE_URL || 'https://neuropersona.onrender.com';
  const url = `${baseURL}${endpoint}`;

  console.log(`[API] ${options.method || 'GET'} ${url}`);

  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Origin': window.location.origin,
    },
    timeout: 90000,
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
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), mergedOptions.timeout);

      const response = await fetch(url, {
        ...mergedOptions,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      let responseData;
      try {
        responseData = await response.json();
      } catch {
        responseData = { error: response.statusText };
      }

      console.log(`[API] Response ${response.status} from ${endpoint}:`, responseData);

      if (!response.ok) {
        const errorMessage = responseData?.message || responseData?.error || `HTTP ${response.status}`;
        throw new Error(errorMessage);
      }

      return responseData;
    } catch (error) {
      lastError = error;
      console.error(`[API] Attempt ${attempt + 1} failed:`, error.message);
      if (attempt < 2) {
        const delay = 2000 * Math.pow(2, attempt);
        console.log(`[API] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw new Error(`API request failed after 3 attempts: ${lastError?.message || 'Unknown error'}`);
}

// ============================================================================
// WAKE-UP CALL: Silent backend health check on page load
// ============================================================================

async function wakeUpBackend() {
  console.log('[STARTUP] Waking up backend service...');
  try {
    const response = await fetch('https://neuropersona.onrender.com/api/health', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(90000),
    });
    
    if (response.ok) {
      globalState.backendReady = true;
      console.log('[STARTUP] ✓ Backend is awake and ready');
    } else {
      console.warn('[STARTUP] Backend responded but status is not OK:', response.status);
    }
  } catch (error) {
    console.warn('[STARTUP] Backend wake-up call failed (will retry on submit):', error.message);
    globalState.backendReady = false;
  }
}

function showToast(message, type = 'success', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function validateAge(age) {
  if (!age) return 'Age is required';
  const ageNum = parseInt(age, 10);
  if (isNaN(ageNum)) return 'Age must be a number';
  if (ageNum < 13) return 'Must be at least 13 years old';
  if (ageNum > 120) return 'Please enter a valid age';
  return '';
}

function validateSex(sex) {
  if (!sex) return 'Gender is required';
  if (!['M', 'F', 'O'].includes(sex)) {
    return 'Please select a valid option';
  }
  return '';
}

// ============================================================================
// INITIALIZE PAGE
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
  console.log('[QUESTIONNAIRE] Initializing...');
  
  const urlParams = new URLSearchParams(window.location.search);
  const assessmentIdFromUrl = urlParams.get('id');
  
  if (assessmentIdFromUrl) {
    globalState.assessmentId = assessmentIdFromUrl;
    console.log('[QUESTIONNAIRE] Assessment ID from URL:', assessmentIdFromUrl);
  }
  
  initializeDemographicsForm();
  initializeQuestionnaireForm();
  initializeButtons();
  
  // Silent wake-up call for Render free tier cold start
  wakeUpBackend();
  
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

async function handleDemographicsSubmit(e) {
  e.preventDefault();

  const age = document.getElementById('age').value;
  const sex = document.getElementById('sex').value;

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

  document.getElementById('age-error').textContent = '';
  document.getElementById('sex-error').textContent = '';

  globalState.demographics = {
    age: parseInt(age, 10),
    sex: sex,
  };
  sessionStorage.setItem('demographics', JSON.stringify(globalState.demographics));

  console.log('[QUESTIONNAIRE] Demographics saved:', globalState.demographics);

  showToast('Starting assessment...', 'success');

  try {
    const response = await apiRequest('/api/start-assessment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        age: globalState.demographics.age,
        sex: globalState.demographics.sex,
      }),
    });

    console.log('[QUESTIONNAIRE] Start assessment response:', response);

    if (response && response.assessment_id) {
      globalState.assessmentId = response.assessment_id;
      sessionStorage.setItem('assessment_id', response.assessment_id);

      const demoSection = document.getElementById('demographics-section');
      const questionsSection = document.getElementById('questions-section');
      
      if (demoSection) demoSection.style.display = 'none';
      if (questionsSection) questionsSection.style.display = 'block';
      
      globalState.currentPage = 'questions';
      window.scrollTo(0, 0);
      showToast('Assessment started! Answer the questions below.', 'success');
      console.log('[QUESTIONNAIRE] Questions section shown');
    } else {
      showToast('Error: No assessment ID returned', 'error');
      console.error('[QUESTIONNAIRE] No assessment_id in response:', response);
    }

  } catch (error) {
    console.error('[QUESTIONNAIRE] Error starting assessment:', error);
    showToast(`Error: ${error.message}`, 'error');
  }
}

// ============================================================================
// QUESTIONNAIRE FORM (RANGE 1-10)
// ============================================================================

function initializeQuestionnaireForm() {
  const form = document.getElementById('assessment-form');
  if (!form) return;

  console.log('[QUESTIONNAIRE] Generating questions...');

  const html = QUESTIONS.map((q, index) => `
    <div class="question-item" style="margin-bottom: 24px;">
      <label style="display: block; margin-bottom: 8px; font-weight: 500;">
        <span style="color: #208099; font-weight: 600;">Question ${index + 1}:</span> ${q.text}
      </label>
      <div style="display: flex; align-items: center; gap: 12px;">
        <input 
          type="range" 
          id="${q.id}" 
          name="${q.id}" 
          min="1" 
          max="10" 
          value="0"
          style="flex: 1; cursor: pointer;"
          data-category="${q.category}"
        />
        <span id="${q.id}-value" style="width: 30px; text-align: center; font-weight: 600; color: #208099;">-</span>
      </div>
      <div style="font-size: 12px; color: #5a6c6d; margin-top: 4px;">
        Strongly Disagree (1) ← → Strongly Agree (10)
      </div>
    </div>
  `).join('');

  form.innerHTML = html;
  console.log('[QUESTIONNAIRE] Generated 35 questions in form');

  form.querySelectorAll('input[type="range"]').forEach(input => {
    input.addEventListener('change', (e) => {
      updateQuestionValue(e.target);
      globalState.responses[e.target.name] = parseInt(e.target.value, 10);
      updateProgressBar();
      updateSubmitButton();
    });

    input.addEventListener('input', (e) => {
      updateQuestionValue(e.target);
      globalState.responses[e.target.name] = parseInt(e.target.value, 10);
      updateProgressBar();
      updateSubmitButton();
    });
  });

  console.log('[QUESTIONNAIRE] Event listeners attached to', form.querySelectorAll('input[type="range"]').length, 'inputs');
}

function updateQuestionValue(input) {
  const valueSpan = document.getElementById(`${input.id}-value`);
  if (!valueSpan) return;

  const value = input.value;
  if (value === '0') {
    valueSpan.textContent = '-';
    valueSpan.style.color = '#999';
  } else {
    valueSpan.textContent = value;
    valueSpan.style.color = '#208099';
  }
}

function updateProgressBar() {
  const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
  const answeredCount = Array.from(inputs).filter(i => i.value !== '0').length;
  const progressPercent = (answeredCount / inputs.length) * 100;

  const progressBar = document.querySelector('[data-element="progress-bar"]');
  if (progressBar) progressBar.style.width = `${progressPercent}%`;

  const progressText = document.querySelector('[data-element="progress-text"]');
  if (progressText) progressText.textContent = `${answeredCount} / ${inputs.length} answered`;
}

function updateSubmitButton() {
  const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
  const allAnswered = Array.from(inputs).every(i => i.value !== '0');
  
  const submitBtn = document.querySelector('button[data-action="submit"]');
  if (submitBtn) submitBtn.disabled = !allAnswered;
}

function initializeButtons() {
  const backBtn = document.querySelector('button[data-action="back"]');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      const questionsSection = document.getElementById('questions-section');
      const demoSection = document.getElementById('demographics-section');
      
      if (questionsSection) questionsSection.style.display = 'none';
      if (demoSection) demoSection.style.display = 'block';
      
      globalState.currentPage = 'demographics';
      window.scrollTo(0, 0);
      console.log('[QUESTIONNAIRE] Returned to demographics');
    });
  }

  const submitBtn = document.querySelector('button[data-action="submit"]');
  if (submitBtn) submitBtn.addEventListener('click', submitAssessment);
}

// ============================================================================
// SUBMIT ASSESSMENT (RANGE 1-10)
// ============================================================================

async function submitAssessment() {
  console.log('[QUESTIONNAIRE] Submit button clicked');
  
  if (!globalState.assessmentId) {
    showToast('Error: No assessment ID. Please start over.', 'error', 5000);
    return;
  }

  if (!globalState.demographics) {
    showToast('Please fill in demographics first', 'error', 5000);
    return;
  }

  const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
  const unanswered = Array.from(inputs).filter(i => i.value === '0');
  
  if (unanswered.length > 0) {
    const answeredCount = inputs.length - unanswered.length;
    showToast(`Please answer all questions (${answeredCount}/${inputs.length})`, 'error', 5000);
    return;
  }

  try {
    showToast('Submitting assessment...', 'success');
    console.log('[QUESTIONNAIRE] Starting submission...');

    const submitBtn = document.querySelector('button[data-action="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Processing...';
    }

    const responses = gatherResponses();

    console.log('[QUESTIONNAIRE] Submission payload:', {
      assessment_id: globalState.assessmentId,
      age: globalState.demographics.age,
      sex: globalState.demographics.sex,
      responses: responses,
    });

    const result = await apiRequest('/api/submit-assessment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        assessment_id: globalState.assessmentId,
        age: globalState.demographics.age,
        sex: globalState.demographics.sex,
        responses: responses,
      }),
    });

    console.log('[QUESTIONNAIRE] Submit response:', result);

    if (result && (result.success || result.assessment_id)) {
      showToast('Assessment submitted! Redirecting to results...', 'success', 2000);

      setTimeout(() => {
        window.location.href = `results.html?id=${globalState.assessmentId}`;
      }, 2000);
    } else {
      throw new Error(result?.message || result?.error || 'Submit failed: Unknown error');
    }

  } catch (error) {
    console.error('[QUESTIONNAIRE] Error submitting assessment:', error);
    showToast(`Error: ${error.message}`, 'error', 5000);

    const submitBtn = document.querySelector('button[data-action="submit"]');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Assessment';
    }
  }
}

function gatherResponses() {
  const responses = {};
  const inputs = document.querySelectorAll('input[type="range"][name^="q"]');

  inputs.forEach(input => {
    const value = parseInt(input.value, 10);
    if (value !== 0) {
      responses[input.name] = value;
    }
  });

  console.log('[QUESTIONNAIRE] Gathered responses:', responses);
  return responses;
}
