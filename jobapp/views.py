import os
import json
import random
import hashlib
from django.db.models import Count
from collections import defaultdict
import calendar

from django.views.generic import DetailView
from dotenv import load_dotenv
from google import genai

from django.shortcuts import render, redirect, get_object_or_404

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse
)

from django.views import View
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages

from django.contrib.auth import (
    authenticate,
    login,
    logout,
    get_user_model
)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password

from django.core.exceptions import ValidationError

from django.utils import timezone

from .models import JobPosts, JobApplications

from .forms import (
    ApplicantRegistrationForm,
    HrRegistrationForm,
    ApplicantLoginForm,
    HrLoginForm,
    JobPostForm,
    JobApplicationForm
)

from .tasks import (
    send_forget_password_otp_email,
    send_job_application_email,
    send_user_status_mail
)


# =========================================================
# LOAD ENV VARIABLES
# =========================================================

User = get_user_model()


# =========================================================
# GEMINI CHATBOT API
# =========================================================

@csrf_exempt
def chatbot_api(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get("message")

        if not user_message:
            return JsonResponse({"error": "Message required"}, status=400)

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            return JsonResponse({"error": "Missing GEMINI_API_KEY"}, status=500)

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message
        )

        return JsonResponse({"response": response.text})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# =========================================================
# GLOBAL FORM MAP
# =========================================================

class BaseAuthFormMixin:

    FORM_MAP = {

        'register': {

            'applicant': {
                'form': ApplicantRegistrationForm,
                'template': 'applicant_sign.html'
            },

            'hr': {
                'form': HrRegistrationForm,
                'template': 'Hr_sign.html'
            }
        },

        'login': {

            'applicant': {
                'form': ApplicantLoginForm,
                'template': 'applicant_login.html'
            },

            'hr': {
                'form': HrLoginForm,
                'template': 'Hr_login.html'
            }
        }
    }

    action_type = None

    def get_config(self, user_type):

        return self.FORM_MAP.get(
            self.action_type,
            {}
        ).get(user_type)

    def get_form(self, user_type, data=None):

        config = self.get_config(user_type)

        if not config:
            return None

        return (
            config['form'](data)
            if data else
            config['form']()
        )

    def get_template(self, user_type):

        config = self.get_config(user_type)

        if not config:
            return None

        return config['template']


# =========================================================
# ROLE MIXINS
# =========================================================

class ApplicantRequiredMixin(LoginRequiredMixin):

    login_url = '/login/applicant/'

    def dispatch(self, request, *args, **kwargs):

        if (
            not request.user.is_authenticated
            or request.user.UserRole != 'applicant'
        ):

            return HttpResponse(
                "Unauthorized",
                status=403
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )


class HrRequiredMixin(LoginRequiredMixin):

    login_url = '/login/hr/'

    def dispatch(self, request, *args, **kwargs):

        if (
            not request.user.is_authenticated
            or request.user.UserRole != 'hr'
        ):

            return HttpResponse(
                "Unauthorized",
                status=403
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )


# =========================================================
# LANDING PAGE
# =========================================================

def landing_page(request):

    return render(
        request,
        'land.html'
    )


# =========================================================
# REGISTRATION
# =========================================================

class UserRegistrationView(
    BaseAuthFormMixin,
    View
):

    action_type = 'register'

    def get(self, request, user_type):

        form = self.get_form(user_type)

        template = self.get_template(user_type)

        if not form:

            return HttpResponseBadRequest(
                "Invalid user type"
            )

        return render(
            request,
            template,
            {
                'form': form,
                'user_type': user_type
            }
        )

    def post(self, request, user_type):

        form = self.get_form(user_type, request.POST)
        template = self.get_template(user_type)

        if not form:
            return HttpResponseBadRequest("Invalid user type")

        if not form.is_valid():
            print("FORM ERRORS =", form.errors)
            return render(request, template, {
                'form': form,
                'user_type': user_type
            })

        user = form.save(commit=False)

        user.UserRole = user_type

        # 🔥 FIX PASSWORD
        user.set_password(form.cleaned_data['password'])

        # role logic
        if user_type == 'hr':
            user.is_approved = "Pending"
            redirect_url = '/land/'
            messages.success(request, "HR registered successfully. Waiting for approval.")

        else:
            user.is_approved = "Approved"
            redirect_url = '/login/applicant/'
            messages.success(request, "Applicant registered successfully.")

        try:
            user.save()
        except Exception as e:
            print("SAVE ERROR:", str(e))
            return HttpResponse(f"Error: {e}")

        return redirect(redirect_url)
