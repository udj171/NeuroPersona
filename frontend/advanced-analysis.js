// ============================================================================
// ADVANCED PERSONALITY ANALYSIS MODULE - Frontend Integration
// ============================================================================
// Handles all advanced personality analysis display and data management
// Supports graceful degradation when backend endpoints are unavailable

/**
 * Advanced Analysis Service - Handles all API calls for advanced analysis
 */
const AdvancedAnalysisService = {
  /**
   * Fetch self-perception bias analysis
   */
  async getBiasAnalysis(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/bias/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Bias analysis not available:', error.message);
      return null;
    }
  },

  /**
   * Fetch dimension-specific insights
   */
  async getDimensionInsights(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/dimensions/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Dimension insights not available:', error.message);
      return null;
    }
  },

  /**
   * Fetch implicit cognition patterns
   */
  async getImplicitPatterns(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/implicit/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Implicit patterns not available:', error.message);
      return null;
    }
  },

  /**
   * Fetch response quality metrics
   */
  async getQualityMetrics(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/quality/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Quality metrics not available:', error.message);
      return null;
    }
  },

  /**
   * Fetch authenticity assessment
   */
  async getAuthenticityMetrics(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/authenticity/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Authenticity metrics not available:', error.message);
      return null;
    }
  },

  /**
   * Fetch complete analysis (all components at once)
   */
  async getCompleteAnalysis(assessmentId) {
    try {
      return await apiRequest(`/api/analysis/complete/${assessmentId}`);
    } catch (error) {
      console.warn('[Advanced Analysis] Complete analysis not available:', error.message);
      return null;
    }
  },
};

/**
 * Advanced Analysis Formatter - Formats data for display
 */
const AdvancedAnalysisFormatter = {
  /**
   * Format self-perception bias data
   */
  formatBias(data) {
    if (!data) {
      return {
        score: null,
        level: 'Not Available',
        interpretation: 'This analysis requires additional backend processing. Please try again later.',
      };
    }

    let level = 'Moderate';
    let interpretation = 'Your responses show typical levels of self-perception variation.';

    const score = data.bias_score || data.lambda || 0.5;

    if (score < 0.35) {
      level = 'Low';
      interpretation = 'Your responses demonstrate strong internal consistency and accurate self-perception.';
    } else if (score < 0.65) {
      level = 'Moderate';
      interpretation = 'Your responses show typical levels of self-perception variation, which is normal and expected.';
    } else {
      level = 'High';
      interpretation = 'Your responses suggest some areas where self-perception may differ from observed behavior patterns.';
    }

    return {
      score: (score * 100).toFixed(1),
      level,
      interpretation,
    };
  },

  /**
   * Format dimension insights
   */
  formatDimensions(data) {
    if (!data) {
      return {
        insights: [],
        message: 'Dimension analysis data not yet available.',
      };
    }

    const domains = {
      R: { name: 'Relationships', color: '#e74c3c', icon: '💑' },
      S: { name: 'Status', color: '#f39c12', icon: '⭐' },
      C: { name: 'Conscientiousness', color: '#3498db', icon: '⚙️' },
      A: { name: 'Agreeableness', color: '#2ecc71', icon: '🤝' },
      O: { name: 'Openness', color: '#9b59b6', icon: '🔮' },
      E: { name: 'Emotional Stability', color: '#1abc9c', icon: '⚡' },
    };

    const insights = Object.entries(data).map(([key, value]) => {
      const domain = domains[key] || { name: key, color: '#95a5a6', icon: '📊' };
      return {
        key,
        ...domain,
        score: value,
      };
    });

    return { insights, message: null };
  },

  /**
   * Format implicit cognition patterns
   */
  formatImplicit(data) {
    if (!data) {
      return {
        patterns: [],
        message: 'Implicit cognition analysis not yet available.',
      };
    }

    return {
      patterns: [
        {
          name: 'Self-Deception Propensity',
          score: (data.self_deception_propensity || 0.5),
        },
        {
          name: 'Credibility Score',
          score: (data.credibility_score || 0.6),
        },
        {
          name: 'Narrative Coherence',
          score: (data.narrative_coherence || 0.7),
        },
      ],
      message: null,
    };
  },

  /**
   * Format quality metrics
   */
  formatQuality(data) {
    if (!data) {
      return {
        metrics: [
          { name: 'Response Quality', score: null },
          { name: 'Consistency', score: null },
          { name: 'Variance', score: null },
        ],
        message: 'Quality metrics not yet available. Please allow time for analysis.',
      };
    }

    return {
      metrics: [
        { name: 'Response Quality', score: data.response_quality },
        { name: 'Consistency', score: data.consistency_score },
        { name: 'Variance', score: data.response_variance },
      ],
      message: null,
    };
  },

  /**
   * Format authenticity metrics
   */
  formatAuthenticity(data) {
    if (!data) {
      return {
        metrics: [
          { name: 'Authenticity', score: null },
          { name: 'Coherence', score: null },
          { name: 'Overall', score: null },
        ],
        message: 'Authenticity assessment not yet available.',
      };
    }

    return {
      metrics: [
        { name: 'Authenticity', score: data.authenticity_score },
        { name: 'Coherence', score: data.coherence_score },
        { name: 'Overall', score: data.response_authenticity },
      ],
      message: null,
    };
  },
};

