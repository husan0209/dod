from django.urls import path, include
from django.contrib.admin.views.decorators import staff_member_required

from . import views

app_name = 'support'

urlpatterns = [
    # Основные страницы
    path('', views.support_center, name='home'),
    path('new/', views.create_ticket, name='create_ticket'),
    path('tickets/', views.my_tickets, name='my_tickets'),
    path('tickets/<uuid:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<uuid:ticket_id>/rate/', views.rate_ticket, name='rate_ticket'),

    # FAQ
    path('faq/', views.faq_list, name='faq_list'),
    path('faq/<slug:category_slug>/<slug:article_slug>/', views.faq_detail, name='faq_detail'),
    path('faq/<int:article_id>/helpful/', views.faq_helpful, name='faq_helpful'),

    # HTMX API
    path('api/suggest-faq/', views.suggest_faq, name='suggest_faq'),

    # Analytics
    path('admin/analytics/', staff_member_required(views.analytics), name='analytics'),
]

# Operator URLs
operator_patterns = [
    path('', views.operator_dashboard, name='operator_dashboard'),
    path('tickets/', views.operator_tickets, name='operator_tickets'),
    path('tickets/<uuid:ticket_id>/', views.operator_ticket_detail, name='operator_ticket_detail'),
]

urlpatterns += [
    path('operator/', include((operator_patterns, 'support'), namespace='operator')),
]
