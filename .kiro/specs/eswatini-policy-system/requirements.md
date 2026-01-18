# Requirements Document

## Introduction

This feature involves rebuilding the policies, comparison, and survey applications to be specifically designed around common health/medical and funeral insurance policy features in Eswatini. The system will be restructured to use a feature-based approach where policies are defined by standardized features specific to each insurance type, surveys collect user preferences for these features, and comparisons are made based on feature matching rather than generic criteria.

## Requirements

### Requirement 1

**User Story:** As a policy administrator, I want to define health/medical and funeral policies using their respective standardized Eswatini insurance features, so that all policies within each category can be consistently compared and matched against user needs.

#### Acceptance Criteria

1. WHEN creating a health/medical policy THEN the system SHALL require specification of annual limit per member per family
2. WHEN creating a health/medical policy THEN the system SHALL require specification of income eligibility ranges
3. WHEN creating a health/medical policy THEN the system SHALL require specification of in-hospital benefit availability (yes/no)
4. WHEN creating a health/medical policy THEN the system SHALL require specification of out-of-hospital benefit availability (yes/no)
5. WHEN creating a health/medical policy THEN the system SHALL require specification of chronic medication coverage availability (yes/no)
6. WHEN creating a funeral policy THEN the system SHALL require specification of coverage amount per family member
7. WHEN creating a funeral policy THEN the system SHALL require specification of income eligibility ranges
8. WHEN creating a funeral policy THEN the system SHALL require specification of waiting period details
9. WHEN creating a funeral policy THEN the system SHALL require specification of additional benefits (repatriation, tombstone, etc.)
10. WHEN saving any policy THEN the system SHALL validate that all required features for that policy type are specified
11. WHEN displaying policies THEN the system SHALL show feature values in a standardized format appropriate to the policy type

### Requirement 2

**User Story:** As a user seeking health/medical or funeral insurance, I want to answer questions about my needs based on the specific features of each insurance type, so that I can receive accurate policy recommendations tailored to the type of coverage I'm seeking.

#### Acceptance Criteria

1. WHEN starting a health/medical survey THEN the system SHALL ask about desired annual coverage limit per family member
2. WHEN completing a health/medical survey THEN the system SHALL ask about monthly household income
3. WHEN answering health survey questions THEN the system SHALL ask about importance of in-hospital benefits
4. WHEN answering health survey questions THEN the system SHALL ask about importance of out-of-hospital benefits  
5. WHEN completing a health survey THEN the system SHALL ask about need for chronic medication coverage
6. WHEN starting a funeral survey THEN the system SHALL ask about desired coverage amount per family member
7. WHEN completing a funeral survey THEN the system SHALL ask about monthly household income
8. WHEN answering funeral survey questions THEN the system SHALL ask about acceptable waiting periods
9. WHEN completing funeral survey THEN the system SHALL ask about importance of additional benefits (repatriation, tombstone, etc.)
10. WHEN submitting survey responses THEN the system SHALL validate all required questions for that insurance type are answered
11. WHEN survey is complete THEN the system SHALL store responses for policy matching within the appropriate category

### Requirement 3

**User Story:** As a user who has completed a health/medical or funeral survey, I want to see policies of the appropriate type ranked by how well they match my stated feature preferences, so that I can easily identify the most suitable options within my chosen insurance category.

#### Acceptance Criteria

1. WHEN health survey is completed THEN the system SHALL match user preferences against health policy features only
2. WHEN funeral survey is completed THEN the system SHALL match user preferences against funeral policy features only
3. WHEN generating matches THEN the system SHALL calculate compatibility scores based on feature alignment within the policy category
4. WHEN displaying results THEN the system SHALL rank policies by compatibility score (highest first) within the selected insurance type
5. WHEN showing policy matches THEN the system SHALL highlight which features align with user preferences for that insurance type
6. WHEN displaying mismatches THEN the system SHALL clearly indicate where policies don't meet user requirements within the category
7. WHEN no perfect matches exist THEN the system SHALL show best available options with explanations specific to the insurance type

### Requirement 4

**User Story:** As a user comparing health/medical or funeral policies, I want to see side-by-side feature comparisons specific to the insurance type, so that I can understand the differences between policies in terms of the standardized features relevant to that category.

#### Acceptance Criteria

