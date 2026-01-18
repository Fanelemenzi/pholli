from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib import messages
from .models import BasePolicy, PolicyFeatures, PolicyCategory
from .forms import HealthPolicyFilterForm, FuneralPolicyFilterForm


class PolicyListView(ListView):
    """
    Generic policy listing view with basic filtering and search.
    """
    model = BasePolicy
    template_name = 'policies/policy_list.html'
    context_object_name = 'policies'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related('additional_features')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(organization__name__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        # Category filtering
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['name', '-name', 'base_premium', '-base_premium', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = PolicyCategory.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        return context


class HealthPolicyListView(ListView):
    """
    Health policy listing view with feature-based filtering.
    Requirement 7.1, 7.2, 8.1, 8.2, 8.3
    """
    model = BasePolicy
    template_name = 'policies/health_policy_list.html'
    context_object_name = 'policies'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED',
            policy_features__insurance_type='HEALTH'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related('additional_features')
        
        # Feature-based filtering
        form = HealthPolicyFilterForm(self.request.GET)
        if form.is_valid():
            # Annual limit filtering
            min_annual_limit = form.cleaned_data.get('min_annual_limit')
            if min_annual_limit:
                queryset = queryset.filter(
                    policy_features__annual_limit_per_member__gte=min_annual_limit
                )
            
            # Income requirement filtering
            max_income_requirement = form.cleaned_data.get('max_income_requirement')
            if max_income_requirement:
                queryset = queryset.filter(
                    Q(policy_features__monthly_household_income__lte=max_income_requirement) |
                    Q(policy_features__monthly_household_income__isnull=True)
                )
            
            # In-hospital benefit filtering (Requirement 8.1)
            in_hospital_benefit = form.cleaned_data.get('in_hospital_benefit')
            if in_hospital_benefit is not None:
                queryset = queryset.filter(
                    policy_features__in_hospital_benefit=in_hospital_benefit
                )
            
            # Out-of-hospital benefit filtering (Requirement 8.2)
            out_hospital_benefit = form.cleaned_data.get('out_hospital_benefit')
            if out_hospital_benefit is not None:
                queryset = queryset.filter(
                    policy_features__out_hospital_benefit=out_hospital_benefit
                )
            
            # Chronic medication filtering (Requirement 8.3)
            chronic_medication = form.cleaned_data.get('chronic_medication')
            if chronic_medication is not None:
                queryset = queryset.filter(
                    policy_features__chronic_medication_availability=chronic_medication
                )
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(organization__name__icontains=search_query)
            )
        
        # Sorting (Requirement 8.9, 8.10)
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by == 'premium_low_high':
            queryset = queryset.order_by('base_premium')
        elif sort_by == 'premium_high_low':
            queryset = queryset.order_by('-base_premium')
        elif sort_by == 'coverage_high_low':
            queryset = queryset.order_by('-coverage_amount')
        elif sort_by == 'coverage_low_high':
            queryset = queryset.order_by('coverage_amount')
        elif sort_by == 'name_a_z':
            queryset = queryset.order_by('name')
        elif sort_by == 'name_z_a':
            queryset = queryset.order_by('-name')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = HealthPolicyFilterForm(self.request.GET)
        context['insurance_type'] = 'health'
        context['page_title'] = 'Health Insurance Policies'
        context['search_query'] = self.request.GET.get('search', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Feature statistics for display
        context['feature_stats'] = self._get_health_feature_stats()
        
        return context
    
    def _get_health_feature_stats(self):
        """Get statistics about health policy features for display."""
        health_policies = PolicyFeatures.objects.filter(
            insurance_type='HEALTH',
            policy__is_active=True,
            policy__approval_status='APPROVED'
        )
        
        return {
            'total_policies': health_policies.count(),
            'with_in_hospital': health_policies.filter(in_hospital_benefit=True).count(),
            'with_out_hospital': health_policies.filter(out_hospital_benefit=True).count(),
            'with_chronic_medication': health_policies.filter(chronic_medication_availability=True).count(),
            'avg_annual_limit': health_policies.aggregate(
                avg=Avg('annual_limit_per_member')
            )['avg'] or 0,
        }


class FuneralPolicyListView(ListView):
    """
    Funeral policy listing view with feature-based filtering.
    Requirement 7.1, 7.2, 8.4, 8.5
    """
    model = BasePolicy
    template_name = 'policies/funeral_policy_list.html'
    context_object_name = 'policies'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED',
            policy_features__insurance_type='FUNERAL'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related('additional_features')
        
        # Feature-based filtering
        form = FuneralPolicyFilterForm(self.request.GET)
        if form.is_valid():
            # Cover amount filtering
            min_cover_amount = form.cleaned_data.get('min_cover_amount')
            if min_cover_amount:
                queryset = queryset.filter(
                    policy_features__cover_amount__gte=min_cover_amount
                )
            
            # Income requirement filtering
            max_income_requirement = form.cleaned_data.get('max_income_requirement')
            if max_income_requirement:
                queryset = queryset.filter(
                    Q(policy_features__monthly_net_income__lte=max_income_requirement) |
                    Q(policy_features__monthly_net_income__isnull=True)
                )
            
            # Marital status filtering
            marital_status = form.cleaned_data.get('marital_status')
            if marital_status:
                queryset = queryset.filter(
                    Q(policy_features__marital_status_requirement=marital_status) |
                    Q(policy_features__marital_status_requirement__isnull=True) |
                    Q(policy_features__marital_status_requirement='')
                )
            
            # Gender filtering
            gender = form.cleaned_data.get('gender')
            if gender:
                queryset = queryset.filter(
                    Q(policy_features__gender_requirement=gender) |
                    Q(policy_features__gender_requirement__isnull=True) |
                    Q(policy_features__gender_requirement='')
                )
            
            # Waiting period filtering (Requirement 8.5)
            max_waiting_period = form.cleaned_data.get('max_waiting_period')
            if max_waiting_period:
                queryset = queryset.filter(
                    waiting_period_days__lte=max_waiting_period
                )
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(organization__name__icontains=search_query)
            )
        
        # Sorting (Requirement 8.9, 8.10)
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by == 'premium_low_high':
            queryset = queryset.order_by('base_premium')
        elif sort_by == 'premium_high_low':
            queryset = queryset.order_by('-base_premium')
        elif sort_by == 'coverage_high_low':
            queryset = queryset.order_by('-policy_features__cover_amount')
        elif sort_by == 'coverage_low_high':
            queryset = queryset.order_by('policy_features__cover_amount')
        elif sort_by == 'name_a_z':
            queryset = queryset.order_by('name')
        elif sort_by == 'name_z_a':
            queryset = queryset.order_by('-name')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = FuneralPolicyFilterForm(self.request.GET)
        context['insurance_type'] = 'funeral'
        context['page_title'] = 'Funeral Insurance Policies'
        context['search_query'] = self.request.GET.get('search', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Feature statistics for display
        context['feature_stats'] = self._get_funeral_feature_stats()
        
        return context
    
    def _get_funeral_feature_stats(self):
        """Get statistics about funeral policy features for display."""
        funeral_policies = PolicyFeatures.objects.filter(
            insurance_type='FUNERAL',
            policy__is_active=True,
            policy__approval_status='APPROVED'
        )
        
        return {
            'total_policies': funeral_policies.count(),
            'avg_cover_amount': funeral_policies.aggregate(
                avg=Avg('cover_amount')
            )['avg'] or 0,
            'min_cover_amount': funeral_policies.aggregate(
                min=Avg('cover_amount')
            )['min'] or 0,
            'max_cover_amount': funeral_policies.aggregate(
                max=Avg('cover_amount')
            )['max'] or 0,
        }


class PolicyDetailView(DetailView):
    """
    Detailed policy view showing all features and information.
    """
    model = BasePolicy
    template_name = 'policies/policy_detail.html'
    context_object_name = 'policy'
    
    def get_queryset(self):
        return BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related(
            'additional_features', 'eligibility_criteria', 'exclusions', 'documents'
        )
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        obj.increment_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        policy = self.object
        
        # Get policy features
        policy_features = policy.get_policy_features()
        if policy_features:
            context['policy_features'] = policy_features
            context['insurance_type'] = policy_features.insurance_type.lower()
            context['features_dict'] = policy.get_all_features_dict()
        
        # Get related policies for comparison
        if policy_features:
            context['related_policies'] = BasePolicy.objects.filter(
                policy_features__insurance_type=policy_features.insurance_type,
                is_active=True,
                approval_status='APPROVED'
            ).exclude(id=policy.id)[:4]
        
        return context


class HealthPolicyFilterView(ListView):
    """
    AJAX view for health policy filtering.
    Requirement 8.6, 8.7, 8.8
    """
    model = BasePolicy
    template_name = 'policies/partials/health_policy_cards.html'
    context_object_name = 'policies'
    
    def get_queryset(self):
        # Same filtering logic as HealthPolicyListView
        queryset = BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED',
            policy_features__insurance_type='HEALTH'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related('additional_features')
        
        form = HealthPolicyFilterForm(self.request.GET)
        if form.is_valid():
            # Apply all filters
            min_annual_limit = form.cleaned_data.get('min_annual_limit')
            if min_annual_limit:
                queryset = queryset.filter(
                    policy_features__annual_limit_per_member__gte=min_annual_limit
                )
            
            max_income_requirement = form.cleaned_data.get('max_income_requirement')
            if max_income_requirement:
                queryset = queryset.filter(
                    Q(policy_features__monthly_household_income__lte=max_income_requirement) |
                    Q(policy_features__monthly_household_income__isnull=True)
                )
            
            in_hospital_benefit = form.cleaned_data.get('in_hospital_benefit')
            if in_hospital_benefit is not None:
                queryset = queryset.filter(
                    policy_features__in_hospital_benefit=in_hospital_benefit
                )
            
            out_hospital_benefit = form.cleaned_data.get('out_hospital_benefit')
            if out_hospital_benefit is not None:
                queryset = queryset.filter(
                    policy_features__out_hospital_benefit=out_hospital_benefit
                )
            
            chronic_medication = form.cleaned_data.get('chronic_medication')
            if chronic_medication is not None:
                queryset = queryset.filter(
                    policy_features__chronic_medication_availability=chronic_medication
                )
        
        # Handle no results case (Requirement 8.7)
        if not queryset.exists():
            # Store filter criteria for suggestion
            self.no_results = True
            self.applied_filters = form.cleaned_data if form.is_valid() else {}
        
        return queryset
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request - return JSON response
            policies_data = []
            for policy in context['policies']:
                policy_features = policy.get_policy_features()
                policies_data.append({
                    'id': policy.id,
                    'name': policy.name,
                    'organization': policy.organization.name,
                    'base_premium': str(policy.base_premium),
                    'coverage_amount': str(policy.coverage_amount),
                    'features': policy.get_all_features_dict() if policy_features else {},
                    'url': f'/policies/{policy.id}/',
                })
            
            response_data = {
                'policies': policies_data,
                'count': len(policies_data),
                'has_results': len(policies_data) > 0,
            }
            
            # Add suggestions if no results (Requirement 8.7)
            if hasattr(self, 'no_results') and self.no_results:
                response_data['suggestions'] = self._get_filter_suggestions()
            
            return JsonResponse(response_data)
        
        return super().render_to_response(context, **response_kwargs)
    
    def _get_filter_suggestions(self):
        """Generate suggestions when no policies match filters."""
        suggestions = []
        
        if hasattr(self, 'applied_filters'):
            filters = self.applied_filters
            
            if filters.get('min_annual_limit'):
                suggestions.append("Try lowering the minimum annual limit requirement")
            
            if filters.get('max_income_requirement'):
                suggestions.append("Consider increasing the maximum income requirement")
            
            if filters.get('in_hospital_benefit') or filters.get('out_hospital_benefit'):
                suggestions.append("Try making hospital benefit requirements optional")
            
            if filters.get('chronic_medication'):
                suggestions.append("Consider making chronic medication coverage optional")
        
        if not suggestions:
            suggestions.append("Try removing some filter criteria to see more options")
        
        return suggestions


class FuneralPolicyFilterView(ListView):
    """
    AJAX view for funeral policy filtering.
    Requirement 8.6, 8.7, 8.8
    """
    model = BasePolicy
    template_name = 'policies/partials/funeral_policy_cards.html'
    context_object_name = 'policies'
    
    def get_queryset(self):
        # Same filtering logic as FuneralPolicyListView
        queryset = BasePolicy.objects.filter(
            is_active=True,
            approval_status='APPROVED',
            policy_features__insurance_type='FUNERAL'
        ).select_related(
            'organization', 'category', 'policy_type', 'policy_features'
        ).prefetch_related('additional_features')
        
        form = FuneralPolicyFilterForm(self.request.GET)
        if form.is_valid():
            # Apply all filters
            min_cover_amount = form.cleaned_data.get('min_cover_amount')
            if min_cover_amount:
                queryset = queryset.filter(
                    policy_features__cover_amount__gte=min_cover_amount
                )
            
            max_income_requirement = form.cleaned_data.get('max_income_requirement')
            if max_income_requirement:
                queryset = queryset.filter(
                    Q(policy_features__monthly_net_income__lte=max_income_requirement) |
                    Q(policy_features__monthly_net_income__isnull=True)
                )
            
            marital_status = form.cleaned_data.get('marital_status')
            if marital_status:
                queryset = queryset.filter(
                    Q(policy_features__marital_status_requirement=marital_status) |
                    Q(policy_features__marital_status_requirement__isnull=True)
                )
            
            gender = form.cleaned_data.get('gender')
            if gender:
                queryset = queryset.filter(
                    Q(policy_features__gender_requirement=gender) |
                    Q(policy_features__gender_requirement__isnull=True)
                )
            
            max_waiting_period = form.cleaned_data.get('max_waiting_period')
            if max_waiting_period:
                queryset = queryset.filter(
                    waiting_period_days__lte=max_waiting_period
                )
        
        # Handle no results case (Requirement 8.7)
        if not queryset.exists():
            self.no_results = True
            self.applied_filters = form.cleaned_data if form.is_valid() else {}
        
        return queryset
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request - return JSON response
            policies_data = []
            for policy in context['policies']:
                policy_features = policy.get_policy_features()
                policies_data.append({
                    'id': policy.id,
                    'name': policy.name,
                    'organization': policy.organization.name,
                    'base_premium': str(policy.base_premium),
                    'coverage_amount': str(policy.coverage_amount),
                    'features': policy.get_all_features_dict() if policy_features else {},
                    'url': f'/policies/{policy.id}/',
                })
            
            response_data = {
                'policies': policies_data,
                'count': len(policies_data),
                'has_results': len(policies_data) > 0,
            }
            
            # Add suggestions if no results (Requirement 8.7)
            if hasattr(self, 'no_results') and self.no_results:
                response_data['suggestions'] = self._get_filter_suggestions()
            
            return JsonResponse(response_data)
        
        return super().render_to_response(context, **response_kwargs)
    
    def _get_filter_suggestions(self):
        """Generate suggestions when no policies match filters."""
        suggestions = []
        
        if hasattr(self, 'applied_filters'):
            filters = self.applied_filters
            
            if filters.get('min_cover_amount'):
                suggestions.append("Try lowering the minimum cover amount requirement")
            
            if filters.get('max_income_requirement'):
                suggestions.append("Consider increasing the maximum income requirement")
            
            if filters.get('max_waiting_period'):
                suggestions.append("Try allowing longer waiting periods")
            
            if filters.get('marital_status') or filters.get('gender'):
                suggestions.append("Consider making demographic requirements optional")
        
        if not suggestions:
            suggestions.append("Try removing some filter criteria to see more options")
        
        return suggestions