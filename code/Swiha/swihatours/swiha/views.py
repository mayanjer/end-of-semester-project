from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def booking(request):
    return render(request, 'booking.html')

def blog(request):
    return render(request, 'blog.html')

def booking(request):
    return render(request, 'booking.html')

def contact(request):
    return render(request, 'contact.html')

def destination(request):
    return render(request, 'destinations.html')

def gallery(request):
    return render(request, 'gallery.html')

def packages(request):
    return render(request, 'packages.html')