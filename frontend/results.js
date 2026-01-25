// ============================================================================
// RESULTS PAGE MANAGEMENT - ENHANCED WITH EFOPA
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

// Global state for EFOPA data
let efopaCacheState = {
  lambdaAnalysis: null,
  domainCosts: null,
  elephantModule: null,
  validityMetrics: null,
  authenticityMetrics: null,
  assessmentMetadata: null,
  isLoaded: false,
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
    
    // Load EFOPA enhancements after main results are displayed
    console.log('[RESULTS] Loading EFOPA enhancements...');
    await loadEFOPAEnhancements(assessmentId);
    
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
// LOAD EFOPA ENHANCEMENTS
// ============================================================================

async function loadEFOPAEnhancements(assessmentId) {
  try {
    console.log('[EFOPA] Loading EFOPA enhancements for:', assessmentId);
    
    // Try to load complete analysis first (if endpoint exists)
    // Falls back to individual endpoints if complete-analysis not available
    try {
      const completeAnalysis = await EFOPAService.getCompleteAnalysis(assessmentId);
      console.log('[EFOPA] Complete analysis loaded:', completeAnalysis);
      
      // Extract and display components
      if (completeAnalysis.lambda_analysis) displayEFOPALambda(completeAnalysis.lambda_analysis);
      if (completeAnalysis.domain_costs) displayEFOPADomainCosts(completeAnalysis.domain_costs);
      if (completeAnalysis.elephant_module) displayEFOPAElephant(completeAnalysis.elephant_module);
      if (completeAnalysis.validity_metrics) displayEFOPAValidity(completeAnalysis.validity_metrics);
      if (completeAnalysis.authenticity_metrics) displayEFOPAAuthenticity(completeAnalysis.authenticity_metrics);
      
      efopaCacheState.isLoaded = true;
      return;
    } catch (completeError) {
      console.log('[EFOPA] Complete analysis not available, loading individual components...');
    }
    
    // Fallback: Load individual endpoints in parallel
    const promises = [
      EFOPAService.getLambdaAnalysis(assessmentId)
        .then(data => { efopaCacheState.lambdaAnalysis = data; displayEFOPALambda(data); })
        .catch(err => console.warn('[EFOPA] Lambda load failed:', err.message)),
      
      EFOPAService.getDomainCosts(assessmentId)
        .then(data => { efopaCacheState.domainCosts = data; displayEFOPADomainCosts(data); })
        .catch(err => console.warn('[EFOPA] Domain costs load failed:', err.message)),
      
      EFOPAService.getElephantModule(assessmentId)
        .then(data => { efopaCacheState.elephantModule = data; displayEFOPAElephant(data); })
        .catch(err => console.warn('[EFOPA] Elephant module load failed:', err.message)),
      
      EFOPAService.getValidityMetrics(assessmentId)
        .then(data => { efopaCacheState.validityMetrics = data; displayEFOPAValidity(data); })
        .catch(err => console.warn('[EFOPA] Validity metrics load failed:', err.message)),
      
      EFOPAService.getAuthenticityMetrics(assessmentId)
        .then(data => { efopaCacheState.authenticityMetrics = data; displayEFOPAAuthenticity(data); })
        .catch(err => console.warn('[EFOPA] Authenticity metrics load failed:', err.message)),
    ];
    
    await Promise.all(promises);
    efopaCacheState.isLoaded = true;
    console.log('[EFOPA] All enhancements loaded');
    
  } catch (error) {
    console.error('[EFOPA] Error loading enhancements:', error);
    // Don't throw - EFOPA is enhancement, not core functionality
  }
}

// ============================================================================
// DISPLAY EFOPA COMPONENTS
// ============================================================================

function displayEFOPALambda(data) {
  if (!data || !data.lambda_score) return;
  
  console.log('[EFOPA] Displaying Lambda analysis...');
  const formatted = EFOPAFormatter.formatLambda(data.lambda_score);
  EFOPADisplay.displayLambda(formatted, 'efopa-lambda-section');
}

function displayEFOPADomainCosts(data) {
  if (!data || !data.domain_costs) return;
  
  console.log('[EFOPA] Displaying domain costs...');
  const formatted = EFOPAFormatter.formatDomainCosts(data.domain_costs);
  EFOPADisplay.displayDomainCosts(formatted, 'efopa-costs-section');
}

function displayEFOPAElephant(data) {
  if (!data) return;
  
  console.log('[EFOPA] Displaying elephant module...');
  const formatted = EFOPAFormatter.formatElephant(data);
  EFOPADisplay.displayElephant(formatted, 'efopa-elephant-section');
}

function displayEFOPAValidity(data) {
  if (!data) return;
  
  console.log('[EFOPA] Displaying validity metrics...');
  const formatted = EFOPAFormatter.formatValidity(data);
  EFOPADisplay.displayValidity(formatted, 'efopa-validity-section');
}

function displayEFOPAAuthenticity(data) {
  if (!data) return;
  
  console.log('[EFOPA] Displaying authenticity metrics...');
  const formatted = EFOPAFormatter.formatAuthenticity(data);
  EFOPADisplay.displayAuthenticity(formatted, 'efopa-authenticity-section');
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults(results) {
  console.log('[RESULTS] Displaying results:', results);

  // Hide loading, show results - USING STYLE DISPLAY NONE
  const loadingState = document.getElementById('loading-state');
  const resultsState = document.getElementById('results-state');

  if (loadingState) {
    loadingState.style.display = 'none';
    console.log('[RESULTS] Hidden loading state');
  }
  
  if (resultsState) {
    resultsState.style.display = 'block';
    console.log('[RESULTS] Showed results state');
  }

  // FIXED: Extract personality from nested structure
  const personalityData = results.personality || {};
  const personalityType = personalityData.personality_type || 'Unknown';
  const confidence = personalityData.confidence_score || 0;
  const interpretation = results.interpretation || 'Your assessment has been processed.';
  
  // FIXED: Extract corrected domain scores from results.results structure
  const resultsData = results.results || {};
  const domainScores = resultsData.corrected_domain_scores || {};

  console.log('[RESULTS] Personality Type:', personalityType);
  console.log('[RESULTS] Confidence:', confidence);
  console.log('[RESULTS] Domain Scores:', domainScores);
  console.log('[RESULTS] Full personality object:', personalityData);

  // Update personality type letter
  const typeLetterEl = document.getElementById('type-letter');
  if (typeLetterEl) {
    typeLetterEl.textContent = personalityType;
    typeLetterEl.style.color = PERSONALITY_TYPES[personalityType]?.color || '#208099';
    console.log('[RESULTS] Updated type letter to:', personalityType);
  } else {
    console.warn('[RESULTS] Element type-letter not found');
  }

  // Update personality type name and description
  const typeNameEl = document.getElementById('type-name');
  const typeDescEl = document.getElementById('type-description');
  
  const typeInfo = PERSONALITY_TYPES[personalityType] || { name: 'Unknown', description: 'Type not found' };
  
  if (typeNameEl) {
    typeNameEl.textContent = typeInfo.name;
    console.log('[RESULTS] Updated type name to:', typeInfo.name);
  } else {
    console.warn('[RESULTS] Element type-name not found');
  }

  if (typeDescEl) {
    typeDescEl.textContent = typeInfo.description;
    console.log('[RESULTS] Updated type description');
  } else {
    console.warn('[RESULTS] Element type-description not found');
  }

  // Update confidence score
  const confidenceFill = document.getElementById('confidence-fill');
  const confidenceValue = document.getElementById('confidence-value');

  if (confidenceFill) {
    const confidencePercent = confidence * 100;
    confidenceFill.style.width = `${confidencePercent}%`;
    console.log('[RESULTS] Updated confidence fill to:', confidencePercent + '%');
  } else {
    console.warn('[RESULTS] Element confidence-fill not found');
  }

  if (confidenceValue) {
    confidenceValue.textContent = `${Math.round(confidence * 100)}`;
    console.log('[RESULTS] Updated confidence value to:', Math.round(confidence * 100) + '%');
  } else {
    console.warn('[RESULTS] Element confidence-value not found');
  }

  // Update interpretation
  const interpretationText = document.getElementById('interpretation-text');
  if (interpretationText) {
    interpretationText.textContent = interpretation;
    console.log('[RESULTS] Updated interpretation');
  } else {
    console.warn('[RESULTS] Element interpretation-text not found');
  }

  // Display domain scores
  displayDomainScores(domainScores);

  console.log('[RESULTS] Display complete');
}

function displayDomainScores(scores) {
  console.log('[RESULTS] displayDomainScores called with:', scores);

  const domains = [
    { key: 'R', name: 'Resilience' },
    { key: 'S', name: 'Stability' },
    { key: 'C', name: 'Creativity' },
    { key: 'A', name: 'Ambition' },
    { key: 'O', name: 'Openness' },
    { key: 'E', name: 'Empathy' },
  ];

  // Use correct element ID
  const scoresContainer = document.getElementById('domain-scores-grid');
  if (!scoresContainer) {
    console.warn('[RESULTS] Element domain-scores-grid not found');
    return;
  }

  // Generate HTML for domain scores
  const html = domains.map(domain => {
    const score = scores[domain.key] || 0;
    const percentage = (score / 10) * 100;

    return `
      <div class="score-item" style="margin-bottom: 16px;">
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

  scoresContainer.innerHTML = html;
  console.log('[RESULTS] Domain scores rendered');
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

function showError(message) {
  console.error('[RESULTS] Error:', message);

  const loadingState = document.getElementById('loading-state');
  const errorState = document.getElementById('error-state');

  if (loadingState) {
    loadingState.style.display = 'none';
  }
  
  if (errorState) {
    errorState.style.display = 'block';
    const errorMessage = errorState.querySelector('#error-message');
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

function downloadPDF() {
  const assessmentId = getAssessmentIdFromURL();
  showToast('PDF download feature coming soon!', 'warning');
}