from django.db import models
class DeliveryStatus(models.TextChoices):
        DELIVERED = 'Delivered', 'Доставлено'
        NOT_DELIVERED = 'Not Delivered', 'Не доставлено'
        CANCEL = 'Cancel', 'Отменено'