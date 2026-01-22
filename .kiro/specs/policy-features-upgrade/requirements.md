# Requirements Document

## Introduction

This feature enhances the existing policy management system by updating policy feature models, adding new functionality for medical aid tracking, ambulance coverage options, rewards management, and improving the user interface for viewing policy benefits. The upgrades focus on expanding the data model to capture more comprehensive policy information and improving the user experience when viewing policy details.

## Requirements

### Requirement 1

**User Story:** As a policy administrator, I want to manage enhanced policy features including annual family limits, medical aid status, and ambulance coverage, so that I can capture more comprehensive policy information for better matching and comparison.

#### Acceptance Criteria

1. WHEN creating or editing a policy THEN the system SHALL allow specification of annual_limit_per_family as a monetary value
2. WHEN managing policy features THEN the system SHALL remove the net_monthly_income field from the policy features model
3. WHEN configuring policy features THEN the system SHALL allow specification of current medical aid status (yes/no)
4. WHEN setting up policy features THEN the system SHALL allow specification of ambulance coverage inclusion (with/without)
5. WHEN saving policy features THEN the system SHALL validate that all new required fields are properly formatted
6. WHEN displaying policy features THEN the system SHALL show the new fields in a clear, organized manner

### Requirement 2

**User Story:** As a survey administrator, I want the enhanced policy features to be available in both the admin interface and simple survey application, so that users can provide complete information during the survey process.

#### Acceptance Criteria

1. WHEN accessing the admin interface THEN the system SHALL display annual_limit_per_family field for policy management
2. WHEN using the admin interface THEN the system SHALL display the medical aid status field for policy configuration
3. WHEN managing policies in admin THEN the system SHALL display the ambulance coverage field for policy setup
4. WHEN users complete surveys THEN the system SHALL collect information about annual family limit preferences
5. WHEN users answer survey questions THEN the system SHALL ask about current medical aid status
6. WHEN users provide survey responses THEN the system SHALL collect preferences for ambulance coverage
7. WHEN survey data is processed THEN the system SHALL use the new fields for policy matching and recommendations

### Requirement 3

**User Story:** As a policy administrator, I want to manage rewards associated with policies, so that I can track and display incentive programs offered by different insurance providers.

#### Acceptance Criteria

1. WHEN accessing the policies app THEN the system SHALL provide a Rewards model for managing policy incentives
2. WHEN creating rewards THEN the system SHALL allow specification of reward details, eligibility criteria, and associated policies
3. WHEN managing rewards THEN the system SHALL support different types of rewards (cashback, discounts, benefits, etc.)
4. WHEN linking rewards to policies THEN the system SHALL maintain proper relationships between rewards and policy records
5. WHEN displaying policies THEN the system SHALL show associated rewards information where applicable
6. WHEN users view policy details THEN the system SHALL clearly present available rewards and their terms

### Requirement 4

**User Story:** As a policy administrator, I want to add detailed coverage information to additional features, so that I can provide comprehensive descriptions of what each policy covers.

#### Acceptance Criteria

1. WHEN managing additional features THEN the system SHALL provide a coverage_details TextField for comprehensive coverage descriptions
2. WHEN entering coverage details THEN the system SHALL allow rich text formatting for clear presentation
3. WHEN saving additional features THEN the system SHALL validate that coverage details are properly formatted
4. WHEN displaying additional features THEN the system SHALL present coverage details in a readable format
5. WHEN users view policy information THEN the system SHALL show detailed coverage information alongside other policy features
6. WHEN comparing policies THEN the system SHALL include coverage details in the comparison interface

### Requirement 5

**User Story:** As a user viewing policy comparison results, I want to see an option to view detailed benefits covered by each matching policy, so that I can understand exactly what coverage each policy provides.

#### Acceptance Criteria

1. WHEN viewing policy comparison results THEN the system SHALL display a "View Benefits Covered" option on each policy card
2. WHEN clicking "View Benefits Covered" THEN the system SHALL show a detailed breakdown of all benefits included in that policy
3. WHEN displaying benefits information THEN the system SHALL organize benefits by category (medical, additional services, coverage limits, etc.)
4. WHEN showing benefit details THEN the system SHALL include information from the coverage_details field and other relevant policy features
5. WHEN users view benefits THEN the system SHALL provide clear, easy-to-understand descriptions of what is covered
6. WHEN displaying benefits THEN the system SHALL highlight key features that match the user's survey preferences
7. WHEN users close the benefits view THEN the system SHALL return them to the comparison results seamlessly

### Requirement 6

**User Story:** As a system user, I want all the enhanced policy features to work seamlessly across the entire system, so that I have consistent access to comprehensive policy information regardless of which part of the system I'm using.

#### Acceptance Criteria

1. WHEN policy features are updated THEN the system SHALL reflect changes across admin interfaces, surveys, and comparison results
2. WHEN new fields are added THEN the system SHALL maintain data integrity and proper validation throughout the system
3. WHEN users interact with any part of the system THEN the system SHALL use consistent terminology and formatting for the enhanced features
4. WHEN displaying policy information THEN the system SHALL show all relevant enhanced features in appropriate contexts
5. WHEN processing survey responses THEN the system SHALL properly match user preferences against the enhanced policy features
6. WHEN generating comparisons THEN the system SHALL include the new fields in matching algorithms and result displays