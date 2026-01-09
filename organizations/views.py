from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.urls import reverse

# Create your views here.
def home(request):
    return render(request, 'public/index.html', {})

def funerals(request):
    return render(request, 'public/funerals.html', {})

def health(request):
    return render(request, 'public/health.html', {})

def funeral_survey(request):
    """
    Start a new funeral survey session and redirect directly to the survey form.
    Bypasses the category selection page.
    """
    return redirect('surveys:direct_survey', category_slug='funeral')

def health_survey(request):
    """
    Start a new health survey session and redirect directly to the survey form.
    Bypasses the category selection page.
    """
    return redirect('surveys:direct_survey', category_slug='health')