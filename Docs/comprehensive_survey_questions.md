# Comprehensive Survey Questions for Finding Best Insurance Policies

This document outlines all the essential questions needed to help users find the best insurance policies through the simple survey system. The questions are designed to capture key user preferences, constraints, and requirements that directly impact policy matching and recommendations.

## How the Survey System Works

The simple survey system collects user responses through targeted questions and converts them into criteria for policy matching. Each question maps to specific policy attributes and helps the comparison engine:

1. **Filter eligible policies** based on basic requirements (age, location, budget)
2. **Score and rank policies** based on user preferences and priorities
3. **Generate personalized recommendations** with the best matching policies
4. **Provide clear comparisons** highlighting pros, cons, and key features

## Health Insurance Survey Questions

### Personal Information Section

#### 1. Age Verification
**Question:** "What is your age?"
- **Type:** Number input
- **Field Name:** `age`
- **Validation:** Min: 18, Max: 80
- **Purpose:** Determines policy eligibility and premium calculations
- **Impact:** High - affects all policy options and pricing

#### 2. Geographic Location
**Question:** "Which province are you located in?"
- **Type:** Dropdown select
- **Field Name:** `location`
- **Options:**
  - Hhohho
  - Manzini
  - Shiselweni
  - Lubombo
- **Purpose:** Determines policy availability and regional pricing
- **Impact:** Medium - affects provider networks and costs

#### 3. Family Coverage Size
**Question:** "How many family members need coverage (including yourself)?"
- **Type:** Number input
- **Field Name:** `family_size`
- **Validation:** Min: 1, Max: 10
- **Purpose:** Determines premium scaling and family plan eligibility
- **Impact:** High - significantly affects costs and plan types

### Health Status Assessment

#### 4. Overall Health Status
**Question:** "How would you describe your current health status?"
- **Type:** Radio buttons
- **Field Name:** `health_status`
- **Options:**
  - Excellent - No health issues, very active
  - Good - Minor issues, generally healthy
  - Fair - Some health concerns, managing conditions
  - Poor - Significant health issues requiring regular care
- **Purpose:** Risk assessment and policy eligibility
- **Impact:** High - affects premiums and coverage options

#### 5. Chronic Conditions Assessment
**Question:** "Do you have any of the following chronic conditions? (Select all that apply)"
- **Type:** Multiple checkboxes
- **Field Name:** `chronic_conditions`
- **Options:**
  - Diabetes (Type 1 or 2)
  - High Blood Pressure
  - Heart Disease
  - Asthma
  - Arthritis
  - Depression/Anxiety
  - Kidney Disease
  - Cancer (current or history)
  - None of the above
- **Purpose:** Identifies need for specialized coverage
- **Impact:** High - affects eligibility and premium calculations

### Coverage Preferences

#### 6. Coverage Priority
**Question:** "What type of coverage is most important to you?"
- **Type:** Radio buttons
- **Field Name:** `coverage_priority`
- **Options:**
  - Hospital Cover - Focus on major medical expenses
  - Day-to-day Medical Expenses - Routine healthcare costs
  - Comprehensive Coverage - Complete healthcare protection
- **Purpose:** Matches user priorities to policy types
- **Impact:** High - determines policy category recommendations

#### 7. Chronic Medication Needs
**Question:** "Do you currently take chronic medication?"
- **Type:** Yes/No toggle
- **Field Name:** `chronic_medication_needed`
- **Purpose:** Identifies need for medication coverage benefits
- **Impact:** Medium - affects policy feature requirements

### Financial Constraints

#### 8. Monthly Budget
**Question:** "What is your maximum monthly budget for health insurance?"
- **Type:** Number input (Rands)
- **Field Name:** `monthly_budget`
- **Validation:** Min: R200, Max: R5,000
- **Purpose:** Primary filter for policy affordability
- **Impact:** Very High - determines available policy options

