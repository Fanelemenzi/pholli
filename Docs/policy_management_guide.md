# Policy Management Guide

This guide explains how to create and customize insurance policies for organizations across different categories in the platform.

## Overview

The platform supports a hierarchical policy structure:
- **Organizations** create and manage their own policies
- **Categories** organize policies by type (Health, Life, Funeral, etc.)
- **Policy Types** provide subcategorization within each category
- **Policies** are the actual insurance products offered

## Getting Started

### Prerequisites
- Organization must be registered and verified
- Admin access to the Django admin interface
- Understanding of your insurance products and pricing

## Organization Setup

### 1. Register Your Organization

Organizations need to be properly set up before creating policies:

**Required Information:**
- Basic details (name, description, logo)
- Contact information (email, phone, website)
- Physical address
- Registration and license numbers
- Verification documents

**Key Settings:**
- `max_policies`: Maximum number of policies you can create (default: 50)
- `commission_rate`: Your commission rate percentage
- `verification_status`: Must be "VERIFIED" to activate policies

### 2. Organization Verification Process

1. Submit all required documents through the admin interface
2. Wait for admin verification
3. Once verified, you can create and activate policies

## Policy Categories and Types

### Understanding the Hierarchy

```
Policy Category (e.g., "Health Insurance")
├── Policy Type (e.g., "Comprehensive Health")
├── Policy Type (e.g., "Basic Health")
└── Policy Type (e.g., "Family Health")
```

### Available Categories

The platform supports various insurance categories:
- **Health Insurance**: Medical coverage policies
- **Life Insurance**: Life protection policies  
- **Funeral Insurance**: Funeral coverage policies
- **Custom Categories**: Additional categories as needed

### Creating Policy Types

Policy types help organize your products within categories:

1. Navigate to **Policy Types** in admin
2. Select the appropriate category
3. Define the type name and description
4. Set display order for organization

## Creating Policies

### Basic Policy Information

When creating a new policy, you'll need to provide:

**Essential Details:**
- Policy name and description
- Category and policy type
- Base premium amount
- Coverage amount
- Age restrictions (minimum/maximum)
- Waiting period

**Example:**
```
Name: "Comprehensive Family Health Plan"
Category: "Health Insurance"
Type: "Comprehensive Health"
Base Premium: R 850.00
Coverage: R 500,000.00
Min Age: 18
Max Age: 65
Waiting Period: 30 days
```

### Policy Status Management

Policies go through several status stages:

1. **DRAFT**: Initial creation, not visible to users
2. **PENDING**: Submitted for admin approval
3. **APPROVED**: Approved by admin, can be activated
4. **REJECTED**: Rejected by admin, needs revision
5. **ARCHIVED**: No longer active

### Activation Requirements

To activate a policy, ensure:
- Organization is verified
- Policy is approved by admin
- Organization hasn't exceeded policy limit
- All required information is complete

## Customizing Policy Features

### Adding Policy Features

Enhance your policies with detailed features:

```python
# Example features for a health policy
- "24/7 Emergency Coverage"
- "Specialist Consultations Included"
- "Prescription Medicine Coverage"
- "Annual Health Checkups"
- "Dental and Optical Benefits"
```

**Feature Configuration:**
- Title and detailed description
- Optional icon for visual appeal
- Highlight important features
- Set display order

### Eligibility Criteria

Define who can apply for your policy:

**Common Criteria:**
- Age requirements
- Health status
- Employment status
- Residency requirements
- Income thresholds

**Example:**
```
- "Must be between 18-65 years old"
- "South African resident"
- "No pre-existing chronic conditions"
- "Employed or self-employed"
```

### Policy Exclusions

Clearly define what's not covered:

**Health Insurance Exclusions:**
- Pre-existing conditions
- Cosmetic procedures
- Experimental treatments
- Self-inflicted injuries

**Life Insurance Exclusions:**
- Suicide within first 2 years
- Death due to illegal activities
- War-related deaths

## Premium Calculation

### Setting Base Premiums

Start with a competitive base premium for your target market.

### Advanced Premium Calculations

Create rules for premium adjustments based on various factors:

