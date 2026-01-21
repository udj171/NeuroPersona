/**
 * EFOPA Platform - Form Logic Module
 * Version: 2.1 (Updated with Retry Logic)
 * Author: EFOPA Development Team
 * Description: Comprehensive form handling, validation, state management, and user interaction logic with error recovery
 * 
 * This module provides:
 * - Form validation (client-side and server-side error handling)
 * - State management for form data
 * - Event handling and user interactions
 * - Progress tracking and navigation
 * - Local storage persistence
 * - Accessibility features
 * - Error recovery and retry logic (3 attempts)
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
    // CSRF TOKEN INITIALIZATION
    // ============================================

    async function initializeCSRFToken() {
        try {
            const response = await fetch('/api/csrf-token');
            const data = await response.json();
            const csrfMeta = document.getElementById('csrf-token');
            if (csrfMeta && data.csrf_token) {
                csrfMeta.content = data.csrf_token;
            }
        } catch (error) {
            console.warn('CSRF token fetch failed:', error);
        }
    }

    // Initialize CSRF token on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeCSRFToken);
    } else {
        initializeCSRFToken();
    }

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
                const validation = Validation.validateAge(value);
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
         * Handle form submission with retry logic
         * @param {event} event - Submit event
         */
        async handleSubmit(event) {
            event.preventDefault();

            const validation = Validation.validateRegistrationForm(formState.registrationData);
            if (!validation.valid) {
                Validation.displayErrors(validation.errors);
                return;
            }

            Validation.clearErrors();

            const submitBtn = document.getElementById('submitBtn');
            let retryCount = 0;
            const maxRetries = 3;

            const attemptSubmit = async () => {
                try {
                    submitBtn.disabled = true;

                    const response = await apiClient.submitDemographics(formState.registrationData);

                    if (response.success) {
                        formState.assessmentId = response.data.assessment_id;
                        formState.sessionToken = response.data.session_token;

                        Storage.set(STORAGE_KEYS.ASSESSMENT_ID, formState.assessmentId);
                        Storage.set(STORAGE_KEYS.SESSION_TOKEN, formState.sessionToken);

                        emitEvent(EVENT_TYPES.FORM_SUBMITTED, { assessmentId: formState.assessmentId });
                        window.location.href = 'questionnaire.html';
                        return;
                    }

                    throw new Error(response.message || 'Submission failed');

                } catch (error) {
                    retryCount++;

                    if (retryCount < maxRetries) {
                        // Show retry option
                        const errorDiv = document.querySelector('.form-error-container');
                        if (!errorDiv) {
                            console.error('Error container not found in DOM');
                            submitBtn.disabled = false;
                            return;
                        }

                        errorDiv.innerHTML = `
                            <div class="error-alert">
                                <p>Error: ${error.message}</p>
                                <p>Attempt ${retryCount}/${maxRetries}</p>
                                <button type="button" class="btn btn-primary" id="retryBtn">
                                    Retry
                                </button>
                            </div>
                        `;

                        document.getElementById('retryBtn').addEventListener('click', () => {
                            errorDiv.innerHTML = '';
                            attemptSubmit();
                        });

                    } else {
                        // All retries exhausted
                        const errorDiv = document.querySelector('.form-error-container');
                        if (errorDiv) {
                            errorDiv.innerHTML = `
                                <div class="error-alert error-critical">
                                    <h3>Submission Failed</h3>
                                    <p>${error.message}</p>
                                    <button type="button" class="btn btn-primary" onclick="location.reload()">
                                        Reload Page
                                    </button>
                                </div>
                            `;
                        }
                    }

                    submitBtn.disabled = false;
                }
            };

            attemptSubmit();
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
    // PUBLIC API
    // ============================================

    return {
        RegistrationForm,
        Storage,
        Validation,
        formState,
        uiState,
        log,
        emitEvent,
        EVENT_TYPES,
        STORAGE_KEYS,
    };
})();

// ============================================
// INITIALIZATION
// ============================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        EFOPAFormLogic.RegistrationForm.init();
    });
} else {
    EFOPAFormLogic.RegistrationForm.init();
}