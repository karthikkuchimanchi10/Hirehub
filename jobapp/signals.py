from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Users
from .tasks import send_registration_email


@receiver(pre_save, sender=Users)
def store_old_status(sender, instance, **kwargs):
    """
    Store previous approval status before saving
    """
    if instance.pk:
        instance._old_status = sender.objects.get(pk=instance.pk).is_approved
    else:
        instance._old_status = None


@receiver(post_save, sender=Users)
def user_status_email(sender, instance, created, **kwargs):

    # SAFE ROLE HANDLING (prevents crash if None)
    role = (instance.UserRole or "").upper()

    status = instance.is_approved
    old_status = getattr(instance, "_old_status", None)

    # ==========================
    # APPLICANT CREATION EMAIL
    # ==========================
    if role == "APPLICANT" and created:
        send_registration_email.delay(
            instance.email,
            instance.first_name,
            instance.last_name,
            instance.Gender,
            role="APPLICANT",
            status="Approved"
        )

    # ==========================
    # HR CREATION EMAIL
    # ==========================
    elif role == "HR" and created:
        send_registration_email.delay(
            instance.email,
            instance.first_name,
            instance.last_name,
            instance.Gender,
            role="HR",
            status="Pending"
        )

    # ==========================
    # HR STATUS CHANGE EMAIL
    # ==========================
    elif (
        role == "HR"
        and not created
        and old_status != status
        and status in ["Approved", "Rejected", "approved", "rejected"]
    ):
        send_registration_email.delay(
            instance.email,
            instance.first_name,
            instance.last_name,
            instance.Gender,
            role="HR",
            status=status.capitalize()
        )