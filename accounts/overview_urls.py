from django.urls import path
from .overview import (
    OperatorOverviewView,
    ExecOverviewView,
    BOTOverviewView,
    AdvisorOverviewView,
    SuperAdminOverviewView,
)

urlpatterns = [
    path('operator/',   OperatorOverviewView.as_view(),    name='operator-overview'),
    path('exec/',       ExecOverviewView.as_view(),        name='exec-overview'),
    path('bot/',        BOTOverviewView.as_view(),         name='bot-overview'),
    path('advisor/',    AdvisorOverviewView.as_view(),     name='advisor-overview'),
    path('superadmin/', SuperAdminOverviewView.as_view(),  name='superadmin-overview'),
]