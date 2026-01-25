// ============================================================================
// EFOPA INTEGRATION MODULE - Frontend Enhancement Layer
// ============================================================================
// This module provides seamless integration with the EFOPA backend enhancement
// Handles Lambda analysis, domain costs, elephant module, validity metrics,
// authenticity analysis, and assessment metadata retrieval

/**
 * EFOPA Service - Handles all EFOPA-specific API calls
 */
const EFOPAService = {
  /**
   * Fetch Lambda Analysis for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Lambda analysis data
   */
  async getLambdaAnalysis(assessmentId) {
    return apiRequest(`/api/efopa/lambda-analysis/${assessmentId}`);
  },

  /**
   * Fetch Domain Costs for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Domain costs data
   */
  async getDomainCosts(assessmentId) {
    return apiRequest(`/api/efopa/domain-costs/${assessmentId}`);
  },

  /**
   * Fetch Elephant Module data for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Elephant module data
   */
  async getElephantModule(assessmentId) {
    return apiRequest(`/api/efopa/elephant-module/${assessmentId}`);
  },

  /**
   * Fetch Validity Metrics for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Validity metrics data
   */
  async getValidityMetrics(assessmentId) {
    return apiRequest(`/api/efopa/validity-metrics/${assessmentId}`);
  },

  /**
   * Fetch Authenticity Metrics for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Authenticity metrics data
   */
  async getAuthenticityMetrics(assessmentId) {
    return apiRequest(`/api/efopa/authenticity-metrics/${assessmentId}`);
  },

  /**
   * Fetch Assessment Metadata for an assessment
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Assessment metadata
   */
  async getAssessmentMetadata(assessmentId) {
    return apiRequest(`/api/efopa/assessment-metadata/${assessmentId}`);
  },

  /**
   * Fetch Complete EFOPA Analysis (all components)
   * This is the primary endpoint - returns all EFOPA data at once
   * @param {string} assessmentId - Assessment ID
   * @returns {Promise<Object>} Complete EFOPA analysis data
   */
  async getCompleteAnalysis(assessmentId) {
    return apiRequest(`/api/efopa/complete-analysis/${assessmentId}`);
  },

  /**
   * Check EFOPA service health
   * @returns {Promise<Object>} Health status
   */
  async getHealth() {
    return apiRequest(`/api/efopa/health`);
  },
};

/**
 * EFOPA Data Formatter - Formats EFOPA data for display
 */
