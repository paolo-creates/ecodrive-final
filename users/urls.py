from django.urls import path, include
from django.conf import settings
from . import views
from rest_framework.routers import DefaultRouter
from .views import (
    BorrowerViewSet, LoanViewSet, MonthlyReleaseViewSet, 
    PaymentViewSet, MonthlyCollectionViewSet, EbikeModelViewSet, StaffViewSet
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'borrowers', BorrowerViewSet)
router.register(r'loans', LoanViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'collections', MonthlyCollectionViewSet)
router.register(r'monthly-releases', MonthlyReleaseViewSet)
router.register(r'ebike-models', EbikeModelViewSet)
router.register(r'staff', StaffViewSet)


urlpatterns = [
    path('api/login/', views.login_api, name='login'),
    path('api/logout/', views.logout_api, name='logout'),
    path('api/borrowers-json/', views.get_borrowers_json, name='get_borrowers_json'),
    path('api/add-borrower/', views.add_borrower, name='add_borrower'),
    path('api/edit-borrower/<int:borrower_id>/', views.edit_borrower, name='edit_borrower'),
    path('api/delete-borrower/<int:borrower_id>/', views.delete_borrower, name='delete_borrower'),
    path('api/add-staff/', views.add_staff, name='add_staff'),
    path('api/edit-staff/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('api/delete-staff/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('api/add-payment/', views.add_payment, name='add_payment'),
    path('api/loan-statistics/', views.get_loan_statistics, name='get_loan_statistics'),
    path('api/add-loan/', views.add_loan, name='add_loan'),
    path('api/ebike-model/', views.manage_ebike_model, name='manage_ebike_model'),
    path('api/ebike-model/<int:model_id>/', views.manage_ebike_model, name='manage_ebike_model_detail'),
    path('api/', include(router.urls)),
    path('', views.index, name='index'),
    path('home/', views.homepage, name='Homepage'),
    path('loans/', views.adminloanslist, name='Adminloanslist'),
    path('payments/', views.adminpayment, name='Adminpayment'),
    path('borrowers/', views.adminborrower, name='Adminborrower'),
    path('staff/', views.admin_staff, name='AdminStaff'),
    path('ebike-models/', views.admin_ebike, name='AdminEbike'),
    path('forgot-password/', views.forgotpass, name='forgotpass'),
    path('reset-password/', views.resetpass, name='resetpass'),
    path('otp/', views.otp, name='otp'),
]

