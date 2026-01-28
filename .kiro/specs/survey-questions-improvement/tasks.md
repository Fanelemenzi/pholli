# Implementation Plan

- [x] 1. Update SimpleSurvey model with new benefit level and range fields





  - Add new choice fields for in_hospital_benefit_level and out_hospital_benefit_level
  - Add new choice fields for annual_limit_family_range and annual_limit_member_range
  - Remove currently_on_medical_aid field from model
  - Create Django migration for schema changes
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2_

- [x] 2. Create data migration to convert existing binary responses












  - Write migration script to convert wants_in_hospital_benefit boolean to benefit levels
  - Write migration script to convert wants_out_hospital_benefit boolean to benefit levels
  - Remove existing currently_on_medical_aid data
  - Handle existing annual limit values by mapping to appropriate ranges
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 3. Update SimpleSurveyForm with new field types and validation





  - Replace binary benefit fields with radio button choices for benefit levels
  - Replace annual limit number inputs with range selection dropdowns
  - Remove currently_on_medical_aid field from form
  - Add form validation for new choice fields
  - Update form widgets with appropriate CSS classes and descriptions
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1_

- [x] 4. Update HealthSurveyForm to use new benefit level questions




  - Modify HealthSurveyForm to inherit new field structure from SimpleSurveyForm
  - Remove medical aid status field from health-specific form
  - Update field initialization to use new benefit level choices
  - _Requirements: 1.1, 1.2, 3.1_

- [x] 5. Create benefit level configuration constants








  - Define HOSPITAL_BENEFIT_CHOICES constant with exact options from Docs/benefits.md
  - Define OUT_HOSPITAL_BENEFIT_CHOICES constant with exact options from Docs/benefits.md
  - Define ANNUAL_LIMIT_FAMILY_RANGES constant with range options and descriptions
  - Define ANNUAL_LIMIT_MEMBER_RANGES constant with range options and descriptions
  - _Requirements: 1.2, 1.3, 2.2, 2.3_

- [x] 6. Update survey templates to display new question types




  - Modify feature_survey_form.html to render benefit level radio buttons
  - Add range selection dropdowns with helpful tooltips for annual limits
  - Remove medical aid status question from templates
  - Add JavaScript for range selection guidance and tooltips
  - Style new question types consistently with existing design
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.5, 3.1_

- [x] 7. Update SimpleSurvey model methods for new field structure





  - Modify get_preferences_dict() method to return benefit levels instead of boolean values
  - Update clean() method validation to work with new choice fields
  - Update is_complete() method to check new required fields
  - Update get_missing_fields() method for new field structure
  - _Requirements: 1.5, 3.3, 6.5_

- [x] 8. Update comparison engine to handle benefit levels and ranges




  - Modify policy matching logic to work with benefit level choices instead of boolean values
  - Update annual limit matching to work with range selections instead of exact values
  - Remove currently_on_medical_aid from comparison criteria processing
  - Update scoring algorithms to handle benefit level compatibility
  - _Requirements: 1.5, 2.6, 3.3, 4.1, 4.2_

- [x] 9. Update SimpleSurveyComparisonAdapter for new response format








  - Modify generate_quotations() method to process benefit level responses
  - Update criteria conversion to map benefit levels to policy features
  - Update range processing to convert user ranges to policy matching criteria
  - Remove medical aid status from adapter processing
  - _Requirements: 1.5, 2.6, 3.3_

- [x] 10. Update policy comparison results display




  - Modify feature_survey_results.html to show benefit level matches
  - Update policy compatibility explanations to reference benefit levels
  - Add range-based scoring explanations in comparison results
  - Remove medical aid status references from result templates
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 11. Create unit tests for new model fields and validation




  - Write tests for SimpleSurvey model with new choice fields
  - Test form validation with benefit level and range selections
  - Test data migration scripts with sample data
  - Test model methods with new field structure
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 6.1, 6.2_

- [ ] 12. Create integration tests for survey flow with new questions
  - Test complete survey submission with benefit level selections
  - Test range selection functionality and validation
  - Test survey completion detection with new required fields
  - Test policy matching with benefit levels and ranges
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 4.1, 4.2_

- [x] 13. Update admin interface for new question management





  - Add admin interface for managing benefit level choices
  - Add admin interface for managing annual limit ranges
  - Update survey response admin to display new field types
  - Add validation for range option management
  - _Requirements: 5.1, 5.2, 5.4_

- [x] 14. Create response migration handling for existing users









  - Implement logic to handle users with existing survey responses
  - Create user interface for updating responses to new question format
  - Test mixed old/new response handling in comparison engine
  - Implement graceful fallback for unmigrated responses
  - _Requirements: 6.3, 6.4, 6.5, 6.6_

- [x] 15. Update survey analytics and reporting








  - Modify survey analytics to track benefit level selections
  - Update completion rate tracking for new question structure
  - Add reporting for range selection patterns
  - Remove medical aid status from analytics dashboards
  - _Requirements: 5.5, 3.6_