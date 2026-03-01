from django.db import models

class DeliveryStatus(models.TextChoices):
    # Планирование
    PENDING = 'Pending', 'Ожидается'          # Поставка запланирована, но еще не выехала
    IN_TRANSIT = 'In Transit', 'В пути'       # Груз отправлен поставщиком
    
    # Завершение
    DELIVERED = 'Delivered', 'Доставлено'     # Груз прибыл на территорию склада (Акт прибытия)
    RECEIVED = 'Received', 'Принято'         # Кладовщик проверил и принял товар (Приемка)
    
    # Проблемы
    NOT_DELIVERED = 'Not Delivered', 'Не доставлено' # Срыв поставки
    CANCEL = 'Cancel', 'Отменено'             # Отмена заказа
    DELAYED = 'Delayed', 'Задерживается'      # Опоздание относительно даты в договоре