1. WHEN comparing health policies THEN the system SHALL display health-specific features (annual limits, income requirements, hospital benefits, chronic medication coverage) in a standardized comparison table
2. WHEN comparing funeral policies THEN the system SHALL display funeral-specific features (coverage amounts, income requirements, waiting periods, additional benefits) in a standardized comparison table
3. WHEN viewing comparisons THEN the system SHALL show only features relevant to the selected insurance type
4. WHEN comparing features THEN the system SHALL highlight differences between policies using visual indicators appropriate to the feature type
5. WHEN a feature matches user preferences THEN the system SHALL mark it as favorable within the insurance category context
6. WHEN a feature doesn't match user needs THEN the system SHALL mark it as unfavorable with category-specific explanations
7. WHEN viewing comparison THEN the system SHALL allow filtering by specific features relevant to the insurance type

### Requirement 5

**User Story:** As a policy administrator, I want to manage the standardized feature definitions for both health/medical and funeral insurance types, so that I can ensure consistency across all policies within each category and adapt to changes in Eswatini insurance standards.

#### Acceptance Criteria

1. WHEN accessing admin panel THEN the system SHALL provide separate interfaces to manage health and funeral feature definitions
2. WHEN updating feature definitions THEN the system SHALL maintain backward compatibility with existing policies within each category
3. WHEN adding new features THEN the system SHALL allow specification of data types, validation rules, and insurance type association
4. WHEN modifying health features THEN the system SHALL update all related health survey questions automatically
5. WHEN modifying funeral features THEN the system SHALL update all related funeral survey questions automatically
6. WHEN removing features THEN the system SHALL handle existing policy data gracefully within the affected insurance category
7. WHEN feature changes are made THEN the system SHALL notify administrators of affected policies by insurance type

### Requirement 6

**User Story:** As a system user, I want the feature-based system to work seamlessly across health/medical and funeral policies, surveys, and comparisons, so that I have a consistent experience within each insurance type regardless of which part of the system I'm using.

#### Acceptance Criteria

1. WHEN a health policy feature is updated THEN the system SHALL reflect changes in health surveys and comparisons immediately
2. WHEN a funeral policy feature is updated THEN the system SHALL reflect changes in funeral surveys and comparisons immediately
3. WHEN health survey questions are modified THEN the system SHALL maintain consistency with health policy feature definitions
4. WHEN funeral survey questions are modified THEN the system SHALL maintain consistency with funeral policy feature definitions
5. WHEN comparison criteria change THEN the system SHALL update matching algorithms accordingly for the affected insurance type
6. WHEN viewing any part of the system THEN the system SHALL use consistent terminology for features within each insurance category
7. WHEN data is entered in one module THEN the system SHALL validate against the same rules used in other modules for that insurance type
8. WHEN features are displayed THEN the system SHALL use consistent formatting across all interfaces within each insurance category

### Requirement 8

**User Story:** As a user interested in specific benefits within health/medical or funeral insurance, I want to filter and sort policies based on benefit availability and match ranking specific to my chosen insurance type, so that I can focus on policies that offer the coverage I need and see the best matches first.

#### Acceptance Criteria

1. WHEN searching for health policies THEN the system SHALL allow filtering by in-hospital benefit availability
2. WHEN filtering health policies THEN the system SHALL allow filtering by out-of-hospital benefit availability
3. WHEN browsing health policies THEN the system SHALL allow filtering by chronic medication coverage
4. WHEN searching for funeral policies THEN the system SHALL allow filtering by additional benefits (repatriation, tombstone, etc.)
5. WHEN filtering funeral policies THEN the system SHALL allow filtering by waiting period ranges
6. WHEN applying filters THEN the system SHALL show only policies that match selected criteria within the insurance type
7. WHEN no policies match filters THEN the system SHALL suggest relaxing specific criteria within the insurance category
8. WHEN viewing filtered results THEN the system SHALL clearly indicate which filters are active for the insurance type
9. WHEN displaying policy results THEN the system SHALL sort policies by best match ranking (highest compatibility score first)
10. WHEN multiple policies have similar rankings THEN the system SHALL provide secondary sorting options (premium, coverage amount, etc.)

### Requirement 7

**User Story:** As a user exploring insurance options, I want to clearly distinguish between health/medical and funeral insurance throughout the system, so that I can focus on the type of coverage I'm seeking without confusion.

#### Acceptance Criteria

1. WHEN accessing the system THEN the system SHALL provide clear navigation between health and funeral insurance sections
2. WHEN viewing policy listings THEN the system SHALL clearly separate health and funeral policies
3. WHEN starting a survey THEN the system SHALL require selection of insurance type (health or funeral) before proceeding
4. WHEN comparing policies THEN the system SHALL prevent comparison between different insurance types
5. WHEN viewing search results THEN the system SHALL clearly indicate the insurance type for each policy
6. WHEN switching between insurance types THEN the system SHALL maintain separate user preferences and history
7. WHEN displaying features THEN the system SHALL use terminology appropriate to the selected insurance type