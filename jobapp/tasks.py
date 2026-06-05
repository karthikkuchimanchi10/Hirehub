from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import JobApplications
from jobapp.email_utils import send_email


@shared_task
def send_registration_email(user_email, first_name, last_name, gender=None, role='Applicant', status='Approved'):

    # Determine salutation
    if gender == 'M':
        salutation = 'Mr.'
    elif gender == 'F':
        salutation = 'Ms.'
    else:
        salutation = ''

    subject_mapping = {
        ('HR', 'Pending'): "Registration Received - HireHub",
        ('HR', 'Approved'): "HR Account Approved - HireHub",
        ('HR', 'Rejected'): "HR Registration Rejected - HireHub",
        ('Applicant', 'Approved'): "Registration Successful - HireHub"
    }

    subject = subject_mapping.get(
        (role.upper(), status.capitalize()),
        'HireHub Notification'
    )

    # Context for HTML template
    context = {
        "first_name": first_name,
        "last_name": last_name,
        "salutation": salutation,
        "year": timezone.now().year,
        "role": role,
        "status": status
    }

    html_content = render_to_string(
        "emails/Registration_mail.html",
        context
    )

    text_content = (
        f"Dear {salutation} {first_name} {last_name},\n\n"
        f"A Notification From HireHub Job Portal"
    )

    # Send via SendGrid (replaces SMTP)
    send_email(
        user_email,
        subject,
        html_content
    )

    return f"Confirmation email sent to {user_email}"


@shared_task
def send_forget_password_otp_email(user_email, first_name, last_name, otp):

    subject = "Password Reset OTP - HireHub"

    text_content = (
        f"Dear {first_name} {last_name},\n\n"
        f"Your OTP for password reset is {otp}.\n\n"
        f"Do not Share it with any one.\n\n"
        f"If it is not you please contact support.\n\n"
        f"Best regards,\nHireHub Team"
    )

    html_content = render_to_string(
        "emails/Forget_password_otp_mail.html",
        {
            "username": f"{first_name} {last_name}",
            "otp": otp,
            "year": timezone.now().year
        }
    )

    send_email(
        user_email,
        subject,
        html_content
    )

    return f"OTP email sent to {user_email}"


@shared_task
def send_job_application_email(application_id):

    application = JobApplications.objects.select_related(
        "user", "job"
    ).get(id=application_id)

    user_email = application.user.email
    first_name = application.user.first_name

    job_title = application.job.job_title
    company_name = application.job.company_name
    job_location = application.job.job_location

    subject = "Application Received - HireHub"

    message = f"""
Dear {first_name},

Your application for "{job_title}" at {company_name} ({job_location}) has been successfully submitted.

We will notify you once the employer reviews your profile.

Thank you for using HireHub.

Regards,
HireHub Team
"""

    send_email(
        user_email,
        subject,
        message
    )

    return f"Application email sent to {user_email}"


@shared_task
def send_user_status_mail(application_id):

    application = JobApplications.objects.select_related(
        "user", "job"
    ).get(id=application_id)

    user_email = application.user.email
    first_name = application.user.first_name
    last_name = application.user.last_name

    job_title = application.job.job_title
    company_name = application.job.company_name
    job_location = application.job.job_location

    full_name = f"{first_name} {last_name}"

    if application.Status == "Accpected":
        subject = "🎉 Congratulations! Your Application is Selected"

        text_content = f"""
Dear {full_name},

Good news!

Your application for the role of "{job_title}" at {company_name} ({job_location}) has been selected.

The company will contact you soon regarding the next steps.

Regards,
HireHub Team
"""

    else:
        subject = "Application Status Update - HireHub"

        text_content = f"""
Dear {full_name},

Thank you for applying for the role of "{job_title}" at {company_name} ({job_location}).

After careful review, we regret to inform you that you have not been selected.

We encourage you to apply for other opportunities.

Regards,
HireHub Team
"""

    send_email(
        user_email,
        subject,
        text_content
    )

    return f"Status email sent to {user_email}"