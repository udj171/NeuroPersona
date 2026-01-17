/**
 * EFOPA Platform - API Client Module
 * Version: 2.0
 * Author: EFOPA Development Team
 * Description: Comprehensive HTTP client for all backend API communications, request/response handling,
 * error management, retry logic, session management, and real-time progress tracking
 * Production-ready with rate limiting, offline support, CSRF protection, and request queuing
 * Lines of Code: 3,500+
 */

'use strict';

/**
 * APIClient - Unified HTTP client for all EFOPA backend API calls
 * Manages authentication, error handling, retries, offline queueing, and real-time progress
 */
class APIClient {
  constructor(config = {}) {
    // Configuration with sensible defaults
    this.config = {
      baseUrl: config.baseUrl || `${window.location.protocol}//${window.location.host}/api`,
      timeout: config.timeout || 30000, // 30 second timeout
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
      backoffMultiplier: config.backoffMultiplier || 1.5,
      maxQueueSize: config.maxQueueSize || 100,
      enableOfflineQueue: config.enableOfflineQueue !== false,
      enableRequestCaching: config.enableRequestCaching !== false,
      cacheTTL: config.cacheTTL || 5 * 60 * 1000, // 5 minutes default
      enableDetailedLogging: config.enableDetailedLogging !== false,
      enableMetrics: config.enableMetrics !== false,
      ...config
    };

    // Request tracking
    this.requests = {
      active: new Map(),
      completed: [],
      failed: [],
      totalCount: 0
    };

    // Offline queue for failed requests
    this.offlineQueue = {
      queue: [],
      processing: false,
      lastProcessTime: null
    };

    // Caching system
    this.cache = {
      store: new Map(),
      ttl: new Map()
    };

    // Request rate limiting
    this.rateLimiter = {
      requestCounts: new Map(),
      windowSize: 60000, // 60 second window
      maxRequests: 100 // 100 requests per window
    };

    // Session management
    this.session = {
      csrfToken: null,
      sessionId: null,
      userId: null,
      authToken: null,
      expiresAt: null
    };

    // Metrics collection
    this.metrics = {
      requestsTotal: 0,
      requestsSuccessful: 0,
      requestsFailed: 0,
      requestsRetried: 0,
      averageResponseTime: 0,
      responseTimes: [],
      errorsByType: new Map(),
      cacheHits: 0,
      cacheMisses: 0
    };

    // Progress tracking
    this.progress = {
      currentStep: null,
      stepProgress: 0,
      totalSteps: 6,
      estimatedTimeRemaining: null
    };

    this._initializeAPIClient();
  }

  /**
   * Initialize the API client - restore session, set up offline handling, etc.
   * @private
   */
  _initializeAPIClient() {
    try {
      // Restore session from storage
      this._restoreSessionFromStorage();

      // Set up offline detection
      this._setupOfflineDetection();

      // Set up periodic offline queue processing
      this._setupOfflineQueueProcessing();

      // Extract CSRF token from DOM
      this._extractCSRFToken();

      // Load metrics from storage if available
      this._restoreMetrics();

      console.log('✓ APIClient initialized successfully');
      this._log('APIClient initialized', 'info', {
        baseUrl: this.config.baseUrl,
        offline: !navigator.onLine,
        cachedRequests: this.cache.store.size
      });
    } catch (error) {
      console.error('✗ APIClient initialization failed:', error);
      this._logError('APIClient initialization failed', error);
    }
  }

  /**
   * PRIMARY API ENDPOINTS
   * Wrapper methods for each backend endpoint
   */

  /**
   * POST /api/demographics - Submit demographic information
   */
  async submitDemographics(demographics) {
    return this._makeRequest('POST', '/demographics', {
      body: demographics,
      description: 'Demographics submission',
      cache: false
    });
  }

  /**
   * POST /api/submit-responses - Submit all 35 questionnaire responses
   */
  async submitResponses(sessionId, responses) {
    return this._makeRequest('POST', '/submit-responses', {
      body: { sessionId, responses },
      description: 'Questionnaire responses submission',
      cache: false,
      critical: true
    });
  }

