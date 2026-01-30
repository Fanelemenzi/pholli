# Funeral vs Health Policy Administration Guide

This guide explains how to create and manage different types of insurance policies in the admin interface, with clear differentiation between funeral and health insurance features.

## Overview

The policy system now provides clear differentiation between funeral and health insurance policies through:

1. **Enhanced PolicyFeatures model** with insurance-type-specific fields
2. **Dynamic admin interface** that shows relevant fields based on insurance type
3. **Comprehensive validation** to ensure data integrity
4. **User-friendly forms** with contextual help and guidance

## Creating a New Policy

### Step 1: Create Base Policy

1. Navigate to **Policies > Base Policies** in the admin
2. Click **Add Base Policy**
3. Fill in the basic information:
   - **Organization**: Select your organization
   - **Category**: Choose "Health Insurance" or "Funeral Insurance"
   - **Policy Type**: Select appropriate type (e.g., "Comprehensive Health", "Standard Funeral")
   - **Name**: Descriptive policy name
   - **Description**: Detailed policy description

### Step 2: Configure Policy Features

After saving the base policy, you'll need to add PolicyFeatures:

1. In the policy edit page, scroll to **Policy Features** inline section
2. Click **Add another Policy Features**
3. **Select Insurance Type**: This is crucial as it determines which fields are shown

## Funeral Insurance Configuration

### Required Fields for Funeral Policies

When you select "Funeral Insurance" as the insurance type, the following fields become available and required:

#### Core Funeral Features
- **Cover Amount Range**: Select the coverage range (R10k-25k, R25k-50k, etc.)
- **Funeral Service Type**: 
  - Basic Service - Essential arrangements only
  - Standard Service - Comprehensive package  
  - Premium Service - Full luxury service
  - Cash Payout Only - No managed services
- **Family Coverage Type**:
  - Individual Only
  - Main Member + Spouse
  - Nuclear Family (Parents + Children)
  - Extended Family (Up to 15 members)
- **Waiting Period Natural Death**: None, 1 month, 3 months, 6 months, 12 months

#### Service Inclusions
Configure what's included in the funeral service:
- **Includes Coffin**: Whether coffin is provided
- **Includes Transport**: Hearse/transport services
- **Includes Venue**: Funeral venue provision
- **Includes Catering**: Catering for mourners
- **Includes Flowers**: Flower arrangements
- **Includes Memorial Service**: Memorial service coordination

#### Additional Benefits
- **Repatriation Covered**: Transport to home area/country
- **Grocery Benefit**: Cash benefit for groceries
- **Grocery Benefit Amount**: Amount if grocery benefit is enabled
- **Mourning Clothes Benefit**: Allowance for mourning attire
- **Claim Payout Hours**: Speed of claim processing (e.g., 48 hours)

### Funeral Policy Examples

#### Basic Funeral Policy
```
Cover Amount Range: R10k-25k
Service Type: Basic Service
Family Coverage: Individual Only
Waiting Period: 6 months
Includes: Coffin, Transport
Additional Benefits: None
```

#### Standard Funeral Policy
```
Cover Amount Range: R25k-75k
Service Type: Standard Service
Family Coverage: Nuclear Family
Waiting Period: 3 months
Includes: Coffin, Transport, Venue, Catering, Flowers
Additional Benefits: Grocery Benefit (R2,000)
```

#### Premium Funeral Policy
```
Cover Amount Range: R75k-200k+
Service Type: Premium Service
Family Coverage: Extended Family
Waiting Period: None
Includes: All services
Additional Benefits: Repatriation, Grocery Benefit (R5,000), Mourning Clothes
```

## Health Insurance Configuration

### Required Fields for Health Policies

When you select "Health/Medical Insurance" as the insurance type:

#### Core Health Features
- **Annual Limit Family Range**: Coverage limit for the family
- **In-Hospital Benefit Level**: Level of hospital coverage
- **Out-of-Hospital Benefit Level**: Level of day-to-day medical coverage
- **Chronic Medication Availability**: Whether chronic meds are covered
- **Ambulance Coverage**: Emergency transport coverage

