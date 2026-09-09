// ============================================================================
// FRONTEND: questionnaire.js
// ============================================================================
// The 50 scored items are the public-domain IPIP Big-Five Factor Markers, the
// same 50 the model was trained on. Five cross-checks follow them.
//
// The item bank is NOT hardcoded here. It is fetched from GET /api/questionnaire,
// which serves it straight out of the module the scorer reads, so the wording,
// the item ids and the answer scale cannot drift apart between the two sides.
// ============================================================================

const globalState = {
  demographics: null,
  assessmentId: null,
  bank: null,
  responses: {},
};

// ============================================================================
// INIT
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
  console.log('[QUESTIONNAIRE] Initializing...');

  const form = document.getElementById('demographics-form');
  if (form) form.addEventListener('submit', handleDemographicsSubmit);

  document.querySelectorAll('[data-action="submit"]').forEach((el) =>
    el.addEventListener('click', handleAssessmentSubmit));
  document.querySelectorAll('[data-action="back"]').forEach((el) =>
    el.addEventListener('click', handleBack));

  // Warm the API and pre-load the bank while the demographics form is filled in.
  loadQuestionnaire().catch((error) =>
    console.warn('[QUESTIONNAIRE] Pre-load failed, will retry on submit:', error.message));
});

// ============================================================================
// ITEM BANK
// ============================================================================

async function loadQuestionnaire() {
  if (globalState.bank) return globalState.bank;

  console.log('[QUESTIONNAIRE] Loading item bank...');
  const bank = await apiRequest('/api/questionnaire', { method: 'GET' });

  if (!bank || !Array.isArray(bank.items) || bank.items.length === 0) {
    throw new Error('The questionnaire could not be loaded. Please try again.');
  }

  globalState.bank = bank;
  console.log(`[QUESTIONNAIRE] Loaded ${bank.items.length} items ` +
    `(${bank.counts.scored} scored, ${bank.counts.validity} cross-checks)`);
  return bank;
}

// ============================================================================
// DEMOGRAPHICS
// ============================================================================

async function handleDemographicsSubmit(event) {
  event.preventDefault();

  const ageInput = document.getElementById('age');
  const sexInput = document.getElementById('sex');
  const ageError = document.getElementById('age-error');
  const sexError = document.getElementById('sex-error');

  const age = ageInput ? ageInput.value : '';
  const sex = sexInput ? sexInput.value : '';

  const ageMessage = validateAge(age);
  const sexMessage = validateSex(sex);
  if (ageError) ageError.textContent = ageMessage;
  if (sexError) sexError.textContent = sexMessage;
  if (ageMessage || sexMessage) return;

  const button = event.target.querySelector('button[type="submit"]');
  const original = button ? button.textContent : '';
  if (button) {
    button.disabled = true;
    button.textContent = 'Starting...';
  }

  try {
    await loadQuestionnaire();

    const started = await apiRequest('/api/start-assessment', {
      method: 'POST',
      body: JSON.stringify({ age: parseInt(age, 10), sex }),
    });

    globalState.demographics = { age: parseInt(age, 10), sex };
    globalState.assessmentId = started.assessment_id;
    sessionStorage.setItem('assessment_id', String(started.assessment_id));

    console.log('[QUESTIONNAIRE] Assessment started:', started.assessment_id);
    renderQuestions();
    showQuestionsSection();
  } catch (error) {
    console.error('[QUESTIONNAIRE] Could not start:', error);
    showToast(error.message || 'Could not start the assessment. Please try again.', 'error', 6000);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

function validateAge(age) {
  if (!age) return 'Age is required';
  const value = parseInt(age, 10);
  if (Number.isNaN(value)) return 'Age must be a number';
  if (value < 13) return 'You must be at least 13 years old';
  if (value > 120) return 'Please enter a valid age';
  return '';
}

function validateSex(sex) {
  if (!sex) return 'This field is required';
  if (!['M', 'F', 'O'].includes(sex)) return 'Please select a valid option';
  return '';
}

// ============================================================================
// RENDER
// ============================================================================

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function renderQuestions() {
  const form = document.getElementById('assessment-form');
  if (!form) {
    console.warn('[QUESTIONNAIRE] Element assessment-form not found');
    return;
  }

  const { items, scale } = globalState.bank;
  const values = [];
  for (let v = scale.min; v <= scale.max; v += 1) values.push(v);

  const blocks = [];
  let lastValidity = null;

  items.forEach((item, index) => {
    if (item.validity !== lastValidity) {
      lastValidity = item.validity;
      blocks.push(item.validity ? sectionHeader(
        'A few questions about answering',
        'These five are not scored as traits. They are how the correction is worked out, ' +
        'and they are meant to be a little uncomfortable.'
      ) : sectionHeader(
        'How well does each statement describe you?',
        `There are ${globalState.bank.counts.scored} of these. Answer quickly and honestly ` +
        'rather than carefully; first reactions are the point.'
      ));
    }
    blocks.push(questionBlock(item, index + 1, values, scale));
  });

  form.innerHTML = blocks.join('');

  form.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.addEventListener('change', handleAnswer);
  });

  updateProgress();
  console.log(`[QUESTIONNAIRE] Rendered ${items.length} items`);
}

