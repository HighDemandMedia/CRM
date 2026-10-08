from django.urls import path

from common.views.attachment_views import AttachmentDeleteView, AttachmentDownloadView
from common.views.auth_views import (
    GoogleIdTokenView,
    GoogleOAuthCallbackView,
    LogoutView,
    MagicLinkRequestView,
    MagicLinkVerifyCodeView,
    MagicLinkVerifyView,
    MeView,
    OrgAwareTokenRefreshView,
    OrgSwitchView,
)
from common.views.creation_form_views import CreationFormSchemaView, CreationFormView
from common.views.crm_report_views import CRMReportView
from common.views.custom_field_views import (
    CustomFieldDefinitionDetailView,
    CustomFieldDefinitionListCreateView,
)
from common.views.dashboard_views import ActivityListView, ApiTodayView
from common.views.google_integration_views import (
    GoogleCalendarListView,
    GoogleCallbackView,
    GoogleConnectionView,
    GoogleConnectView,
    GoogleEventsView,
    GoogleMailBodyView,
)
from common.views.google_mail_views import RecordMailActionView, RecordMailView
from common.views.help_views import HelpRequestView
from common.views.invitation_views import (
    AcceptInvitationView,
    InvitationDetailView,
    InvitationsView,
)
from common.views.member_removal_views import MemberRemovalView
from common.views.notification_views import (
    NotificationDetailView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
)
from common.views.org_settings_views import OrgSettingsView, TimezoneListView
from common.views.organization_views import (
    OrgProfileCreateView,
    OrgUpdateView,
    ProfileDetailView,
    ProfileView,
)
from common.views.password_auth_views import (
    InvitationPreviewView,
    PasswordChangeView,
    PasswordLoginView,
    PasswordRegisterView,
)
from common.views.pipeline_settings_views import PipelineSettingsView
from common.views.profile_photo_views import ProfilePhotoView
from common.views.property_layout_views import PropertyLayoutView
from common.views.record_association_views import RecordAssociationView
from common.views.record_delete_views import RecordDeleteView
from common.views.role_views import (
    MemberRoleView,
    MyPermissionsView,
    RoleDetailView,
    RoleExportCheckView,
    RolesView,
)
from common.views.sales_appointment_views import (
    AppointmentAttendeesView,
    AppointmentAvailabilityView,
    SalesAppointmentManageView,
    SalesAppointmentView,
)
from common.views.tags_views import (
    TagsDetailView,
    TagsListView,
    TagsMergeView,
    TagsRestoreView,
)
from common.views.team_views import TeamsDetailView, TeamsListView
from common.views.today_summary_views import TodaySummaryView
from common.views.ui_context_views import UIContextView
from common.views.user_views import (
    GetTeamsAndUsersView,
    UserDetailView,
    UsersListView,
    UserStatusView,
)

app_name = "api_common"


