// Policy Features Inline JavaScript
(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Function to update field visibility based on insurance type
        function updateFieldVisibility() {
            var insuranceType = $('#id_policy_features-0-insurance_type').val();
            var $healthSection = $('.health-features');
            var $funeralSection = $('.funeral-features');
            var $form = $('.inline-group');
            
            // Remove existing classes
            $form.removeClass('insurance-type-health insurance-type-funeral');
            
            if (insuranceType === 'HEALTH') {
                $form.addClass('insurance-type-health');
                $healthSection.show().css('opacity', '1');
                $funeralSection.show().css('opacity', '0.5');
                
                // Add visual indicators
                $healthSection.find('h2').prepend('<span style="color: #28a745; margin-right: 8px;">💊</span>');
                $funeralSection.find('h2').prepend('<span style="color: #ccc; margin-right: 8px;">⚱️</span>');
                
                // Show helpful message
                showInsuranceTypeMessage('health');
                
            } else if (insuranceType === 'FUNERAL') {
                $form.addClass('insurance-type-funeral');
                $funeralSection.show().css('opacity', '1');
                $healthSection.show().css('opacity', '0.5');
                
                // Add visual indicators
                $funeralSection.find('h2').prepend('<span style="color: #6f42c1; margin-right: 8px;">⚱️</span>');
                $healthSection.find('h2').prepend('<span style="color: #ccc; margin-right: 8px;">💊</span>');
                
                // Show helpful message
                showInsuranceTypeMessage('funeral');
                
            } else {
                // No insurance type selected - show both sections normally
                $healthSection.show().css('opacity', '1');
                $funeralSection.show().css('opacity', '1');
                
                // Remove icons
                $healthSection.find('h2 span').remove();
                $funeralSection.find('h2 span').remove();
                
                // Show selection message
                showInsuranceTypeMessage('none');
            }
        }
        
        // Function to show contextual messages
        function showInsuranceTypeMessage(type) {
            // Remove existing messages
            $('.insurance-type-message').remove();
            
            var message = '';
            var messageClass = 'info';
            
            switch(type) {
                case 'health':
                    message = '<strong>Health Insurance Selected:</strong> Focus on the Health Policy Features section (highlighted in green). The Funeral Policy Features section is dimmed and should be left empty.';
                    messageClass = 'success';
                    break;
                case 'funeral':
                    message = '<strong>Funeral Insurance Selected:</strong> Focus on the Funeral Policy Features section (highlighted in purple). The Health Policy Features section is dimmed and should be left empty.';
                    messageClass = 'info';
                    break;
                case 'none':
                    message = '<strong>Please select an Insurance Type first</strong> to see which feature sections are relevant for your policy.';
                    messageClass = 'warning';
                    break;
            }
            
            if (message) {
                var $messageDiv = $('<div class="insurance-type-message alert alert-' + messageClass + '" style="margin: 10px 0; padding: 10px; border-radius: 4px; font-size: 13px;">' + message + '</div>');
                $('.fieldset:first-child').after($messageDiv);
            }
        }
        
        // Function to validate fields based on insurance type
        function validateFields() {
            var insuranceType = $('#id_policy_features-0-insurance_type').val();
            var errors = [];
            
            if (insuranceType === 'HEALTH') {
                // Check if any funeral fields are filled
                var funeralFields = [
                    'cover_amount',
                    'cover_amount_range',
                    'funeral_service_type',
                    'family_coverage_type'
                ];
                
                funeralFields.forEach(function(field) {
                    var $field = $('#id_policy_features-0-' + field);
                    if ($field.val()) {
                        errors.push('Funeral field "' + field + '" should be empty for Health insurance');
                    }
                });
                
            } else if (insuranceType === 'FUNERAL') {
                // Check if any health fields are filled
                var healthFields = [
                    'annual_limit_per_member',
                    'annual_limit_per_family',
                    'annual_limit_family_range',
                    'monthly_household_income'
                ];
                
                healthFields.forEach(function(field) {
                    var $field = $('#id_policy_features-0-' + field);
                    if ($field.val()) {
                        errors.push('Health field "' + field + '" should be empty for Funeral insurance');
                    }
                });
            }
            
            // Display validation errors
            $('.field-validation-error').remove();
            if (errors.length > 0) {
                var errorHtml = '<div class="field-validation-error alert alert-danger" style="margin: 10px 0; padding: 10px; border-radius: 4px; font-size: 13px;"><strong>Validation Errors:</strong><ul>';
                errors.forEach(function(error) {
                    errorHtml += '<li>' + error + '</li>';
                });
                errorHtml += '</ul></div>';
                
                $('.insurance-type-message').after(errorHtml);
            }
        }
        
        // Initialize on page load
        updateFieldVisibility();
        
        // Update when insurance type changes
        $(document).on('change', '#id_policy_features-0-insurance_type', function() {
            updateFieldVisibility();
            validateFields();
        });
        
        // Validate when any field changes
        $(document).on('change', '.inline-group input, .inline-group select', function() {
            setTimeout(validateFields, 100); // Small delay to ensure value is updated
        });
        
        // Add helpful tooltips
        function addTooltips() {
            // Health fields tooltips
            $('#id_policy_features-0-annual_limit_per_member').attr('title', 'Maximum annual coverage amount per individual member');
            $('#id_policy_features-0-annual_limit_per_family').attr('title', 'Maximum annual coverage amount for the entire family');
            $('#id_policy_features-0-in_hospital_benefit_level').attr('title', 'Level of coverage for hospital stays and procedures');
            $('#id_policy_features-0-out_hospital_benefit_level').attr('title', 'Level of coverage for outpatient medical care');
            
            // Funeral fields tooltips
            $('#id_policy_features-0-cover_amount').attr('title', 'Death benefit amount paid to beneficiaries');
            $('#id_policy_features-0-funeral_service_type').attr('title', 'Type of funeral service package included');
            $('#id_policy_features-0-waiting_period_natural_death').attr('title', 'Waiting period before natural death claims are covered');
            $('#id_policy_features-0-waiting_period_accidental_death').attr('title', 'Waiting period before accidental death claims are covered');
        }
        
        addTooltips();
        
        // Add section toggle functionality
        $('.fieldset h2').click(function() {
            var $fieldset = $(this).closest('.fieldset');
            var $content = $fieldset.find('.form-row, .description');
            
            if ($content.is(':visible')) {
                $content.slideUp();
                $(this).addClass('collapsed');
            } else {
                $content.slideDown();
                $(this).removeClass('collapsed');
            }
        });
        
        // Add expand/collapse all functionality
        if ($('.inline-group .fieldset').length > 1) {
            var $toggleAll = $('<button type="button" class="btn btn-sm btn-outline-secondary" style="margin: 10px 0;">Toggle All Sections</button>');
            $('.inline-group').prepend($toggleAll);
            
            $toggleAll.click(function() {
                var $allContent = $('.fieldset .form-row, .fieldset .description');
                if ($allContent.first().is(':visible')) {
                    $allContent.slideUp();
                    $('.fieldset h2').addClass('collapsed');
                } else {
                    $allContent.slideDown();
                    $('.fieldset h2').removeClass('collapsed');
                }
            });
        }
    });
    
})(django.jQuery);