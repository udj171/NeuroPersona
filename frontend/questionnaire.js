// ============================================================================
// FRONTEND: questionnaire.js - EFOPA COMPACT PERSONALITY ASSESSMENT
// 30-Item Questionnaire with 0-10 Scale + 5 Validity Check Items
// ============================================================================

// Global state
let globalState = {
  demographics: null,
  responses: {},
  currentPage: 'demographics',
  assessmentId: null,
};

// Questions data - EFOPA Compact Personality Assessment (30 core + 5 validity items)
const QUESTIONS = [
  // DOMAIN R: Sexual and Romantic Relationships (R1-R5)
  { id: 'R1', text: 'When faced with a major life opportunity that would take time away from my partner, I feel torn between both goals because I genuinely value both my career success and my relationship equally.', category: 'R', domain: 'Relationships' },
  { id: 'R2', text: 'Early in dating, I think it\'s better to be honest about how committed I want to be, rather than creating mystery or seeming less interested to maintain attraction.', category: 'R', domain: 'Relationships' },
  { id: 'R3', text: 'When looking for a long-term partner, I notice I become more selective about what I want if I know other attractive people are available.', category: 'R', domain: 'Relationships' },
  { id: 'R4', text: 'Even in a committed relationship, I find it hard to avoid noticing attractive people around me, even though I\'m deeply committed.', category: 'R', domain: 'Relationships' },
  { id: 'R5', text: 'In my relationships, my interest in sex and my emotional connection to my partner tend to move together—either both grow stronger or both weaken.', category: 'R', domain: 'Relationships' },
  
  // DOMAIN S: Confidence and Status (S6-S10)
  { id: 'S6', text: 'When I try something challenging for the first time, I can usually judge how well I\'ll do fairly accurately—I don\'t tend to overestimate or underestimate my abilities.', category: 'S', domain: 'Status' },
  { id: 'S7', text: 'I notice I talk more about my accomplishments and strengths when I\'m speaking with people who seem more successful or important than me.', category: 'S', domain: 'Status' },
  { id: 'S8', text: 'If I\'m in a disagreement with someone at my level, I\'d only make aggressive threats if I genuinely believed I could back them up with my strength or social influence.', category: 'S', domain: 'Status' },
  { id: 'S9', text: 'If I could become more successful without anyone knowing about it, I\'d feel just as good as if everyone praised me for the improvement.', category: 'S', domain: 'Status' },
  { id: 'S10', text: 'When discussing money and finances, which facts I emphasize (salary, savings, investments, home value) depends on which numbers look best compared to the people I\'m talking to.', category: 'S', domain: 'Status' },
  
  // DOMAIN C: Reliability and Follow-Through (C11-C15)
  { id: 'C11', text: 'When I commit to finishing something by a certain date and it turns out to be harder than expected, I work harder to meet the original deadline instead of asking for more time.', category: 'C', domain: 'Reliability' },
  { id: 'C12', text: 'When I look back at my work, people who know me well probably see me as organized and reliable, or maybe even more reliable than I actually am.', category: 'C', domain: 'Reliability' },
  { id: 'C13', text: 'I keep working hard at my tasks even when nobody is watching or evaluating me, which shows that my motivation comes from within rather than from being observed.', category: 'C', domain: 'Reliability' },
  { id: 'C14', text: 'I\'m about equally productive whether my work will be recognized and visible or whether I\'ll get no credit and it will be anonymous.', category: 'C', domain: 'Reliability' },
  { id: 'C15', text: 'If I became a parent, the amount of time and energy I\'d actually spend with my children would match what I\'d say to others about how important parenting is to me.', category: 'C', domain: 'Reliability' },
  
  // DOMAIN A: Helping and Working with Others (A16-A20)
  { id: 'A16', text: 'Whether I\'m helping someone publicly (where others see my good deed) or privately (where nobody knows), I\'m equally motivated to actually help them.', category: 'A', domain: 'Agreeableness' },
  { id: 'A17', text: 'I can tell the difference between feeling real sympathy for someone and being aware of how I might appear to others, and these feelings usually go together for me.', category: 'A', domain: 'Agreeableness' },
  { id: 'A18', text: 'When I\'ve gone against my public values in private moments, I felt genuine guilt about it on my own, without needing anyone else to find out.', category: 'A', domain: 'Agreeableness' },
  { id: 'A19', text: 'In group projects where it\'s hard to track individual effort, I keep the same level of effort whether my teammates are working hard or slacking off.', category: 'A', domain: 'Agreeableness' },
  { id: 'A20', text: 'If I promised to help a group or be part of a team, I\'d stay committed even if a much better personal opportunity came along that would benefit me more.', category: 'A', domain: 'Agreeableness' },
  
  // DOMAIN O: Knowledge and Open-Mindedness (O21-O25)
  { id: 'O21', text: 'When I\'m truly unsure about something in my area of work or expertise, I can say so directly without worrying that it makes me look less knowledgeable.', category: 'O', domain: 'Openness' },
  { id: 'O22', text: 'When someone disagrees with me about something I know well, my first instinct is to argue for my position, and I have to deliberately remind myself to fairly consider their evidence.', category: 'O', domain: 'Openness' },
  { id: 'O23', text: 'Looking back at creative work I\'ve gotten credit for, I\'ve been honest about where the original ideas came from and haven\'t overstated my contribution.', category: 'O', domain: 'Openness' },
  { id: 'O24', text: 'When I solve a complicated problem, I usually test my answer thoroughly by trying different approaches, instead of being confident my first solution is right.', category: 'O', domain: 'Openness' },
  { id: 'O25', text: 'If someone only saw my best creative work without knowing about all my failed attempts and average projects, they\'d get an exaggerated sense of how good and consistent my work really is.', category: 'O', domain: 'Openness' },
  
  // DOMAIN E: Emotional Strength and Recovery (E26-E30)
  { id: 'E26', text: 'It\'s natural for me to act calm and in control on the outside, even when I\'m really feeling anxious or worried on the inside.', category: 'E', domain: 'Emotional' },
  { id: 'E27', text: 'When I handle stress well, it\'s because I genuinely have good self-control, not because I\'m fooling myself about how stressed I actually am.', category: 'E', domain: 'Emotional' },
  { id: 'E28', text: 'When I\'m tempted by something, I can usually predict whether I\'ll resist or give in, and I\'m not often wrong about my self-control ability.', category: 'E', domain: 'Emotional' },
  { id: 'E29', text: 'The people closest to me really understand how much I struggle emotionally because I\'m comfortable talking to them about my weaknesses and fears.', category: 'E', domain: 'Emotional' },
  { id: 'E30', text: 'When I think about how quickly I\'ll bounce back after something difficult happens, my predictions are usually accurate—I don\'t typically overestimate how fast I\'ll recover.', category: 'E', domain: 'Emotional' },
  
  // VALIDITY CHECK ITEMS (V31-V35)
  { id: 'V31', text: 'I find it easy to admit when I make a mistake or when I\'m wrong about something.', category: 'V', domain: 'Validity', isValidity: true },
  { id: 'V32', text: 'I would say I\'m truly humble, not just appearing humble to get social approval.', category: 'V', domain: 'Validity', isValidity: true },
  { id: 'V33', text: 'My behavior and values are pretty much the same whether I\'m with close friends, at work, with family, or meeting new people.', category: 'V', domain: 'Validity', isValidity: true },
  { id: 'V34', text: 'I sometimes have trouble understanding my own reasons for doing things, even when I think about it carefully.', category: 'V', domain: 'Validity', isValidity: true },
  { id: 'V35', text: 'I can remember specific times when I acted selfishly, even though I tell people that being generous is important to me.', category: 'V', domain: 'Validity', isValidity: true },
];

