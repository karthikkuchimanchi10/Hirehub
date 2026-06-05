from django import forms
from django.forms import ModelForm
from .models import Users,JobPosts,JobApplications
from django.utils.timezone import now
import datetime
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


from django import forms
from django.forms import ModelForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import datetime
from .models import Users


class ApplicantRegistrationForm(ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )

    class Meta:
        model = Users
        fields = [
            'username',
            'first_name',
            'last_name',
            'Gender',
            'email',
            'Mobile_num',
            'DOB',
            'location',
            'password',
        ]

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'Gender': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'Mobile_num': forms.TextInput(attrs={'class': 'form-control'}),
            'DOB': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        return cleaned_data

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            validate_password(password)
        return password

    def clean_DOB(self):
        dob = self.cleaned_data.get("DOB")
        if dob and dob > datetime.date.today():
            raise forms.ValidationError("DOB cannot be in the future.")
        return dob

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if Users.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.UserRole = "applicant"
        user.is_approved = "Pending"

        if commit:
            user.save()

        return user

class HrRegistrationForm(ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )

    class Meta:
        model = Users
        fields = [
            'username',
            'first_name',
            'last_name',
            'Gender',
            'email',
            'Mobile_num',
            'DOB',
            'location',
            'company_name',
            'company_mail',
            'password',
        ]

        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'Gender': forms.Select(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'Mobile_num': forms.TextInput(attrs={'class': 'form-control'}),
            'DOB': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_mail': forms.EmailInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.UserRole = "hr"
        user.is_approved = "Pending"

        if commit:
            user.save()

        return user

class HrLoginForm(forms.Form):
    username = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Your Employee ID as username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Your Password'})
    )


class ApplicantLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Your Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Your Password'})
    )


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPosts
        fields = [
            'job_title',
            'company_name',
            'job_location',
            'job_type',
            'salary',
            'last_date_to_apply',
            'skills_required',
            'responsibilities',
            'job_description',
            'company_logo',
        ]

        widgets = {
            'job_title': forms.TextInput(attrs={
                'placeholder': 'Senior Software Engineer'
            }),
            'company_name': forms.TextInput(attrs={
                'placeholder': 'ABC Technologies'
            }),
            'job_location': forms.TextInput(attrs={
                'placeholder': 'Bangalore / Remote'
            }),
            'salary': forms.NumberInput(attrs={
                'min': 0,
                'placeholder': '80000'
            }),
            'last_date_to_apply': forms.DateInput(attrs={
                'type': 'date'
            }),
            'skills_required': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Python, Django, REST APIs'
            }),
            'responsibilities':forms.Textarea(attrs={
                'rows':5,
                'placeholder':'Logical Thinking,Problem Solving etc.'
            }),
            'job_description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe the role and responsibilities'
            }),
        }

    def clean_last_date_to_apply(self):
        date = self.cleaned_data['last_date_to_apply']
        if date < now().date():
            raise forms.ValidationError("Last date cannot be in the past.")
        return date

class JobApplicationForm(forms.ModelForm):
    graduation = forms.IntegerField(
        min_value=1900,
        max_value=datetime.date.today().year,
        widget=forms.NumberInput(attrs={'placeholder': 'YYYY'})
    )

    class Meta:
        model = JobApplications
        fields = [
            'first_name', 'last_name', 'age', 'email', 'mobile_num', 'gender',
            'highest_degree', 'field', 'graduation', 'institute', 'grade',
            'experience', 'exp_details', 'resume'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'John'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Doe'}),
            'age': forms.NumberInput(attrs={'min': 15, 'max': 100, 'placeholder': '25'}),
            'email': forms.EmailInput(attrs={'placeholder': 'john.doe@example.com'}),
            'mobile_num': forms.TextInput(attrs={'placeholder': '+1234567890'}),
            'gender': forms.Select(),
            'highest_degree': forms.Select(),
            'field': forms.TextInput(attrs={'placeholder': 'Computer Science'}),
            'institute': forms.TextInput(attrs={'placeholder': 'University Name'}),
            'grade': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '8.5'}),
            'experience': forms.Select(),
            'exp_details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your work experience...'}),
            'resume': forms.FileInput(),
        }

    def clean_age(self):
        age = self.cleaned_data['age']
        if age < 15 or age > 100:
            raise forms.ValidationError("Age must be between 15 and 100.")
        return age

    def clean_mobile_num(self):
        mobile = self.cleaned_data['mobile_num']
        if not mobile.replace('+', '').replace(' ', '').isdigit():
            raise forms.ValidationError("Enter a valid phone number.")
        return mobile

    def clean_graduation(self):
        year = self.cleaned_data['graduation']
        if year < 1900 or year > datetime.date.today().year:
            raise forms.ValidationError(f"Year must be between 1900 and {datetime.date.today().year}.")
        return year

    def clean(self):
        cleaned_data = super().clean()
        experience = cleaned_data.get('experience')
        exp_details = cleaned_data.get('exp_details')

        if experience == 'yes' and not exp_details:
            self.add_error('exp_details', 'Please provide your experience details.')
        if experience == 'no' and exp_details:
            self.add_error('exp_details', 'Experience details should be empty if you have no experience.')
        return cleaned_data