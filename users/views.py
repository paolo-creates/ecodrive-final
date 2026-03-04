from django.shortcuts import render
import json
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from .models import Borrower, Loan, Payment, MonthlyCollection, MonthlyRelease, EbikeModel, Staff
from .serializers import (
    BorrowerSerializer, LoanSerializer, 
    PaymentSerializer, MonthlyCollectionSerializer,
    MonthlyReleaseSerializer, EbikeModelSerializer, StaffSerializer
)

class BorrowerViewSet(viewsets.ModelViewSet):
    # Fixed: Changed 'name' to 'last_name' for ordering
    queryset = Borrower.objects.all().order_by('last_name', 'first_name')
    serializer_class = BorrowerSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    # Fixed: Search by split name fields
    search_fields = ['first_name', 'last_name', 'mobile_number']
    
    def get_permissions(self):
        """Allow any authenticated user to list borrowers, only admins can modify"""
        if self.action == 'list':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all().order_by('-date_issued')
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'term']
    # Fixed: Search by split name fields in the related borrower model
    search_fields = ['loan_id', 'borrower__first_name', 'borrower__last_name']

class MonthlyReleaseViewSet(viewsets.ModelViewSet):
    """
    New viewset for tracking the release of units, down payments, and references.
    """
    queryset = MonthlyRelease.objects.all().order_by('-date_released')
    serializer_class = MonthlyReleaseSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['loan']
    search_fields = ['unit', 'loan__loan_id']

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['loan']

class EbikeModelViewSet(viewsets.ModelViewSet):
    queryset = EbikeModel.objects.all().order_by('name')
    serializer_class = EbikeModelSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('-created_at')
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']

class MonthlyCollectionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MonthlyCollection.objects.all().order_by('-month_for')
    serializer_class = MonthlyCollectionSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['month_for', 'payment_type']

# --- Auth and Page Views ---

