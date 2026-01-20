/**
 * EFOPA Platform - Form Logic Module
 * Version: 2.0
 * Author: EFOPA Development Team
 * Description: Comprehensive form handling, validation, state management, and user interaction logic
 * 
 * This module provides:
 * - Form validation (client-side and server-side error handling)
 * - State management for form data
 * - Event handling and user interactions
 * - Progress tracking and navigation
 * - Local storage persistence
 * - Accessibility features
 * - Error recovery and retry logic
 * 
 * Dependencies:
 * - api-client.js (for API communication)
 * - DOM elements (HTML structure from index.html, questionnaire.html, results.html)
 * 
 * Module Pattern: Revealing Module Pattern with namespacing
 * Browser Support: ES6+, modern browsers with LocalStorage support
 */

'use strict';

/**
 * EFOPA FormLogic Module
 * Main namespace for all form-related logic
 */
const EFOPAFormLogic = (() => {
  // ============================================
  // PRIVATE CONSTANTS
  // ============================================
  
  const STORAGE_KEYS = {
    REGISTRATION_DATA: 'efopa_registration_data',
    QUESTIONNAIRE_STATE: 'efopa_questionnaire_state',
    RESPONSES: 'efopa_responses',
    ASSESSMENT_ID: 'efopa_assessment_id',
    SESSION_TOKEN: 'efopa_session_token',
    COMPLETION_TIME: 'efopa_completion_time',
  };

  const VALIDATION_RULES = {
    email: {
      pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      message: 'Please enter a valid email address',
      required: true,
    },
    age: {
      min: 18,
      max: 120,
      message: 'Age must be between 18 and 120',
      required: true,
    },
    country: {
      required: true,
      message: 'Please select a country',
    },
    sex: {
      required: true,
      message: 'Please select a gender',
    },
    consent: {
      required: true,
      message: 'You must agree to the terms to continue',
    },
  };

  const RESPONSE_SCALE = {
    MIN: 0,
    MAX: 10,
    MID: 5,
  };

  const QUESTIONNAIRE_CONFIG = {
    TOTAL_QUESTIONS: 35,
    DOMAINS: {
      'R': { name: 'Relationships', count: 5, abbr: 'REL' },
      'S': { name: 'Stability', count: 5, abbr: 'STB' },
      'C': { name: 'Conscientiousness', count: 5, abbr: 'CON' },
      'A': { name: 'Ambition', count: 5, abbr: 'AMB' },
      'O': { name: 'Openness', count: 5, abbr: 'OPN' },
      'E': { name: 'Extraversion', count: 5, abbr: 'EXT' },
      'V': { name: 'Values', count: 5, abbr: 'VAL' },
    },
    ESTIMATED_TIME_MINUTES: 12,
  };

  const ERROR_CODES = {
    VALIDATION_ERROR: 'VALIDATION_ERROR',
    NETWORK_ERROR: 'NETWORK_ERROR',
    SERVER_ERROR: 'SERVER_ERROR',
    MISSING_DATA: 'MISSING_DATA',
    EXPIRED_SESSION: 'EXPIRED_SESSION',
  };

  const EVENT_TYPES = {
    FORM_INITIALIZED: 'efopa:form:initialized',
    FORM_SUBMITTED: 'efopa:form:submitted',
    FORM_VALIDATED: 'efopa:form:validated',
    FORM_ERROR: 'efopa:form:error',
    RESPONSE_RECORDED: 'efopa:response:recorded',
    PROGRESS_UPDATED: 'efopa:progress:updated',
    ASSESSMENT_COMPLETED: 'efopa:assessment:completed',
    DATA_SAVED: 'efopa:data:saved',
    ERROR_RECOVERED: 'efopa:error:recovered',
  };

  // ============================================
  // PRIVATE STATE
  // ============================================

  let formState = {
    currentQuestion: 1,
    responses: {},
    registrationData: {},
    assessmentId: null,
    sessionToken: null,
    isProcessing: false,
    errors: {},
    isDirty: false,
    startTime: null,
    endTime: null,
  };

  let uiState = {
    isInitialized: false,
    isLoading: false,
    currentPanel: 'instruction', // 'instruction', 'question', 'summary'
    showingUnsavedWarning: false,
  };

  // ============================================
  // PRIVATE UTILITY FUNCTIONS
  // ============================================

  /**
   * Emit custom event
   * @param {string} eventType - Event type from EVENT_TYPES
   * @param {object} detail - Event detail data
   */
  function emitEvent(eventType, detail = {}) {
    const event = new CustomEvent(eventType, {
      detail,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);
  }

  /**
   * Log with optional debugging
   * @param {string} message - Log message
   * @param {*} data - Optional data to log
   * @param {string} level - Log level (log, warn, error)
   */
  function log(message, data = null, level = 'log') {
    const timestamp = new Date().toISOString();
    const prefix = `[EFOPA FormLogic ${timestamp}]`;
    
    if (window.__EFOPA_DEBUG__) {
      console[level](prefix, message, data);
    }
  }

  /**
   * Generate unique ID
   * @returns {string}
   */
  function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Safe localStorage operations
   */
  const Storage = {
    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        log('Storage.get error', error, 'warn');
        return defaultValue;
      }
    },

    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        log('Storage.set error', error, 'warn');
        return false;
      }
    },

    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        log('Storage.remove error', error, 'warn');
        return false;
      }
    },

    clear(keys = []) {
      try {
        if (keys.length === 0) {
          localStorage.clear();
        } else {
          keys.forEach(key => localStorage.removeItem(key));
        }
        return true;
      } catch (error) {
        log('Storage.clear error', error, 'warn');
        return false;
      }
    },
  };

  /**
   * Debounce function
   * @param {function} fn - Function to debounce
   * @param {number} delay - Delay in milliseconds
   * @returns {function}
   */
  function debounce(fn, delay = 300) {
    let timeoutId;
    return function debounced(...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  /**
   * Throttle function
   * @param {function} fn - Function to throttle
   * @param {number} limit - Limit in milliseconds
   * @returns {function}
   */
  function throttle(fn, limit = 300) {
    let lastCall = 0;
    return function throttled(...args) {
      const now = Date.now();
      if (now - lastCall >= limit) {
        lastCall = now;
        return fn.apply(this, args);
      }
    };
  }

  /**
   * Deep clone object
   * @param {*} obj - Object to clone
   * @returns {*}
   */
  function deepClone(obj) {
    try {
      return JSON.parse(JSON.stringify(obj));
    } catch (error) {
      log('deepClone error', error, 'warn');
      return obj;
    }
  }

  // ============================================
  // VALIDATION MODULE
  // ============================================

  const Validation = {
    /**
     * Validate email
     * @param {string} email - Email to validate
     * @returns {object} - { valid: boolean, message: string }
     */
    validateEmail(email) {
      if (!email || !email.trim()) {
        return { valid: false, message: 'Email is required' };
      }
      if (!VALIDATION_RULES.email.pattern.test(email)) {
        return { valid: false, message: VALIDATION_RULES.email.message };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate age
     * @param {number|string} age - Age to validate
     * @returns {object} - { valid: boolean, message: string }
     */
    validateAge(age) {
      const ageNum = parseInt(age, 10);
      if (isNaN(ageNum)) {
        return { valid: false, message: 'Age must be a valid number' };
      }
      if (ageNum < VALIDATION_RULES.age.min || ageNum > VALIDATION_RULES.age.max) {
        return { valid: false, message: VALIDATION_RULES.age.message };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate country selection
     * @param {string} country - Country code
     * @returns {object} - { valid: boolean, message: string }
     */
    validateCountry(country) {
      if (!country || !country.trim()) {
        return { valid: false, message: VALIDATION_RULES.country.message };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate gender selection
     * @param {string} sex - Gender value
     * @returns {object} - { valid: boolean, message: string }
     */
    validateSex(sex) {
      if (!sex || !sex.trim()) {
        return { valid: false, message: VALIDATION_RULES.sex.message };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate consent checkbox
     * @param {boolean} consent - Consent value
     * @returns {object} - { valid: boolean, message: string }
     */
    validateConsent(consent) {
      if (!consent) {
        return { valid: false, message: VALIDATION_RULES.consent.message };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate response value
     * @param {number|string} response - Response value
     * @returns {object} - { valid: boolean, message: string }
     */
    validateResponse(response) {
      const value = parseInt(response, 10);
      if (isNaN(value)) {
        return { valid: false, message: 'Invalid response value' };
      }
      if (value < RESPONSE_SCALE.MIN || value > RESPONSE_SCALE.MAX) {
        return {
          valid: false,
          message: `Response must be between ${RESPONSE_SCALE.MIN} and ${RESPONSE_SCALE.MAX}`,
        };
      }
      return { valid: true, message: '' };
    },

    /**
     * Validate entire registration form
     * @param {object} data - Form data
     * @returns {object} - { valid: boolean, errors: object }
     */
    validateRegistrationForm(data) {
      const errors = {};

      const emailValidation = this.validateEmail(data.email);
      if (!emailValidation.valid) {
        errors.email = emailValidation.message;
      }

      const ageValidation = this.validateAge(data.age);
      if (!ageValidation.valid) {
        errors.age = ageValidation.message;
      }

      const countryValidation = this.validateCountry(data.country);
      if (!countryValidation.valid) {
        errors.country = countryValidation.message;
      }

      const sexValidation = this.validateSex(data.sex);
      if (!sexValidation.valid) {
        errors.sex = sexValidation.message;
      }

      const consentValidation = this.validateConsent(data.consent);
      if (!consentValidation.valid) {
        errors.consent = consentValidation.message;
      }

      return {
        valid: Object.keys(errors).length === 0,
        errors,
      };
    },

    /**
     * Display validation errors in UI
     * @param {object} errors - Errors object
     */
    displayErrors(errors) {
      // Clear previous errors
      document.querySelectorAll('.form-error').forEach(el => {
        el.textContent = '';
      });

      // Display new errors
      Object.entries(errors).forEach(([field, message]) => {
        const errorEl = document.getElementById(`${field}Error`);
        if (errorEl) {
          errorEl.textContent = message;
        }

        const inputEl = document.getElementById(field);
        if (inputEl) {
          inputEl.classList.add('error');
        }
      });

      emitEvent(EVENT_TYPES.FORM_ERROR, { errors });
    },

    /**
     * Clear validation errors
     * @param {string|null} fieldName - Optional specific field
     */
    clearErrors(fieldName = null) {
      if (fieldName) {
        const errorEl = document.getElementById(`${fieldName}Error`);
        if (errorEl) {
          errorEl.textContent = '';
        }
        const inputEl = document.getElementById(fieldName);
        if (inputEl) {
          inputEl.classList.remove('error');
        }
      } else {
        document.querySelectorAll('.form-error').forEach(el => {
          el.textContent = '';
        });
        document.querySelectorAll('.form-input, .form-select, .form-textarea').forEach(el => {
          el.classList.remove('error');
        });
      }
    },
  };

  // ============================================
  // REGISTRATION FORM MODULE
  // ============================================

  const RegistrationForm = {
    /**
     * Initialize registration form
     */
    init() {
      const form = document.getElementById('registrationForm');
      if (!form) {
        log('Registration form not found');
        return;
      }

      // Load saved data if exists
      const savedData = Storage.get(STORAGE_KEYS.REGISTRATION_DATA);
      if (savedData) {
        this.populateForm(savedData);
      }

      // Add event listeners
      form.addEventListener('submit', (e) => this.handleSubmit(e));
      form.addEventListener('change', (e) => this.handleChange(e));
      form.addEventListener('input', (e) => this.handleInput(e));

      // Auto-save on change (debounced)
      const autoSave = debounce(() => this.saveFormData(), 500);
      form.addEventListener('change', autoSave);

      // Warn on unsaved changes
      window.addEventListener('beforeunload', (e) => {
        if (formState.isDirty) {
          e.preventDefault();
          e.returnValue = '';
          return '';
        }
      });

      log('Registration form initialized');
    },

    /**
     * Populate form with data
     * @param {object} data - Form data
     */
    populateForm(data) {
      Object.entries(data).forEach(([key, value]) => {
        const element = document.getElementById(key);
        if (element) {
          if (element.type === 'checkbox') {
            element.checked = value;
          } else {
            element.value = value;
          }
        }
      });
    },

    /**
     * Handle form input change
     * @param {event} event - Input event
     */
    handleInput(event) {
      const { id, value } = event.target;
      formState.registrationData[id] = value;
      formState.isDirty = true;

      // Validate on input for better UX
      if (id === 'age') {
        const validation = Validation.validateEmail(value);
        if (validation.valid) {
          Validation.clearErrors(id);
        }
      }
    },

    /**
     * Handle form field change
     * @param {event} event - Change event
     */
    handleChange(event) {
      const { id, type, value, checked } = event.target;
      
      if (type === 'checkbox') {
        formState.registrationData[id] = checked;
      } else {
        formState.registrationData[id] = value;
      }
      
      formState.isDirty = true;

      // Validate on change
      if (id === 'country') {
        const validation = Validation.validateCountry(value);
        if (validation.valid) {
          Validation.clearErrors(id);
        }
      } else if (id === 'sex') {
        const validation = Validation.validateSex(value);
        if (validation.valid) {
          Validation.clearErrors(id);
        }
      }
    },

    /**
     * Handle form submission
     * @param {event} event - Submit event
     */
    async handleSubmit(event) {
      event.preventDefault();

      // Validate form
      const validation = Validation.validateRegistrationForm(formState.registrationData);
      if (!validation.valid) {
        Validation.displayErrors(validation.errors);
        return;
      }

      Validation.clearErrors();
      
      // Set loading state
      const submitBtn = document.getElementById('submitBtn');
      const submitLoader = document.getElementById('submitLoader');
      submitBtn.disabled = true;
      if (submitLoader) {
        submitLoader.hidden = false;
      }

      try {
        // Save form data
        this.saveFormData();

        // Create user via API
        const payload = {
          email: formState.registrationData.email,
          age: parseInt(formState.registrationData.age, 10),
          sex: formState.registrationData.sex,
          country: formState.registrationData.country
        };

        if (!window.apiClient) {
                throw new Error('APIClient not initialized');
            }
            const response = awaitwindow.apiClient.submitDemographics(payload); 
        

        
        if (response.success) {
          formState.sessionToken = response.session_id;
          formState.assessmentId = response.session_id;
          console.log('✓ Demographics submitted:', response);
          Storage.set(STORAGE_KEYS.ASSESSMENT_ID,formState.assessmentId);
          Storage.set(STORAGE_KEYS.SESSION_TOKEN,formState.sessionToken);
          emitEvent(EVENT_TYPES.FORM_SUBMITTED, {
            assessmentId: formState.assessmentId,
            registrationData: formState.registrationData,
            });

          
          // Navigate to questionnaire
          emitEvent(EVENT_TYPES.FORM_SUBMITTED, {
            assessmentId: formState.assessmentId,
            registrationData: formState.registrationData,
          });

          // Redirect to questionnaire
          window.location.href = 'questionnaire.html';
        } else {
          throw new Error(response.error || response.message || 'Failedto create user');
        }
      } catch (error) {
        log('Form submission error', error, 'error');
        Validation.displayErrors({
          form: error.message || 'An error occurred. Please try again.',
        });
      } finally {
        submitBtn.disabled = false;
        if (submitLoader) {
          submitLoader.hidden = true;
        }
      }
    },

    /**
     * Save form data to storage
     */
    saveFormData() {
      Storage.set(STORAGE_KEYS.REGISTRATION_DATA, formState.registrationData);
      emitEvent(EVENT_TYPES.DATA_SAVED, { type: 'registration' });
    },

    /**
     * Get form data
     * @returns {object}
     */
    getFormData() {
      return deepClone(formState.registrationData);
    },

    /**
     * Reset form
     */
    reset() {
      const form = document.getElementById('registrationForm');
      if (form) {
        form.reset();
      }
      formState.registrationData = {};
      formState.isDirty = false;
      Validation.clearErrors();
    },
  };

  // ============================================
  // QUESTIONNAIRE MODULE
  // ============================================

  const Questionnaire = {
    /**
     * Initialize questionnaire
     * @param {array} questions - Question data
     */
    init(questions) {
      if (!questions || questions.length === 0) {
        log('No questions provided');
        return;
      }

      // Restore state from storage
      const savedState = Storage.get(STORAGE_KEYS.QUESTIONNAIRE_STATE);
      if (savedState) {
        formState.currentQuestion = savedState.currentQuestion || 1;
        formState.responses = savedState.responses || {};
      } else {
        formState.startTime = Date.now();
      }

      formState.assessmentId = Storage.get(STORAGE_KEYS.ASSESSMENT_ID);
      formState.sessionToken = Storage.get(STORAGE_KEYS.SESSION_TOKEN);

      // Setup event listeners
      this.setupEventListeners();

      // Display first question
      this.displayQuestion(questions, formState.currentQuestion);

      // Initialize progress tracking
      this.updateProgress();

      // Setup keyboard navigation
      this.setupKeyboardNavigation();

      // Setup periodic autosave
      this.setupAutosave();

      emitEvent(EVENT_TYPES.FORM_INITIALIZED, { type: 'questionnaire' });
      log('Questionnaire initialized');
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
      // Slider input
      const slider = document.getElementById('responseSlider');
      if (slider) {
        slider.addEventListener('input', (e) => this.handleSliderInput(e));
      }

      // Quick select buttons
      document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', (e) => this.handleQuickSelect(e));
      });

      // Navigation buttons
      const prevBtn = document.getElementById('prevBtn');
      const nextBtn = document.getElementById('nextBtn');

      if (prevBtn) {
        prevBtn.addEventListener('click', () => this.previousQuestion());
      }
      if (nextBtn) {
        nextBtn.addEventListener('click', () => this.nextQuestion());
      }

      // Question navigator dots
      document.addEventListener('click', (e) => {
        if (e.target.classList.contains('navigator-dot')) {
          const questionNum = parseInt(e.target.dataset.question, 10);
          this.goToQuestion(questionNum);
        }
      });
    },

    /**
     * Setup keyboard navigation
     */
    setupKeyboardNavigation() {
      document.addEventListener('keydown', (e) => {
        // Arrow keys for navigation
        if (e.key === 'ArrowLeft') {
          this.previousQuestion();
        } else if (e.key === 'ArrowRight') {
          this.nextQuestion();
        }
        // Number keys for quick select
        else if (e.key >= '0' && e.key <= '9') {
          const value = parseInt(e.key, 10) * 10 / 10;
          if (value >= RESPONSE_SCALE.MIN && value <= RESPONSE_SCALE.MAX) {
            this.recordResponse(value);
          }
        }
      });
    },

    /**
     * Handle slider input
     * @param {event} event - Input event
     */
    handleSliderInput(event) {
      const value = event.target.value;
      this.updateResponseDisplay(value);
      this.recordResponse(value);
    },

    /**
     * Handle quick select button
     * @param {event} event - Click event
     */
    handleQuickSelect(event) {
      const value = event.target.dataset.value;
      const slider = document.getElementById('responseSlider');
      if (slider) {
        slider.value = value;
      }
      this.updateResponseDisplay(value);
      this.recordResponse(value);
      
      // Update button state
      document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.classList.remove('active');
      });
      event.target.classList.add('active');
    },

    /**
     * Update response display
     * @param {number|string} value - Response value
     */
    updateResponseDisplay(value) {
      const valueEl = document.getElementById('responseValue');
      const labelEl = document.getElementById('responseLabel');

      if (!valueEl || !labelEl) return;

      const numValue = parseInt(value, 10);
      valueEl.textContent = numValue;

      // Determine label
      let label = 'Neutral';
      if (numValue < 3) label = 'Disagree';
      else if (numValue > 7) label = 'Agree';

      labelEl.textContent = label;

      // Update color gradient
      const percentage = (numValue / RESPONSE_SCALE.MAX) * 100;
      labelEl.style.color = this.getResponseColor(numValue);
    },

    /**
     * Get color for response value
     * @param {number} value - Response value
     * @returns {string}
     */
    getResponseColor(value) {
      if (value < 3) return 'var(--color-error)';
      if (value > 7) return 'var(--color-success)';
      return 'var(--color-text-secondary)';
    },

    /**
     * Record response
     * @param {number|string} value - Response value
     */
    recordResponse(value) {
      const validation = Validation.validateResponse(value);
      if (!validation.valid) {
        log('Invalid response', { value, error: validation.message }, 'warn');
        return;
      }

      const questionNum = formState.currentQuestion;
      formState.responses[questionNum] = parseInt(value, 10);
      formState.isDirty = true;

      emitEvent(EVENT_TYPES.RESPONSE_RECORDED, {
        question: questionNum,
        value: parseInt(value, 10),
      });

      // Save state
      this.saveState();
    },

    /**
     * Display question
     * @param {array} questions - All questions
     * @param {number} questionNum - Question number to display
     */
    displayQuestion(questions, questionNum) {
      if (questionNum < 1 || questionNum > questions.length) {
        log('Invalid question number', { questionNum });
        return;
      }

      const question = questions[questionNum - 1];
      
      // Update DOM
      const domainEl = document.getElementById('questionDomain');
      const textEl = document.getElementById('questionText');
      const slider = document.getElementById('responseSlider');

      if (domainEl) {
        domainEl.textContent = question.domainName;
      }

      if (textEl) {
        textEl.textContent = question.text;
      }

      // Set slider value if response exists
      if (slider) {
        const existingResponse = formState.responses[questionNum];
        slider.value = existingResponse || RESPONSE_SCALE.MID;
        this.updateResponseDisplay(slider.value);
      }

      // Update quick buttons
      document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.classList.remove('active');
        if (existingResponse && btn.dataset.value == existingResponse) {
          btn.classList.add('active');
        }
      });

      // Update question number
      const currentEl = document.getElementById('currentQuestion');
      if (currentEl) {
        currentEl.textContent = questionNum;
      }

      // Update navigation buttons
      const prevBtn = document.getElementById('prevBtn');
      const nextBtn = document.getElementById('nextBtn');
      if (prevBtn) {
        prevBtn.disabled = questionNum === 1;
      }
      if (nextBtn) {
        nextBtn.textContent = questionNum === questions.length ? 'Submit' : 'Next →';
      }

      formState.currentQuestion = questionNum;
      this.updateProgress();
      this.updateNavigator(questions.length);
    },

    /**
     * Go to next question
     */
    nextQuestion() {
      const questionsData = this.getQuestionsData();
      const nextNum = formState.currentQuestion + 1;

      if (nextNum > QUESTIONNAIRE_CONFIG.TOTAL_QUESTIONS) {
        // Submit assessment
        this.submitAssessment();
        return;
      }

      this.displayQuestion(questionsData, nextNum);
    },

    /**
     * Go to previous question
     */
    previousQuestion() {
      const questionsData = this.getQuestionsData();
      const prevNum = formState.currentQuestion - 1;

      if (prevNum < 1) {
        return;
      }

      this.displayQuestion(questionsData, prevNum);
    },

    /**
     * Go to specific question
     * @param {number} questionNum - Question number
     */
    goToQuestion(questionNum) {
      const questionsData = this.getQuestionsData();
      this.displayQuestion(questionsData, questionNum);
    },

    /**
     * Get questions data from DOM
     * @returns {array}
     */
    getQuestionsData() {
      const scriptEl = document.getElementById('questionData');
      if (!scriptEl) {
        log('Question data not found');
        return [];
      }

      try {
        const data = JSON.parse(scriptEl.textContent);
        return data.questions || [];
      } catch (error) {
        log('Error parsing question data', error, 'error');
        return [];
      }
    },

    /**
     * Update progress bar
     */
    updateProgress() {
      const current = formState.currentQuestion;
      const total = QUESTIONNAIRE_CONFIG.TOTAL_QUESTIONS;
      const percentage = Math.round((current / total) * 100);

      // Update progress bar
      const progressBar = document.getElementById('progressBar');
      if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', current);
      }

      // Update percentage text
      const percentageEl = document.getElementById('progressPercentage');
      if (percentageEl) {
        percentageEl.textContent = `${percentage}%`;
      }

      // Update sidebar progress
      const sidebarProgress = document.getElementById('sidebarProgress');
      if (sidebarProgress) {
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (percentage / 100) * circumference;
        sidebarProgress.style.strokeDashoffset = offset;
      }

      const sidebarPercentage = document.getElementById('sidebarPercentage');
      if (sidebarPercentage) {
        sidebarPercentage.textContent = `${percentage}%`;
      }

      emitEvent(EVENT_TYPES.PROGRESS_UPDATED, { current, total, percentage });
    },

    /**
     * Update question navigator dots
     * @param {number} totalQuestions - Total number of questions
     */
    updateNavigator(totalQuestions) {
      const navigator = document.getElementById('questionNavigator');
      if (!navigator) return;

      // Clear existing dots
      navigator.innerHTML = '';

      // Create dots
      for (let i = 1; i <= totalQuestions; i++) {
        const dot = document.createElement('button');
        dot.className = 'navigator-dot';
        dot.dataset.question = i;
        dot.textContent = i;
        dot.type = 'button';

        // Add state classes
        if (i === formState.currentQuestion) {
          dot.classList.add('active');
        } else if (formState.responses[i] !== undefined) {
          dot.classList.add('answered');
        }

        navigator.appendChild(dot);
      }
    },

    /**
     * Submit assessment
     */
    async submitAssessment() {
      formState.endTime = Date.now();

      // Show processing state
      this.showProcessingState();

      try {
        // Validate all responses are recorded
        const questionsData = this.getQuestionsData();
        const allResponded = questionsData.every(q => formState.responses[q.id] !== undefined);

        if (!allResponded) {
          throw new Error('Not all questions have been answered');
        }

        // Save final state
        this.saveState();

        // Submit responses via API
        const response = await ApiClient.submitAssessment({
          assessment_id: formState.assessmentId,
          responses: formState.responses,
          completion_time: Math.round((formState.endTime - formState.startTime) / 1000),
          session_token: formState.sessionToken,
        });

        if (response.success) {
          emitEvent(EVENT_TYPES.ASSESSMENT_COMPLETED, {
            assessmentId: formState.assessmentId,
            responses: formState.responses,
          });

          // Redirect to results
          window.location.href = `results.html?assessment_id=${formState.assessmentId}`;
        } else {
          throw new Error(response.message || 'Failed to submit assessment');
        }
      } catch (error) {
        log('Assessment submission error', error, 'error');
        this.showProcessingError(error.message);

        // Recover by showing retry option
        emitEvent(EVENT_TYPES.ERROR_RECOVERED, { error: error.message });
      }
    },

    /**
     * Show processing state
     */
    showProcessingState() {
      const instructionPanel = document.getElementById('instructionPanel');
      const questionPanel = document.getElementById('questionPanel');
      const summaryPanel = document.getElementById('summaryPanel');

      if (instructionPanel) instructionPanel.hidden = true;
      if (questionPanel) questionPanel.hidden = true;
      if (summaryPanel) summaryPanel.hidden = false;
    },

    /**
     * Show processing error
     * @param {string} message - Error message
     */
    showProcessingError(message) {
      const errorBox = document.createElement('div');
      errorBox.className = 'error-box';
      errorBox.innerHTML = `
        <h3>Error Processing Assessment</h3>
        <p>${message}</p>
        <button class="btn btn-primary" id="retrySubmitBtn">Retry</button>
      `;

      const summaryPanel = document.getElementById('summaryPanel');
      if (summaryPanel) {
        summaryPanel.appendChild(errorBox);
      }

      document.getElementById('retrySubmitBtn')?.addEventListener('click', () => {
        this.submitAssessment();
      });
    },

    /**
     * Save questionnaire state
     */
    saveState() {
      Storage.set(STORAGE_KEYS.QUESTIONNAIRE_STATE, {
        currentQuestion: formState.currentQuestion,
        responses: formState.responses,
      });

      Storage.set(STORAGE_KEYS.RESPONSES, formState.responses);
      emitEvent(EVENT_TYPES.DATA_SAVED, { type: 'questionnaire' });
    },

    /**
     * Setup periodic autosave
     */
    setupAutosave() {
      // Autosave every 30 seconds
      setInterval(() => {
        if (formState.isDirty) {
          this.saveState();
          formState.isDirty = false;
          log('State autosaved');
        }
      }, 30000);
    },

    /**
     * Get current responses
     * @returns {object}
     */
    getResponses() {
      return deepClone(formState.responses);
    },

    /**
     * Reset questionnaire
     */
    reset() {
      formState.responses = {};
      formState.currentQuestion = 1;
      Storage.remove(STORAGE_KEYS.QUESTIONNAIRE_STATE);
      Storage.remove(STORAGE_KEYS.RESPONSES);
    },
  };

  // ============================================
  // RESULTS MODULE
  // ============================================

  const ResultsPage = {
    /**
     * Initialize results page
     */
    async init() {
      try {
        // Get assessment ID from URL
        const urlParams = new URLSearchParams(window.location.search);
        const assessmentId = urlParams.get('assessment_id');

        if (!assessmentId) {
          throw new Error('No assessment ID provided');
        }

        // Fetch results from API
        const sessionToken = Storage.get(STORAGE_KEYS.SESSION_TOKEN);
        const response = await ApiClient.getAssessmentResults({
          assessment_id: assessmentId,
          session_token: sessionToken,
        });

        if (response.success) {
          this.displayResults(response.data);
          this.setupResultsInteractions();
        } else {
          throw new Error(response.message || 'Failed to fetch results');
        }
      } catch (error) {
        log('Results initialization error', error, 'error');
        this.showError(error.message);
      }
    },

    /**
     * Display results in UI
     * @param {object} resultsData - Results data from API
     */
    displayResults(resultsData) {
      try {
        // Hide loading state
        const loadingState = document.getElementById('loadingState');
        const resultsContent = document.getElementById('resultsContent');

        if (loadingState) loadingState.hidden = true;
        if (resultsContent) resultsContent.hidden = false;

        // Populate personality type
        const typeEl = document.getElementById('primaryType');
        const labelEl = document.getElementById('primaryTypeLabel');

        if (typeEl) typeEl.textContent = resultsData.personality_type;
        if (labelEl) labelEl.textContent = resultsData.type_label;

        // Populate confidence badge
        const badgeEl = document.getElementById('confidenceBadge');
        if (badgeEl) {
          badgeEl.textContent = `${resultsData.confidence}% Confidence`;
        }

        // Populate description
        const descEl = document.getElementById('typeDescription');
        if (descEl) {
          descEl.textContent = resultsData.type_description;
        }

        // Populate characteristics
        const charList = document.getElementById('typeCharacteristics');
        if (charList && resultsData.characteristics) {
          charList.innerHTML = resultsData.characteristics
            .map(char => `<li>${char}</li>`)
            .join('');
        }

        // Populate domain scores
        this.displayDomainScores(resultsData.domains);

        // Populate blend data
        this.displayBlend(resultsData.blend);

        // Populate narrative
        const narrativeEl = document.getElementById('narrative');
        if (narrativeEl && resultsData.narrative) {
          narrativeEl.textContent = resultsData.narrative;
        }

        // Populate other sections
        this.displayStrengths(resultsData.strengths);
        this.displayWeaknesses(resultsData.weaknesses);
        this.displayRecommendations(resultsData.recommendations);
        this.displayCareerInsights(resultsData.career_insights);
        this.displayAssessmentDetails(resultsData.assessment_details);

        log('Results displayed successfully');
      } catch (error) {
        log('Error displaying results', error, 'error');
        this.showError('Error displaying results');
      }
    },

    /**
     * Display domain scores
     * @param {object} domains - Domain data
     */
    displayDomainScores(domains) {
      const grid = document.getElementById('domainsGrid');
      if (!grid) return;

      grid.innerHTML = Object.entries(domains).map(([name, data]) => `
        <div class="domain-card">
          <div class="domain-header">
            <h3 class="domain-card-title">${name}</h3>
            <span class="domain-badge">${data.raw_score.toFixed(1)}/5</span>
          </div>
          <div class="score-display">
            <span class="score-value">${data.corrected_score.toFixed(1)}</span>
            <span class="score-max">/5</span>
          </div>
          <div class="confidence-interval">
            <strong>95% CI:</strong> [${data.confidence_lower.toFixed(1)}, ${data.confidence_upper.toFixed(1)}]
          </div>
          <div class="percentile">
            <span class="percentile-label">Percentile:</span>
            <span class="percentile-value">${data.percentile}%</span>
          </div>
        </div>
      `).join('');
    },

    /**
     * Display personality blend
     * @param {object} blend - Blend data
     */
    displayBlend(blend) {
      const barsContainer = document.getElementById('blendBars');
      const legendContainer = document.getElementById('blendLegend');

      if (!barsContainer || !blend) return;

      const types = Object.entries(blend).sort((a, b) => b[1] - a[1]);

      barsContainer.innerHTML = types.map(([type, percentage]) => `
        <div class="blend-bar">
          <div class="blend-bar-label">
            <span class="blend-bar-type">Type ${type}</span>
            <span class="blend-bar-value">${percentage}%</span>
          </div>
          <div class="blend-bar-track">
            <div class="blend-bar-fill" style="width: ${percentage}%"></div>
          </div>
        </div>
      `).join('');

      if (legendContainer) {
        legendContainer.innerHTML = types.map(([type, percentage]) => `
          <div class="legend-item">
            <span class="legend-color" style="background: var(--color-type-${type.toLowerCase()})"></span>
            <span>Type ${type}: ${percentage}%</span>
          </div>
        `).join('');
      }
    },

    /**
     * Display strengths
     * @param {array} strengths - Strengths list
     */
    displayStrengths(strengths) {
      const list = document.getElementById('strengthsList');
      if (list && strengths) {
        list.innerHTML = strengths.map(s => `<li>${s}</li>`).join('');
      }
    },

    /**
     * Display weaknesses
     * @param {array} weaknesses - Weaknesses list
     */
    displayWeaknesses(weaknesses) {
      const list = document.getElementById('weaknessesList');
      if (list && weaknesses) {
        list.innerHTML = weaknesses.map(w => `<li>${w}</li>`).join('');
      }
    },

    /**
     * Display recommendations
     * @param {array} recommendations - Recommendations list
     */
    displayRecommendations(recommendations) {
      const grid = document.getElementById('recommendationsGrid');
      if (!grid || !recommendations) return;

      grid.innerHTML = recommendations.map(rec => `
        <div class="recommendation-item">
          <h3>${rec.title}</h3>
          <p>${rec.description}</p>
        </div>
      `).join('');
    },

    /**
     * Display career insights
     * @param {object} insights - Career insights
     */
    displayCareerInsights(insights) {
      if (!insights) return;

      const rolesEl = document.getElementById('idealRoles');
      if (rolesEl && insights.ideal_roles) {
        rolesEl.innerHTML = insights.ideal_roles.map(r => `<li>${r}</li>`).join('');
      }

      const prefsEl = document.getElementById('workPreferences');
      if (prefsEl && insights.work_preferences) {
        prefsEl.innerHTML = insights.work_preferences.map(p => `<li>${p}</li>`).join('');
      }

      const challengesEl = document.getElementById('careerChallenges');
      if (challengesEl && insights.challenges) {
        challengesEl.innerHTML = insights.challenges.map(c => `<li>${c}</li>`).join('');
      }
    },

    /**
     * Display assessment details
     * @param {object} details - Assessment details
     */
    displayAssessmentDetails(details) {
      if (!details) return;

      const mapping = {
        'assessment_id': 'assessmentId',
        'completion_time': 'completionTime',
        'validity_score': 'validityScore',
        'anomaly_detection': 'anomalyDetection',
        'response_quality': 'responseQuality',
        'assessment_date': 'assessmentDate',
      };

      Object.entries(mapping).forEach(([key, elId]) => {
        const el = document.getElementById(elId);
        if (el && details[key]) {
          el.textContent = details[key];
        }
      });
    },

    /**
     * Setup results page interactions
     */
    setupResultsInteractions() {
      // Download button
      const downloadBtn = document.getElementById('downloadBtn');
      if (downloadBtn) {
        downloadBtn.addEventListener('click', () => this.downloadResults());
      }

      // Share button
      const shareBtn = document.getElementById('shareBtn');
      if (shareBtn) {
        shareBtn.addEventListener('click', () => this.showShareModal());
      }

      // Delete button
      const deleteBtn = document.getElementById('deleteBtn');
      if (deleteBtn) {
        deleteBtn.addEventListener('click', () => this.showDeleteModal());
      }

      // Retake button
      const retakeBtn = document.getElementById('retakeBtn');
      if (retakeBtn) {
        retakeBtn.addEventListener('click', () => {
          Storage.clear([
            STORAGE_KEYS.QUESTIONNAIRE_STATE,
            STORAGE_KEYS.RESPONSES,
            STORAGE_KEYS.ASSESSMENT_ID,
          ]);
          window.location.href = 'index.html';
        });
      }
    },

    /**
     * Download results as PDF
     */
    downloadResults() {
      // Implementation would use a PDF library
      log('Download results clicked');
      alert('PDF download feature coming soon');
    },

    /**
     * Show share modal
     */
    showShareModal() {
      const modal = document.getElementById('shareModal');
      if (modal) {
        modal.hidden = false;
        this.setupShareButtons();
      }
    },

    /**
     * Setup share buttons
     */
    setupShareButtons() {
      const shareLink = `${window.location.origin}${window.location.pathname}${window.location.search}`;
      const text = 'I just completed the EFOPA personality assessment. Check your results!';

      document.getElementById('shareLinkedin')?.addEventListener('click', () => {
        window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareLink)}`);
      });

      document.getElementById('shareTwitter')?.addEventListener('click', () => {
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareLink)}`);
      });

      document.getElementById('shareFacebook')?.addEventListener('click', () => {
        window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareLink)}`);
      });

      document.getElementById('copyLink')?.addEventListener('click', () => {
        navigator.clipboard.writeText(shareLink);
        alert('Link copied to clipboard!');
      });

      document.getElementById('emailShare')?.addEventListener('click', () => {
        window.location.href = `mailto:?subject=${encodeURIComponent('EFOPA Results')}&body=${encodeURIComponent(text + '\n\n' + shareLink)}`;
      });
    },

    /**
     * Show delete modal
     */
    async showDeleteModal() {
      const modal = document.getElementById('deleteModal');
      if (modal) {
        modal.hidden = false;

        document.getElementById('confirmDelete')?.addEventListener('click', async () => {
          try {
            const assessmentId = new URLSearchParams(window.location.search).get('assessment_id');
            const sessionToken = Storage.get(STORAGE_KEYS.SESSION_TOKEN);

            await EFOPAApiClient.deleteAssessmentData({
              assessment_id: assessmentId,
              session_token: sessionToken,
            });

            Storage.clear();
            window.location.href = 'index.html';
          } catch (error) {
            log('Delete error', error, 'error');
            alert('Error deleting data. Please try again.');
          }
        });

        document.getElementById('cancelDelete')?.addEventListener('click', () => {
          modal.hidden = true;
        });
      }
    },

    /**
     * Show error
     * @param {string} message - Error message
     */
    showError(message) {
      const loadingState = document.getElementById('loadingState');
      const errorState = document.getElementById('errorState');
      const errorMessage = document.getElementById('errorMessage');

      if (loadingState) loadingState.hidden = true;
      if (errorState) errorState.hidden = false;
      if (errorMessage) errorMessage.textContent = message;

      document.getElementById('retryBtn')?.addEventListener('click', () => {
        location.reload();
      });
    },
  };

  // ============================================
  // PUBLIC API
  // ============================================

  return {
    // Initialization
    initRegistrationForm() {
      RegistrationForm.init();
    },

    initQuestionnaire(questions) {
      Questionnaire.init(questions);
    },

    initResultsPage() {
      ResultsPage.init();
    },

    // Form data access
    getRegistrationData() {
      return RegistrationForm.getFormData();
    },

    getResponses() {
      return Questionnaire.getResponses();
    },

    getFormState() {
      return deepClone(formState);
    },

    // Storage utilities
    saveData(key, value) {
      return Storage.set(key, value);
    },

    getData(key, defaultValue = null) {
      return Storage.get(key, defaultValue);
    },

    removeData(key) {
      return Storage.remove(key);
    },

    clearAllData() {
      return Storage.clear(Object.values(STORAGE_KEYS));
    },

    // Validation utilities
    validateField(fieldName, value) {
      const validators = {
        email: () => Validation.validateEmail(value),
        age: () => Validation.validateAge(value),
        country: () => Validation.validateCountry(value),
        sex: () => Validation.validateSex(value),
        consent: () => Validation.validateConsent(value),
        response: () => Validation.validateResponse(value),
      };

      return validators[fieldName] ? validators[fieldName]() : { valid: false, message: 'Unknown field' };
    },

    // Event subscription
    on(eventType, callback) {
      document.addEventListener(eventType, callback);
    },

    off(eventType, callback) {
      document.removeEventListener(eventType, callback);
    },

    // Utilities
    setDebugMode(enabled) {
      window.__EFOPA_DEBUG__ = enabled;
    },

    getConstants() {
      return {
        STORAGE_KEYS,
        EVENT_TYPES,
        QUESTIONNAIRE_CONFIG,
        RESPONSE_SCALE,
      };
    },
  };
})();

// Auto-initialize based on current page
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    if (path.includes('index.html') || path === '/') {
      EFOPAFormLogic.initRegistrationForm();
    } else if (path.includes('questionnaire.html')) {
      // Questions will be initialized when modal closes
      const beginBtn = document.getElementById('beginBtn');
      if (beginBtn) {
        beginBtn.addEventListener('click', () => {
          const questions = JSON.parse(document.getElementById('questionData').textContent).questions;
          EFOPAFormLogic.initQuestionnaire(questions);
        });
      }
    } else if (path.includes('results.html')) {
      EFOPAFormLogic.initResultsPage();
    }
  });
} else {
  const path = window.location.pathname;
  
  if (path.includes('index.html') || path === '/') {
    EFOPAFormLogic.initRegistrationForm();
  } else if (path.includes('questionnaire.html')) {
    const beginBtn = document.getElementById('beginBtn');
    if (beginBtn) {
      beginBtn.addEventListener('click', () => {
        const questions = JSON.parse(document.getElementById('questionData').textContent).questions;
        EFOPAFormLogic.initQuestionnaire(questions);
      });
    }
  } else if (path.includes('results.html')) {
    EFOPAFormLogic.initResultsPage();
  }
}
