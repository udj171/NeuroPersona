// ============================================================================
// RESULTS PAGE FUNCTIONALITY
// ============================================================================

// API helper - same as questionnaire.js
async function makeApiRequest(endpoint, options = {}) {
    const baseUrl = window.API_CONFIG?.BASE_URL || 'https://neuropersona.onrender.com';
    const url = `${baseUrl}${endpoint}`;
    
    console.log(`[API] ${options.method || 'GET'} ${url}`);
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    const config = {
        method: options.method || 'GET',
        headers: {
            ...defaultHeaders,
            ...(options.headers || {}),
        },
        ...(options.body && { body: options.body }),
    };
    
    try {
        const response = await fetch(url, config);
        
        console.log(`[API] Response status: ${response.status}`);
        
        const contentType = response.headers.get('content-type');
        const isJson = contentType && contentType.includes('application/json');
        const data = isJson ? await response.json() : await response.text();
        
        if (!response.ok) {
            const errorMsg = data.error || data.message || `HTTP ${response.status}`;
            throw new Error(`${response.status}: ${errorMsg}`);
        }
        
        return data;
    } catch (error) {
        console.error(`[API] Error:`, error);
        throw error;
    }
}

// ============================================================================
// PAGE INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[RESULTS] Page initialized');
    loadResults();
});

// ============================================================================
// LOAD AND DISPLAY RESULTS
// ============================================================================

async function loadResults() {
    // Get assessment ID from URL
    const params = new URLSearchParams(window.location.search);
    const assessmentId = params.get('id');
    
    console.log('[RESULTS] Assessment ID:', assessmentId);
    
    if (!assessmentId) {
        displayError('No assessment ID provided. <a href="index.html">Go back home</a>');
        return;
    }
    
    try {
        // Show loading message
        const container = document.getElementById('results-container');
        if (container) {
            container.innerHTML = '<p class="loading">Loading your results...</p>';
        }
        
        // FIXED: Use consistent API call with proper error handling
        const data = await makeApiRequest(`/api/results/${assessmentId}`);
        
        console.log('[RESULTS] Data received:', data);
        displayResults(data);
        
    } catch (error) {
        console.error('[RESULTS] Error loading results:', error);
        displayError(`Failed to load results: ${error.message}<br><br><a href="index.html">Try again</a>`);
    }
}

// ============================================================================
// DISPLAY RESULTS
// ============================================================================

function displayResults(result) {
    const container = document.getElementById('results-container');
    if (!container) return;
    
    const {
        personality_type = 'Unknown',
        confidence_score = 0,
        interpretation = 'Assessment complete',
        dimensions = {},
        recommendations = []
    } = result;
    
    const typeDescription = getPersonalityTypeDescription(personality_type);
    const confidencePercent = (parseFloat(confidence_score) * 100).toFixed(1);
    
    // Build dimensions HTML
    const dimensionsHtml = Object.entries(dimensions).map(([key, value]) => `
        <div class="dimension-item">
            <h4>${key}</h4>
            <div class="dimension-bar">
                <div class="dimension-fill" style="width: ${value * 100}%"></div>
            </div>
            <p class="dimension-value">${(value * 100).toFixed(1)}%</p>
        </div>
    `).join('');
    
    // Build recommendations HTML
    const recommendationsHtml = recommendations.length > 0 
        ? recommendations.map((rec, i) => `<li>${rec}</li>`).join('')
        : '<li>Continue developing your self-awareness through reflection and practice.</li>';
    
    container.innerHTML = `
        <div class="results-card">
            <div class="personality-type-display">
                <div class="type-badge">${personality_type}</div>
                <h2>${typeDescription}</h2>
                <p class="confidence">Confidence: ${confidencePercent}%</p>
            </div>
            
            <div class="interpretation-section">
                <h3>Your Assessment</h3>
                <p>${interpretation}</p>
            </div>
            
            ${dimensionsHtml ? `
                <div class="dimensions-section">
                    <h3>Personality Dimensions</h3>
                    ${dimensionsHtml}
                </div>
            ` : ''}
            
            <div class="recommendations-section">
                <h3>Recommendations</h3>
                <ul>
                    ${recommendationsHtml}
                </ul>
            </div>
            
            <div class="action-buttons">
                <button onclick="window.location.href='index.html'" class="btn btn-primary">
                    Take Assessment Again
                </button>
                <button onclick="shareResults('${personality_type}')" class="btn btn-secondary">
                    Share Results
                </button>
                <button onclick="downloadResults('${personality_type}', '${confidencePercent}')" class="btn btn-secondary">
                    Download PDF
                </button>
            </div>
        </div>
    `;
}

function getPersonalityTypeDescription(type) {
    const descriptions = {
        'A': 'The Analytical - Detail-oriented, logical, and systematic',
        'B': 'The Builder - Practical, goal-focused, and ambitious',
        'C': 'The Connector - Social, empathetic, and relationship-driven',
        'D': 'The Driver - Competitive, confident, and action-oriented',
        'E': 'The Explorer - Creative, curious, and open-minded',
        'F': 'The Facilitator - Collaborative, supportive, and harmony-seeking',
    };
    return descriptions[type] || 'Unknown Personality Type';
}

function displayError(message) {
    const container = document.getElementById('results-container');
    if (container) {
        container.innerHTML = `
            <div class="error-message">
                <h2>Error Loading Results</h2>
                <p>${message}</p>
            </div>
        `;
    }
}

// ============================================================================
// SHARE AND DOWNLOAD
// ============================================================================

function shareResults(type) {
    const url = window.location.href;
    const text = `I just discovered my personality type: ${type}! Check out your personality with this AI-powered assessment.`;
    
    if (navigator.share) {
        navigator.share({
            title: 'My Personality Assessment',
            text: text,
            url: url
        }).catch(err => console.log('Share failed:', err));
    } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(`${text}\n\n${url}`).then(() => {
            alert('Results link copied to clipboard!');
        }).catch(err => console.error('Copy failed:', err));
    }
}

function downloadResults(type, confidence) {
    // Simple text-based download
    const content = `
PERSONALITY ASSESSMENT RESULTS
==============================

Type: ${type}
Confidence: ${confidence}%

Take your assessment at: https://www.predictmypersonality.com

This is a generated results summary from your personality assessment.
    `.trim();
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `personality-results-${type}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
