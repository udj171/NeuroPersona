// ============================================================================
// RESULTS PAGE MANAGEMENT
// ============================================================================

const PERSONALITY_TYPES = {
  'A': { 
    name: 'The Analytical', 
    description: 'Detail-oriented, logical, and systematic thinker',
    color: '#2980b9'
  },
  'B': { 
    name: 'The Builder', 
    description: 'Practical, goal-focused, and ambitious',
    color: '#27ae60'
  },
  'C': { 
    name: 'The Connector', 
    description: 'Social, empathetic, and relationship-driven',
    color: '#e74c3c'
  },
  'D': { 
    name: 'The Driver', 
    description: 'Competitive, confident, and action-oriented',
    color: '#f39c12'
  },
  'E': { 
    name: 'The Explorer', 
    description: 'Creative, curious, and open-minded',
    color: '#9b59b6'
  },
  'F': { 
    name: 'The Facilitator', 
    description: 'Collaborative, supportive, and harmony-seeking',
    color: '#1abc9c'
  },
};

// ============================================================================
// INITIALIZE RESULTS PAGE
// ============================================================================

document.addEventListener('DOMContentLoaded', async function() {
  console.log('[RESULTS] Initializing...');

  const assessmentId = getAssessmentIdFromURL();
  console.log('[RESULTS] Assessment ID:', assessmentId);

  if (!assessmentId) {
    showError('No assessment ID provided. Please start a new assessment.');
    return;
  }

  try {
    console.log('[RESULTS] Fetching results for assessment:', assessmentId);
    const results = await fetchResults(assessmentId);
    console.log('[RESULTS] Received results:', results);
    displayResults(results);
  } catch (error) {
    console.error('[RESULTS] Error:', error);
    showError(error.message);
  }
});

// ============================================================================
// GET ASSESSMENT ID FROM URL
// ============================================================================

function getAssessmentIdFromURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get('id');
}

// ============================================================================
// FETCH RESULTS
// ============================================================================

async function fetchResults(assessmentId) {
  console.log('[RESULTS] Fetching from:', `/api/results/${assessmentId}`);

  const response = await apiRequest(`/api/results/${assessmentId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response) {
    throw new Error('No response from server');
  }

  return response;
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults(results) {
  console.log('[RESULTS] Displaying results:', results);

  // Hide loading, show results
  const loadingState = document.getElementById('loading-state');
  const resultsState = document.getElementById('results-state');

  if (loadingState) loadingState.classList.add('hidden');
  if (resultsState) resultsState.classList.remove('hidden');

  const personalityType = results.personality_type || 'Unknown';
  const confidence = results.confidence_score || 0;
  const interpretation = results.interpretation || 'Your assessment has been processed.';
  const domainScores = results.domain_scores || {};

  // Update personality type
  const typeLetterEl = document.getElementById('type-letter');
  if (typeLetterEl) {
    typeLetterEl.textContent = personalityType;
    typeLetterEl.style.color = PERSONALITY_TYPES[personalityType]?.color || '#208099';
  }

  // Update personality description
  const typeDescEl = document.getElementById('type-description');
  if (typeDescEl) {
    const typeInfo = PERSONALITY_TYPES[personalityType] || { name: 'Unknown', description: 'Type not found' };
    typeDescEl.textContent = typeInfo.name;
  }

  // Update confidence score
  const confidenceFill = document.getElementById('confidence-fill');
  if (confidenceFill) {
    const confidencePercent = confidence * 100;
    confidenceFill.style.width = `${confidencePercent}%`;
  }

  const confidenceValue = document.getElementById('confidence-value');
  if (confidenceValue) {
    confidenceValue.textContent = `${Math.round(confidence * 100)}%`;
  }

  // Update interpretation
  const interpretationText = document.getElementById('interpretation-text');
  if (interpretationText) {
    interpretationText.textContent = interpretation;
  }

  // Display domain scores
  displayDomainScores(domainScores);

  console.log('[RESULTS] Display complete');
}

function displayDomainScores(scores) {
  const domains = [
    { key: 'R', name: 'Resilience' },
    { key: 'S', name: 'Stability' },
    { key: 'C', name: 'Creativity' },
    { key: 'A', name: 'Ambition' },
    { key: 'O', name: 'Openness' },
    { key: 'E', name: 'Empathy' },
  ];

  const scoresContainer = document.getElementById('domain-scores');
  if (!scoresContainer) return;

  scoresContainer.innerHTML = domains.map(domain => {
    const score = scores[domain.key] || 0;
    const percentage = (score / 10) * 100;

    return `
      <div class="domain-score-item" style="margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
          <span style="font-weight: 500; color: #1f3a42;">${domain.name}</span>
          <span style="font-weight: 600; color: #208099;">${score.toFixed(1)}/10</span>
        </div>
        <div style="width: 100%; height: 8px; background-color: #e0e0e0; border-radius: 4px; overflow: hidden;">
          <div 
            style="height: 100%; width: ${percentage}%; background-color: #208099; transition: width 0.3s ease;"
          ></div>
        </div>
      </div>
    `;
  }).join('');
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

function showError(message) {
  console.error('[RESULTS] Error:', message);

  const loadingState = document.getElementById('loading-state');
  const errorState = document.getElementById('error-state');

  if (loadingState) loadingState.classList.add('hidden');
  if (errorState) {
    errorState.classList.remove('hidden');
    const errorMessage = errorState.querySelector('[data-element="error-message"]');
    if (errorMessage) {
      errorMessage.textContent = message;
    }
  }

  showToast(message, 'error', 5000);
}

// ============================================================================
// UTILITIES
// ============================================================================

function retakeAssessment() {
  // Clear session storage
  sessionStorage.removeItem('demographics');
  sessionStorage.removeItem('assessment_id');

  // Redirect to questionnaire
  window.location.href = 'questionnaire.html';
}

function shareResults() {
  const assessmentId = getAssessmentIdFromURL();
  const resultsURL = `${window.location.origin}${window.location.pathname}?id=${assessmentId}`;

  if (navigator.share) {
    navigator.share({
      title: 'My Personality Assessment',
      text: 'Check out my personality assessment results!',
      url: resultsURL,
    });
  } else {
    // Fallback: copy to clipboard
    navigator.clipboard.writeText(resultsURL);
    showToast('Results link copied to clipboard!', 'success');
  }
}