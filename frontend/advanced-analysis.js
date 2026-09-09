// ============================================================================
// ADVANCED ANALYSIS
// ============================================================================
// Every number on these panels is read from the server response. Nothing here
// re-derives a score in the browser: an earlier version approximated these
// panels client-side because the endpoints behind them did not exist, and the
// approximations quietly disagreed with the real scoring.
// ============================================================================

const PANEL_STYLES = {
  correction: { bg: 'rgba(224, 113, 79, 0.08)', border: '#e0714f' },
  contradictions: { bg: 'rgba(230, 126, 34, 0.08)', border: '#e67e22' },
  standing: { bg: 'rgba(0, 144, 176, 0.08)', border: '#0090b0' },
  quality: { bg: 'rgba(46, 204, 113, 0.08)', border: '#2ecc71' },
  novelty: { bg: 'rgba(155, 89, 182, 0.08)', border: '#9b59b6' },
};

const CONTRADICTION_TEXT = {
  agreeableness_without_selfishness:
    'You scored high on agreeableness while saying you cannot recall acting selfishly. '
    + 'Each is plausible; together they describe someone who has never been at odds with themselves.',
  conscientiousness_without_admission:
    'You scored high on conscientiousness while saying you find it hard to admit a mistake. '
    + 'Sustained diligence usually comes with a memory of getting things wrong.',
  stability_without_opacity:
    'You reported unusual calm and complete insight into your own motives. '
    + 'Self-knowledge that total is rarer than either answer alone suggests.',
  openness_without_context_shift:
    'You scored high on openness while reporting that you are identical in every social context. '
    + 'Curiosity and complete consistency across settings rarely travel together.',
};

// ============================================================================
// ENTRY POINT
// ============================================================================

function loadAdvancedAnalysis(data) {
  console.log('[Advanced Analysis] Rendering panels from server data');
  try {
    const results = data.results || {};
    const model = data.model || {};
    const traits = data.traits || {};
    const analysis = results.lambda_analysis || {};

    renderCorrection(results, traits);
    renderContradictions(analysis);
    renderStanding(model, traits);
    renderQuality(analysis);
    renderNovelty(model);

    console.log('[Advanced Analysis] Display complete');
  } catch (error) {
    console.error('[Advanced Analysis] Error rendering panels:', error);
  }
}

// ============================================================================
// PANELS
// ============================================================================

function renderCorrection(results, traits) {
  const lambda = Number(results.lambda_score ?? 0);
  const band = results.lambda_band || 'moderate';
  const biases = results.trait_biases || {};
  const names = traits.names || {};
  const order = traits.order || ['O', 'C', 'E', 'A', 'N'];

  const bandCopy = {
    light: 'Your answers hang together, so the correction barely moved them.',
    moderate: 'There is some tension between your cross-checks and your trait answers.',
    substantial: 'Your answers describe someone more consistent than people usually are, '
      + 'so the correction is doing real work here.',
  }[band] || '';

  const rows = order
    .filter((key) => Math.abs(Number(biases[key] ?? 0)) >= 0.05)
    .map((key) => {
      const shift = Number(biases[key]);
      const direction = shift > 0 ? 'lowered' : 'raised';
      return `<li style="margin-bottom: 4px;">${escapeHtml(names[key] || key)} was
              ${direction} by ${Math.abs(shift).toFixed(1)} points</li>`;
    }).join('');

  panel('advanced-correction-section', 'correction', 'The correction applied', `
    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 10px;">
      <span style="font-size: 26px; font-weight: 700; color: #e0714f;">${lambda.toFixed(2)}</span>
      <span style="font-size: 15px; font-weight: 600; color: #134252; text-transform: capitalize;">${escapeHtml(band)}</span>
      <span style="font-size: 12px; color: #5a6c6d;">on a scale of 0 to 1</span>
    </div>
    <p style="color: #5a6c6d; font-size: 13px; line-height: 1.6; margin: 0 0 10px;">${escapeHtml(bandCopy)}</p>
    ${rows ? `<ul style="color: #5a6c6d; font-size: 13px; margin: 0; padding-left: 18px;">${rows}</ul>`
           : '<p style="color: #5a6c6d; font-size: 13px; margin: 0;">No trait moved by a meaningful amount.</p>'}
  `);
}

function renderContradictions(analysis) {
  const found = Array.isArray(analysis.contradictions) ? analysis.contradictions : [];

  const body = found.length === 0
    ? '<p style="color: #5a6c6d; font-size: 13px; margin: 0; line-height: 1.6;">'
      + 'None found. Your trait answers and your cross-check answers describe the same person.</p>'
    : found.map((item) => `
        <div style="margin-bottom: 12px;">
          <div style="font-size: 13px; font-weight: 600; color: #134252; margin-bottom: 2px;">
            ${escapeHtml(item.trait || '')} · ${escapeHtml(item.item || '')}
            <span style="font-weight: 400; color: #9aa5a6;">(${escapeHtml(item.severity || '')})</span>
          </div>
          <p style="color: #5a6c6d; font-size: 13px; line-height: 1.6; margin: 0;">
            ${escapeHtml(CONTRADICTION_TEXT[item.type] || item.type || '')}
          </p>
        </div>`).join('');

  panel('advanced-contradictions-section', 'contradictions',
    `Answer pairs that rarely hold together (${found.length})`, body);
}