#### Additional Health Features
- **Monthly Household Income**: Income requirements
- **Currently on Medical Aid**: Whether applicant has existing coverage
- **Annual Limit Per Member/Family**: Specific monetary limits

### Health Policy Examples

#### Basic Health Policy
```
Family Limit Range: R50k-100k
Hospital Benefit: Basic hospital care
Out-Hospital Benefit: Basic clinic visits
Chronic Medication: No
Ambulance Coverage: Yes
```

#### Comprehensive Health Policy
```
Family Limit Range: R500k-1m
Hospital Benefit: Comprehensive hospital care
Out-Hospital Benefit: Comprehensive day-to-day care
Chronic Medication: Yes
Ambulance Coverage: Yes
```

## Admin Interface Features

### Dynamic Field Visibility

The admin interface automatically shows/hides fields based on the selected insurance type:

- **Health Insurance**: Shows medical coverage fields, hides funeral service fields
- **Funeral Insurance**: Shows funeral service fields, hides medical coverage fields

### Validation and Help

- **Real-time Validation**: Form validates that appropriate fields are filled
- **Contextual Help**: Each field includes relevant help text
- **Feature Summary**: Live summary of configured features
- **Required Field Indicators**: Visual indicators for mandatory fields

### Visual Differentiation

- **Color Coding**: Health fields have green borders, funeral fields have purple borders
- **Insurance Type Badges**: Visual indicators showing policy type
- **Grouped Fieldsets**: Related fields are grouped together logically

## Best Practices

### For Funeral Policies

1. **Service Level Alignment**: Ensure service inclusions match the service type
   - Basic: Essential services only
   - Standard: Balanced service package
   - Premium: Comprehensive luxury services

2. **Family Coverage**: Match family coverage type with target market
   - Individual: Single professionals
   - Nuclear Family: Young families
   - Extended Family: Multi-generational households

3. **Waiting Periods**: Balance customer appeal with risk management
   - No waiting period: Premium pricing required
   - 3-6 months: Standard market practice
   - 12 months: Budget-friendly options

### For Health Policies

1. **Coverage Limits**: Set appropriate limits for target market
   - Basic: R50k-100k family limits
   - Standard: R250k-500k family limits
   - Comprehensive: R1m+ family limits

2. **Benefit Levels**: Align hospital and out-of-hospital benefits
   - Comprehensive hospital should include comprehensive day-to-day
   - Basic hospital can pair with routine day-to-day care

3. **Chronic Medication**: Consider target market health needs
   - Younger demographics: May not need chronic coverage
   - Older demographics: Chronic coverage is essential

## Troubleshooting

### Common Issues

1. **Fields Not Showing**: Ensure insurance type is selected first
2. **Validation Errors**: Check that required fields for the insurance type are filled
3. **Conflicting Data**: Ensure only relevant fields for the insurance type contain data

### Error Messages

- "Health fields should not be filled for funeral policies"
- "Funeral fields should not be filled for health policies"
- "Cover amount range is required for funeral policies"
- "Annual limit family range is required for health policies"

## Integration with Comparison Engine

The configured features directly feed into the comparison engine:

### Funeral Policy Matching
- Cover amount preferences match to `cover_amount_range`
- Service preferences match to `funeral_service_type`
- Family size matches to `family_coverage_type` and `max_family_members`
- Budget matches to calculated premiums
- Waiting period tolerance matches to `waiting_period_natural_death`

### Health Policy Matching
- Coverage needs match to `annual_limit_family_range`
- Hospital preferences match to `in_hospital_benefit_level`
- Day-to-day needs match to `out_hospital_benefit_level`
- Chronic medication needs match to `chronic_medication_availability`

## Conclusion

The enhanced admin interface provides clear differentiation between funeral and health insurance policies, making it easy for administrators to:

1. Create appropriate policies for their target market
2. Configure relevant features without confusion
3. Ensure data integrity through validation
4. Provide accurate information for the comparison engine

This system supports the full policy lifecycle from creation through customer comparison and selection.