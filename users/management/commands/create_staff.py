from django.core.management.base import BaseCommand
from users.models import Staff


class Command(BaseCommand):
    help = 'Create a new staff member account'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Staff username')
        parser.add_argument('--email', type=str, required=True, help='Staff email')
        parser.add_argument('--password', type=str, required=True, help='Staff password')
        parser.add_argument('--first-name', type=str, default='', help='Staff first name')
        parser.add_argument('--last-name', type=str, default='', help='Staff last name')
        parser.add_argument('--role', type=str, default='OFFICER', help='Role: OFFICER, MANAGER, or ADMIN')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')
        role = options.get('role', 'OFFICER')

        # Check if staff already exists
        if Staff.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'Staff with username "{username}" already exists'))
            return

        if Staff.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Staff with email "{email}" already exists'))
            return

        # Create staff
        staff = Staff(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        staff.set_password(password)
        staff.save()

        self.stdout.write(self.style.SUCCESS(f'Staff member "{username}" created successfully'))
        self.stdout.write(self.style.SUCCESS(f'Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Email: {email}'))
        self.stdout.write(self.style.SUCCESS(f'Role: {staff.get_role_display()}'))
