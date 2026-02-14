/**
 * Survey UI Components - Core JavaScript functionality
 */

// Global survey utilities
window.SurveyUtils = {
    
    /**
     * Get CSRF token from DOM
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                     document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
                     '';
        return token;
    },
    
    /**
     * Show loading state for an element
     */
    showLoading(element, message = 'Loading...') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (element) {
            element.innerHTML = `
                <div class="loading-state">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>${message}</p>
                </div>
            `;
        }
    },
    
    /**
     * Show error state for an element
     */
    showError(element, message = 'An error occurred', retryCallback = null) {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (element) {
            const retryButton = retryCallback ? 
                `<button class="btn btn-secondary" onclick="${retryCallback}">Retry</button>` : '';
            
            element.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                    ${retryButton}
                </div>
            `;
        }
    },
    
    /**
     * Debounce function calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Throttle function calls
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },
    
    /**
     * Format validation error messages
     */
    formatValidationError(error) {
        if (typeof error === 'string') return error;
        if (error.message) return error.message;
        if (error.detail) return error.detail;
        return 'Validation error occurred';
    },
    
    /**
     * Animate element entrance
     */
    animateIn(element, animationClass = 'fade-in') {
        if (typeof element === 'string') {
            element = document.getElementById(element);
        }
        
        if (element) {
            element.classList.add(animationClass);
            setTimeout(() => {
                element.classList.remove(animationClass);
            }, 300);
        }
    },
    
    /**
     * Smooth scroll to element
     */
    scrollToElement(element, offset = 0) {
        if (typeof element === 'string') {
            element = document.getElementById(element) || document.querySelector(element);
        }
        
        if (element) {
            const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
            const offsetPosition = elementPosition - offset;
            
            window.scrollTo({
                top: offsetPosition,
                behavior: 'smooth'
            });
        }
    },
    
    /**
     * Local storage helpers with error handling
     */
    storage: {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                console.warn('Failed to save to localStorage:', error);
                return false;
            }
        },
        
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                console.warn('Failed to read from localStorage:', error);
                return defaultValue;
            }
        },
        
        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (error) {
                console.warn('Failed to remove from localStorage:', error);
                return false;
            }
        }
    }
};

// Progress Tracker Component
class ProgressTracker {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? 
            document.getElementById(container) : container;
        this.options = {
            showPercentage: true,
            showSectionNames: true,
            animateProgress: true,
            ...options
        };
        this.sections = [];
        this.currentSection = 0;
        this.completedSections = new Set();
    }
    
    setSections(sections) {
        this.sections = sections;
        this.render();
    }
    
    setCurrentSection(index) {
        this.currentSection = index;
        this.updateDisplay();
    }
    
    markSectionCompleted(index) {
        this.completedSections.add(index);
        this.updateDisplay();
    }
    
    markSectionIncomplete(index) {
        this.completedSections.delete(index);
        this.updateDisplay();
    }
    
    getCompletionPercentage() {
        return this.sections.length > 0 ? 
            Math.round((this.completedSections.size / this.sections.length) * 100) : 0;
    }
    
    render() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="progress-sections" id="progressSections"></div>
            ${this.options.showPercentage ? '<div class="progress-text" id="progressText">0% Complete</div>' : ''}
        `;
        
        this.renderSections();
        this.updateDisplay();
    }
    
    renderSections() {
        const sectionsContainer = this.container.querySelector('#progressSections');
        if (!sectionsContainer) return;
        
        sectionsContainer.innerHTML = '';
        
        this.sections.forEach((section, index) => {
            const sectionElement = document.createElement('div');
            sectionElement.className = 'progress-section';
            sectionElement.innerHTML = `
                <div class="section-dot"></div>
                ${this.options.showSectionNames ? `<span class="section-name">${section.name}</span>` : ''}
            `;
            sectionsContainer.appendChild(sectionElement);
        });
    }
    
    updateDisplay() {
        const percentage = this.getCompletionPercentage();
        
        // Update progress bar
        const progressFill = this.container.querySelector('#progressFill');
        if (progressFill) {
            if (this.options.animateProgress) {
                progressFill.style.transition = 'width 0.3s ease';
            }
            progressFill.style.width = `${percentage}%`;
        }
        
        // Update progress text
        const progressText = this.container.querySelector('#progressText');
        if (progressText) {
            progressText.textContent = `${percentage}% Complete`;
        }
        
        // Update section indicators
        const sectionElements = this.container.querySelectorAll('.progress-section');
        sectionElements.forEach((element, index) => {
            element.classList.toggle('active', index === this.currentSection);
            element.classList.toggle('completed', this.completedSections.has(index));
        });
    }
}