# =========================================================
# LOGIN
# =========================================================

class LoginView(
    BaseAuthFormMixin,
    View
):

    action_type = 'login'

    def get(self, request, user_type):

        form = self.get_form(user_type)

        template = self.get_template(user_type)

        if not form:

            return HttpResponseBadRequest(
                "Invalid user type"
            )

        return render(
            request,
            template,
            {
                'form': form,
                'user_type': user_type
            }
        )

    def post(self, request, user_type):

        form = self.get_form(user_type, request.POST)
        template = self.get_template(user_type)

        if not form or not form.is_valid():
            return render(request, template, {
                'form': form,
                'user_type': user_type
            })

        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        # 1. Authenticate user
        user = authenticate(request, username=username, password=password)

        # 2. CHECK 1: invalid credentials
        if not user:
            messages.error(request, "Invalid credentials.")
            return redirect(f'/login/{user_type}/')

        # 3. CHECK 2: wrong portal
        if user.UserRole != user_type:
            messages.error(request, "Wrong portal.")
            return redirect(f'/login/{user_type}/')

        # 4. CHECK 3: HR approval check (IMPORTANT PART)
        if user.UserRole == 'hr' and user.is_approved != "Approved":
            messages.error(request, "Awaiting admin approval.")
            return redirect(f'/login/{user_type}/')

        # 5. LOGIN ONLY AFTER ALL CHECKS PASS
        login(request, user)

        return redirect(f'/dashboard/{user.UserRole}/')

