from django.shortcuts import render

# Create your views here.


def index(request):
    """view to return index page"""
    return render(request, 'home/index.html')


def privacy(request):
    return render(request, 'home/privacy_policy.html')


def about(request):
    return render(request, 'home/about.html')