// Question Renderer Component
class QuestionRenderer {
    constructor(container) {
        this.container = typeof container === 'string' ? 
            document.getElementById(container) : container;
        this.validators = new Map();
        this.changeHandlers = new Map();
    }
    
    renderQuestion(question, value = null) {
        const questionElement = document.createElement('div');
        questionElement.className = 'question-container';
        questionElement.setAttribute('data-question-id', question.id);
        
        const renderer = this.getQuestionRenderer(question.question_type);
        questionElement.innerHTML = renderer(question, value);
        
        // Setup event listeners
        this.setupQuestionListeners(questionElement, question);
        
        return questionElement;
    }
    
    getQuestionRenderer(questionType) {
        const renderers = {
            'TEXT': this.renderTextQuestion.bind(this),
            'NUMBER': this.renderNumberQuestion.bind(this),
            'CHOICE': this.renderChoiceQuestion.bind(this),
            'MULTI_CHOICE': this.renderMultiChoiceQuestion.bind(this),
            'RANGE': this.renderRangeQuestion.bind(this),
            'BOOLEAN': this.renderBooleanQuestion.bind(this)
        };
        
        return renderers[questionType] || renderers['TEXT'];
    }
    
    renderTextQuestion(question, value) {
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <input 
                type="text" 
                name="question_${question.id}" 
                value="${value || ''}"
                class="form-input"
                ${question.is_required ? 'required' : ''}
                placeholder="${question.placeholder || ''}"
            />
            <div class="validation-message"></div>
        `;
    }
    
    renderNumberQuestion(question, value) {
        const rules = question.validation_rules || {};
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <input 
                type="number" 
                name="question_${question.id}" 
                value="${value || ''}"
                class="form-input"
                ${rules.min !== undefined ? `min="${rules.min}"` : ''}
                ${rules.max !== undefined ? `max="${rules.max}"` : ''}
                ${rules.step !== undefined ? `step="${rules.step}"` : ''}
                ${question.is_required ? 'required' : ''}
                placeholder="${question.placeholder || ''}"
            />
            <div class="validation-message"></div>
        `;
    }
    
    renderChoiceQuestion(question, value) {
        const choices = question.choices || [];
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <div class="choice-options">
                ${choices.map(choice => `
                    <label class="choice-option">
                        <input 
                            type="radio" 
                            name="question_${question.id}" 
                            value="${choice.value}"
                            ${value === choice.value ? 'checked' : ''}
                            ${question.is_required ? 'required' : ''}
                        />
                        <span class="choice-text">${choice.label}</span>
                    </label>
                `).join('')}
            </div>
            <div class="validation-message"></div>
        `;
    }
    
    renderMultiChoiceQuestion(question, value) {
        const choices = question.choices || [];
        const selectedValues = Array.isArray(value) ? value : (value ? [value] : []);
        
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <div class="choice-options multi-choice">
                ${choices.map(choice => `
                    <label class="choice-option">
                        <input 
                            type="checkbox" 
                            name="question_${question.id}" 
                            value="${choice.value}"
                            ${selectedValues.includes(choice.value) ? 'checked' : ''}
                        />
                        <span class="choice-text">${choice.label}</span>
                    </label>
                `).join('')}
            </div>
            <div class="validation-message"></div>
        `;
    }
    