class ForgotPasswordView(View):

    def get(self, request, user_type):

        step = request.session.get('reset_step', 1)

        return render(
            request,
            'forget_password.html',
            {
                'user_type': user_type,
                'step': step
            }
        )

    def post(self, request, user_type):

        action = request.POST.get('action')

        if action == 'send_otp':
            return self.send_otp(request, user_type)

        elif action == 'verify_otp':
            return self.verify_otp(request, user_type)

        elif action == 'reset_password':
            return self.reset_password(request, user_type)

        return redirect(
            f'/forget-password/{user_type}/'
        )

    def send_otp(self, request, user_type):

        username = request.POST.get('username')

        email = request.POST.get('email')

        user = User.objects.filter(
            username=username,
            email=email,
            UserRole=user_type
        ).first()

        if not user:

            messages.error(
                request,
                "User not found."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        otp = random.randint(100000, 999999)

        hashed_otp = hashlib.sha256(
            str(otp).encode()
        ).hexdigest()

        request.session['reset_user'] = user.id

        request.session['otp'] = hashed_otp

        request.session['otp_created_at'] = (
            timezone.now().timestamp()
        )

        request.session['otp_attempts'] = 0

        request.session['reset_step'] = 2

        request.session.set_expiry(300)

        send_forget_password_otp_email.delay(
            user.email,
            user.first_name,
            user.last_name,
            otp
        )

        messages.success(
            request,
            "OTP sent successfully."
        )

        return redirect(
            f'/forget-password/{user_type}/'
        )

    def verify_otp(self, request, user_type):

        entered_otp = request.POST.get('otp')

        if not entered_otp:

            messages.error(
                request,
                "Enter OTP."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        otp_created_time = request.session.get(
            'otp_created_at',
            0
        )

        if (
            timezone.now().timestamp()
            - otp_created_time
        ) > 300:

            messages.error(
                request,
                "OTP expired."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        attempts = request.session.get(
            'otp_attempts',
            0
        )

        if attempts >= 5:

            messages.error(
                request,
                "Too many attempts."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        hashed_entered = hashlib.sha256(
            entered_otp.encode()
        ).hexdigest()

        if hashed_entered == request.session.get('otp'):

            request.session['otp_verified'] = True

            request.session['reset_step'] = 3

            request.session.pop('otp', None)

            messages.success(
                request,
                "OTP verified successfully."
            )

        else:

            request.session['otp_attempts'] = attempts + 1

            messages.error(
                request,
                "Invalid OTP."
            )

        return redirect(
            f'/forget-password/{user_type}/'
        )

    def reset_password(self, request, user_type):

        if not request.session.get('otp_verified'):

            messages.error(
                request,
                "OTP verification required."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        new_password = request.POST.get('new_password')

        confirm_password = request.POST.get(
            'confirm_new_password'
        )

        if new_password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        user = User.objects.filter(
            id=request.session.get('reset_user')
        ).first()

        try:

            validate_password(
                new_password,
                user
            )

        except ValidationError as e:

            messages.error(
                request,
                e.messages[0]
            )

            return redirect(
                f'/forget-password/{user_type}/'
            )

        user.set_password(new_password)

        user.save()

        for key in [
            'otp',
            'reset_user',
            'otp_verified',
            'reset_step'
        ]:

            request.session.pop(key, None)

        messages.success(
            request,
            "Password reset successful."
        )

        return redirect(
            f'/login/{user_type}/'
        )


# =========================================================
# APPLICANT DASHBOARD
# =========================================================

class ApplicantDashboard(
    ApplicantRequiredMixin,
    View
):

    def get(self, request):

        today = timezone.now().date()

        jobs = JobPosts.objects.select_related(
            'posted_by'
        ).filter(
            last_date_to_apply__gte=today
        ).order_by('-posted_on')

        search = request.GET.get("job")

        if search:
            jobs = jobs.filter(
                job_title__icontains=search
            )

        return render(
            request,
            'app_dash.html',
            {
                'jobs': jobs
            }
        )


# =========================================================
# JOB DETAIL VIEW
# =========================================================

class JobDetailView(
    ApplicantRequiredMixin,
    View
):

    def get(self, request, pk):

        job = get_object_or_404(
            JobPosts,
            pk=pk
        )

        skills = []

        if job.skills_required:

            skills = [
                skill.strip()
                for skill in
                job.skills_required.split(',')
            ]

        return render(
            request,
            'description.html',
            {
                'job': job,
                'form': JobApplicationForm(),
                'skills': skills
            }
        )


# =========================================================
# APPLY JOB VIEW
# =========================================================

class ApplyJobView(
    ApplicantRequiredMixin,
    View
):

    def get(self, request, job_id):

        job = get_object_or_404(
            JobPosts,
            id=job_id
        )

        form = JobApplicationForm()

        return render(
            request,
            'APPLYJOB.html',
            {
                'job': job,
                'form': form
            }
        )

    def post(self, request, job_id):

        job = get_object_or_404(
            JobPosts,
            id=job_id
        )

        form = JobApplicationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            emails = form.cleaned_data['email']
            # print("EMAIL =", repr(emails))

            already_applied = JobApplications.objects.filter(
                job=job,
                user=request.user,
               email=emails
            ).exists()
            # print("ALREADY APPLIED =", already_applied)

            if already_applied:

                messages.error(
                    request,
                    "You already applied for this job."
                )
                return redirect('apply_job', job_id=job.id)

            else:

                application = form.save(commit=False)

                application.job = job

                application.user = request.user

                application.save()
                send_job_application_email.delay(application.id)
                messages.success(
                    request,
                    "Application submitted successfully."
                )

                return redirect(
                    'my_applied_jobs'
                )


        return render(
            request,
            'APPLYJOB.html',
            {
                'job': job,
                'form': form
            }
        )


# =========================================================
# HR DASHBOARD
# =========================================================

class HrDashboard(
    HrRequiredMixin,
    View
):

    def get(
        self,
        request,
        action=None,
        job_id=None
    ):

        today = timezone.now().date()

        job_posts = JobPosts.objects.filter(
            posted_by=request.user
        ).order_by('-posted_on')

        active_jobs_count = job_posts.filter(
            last_date_to_apply__gte=today
        ).count()

        total_applicants = JobApplications.objects.filter(
            job__posted_by=request.user
        ).count()

        accpected_applicants=JobApplications.objects.filter(job__posted_by=request.user,Status="Accpected").count()
        if action == 'jobpost':

            return render(
                request,
                'jobpost.html',
                {
                    'form': JobPostForm(),
                    'action': 'jobpost'
                }
            )

        if action == 'myjobs':

            return render(
                request,
                'my_jobs.html',
                {
                    'job_posts': job_posts,
                    'active_jobs_count': active_jobs_count
                }
            )

        if action == 'update_job':

            job = get_object_or_404(
                JobPosts,
                id=job_id,
                posted_by=request.user
            )

            return render(
                request,
                'jobpost.html',
                {
                    'form': JobPostForm(instance=job),
                    'action': 'update_job',
                    'job': job
                }
            )

        if action == 'delete_job':

            job = get_object_or_404(
                JobPosts,
                id=job_id,
                posted_by=request.user
            )

            job.delete()

            messages.success(
                request,
                "Job deleted successfully."
            )

            return redirect('my_jobs')

        return render(
            request,
            'hr_dash.html',
            {
                'active_jobs_count': active_jobs_count,
                'total_applicants':total_applicants,
                'accpected_applicants':accpected_applicants
            }
        )

    def post(
        self,
        request,
        action=None,
        job_id=None
    ):

        action = request.POST.get('action')

        if action == 'jobpost':

            form = JobPostForm(
                request.POST,
                request.FILES
            )

            if form.is_valid():

                job = form.save(commit=False)

                job.posted_by = request.user

                job.save()

                messages.success(
                    request,
                    "Job posted successfully."
                )

                return redirect('my_jobs')

            return render(
                request,
                'jobpost.html',
                {
                    'form': form,
                    'action': action
                }
            )

        if action == 'update_job':

            job = get_object_or_404(
                JobPosts,
                id=job_id,
                posted_by=request.user
            )

            form = JobPostForm(
                request.POST,
                request.FILES,
                instance=job
            )

            if form.is_valid():

                form.save()

                messages.success(
                    request,
                    "Job updated successfully."
                )

                return redirect('my_jobs')

            return render(
                request,
                'jobpost.html',
                {
                    'form': form,
                    'action': action
                }
            )

class MyAppliedjobs(ApplicantRequiredMixin,View):
    def get(self,request):
        applied_jobs=JobApplications.objects.select_related('job').filter(user=request.user).order_by('-id')
        search=request.GET.get('job')
        status=request.GET.get('status')
        if search:
            applied_jobs = applied_jobs.filter(
                job__job_title__icontains=search
            )
        if status:
            applied_jobs = applied_jobs.filter(
                Status=status
            )

        return render(request,'my_applications.html',{'applied_jobs':applied_jobs})


class TotalApplicants(HrRequiredMixin, View):

    def get(self, request):

        applications = JobApplications.objects.filter(
            job__posted_by=request.user
        ).select_related('job')

        search = request.GET.get('job')
        status = request.GET.get('status')
        if search:
            applications = applications.filter(
                job__job_title__icontains=search
            )
        if status:
            applications = applications.filter(
                Status=status
            )

        return render(
            request,
            'total_applications.html',
            {
                'total_applications': applications
            }
        )

class UpdateApplicantStatus(HrRequiredMixin,View):
    def post(self,request,pk):
        Applicants=get_object_or_404(
            JobApplications,
            id=pk,
            job__posted_by=request.user
        )
        status=request.POST.get('status')
        if status in ['Accpected','Rejected']:
            Applicants.Status=status
            Applicants.save()
            send_user_status_mail.delay(Applicants.id)
            if status == 'Rejected':
                Applicants.delete()
        return redirect('total_applications')

class ApplicantDetail(HrRequiredMixin,View):
    def get(self,request,pk):
        application=get_object_or_404(
            JobApplications,
            id=pk,
        )
        return render(request,'applicants.html',{'application': application})




class JobAnalyticsView(HrRequiredMixin, View):

    def get(self, request):

        # ==================================================
        # HR JOBS
        # ==================================================
        hr_jobs = JobPosts.objects.filter(
            posted_by=request.user
        )

        applications = (
            JobApplications.objects
            .filter(job__posted_by=request.user)
            .select_related('job', 'user')
        )

        # ==================================================
        # KPI CARDS
        # ==================================================
        total_jobs = hr_jobs.count()
        total_applications = applications.count()

        accepted_count = applications.filter(
            Status='Accpected'
        ).count()

        rejected_count = applications.filter(
            Status='Rejected'
        ).count()

        pending_count = applications.filter(
            Status='Pending'
        ).count()

        success_rate = 0

        if total_applications > 0:
            success_rate = round(
                (accepted_count / total_applications) * 100,
                2
            )

        # ==================================================
        # STATUS CHART
        # ==================================================
        status_labels = [
            'Accepted',
            'Pending',
            'Rejected'
        ]

        status_counts = [
            accepted_count,
            pending_count,
            rejected_count
        ]

        # ==================================================
        # APPLICATIONS PER JOB
        # ==================================================
        job_wise_data = (
            applications
            .values('job__job_title')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        job_titles = [
            item['job__job_title']
            for item in job_wise_data
        ]

        job_counts = [
            item['count']
            for item in job_wise_data
        ]

        # ==================================================
        # JOB TYPE ANALYTICS
        # ==================================================
        job_type_data = (
            applications
            .values('job__job_type')
            .annotate(count=Count('id'))
        )

        job_type_labels = [
            item['job__job_type']
            for item in job_type_data
        ]

        job_type_counts = [
            item['count']
            for item in job_type_data
        ]

        # ==================================================
        # MONTHLY TREND
        # ==================================================
        monthly_data = defaultdict(int)

        for app in applications:
            month = calendar.month_name[
                app.applied_on.month
            ]

            monthly_data[month] += 1

        month_order = list(calendar.month_name)[1:]

        months = [
            month
            for month in month_order
            if month in monthly_data
        ]

        monthly_counts = [
            monthly_data[month]
            for month in months
        ]

        # ==================================================
        # TOP PERFORMING JOB
        # ==================================================
        top_job = None

        if job_wise_data:
            top_job = job_wise_data[0]

        # ==================================================
        # RECRUITMENT FUNNEL
        # ==================================================
        funnel_labels = [
            'Applications',
            'Accepted',
            'Rejected'
        ]

        funnel_counts = [
            total_applications,
            accepted_count,
            rejected_count
        ]

        # ==================================================
        # CONTEXT
        # ==================================================
        context = {

            # KPI
            'total_jobs': total_jobs,
            'total_applications': total_applications,
            'accepted_count': accepted_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'success_rate': success_rate,

            # Status Chart
            'status_labels': status_labels,
            'status_counts': status_counts,

            # Job Wise Chart
            'job_titles': job_titles,
            'job_counts': job_counts,

            # Job Type Chart
            'job_type_labels': job_type_labels,
            'job_type_counts': job_type_counts,

            # Monthly Trend
            'months': months,
            'monthly_counts': monthly_counts,

            # Funnel
            'funnel_labels': funnel_labels,
            'funnel_counts': funnel_counts,

            # Insights
            'top_job': top_job,
        }

        return render(
            request,
            'analytics.html',
            context
        )

# =========================================================
# LOGOUT
# =========================================================

class Logout(
    LoginRequiredMixin,
    View
):

    login_url = '/land/'

    def get(self, request):

        logout(request)

        messages.success(
            request,
            "Logged out successfully."
        )

        return redirect('/land/')

