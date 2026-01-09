from django.db import models


class BasePolicyManager(models.Manager):
    """
    Custom manager for BasePolicy model.
    Provides common query methods for policies.
    """
    
    def active(self):
        """Return only active policies."""
        return self.filter(is_active=True)
    
    def approved(self):
        """Return only approved policies."""
        return self.filter(approval_status='APPROVED')
    
    def active_and_approved(self):
        """Return policies that are both active and approved."""
        return self.filter(is_active=True, approval_status='APPROVED')
    
    def by_category(self, category_slug):
        """Return policies filtered by category slug."""
        return self.filter(category__slug=category_slug)
    
    def featured(self):
        """Return featured policies."""
        return self.filter(is_featured=True, is_active=True)