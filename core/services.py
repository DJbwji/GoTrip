import logging
from io import BytesIO
from PIL import Image, ImageOps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from .models import Activity

def record(user, text):
    Activity.objects.create(user=user, text=text)

def moderator_recipients():
    from django.contrib.auth import get_user_model
    addresses = list(get_user_model().objects.filter(is_active=True, is_staff=True).exclude(email='').values_list('email', flat=True))
    return list(dict.fromkeys([settings.MODERATOR_EMAIL, *addresses]))

def notify(subject, body, recipients=None):
    try:
        send_mail('GoTrip — ' + subject, body, settings.DEFAULT_FROM_EMAIL,
                  recipients or moderator_recipients(), fail_silently=False)
    except Exception:
        logging.getLogger(__name__).exception('Email delivery failed: %s', subject)

def resize_image(upload):
    if not upload:
        return upload
    img = ImageOps.exif_transpose(Image.open(upload)).convert('RGB')
    img.thumbnail((1600, 1200))
    output = BytesIO()
    img.save(output, format='JPEG', quality=86)
    return ContentFile(output.getvalue(), name='photo.jpg')
