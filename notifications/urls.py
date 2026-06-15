from django.urls import path
from .views import (
    MyNotificationsView, UnreadCountView,
    MarkReadView, MarkAllReadView,
    MyPreferencesView, TestNotificationView,
)

urlpatterns = [

    # ── All authenticated users ─────────────────────────────────────
    path('',                        MyNotificationsView.as_view(),  name='my-notifications'),
    path('unread-count/',           UnreadCountView.as_view(),      name='unread-count'),
    path('mark-all-read/',          MarkAllReadView.as_view(),      name='mark-all-read'),
    path('<uuid:pk>/mark-read/',    MarkReadView.as_view(),         name='mark-read'),
    path('preferences/',            MyPreferencesView.as_view(),    name='notification-preferences'),
    path('test/',                   TestNotificationView.as_view(), name='test-notification'),
]