const EFOPAFormatter = {
  /**
   * Format Lambda score for display
   * @param {number} lambda - Lambda value (0-1)
   * @returns {Object} Formatted lambda data with level and interpretation
   */
  formatLambda(lambda) {
    let level = 'Low';
    let levelClass = 'efopa-lambda-low';
    let interpretation = 'Responses align closely with behavioral reality';

    if (lambda < 0.35) {
      level = 'Low';
      levelClass = 'efopa-lambda-low';
      interpretation = 'Your responses show strong internal consistency. You likely provide honest and accurate self-assessments.';
    } else if (lambda < 0.65) {
      level = 'Moderate';
      levelClass = 'efopa-lambda-moderate';
      interpretation = 'Your responses show typical levels of self-perception bias. This is normal and expected in personality assessments.';
    } else {
      level = 'High';
      levelClass = 'efopa-lambda-high';
      interpretation = 'Your responses indicate significant self-deceptive tendencies. Consider how self-perception might differ from actual behavior.';
    }

    return {
      lambda: lambda.toFixed(3),
      level,
      levelClass,
      interpretation,
      percentage: Math.round(lambda * 100),
    };
  },

  /**
   * Format domain costs for display
   * @param {Object} domainCosts - Domain costs object {R, S, C, A, O, E}
   * @returns {Object} Formatted costs with interpretations
   */
  formatDomainCosts(domainCosts) {
    const domains = {
      R: { name: 'Relationships', color: '#e74c3c' },
      S: { name: 'Status', color: '#f39c12' },
      C: { name: 'Conscientiousness', color: '#3498db' },
      A: { name: 'Agreeableness', color: '#2ecc71' },
      O: { name: 'Openness', color: '#9b59b6' },
      E: { name: 'Emotional Stability', color: '#1abc9c' },
    };

    const formatted = {};
    Object.entries(domainCosts).forEach(([key, value]) => {
      if (domains[key]) {
        formatted[key] = {
          name: domains[key].name,
          cost: value.toFixed(3),
          percentage: Math.round(value * 100),
          color: domains[key].color,
          interpretation: EFOPAFormatter.getDeceptionPressureInterpretation(key, value),
        };
      }
    });

    return formatted;
  },

  /**
   * Get interpretation of deception pressure for a domain
   */
  getDeceptionPressureInterpretation(domain, value) {
    const pressures = {
      R: { high: 'Highest evolutionary pressure (reproductive fitness)', threshold: 0.88 },
      S: { high: 'Very high pressure (status and resources)', threshold: 0.82 },
      E: { high: 'High pressure (emotional stability affects partnerships)', threshold: 0.75 },
      C: { high: 'Moderate pressure (affects partnership value)', threshold: 0.68 },
      A: { high: 'Moderate pressure (affects coalition access)', threshold: 0.62 },
      O: { high: 'Moderate-low pressure (affects mate selection)', threshold: 0.58 },
    };

    const pressure = pressures[domain];
    if (!pressure) return 'Unknown domain';

    if (value >= pressure.threshold * 0.9) {
      return pressure.high;
    } else if (value >= pressure.threshold * 0.7) {
      return 'Moderate deception pressure in this domain';
    } else {
      return 'Lower deception pressure in this domain';
    }
  },

  /**
   * Format elephant module data
   * @param {Object} elephantData - Elephant module data
   * @returns {Object} Formatted elephant data
   */
  formatElephant(elephantData) {
    return {
      selfDeceptionPropensity: (elephantData.self_deception_propensity || 0).toFixed(3),
      credibilityScore: (elephantData.credibility_score || 0).toFixed(3),
      narrativeCoherence: (elephantData.narrative_coherence || 0).toFixed(3),
      interpretation: EFOPAFormatter.getElephantInterpretation(elephantData),
    };
  },

  /**
   * Get interpretation of elephant module
   */
  getElephantInterpretation(data) {
    const propensity = data.self_deception_propensity || 0;
    
    if (propensity < 0.3) {
      return 'Your responses show high self-awareness with minimal blind spots.';
    } else if (propensity < 0.6) {
      return 'Your responses indicate typical levels of self-awareness with some blind spots.';
    } else {
      return 'Your responses suggest significant areas where self-perception may diverge from reality.';
    }
  },

  /**
   * Format validity metrics
   * @param {Object} validityData - Validity metrics data
   * @returns {Object} Formatted validity data
   */
  formatValidity(validityData) {
    return {
      responseQuality: (validityData.response_quality || 0).toFixed(3),
      consistencyScore: (validityData.consistency_score || 0).toFixed(3),
      responseVariance: (validityData.response_variance || 0).toFixed(3),
      interpretation: EFOPAFormatter.getValidityInterpretation(validityData),
    };
  },

  /**
   * Get validity interpretation
   */
  getValidityInterpretation(data) {
    const quality = data.response_quality || 0;
    
    if (quality > 0.8) {
      return 'Excellent response quality - thoughtful and considered answers';
    } else if (quality > 0.6) {
      return 'Good response quality - consistent and engaged responses';
    } else {
      return 'Response quality could be improved - consider reviewing your answers';
    }
  },

  /**
   * Format authenticity metrics
   * @param {Object} authData - Authenticity metrics data
   * @returns {Object} Formatted authenticity data
   */
  formatAuthenticity(authData) {
    return {
      authenticityScore: (authData.authenticity_score || 0).toFixed(3),
      coherenceScore: (authData.coherence_score || 0).toFixed(3),
      responseAuthenticity: (authData.response_authenticity || 0).toFixed(3),
      interpretation: EFOPAFormatter.getAuthenticityInterpretation(authData),
    };
  },

  /**
   * Get authenticity interpretation
   */
  getAuthenticityInterpretation(data) {
    const score = data.authenticity_score || 0;
    
    if (score > 0.8) {
      return 'Highly authentic responses reflecting genuine self-perception';
    } else if (score > 0.6) {
      return 'Mostly authentic responses with some narrative construction';
    } else {
      return 'Responses show evidence of narrative construction and strategic presentation';
    }
  },
};

/**
 * EFOPA Display Manager - Manages UI display of EFOPA data
 */
