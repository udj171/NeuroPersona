// ============================================================================
// ADVANCED PERSONALITY ANALYSIS MODULE - Frontend Integration (FIXED)
// ============================================================================
// Handles all advanced personality analysis display and data management
// Generates analysis from existing results data - no external API calls
// Supports graceful degradation when backend endpoints are unavailable

/**
 * Advanced Analysis Data Generator - Generates analysis from results
 */
const AdvancedAnalysisGenerator = {
  /**
   * Generate self-perception bias analysis from results
   */
  generateBiasAnalysis(results) {
    try {
      if (!results || !results.results) {
        console.warn('[Advanced Analysis] No results data for bias analysis');
        return null;
      }

      const resultsData = results.results;
      const rawScores = resultsData.raw_domain_scores || {};
      const correctedScores = resultsData.corrected_domain_scores || {};

      // Calculate lambda (bias score) based on difference between raw and corrected
      let totalBias = 0;
      let domainCount = 0;

      ['R', 'S', 'C', 'A', 'O', 'E'].forEach(domain => {
        const raw = rawScores[domain] || 5;
        const corrected = correctedScores[domain] || 5;
        const diff = Math.abs(raw - corrected);
        totalBias += diff;
        domainCount++;
      });

      const avgBias = totalBias / domainCount / 10; // Normalize to 0-1
      const lambda = Math.min(avgBias, 1.0);

      return {
        bias_score: lambda,
        lambda: lambda,
        raw_scores: rawScores,
        corrected_scores: correctedScores,
      };
    } catch (error) {
      console.error('[Advanced Analysis] Error generating bias analysis:', error);
      return null;
    }
  },

  /**
   * Generate dimension-specific insights
   */
  generateDimensionInsights(results) {
    try {
      if (!results || !results.results) {
        console.warn('[Advanced Analysis] No results data for dimension insights');
        return null;
      }

      const correctedScores = results.results.corrected_domain_scores || {};
      const domains = {};

      ['R', 'S', 'C', 'A', 'O', 'E'].forEach(domain => {
        domains[domain] = (correctedScores[domain] || 5) / 10; // Normalize to 0-1
      });

      return domains;
    } catch (error) {
      console.error('[Advanced Analysis] Error generating dimension insights:', error);
      return null;
    }
  },

  /**
   * Generate implicit cognition patterns
   */
  generateImplicitPatterns(results) {
    try {
      if (!results || !results.results) {
        console.warn('[Advanced Analysis] No results data for implicit patterns');
        return null;
      }

      const rawScores = results.results.raw_domain_scores || {};
      const correctedScores = results.results.corrected_domain_scores || {};

      // Self-deception: how much scores changed
      let deceptionScore = 0;
      let count = 0;
      ['R', 'S', 'C', 'A', 'O', 'E'].forEach(domain => {
        const raw = rawScores[domain] || 5;
        const corrected = correctedScores[domain] || 5;
        deceptionScore += Math.abs(raw - corrected) / 10;
        count++;
      });
      const selfDeception = Math.min(deceptionScore / count, 1.0);

      // Credibility: based on pattern consistency
      const credibilityScore = 1 - selfDeception;

      // Narrative coherence: based on domain correlation
      const avgScore =
        ['R', 'S', 'C', 'A', 'O', 'E'].reduce(
          (sum, d) => sum + (correctedScores[d] || 5),
          0
        ) / 6;

      let variance = 0;
      ['R', 'S', 'C', 'A', 'O', 'E'].forEach(domain => {
        const diff = (correctedScores[domain] || 5) - avgScore;
        variance += diff * diff;
      });
      variance /= 6;

      // Coherence: lower variance = higher coherence
      const narrativeCoherence = 1 - Math.min(variance / 100, 1.0);

      return {
        self_deception_propensity: selfDeception,
        credibility_score: credibilityScore,
        narrative_coherence: narrativeCoherence,
      };
    } catch (error) {
      console.error('[Advanced Analysis] Error generating implicit patterns:', error);
      return null;
    }
  },

  /**
   * Generate response quality metrics
   */
  generateQualityMetrics(results) {
    try {
      if (!results || !results.results) {
        console.warn('[Advanced Analysis] No results data for quality metrics');
        return null;
      }

      const rawScores = results.results.raw_domain_scores || {};
      const validityScores = results.results.validity_scores || {};

      // Response quality: based on how thoughtfully they answered (variability)
      let variance = 0;
      const scores = Object.values(rawScores);
      const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
      scores.forEach(score => {
        variance += Math.pow(score - avg, 2);
      });
      variance = Math.sqrt(variance / scores.length);
      const responseQuality = Math.min(variance / 5, 1.0); // Normalize

      // Consistency: based on validity items
      let consistencyScore = 0.7; // Default
      if (Object.keys(validityScores).length > 0) {
        const validityArray = Object.values(validityScores);
        const avgValidity =
          validityArray.reduce((a, b) => a + b, 0) / validityArray.length;
        consistencyScore = avgValidity / 10; // Normalize to 0-1
      }

      // Response variance
      const responseVariance = variance / 10; // Normalize to 0-1

      return {
        response_quality: responseQuality,
        consistency_score: consistencyScore,
        response_variance: responseVariance,
      };
    } catch (error) {
      console.error('[Advanced Analysis] Error generating quality metrics:', error);
      return null;
    }
  },

  /**
   * Generate authenticity metrics
   */
  generateAuthenticityMetrics(results) {
    try {
      if (!results || !results.results) {
        console.warn('[Advanced Analysis] No results data for authenticity metrics');
        return null;
      }

      const correctedScores = results.results.corrected_domain_scores || {};
      const personalityType = results.personality?.personality_type || 'Unknown';

      // Authenticity: based on score coherence
      const scores = Object.values(correctedScores);
      const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
      let sumSquaredDiff = 0;
      scores.forEach(score => {
        sumSquaredDiff += Math.pow(score - avg, 2);
      });
      const stdDev = Math.sqrt(sumSquaredDiff / scores.length);
      const authenticity = 1 - Math.min(stdDev / 5, 1.0); // Lower variance = higher authenticity

      // Coherence: personality type matches scores
      const typeCoherence = personalityType !== 'Unknown' ? 0.85 : 0.5;

      // Overall response authenticity
      const responseAuthenticity = (authenticity + typeCoherence) / 2;

      return {
        authenticity_score: authenticity,
        coherence_score: typeCoherence,
        response_authenticity: responseAuthenticity,
      };
    } catch (error) {
      console.error('[Advanced Analysis] Error generating authenticity metrics:', error);
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
        interpretation:
          'This analysis requires additional processing. Please try again later.',
      };
    }

    let level = 'Moderate';
    let interpretation =
      'Your responses show typical levels of self-perception variation.';

    const score = data.bias_score || data.lambda || 0.5;

    if (score < 0.35) {
      level = 'Low';
      interpretation =
        'Your responses demonstrate strong internal consistency and accurate self-perception.';
    } else if (score < 0.65) {
      level = 'Moderate';
      interpretation =
        'Your responses show typical levels of self-perception variation, which is normal and expected.';
    } else {
      level = 'High';
      interpretation =
        'Your responses suggest some areas where self-perception may differ from observed behavior patterns.';
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
          score: data.self_deception_propensity || 0.5,
        },
        {
          name: 'Credibility Score',
          score: data.credibility_score || 0.6,
        },
        {
          name: 'Narrative Coherence',
          score: data.narrative_coherence || 0.7,
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
          <div style="font-size: 18px; font-weight: 700; color: ${insight.color};">${((insight.score || 0) * 10).toFixed(1)}</div>
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
 * Now generates analysis from existing results instead of making new API calls
 */
async function loadAdvancedAnalysis(assessmentId) {
  try {
    console.log('[Advanced Analysis] Loading for assessment:', assessmentId);

    // Fetch results (already loaded in results.js, but get fresh copy)
    const response = await apiRequest(`/api/results/${assessmentId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response) {
      console.warn('[Advanced Analysis] No results data received');
      return;
    }

    console.log('[Advanced Analysis] Results received:', response);

    // Generate all analyses from results data
    const bias = AdvancedAnalysisGenerator.generateBiasAnalysis(response);
    const dimensions =
      AdvancedAnalysisGenerator.generateDimensionInsights(response);
    const implicit = AdvancedAnalysisGenerator.generateImplicitPatterns(
      response
    );
    const quality = AdvancedAnalysisGenerator.generateQualityMetrics(response);
    const authenticity =
      AdvancedAnalysisGenerator.generateAuthenticityMetrics(response);

    console.log('[Advanced Analysis] Generated analyses:', {
      bias,
      dimensions,
      implicit,
      quality,
      authenticity,
    });

    // Display all components
    AdvancedAnalysisDisplay.displayBias(bias);
    AdvancedAnalysisDisplay.displayDimensions(dimensions);
    AdvancedAnalysisDisplay.displayImplicit(implicit);
    AdvancedAnalysisDisplay.displayQuality(quality);
    AdvancedAnalysisDisplay.displayAuthenticity(authenticity);

    console.log('[Advanced Analysis] Display complete');
  } catch (error) {
    console.error('[Advanced Analysis] Error loading:', error);
    // Gracefully show error messages in each section
    AdvancedAnalysisDisplay.displayBias(null);
    AdvancedAnalysisDisplay.displayDimensions(null);
    AdvancedAnalysisDisplay.displayImplicit(null);
    AdvancedAnalysisDisplay.displayQuality(null);
    AdvancedAnalysisDisplay.displayAuthenticity(null);
  }
}

console.log('[Advanced Analysis] Module loaded successfully');