**Age-Based Pricing:**
```
Age 18-25: Base premium × 0.8
Age 26-35: Base premium × 1.0
Age 36-45: Base premium × 1.2
Age 46-55: Base premium × 1.5
Age 56-65: Base premium × 2.0
```

**Risk Factor Adjustments:**
```
Non-smoker: Base premium × 1.0
Smoker: Base premium × 1.3
High-risk occupation: +R 200
Family history: +R 150
```

### Implementation Example

```python
# In the admin, create premium calculation rules:
Factor: "age_group"
Value: "18-25"
Multiplier: 0.80
Additional Amount: 0.00

Factor: "smoking_status"
Value: "smoker"
Multiplier: 1.30
Additional Amount: 0.00
```

## Document Management

### Required Documents

Upload essential policy documents:

**Document Types:**
- **Brochure**: Marketing material for customers
- **Terms & Conditions**: Legal policy terms
- **Application Form**: Customer application form
- **Claim Form**: Claims submission form
- **User Guide**: How to use the policy

### Document Best Practices

- Use PDF format for official documents
- Keep file sizes reasonable (< 10MB)
- Use clear, descriptive filenames
- Mark public documents appropriately
- Update documents when policy changes

## Policy Management Workflow

### 1. Planning Phase
- Research market needs
- Define target audience
- Set competitive pricing
- Plan policy features

### 2. Creation Phase
- Create policy in DRAFT status
- Add all features and details
- Upload required documents
- Set premium calculation rules

### 3. Review Phase
- Submit for admin approval
- Address any feedback
- Make necessary revisions

### 4. Launch Phase
- Activate approved policy
- Monitor performance
- Collect customer feedback

### 5. Maintenance Phase
- Regular policy reviews
- Update pricing as needed
- Refresh marketing materials
- Analyze performance metrics

## Advanced Customization

### Custom Fields

Use the `custom_fields` JSON field for organization-specific data:

```json
{
  "underwriting_requirements": ["medical_exam", "financial_statements"],
  "special_benefits": ["gym_membership", "wellness_program"],
  "partner_networks": ["hospital_group_a", "pharmacy_chain_b"]
}
```

### Tags for Organization

Use tags for better categorization and search:

```json
["family-friendly", "comprehensive", "affordable", "digital-first"]
```

## Best Practices

### Policy Naming
- Use clear, descriptive names
- Include key benefits in the name
- Avoid technical jargon
- Keep names concise but informative

### Pricing Strategy
- Research competitor pricing
- Consider your target market
- Factor in all costs and desired profit
- Regularly review and adjust

### Feature Presentation
- Highlight unique selling points
- Use customer-friendly language
- Organize features logically
- Include relevant icons/visuals

### Documentation
- Keep all documents current
- Use professional formatting
- Ensure legal compliance
- Make information accessible

## Monitoring and Analytics

### Key Metrics to Track
- Policy views and comparisons
- Application conversion rates
- Customer reviews and ratings
- Premium collection rates
- Claim ratios

### Performance Optimization
- A/B test different descriptions
- Adjust pricing based on market response
- Update features based on feedback
- Optimize for search and comparison

## Troubleshooting

### Common Issues

**Policy Won't Activate:**
- Check organization verification status
- Ensure policy is approved
- Verify policy limit not exceeded
- Complete all required fields

**Premium Calculations Not Working:**
- Check calculation rule syntax
- Ensure factors are properly defined
- Verify multipliers and amounts
- Test with sample data

**Documents Not Displaying:**
- Check file upload success
- Verify file permissions
- Ensure proper file format
- Check public/private settings

## Support and Resources

### Getting Help
- Contact platform administrators
- Review documentation and guides
- Join organization forums
- Submit support tickets

### Training Resources
- Admin interface tutorials
- Policy creation workshops
- Best practices webinars
- Industry compliance guides

## Conclusion

Creating effective insurance policies requires careful planning, attention to detail, and ongoing optimization. Use this guide as a reference throughout your policy management journey, and don't hesitate to reach out for support when needed.

Remember that successful policies balance competitive pricing, comprehensive coverage, and clear communication to attract and retain customers while maintaining profitability for your organization.