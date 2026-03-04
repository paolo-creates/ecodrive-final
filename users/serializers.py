from rest_framework import serializers
from .models import Borrower, Loan, Payment, MonthlyCollection, MonthlyRelease, EbikeModel, PaymentSchedule, Staff

class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = Staff
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'role', 'role_display', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'role_display']

class EbikeModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EbikeModel
        fields = ['id', 'name', 'srp', 'downpayment', 'installment_6_months', 
                  'installment_12_months', 'installment_15_months', 'installment_18_months', 
                  'installment_24_months', 'created_at', 'updated_at']

class BorrowerSerializer(serializers.ModelSerializer):
    # This pulls from the @property in your model
    full_name = serializers.ReadOnlyField() 

    class Meta:
        model = Borrower
        fields = [
            'id', 'first_name', 'middle_name', 'last_name', 
            'full_name', 'address', 'email', 'mobile_number'
        ]

class MonthlyReleaseSerializer(serializers.ModelSerializer):
    # Pulling reference number directly from the related Loan's ID
    reference_number = serializers.ReadOnlyField()

    class Meta:
        model = MonthlyRelease
        fields = ['id', 'reference_number', 'date_released', 'down_payment']

class PaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSchedule
        fields = ['id', 'installment_number', 'due_date', 'amount', 'status']
        read_only_fields = ['id', 'installment_number', 'due_date', 'amount', 'status']

class LoanSerializer(serializers.ModelSerializer):
    # Use nested BorrowerSerializer to get borrower details
    borrower = BorrowerSerializer(read_only=True)
    borrower_name = serializers.ReadOnlyField(source='borrower.full_name')
    term_label = serializers.CharField(source='get_term_display', read_only=True)
    
    # New Scheduling Fields
    next_payment_date = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    monthly_payment = serializers.ReadOnlyField()
    remaining_months = serializers.ReadOnlyField()
    paid_months = serializers.ReadOnlyField()
    
    # Nested Release Details & Payment Schedule
    release_details = MonthlyReleaseSerializer(read_only=True)
    payment_schedules = PaymentScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_id', 'borrower', 'borrower_name', 
            'amount', 'remaining_balance', 'term', 'term_label', 
            'monthly_payment', 'remaining_months', 'paid_months',
            'status', 'is_overdue', 'next_payment_date', 
            'date_issued', 'release_details', 'payment_schedules'
        ]
        read_only_fields = ['loan_id', 'remaining_balance', 'status', 'date_issued']

class PaymentSerializer(serializers.ModelSerializer):
    # Fix: Changed source to use full_name
    borrower_name = serializers.ReadOnlyField(source='loan.borrower.full_name')

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'loan', 'borrower_name', 
            'amount', 'payment_date'
        ]
        read_only_fields = ['payment_id', 'payment_date']

class MonthlyCollectionSerializer(serializers.ModelSerializer):
    # Fix: Changed source to use full_name
    borrower_name = serializers.ReadOnlyField(source='borrower.full_name')
    
    class Meta:
        model = MonthlyCollection
        fields = [
            'id', 'payment', 'borrower', 'borrower_name', 
            'amount', 'payment_type', 'month_for'
        ]