from django.db import models

class DeliveryStatus(models.TextChoices):
    # Планирование
    PENDING = 'Pending', 'Ожидается'
    IN_TRANSIT = 'In Transit', 'В пути'

    # Завершение
    DELIVERED = 'Delivered', 'Доставлено'
    RECEIVING = 'Receiving', 'Осуществление приёма'
    RECEIVED = 'Received', 'Принято'

    # Проблемы
    NOT_DELIVERED = 'Not Delivered', 'Не доставлено'
    CANCEL = 'Cancel', 'Отменено'
    DELAYED = 'Delayed', 'Задерживается'
