from __future__ import annotations

import logging

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import Alert

logger = logging.getLogger(__name__)


@shared_task(name="alerts.tasks.send_alert_email")
def send_alert_email(
    alert_id: int,
    cena: str,
    platforma: str,
    sprzedawca: str,
) -> None:
    """Send the user a notification email for a triggered alert.

    Routed to: powiadomienia
    """
    alert = Alert.objects.select_related("grupa__uzytkownik").filter(id=alert_id).first()
    if alert is None or not alert.aktywny:
        return

    grupa = alert.grupa
    user = grupa.uzytkownik
    subject = f"Alert: {grupa.nazwa} — cena {cena} PLN"
    message = (
        f"Cześć,\n\n"
        f"Wyzwoliłeś alert dla grupy '{grupa.nazwa}'.\n"
        f"Typ: {alert.get_typ_alertu_display()}\n"
        f"Aktualna najniższa cena: {cena} PLN na {platforma} ({sprzedawca}).\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=None,  # uses DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )

    alert.ostatnie_wyzwolenie = timezone.now()
    alert.save(update_fields=["ostatnie_wyzwolenie"])
    logger.info("Alert email sent to %s for alert %s", user.email, alert_id)
