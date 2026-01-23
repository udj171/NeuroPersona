============================================================================
// RESULTS PAGE MANAGEMENT
// ============================================================================

const PERSONALITY_TYPES = {
  'A': { name: 'The Analytical', description: 'Detail-oriented, logical, and systematic thinker' },
  'B': { name: 'The Builder', description: 'Practical, goal-focused, and ambitious' },
  'C': { name: 'The Connector', description: 'Social, empathetic, and relationship-driven' },
  'D': { name: 'The Driver', description: 'Competitive, confident, and action-oriented' },
  'E': { name: 'The Explorer', description: 'Creative, curious, and open-minded' },
  'F': { name: 'The Facilitator', description: 'Collaborative, supportive, and harmony-seeking' },
};

/**
 * Initialize results page
 */
document.addEventListener('DOMContentLoaded', async function() {
  console.log('[RESULTS] Initializing...');
  console.log('[RESULTS] API Config:', window.API_CONFIG);
  
  const assessmentId = getAssessmentIdFromURL();
  if (!assessmentId) {
    showError('No assessment ID found. Please start a new assessment.');
    return;
  }
  
  try {
    const results = await fetchResults(assessmentId);
    displayResults(results);
  } catch (error) {
    console.error('[RESULTS ERROR]', error);
    showError(error.message);
  }
});

/**
 * Fetch results from API
 */
async function fetchResults(assessmentId) {
  console.log('[RESULTS] Fetching results for:', assessmentId);
  
  const data = await makeApiRequest(`/api/results/${assessmentId}`, {
    method: 'GET',
  });
  
  console.log('[RESULTS] Fetched:', data);
  return data;
}

/**
 * Display results on page
 */
function displayResults(results) {
  console.log('[RESULTS] Displaying results');
  
  // Hide loading, show results
  const loadingState = document.getElementById('loading-state');
  const resultsState = document.getElementById('results-state');
  
  if (loadingState) loadingState.classList.add('hidden');
  if (resultsState) resultsState.classList.remove('hidden');
  
  const personalityType = results.personality_type || 'Unknown';
  const confidence = results.confidence_score || 0;
  const interpretation = results.interpretation || 'Your assessment has been processed successfully.';
  const domainScores = results.domain_scores || {};
  
  // Update personality type
  const typeLetterEl = document.getElementById('type-letter');
  if (typeLetterEl) typeLetterEl.textContent = personalityType;
  
  const typeInfo = PERSONALITY_TYPES[personalityType] || { name: 'Unknown', description: 'Type not found' };
  const typeDescEl = document.getElementById('type-description');
  if (typeDescEl) typeDescEl.textContent = typeInfo.name;
  
  // Update confidence
  const confidenceFillEl = document.getElementById('confidence-fill');
  if (confidenceFillEl) {
    confidenceFillEl.style.width = `${confidence * 100}%`;
  }
  
  const confidenceValueEl = document.getElementById('confidence-value');
  if (confidenceValueEl) {
    confidenceValueEl.textContent = `${Math.round(confidence * 100)}%`;
  }
  
  // Update interpretation
  const interpretationEl = document.getElementById('interpretation-text');
  if (interpretationEl) interpretationEl.textContent = interpretation;
  
  // Update domain scores
  displayDomainScores(domainScores);
  
  console.log('[RESULTS] Rendered successfully');
}

/**
 * Display domain scores
 */
function displayDomainScores(scores) {
  const domains = [
    { key: 'R', name: 'Resilience' },
    { key: 'S', name: 'Stability' },
    { key: 'C', name: 'Creativity' },
    { key: 'A', name: 'Ambition' },
    { key: 'O', name: 'Openness' },
    { key: 'E', name: 'Empathy' },
  ];
  
  const html = domains.map(domain => {
    const score = scores[domain.key] || 0;
    const percentage = (score / 10) * 100;
    return `
      <div class="domain-score">
        <div class="domain-label">${domain.name}</div>
        <div class="domain-bar">
          <div class="domain-fill" style="width: ${percentage}%"></div>
        </div>
        <div class="domain-value">${score.toFixed(1)}/10</div>
      </div>
    `;
  }).join('');
  
  const container = document.getElementById('domain-scores-container');
  if (container) {
    container.innerHTML = html;
  }
}