function sectionHeader(title, blurb) {
  return `
    <div style="margin: 28px 0 18px; padding-bottom: 12px; border-bottom: 2px solid #e0e0e0;">
      <h3 style="color: #134252; margin: 0 0 6px; font-size: 17px;">${escapeHtml(title)}</h3>
      <p style="color: #5a6c6d; font-size: 14px; margin: 0; line-height: 1.6;">${escapeHtml(blurb)}</p>
    </div>`;
}

function questionBlock(item, number, values, scale) {
  const accent = item.validity ? '#e0714f' : '#0090b0';
  const options = values.map((value) => `
    <label style="flex: 1; text-align: center; cursor: pointer; padding: 6px 2px;">
      <input
        type="radio"
        name="${item.id}"
        value="${value}"
        data-item-id="${item.id}"
        style="cursor: pointer; accent-color: ${accent}; width: 18px; height: 18px;"
      />
      <div style="font-size: 11px; color: #5a6c6d; margin-top: 4px;">${value}</div>
    </label>`).join('');

  return `
    <div class="question-block" data-question-id="${item.id}"
         style="padding: 16px 0; border-bottom: 1px solid #f0f0ed;">
      <p style="color: #1f3a42; margin: 0 0 12px; line-height: 1.5;">
        <span style="color: #9aa5a6; font-size: 13px; margin-right: 8px;">${number}</span>
        ${escapeHtml(item.text)}
      </p>
      <div style="display: flex; align-items: flex-start; gap: 4px; max-width: 420px;">
        ${options}
      </div>
      <div style="display: flex; justify-content: space-between; max-width: 420px;
                  font-size: 11px; color: #9aa5a6; margin-top: 2px;">
        <span>${escapeHtml(scale.labels[String(scale.min)])}</span>
        <span>${escapeHtml(scale.labels[String(scale.max)])}</span>
      </div>
    </div>`;
}

function handleAnswer(event) {
  const { itemId } = event.target.dataset;
  globalState.responses[itemId] = parseInt(event.target.value, 10);

  const block = document.querySelector(`[data-question-id="${itemId}"]`);
  if (block) block.style.background = 'transparent';

  updateProgress();
}

function updateProgress() {
  const total = globalState.bank ? globalState.bank.items.length : 0;
  const answered = Object.keys(globalState.responses).length;
  const percent = total ? (answered / total) * 100 : 0;

  const text = document.querySelector('[data-element="progress-text"]');
  const bar = document.querySelector('[data-element="progress-bar"]');
  if (text) text.textContent = `${answered} / ${total} answered`;
  if (bar) bar.style.width = `${percent}%`;
}

function showQuestionsSection() {
  const demographics = document.getElementById('demographics-section');
  const questions = document.getElementById('questions-section');
  if (demographics) demographics.style.display = 'none';
  if (questions) {
    questions.style.display = 'block';
    questions.classList.remove('hidden');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleBack() {
  const demographics = document.getElementById('demographics-section');
  const questions = document.getElementById('questions-section');
  if (questions) questions.style.display = 'none';
  if (demographics) demographics.style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================================================
// SUBMIT
// ============================================================================

async function handleAssessmentSubmit(event) {
  if (event) event.preventDefault();

  const missing = globalState.bank.items
    .filter((item) => globalState.responses[item.id] === undefined)
    .map((item) => item.id);

  if (missing.length > 0) {
    showToast(`${missing.length} question${missing.length === 1 ? '' : 's'} still unanswered.`,
      'warning', 5000);
    highlightMissing(missing);
    return;
  }

  const button = event ? event.target : null;
  const original = button ? button.textContent : '';
  if (button) {
    button.disabled = true;
    button.textContent = 'Scoring...';
  }

  try {
    const assessmentId = globalState.assessmentId
      || parseInt(sessionStorage.getItem('assessment_id'), 10);

    console.log('[QUESTIONNAIRE] Submitting', Object.keys(globalState.responses).length, 'responses');
    await apiRequest('/api/submit-assessment', {
      method: 'POST',
      body: JSON.stringify({
        assessment_id: assessmentId,
        responses: globalState.responses,
      }),
    });

    window.location.href = `results.html?id=${assessmentId}`;
  } catch (error) {
    console.error('[QUESTIONNAIRE] Submit failed:', error);
    showToast(error.message || 'Could not submit your answers. Please try again.', 'error', 6000);
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

function highlightMissing(missing) {
  missing.forEach((itemId) => {
    const block = document.querySelector(`[data-question-id="${itemId}"]`);
    if (block) block.style.background = 'rgba(224, 113, 79, 0.08)';
  });

  const first = document.querySelector(`[data-question-id="${missing[0]}"]`);
  if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
