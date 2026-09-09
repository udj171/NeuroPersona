// ============================================================================
// RESULTS PAGE
// ============================================================================
// Renders the headline result first, then hands the deeper panels to
// advanced-analysis.js. Everything shown comes from the server; nothing on this
// page recomputes a score.
// ============================================================================

const TRAIT_COLOURS = {
  O: '#0090b0',
  C: '#007a96',
  E: '#16a3c0',
  A: '#0d5f74',
  N: '#5cbdd4',
};

document.addEventListener('DOMContentLoaded', async function () {
  console.log('[RESULTS] Initializing results page...');

  const assessmentId = getAssessmentIdFromURL();
  if (!assessmentId) {
    showError('No assessment id provided. Please start a new assessment.');
    return;
  }

  try {
    const results = await fetchResults(assessmentId);
    console.log('[RESULTS] Results received');
    displayResults(results);
    loadAdvancedAnalysis(results);
  } catch (error) {
    console.error('[RESULTS] Error:', error);
    showError(error.message);
  }
});

function getAssessmentIdFromURL() {
  return new URLSearchParams(window.location.search).get('id');
}

async function fetchResults(assessmentId) {
  const response = await apiRequest(`/api/results/${assessmentId}`, { method: 'GET' });
  if (!response) throw new Error('No response from the server');
  return response;
}

// ============================================================================
// DISPLAY
// ============================================================================

function displayResults(data) {
  const loading = document.getElementById('loading-state');
  const state = document.getElementById('results-state');
  if (loading) loading.style.display = 'none';
  if (state) state.style.display = 'block';

  const personality = data.personality || {};
  const model = data.model || {};
  const results = data.results || {};

  displayHeadline(personality, model);
  displayConfidence(personality, model);
  displayInterpretation(data.interpretation);
  displayTraits(data.traits, results, model);

  console.log('[RESULTS] Display complete');
}

function displayHeadline(personality, model) {
  const letter = document.getElementById('type-letter');
  const name = document.getElementById('type-name');
  const description = document.getElementById('type-description');

  // The old design led with a single letter. The types are learned clusters
  // now, so the name carries the meaning and the letter would be noise.
  if (letter) letter.style.display = 'none';

  if (name) name.textContent = personality.type_name || 'Your profile';

  if (description) {
    if (model.weights_loaded === false) {
      description.textContent =
        'No trained model is installed yet, so this names the trait that stands out '
        + 'rather than matching you to a pattern.';
    } else if (personality.runner_up_name) {
      description.textContent = `Nearest pattern, with ${personality.runner_up_name} next closest.`;
    } else {
      description.textContent = 'Your nearest reference pattern.';
    }
  }
}

function displayConfidence(personality, model) {
  const fill = document.getElementById('confidence-fill');
  const value = document.getElementById('confidence-value');
  const wrapper = document.getElementById('confidence-section');

  const confidence = personality.confidence_score;

  if (confidence === null || confidence === undefined) {
    // Honest absence beats a fabricated number.
    if (wrapper) wrapper.style.display = 'none';
    return;
  }

  if (wrapper) wrapper.style.display = 'block';
  const percent = Math.round(confidence * 100);
  if (fill) fill.style.width = `${percent}%`;
  if (value) value.textContent = String(percent);
}

function displayInterpretation(text) {
  const target = document.getElementById('interpretation-text');
  if (!target) return;

  if (!text) {
    target.textContent = 'No written reading is available for this assessment.';
    return;
  }

  target.innerHTML = String(text)
    .split(/\n\s*\n/)
    .map((paragraph) => `<p style="margin: 0 0 14px;">${escapeHtml(paragraph.trim())}</p>`)
    .join('');
}

function displayTraits(traits, results, model) {
  const container = document.getElementById('trait-scores-grid');
  if (!container) {
    console.warn('[RESULTS] Element trait-scores-grid not found');
    return;
  }

  const order = (traits && traits.order) || ['O', 'C', 'E', 'A', 'N'];
  const names = (traits && traits.names) || {};
  const blurbs = (traits && traits.blurbs) || {};
  const corrected = results.corrected_trait_scores || {};
  const raw = results.raw_trait_scores || {};
  const percentiles = model.percentiles || null;

  container.innerHTML = order.map((key) => {
    const score = Number(corrected[key] ?? 0);
    const original = Number(raw[key] ?? score);
    const moved = Math.abs(score - original) >= 0.5;
    const colour = TRAIT_COLOURS[key] || '#0090b0';

    const percentileNote = percentiles
      ? `<span style="color: #5a6c6d; font-size: 12px;">higher than ${Math.round(percentiles[key])}% of the reference sample</span>`
      : '';

    const rawMarker = moved
      ? `<div title="As answered: ${original.toFixed(1)}"
              style="position: absolute; top: -3px; bottom: -3px; left: ${clamp(original)}%;
                     width: 2px; background: #9aa5a6;"></div>`
      : '';

    return `
      <div style="margin-bottom: 22px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
          <span style="font-weight: 600; color: #1f3a42;">${escapeHtml(names[key] || key)}</span>
          <span style="font-weight: 700; color: ${colour};">${score.toFixed(1)}</span>
        </div>
        <div style="position: relative; width: 100%; height: 10px; background-color: #dde3e4;
                    border-radius: 5px; margin-bottom: 6px;">
          <div style="height: 100%; width: ${clamp(score)}%; background-color: ${colour};
                      border-radius: 5px; transition: width 0.4s ease;"></div>
          ${rawMarker}
        </div>
        <div style="display: flex; justify-content: space-between; gap: 12px; font-size: 12px;">
          <span style="color: #5a6c6d;">${escapeHtml(blurbs[key] || '')}</span>
          ${percentileNote}
        </div>
        ${moved ? `<div style="font-size: 12px; color: #9aa5a6; margin-top: 4px;">
              As answered: ${original.toFixed(1)} · after correction: ${score.toFixed(1)}
            </div>` : ''}
      </div>`;
  }).join('');

  console.log('[RESULTS] Trait scores rendered');
}

// ============================================================================
// HELPERS
// ============================================================================

function clamp(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function showError(message) {
  console.error('[RESULTS] Error:', message);
  const loading = document.getElementById('loading-state');
  const error = document.getElementById('error-state');
  if (loading) loading.style.display = 'none';
  if (error) {
    error.style.display = 'block';
    const target = error.querySelector('#error-message');
    if (target) target.textContent = message;
  }
  showToast(message, 'error', 5000);
}

function retakeAssessment() {
  sessionStorage.removeItem('assessment_id');
  window.location.href = 'questionnaire.html';
}

function shareResults() {
  const assessmentId = getAssessmentIdFromURL();
  const url = `${window.location.origin}${window.location.pathname}?id=${assessmentId}`;

  if (navigator.share) {
    navigator.share({
      title: 'My personality assessment',
      text: 'My results from PredictMyPersonality',
      url,
    }).catch(() => {});
  } else if (navigator.clipboard) {
    navigator.clipboard.writeText(url);
    showToast('Results link copied to clipboard.', 'success');
  }
}
