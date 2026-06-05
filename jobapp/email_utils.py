import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    message = Mail(
        from_email="hirehub.com@gmail.com",  # MUST MATCH VERIFIED SENDER
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)

        print("STATUS:", response.status_code)
        print("BODY:", response.body)

        return response.status_code

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None