function renderStanding(model, traits) {
  const percentiles = model.percentiles;
  const names = traits.names || {};
  const order = traits.order || ['O', 'C', 'E', 'A', 'N'];

  if (!percentiles) {
    panel('advanced-standing-section', 'standing', 'Where you sit in the reference sample',
      '<p style="color: #5a6c6d; font-size: 13px; margin: 0; line-height: 1.6;">'
      + 'Unavailable until a trained model is installed. Percentiles come from the '
      + 'reference sample the model was trained on.</p>');
    return;
  }

  const rows = order.map((key) => {
    const value = Number(percentiles[key] ?? 0);
    return `
      <div style="margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 3px;">
          <span style="color: #1f3a42;">${escapeHtml(names[key] || key)}</span>
          <span style="color: #0090b0; font-weight: 600;">${value.toFixed(0)}th percentile</span>
        </div>
        <div style="width: 100%; height: 6px; background: #dde3e4; border-radius: 3px;">
          <div style="height: 100%; width: ${value}%; background: #0090b0; border-radius: 3px;"></div>
        </div>
      </div>`;
  }).join('');

  panel('advanced-standing-section', 'standing', 'Where you sit in the reference sample', rows);
}

function renderQuality(analysis) {
  const style = analysis.response_style || {};
  const std = Number(style.std_deviation ?? 0);
  const extreme = Number(style.extreme_fraction ?? 0);
  const midpoint = Number(style.midpoint_fraction ?? 0);
  const penalty = Number(style.penalty ?? 0);

  const notes = [];
  if (std < 0.6) notes.push('Your answers varied very little across 50 statements, which usually means the scale stopped being read.');
  if (extreme > 0.7) notes.push('Most answers sat at one end of the scale or the other.');
  if (midpoint > 0.6) notes.push('Most answers sat on the neutral midpoint.');
  if (notes.length === 0) notes.push('Your answers varied the way an engaged respondent’s usually do.');

  panel('advanced-quality-section', 'quality', 'How you used the scale', `
    <div style="display: flex; gap: 22px; flex-wrap: wrap; margin-bottom: 10px;">
      ${metric('Spread', std.toFixed(2))}
      ${metric('At the extremes', `${Math.round(extreme * 100)}%`)}
      ${metric('On neutral', `${Math.round(midpoint * 100)}%`)}
      ${metric('Style penalty', penalty.toFixed(2))}
    </div>
    <p style="color: #5a6c6d; font-size: 13px; line-height: 1.6; margin: 0;">${escapeHtml(notes.join(' '))}</p>
  `);
}

function renderNovelty(model) {
  if (model.novelty_score === null || model.novelty_score === undefined) {
    panel('advanced-novelty-section', 'novelty', 'How unusual your profile is',
      '<p style="color: #5a6c6d; font-size: 13px; margin: 0; line-height: 1.6;">'
      + 'Unavailable until a trained model is installed.</p>');
    return;
  }

  const novelty = Number(model.novelty_score);
  const label = novelty > 0.66 ? 'Unusual' : novelty > 0.33 ? 'Somewhat unusual' : 'Typical';

  panel('advanced-novelty-section', 'novelty', 'How unusual your profile is', `
    <div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 10px;">
      <span style="font-size: 26px; font-weight: 700; color: #9b59b6;">${novelty.toFixed(2)}</span>
      <span style="font-size: 15px; font-weight: 600; color: #134252;">${label}</span>
    </div>
    <p style="color: #5a6c6d; font-size: 13px; line-height: 1.6; margin: 0;">
      How far your combination of answers sits from the patterns in the reference sample.
      Unusual is neither better nor worse; it means fewer people answered the way you did.
    </p>
  `);
}

// ============================================================================
// HELPERS
// ============================================================================

function metric(label, value) {
  return `
    <div>
      <div style="font-size: 18px; font-weight: 700; color: #134252;">${escapeHtml(value)}</div>
      <div style="font-size: 12px; color: #5a6c6d;">${escapeHtml(label)}</div>
    </div>`;
}

function panel(containerId, styleKey, title, bodyHtml) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.warn(`[Advanced Analysis] Container ${containerId} not found`);
    return;
  }
  const style = PANEL_STYLES[styleKey];
  container.innerHTML = `
    <div style="background: ${style.bg}; border-left: 4px solid ${style.border};
                padding: 16px; border-radius: 8px;">
      <h4 style="color: #134252; margin: 0 0 12px; font-weight: 600;">${escapeHtml(title)}</h4>
      ${bodyHtml}
    </div>`;
}

console.log('[Advanced Analysis] Module loaded');