@csrf_exempt
def add_payment(request):
    """Add a new payment"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            loan_id = data.get('loan_id')
            
            # Validate loan_id
            if not loan_id:
                return JsonResponse({'status': 'error', 'message': 'Loan ID is required'}, status=400)
            
            # Get the loan
            try:
                loan = Loan.objects.get(id=loan_id)
            except Loan.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'Loan not found (ID: {loan_id})'}, status=404)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': f'Invalid loan ID format: {loan_id}'}, status=400)
            
            # Validate and parse amount
            try:
                amount = Decimal(str(data.get('amount', 0)))
                if amount <= 0:
                    return JsonResponse({'status': 'error', 'message': 'Amount must be greater than 0'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': f'Invalid amount format: {data.get("amount")}'}, status=400)
            
            payment_type = data.get('payment_type', 'CASH')
            
            # Create payment - this will automatically create MonthlyCollection via the save() method
            payment = Payment.objects.create(
                loan=loan,
                amount=amount
            )
            
            # Update the MonthlyCollection with payment type
            try:
                monthly_collection = MonthlyCollection.objects.get(payment=payment)
                monthly_collection.payment_type = payment_type
                monthly_collection.save()
            except MonthlyCollection.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'MonthlyCollection was not created'}, status=400)
            
            # Refresh loan to get updated value
            loan.refresh_from_db()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Payment added successfully',
                'payment_id': payment.payment_id,
                'loan_remaining_balance': str(loan.remaining_balance)
            })
        except json.JSONDecodeError as e:
            return JsonResponse({'status': 'error', 'message': f'Invalid JSON: {str(e)}'}, status=400)
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': f'Error: {error_msg}'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def get_loan_statistics(request):
    """Get updated monthly statistics for releases and collections"""
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    try:
        # Get current month and year
        today = timezone.now()
        current_month_start = today.replace(day=1)
        next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)
        
        # Calculate THIS MONTH's releases (SRP of ebike models released)
        monthly_releases = MonthlyRelease.objects.filter(
            date_released__gte=current_month_start,
            date_released__lt=next_month_start
        ).select_related('loan__ebike_model')
        
        this_month_releases = Decimal('0')
        for release in monthly_releases:
            if release.loan.ebike_model:
                this_month_releases += release.loan.ebike_model.srp
        
        # Calculate THIS MONTH's collections
        monthly_collections = MonthlyCollection.objects.filter(
            month_for=current_month_start
        )
        this_month_collections = sum(Decimal(str(mc.amount)) for mc in monthly_collections)
        
        return JsonResponse({
            'status': 'success',
            'this_month_releases': str(this_month_releases),
            'this_month_collections': str(this_month_collections),
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@csrf_exempt
def login_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return JsonResponse({"error": "Username and password are required"}, status=400)

            # First try to authenticate as Django superuser/admin
            from django.contrib.auth.models import User
            django_user = None
            try:
                django_user = User.objects.get(username=username)
                if django_user.check_password(password):
                    # Django superuser authenticated
                    # Set the backend explicitly since we have multiple backends
                    django_user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, django_user)
                    return JsonResponse({
                        "message": "Login successful",
                        "user_id": django_user.id,
                        "username": django_user.username,
                        "email": django_user.email,
                        "role": "Administrator" if django_user.is_superuser else "Staff",
                        "is_superuser": django_user.is_superuser
                    }, status=200)
                else:
                    # Password is incorrect for Django user
                    pass
            except User.DoesNotExist:
                # Django user not found, try Staff model
                pass

            # If not a Django superuser, try Staff model
            staff = None
            try:
                # Try by username
                staff = Staff.objects.get(username=username)
            except Staff.DoesNotExist:
                try:
                    # Try by email
                    staff = Staff.objects.get(email=username)
                except Staff.DoesNotExist:
                    pass

            if staff:
                # Check if staff is active
                if not staff.is_active:
                    return JsonResponse({"error": "Staff account is inactive"}, status=401)

                # Verify password
                if not staff.check_password(password):
                    return JsonResponse({"error": "Invalid password"}, status=401)

                # Create session for staff
                request.session['staff_id'] = staff.id
                request.session['staff_username'] = staff.username
                request.session['staff_role'] = staff.role
                request.session.set_expiry(86400)  # 24 hours
                request.session.save()

                return JsonResponse({
                    "message": "Login successful",
                    "staff_id": staff.id,
                    "username": staff.username,
                    "email": staff.email,
                    "role": staff.get_role_display()
                }, status=200)

            # No user found in either Django User or Staff
            return JsonResponse({"error": "Invalid username/email or password"}, status=401)

        except json.JSONDecodeError as e:
            return JsonResponse({"error": f"Invalid JSON: {str(e)}"}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

# Standard Django Template Views
def index(request):
    return render(request, "index.html")

def homepage(request):
    from django.db.models import Q, Sum
    from datetime import date
    
    # Get counts
    active_loans_count = Loan.objects.filter(status='ACTIVE').count()
    borrowers_count = Borrower.objects.count()
    overdue_loans_count = Loan.objects.filter(status='OVERDUE').count()
    completed_loans_count = Loan.objects.filter(status='COMPLETED').count()
    completed_loans_total = Loan.objects.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
    
    # Get current month and year
    today = date.today()
    current_month_start = today.replace(day=1)
    
    # Get monthly releases for current month (sum of ebike model SRP)
    monthly_releases = MonthlyRelease.objects.filter(
        date_released__gte=current_month_start
    ).select_related('loan__ebike_model')
    monthly_releases_total = Decimal('0')
    for release in monthly_releases:
        if release.loan.ebike_model:
            monthly_releases_total += release.loan.ebike_model.srp
    
    # Get monthly collections for current month
    monthly_collections_total = MonthlyCollection.objects.filter(
        month_for__year=today.year,
        month_for__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'active_loans_count': active_loans_count,
        'borrowers_count': borrowers_count,
        'overdue_loans_count': overdue_loans_count,
        'completed_loans_count': completed_loans_count,
        'completed_loans_total': completed_loans_total,
        'monthly_releases_total': monthly_releases_total,
        'monthly_collections_total': monthly_collections_total,
        'current_month': today.strftime('%B %Y'),
    }
    
    return render(request, "Homepage.html", context)

def adminloanslist(request):
    from django.utils import timezone
    from datetime import datetime, timedelta
    from decimal import Decimal
    
    loans = Loan.objects.all().select_related('borrower', 'release_details').prefetch_related('payments')
    
    # Get current month and year
    today = timezone.now()
    current_month_start = today.replace(day=1)
    next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)
    
    # Calculate THIS MONTH's releases (SRP of ebike models released this month)
    monthly_releases = MonthlyRelease.objects.filter(
        date_released__gte=current_month_start,
        date_released__lt=next_month_start
    ).select_related('loan__borrower', 'loan__ebike_model').order_by('-date_released')
    
    total_releases = Decimal('0')
    for release in monthly_releases:
        if release.loan.ebike_model:
            total_releases += release.loan.ebike_model.srp
    
    # Calculate THIS MONTH's collections
    monthly_collections = MonthlyCollection.objects.filter(
        month_for=current_month_start
    ).select_related('borrower', 'payment')
    
    total_collections = sum(Decimal(str(mc.amount)) for mc in monthly_collections)
    
    context = {
        'loans': loans,
        'monthly_releases': monthly_releases,
        'total_releases': total_releases,
        'monthly_collections': monthly_collections,
        'total_collections': total_collections,
        'collections_count': monthly_collections.count(),
        'current_month': current_month_start,
    }
    return render(request, "Adminloanslist.html", context)

def adminpayment(request):
    payments = Payment.objects.all().select_related('loan__borrower').order_by('-payment_date')
    context = {
        'payments': payments,
    }
    return render(request, "Adminpayment.html", context)

def adminborrower(request):
    borrowers = Borrower.objects.all().order_by('last_name', 'first_name')
    context = {
        'borrowers': borrowers,
    }
    return render(request, "Adminborrower.html", context)

def admin_ebike(request):
    ebike_models = EbikeModel.objects.all().order_by('name')
    context = {
        'ebike_models': ebike_models,
    }
    return render(request, "AdminEbike.html", context)

def admin_staff(request):
    staff_members = Staff.objects.all().order_by('-created_at')
    context = {
        'staff_members': staff_members,
    }
    return render(request, "AdminStaff.html", context)

def forgotpass(request):
    return render(request, "forgotpass.html")

def resetpass(request):
    return render(request, "resetpass.html")

def otp(request):
    return render(request, "otp.html")

# API Endpoints for Adding Data

@csrf_exempt
@login_required(login_url="/")
def get_borrowers_json(request):
    """Simple JSON endpoint for borrower dropdown"""
    if request.method == "GET":
        try:
            borrowers = Borrower.objects.all().order_by('last_name', 'first_name').values('id', 'first_name', 'last_name', 'mobile_number')
            borrowers_list = list(borrowers)
            print(f"DEBUG: Found {len(borrowers_list)} borrowers")
            return JsonResponse({
                'results': borrowers_list,
                'count': len(borrowers_list)
            })
        except Exception as e:
            print(f"ERROR in get_borrowers_json: {str(e)}")
            return JsonResponse({
                'error': str(e),
                'results': []
            }, status=500)
    return JsonResponse({'error': 'Method not allowed', 'results': []}, status=405)

@csrf_exempt
def add_borrower(request):
    """Add a new borrower"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            borrower = Borrower.objects.create(
                first_name=data.get('first_name', ''),
                middle_name=data.get('middle_name', ''),
                last_name=data.get('last_name', ''),
                address=data.get('address', ''),
                email=data.get('email', ''),
                mobile_number=data.get('mobile_number', '')
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Borrower added successfully',
                'borrower_id': borrower.id,
                'borrower_name': borrower.full_name
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def edit_borrower(request, borrower_id):
    """Edit an existing borrower"""
    if request.method == "POST":
        try:
            try:
                borrower = Borrower.objects.get(id=borrower_id)
            except Borrower.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Borrower not found'}, status=404)
            
            data = json.loads(request.body)
            
            # Update borrower fields
            borrower.first_name = data.get('first_name', borrower.first_name)
            borrower.middle_name = data.get('middle_name', borrower.middle_name)
            borrower.last_name = data.get('last_name', borrower.last_name)
            borrower.address = data.get('address', borrower.address)
            borrower.email = data.get('email', borrower.email)
            borrower.mobile_number = data.get('mobile_number', borrower.mobile_number)
            borrower.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Borrower updated successfully',
                'borrower_id': borrower.id,
                'borrower_name': borrower.full_name
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def delete_borrower(request, borrower_id):
    """Delete a borrower"""
    if request.method == "POST":
        try:
            try:
                borrower = Borrower.objects.get(id=borrower_id)
            except Borrower.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Borrower not found'}, status=404)
            
            borrower_name = borrower.full_name
            borrower.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Borrower deleted successfully',
                'borrower_name': borrower_name
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def add_staff(request):
    """Add a new staff member"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            role = data.get('role', 'OFFICER')
            
            # Validation
            if not username or not email or not password:
                return JsonResponse({'status': 'error', 'message': 'Username, email, and password are required'}, status=400)
            
            # Check if staff already exists
            if Staff.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already exists'}, status=400)
            
            if Staff.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
            
            # Create new staff
            staff = Staff(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            staff.set_password(password)
            staff.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Staff member added successfully',
                'id': staff.id,
                'username': staff.username,
                'email': staff.email,
                'full_name': staff.full_name,
                'role': staff.get_role_display()
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def edit_staff(request, staff_id):
    """Edit a staff member"""
    if request.method == "POST":
        try:
            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Staff member not found'}, status=404)
            
            data = json.loads(request.body)
            
            # Update fields
            staff.email = data.get('email', staff.email).strip()
            staff.first_name = data.get('first_name', staff.first_name).strip()
            staff.last_name = data.get('last_name', staff.last_name).strip()
            staff.role = data.get('role', staff.role)
            staff.is_active = data.get('is_active', staff.is_active)
            
            # Update password if provided
            if 'password' in data and data.get('password', '').strip():
                staff.set_password(data.get('password'))
            
            staff.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Staff member updated successfully',
                'id': staff.id,
                'username': staff.username,
                'email': staff.email,
                'full_name': staff.full_name,
                'role': staff.get_role_display(),
                'is_active': staff.is_active
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def delete_staff(request, staff_id):
    """Delete a staff member"""
    if request.method == "POST":
        try:
            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Staff member not found'}, status=404)
            
            staff_name = staff.full_name
            staff.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Staff member deleted successfully',
                'staff_name': staff_name
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def logout_api(request):
    """Logout staff member"""
    if request.method == "POST":
        # Clear staff session
        if 'staff_id' in request.session:
            del request.session['staff_id']
        if 'staff_username' in request.session:
            del request.session['staff_username']
        if 'staff_role' in request.session:
            del request.session['staff_role']
        
        return JsonResponse({
            "message": "Logout successful"
        })
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def add_loan(request):
    """Add a new loan"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            borrower_id = data.get('borrower_id')
            
            try:
                borrower = Borrower.objects.get(id=borrower_id)
            except Borrower.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Borrower not found'}, status=404)
            
            # Get ebike model if provided
            ebike_model = None
            if data.get('ebike_model_id'):
                try:
                    ebike_model = EbikeModel.objects.get(id=data.get('ebike_model_id'))
                except EbikeModel.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Ebike model not found'}, status=404)
            
            loan = Loan.objects.create(
                borrower=borrower,
                ebike_model=ebike_model,
                amount=float(data.get('amount', 0)),
                term=int(data.get('term', 12))
            )
            
            # Create release details if provided
            if data.get('down_payment') is not None:
                MonthlyRelease.objects.create(
                    loan=loan,
                    down_payment=float(data.get('down_payment', 0))
                )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Loan added successfully',
                'loan_id': loan.loan_id,
                'loan_amount': str(loan.amount)
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
@login_required(login_url="/")
def manage_ebike_model(request, model_id=None):
    """Manage ebike models (create, update, delete)"""
    if request.method == "POST":
        # Create new ebike model
        try:
            data = json.loads(request.body)
            name = data.get('name')
            srp = float(data.get('srp'))
            downpayment = float(data.get('downpayment'))
            installment_6_months = float(data.get('installment_6_months'))
            installment_12_months = float(data.get('installment_12_months'))
            installment_15_months = float(data.get('installment_15_months'))
            installment_18_months = float(data.get('installment_18_months'))
            installment_24_months = float(data.get('installment_24_months'))
            
            # Check if model with this name already exists
            existing = EbikeModel.objects.filter(name=name)
            if existing.exists():
                return JsonResponse({'status': 'error', 'message': 'An ebike model with this name already exists'}, status=400)
            
            model = EbikeModel.objects.create(
                name=name,
                srp=srp,
                downpayment=downpayment,
                installment_6_months=installment_6_months,
                installment_12_months=installment_12_months,
                installment_15_months=installment_15_months,
                installment_18_months=installment_18_months,
                installment_24_months=installment_24_months
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ebike model created successfully',
                'id': model.id,
                'name': model.name,
                'srp': float(model.srp),
                'downpayment': float(model.downpayment),
                'installment_6_months': float(model.installment_6_months),
                'installment_12_months': float(model.installment_12_months),
                'installment_15_months': float(model.installment_15_months),
                'installment_18_months': float(model.installment_18_months),
                'installment_24_months': float(model.installment_24_months)
            })
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': 'Invalid input values'}, status=400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    elif request.method == "PUT":
        # Update existing ebike model
        try:
            if not model_id:
                return JsonResponse({'status': 'error', 'message': 'Model ID required'}, status=400)
            
            model = EbikeModel.objects.get(id=model_id)
            data = json.loads(request.body)
            
            model.name = data.get('name', model.name)
            model.srp = float(data.get('srp', model.srp))
            model.downpayment = float(data.get('downpayment', model.downpayment))
            model.installment_6_months = float(data.get('installment_6_months', model.installment_6_months))
            model.installment_12_months = float(data.get('installment_12_months', model.installment_12_months))
            model.installment_15_months = float(data.get('installment_15_months', model.installment_15_months))
            model.installment_18_months = float(data.get('installment_18_months', model.installment_18_months))
            model.installment_24_months = float(data.get('installment_24_months', model.installment_24_months))
            model.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ebike model updated successfully',
                'id': model.id,
                'name': model.name,
                'srp': float(model.srp),
                'downpayment': float(model.downpayment),
                'installment_6_months': float(model.installment_6_months),
                'installment_12_months': float(model.installment_12_months),
                'installment_15_months': float(model.installment_15_months),
                'installment_18_months': float(model.installment_18_months),
                'installment_24_months': float(model.installment_24_months)
            })
        except EbikeModel.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Ebike model not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    elif request.method == "DELETE":
        # Delete ebike model
        try:
            if not model_id:
                return JsonResponse({'status': 'error', 'message': 'Model ID required'}, status=400)
            
            model = EbikeModel.objects.get(id=model_id)
            name = model.name
            model.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Ebike model {name} deleted successfully'
            })
        except EbikeModel.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Ebike model not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)