# Generated migration for LoanPlan model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('months', models.IntegerField(help_text='Loan term in months', unique=True)),
                ('interest_rate', models.DecimalField(decimal_places=2, help_text='Monthly interest rate (%)', max_digits=5)),
                ('overdue_penalty', models.DecimalField(decimal_places=2, help_text='Monthly overdue penalty (%)', max_digits=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['months'],
            },
        ),
    ]
