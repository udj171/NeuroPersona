// ============================================================================
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

// ============================================================================
// INITIALIZE RESULTS PAGE
// ============================================================================

document.addEventListener('DOMContentLoaded', async function() {
    console.log('[RESULTS] Initializing...');
    
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

// ============================================================================
// FETCH RESULTS
// ============================================================================

async function fetchResults(assessmentId) {
    console.log('[RESULTS] Fetching results for:', assessmentId);
    
    const response = await fetch(`${window.API_CONFIG.BASE_URL}/api/results/${assessmentId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Origin': window.location.origin,
        },
        timeout: window.API_CONFIG.TIMEOUT,
    });
    
    if (!response.ok) {
        throw new Error(`Failed to load results: HTTP ${response.status}`);
    }
    
    const data = await response.json();
    console.log('[RESULTS] Fetched:', data);
    
    return data;
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults(results) {
    console.log('[RESULTS] Displaying results');
    
    // Hide loading, show results
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('results-state').classList.remove('hidden');
    
    const personalityType = results.personality_type || 'Unknown';
    const confidence = results.confidence_score || 0;
    const interpretation = results.interpretation || 'Your assessment has been processed successfully.';
    const domainScores = results.domain_scores || {};
    
    // Update personality type
    document.getElementById('type-letter').textContent = personalityType;
    const typeInfo = PERSONALITY_TYPES[personalityType] || { name: 'Unknown', description: 'Type not found' };
    document.getElementById('type-description').textContent = typeInfo.name;
    
    // Update confidence
    document.getElementById('confidence-fill').style.width = `${confidence * 100}%`;
    document.getElementById('confidence-value').textContent = `${Math.round(confidence * 100)}%`;
    
    // Update interpretation
    document.getElementById('interpretation-text').textContent = interpretation;
    
    // Update domain scores
    displayDomainScores(domainScores);
    
    console.log('[RESULTS] Rendered successfully');
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
    
    const html = domains.map(domain => {
        const score = scores[domain.key] || 0;
        const percentage = (score / 10) * 100;
        
        return `
            <div class="score-item">
                <label>${domain.name}</label>
                <div class="score-bar">
                    <div class="score-fill" style="width: ${percentage}%"></div>
                </div>
                <span class="score-value">${score.toFixed(1)} / 10</span>
            </div>
        `;
    }).join('');
    
    document.getElementById('domain-scores-grid').innerHTML = html;
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

function showError(message) {
    console.error('[RESULTS ERROR]', message);
    
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('error-state').classList.remove('hidden');
    document.getElementById('error-message').textContent = message;
}

// ============================================================================
// ACTIONS
// ============================================================================

function downloadPDF() {
    const assessmentId = getAssessmentIdFromURL();
    showToast('PDF download feature coming soon!', 'warning');
    // Future: Implement PDF generation
}

function shareResults() {
    const assessmentId = getAssessmentIdFromURL();
    const url = `${window.location.origin}/results.html?id=${assessmentId}`;
    
    if (navigator.share) {
        navigator.share({
            title: 'My Personality Assessment Results',
            text: 'Check out my personality assessment results!',
            url: url,
        });
    } else {
        navigator.clipboard.writeText(url);
        showToast('Results link copied to clipboard!', 'success');
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function getAssessmentIdFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id');
}

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