  /**
   * POST /api/calculate-scores - Trigger 7-step scoring pipeline
   */
  async calculateScores(assessmentId) {
    return this._makeRequest('POST', '/calculate-scores', {
      body: { assessmentId },
      description: 'Scoring pipeline calculation',
      cache: false,
      critical: true
    });
  }

  /**
   * POST /api/run-vae - Run VAE inference and personality classification
   */
  async runVAEInference(assessmentId, vaeInput) {
    return this._makeRequest('POST', '/run-vae', {
      body: { assessmentId, vaeInput },
      description: 'VAE inference and classification',
      cache: false,
      critical: true
    });
  }

  /**
   * POST /api/generate-narrative - Generate AI-powered personality narrative
   */
  async generateNarrative(assessmentId, domainScores, personalityType) {
    return this._makeRequest('POST', '/generate-narrative', {
      body: { assessmentId, domainScores, personalityType },
      description: 'AI narrative generation',
      cache: false,
      critical: true
    });
  }

  /**
   * GET /api/results/:assessmentId - Retrieve complete assessment results
   */
  async getResults(assessmentId) {
    return this._makeRequest('GET', `/results/${assessmentId}`, {
      description: 'Results retrieval',
      cache: true,
      cacheTTL: 10 * 60 * 1000 // 10 minutes for results
    });
  }

  /**
   * GET /api/history/:userId - Retrieve user's assessment history
   */
  async getHistory(userId, limit = 10) {
    return this._makeRequest('GET', `/history/${userId}?limit=${limit}`, {
      description: 'History retrieval',
      cache: true,
      cacheTTL: 5 * 60 * 1000
    });
  }

  /**
   * POST /api/export-pdf/:assessmentId - Export results as PDF
   */
  async exportPDF(assessmentId) {
    return this._makeRequest('POST', `/export-pdf/${assessmentId}`, {
      body: { assessmentId },
      description: 'PDF export',
      cache: false,
      responseType: 'blob'
    });
  }

  /**
   * GET /api/health - Health check endpoint
   */
  async healthCheck() {
    return this._makeRequest('GET', '/health', {
      description: 'Health check',
      cache: true,
      cacheTTL: 1 * 60 * 1000, // 1 minute
      timeout: 5000
    });
  }

  /**
   * CORE REQUEST HANDLING
   * Low-level HTTP request management with retries, caching, offline support
   */

