from django import template
from django.templatetags.static import static
register = template.Library()

@register.simple_tag
def photo(obj):
    image = getattr(obj, 'image', None)
    if image: return image.url
    asset = getattr(obj, 'asset', None)
    if asset: return static('img/' + asset)
    destination = getattr(obj, 'destination', None)
    if destination: return photo(destination)
    return static('img/italy.jpg')

@register.simple_tag(takes_context=True)
def page_url(context, number):
    query = context['request'].GET.copy()
    query['page'] = number
    return '?' + query.urlencode()
