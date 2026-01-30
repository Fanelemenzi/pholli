// Policy Features Admin JavaScript

(function($) {
    'use strict';
    
    // Initialize when DOM is ready
    $(document).ready(function() {
        initializePolicyFeaturesAdmin();
    });
    
    function initializePolicyFeaturesAdmin() {
        // Set up insurance type change handler
        setupInsuranceTypeHandler();
        
        // Initialize field visibility based on current selection
        initializeFieldVisibility();
        
        // Set up form validation
        setupFormValidation();
        
        // Add feature summary
        addFeatureSummary();
        
        // Set up help text toggles
        setupHelpTextToggles();
    }
    
    function setupInsuranceTypeHandler() {
        const insuranceTypeField = $('#id_insurance_type');
        
        if (insuranceTypeField.length) {
            insuranceTypeField.on('change', function() {
                const selectedType = $(this).val();
                toggleFeatureFields(selectedType);
                updateRequiredFields(selectedType);
                updateFeatureSummary(selectedType);
            });
        }
    }
    
    function initializeFieldVisibility() {
        const insuranceTypeField = $('#id_insurance_type');
        if (insuranceTypeField.length) {
            const currentType = insuranceTypeField.val();
            if (currentType) {
                toggleFeatureFields(currentType);
                updateRequiredFields(currentType);
            }
        }
    }
    
    // Global function for insurance type changes
    window.toggleFeatureFields = function(insuranceType) {
        // Hide all fields first
        $('.health-field, .funeral-field').closest('.form-row').addClass('field-hidden');
        
        if (insuranceType === 'HEALTH') {
            // Show health fields
            $('.health-field').closest('.form-row').removeClass('field-hidden').addClass('field-visible');
            
            // Update fieldset styling
            updateFieldsetStyling('health');
            
        } else if (insuranceType === 'FUNERAL') {
            // Show funeral fields
            $('.funeral-field').closest('.form-row').removeClass('field-hidden').addClass('field-visible');
            
            // Update fieldset styling
            updateFieldsetStyling('funeral');
        }
        
        // Update form layout
        updateFormLayout();
    };
    
    function updateRequiredFields(insuranceType) {
        // Remove all required indicators first
        $('.required-field').removeClass('required-field');
        
        if (insuranceType === 'HEALTH') {
            // Mark health fields as required
            const requiredHealthFields = [
                '#id_annual_limit_family_range',
                '#id_in_hospital_benefit_level',
                '#id_out_hospital_benefit_level'
            ];
            
            requiredHealthFields.forEach(function(fieldId) {
                $(fieldId).closest('.form-row').addClass('required-field');
            });
            
        } else if (insuranceType === 'FUNERAL') {
            // Mark funeral fields as required
            const requiredFuneralFields = [
                '#id_cover_amount_range',
                '#id_funeral_service_type',
                '#id_family_coverage_type',
                '#id_waiting_period_natural_death'
            ];
            
            requiredFuneralFields.forEach(function(fieldId) {
                $(fieldId).closest('.form-row').addClass('required-field');
            });
        }
    }
    
    function updateFieldsetStyling(insuranceType) {
        // Remove existing styling
        $('.health-fieldset, .funeral-fieldset').removeClass('health-fieldset funeral-fieldset');
        
        // Add appropriate styling
        if (insuranceType === 'health') {
            $('.field-visible').closest('fieldset').addClass('health-fieldset');
        } else if (insuranceType === 'funeral') {
            $('.field-visible').closest('fieldset').addClass('funeral-fieldset');
        }
    }
    
    function updateFormLayout() {
        // Reorganize form layout for better UX
        const visibleFields = $('.field-visible');
        
        if (visibleFields.length > 0) {
            // Group related fields together
            groupRelatedFields();
        }
    }
    
    function groupRelatedFields() {
        // This function can be expanded to group related fields
        // For now, it just ensures proper spacing
        $('.field-visible').css('margin-bottom', '15px');
    }
    
    function setupFormValidation() {
        // Add real-time validation
        $('form').on('submit', function(e) {
            const insuranceType = $('#id_insurance_type').val();
            
            if (!validateRequiredFields(insuranceType)) {
                e.preventDefault();
                showValidationErrors();
                return false;
            }
        });
        
        // Add field-level validation
        setupFieldValidation();
    }
    
    function validateRequiredFields(insuranceType) {
        let isValid = true;
        const errors = [];
        
        if (insuranceType === 'HEALTH') {
            const requiredFields = {
                'annual_limit_family_range': 'Annual limit family range',
                'in_hospital_benefit_level': 'In-hospital benefit level',
                'out_hospital_benefit_level': 'Out-of-hospital benefit level'
            };
            
            Object.keys(requiredFields).forEach(function(fieldName) {
                const field = $('#id_' + fieldName);
                if (field.length && !field.val()) {
                    isValid = false;
                    errors.push(requiredFields[fieldName] + ' is required for health policies.');
                }
            });
            
        } else if (insuranceType === 'FUNERAL') {
            const requiredFields = {
                'cover_amount_range': 'Cover amount range',
                'funeral_service_type': 'Funeral service type',
                'family_coverage_type': 'Family coverage type',
                'waiting_period_natural_death': 'Waiting period for natural death'
            };
            
            Object.keys(requiredFields).forEach(function(fieldName) {
                const field = $('#id_' + fieldName);
                if (field.length && !field.val()) {
                    isValid = false;
                    errors.push(requiredFields[fieldName] + ' is required for funeral policies.');
                }
            });
        }
        
        // Store errors for display
        window.validationErrors = errors;
        return isValid;
    }
    
    function showValidationErrors() {
        if (window.validationErrors && window.validationErrors.length > 0) {
            let errorHtml = '<div class="errorlist"><ul>';
            window.validationErrors.forEach(function(error) {
                errorHtml += '<li>' + error + '</li>';
            });
            errorHtml += '</ul></div>';
            
            // Show errors at the top of the form
            $('.form-row').first().before(errorHtml);
            
            // Scroll to top
            $('html, body').animate({scrollTop: 0}, 500);
        }
    }
    
    function setupFieldValidation() {
        // Validate grocery benefit amount when grocery benefit is checked
        $('#id_grocery_benefit').on('change', function() {
            const groceryBenefitAmount = $('#id_grocery_benefit_amount');
            if ($(this).is(':checked')) {
                groceryBenefitAmount.prop('required', true);
                groceryBenefitAmount.closest('.form-row').addClass('required-field');
            } else {
                groceryBenefitAmount.prop('required', false);
                groceryBenefitAmount.closest('.form-row').removeClass('required-field');
            }
        });
        
        // Validate numeric fields
        $('input[type="number"]').on('blur', function() {
            const value = parseFloat($(this).val());
            if (value < 0) {
                $(this).addClass('error');
                $(this).after('<span class="error-message">Value must be positive</span>');
            } else {
                $(this).removeClass('error');
                $(this).siblings('.error-message').remove();
            }
        });
    }
    
    function addFeatureSummary() {
        // Add a summary box showing configured features
        const summaryHtml = `
            <div id="feature-summary" class="feature-summary">
                <h4>Feature Configuration Summary</h4>
                <div id="summary-content">
                    <p>Select an insurance type to see feature summary.</p>
                </div>
            </div>
        `;
        
        $('.form-row').first().before(summaryHtml);
        
        // Update summary when fields change
        $('select, input[type="checkbox"]').on('change', function() {
            updateFeatureSummary($('#id_insurance_type').val());
        });
    }
    
    function updateFeatureSummary(insuranceType) {
        const summaryContent = $('#summary-content');
        
        if (!insuranceType) {
            summaryContent.html('<p>Select an insurance type to see feature summary.</p>');
            return;
        }
        
        let summary = '<ul>';
        
        if (insuranceType === 'HEALTH') {
            const healthFeatures = [
                {field: 'annual_limit_family_range', label: 'Family Annual Limit'},
                {field: 'in_hospital_benefit_level', label: 'Hospital Benefit'},
                {field: 'out_hospital_benefit_level', label: 'Out-of-Hospital Benefit'},
                {field: 'chronic_medication_availability', label: 'Chronic Medication', type: 'checkbox'},
                {field: 'ambulance_coverage', label: 'Ambulance Coverage', type: 'checkbox'}
            ];
            
            healthFeatures.forEach(function(feature) {
                const field = $('#id_' + feature.field);
                let value = '';
                
                if (feature.type === 'checkbox') {
                    value = field.is(':checked') ? 'Yes' : 'No';
                } else {
                    value = field.find('option:selected').text() || field.val() || 'Not set';
                }
                
                summary += `<li><strong>${feature.label}:</strong> ${value}</li>`;
            });
            
        } else if (insuranceType === 'FUNERAL') {
            const funeralFeatures = [
                {field: 'cover_amount_range', label: 'Cover Amount Range'},
                {field: 'funeral_service_type', label: 'Service Type'},
                {field: 'family_coverage_type', label: 'Family Coverage'},
                {field: 'waiting_period_natural_death', label: 'Waiting Period'},
                {field: 'includes_coffin', label: 'Includes Coffin', type: 'checkbox'},
                {field: 'includes_catering', label: 'Includes Catering', type: 'checkbox'},
                {field: 'repatriation_covered', label: 'Repatriation', type: 'checkbox'}
            ];
            
            funeralFeatures.forEach(function(feature) {
                const field = $('#id_' + feature.field);
                let value = '';
                
                if (feature.type === 'checkbox') {
                    value = field.is(':checked') ? 'Yes' : 'No';
                } else {
                    value = field.find('option:selected').text() || field.val() || 'Not set';
                }
                
                summary += `<li><strong>${feature.label}:</strong> ${value}</li>`;
            });
        }
        
        summary += '</ul>';
        summaryContent.html(summary);
    }
    
    function setupHelpTextToggles() {
        // Add toggle buttons for help text
        $('.help').each(function() {
            const helpText = $(this);
            const toggleButton = $('<button type="button" class="help-toggle">?</button>');
            
            helpText.hide();
            helpText.before(toggleButton);
            
            toggleButton.on('click', function() {
                helpText.toggle();
                $(this).toggleClass('active');
            });
        });
    }
    
    // Utility functions
    function showLoadingOverlay() {
        const overlay = $('<div class="loading-overlay"><div class="loading-spinner"></div></div>');
        $('body').append(overlay);
    }
    
    function hideLoadingOverlay() {
        $('.loading-overlay').remove();
    }
    
    function showSuccessMessage(message) {
        const successDiv = $('<div class="success-message">' + message + '</div>');
        $('.form-row').first().before(successDiv);
        
        setTimeout(function() {
            successDiv.fadeOut();
        }, 3000);
    }
    
    function showWarningMessage(message) {
        const warningDiv = $('<div class="warning-message">' + message + '</div>');
        $('.form-row').first().before(warningDiv);
        
        setTimeout(function() {
            warningDiv.fadeOut();
        }, 5000);
    }
    
})(django.jQuery);
                '