urlpatterns = [
    path("integrations/google/connect/<str:service>/", GoogleConnectView.as_view()),
    path("integrations/google/callback/", GoogleCallbackView.as_view()),
    path("integrations/google/", GoogleConnectionView.as_view()),
    path("integrations/google/calendars/", GoogleCalendarListView.as_view()),
    path("integrations/google/events/", GoogleEventsView.as_view()),
    path("integrations/google/events/<uuid:pk>/", GoogleEventsView.as_view()),
    path("integrations/google/mail/<uuid:pk>/", GoogleMailBodyView.as_view()),
    path(
        "integrations/google/records/<str:kind>/<uuid:pk>/mail/",
        RecordMailView.as_view(),
    ),
    path(
        "integrations/google/records/<str:kind>/<uuid:pk>/mail/actions/",
        RecordMailActionView.as_view(),
    ),
    path("org/ui-context/", UIContextView.as_view()),
    path("auth/password/login/", PasswordLoginView.as_view()),
    path("auth/password/register/", PasswordRegisterView.as_view()),
    path("auth/password/invitation/", InvitationPreviewView.as_view()),
    path("auth/password/change/", PasswordChangeView.as_view()),
    path("help/requests/", HelpRequestView.as_view(), name="help_requests"),
    path("reports/crm/", CRMReportView.as_view(), name="crm_reports"),
    path("creation-forms/", CreationFormView.as_view()),
    path("creation-forms/<str:target>/", CreationFormSchemaView.as_view()),
    path("property-layout/", PropertyLayoutView.as_view()),
    path("pipeline-settings/", PipelineSettingsView.as_view()),
    path("members/<uuid:pk>/remove/", MemberRemovalView.as_view()),
    path("roles/export/<str:module>/", RoleExportCheckView.as_view()),
    path("permissions/me/", MyPermissionsView.as_view()),
    path("roles/", RolesView.as_view()),
    path("roles/<uuid:pk>/", RoleDetailView.as_view()),
    path("roles/members/<uuid:pk>/", MemberRoleView.as_view()),
    path("invitations/", InvitationsView.as_view()),
    path("invitations/<uuid:pk>/", InvitationDetailView.as_view()),
    path("auth/accept-invitation/", AcceptInvitationView.as_view()),
    path("dashboard/day-summary/", TodaySummaryView.as_view()),
    path("record-delete/<str:kind>/<uid:pk>/", RecordDeleteView.as_view()),
    path("record-associations/<str:kind>/<uid:pk>/", RecordAssociationView.as_view()),
    path(
        "sales-appointments/availability/",
        AppointmentAvailabilityView.as_view(),
        name="appointment_availability",
    ),
    path(
        "sales-appointments/<uid:pk>/",
        SalesAppointmentManageView.as_view(),
        name="manage_sales_appointment",
    ),
    path(
        "sales-appointments/attendees/",
        AppointmentAttendeesView.as_view(),
        name="appointment_attendees",
    ),
    path(
        "sales-appointments/", SalesAppointmentView.as_view(), name="sales_appointments"
    ),
    path("dashboard/today/", ApiTodayView.as_view()),
    # JWT Authentication endpoints for SvelteKit integration
    path(
        "auth/refresh-token/",
        OrgAwareTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/profile/", ProfileDetailView.as_view(), name="profile_detail"),
    path("auth/switch-org/", OrgSwitchView.as_view(), name="switch_org"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # Google OAuth callback with PKCE (secure implementation)
    path("auth/google/callback/", GoogleOAuthCallbackView.as_view()),
    # Google ID token auth for mobile apps
    path("auth/google/", GoogleIdTokenView.as_view(), name="google_id_token"),
    # Magic link (passwordless) authentication
    path(
        "auth/magic-link/request/",
        MagicLinkRequestView.as_view(),
        name="magic_link_request",
    ),
    path(
        "auth/magic-link/verify/",
        MagicLinkVerifyView.as_view(),
        name="magic_link_verify",
    ),
    path(
        "auth/magic-link/verify-code/",
        MagicLinkVerifyCodeView.as_view(),
        name="magic_link_verify_code",
    ),
    # Organization and profile management
    path("org/", OrgProfileCreateView.as_view()),
    path("org/settings/", OrgSettingsView.as_view(), name="org_settings"),
    # Static reference data, org-free by design: the first caller is a user
    # creating their first org and has no org claim yet.
    path("org/timezones/", TimezoneListView.as_view(), name="timezone_list"),
    # These literal org/… paths must precede org/<uid:pk>/ so they are not
    # captured as a pk (org/tokens/ would otherwise resolve to OrgUpdateView
    # with pk="tokens"). org/tokens/ is ADMIN-only token oversight, separate
    # from profile/tokens/ (self-scoped) so the self guard is never widened; an
    # admin sees and can revoke any token in their own org, a deactivated
    # colleague's included.
    path("org/<uid:pk>/", OrgUpdateView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("profile/photo/", ProfilePhotoView.as_view(), name="profile_photo"),
    # Personal Access Tokens (REST API), a user manages ONLY their own
    # User management
    path("users/get-teams-and-users/", GetTeamsAndUsersView.as_view()),
    path("users/", UsersListView.as_view()),
    path("user/<uid:pk>/", UserDetailView.as_view()),
    path("user/<uid:pk>/status/", UserStatusView.as_view()),
    # Documents
    # Attachments. One generic download for every attachable record type; see
    # the view for why a /media/ URL is not an alternative to it.
    path("attachments/<uid:pk>/download/", AttachmentDownloadView.as_view()),
    path("attachments/<uid:pk>/", AttachmentDeleteView.as_view()),
    # API Settings
    # Activities (for dashboard recent activities)
    path("activities/", ActivityListView.as_view(), name="activities"),
    # Teams (merged from teams app)
    path("teams/", TeamsListView.as_view()),
    path("teams/<uid:pk>/", TeamsDetailView.as_view()),
    # Tags
    path("tags/", TagsListView.as_view()),
    path("tags/<uid:pk>/", TagsDetailView.as_view()),
    path("tags/<uid:pk>/restore/", TagsRestoreView.as_view()),
    path("tags/<uid:pk>/merge/", TagsMergeView.as_view()),
    # Custom fields (per-org schema extension; cross-entity)
    path(
        "custom-fields/",
        CustomFieldDefinitionListCreateView.as_view(),
        name="custom_fields_list_create",
    ),
    path(
        "custom-fields/<uid:pk>/",
        CustomFieldDefinitionDetailView.as_view(),
        name="custom_field_detail",
    ),
    # In-app notifications (per-recipient feed)
    path("notifications/", NotificationListView.as_view(), name="notifications_list"),
    path(
        "notifications/read-all/",
        NotificationReadAllView.as_view(),
        name="notifications_read_all",
    ),
    path(
        "notifications/<uid:pk>/read/",
        NotificationReadView.as_view(),
        name="notifications_read",
    ),
    path(
        "notifications/<uid:pk>/",
        NotificationDetailView.as_view(),
        name="notifications_detail",
    ),
    # Vertical packs: any member may list; apply/clear are ADMIN-only (see
    # common/views/pack_views.py). sample-data/ must precede
    # <str:pack_id>/apply/ so it is never captured as a pack id.
]
