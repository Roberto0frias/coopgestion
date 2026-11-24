from django.utils import timezone


def fecha_actual(request):
    del request
    return {"now": timezone.localtime()}
