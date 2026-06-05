from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import datetime
from django.utils.timezone import now
from cloudinary.models import CloudinaryField
# -------------------------------
# Custom User Model
# -------------------------------
class Users(AbstractUser):
    GENDERS = [('M', 'Male'), ('F', 'Female'), ('O', 'Others')]
    ROLES = [('applicant', 'Applicant'), ('hr', 'Recruiter')]
    EMP_STATUS = [('Fresher', 'Fresher'), ('Experienced', 'Experienced')]
    APPROVAL = [('Approved', 'Approved'), ('Pending', 'Pending'), ('Rejected', 'Rejected')]

    Gender = models.CharField(max_length=1, choices=GENDERS)
    UserRole = models.CharField(max_length=10, choices=ROLES)
    Mobile_num = models.CharField(max_length=15, null=False, blank=False, default='0')  # safer than IntegerField
    location = models.CharField(max_length=50, null=True, blank=True)
    DOB = models.DateField(null=True, blank=True)
    is_approved = models.CharField(max_length=10, choices=APPROVAL, default='Pending', null=True, blank=True)
    company_name = models.CharField(max_length=50, null=True, blank=True)
    company_mail = models.EmailField(max_length=50, null=True, blank=True)


    def __str__(self):
        return self.username


# -------------------------------
# Job Posts by Recruiters
# -------------------------------
class JobPosts(models.Model):
    JOB_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('INTERNSHIP', 'Internship'),
        ('FREELANCE', 'Freelance'),
    ]

    job_title = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    job_location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    salary = models.BigIntegerField(null=True, blank=True)  # BIGINT for large salaries
    skills_required = models.TextField(help_text="Comma-separated skills")
    responsibilities=models.TextField(blank=True, null=True)
    job_description = models.TextField(max_length=1000)
    company_logo = CloudinaryField('image', blank=True, null=True)
    posted_on = models.DateTimeField(auto_now_add=True)
    last_date_to_apply = models.DateField(default=now)
    posted_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='jobposts')

    class Meta:
        ordering = ['-posted_on']

    @property
    def is_active(self):
        return self.last_date_to_apply >= now().date()

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"


# -------------------------------
# General Job Table (DL / API output)
# -------------------------------
class Job(models.Model):
    id = models.BigIntegerField(primary_key=True)  # supports large IDs
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    required_skills = models.TextField()
    min_experience = models.PositiveIntegerField()
    max_experience = models.PositiveIntegerField()
    min_salary = models.BigIntegerField()
    max_salary = models.BigIntegerField()
    location = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title} at {self.company_name}"

class JobApplications(models.Model):
    # Gender Choices
    GENDERS = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Others'),
    ]

    # Degree Choices
    DEGREE_CHOICES = [
        ('high_school', 'High School Diploma'),
        ('associate', 'Associate Degree'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('phd', 'PhD/Doctorate'),
        ('professional', 'Professional Degree'),
        ('other', 'Other'),
    ]

    # Experience Choices
    EXPERIENCE_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]
    status_choices =[('Accpected','Accpected'),('Rejected','Rejected'),('Pending','Pending')]

    # Foreign Keys
    user = models.ForeignKey('Users', on_delete=models.CASCADE)
    job = models.ForeignKey('JobPosts', on_delete=models.CASCADE)

    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(validators=[MinValueValidator(15), MaxValueValidator(100)])
    email = models.EmailField(max_length=100, unique=False)
    mobile_num = models.CharField(max_length=15,validators=[RegexValidator(r'^\+?\d{7,15}$', message="Enter a valid phone number.")])
    gender = models.CharField(max_length=1, choices=GENDERS, default='O')

    # Education Details
    highest_degree = models.CharField("Highest Qualification", max_length=20, choices=DEGREE_CHOICES)
    field = models.CharField("Field of Qualification", max_length=100)
    graduation = models.PositiveIntegerField("Year of Graduation",validators=[MinValueValidator(1900), MaxValueValidator(datetime.date.today().year)] )
    institute = models.CharField("Institute Name", max_length=100)
    grade = models.DecimalField("Last Grade", max_digits=4, decimal_places=2)

    # Work Experience
    experience = models.CharField("Work Experience", max_length=3, choices=EXPERIENCE_CHOICES)
    exp_details = models.TextField("Experience Details", blank=True, null=True)

    # Resume Upload
    resume = CloudinaryField(
        resource_type="raw",
        blank=True,
        null=True
    )
    applied_on = models.DateTimeField(auto_now_add=True)    # String Representation
    Status = models.CharField("Status", max_length=20, choices=status_choices, default='Pending')
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job}"

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        constraints = [
            models.UniqueConstraint(fields=['email', 'job'], name='unique_email_per_job')
        ]