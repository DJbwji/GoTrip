from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from tours.models import Destination, Category, Excursion
from trips.models import Trip

def home(request):
    return render(request, 'core/home.html', {'destinations': Destination.objects.annotate(published_count=Count('excursions', filter=Q(excursions__status='approved'))).order_by('pk')[:5],
        'categories': Category.objects.all(), 'excursions': Excursion.objects.filter(status='approved').select_related('destination','guide')[:4],
        'trips': Trip.objects.filter(start_date__gte=timezone.localdate()).select_related('destination').prefetch_related('participants')[:4]})

def about(request):
    return render(request, 'core/about.html')
