// ============================================================================
// QUESTIONNAIRE PAGE MANAGEMENT
// ============================================================================

// Global state
let globalState = {
  demographics: null,
  responses: {},
  currentPage: 'demographics', // 'demographics' or 'questions'
};

// Add this at the very top of questionnaire.js (before QUESTIONS array)
async function apiRequest(endpoint, options = {}) {
  const baseUrl = window.APICONFIG?.BASE_URL || 
                  (window.location.hostname === 'localhost' 
                    ? 'http://localhost:8000' 
                    : 'https://neuropersona.onrender.com');

  const url = baseUrl + endpoint;
  const defaultOptions = {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,
  };

  const mergedOptions = { ...defaultOptions, ...options };
  
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
    console.error('[API] Request failed:', error);
    throw error;
  }
}


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

async function handleDemographicsSubmit(e) {
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

  // Save demographics locally
  globalState.demographics = {
    age: parseInt(age),
    sex: sex,
  };
  sessionStorage.setItem('demographics', JSON.stringify(globalState.demographics));

  console.log('[QUESTIONNAIRE] Demographics saved:', globalState.demographics);

  // Show loading
  showToast('Starting assessment...', 'success');

  try {
    // Call backend to initialize assessment
    const response = await apiRequest('/api/start-assessment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        age: parseInt(age),
        sex: sex,
      }),
    });

    console.log('[QUESTIONNAIRE] Start assessment response:', response);

    if (response && response.assessment_id) {
      // Store assessment ID for later
      sessionStorage.setItem('assessment_id', response.assessment_id);

      // Show questions section
      document.getElementById('demographics-section').classList.add('hidden');
      document.getElementById('questions-section').classList.remove('hidden');
      globalState.currentPage = 'questions';

      // Scroll to top
      window.scrollTo(0, 0);

      showToast('Assessment started! Answer the questions below.', 'success');
    } else {
      showToast('Error: No assessment ID returned', 'error');
    }

  } catch (error) {
    console.error('[QUESTIONNAIRE] Error starting assessment:', error);
    showToast(`Error: ${error.message}`, 'error');
  }
}

function validateAge(age) {
  if (!age) return 'Age is required';
  if (!isValidAge(age)) {
    return 'Please enter a valid age between 13 and 120';
  }
  return '';
}

function validateSex(sex) {
  if (!sex) return 'Gender is required';
  if (!isValidSex(sex)) {
    return 'Please select a valid option';
  }
  return '';
}

// ============================================================================
// QUESTIONNAIRE FORM
// ============================================================================

function initializeQuestionnaireForm() {
  const form = document.getElementById('assessment-form');
  if (!form) return;

  // Generate question HTML
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
          max="5" 
          value="0"
          style="flex: 1; cursor: pointer;"
          data-category="${q.category}"
        />
        <span id="${q.id}-value" style="width: 30px; text-align: center; font-weight: 600; color: #208099;">-</span>
      </div>
      <div style="font-size: 12px; color: #5a6c6d; margin-top: 4px;">
        Strongly Disagree (1) ← → Strongly Agree (5)
      </div>
    </div>
  `).join('');

  form.innerHTML = html;

  // Add event listeners to range inputs
  form.querySelectorAll('input[type="range"]').forEach(input => {
    input.addEventListener('change', (e) => {
      const value = e.target.value;
      const valueSpan = document.getElementById(`${e.target.id}-value`);
      if (value === '0') {
        valueSpan.textContent = '-';
        valueSpan.style.color = '#999';
      } else {
        valueSpan.textContent = value;
        valueSpan.style.color = '#208099';
      }
      updateProgressBar();
    });

    input.addEventListener('input', (e) => {
      const value = e.target.value;
      const valueSpan = document.getElementById(`${e.target.id}-value`);
      if (value === '0') {
        valueSpan.textContent = '-';
        valueSpan.style.color = '#999';
      } else {
        valueSpan.textContent = value;
        valueSpan.style.color = '#208099';
      }
      updateProgressBar();
    });
  });
}

function updateProgressBar() {
  const inputs = document.querySelectorAll('input[type="range"][name^="q"]');
  const answeredCount = Array.from(inputs).filter(i => i.value !== '0').length;
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

function initializeButtons() {
  // Back button
  const backBtn = document.querySelector('button[data-action="back"]');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      document.getElementById('questions-section').classList.add('hidden');
      document.getElementById('demographics-section').classList.remove('hidden');
      globalState.currentPage = 'demographics';
      window.scrollTo(0, 0);
    });
  }

  // Submit button
  const submitBtn = document.querySelector('button[data-action="submit"]');
  if (submitBtn) {
    submitBtn.addEventListener('click', submitAssessment);
  }
}

// ============================================================================
// SUBMIT ASSESSMENT
// ============================================================================

async function submitAssessment() {
  const demographicsStr = sessionStorage.getItem('demographics');
  const assessmentId = sessionStorage.getItem('assessment_id');

  if (!demographicsStr || !assessmentId) {
    showToast('Please complete demographics first', 'error');
    return;
  }

  const demographics = JSON.parse(demographicsStr);
  const responses = gatherResponses();

  // Check if all questions answered
  if (Object.keys(responses).length !== QUESTIONS.length) {
    const answeredCount = Object.keys(responses).length;
    showToast(`Please answer all questions (${answeredCount}/${QUESTIONS.length})`, 'error');
    return;
  }

  try {
    showToast('Submitting assessment...', 'success');

    // Disable submit button
    const submitBtn = document.querySelector('button[data-action="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Processing...';
    }

    console.log('[QUESTIONNAIRE] Submitting assessment:', {
      assessmentId,
      demographics,
      responses,
    });

    // Submit to backend
    const result = await apiRequest('/api/submit-assessment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        assessment_id: assessmentId,
        age: demographics.age,
        sex: demographics.sex,
        responses: responses,
      }),
    });

    console.log('[QUESTIONNAIRE] Submit response:', result);

    showToast('Assessment submitted! Redirecting to results...', 'success');

    // Redirect to results page after short delay
    setTimeout(() => {
      window.location.href = `results.html?id=${assessmentId}`;
    }, 1500);

  } catch (error) {
    console.error('[QUESTIONNAIRE] Error submitting assessment:', error);
    showToast(`Error: ${error.message}`, 'error');

    // Re-enable submit button
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

  return responses;
}
