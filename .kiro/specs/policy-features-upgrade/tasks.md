n# Implementation Plan

- [x] 1. Update PolicyFeatures model with new fields and remove deprecated field





  - Add annual_limit_per_family DecimalField to PolicyFeatures model
  - Add currently_on_medical_aid BooleanField to PolicyFeatures model  
  - Add ambulance_coverage BooleanField to PolicyFeatures model
  - Create migration to add new fields with appropriate defaults
  - Create migration to remove net_monthly_income field (deprecated)
  - Update model's __str__ method and get_all_features_dict method to include new fields
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Create new Rewards model in policies app
   




  - Create Rewards model with all specified fields (title, description, reward_type, value, etc.)
  - Define proper relationships with BasePolicy model
  - Add appropriate choices for reward_type field
  - Include proper validation for value and percentage fields
  - Add Meta class with ordering and verbose names
  - Create migration for the new Rewards model
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Update AdditionalFeatures model with coverage_details field





  - Add coverage_details TextField to AdditionalFeatures model
  - Create migration to add the new field
  - Update model's __str__ method if needed
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 4. Update Django admin interface for PolicyFeatures




  - Modify PolicyFeaturesAdmin to include new fields in fieldsets
  - Remove net_monthly_income from admin forms and displays
  - Add currently_on_medical_aid and ambulance_coverage to health policy fieldset
  - Update list_display and list_filter to include new fields where appropriate
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 5. Create Django admin interface for Rewards model












  - Create RewardsAdmin class with appropriate list_display, list_filter, and search_fields
  - Configure fieldsets for organized form display
  - Add inline admin for managing rewards from policy admin page
  - Configure proper ordering and filtering options
  - _Requirements: 3.5, 3.6_


- [ ] 6. Update Django admin interface for AdditionalFeatures




  - Add coverage_details field to AdditionalFeaturesAdmin fieldsets
  - Update form layout to accommodate the new field
  - Ensure proper display in list views if needed
  - _Requirements: 4.4, 4.5_

- [x] 7. Update SimpleSurvey model with new preference fields





  - Add preferred_annual_limit_per_family field to SimpleSurvey model
  - Add currently_on_medical_aid field to SimpleSurvey model
  - Add wants_ambulance_coverage field to SimpleSurvey model
  - Remove net_monthly_income field from SimpleSurvey model
  - Create migrations for field additions and removal
  - Update clean() method to validate new fields for health insurance type
  - Update get_preferences_dict() method to include new fields
  - _Requirements: 2.4, 2.5, 2.6_

- [x] 8. Update SimpleSurveyQuestion data with new survey questions





  - Create management command or data migration to add new survey questions
  - Add question for preferred annual limit per family (health insurance)
  - Add question for current medical aid status (health insurance)
  - Add question for ambulance coverage preference (health insurance)
  - Update or remove questions related to net monthly income
  - Ensure proper ordering and validation rules for new questions
  - _Requirements: 2.4, 2.5, 2.6_

- [x] 9. Update simple_surveys admin interface








  - Update SimpleSurveyAdmin to include new fields in fieldsets
  - Remove net_monthly_income from admin forms and displays
  - Add new fields to health insurance fieldset in admin
  - Update list_display and list_filter as appropriate
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 10. Create benefits viewing functionality in templates





  - Create benefits detail template or modal for displaying comprehensive policy benefits
  - Add "View Benefits Covered" button to policy cards in comparison results
  - Create view function to aggregate and return benefits data (PolicyFeatures, AdditionalFeatures, Rewards)
  - Implement JavaScript/AJAX functionality for showing benefits modal
  - Style benefits display with proper sections for different types of benefits
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 11. Update policy comparison templates to include new fields





  - Update policy card templates to display new PolicyFeatures fields where appropriate
  - Add display logic for annual_limit_per_family, currently_on_medical_aid, and ambulance_coverage
  - Update comparison tables to include new fields in appropriate sections
  - Ensure proper formatting and labeling for new fields
  - _Requirements: 5.5, 5.6_

- [x] 12. Update survey forms and processing logic





  - Update survey form templates to include new question fields
  - Modify survey processing logic to handle new preference fields
  - Update survey validation to ensure new required fields are properly validated
  - Update survey completion logic to account for new fields
  - _Requirements: 2.4, 2.5, 2.6, 6.2_

- [-] 13. Update policy matching algorithms to use new fields



  - Modify comparison engine to include new PolicyFeatures fields in matching logic
  - Update scoring algorithms to account for annual_limit_per_family, medical_aid_status, and ambulance_coverage
  - Ensure proper weighting of new fields in compatibility calculations
  - Update matching explanations to include new field comparisons
  - _Requirements: 6.5, 6.6_

- [ ] 14. Create comprehensive tests for all new functionality
  - Write unit tests for updated PolicyFeatures model including new fields
  - Write unit tests for new Rewards model and its relationships
  - Write unit tests for updated AdditionalFeatures model
  - Write unit tests for updated SimpleSurvey model and validation
  - Write integration tests for admin interface functionality
  - Write integration tests for survey flow with new fields
  - Write integration tests for benefits viewing functionality
  - Write tests for updated matching algorithms
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 15. Update existing data and ensure system consistency
  - Create data migration to populate default values for new fields where appropriate
  - Update any existing survey responses or policy data to work with new structure
  - Verify that all existing functionality continues to work with enhanced models
  - Test backward compatibility with existing API endpoints
  - Ensure proper handling of null/empty values for new fields
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_