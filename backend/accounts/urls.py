from django.urls import path

from accounts import views
from accounts.merge_views import AccountMergeView

app_name = "api_accounts"

urlpatterns = [
    path("", views.AccountsListView.as_view()),
    path("<uid:pk>/merge/", AccountMergeView.as_view()),
    path("<uid:pk>/", views.AccountDetailView.as_view()),
    path("<uid:pk>/create_mail/", views.AccountCreateMailView.as_view()),
    path("comment/<uid:pk>/", views.AccountCommentView.as_view()),
    path("attachment/<uid:pk>/", views.AccountAttachmentView.as_view()),
]