const EFOPADisplay = {
  /**
   * Display Lambda analysis in results
   * @param {Object} lambdaData - Formatted lambda data
   * @param {string} containerId - Container element ID
   */
  displayLambda(lambdaData, containerId = 'efopa-lambda-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const html = `
      <div class="efopa-component" style="background: rgba(230, 126, 34, 0.08); border-left: 4px solid #e67e22; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Deception Susceptibility (Lambda)</h4>
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
          <div style="flex: 1;">
            <div style="font-size: 24px; font-weight: 700; color: #e67e22;">${lambdaData.lambda}</div>
            <div style="font-size: 12px; color: #666; margin-top: 4px;">Susceptibility Score (0-1)</div>
          </div>
          <div style="text-align: center;">
            <div style="font-size: 18px; font-weight: 600; color: #134252;">${lambdaData.level}</div>
            <div style="font-size: 12px; color: #666; margin-top: 4px;">${lambdaData.percentage}%</div>
          </div>
        </div>
        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e0e0e0;">
          <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #333;">${lambdaData.interpretation}</p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * Display domain costs
   * @param {Object} formattedCosts - Formatted domain costs
   * @param {string} containerId - Container element ID
   */
  displayDomainCosts(formattedCosts, containerId = 'efopa-costs-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = `
      <div class="efopa-component" style="background: rgba(52, 152, 219, 0.08); border-left: 4px solid #3498db; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="color: #134252; margin: 0 0 16px 0; font-weight: 600;">Domain-Specific Deception Pressure</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
    `;

    Object.entries(formattedCosts).forEach(([key, cost]) => {
      html += `
        <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
          <div style="font-weight: 600; color: ${cost.color}; margin-bottom: 8px;">${cost.name}</div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
            <div style="font-size: 18px; font-weight: 700; color: ${cost.color};">${cost.cost}</div>
            <div style="font-size: 12px; color: #666;">${cost.percentage}%</div>
          </div>
          <div style="width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden;">
            <div style="height: 100%; width: ${cost.percentage}%; background: ${cost.color}; transition: width 0.3s ease;"></div>
          </div>
          <div style="font-size: 11px; color: #666; margin-top: 8px; line-height: 1.4;">${cost.interpretation}</div>
        </div>
      `;
    });

    html += `
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * Display elephant module
   * @param {Object} elephantData - Formatted elephant data
   * @param {string} containerId - Container element ID
   */
  displayElephant(elephantData, containerId = 'efopa-elephant-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const html = `
      <div class="efopa-component" style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid #9b59b6; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Implicit Cognition Module (Elephant)</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Self-Deception</div>
            <div style="font-size: 20px; font-weight: 700; color: #9b59b6;">${elephantData.selfDeceptionPropensity}</div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Credibility</div>
            <div style="font-size: 20px; font-weight: 700; color: #9b59b6;">${elephantData.credibilityScore}</div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0; text-align: center;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Coherence</div>
            <div style="font-size: 20px; font-weight: 700; color: #9b59b6;">${elephantData.narrativeCoherence}</div>
          </div>
        </div>
        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e0e0e0;">
          <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #333;">${elephantData.interpretation}</p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * Display validity metrics
   * @param {Object} validityData - Formatted validity data
   * @param {string} containerId - Container element ID
   */
  displayValidity(validityData, containerId = 'efopa-validity-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const html = `
      <div class="efopa-component" style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid #2ecc71; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Response Quality & Validity</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Quality Score</div>
            <div style="font-size: 20px; font-weight: 700; color: #2ecc71;">${validityData.responseQuality}</div>
            <div style="width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; margin-top: 8px; overflow: hidden;">
              <div style="height: 100%; width: ${Math.min(parseFloat(validityData.responseQuality) * 100, 100)}%; background: #2ecc71;"></div>
            </div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Consistency</div>
            <div style="font-size: 20px; font-weight: 700; color: #2ecc71;">${validityData.consistencyScore}</div>
            <div style="width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; margin-top: 8px; overflow: hidden;">
              <div style="height: 100%; width: ${Math.min(parseFloat(validityData.consistencyScore) * 100, 100)}%; background: #2ecc71;"></div>
            </div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Variance</div>
            <div style="font-size: 20px; font-weight: 700; color: #2ecc71;">${validityData.responseVariance}</div>
            <div style="width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; margin-top: 8px; overflow: hidden;">
              <div style="height: 100%; width: ${Math.min(parseFloat(validityData.responseVariance) * 100, 100)}%; background: #2ecc71;"></div>
            </div>
          </div>
        </div>
        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e0e0e0;">
          <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #333;">${validityData.interpretation}</p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * Display authenticity metrics
   * @param {Object} authData - Formatted authenticity data
   * @param {string} containerId - Container element ID
   */
  displayAuthenticity(authData, containerId = 'efopa-authenticity-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const html = `
      <div class="efopa-component" style="background: rgba(26, 188, 156, 0.08); border-left: 4px solid #1abc9c; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
        <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Authenticity Analysis</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Authenticity</div>
            <div style="font-size: 20px; font-weight: 700; color: #1abc9c;">${authData.authenticityScore}</div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Coherence</div>
            <div style="font-size: 20px; font-weight: 700; color: #1abc9c;">${authData.coherenceScore}</div>
          </div>
          <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">Overall</div>
            <div style="font-size: 20px; font-weight: 700; color: #1abc9c;">${authData.responseAuthenticity}</div>
          </div>
        </div>
        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e0e0e0;">
          <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #333;">${authData.interpretation}</p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },
};

console.log('[EFOPA Integration] Module loaded successfully');