/**
 * Advanced Analysis Display Manager - Manages UI display
 */
const AdvancedAnalysisDisplay = {
  /**
   * Display bias analysis
   */
  displayBias(data, containerId = 'advanced-lambda-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const formatted = AdvancedAnalysisFormatter.formatBias(data);

    const html = `
      <div class="analysis-component" style="background: rgba(230, 126, 34, 0.08); border-left: 4px solid #e67e22; padding: 16px; border-radius: 8px;">
        <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Self-Perception Bias Analysis</h4>
        <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 12px;">
          <div style="flex: 1;">
            <div style="font-size: 24px; font-weight: 700; color: #e67e22;">${formatted.score || 'N/A'}</div>
            <div style="font-size: 12px; color: #666; margin-top: 4px;">Bias Score</div>
          </div>
          <div style="text-align: center;">
            <div style="font-size: 18px; font-weight: 600; color: #134252;">${formatted.level}</div>
          </div>
        </div>
        <div style="padding: 12px; background: white; border-radius: 6px; border: 1px solid #e0e0e0;">
          <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #333;">${formatted.interpretation}</p>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  /**
   * Display dimension insights
   */
  displayDimensions(data, containerId = 'advanced-costs-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const formatted = AdvancedAnalysisFormatter.formatDimensions(data);

    if (formatted.message) {
      container.innerHTML = `
        <div style="background: rgba(52, 152, 219, 0.08); border-left: 4px solid #3498db; padding: 16px; border-radius: 8px;">
          <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Dimension-Specific Insights</h4>
          <p style="color: #666; font-size: 13px; margin: 0; line-height: 1.5;">${formatted.message}</p>
        </div>
      `;
      return;
    }

    let html = `
      <div style="background: rgba(52, 152, 219, 0.08); border-left: 4px solid #3498db; padding: 16px; border-radius: 8px;">
        <h4 style="color: #134252; margin: 0 0 16px 0; font-weight: 600;">Dimension-Specific Insights</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
    `;

    formatted.insights.forEach(insight => {
      const percentage = Math.min(insight.score * 100, 100);
      html += `
        <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
          <div style="font-size: 20px; margin-bottom: 4px;">${insight.icon}</div>
          <div style="font-weight: 600; color: ${insight.color}; font-size: 13px; margin-bottom: 8px;">${insight.name}</div>
          <div style="font-size: 18px; font-weight: 700; color: ${insight.color};">${(insight.score || 0).toFixed(2)}</div>
          <div style="width: 100%; height: 4px; background: #e0e0e0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
            <div style="height: 100%; width: ${percentage}%; background: ${insight.color};"></div>
          </div>
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
   * Display implicit patterns
   */
  displayImplicit(data, containerId = 'advanced-elephant-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const formatted = AdvancedAnalysisFormatter.formatImplicit(data);

    if (formatted.message) {
      container.innerHTML = `
        <div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid #9b59b6; padding: 16px; border-radius: 8px;">
          <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Implicit Cognition Patterns</h4>
          <p style="color: #666; font-size: 13px; margin: 0; line-height: 1.5;">${formatted.message}</p>
        </div>
      `;
      return;
    }

    let html = `
      <div style="background: rgba(155, 89, 182, 0.08); border-left: 4px solid #9b59b6; padding: 16px; border-radius: 8px;">
        <h4 style="color: #134252; margin: 0 0 16px 0; font-weight: 600;">Implicit Cognition Patterns</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    `;

    formatted.patterns.forEach(pattern => {
      const percentage = Math.min(pattern.score * 100, 100);
      html += `
        <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
          <div style="font-size: 12px; color: #666; margin-bottom: 8px; font-weight: 500;">${pattern.name}</div>
          <div style="font-size: 20px; font-weight: 700; color: #9b59b6;">${(pattern.score || 0).toFixed(3)}</div>
          <div style="width: 100%; height: 4px; background: #e0e0e0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
            <div style="height: 100%; width: ${percentage}%; background: #9b59b6;"></div>
          </div>
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
   * Display quality metrics
   */
  displayQuality(data, containerId = 'advanced-validity-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const formatted = AdvancedAnalysisFormatter.formatQuality(data);

    if (formatted.message) {
      container.innerHTML = `
        <div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid #2ecc71; padding: 16px; border-radius: 8px;">
          <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Response Quality & Validity</h4>
          <p style="color: #666; font-size: 13px; margin: 0; line-height: 1.5;">${formatted.message}</p>
        </div>
      `;
      return;
    }

    let html = `
      <div style="background: rgba(46, 204, 113, 0.08); border-left: 4px solid #2ecc71; padding: 16px; border-radius: 8px;">
        <h4 style="color: #134252; margin: 0 0 16px 0; font-weight: 600;">Response Quality & Validity</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    `;

    formatted.metrics.forEach(metric => {
      const score = metric.score !== null ? metric.score : 0;
      const percentage = Math.min(score * 100, 100);
      const displayValue = metric.score !== null ? score.toFixed(3) : 'N/A';
      html += `
        <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
          <div style="font-size: 12px; color: #666; margin-bottom: 8px;">${metric.name}</div>
          <div style="font-size: 20px; font-weight: 700; color: #2ecc71;">${displayValue}</div>
          <div style="width: 100%; height: 4px; background: #e0e0e0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
            <div style="height: 100%; width: ${percentage}%; background: #2ecc71;"></div>
          </div>
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
   * Display authenticity metrics
   */
  displayAuthenticity(data, containerId = 'advanced-authenticity-section') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const formatted = AdvancedAnalysisFormatter.formatAuthenticity(data);

    if (formatted.message) {
      container.innerHTML = `
        <div style="background: rgba(26, 188, 156, 0.08); border-left: 4px solid #1abc9c; padding: 16px; border-radius: 8px;">
          <h4 style="color: #134252; margin: 0 0 12px 0; font-weight: 600;">Authenticity Assessment</h4>
          <p style="color: #666; font-size: 13px; margin: 0; line-height: 1.5;">${formatted.message}</p>
        </div>
      `;
      return;
    }

    let html = `
      <div style="background: rgba(26, 188, 156, 0.08); border-left: 4px solid #1abc9c; padding: 16px; border-radius: 8px;">
        <h4 style="color: #134252; margin: 0 0 16px 0; font-weight: 600;">Authenticity Assessment</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    `;

    formatted.metrics.forEach(metric => {
      const score = metric.score !== null ? metric.score : 0;
      const percentage = Math.min(score * 100, 100);
      const displayValue = metric.score !== null ? score.toFixed(3) : 'N/A';
      html += `
        <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
          <div style="font-size: 12px; color: #666; margin-bottom: 8px;">${metric.name}</div>
          <div style="font-size: 20px; font-weight: 700; color: #1abc9c;">${displayValue}</div>
          <div style="width: 100%; height: 4px; background: #e0e0e0; border-radius: 2px; margin-top: 8px; overflow: hidden;">
            <div style="height: 100%; width: ${percentage}%; background: #1abc9c;"></div>
          </div>
        </div>
      `;
    });

    html += `
        </div>
      </div>
    `;

    container.innerHTML = html;
  },
};

/**
 * Load Advanced Analysis - Called from results.js
 */
async function loadAdvancedAnalysis(assessmentId) {
  try {
    console.log('[Advanced Analysis] Loading for assessment:', assessmentId);

    // Load all analyses in parallel
    const [bias, dimensions, implicit, quality, authenticity] = await Promise.all([
      AdvancedAnalysisService.getBiasAnalysis(assessmentId),
      AdvancedAnalysisService.getDimensionInsights(assessmentId),
      AdvancedAnalysisService.getImplicitPatterns(assessmentId),
      AdvancedAnalysisService.getQualityMetrics(assessmentId),
      AdvancedAnalysisService.getAuthenticityMetrics(assessmentId),
    ]);

    // Display all components
    AdvancedAnalysisDisplay.displayBias(bias);
    AdvancedAnalysisDisplay.displayDimensions(dimensions);
    AdvancedAnalysisDisplay.displayImplicit(implicit);
    AdvancedAnalysisDisplay.displayQuality(quality);
    AdvancedAnalysisDisplay.displayAuthenticity(authenticity);

    console.log('[Advanced Analysis] Display complete');
  } catch (error) {
    console.error('[Advanced Analysis] Error loading:', error);
    // Errors are handled gracefully by display functions
  }
}

console.log('[Advanced Analysis] Module loaded successfully');