// ============================================================================
// UTILITY: API REQUEST (FIXED CONFIG + LOGGING)
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
    timeout: 30000,
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
        const delay = 1000 * Math.pow(2, attempt);
        console.log(`[API] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw new Error(`API request failed after 3 attempts: ${lastError?.message || 'Unknown error'}`);
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
// QUESTIONNAIRE FORM (RANGE 0-10, SCALE 1-10 DISPLAY)
// ============================================================================

function initializeQuestionnaireForm() {
  const form = document.getElementById('assessment-form');
  if (!form) return;

  console.log('[QUESTIONNAIRE] Generating 35 questions (30 core + 5 validity)...');

  // Build HTML with domain headers and validity section
  let html = '';
  const domains = ['R', 'S', 'C', 'A', 'O', 'E'];
  const domainLabels = {
    R: 'Sexual & Romantic Relationships',
    S: 'Confidence & Status',
    C: 'Reliability & Follow-Through',
    A: 'Helping & Working with Others',
    O: 'Knowledge & Open-Mindedness',
    E: 'Emotional Strength & Recovery'
  };

  domains.forEach(domain => {
    const domainQuestions = QUESTIONS.filter(q => q.category === domain);
    html += `
      <div style="margin-bottom: 40px;">
        <h3 style="color: #134252; font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #208099;">
          ${domain}: ${domainLabels[domain]}
        </h3>
    `;
    
    domainQuestions.forEach((q, index) => {
      html += `
        <div class="question-item" style="margin-bottom: 24px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500;">
            <span style="color: #208099; font-weight: 600;">${q.id}:</span> ${q.text}
          </label>
          <div style="display: flex; align-items: center; gap: 12px;">
            <input 
              type="range" 
              id="${q.id}" 
              name="${q.id}" 
              min="0" 
              max="10" 
              value="0"
              style="flex: 1; cursor: pointer;"
              data-category="${q.category}"
            />
            <span id="${q.id}-value" style="width: 40px; text-align: center; font-weight: 600; color: #208099;">-</span>
          </div>
          <div style="font-size: 12px; color: #5a6c6d; margin-top: 4px;">
            Strongly Disagree (0) ← → Strongly Agree (10)
          </div>
        </div>
      `;
    });
    html += '</div>';
  });

  // Add Validity Check Section
  const validityQuestions = QUESTIONS.filter(q => q.category === 'V');
  html += `
    <div style="margin-bottom: 40px; padding: 16px; background: rgba(32, 128, 153, 0.08); border-radius: 8px; border-left: 4px solid #208099;">
      <h3 style="color: #134252; font-size: 16px; font-weight: 600; margin-bottom: 16px;">
        Validity Check Items
      </h3>
  `;
  
  validityQuestions.forEach((q) => {
    html += `
      <div class="question-item" style="margin-bottom: 20px;">
        <label style="display: block; margin-bottom: 8px; font-weight: 500;">
          <span style="color: #208099; font-weight: 600;">${q.id}:</span> ${q.text}
        </label>
        <div style="display: flex; align-items: center; gap: 12px;">
          <input 
            type="range" 
            id="${q.id}" 
            name="${q.id}" 
            min="0" 
            max="10" 
            value="0"
            style="flex: 1; cursor: pointer;"
            data-category="${q.category}"
            data-validity="true"
          />
          <span id="${q.id}-value" style="width: 40px; text-align: center; font-weight: 600; color: #208099;">-</span>
        </div>
        <div style="font-size: 12px; color: #5a6c6d; margin-top: 4px;">
          Strongly Disagree (0) ← → Strongly Agree (10)
        </div>
      </div>
    `;
  });
  html += '</div>';

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
  const inputs = document.querySelectorAll('input[type="range"]');
  const answeredCount = Array.from(inputs).filter(i => i.value !== '0').length;
  const progressPercent = (answeredCount / inputs.length) * 100;

  const progressBar = document.querySelector('[data-element="progress-bar"]');
  if (progressBar) progressBar.style.width = `${progressPercent}%`;

  const progressText = document.querySelector('[data-element="progress-text"]');
  if (progressText) progressText.textContent = `${answeredCount} / ${inputs.length} answered`;
}

function updateSubmitButton() {
  const inputs = document.querySelectorAll('input[type="range"]');
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
// SUBMIT ASSESSMENT (0-10 SCALE)
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

  const inputs = document.querySelectorAll('input[type="range"]');
  const unanswered = Array.from(inputs).filter(i => i.value === '0');
  
  if (unanswered.length > 0) {
    const answeredCount = inputs.length - unanswered.length;
    showToast(`Please answer all 35 items (${answeredCount}/35)`, 'error', 5000);
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
  const inputs = document.querySelectorAll('input[type="range"]');

  inputs.forEach(input => {
    const value = parseInt(input.value, 10);
    if (value !== 0) {
      responses[input.name] = value;
    }
  });

  console.log('[QUESTIONNAIRE] Gathered responses (all 35 items):', responses);
  return responses;
}
