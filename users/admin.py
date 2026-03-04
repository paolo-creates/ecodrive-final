from django.contrib import admin
from .models import Borrower, Loan, Payment, MonthlyCollection, MonthlyRelease, EbikeModel

@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile_number', 'email')
    search_fields = ('first_name', 'last_name', 'mobile_number')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_id', 'borrower', 'amount', 'remaining_balance', 'status', 'date_issued')
    list_filter = ('status', 'term', 'date_issued')
    search_fields = ('loan_id', 'borrower__first_name', 'borrower__last_name')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'loan', 'amount', 'payment_date')
    list_filter = ('payment_date',)
    search_fields = ('payment_id', 'loan__loan_id')

@admin.register(MonthlyCollection)
class MonthlyCollectionAdmin(admin.ModelAdmin):
    list_display = ('month_for', 'borrower', 'amount', 'payment_type')
    list_filter = ('payment_type', 'month_for')
    search_fields = ('borrower__first_name', 'borrower__last_name')

@admin.register(MonthlyRelease)
class MonthlyReleaseAdmin(admin.ModelAdmin):
    list_display = ('loan', 'date_released', 'down_payment')
    list_filter = ('date_released',)
    search_fields = ('loan__loan_id',)

@admin.register(EbikeModel)
class EbikeModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'srp', 'downpayment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('name',)
