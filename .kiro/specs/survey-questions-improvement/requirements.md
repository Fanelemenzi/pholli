# Requirements Document

## Introduction

This feature improves the existing survey questions in the policy comparison system by adding range-based options for benefits coverage and annual limits, while removing unnecessary questions. The improvements will provide users with more nuanced options that better match real-world policy variations and help guide users who are uncertain about their coverage needs.

## Requirements

### Requirement 1

**User Story:** As a user completing a health insurance survey, I want to select specific levels of in-hospital and out-of-hospital benefits instead of just yes/no options, so that I can better match policies that offer different coverage levels.

#### Acceptance Criteria

1. WHEN a user encounters in-hospital benefits questions THEN the system SHALL present 5 coverage level options instead of binary yes/no choices
2. WHEN a user selects in-hospital benefits THEN the system SHALL offer these exact options from Docs/benefits.md:
   - Option 1: "No hospital cover" - "I do not need cover for hospital admission"
   - Option 2: "Basic hospital care" - "Covers admission and standard hospital treatment"
   - Option 3: "Moderate hospital care" - "Covers admission, procedures, and specialist treatment"
   - Option 4: "Extensive hospital care" - "Covers most hospital needs, including major procedures"
   - Option 5: "Comprehensive hospital care" - "Covers all hospital-related treatment and services"
3. WHEN a user encounters out-of-hospital benefits questions THEN the system SHALL present 5 coverage level options instead of binary yes/no choices
4. WHEN a user selects out-of-hospital benefits THEN the system SHALL offer these exact options from Docs/benefits.md:
   - Option 1: "No out-of-hospital cover" - "No cover for day-to-day medical care"
   - Option 2: "Basic clinic visits" - "Covers GP/clinic visits only"
   - Option 3: "Routine medical care" - "Covers GP visits and basic medication"
   - Option 4: "Extended medical care" - "Covers GP visits, specialists, and diagnostics"
   - Option 5: "Comprehensive day-to-day care" - "Covers most medical needs outside hospital, including chronic care"
5. WHEN the comparison engine processes these responses THEN it SHALL match policies based on coverage levels using the existing PolicyFeatures model's in_hospital_benefit and out_hospital_benefit fields
6. WHEN displaying comparison results THEN the system SHALL show how policy benefits align with the user's selected coverage levels

### Requirement 2

**User Story:** As a user who is unsure about coverage amounts, I want to choose from range options for annual limits per family and per member, so that I can make informed decisions about how much coverage I might need.

#### Acceptance Criteria

1. WHEN a user encounters annual limit per family questions THEN the system SHALL present helpful range options to guide their decision
2. WHEN a user selects annual family limit ranges THEN the system SHALL offer these specific options:
   - "R10,000 - R50,000" - "Basic family coverage for routine medical needs"
   - "R50,001 - R100,000" - "Standard family coverage for most medical situations"
   - "R100,001 - R250,000" - "Enhanced family coverage including specialist care"
   - "R250,001 - R500,000" - "Comprehensive family coverage for major medical needs"
   - "R500,001 - R1,000,000" - "Premium family coverage for extensive medical care"
   - "R1,000,001 - R2,000,000" - "High-end family coverage for complex medical needs"
   - "R2,000,001 - R5,000,000" - "Luxury family coverage for all medical scenarios"
   - "R5,000,001+" - "Unlimited family coverage preferred"
   - "Not sure / Need guidance" - "Help me choose based on my situation"
3. WHEN a user encounters annual limit per member questions THEN the system SHALL present helpful range options to guide their decision
4. WHEN a user selects annual member limit ranges THEN the system SHALL offer these specific options:
   - "R10,000 - R25,000" - "Basic individual coverage for routine care"
   - "R25,001 - R50,000" - "Standard individual coverage for most needs"
   - "R50,001 - R100,000" - "Enhanced individual coverage including specialists"
   - "R100,001 - R200,000" - "Comprehensive individual coverage for major needs"
   - "R200,001 - R500,000" - "Premium individual coverage for extensive care"
   - "R500,001 - R1,000,000" - "High-end individual coverage for complex needs"
   - "R1,000,001 - R2,000,000" - "Luxury individual coverage for all scenarios"
   - "R2,000,001+" - "Unlimited individual coverage preferred"
   - "Not sure / Need guidance" - "Help me choose based on my situation"