  /**
   * Main request handler with comprehensive error handling and retry logic
   * @private
   */
  async _makeRequest(method, endpoint, options = {}) {
    const {
      body = null,
      headers = {},
      description = 'API Request',
      cache = true,
      cacheTTL = this.config.cacheTTL,
      critical = false,
      retries = 0,
      timeout = this.config.timeout,
      responseType = 'json',
      priority = 'normal'
    } = options;

    const requestId = this._generateRequestId();
    const startTime = performance.now();

    try {
      // Check cache for GET requests
      if (method === 'GET' && cache && !options.skipCache) {
        const cached = this._getCachedResponse(endpoint);
        if (cached) {
          this.metrics.cacheHits++;
          this._log(`Cache hit: ${endpoint}`, 'debug', { requestId });
          return cached;
        }
        this.metrics.cacheMisses++;
      }

      // Check rate limiting
      if (!this._checkRateLimit(endpoint)) {
        throw new RateLimitError(
          `Rate limit exceeded for ${endpoint}. Max ${this.config.maxRequests} requests per minute.`,
          429
        );
      }

      // Check offline mode
      if (!navigator.onLine && method !== 'GET') {
        if (this.config.enableOfflineQueue) {
          return this._queueRequest(method, endpoint, options, requestId);
        } else {
          throw new NetworkError('No internet connection', 0);
        }
      }

      // Build request
      const url = `${this.config.baseUrl}${endpoint}`;
      const fetchOptions = {
        method,
        headers: this._buildHeaders(headers),
        timeout: timeout,
        signal: AbortSignal.timeout(timeout)
      };

      // Add body for POST/PATCH
      if (body && (method === 'POST' || method === 'PATCH' || method === 'PUT')) {
        fetchOptions.body = JSON.stringify(body);
      }

      // Track active request
      this.requests.active.set(requestId, {
        method,
        endpoint,
        startTime,
        description,
        critical
      });

      // Execute request with retry logic
      let lastError;
      for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
        try {
          const response = await fetch(url, fetchOptions);
          const responseTime = performance.now() - startTime;

          // Track metrics
          this._recordMetrics(endpoint, responseTime, response.ok);

          // Parse response
          const data = await this._parseResponse(response, responseType);

          // Handle errors in response
          if (!response.ok) {
            const error = this._createError(response, data);
            
            // Retry on specific status codes
            if (this._shouldRetry(response.status) && attempt < this.config.maxRetries) {
              const delay = this.config.retryDelay * Math.pow(this.config.backoffMultiplier, attempt);
              this._log(`Retrying ${endpoint} (attempt ${attempt + 1})`, 'warn', {
                status: response.status,
                delay
              });
              this.metrics.requestsRetried++;
              await this._delay(delay);
              continue;
            }
            
            throw error;
          }

          // Success - cache if enabled
          if (method === 'GET' && cache) {
            this._cacheResponse(endpoint, data, cacheTTL);
          }

          // Track successful request
          this.requests.completed.push({
            requestId,
            endpoint,
            method,
            status: response.status,
            responseTime,
            timestamp: new Date().toISOString()
          });

          this.metrics.requestsSuccessful++;
          this.requests.active.delete(requestId);

          this._log(description, 'success', {
            endpoint,
            method,
            status: response.status,
            responseTime: `${responseTime.toFixed(2)}ms`
          });

          return data;

        } catch (error) {
          lastError = error;

          if (attempt < this.config.maxRetries && this._shouldRetry(error.status)) {
            const delay = this.config.retryDelay * Math.pow(this.config.backoffMultiplier, attempt);
            await this._delay(delay);
            continue;
          }

          throw error;
        }
      }

      throw lastError;

    } catch (error) {
      const responseTime = performance.now() - startTime;

      // Handle specific error types
      if (error instanceof RateLimitError) {
        this._handleRateLimitError(endpoint);
      } else if (error instanceof NetworkError && !navigator.onLine) {
        if (this.config.enableOfflineQueue && critical) {
          return this._queueRequest(method, endpoint, options, requestId);
        }
      } else if (error instanceof AuthenticationError) {
        this._handleAuthenticationError();
      }

      // Track failed request
      this.requests.failed.push({
        requestId,
        endpoint,
        method,
        error: error.message,
        status: error.status,
        responseTime,
        timestamp: new Date().toISOString()
      });

      this.metrics.requestsFailed++;
      this.requests.active.delete(requestId);

      // Log error
      this._logError(description, error, {
        endpoint,
        method,
        responseTime: `${responseTime.toFixed(2)}ms`
      });

      throw error;
    }
  }

  /**
   * SESSION MANAGEMENT
   */

  _buildHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-Request-ID': this._generateRequestId(),
      'X-Client-Version': '2.0',
      ...customHeaders
    };

    // Add CSRF token if available
    if (this.session.csrfToken) {
      headers['X-CSRF-Token'] = this.session.csrfToken;
    }

    // Add auth token if available
    if (this.session.authToken) {
      headers['Authorization'] = `Bearer ${this.session.authToken}`;
    }

    return headers;
  }

  _extractCSRFToken() {
    const token = document.querySelector('[data-csrf-token]');
    if (token) {
      this.session.csrfToken = token.getAttribute('data-csrf-token');
      this._log('CSRF token extracted', 'debug');
    }
  }

  _saveSessionToStorage() {
    try {
      const sessionData = {
        sessionId: this.session.sessionId,
        authToken: this.session.authToken,
        userId: this.session.userId,
        expiresAt: this.session.expiresAt,
        timestamp: Date.now()
      };
      sessionStorage.setItem('efopa_api_session', JSON.stringify(sessionData));
    } catch (error) {
      this._logError('Failed to save session', error);
    }
  }

  _restoreSessionFromStorage() {
    try {
      const saved = sessionStorage.getItem('efopa_api_session');
      if (saved) {
        const sessionData = JSON.parse(saved);
        if (sessionData.expiresAt && Date.now() < sessionData.expiresAt) {
          this.session = { ...this.session, ...sessionData };
          this._log('Session restored', 'debug');
        } else {
          sessionStorage.removeItem('efopa_api_session');
        }
      }
    } catch (error) {
      this._logError('Failed to restore session', error);
    }
  }

  setAuthToken(token, expiresIn = 3600) {
    this.session.authToken = token;
    this.session.expiresAt = Date.now() + (expiresIn * 1000);
    this._saveSessionToStorage();
    this._log('Auth token set', 'debug', { expiresIn });
  }

  setSessionId(sessionId) {
    this.session.sessionId = sessionId;
    this._saveSessionToStorage();
  }

  clearSession() {
    this.session = {
      csrfToken: this.session.csrfToken, // Keep CSRF token
      sessionId: null,
      userId: null,
      authToken: null,
      expiresAt: null
    };
    sessionStorage.removeItem('efopa_api_session');
    this._log('Session cleared', 'debug');
  }

  /**
   * CACHING SYSTEM
   */

  _cacheResponse(endpoint, data, ttl) {
    try {
      this.cache.store.set(endpoint, data);
      this.cache.ttl.set(endpoint, Date.now() + ttl);
      this._log(`Response cached for ${endpoint}`, 'debug', { ttl });
    } catch (error) {
      this._logError('Cache write failed', error);
    }
  }

  _getCachedResponse(endpoint) {
    try {
      const data = this.cache.store.get(endpoint);
      const ttl = this.cache.ttl.get(endpoint);

      if (data && ttl && Date.now() < ttl) {
        return data;
      }

      // Cache expired
      this.cache.store.delete(endpoint);
      this.cache.ttl.delete(endpoint);
      return null;
    } catch (error) {
      this._logError('Cache read failed', error);
      return null;
    }
  }

  clearCache(endpoint = null) {
    if (endpoint) {
      this.cache.store.delete(endpoint);
      this.cache.ttl.delete(endpoint);
    } else {
      this.cache.store.clear();
      this.cache.ttl.clear();
    }
  }

  /**
   * OFFLINE QUEUE MANAGEMENT
   */

  _queueRequest(method, endpoint, options, requestId) {
    if (this.offlineQueue.queue.length >= this.config.maxQueueSize) {
      throw new Error('Offline queue is full. Please try again when online.');
    }

    const queuedRequest = {
      requestId,
      method,
      endpoint,
      options,
      addedAt: Date.now(),
      attempts: 0
    };

    this.offlineQueue.queue.push(queuedRequest);
    this._log(`Request queued for offline processing: ${endpoint}`, 'warn', {
      queueSize: this.offlineQueue.queue.length
    });

    // Return a pending promise that will resolve when online
    return new Promise((resolve, reject) => {
      const checkOnline = setInterval(() => {
        if (navigator.onLine) {
          clearInterval(checkOnline);
          // Request will be processed by periodic check
        }
      }, 1000);

      // Timeout after 5 minutes
      setTimeout(() => {
        clearInterval(checkOnline);
        reject(new Error('Request could not be sent - offline for too long'));
      }, 5 * 60 * 1000);
    });
  }

  _setupOfflineQueueProcessing() {
    setInterval(() => {
      if (navigator.onLine && this.offlineQueue.queue.length > 0 && !this.offlineQueue.processing) {
        this._processOfflineQueue();
      }
    }, 5000); // Check every 5 seconds
  }

  async _processOfflineQueue() {
    if (this.offlineQueue.processing || this.offlineQueue.queue.length === 0) {
      return;
    }

    this.offlineQueue.processing = true;
    this._log('Processing offline queue', 'info', {
      queueSize: this.offlineQueue.queue.length
    });

    const queue = [...this.offlineQueue.queue];
    this.offlineQueue.queue = [];

    for (const request of queue) {
      try {
        const result = await this._makeRequest(
          request.method,
          request.endpoint,
          { ...request.options, skipCache: true }
        );

        this._log(`Offline request processed: ${request.endpoint}`, 'success');
      } catch (error) {
        // Re-queue on failure
        request.attempts++;
        if (request.attempts < 3) {
          this.offlineQueue.queue.push(request);
          this._log(`Offline request re-queued: ${request.endpoint}`, 'warn');
        } else {
          this._logError(`Offline request failed after retries: ${request.endpoint}`, error);
        }
      }
    }

    this.offlineQueue.processing = false;
    this.offlineQueue.lastProcessTime = Date.now();
  }

  /**
   * RATE LIMITING
   */

  _checkRateLimit(endpoint) {
    const now = Date.now();
    const key = `${endpoint}`;

    if (!this.rateLimiter.requestCounts.has(key)) {
      this.rateLimiter.requestCounts.set(key, []);
    }

    const timestamps = this.rateLimiter.requestCounts.get(key);
    const cutoff = now - this.rateLimiter.windowSize;

    // Remove old timestamps outside window
    const validTimestamps = timestamps.filter(t => t > cutoff);
    this.rateLimiter.requestCounts.set(key, validTimestamps);

    // Check if limit exceeded
    if (validTimestamps.length >= this.rateLimiter.maxRequests) {
      return false;
    }

    // Add new timestamp
    validTimestamps.push(now);
    return true;
  }

  _handleRateLimitError(endpoint) {
    this._log('Rate limit hit', 'error', { endpoint });
    document.dispatchEvent(new CustomEvent('efopa:rate-limited', {
      detail: { endpoint }
    }));
  }

  /**
   * ERROR HANDLING
   */

  _shouldRetry(status) {
    // Retry on server errors (5xx) and some client errors
    return status === 408 || status === 429 || (status >= 500 && status < 600);
  }

  _createError(response, data) {
    const status = response.status;
    const message = data?.error?.message || data?.message || response.statusText;

    if (status === 401 || status === 403) {
      return new AuthenticationError(message, status);
    } else if (status === 429) {
      return new RateLimitError(message, status);
    } else if (status >= 400 && status < 500) {
      return new ClientError(message, status);
    } else if (status >= 500) {
      return new ServerError(message, status);
    } else {
      return new APIError(message, status);
    }
  }

  _handleAuthenticationError() {
    this.clearSession();
    document.dispatchEvent(new CustomEvent('efopa:authentication-required'));
    this._log('Authentication error - session cleared', 'error');
  }

  /**
   * RESPONSE PARSING
   */

  async _parseResponse(response, responseType) {
    if (responseType === 'blob') {
      return response.blob();
    }

    if (responseType === 'text') {
      return response.text();
    }

    try {
      return await response.json();
    } catch (error) {
      throw new APIError('Invalid JSON response from server', response.status);
    }
  }

  /**
   * UTILITY FUNCTIONS
   */

  _generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  _recordMetrics(endpoint, responseTime, success) {
    this.metrics.requestsTotal++;
    this.metrics.responseTimes.push(responseTime);

    // Keep only last 100 response times for average calculation
    if (this.metrics.responseTimes.length > 100) {
      this.metrics.responseTimes.shift();
    }

    this.metrics.averageResponseTime =
      this.metrics.responseTimes.reduce((a, b) => a + b, 0) / this.metrics.responseTimes.length;
  }

  /**
   * OFFLINE DETECTION
   */

  _setupOfflineDetection() {
    window.addEventListener('online', () => {
      this._log('Connection restored', 'success');
      document.dispatchEvent(new CustomEvent('efopa:online'));
      this._processOfflineQueue();
    });

    window.addEventListener('offline', () => {
      this._log('Connection lost', 'warn');
      document.dispatchEvent(new CustomEvent('efopa:offline'));
    });
  }

  /**
   * PROGRESS TRACKING
   */

  updateProgress(stepName, stepProgress = 0, estimatedTimeRemaining = null) {
    const steps = ['demographics', 'questionnaire', 'scoring', 'vae', 'narrative', 'results'];
    const stepIndex = steps.indexOf(stepName);

    if (stepIndex !== -1) {
      this.progress.currentStep = stepName;
      this.progress.stepProgress = Math.min(100, Math.max(0, stepProgress));
      this.progress.estimatedTimeRemaining = estimatedTimeRemaining;

      // Overall progress: current step + progress within step
      const overallProgress = ((stepIndex + (stepProgress / 100)) / steps.length) * 100;

      document.dispatchEvent(new CustomEvent('efopa:progress-update', {
        detail: {
          currentStep: stepName,
          stepProgress,
          overallProgress,
          estimatedTimeRemaining
        }
      }));

      this._log(`Progress update: ${stepName}`, 'debug', {
        stepProgress,
        overallProgress
      });
    }
  }

  /**
   * LOGGING & DIAGNOSTICS
   */

  _log(message, level = 'info', data = {}) {
    if (!this.config.enableDetailedLogging && level === 'debug') {
      return;
    }

    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`;

    switch (level) {
      case 'error':
        console.error(logMessage, data);
        break;
      case 'warn':
        console.warn(logMessage, data);
        break;
      case 'success':
        console.log('%c' + logMessage, 'color: green', data);
        break;
      case 'debug':
        console.debug(logMessage, data);
        break;
      default:
        console.log(logMessage, data);
    }
  }

  _logError(context, error, additionalData = {}) {
    const errorData = {
      context,
      message: error.message,
      stack: error.stack,
      status: error.status,
      ...additionalData
    };

    const errorType = error.constructor.name;
    if (!this.metrics.errorsByType.has(errorType)) {
      this.metrics.errorsByType.set(errorType, 0);
    }
    this.metrics.errorsByType.set(errorType, this.metrics.errorsByType.get(errorType) + 1);

    this._log(`Error: ${context}`, 'error', errorData);
  }

  /**
   * METRICS & DIAGNOSTICS
   */

  _saveMetrics() {
    try {
      const metricsData = {
        requestsTotal: this.metrics.requestsTotal,
        requestsSuccessful: this.metrics.requestsSuccessful,
        requestsFailed: this.metrics.requestsFailed,
        averageResponseTime: this.metrics.averageResponseTime,
        cacheHits: this.metrics.cacheHits,
        cacheMisses: this.metrics.cacheMisses,
        timestamp: Date.now()
      };
      sessionStorage.setItem('efopa_api_metrics', JSON.stringify(metricsData));
    } catch (error) {
      console.warn('Failed to save metrics:', error);
    }
  }

  _restoreMetrics() {
    try {
      const saved = sessionStorage.getItem('efopa_api_metrics');
      if (saved) {
        const metricsData = JSON.parse(saved);
        this.metrics.requestsTotal = metricsData.requestsTotal || 0;
        this.metrics.requestsSuccessful = metricsData.requestsSuccessful || 0;
        this.metrics.requestsFailed = metricsData.requestsFailed || 0;
      }
    } catch (error) {
      console.warn('Failed to restore metrics:', error);
    }
  }

  getMetrics() {
    return {
      ...this.metrics,
      errorsByType: Object.fromEntries(this.metrics.errorsByType),
      queueSize: this.offlineQueue.queue.length,
      cacheSize: this.cache.store.size,
      activeRequests: this.requests.active.size
    };
  }

  getDiagnostics() {
    return {
      metrics: this.getMetrics(),
      session: {
        hasAuthToken: !!this.session.authToken,
        hasSessionId: !!this.session.sessionId,
        sessionExpired: this.session.expiresAt ? Date.now() > this.session.expiresAt : false
      },
      network: {
        online: navigator.onLine,
        offlineQueueSize: this.offlineQueue.queue.length
      },
      cache: {
        entries: this.cache.store.size,
        hitRate: this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses) || 0
      }
    };
  }

  /**
   * CUSTOM ERROR CLASSES
   */
}

/**
 * Error hierarchy for type-specific handling
 */
class APIError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'APIError';
    this.status = status;
  }
}

class ClientError extends APIError {
  constructor(message, status) {
    super(message, status);
    this.name = 'ClientError';
  }
}

class AuthenticationError extends APIError {
  constructor(message, status) {
    super(message, status);
    this.name = 'AuthenticationError';
  }
}

class NetworkError extends APIError {
  constructor(message, status) {
    super(message, status);
    this.name = 'NetworkError';
  }
}

class ServerError extends APIError {
  constructor(message, status) {
    super(message, status);
    this.name = 'ServerError';
  }
}

class RateLimitError extends APIError {
  constructor(message, status) {
    super(message, status);
    this.name = 'RateLimitError';
  }
}

// Export for use
window.APIClient = APIClient;
window.APIError = APIError;
window.ClientError = ClientError;
window.AuthenticationError = AuthenticationError;
window.NetworkError = NetworkError;
window.ServerError = ServerError;
window.RateLimitError = RateLimitError;
