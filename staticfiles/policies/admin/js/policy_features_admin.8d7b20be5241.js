/**
 * JavaScript for PolicyFeatures admin interface
 * Handles dynamic field visibility based on insurance type
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Initialize field visibility on page load
        toggleFieldsByInsuranceType();
        
        // Handle insurance type changes
        $('#id_insurance_type').change(function() {
            toggleFieldsByInsuranceType();
        });
        
        // Add visual indicators for required fields
        addRequiredFieldIndicators();
        
        // Add help text for better UX
        addDynamicHelpText();
    });
    
    function toggleFieldsByInsuranceType() {
        var insuranceType = $('#id_insurance_type').val();
        
        // Health policy fields
        var healthFields = [
            'annual_limit_per_member',
            'monthly_household_income',
            'in_hospital_benefit',
            'out_hospital_benefit',
            'chronic_medication_availability'
        ];
        
        // Funeral policy fields
        var funeralFields = [
            'cover_amount',
            'marital_status_requirement',
            'gender_requirement',
            'monthly_net_income'
        ];
        
        if (insuranceType === 'HEALTH') {
            // Show health fields, hide funeral fields
            showFields(healthFields);
            hideFields(funeralFields);
            
            // Update fieldset titles
            updateFieldsetTitle('Health Policy Features', true);
            updateFieldsetTitle('Funeral Policy Features', false);
            
        } else if (insuranceType === 'FUNERAL') {
            // Show funeral fields, hide health fields
            showFields(funeralFields);
            hideFields(healthFields);
            
            // Update fieldset titles
            updateFieldsetTitle('Health Policy Features', false);
            updateFieldsetTitle('Funeral Policy Features', true);
            
        } else {
            // No insurance type selected, show all fields but mark as optional
            showFields(healthFields.concat(funeralFields));
            updateFieldsetTitle('Health Policy Features', false);
            updateFieldsetTitle('Funeral Policy Features', false);
        }
    }
    
    function showFields(fieldNames) {
        fieldNames.forEach(function(fieldName) {
            var fieldRow = $('.field-' + fieldName);
            fieldRow.show();
            fieldRow.removeClass('hidden-field');
            fieldRow.addClass('visible-field');
        });
    }
    
    function hideFields(fieldNames) {
        fieldNames.forEach(function(fieldName) {
            var fieldRow = $('.field-' + fieldName);
            fieldRow.hide();
            fieldRow.removeClass('visible-field');
            fieldRow.addClass('hidden-field');
            
            // Clear values of hidden fields to prevent validation issues
            var input = fieldRow.find('input, select');
            if (input.length > 0) {
                if (input.attr('type') === 'checkbox') {
                    input.prop('checked', false);
                } else {
                    input.val('');
                }
            }
        });
    }
    
    function updateFieldsetTitle(fieldsetTitle, isActive) {
        var fieldset = $('fieldset').filter(function() {
            return $(this).find('h2').text().indexOf(fieldsetTitle) !== -1;
        });
        
        var header = fieldset.find('h2');
        if (isActive) {
            header.css({
                'color': '#28a745',
                'font-weight': 'bold'
            });
            header.prepend('<span style="color: #28a745;">✓ </span>');
            fieldset.removeClass('collapsed');
        } else {
            header.css({
                'color': '#6c757d',
                'font-weight': 'normal'
            });
            header.find('span').remove();
            if (!fieldset.hasClass('collapsed')) {
                fieldset.addClass('collapsed');
            }
        }
    }
    
    function addRequiredFieldIndicators() {
        // Add asterisk to required fields based on insurance type
        $('#id_insurance_type').change(function() {
            var insuranceType = $(this).val();
            
            // Remove all existing required indicators
            $('.required-indicator').remove();
            
            var requiredFields = [];
            if (insuranceType === 'HEALTH') {
                requiredFields = [
                    'annual_limit_per_member',
                    'monthly_household_income',
                    'in_hospital_benefit',
                    'out_hospital_benefit',
                    'chronic_medication_availability'
                ];
            } else if (insuranceType === 'FUNERAL') {
                requiredFields = [
                    'cover_amount',
                    'marital_status_requirement',
                    'gender_requirement',
                    'monthly_net_income'
                ];
            }
            
            requiredFields.forEach(function(fieldName) {
                var label = $('.field-' + fieldName + ' label');
                if (label.length > 0 && label.find('.required-indicator').length === 0) {
                    label.append(' <span class="required-indicator" style="color: red;">*</span>');
                }
            });
        });
    }
    
    function addDynamicHelpText() {
        // Add contextual help text
        var helpTexts = {
            'HEALTH': {
                'general': 'Fill in all health-related features. Funeral features will be automatically cleared.',
                'annual_limit_per_member': 'Maximum amount covered per family member per year',
                'monthly_household_income': 'Minimum monthly household income required for eligibility',
                'in_hospital_benefit': 'Check if policy covers in-hospital medical expenses',
                'out_hospital_benefit': 'Check if policy covers out-of-hospital medical expenses',
                'chronic_medication_availability': 'Check if policy covers chronic medication costs'
            },
            'FUNERAL': {
                'general': 'Fill in all funeral-related features. Health features will be automatically cleared.',
                'cover_amount': 'Total amount covered for funeral expenses',
                'marital_status_requirement': 'Required marital status for policy eligibility',
                'gender_requirement': 'Required gender for policy eligibility (if any)',
                'monthly_net_income': 'Minimum monthly net income required for eligibility'
            }
        };
        
        $('#id_insurance_type').change(function() {
            var insuranceType = $(this).val();
            var texts = helpTexts[insuranceType];
            
            if (texts) {
                // Add general help text
                var generalHelp = $('#insurance-type-help');
                if (generalHelp.length === 0) {
                    $('#id_insurance_type').after(
                        '<div id="insurance-type-help" class="help" style="margin-top: 5px; color: #666; font-style: italic;"></div>'
                    );
                    generalHelp = $('#insurance-type-help');
                }
                generalHelp.text(texts.general);
                
                // Update field-specific help texts
                Object.keys(texts).forEach(function(fieldName) {
                    if (fieldName !== 'general') {
                        var helpElement = $('.field-' + fieldName + ' .help');
                        if (helpElement.length > 0) {
                            helpElement.text(texts[fieldName]);
                        }
                    }
                });
            }
        });
    }
    
})(django.jQuery);