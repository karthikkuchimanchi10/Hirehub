from django.contrib import admin
from django.urls import path, include
from jobapp import views
from django.conf import settings
from django.conf.urls.static import static
from jobapp.views import chatbot_api, MyAppliedjobs, TotalApplicants, UpdateApplicantStatus, ApplicantDetail, \
    JobAnalyticsView

urlpatterns = [

    # Admin
    path('admin/', admin.site.urls),

    # Landing
    path('', views.landing_page, name='home'),
    path('land/', views.landing_page, name='land'),

    # Allauth (Google, GitHub, etc.)
    path('accounts/', include('allauth.urls')),

    # =============================
    # 🔐 Authentication
    # =============================
    path('login/<str:user_type>/', views.LoginView.as_view(), name='login'),
    path( 'chatbot/', chatbot_api, name='chatbot_api' ),
    path('register/<str:user_type>/', views.UserRegistrationView.as_view(), name='register'),
    path('forget-password/<str:user_type>/', views.ForgotPasswordView.as_view(), name='forget_password'),
    path('logout/', views.Logout.as_view(), name='logout'),

    # =============================
    # 👤 Applicant
    # =============================
    path('dashboard/applicant/', views.ApplicantDashboard.as_view(), name='applicant_dashboard'),
    path('job/<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('apply-job/<int:job_id>/', views.ApplyJobView.as_view(), name='apply_job'),
    path('my-applied-jobs/', MyAppliedjobs.as_view(), name='my_applied_jobs'),

    # =============================
    # 🧑‍💼 HR Dashboard
    # =============================
    path('dashboard/hr/', views.HrDashboard.as_view(), name='hr_dashboard'),

    # Actions (clean routing)
    path('dashboard/hr/jobpost/', views.HrDashboard.as_view(), {'action': 'jobpost'}, name='job_post'),
    path('dashboard/hr/myjobs/', views.HrDashboard.as_view(), {'action': 'myjobs'}, name='my_jobs'),
    path('dashboard/hr/update/<int:job_id>/', views.HrDashboard.as_view(), {'action': 'update_job'}, name='update_job'),
    path('dashboard/hr/delete/<int:job_id>/', views.HrDashboard.as_view(), {'action': 'delete_job'}, name='delete_job'),
    path('applicants/',TotalApplicants.as_view(), name='total_applications'),
    path('update-status/<int:pk>/status/',UpdateApplicantStatus.as_view(), name='update_status'),
    path('applicant-detail/<int:pk>/',ApplicantDetail.as_view(), name='application_details'),
    path('analytics/',JobAnalyticsView.as_view(),name='job_analytics'),
]

# =============================
# 📁 Media Files (Dev Only)
# =============================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)