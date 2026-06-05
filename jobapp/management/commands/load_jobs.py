import csv
from django.core.management.base import BaseCommand
from jobapp.models import Job

class Command(BaseCommand):
    help = "Load jobs from CSV"

    def handle(self, *args, **kwargs):
        with open('job_table_5000.csv', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            count = 0
            for row in reader:
                Job.objects.create(
                    id=int(row['job_id']),  # assuming CSV has job IDs
                    title=row['title'],
                    company_name=row['company_name'],
                    required_skills=row['required_skills'],  # matches model
                    location=row['location'],
                    min_experience=int(row['min_experience']),
                    max_experience=int(row['max_experience']),
                    min_salary=int(row['min_salary']),
                    max_salary=int(row['max_salary'])
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{count} jobs loaded successfully")
        )
