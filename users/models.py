import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password

def generate_unique_id(prefix):
    date_str = timezone.now().strftime('%Y%m%d')
    short_uuid = str(uuid.uuid4()).upper()[:6]
    return f"{prefix}-{date_str}-{short_uuid}"

class Staff(models.Model):
    """Staff model for admin users with email or username login"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('OFFICER', 'Loan Officer'),
    ]
    
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='OFFICER')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Staff'
        verbose_name_plural = 'Staff'
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def set_password(self, raw_password):
        """Hash and set password"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Verify raw password against hashed password"""
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

class Borrower(models.Model):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    address = models.TextField()
    email = models.EmailField(blank=True, null=True)
    mobile_number = models.CharField(max_length=20)

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name

class EbikeModel(models.Model):
    """E-bike model with pricing and available installment terms"""
    name = models.CharField(max_length=255, unique=True)
    srp = models.DecimalField(max_digits=12, decimal_places=2,help_text="Suggested Retail Price")
    downpayment = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Installment plans - monthly payment for each term
    installment_6_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    installment_12_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    installment_15_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    installment_18_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    installment_24_months = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Available installment months
    INSTALLMENT_MONTHS = [6, 12, 15, 18, 24]

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Loan(models.Model):
    TERM_CHOICES = [(6, '6 Months'), (12, '12 Months'), (15, '15 Months'), (18, '18 Months'), (24, '24 Months')]
    STATUS_CHOICES = [('ACTIVE', 'Active'), ('COMPLETED', 'Completed'), ('OVERDUE', 'Overdue')]

    loan_id = models.CharField(max_length=25, unique=True, editable=False, null=True, blank=True)
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE, related_name='loans')
    ebike_model = models.ForeignKey(EbikeModel, on_delete=models.PROTECT, related_name='loans', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2, editable=False, null=True, blank=True)
    term = models.IntegerField(choices=TERM_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    date_issued = models.DateField(auto_now_add=True)

    @property
    def monthly_payment(self):
        """Get the monthly payment amount from ebike model based on term"""
        if not self.ebike_model:
            return 0
        installment_field = f'installment_{self.term}_months'
        return getattr(self.ebike_model, installment_field, 0) or 0
    
    @property
    def remaining_months(self):
        """Count of unpaid installments remaining"""
        return self.payment_schedules.filter(status='PENDING').count()
    
    @property
    def paid_months(self):
        """Count of paid installments"""
        return self.payment_schedules.filter(status='PAID').count()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            self.loan_id = generate_unique_id("LOAN")
            # Calculate remaining_balance as: term × monthly_payment
            monthly_payment = self.monthly_payment
            self.remaining_balance = monthly_payment * self.term
        super().save(*args, **kwargs)
        
        # Generate payment schedule on first save
        if is_new:
            self._generate_payment_schedule()
    
    def _generate_payment_schedule(self):
        """Generate monthly payment schedule starting from loan date"""
        monthly_payment = self.monthly_payment
        current_date = self.date_issued
        
        # Clear existing schedules (if any)
        self.payment_schedules.all().delete()
        
        # Create installment schedule for each month
        for i in range(1, self.term + 1):
            due_date = current_date + timedelta(days=30 * i)
            PaymentSchedule.objects.create(
                loan=self,
                installment_number=i,
                due_date=due_date,
                amount=monthly_payment
            )

    @property
    def next_payment_date(self):
        """Get the next pending payment date from the payment schedule"""
        # Get the first pending schedule item
        pending_schedule = self.payment_schedules.filter(status='PENDING').order_by('installment_number').first()
        if pending_schedule:
            return pending_schedule.due_date
        # If no pending schedules, return last payment date + 30 days
        last_payment = self.payments.order_by('-payment_date').first()
        base_date = last_payment.payment_date.date() if last_payment else self.date_issued
        return base_date + timedelta(days=30)

    @property
    def is_overdue(self):
        if self.status == 'COMPLETED':
            return False
        return timezone.now().date() > self.next_payment_date

    def __str__(self):
        return f"{self.loan_id} - {self.borrower.full_name}"

class MonthlyRelease(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='release_details')
    date_released = models.DateField(default=timezone.now)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def reference_number(self):
        return self.loan.loan_id

    def __str__(self):
        return f"Release: {self.reference_number}"

class PaymentSchedule(models.Model):
    """Tracks individual installments for a loan"""
    STATUS_CHOICES = [('PENDING', 'Pending'), ('PAID', 'Paid')]
    
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payment_schedules')
    installment_number = models.IntegerField()  # 1st, 2nd, 3rd, etc.
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, null=True, blank=True, related_name='schedule_items')
    
    class Meta:
        ordering = ['loan', 'installment_number']
        unique_together = ('loan', 'installment_number')
    
    def __str__(self):
        return f"{self.loan.loan_id} - Installment {self.installment_number}"

class Payment(models.Model):
    payment_id = models.CharField(max_length=25, unique=True, editable=False, null=True, blank=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None 
        with transaction.atomic():
            if not self.payment_id:
                self.payment_id = generate_unique_id("PAY")
            
            if is_new:
                # Ensure amount is a Decimal
                payment_amount = Decimal(str(self.amount)) if not isinstance(self.amount, Decimal) else self.amount
                
                # Update Loan Balance
                self.loan.remaining_balance -= payment_amount
                if self.loan.remaining_balance <= 0:
                    self.loan.remaining_balance = 0
                    self.loan.status = 'COMPLETED'
                self.loan.save()
                
                # Mark the earliest pending schedule item as paid
                pending_schedule = self.loan.payment_schedules.filter(status='PENDING').order_by('installment_number').first()
                if pending_schedule:
                    pending_schedule.status = 'PAID'
                    pending_schedule.payment = None  # Will be set after super().save()
                    pending_schedule.save()

            super().save(*args, **kwargs)
            
            # Now update the schedule item with this payment reference
            if is_new:
                paid_schedule = self.loan.payment_schedules.filter(status='PAID', payment__isnull=True).order_by('installment_number').first()
                if paid_schedule:
                    paid_schedule.payment = self
                    paid_schedule.save()

            # Create or Update Monthly Collection Record
            p_date = self.payment_date.date() if self.payment_date else timezone.now().date()
            MonthlyCollection.objects.get_or_create(
                payment=self,
                borrower=self.loan.borrower,
                defaults={
                    'amount': self.amount,
                    'month_for': p_date.replace(day=1)
                }
            )

    def __str__(self):
        return f"{self.payment_id} - {self.amount}"

class MonthlyCollection(models.Model):
    PAYMENT_TYPES = [('CASH', 'Cash'), ('TRANSFER', 'Bank Transfer'), ('GCASH', 'GCash')]

    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='CASH')
    month_for = models.DateField()

    def __str__(self):
        return f"{self.month_for.strftime('%B %Y')} - {self.borrower.full_name}"