5. WHEN displaying range options THEN the system SHALL provide helpful tooltips explaining what each range typically covers
6. WHEN the comparison engine processes these responses THEN it SHALL prioritize policies using the existing PolicyFeatures model's annual_limit_per_member and annual_limit_per_family fields that fall within or exceed the user's selected ranges

### Requirement 3

**User Story:** As a user completing surveys, I want the system to focus on relevant questions only, so that I can complete the survey more efficiently without answering unnecessary questions about my current medical aid status.

#### Acceptance Criteria

1. WHEN a user completes a health insurance survey THEN the system SHALL NOT ask about current medical aid membership status
2. WHEN the comparison engine processes survey responses THEN it SHALL NOT consider the PolicyFeatures model's currently_on_medical_aid field in its calculations
3. WHEN displaying comparison results THEN the system SHALL NOT reference current medical aid status in explanations or recommendations
4. WHEN a user views their survey responses THEN the system SHALL NOT store or display current medical aid status information
5. WHEN the survey is updated THEN existing survey templates SHALL be modified to remove medical aid status questions completely
6. WHEN users access the survey THEN the total number of questions SHALL be reduced due to removal of medical aid questions
7. WHEN policies are compared THEN the system SHALL ignore the currently_on_medical_aid field from the PolicyFeatures model entirely

### Requirement 4

**User Story:** As a user reviewing policy comparisons, I want to see how my range selections influence policy rankings, so that I can understand why certain policies are recommended over others.

#### Acceptance Criteria

1. WHEN displaying comparison results THEN the system SHALL show which policies best match the user's selected benefit ranges
2. WHEN a policy partially matches ranges THEN the system SHALL indicate the coverage gap or excess clearly
3. WHEN explaining policy rankings THEN the system SHALL reference how annual limit ranges influenced the scoring
4. WHEN a user views policy details THEN the system SHALL highlight benefit amounts in relation to their selected ranges
5. WHEN comparing multiple policies THEN the system SHALL use range-based scoring to rank policies more accurately
6. WHEN a policy exceeds user ranges significantly THEN the system SHALL indicate potential over-coverage and cost implications

### Requirement 5

**User Story:** As a system administrator, I want to manage the new range-based questions and remove outdated questions, so that the survey system stays current and provides better user experience.

#### Acceptance Criteria

1. WHEN an administrator accesses survey management THEN the system SHALL allow editing of range-based question options
2. WHEN an administrator updates benefit ranges THEN the system SHALL validate that ranges don't overlap inappropriately
3. WHEN an administrator removes medical aid questions THEN the system SHALL handle existing survey responses gracefully
4. WHEN an administrator adds new range options THEN the system SHALL allow specification of comparison weights for each range
5. WHEN an administrator reviews survey analytics THEN the system SHALL show how range-based questions perform compared to previous binary questions
6. WHEN an administrator manages question dependencies THEN the system SHALL ensure range-based questions integrate properly with other survey logic

### Requirement 6

**User Story:** As a user with existing survey responses, I want my previous answers to be handled appropriately when the survey questions are updated, so that I don't lose my progress or receive inconsistent recommendations.

#### Acceptance Criteria

1. WHEN a user has existing binary benefit responses THEN the system SHALL migrate them to appropriate range selections where possible
2. WHEN a user has existing medical aid status responses THEN the system SHALL remove this data without affecting other responses
3. WHEN a user returns to an updated survey THEN the system SHALL show the new range-based questions with any migrated responses pre-filled
4. WHEN the system cannot migrate old responses THEN it SHALL prompt the user to answer the updated questions
5. WHEN generating comparisons for users with mixed old/new responses THEN the system SHALL handle both formats appropriately
6. WHEN a user wants to update their responses THEN the system SHALL allow them to modify their range selections and regenerate comparisons