#### 9. Deductible Preference
**Question:** "What deductible amount would you prefer?"
- **Type:** Radio buttons
- **Field Name:** `preferred_deductible`
- **Options:**
  - No Deductible - Pay nothing out-of-pocket
  - R1,000 - Lower premiums, small deductible
  - R2,500 - Moderate premiums, moderate deductible
  - R5,000 - Lower premiums, higher deductible
- **Purpose:** Balances premium costs with out-of-pocket expenses
- **Impact:** Medium - affects premium calculations

### Additional Health Questions (Enhanced Coverage)

#### 10. Dental and Optical Needs
**Question:** "Do you need dental and optical coverage?"
- **Type:** Multiple checkboxes
- **Field Name:** `additional_coverage_needs`
- **Options:**
  - Dental coverage (cleanings, fillings, procedures)
  - Optical coverage (eye exams, glasses, contacts)
  - Both dental and optical
  - Neither - medical only
- **Purpose:** Identifies need for supplementary benefits
- **Impact:** Medium - affects policy feature matching

#### 11. Maternity Coverage
**Question:** "Do you need maternity coverage?"
- **Type:** Radio buttons
- **Field Name:** `maternity_coverage_needed`
- **Options:**
  - Yes - Planning pregnancy or currently pregnant
  - Maybe - Might need in future
  - No - Not needed
- **Purpose:** Identifies need for maternity benefits
- **Impact:** Medium - affects policy selection for applicable users

## Funeral Insurance Survey Questions

### Personal Information Section

#### 1. Age Verification
**Question:** "What is your age?"
- **Type:** Number input
- **Field Name:** `age`
- **Validation:** Min: 18, Max: 80
- **Purpose:** Determines premium calculations and waiting periods
- **Impact:** High - affects all policy pricing

#### 2. Geographic Location
**Question:** "Which province are you located in?"
- **Type:** Dropdown select
- **Field Name:** `location`
- **Options:** [Same as health insurance]
- **Purpose:** Determines service provider availability
- **Impact:** Medium - affects provider networks

#### 3. Family Coverage Size
**Question:** "How many family members do you want to cover with funeral insurance?"
- **Type:** Number input
- **Field Name:** `family_members_to_cover`
- **Validation:** Min: 1, Max: 15
- **Purpose:** Determines total coverage needs and premium scaling
- **Impact:** High - significantly affects costs

### Coverage Requirements

#### 4. Coverage Amount Needed
**Question:** "What coverage amount do you need per person?"
- **Type:** Radio buttons
- **Field Name:** `coverage_amount`
- **Options:**
  - R25,000 - Basic funeral coverage
  - R50,000 - Standard funeral coverage
  - R100,000 - Comprehensive funeral coverage
  - R200,000+ - Premium funeral coverage
- **Purpose:** Matches coverage level to funeral cost expectations
- **Impact:** Very High - primary factor in policy selection

#### 5. Service Level Preference
**Question:** "What level of funeral service do you prefer?"
- **Type:** Radio buttons
- **Field Name:** `service_preference`
- **Options:**
  - Basic - Simple, dignified funeral service
  - Standard - Traditional funeral with common extras
  - Premium - Enhanced service with additional benefits
  - Luxury - Top-tier service with all amenities
- **Purpose:** Matches service expectations to policy benefits
- **Impact:** High - affects policy type recommendations

### Financial Constraints

#### 6. Monthly Budget
**Question:** "What is your maximum monthly budget for funeral insurance?"
- **Type:** Number input (Rands)
- **Field Name:** `monthly_budget`
- **Validation:** Min: R50, Max: R500
- **Purpose:** Primary affordability filter
- **Impact:** Very High - determines available options

#### 7. Waiting Period Tolerance
**Question:** "What waiting period can you tolerate before coverage begins?"
- **Type:** Radio buttons
- **Field Name:** `waiting_period`
- **Options:**
  - No Waiting Period - Immediate coverage (higher premiums)
  - 3 Months - Short waiting period
  - 6 Months - Standard waiting period
  - 12 Months - Longer waiting period (lower premiums)