    renderRangeQuestion(question, value) {
        const rules = question.validation_rules || {};
        const min = rules.min || 0;
        const max = rules.max || 100;
        const step = rules.step || 1;
        const currentValue = value || min;
        
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <div class="range-container">
                <input 
                    type="range" 
                    name="question_${question.id}" 
                    value="${currentValue}"
                    min="${min}"
                    max="${max}"
                    step="${step}"
                    class="form-range"
                />
                <div class="range-labels">
                    <span>${min}</span>
                    <span class="range-value">${currentValue}</span>
                    <span>${max}</span>
                </div>
            </div>
            <div class="validation-message"></div>
        `;
    }
    
    renderBooleanQuestion(question, value) {
        return `
            <label class="question-label">
                ${question.question_text}
                ${question.is_required ? '<span class="required">*</span>' : ''}
            </label>
            ${question.help_text ? `<p class="question-help">${question.help_text}</p>` : ''}
            <div class="boolean-options">
                <label class="choice-option">
                    <input 
                        type="radio" 
                        name="question_${question.id}" 
                        value="true"
                        ${value === 'true' || value === true ? 'checked' : ''}
                        ${question.is_required ? 'required' : ''}
                    />
                    <span class="choice-text">Yes</span>
                </label>
                <label class="choice-option">
                    <input 
                        type="radio" 
                        name="question_${question.id}" 
                        value="false"
                        ${value === 'false' || value === false ? 'checked' : ''}
                        ${question.is_required ? 'required' : ''}
                    />
                    <span class="choice-text">No</span>
                </label>
            </div>
            <div class="validation-message"></div>
        `;
    }
    
    setupQuestionListeners(questionElement, question) {
        const inputs = questionElement.querySelectorAll(`[name="question_${question.id}"]`);
        
        inputs.forEach(input => {
            // Handle range input display updates
            if (input.type === 'range') {
                input.addEventListener('input', (e) => {
                    const valueSpan = questionElement.querySelector('.range-value');
                    if (valueSpan) {
                        valueSpan.textContent = e.target.value;
                    }
                });
            }
            
            // Handle change events
            const changeHandler = SurveyUtils.debounce((e) => {
                const handler = this.changeHandlers.get(question.id);
                if (handler) {
                    handler(question.id, this.getQuestionValue(question.id));
                }
            }, 300);
            
            input.addEventListener('change', changeHandler);
            input.addEventListener('input', changeHandler);
        });
    }
    
    getQuestionValue(questionId) {
        const inputs = document.querySelectorAll(`[name="question_${questionId}"]`);
        
        if (inputs.length === 0) return null;
        
        const firstInput = inputs[0];
        
        if (firstInput.type === 'checkbox') {
            // Multi-choice question
            const checkedInputs = document.querySelectorAll(`[name="question_${questionId}"]:checked`);
            return Array.from(checkedInputs).map(input => input.value);
        } else if (firstInput.type === 'radio') {
            // Single choice question
            const checkedInput = document.querySelector(`[name="question_${questionId}"]:checked`);
            return checkedInput ? checkedInput.value : null;
        } else {
            // Text, number, range inputs
            return firstInput.value;
        }
    }
    
    setQuestionValue(questionId, value) {
        const inputs = document.querySelectorAll(`[name="question_${questionId}"]`);
        
        if (inputs.length === 0) return;
        
        const firstInput = inputs[0];
        
        if (firstInput.type === 'checkbox') {
            // Multi-choice question
            const values = Array.isArray(value) ? value : [value];
            inputs.forEach(input => {
                input.checked = values.includes(input.value);
            });
        } else if (firstInput.type === 'radio') {
            // Single choice question
            inputs.forEach(input => {
                input.checked = input.value === value;
            });
        } else {
            // Text, number, range inputs
            firstInput.value = value || '';
            
            // Update range display if needed
            if (firstInput.type === 'range') {
                const valueSpan = firstInput.closest('.question-container').querySelector('.range-value');
                if (valueSpan) {
                    valueSpan.textContent = value || firstInput.min;
                }
            }
        }
    }
    
    validateQuestion(questionId) {
        const validator = this.validators.get(questionId);
        if (validator) {
            const value = this.getQuestionValue(questionId);
            return validator(value);
        }
        return { isValid: true };
    }
    
    showValidationError(questionId, message) {
        const container = document.querySelector(`[data-question-id="${questionId}"]`);
        if (container) {
            const validationMessage = container.querySelector('.validation-message');
            if (validationMessage) {
                validationMessage.textContent = message;
                container.classList.add('error');
            }
        }
    }
    
    clearValidationError(questionId) {
        const container = document.querySelector(`[data-question-id="${questionId}"]`);
        if (container) {
            const validationMessage = container.querySelector('.validation-message');
            if (validationMessage) {
                validationMessage.textContent = '';
                container.classList.remove('error');
            }
        }
    }
    
    onQuestionChange(questionId, handler) {
        this.changeHandlers.set(questionId, handler);
    }
    
    setQuestionValidator(questionId, validator) {
        this.validators.set(questionId, validator);
    }
}

// Response Validator Component
class ResponseValidator {
    constructor() {
        this.rules = new Map();
    }
    
    addRule(questionId, rule) {
        if (!this.rules.has(questionId)) {
            this.rules.set(questionId, []);
        }
        this.rules.get(questionId).push(rule);
    }
    
    validate(questionId, value, question = null) {
        const rules = this.rules.get(questionId) || [];
        
        // Add default validation rules based on question
        if (question) {
            const defaultRules = this.getDefaultRules(question);
            rules.unshift(...defaultRules);
        }
        
        for (const rule of rules) {
            const result = rule(value, question);
            if (!result.isValid) {
                return result;
            }
        }
        
        return { isValid: true };
    }
    
    getDefaultRules(question) {
        const rules = [];
        
        // Required field validation
        if (question.is_required) {
            rules.push((value) => {
                if (!value || (Array.isArray(value) && value.length === 0)) {
                    return { isValid: false, message: 'This field is required.' };
                }
                return { isValid: true };
            });
        }
        
        // Type-specific validation
        const validationRules = question.validation_rules || {};
        
        if (question.question_type === 'NUMBER') {
            rules.push((value) => {
                if (value && isNaN(parseFloat(value))) {
                    return { isValid: false, message: 'Please enter a valid number.' };
                }
                
                const numValue = parseFloat(value);
                if (validationRules.min !== undefined && numValue < validationRules.min) {
                    return { isValid: false, message: `Value must be at least ${validationRules.min}.` };
                }
                if (validationRules.max !== undefined && numValue > validationRules.max) {
                    return { isValid: false, message: `Value must be no more than ${validationRules.max}.` };
                }
                
                return { isValid: true };
            });
        }
        
        if (question.question_type === 'TEXT') {
            rules.push((value) => {
                if (value) {
                    if (validationRules.minLength && value.length < validationRules.minLength) {
                        return { isValid: false, message: `Must be at least ${validationRules.minLength} characters.` };
                    }
                    if (validationRules.maxLength && value.length > validationRules.maxLength) {
                        return { isValid: false, message: `Must be no more than ${validationRules.maxLength} characters.` };
                    }
                    if (validationRules.pattern) {
                        const regex = new RegExp(validationRules.pattern);
                        if (!regex.test(value)) {
                            return { isValid: false, message: validationRules.patternMessage || 'Invalid format.' };
                        }
                    }
                }
                return { isValid: true };
            });
        }
        
        return rules;
    }
}

// Auto-save Manager
class AutoSaveManager {
    constructor(saveCallback, options = {}) {
        this.saveCallback = saveCallback;
        this.options = {
            interval: 30000, // 30 seconds
            debounceDelay: 2000, // 2 seconds
            showIndicator: true,
            ...options
        };
        
        this.pendingChanges = new Set();
        this.saveTimer = null;
        this.intervalTimer = null;
        
        this.debouncedSave = SurveyUtils.debounce(
            this.performSave.bind(this), 
            this.options.debounceDelay
        );
        
        this.startPeriodicSave();
    }
    
    markChanged(key) {
        this.pendingChanges.add(key);
        this.debouncedSave();
    }
    
    async performSave() {
        if (this.pendingChanges.size === 0) return;
        
        try {
            const changes = Array.from(this.pendingChanges);
            await this.saveCallback(changes);
            
            // Clear pending changes only if save was successful
            this.pendingChanges.clear();
            
            if (this.options.showIndicator) {
                this.showSaveIndicator();
            }
            
        } catch (error) {
            console.error('Auto-save failed:', error);
            // Keep pending changes for retry
        }
    }
    
    startPeriodicSave() {
        this.intervalTimer = setInterval(() => {
            if (this.pendingChanges.size > 0) {
                this.performSave();
            }
        }, this.options.interval);
    }
    
    stopPeriodicSave() {
        if (this.intervalTimer) {
            clearInterval(this.intervalTimer);
            this.intervalTimer = null;
        }
    }
    
    showSaveIndicator() {
        let indicator = document.getElementById('autoSaveIndicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'autoSaveIndicator';
            indicator.className = 'auto-save-indicator';
            indicator.innerHTML = '<i class="fas fa-save"></i><span>Saved</span>';
            document.body.appendChild(indicator);
        }
        
        indicator.classList.add('show');
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }
    
    destroy() {
        this.stopPeriodicSave();
        if (this.saveTimer) {
            clearTimeout(this.saveTimer);
        }
    }
}

// Export components for global use
window.ProgressTracker = ProgressTracker;
window.QuestionRenderer = QuestionRenderer;
window.ResponseValidator = ResponseValidator;
window.AutoSaveManager = AutoSaveManager;

// Initialize common functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                SurveyUtils.scrollToElement(target, 80);
            }
        });
    });
    
    // Add keyboard navigation support
    document.addEventListener('keydown', function(e) {
        // Escape key to close modals or cancel operations
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show, .overlay.show');
            modals.forEach(modal => {
                modal.classList.remove('show');
            });
        }
    });
    
    // Add focus management for accessibility
    const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const focusable = Array.from(document.querySelectorAll(focusableElements))
                .filter(el => !el.disabled && el.offsetParent !== null);
            
            const firstFocusable = focusable[0];
            const lastFocusable = focusable[focusable.length - 1];
            
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    lastFocusable.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    firstFocusable.focus();
                    e.preventDefault();
                }
            }
        }
    });
});