// Global state
let globalState = {
  demographics: null,
  responses: {},
  currentPage: 'demographics',
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

/**
 * Initialize page on load
 */
document.addEventListener('DOMContentLoaded', function() {
  console.log('[QUESTIONNAIRE] Initializing...');
  console.log('[QUESTIONNAIRE] API Config:', window.API_CONFIG);
  
  initializeDemographicsForm();
  initializeQuestionnaireForm();
  initializeButtons();
  
  console.log('[QUESTIONNAIRE] Ready');
});

/**
 * Initialize demographics form
 */
function initializeDemographicsForm() {
  const form = document.getElementById('demographics-form');
  if (!form) return;
  
  form.addEventListener('submit', handleDemographicsSubmit);
}

/**
 * Handle demographics submission
 */
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
  globalState.demographics = {
    age: parseInt(age),
    sex,
  };
  sessionStorage.setItem('demographics', JSON.stringify(globalState.demographics));
  console.log('[QUESTIONNAIRE] Demographics saved:', globalState.demographics);
  
  // Show questions section
  document.getElementById('demographics-section').classList.add('hidden');
  document.getElementById('questions-section').classList.remove('hidden');
  globalState.currentPage = 'questions';
  
  window.scrollTo(0, 0);
}

/**
 * Initialize questionnaire form
 */
function initializeQuestionnaireForm() {
  const form = document.getElementById('assessment-form');
  if (!form) return;
  
  // Generate question HTML
  const html = QUESTIONS.map((q, index) => `
    <div class="question-item">
      <label for="${q.id}">${index + 1}. ${q.text}</label>
      <input type="range" id="${q.id}" name="${q.id}" min="1" max="5" value="0" class="question-slider">
      <div class="range-labels">
        <span>Strongly Disagree</span>
        <span>Strongly Agree</span>
      </div>
    </div>
  `).join('');
  
  const container = document.getElementById('questions-container');
  if (container) {
    container.innerHTML = html;
    
    // Add event listeners for progress tracking
    document.querySelectorAll('.question-slider').forEach(input => {
      input.addEventListener('input', updateProgressBar);
    });
  }
}

/**
 * Initialize buttons
 */
function initializeButtons() {
  const submitBtn = document.getElementById('submit-btn');
  if (submitBtn) {
    submitBtn.addEventListener('click', submitAssessment);
  }
  
  const backBtn = document.getElementById('back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', goBackToDemographics);
  }
}

/**
 * Update progress bar
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

/**
 * Gather responses from form
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
 * Submit assessment
 */
async function submitAssessment() {
  const demographicsStr = sessionStorage.getItem('demographics');
  if (!demographicsStr) {
    showToast('Please fill in demographics first', 'error');
    return;
  }
  
  const demographics = JSON.parse(demographicsStr);
  const responses = gatherResponses();
  
  // Check if all questions answered
  const unanswered = Object.values(responses).filter(v => v === 0).length;
  if (unanswered > 0) {
    showToast(`Please answer all questions (${unanswered} remaining)`, 'error');
    return;
  }
  
  try {
    showToast('Processing assessment...', 'info');
    
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '⏳ Processing...';
    }
    
    // Submit assessment using centralized API request
    const result = await makeApiRequest('/api/submit-assessment', {
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
    } else {
      throw new Error('No assessment ID returned from server');
    }
    
  } catch (error) {
    showToast(`Submission failed: ${error.message}`, 'error');
    
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Assessment';
    }
  }
}

/**
 * Go back to demographics
 */
function goBackToDemographics() {
  document.getElementById('questions-section').classList.add('hidden');
  document.getElementById('demographics-section').classList.remove('hidden');
  globalState.currentPage = 'demographics';
  window.scrollTo(0, 0);
}