- **Purpose:** Balances immediate coverage needs with affordability
- **Impact:** High - affects policy eligibility and pricing

### Additional Funeral Questions (Enhanced Coverage)

#### 8. Additional Benefits Needed
**Question:** "Which additional benefits are important to you? (Select all that apply)"
- **Type:** Multiple checkboxes
- **Field Name:** `additional_benefits`
- **Options:**
  - Repatriation - Transport deceased to home province/country
  - Grocery Benefit - Financial support for family during mourning
  - Tombstone Benefit - Assistance with memorial costs
  - Memorial Service - Help organizing memorial events
  - None of the above
- **Purpose:** Identifies need for supplementary benefits
- **Impact:** Medium - affects policy feature matching

#### 9. Payout Speed Preference
**Question:** "How quickly do you need claim payouts?"
- **Type:** Radio buttons
- **Field Name:** `payout_speed_preference`
- **Options:**
  - Within 24 hours - Emergency speed (may cost more)
  - Within 48 hours - Fast processing
  - Within 1 week - Standard processing
  - Flexible - Cost is more important than speed
- **Purpose:** Matches urgency needs to policy features
- **Impact:** Medium - affects policy selection criteria

## Question Weighting and Impact System

### High Impact Questions (Weight: 3.0-3.5)
- Monthly budget (both categories)
- Coverage amount needed (funeral)
- Age (both categories)
- Family size/coverage size

### Medium-High Impact Questions (Weight: 2.0-2.5)
- Health status (health)
- Chronic conditions (health)
- Coverage priority (health)
- Service preference (funeral)

### Medium Impact Questions (Weight: 1.5-2.0)
- Location (both categories)
- Waiting period tolerance (funeral)
- Deductible preference (health)

### Lower Impact Questions (Weight: 1.0-1.5)
- Additional coverage needs
- Supplementary benefits
- Payout speed preferences

## Survey Flow and Logic

### Progressive Disclosure
1. **Start with essential questions** (age, location, budget)
2. **Move to coverage-specific questions** (health status, coverage amounts)
3. **End with preference questions** (additional benefits, service levels)

### Conditional Logic
- Show chronic medication question only if chronic conditions are selected
- Show maternity coverage only for applicable age ranges
- Adjust budget validation based on family size

### Completion Requirements
- All questions marked as "required" must be answered
- Survey completion triggers policy matching algorithm
- Users can modify answers and see updated recommendations

## Data Processing and Policy Matching

### Criteria Conversion
Survey responses are converted to policy matching criteria:
- **Budget constraints** → Premium filtering
- **Coverage needs** → Benefit matching
- **Health status** → Risk assessment
- **Preferences** → Feature prioritization

### Scoring Algorithm
Policies are scored based on:
1. **Criteria match** (70% weight) - How well policy meets requirements
2. **Value for money** (20% weight) - Premium vs. benefits ratio
3. **Provider reputation** (5% weight) - Organization reliability
4. **User reviews** (5% weight) - Customer satisfaction

### Result Presentation
- **Top 5 matching policies** ranked by overall score
- **Key features highlighted** for each policy
- **Pros and cons** clearly listed
- **Value rating** (Excellent/Good/Fair/Poor)
- **Direct quote links** for easy application

## Implementation Notes

### Technical Requirements
- All questions stored in `SimpleSurveyQuestion` model
- Responses saved in `SimpleSurveyResponse` model
- Session management for anonymous users
- Real-time validation and progress tracking

### User Experience
- **Progressive completion** - save responses as user progresses
- **Clear progress indicators** - show completion percentage
- **Helpful explanations** - provide context for each question
- **Easy navigation** - allow users to go back and modify answers

### Performance Optimization
- **Efficient policy filtering** - reduce comparison set early
- **Cached results** - store recommendations for session duration
- **Minimal data collection** - only ask essential questions
- **Fast response times** - optimize database queries

This comprehensive question set ensures that users provide all necessary information to receive accurate, personalized insurance policy recommendations while maintaining a smooth and efficient survey experience.