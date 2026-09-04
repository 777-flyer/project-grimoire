from django.urls import path

from . import views

urlpatterns = [
    path("project-managers", views.ProjectManagersView.as_view()),
    path("tasks-summary", views.TaskSummaryView.as_view()),
    path("projects", views.ProjectListCreateView.as_view()),
    path("projects/<int:project_id>", views.ProjectDetailView.as_view()),
    path("projects/<int:project_id>/feed", views.FeedView.as_view()),
    path("projects/<int:project_id>/records", views.RecordListCreateView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>", views.RecordDetailView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/metadata", views.RecordMetadataView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/approve", views.RecordApproveView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/reject", views.RecordRejectView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/notes", views.RecordNoteView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/notes/<str:note_id>/resolve", views.ResolveIssueView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/access-log", views.RecordAccessLogView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/change-requests", views.ChangeRequestListCreateView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/change-requests/<int:cr_id>/approve", views.ChangeRequestApproveView.as_view()),
    path("projects/<int:project_id>/records/<int:record_id>/change-requests/<int:cr_id>/reject", views.ChangeRequestRejectView.as_view()),
    path("projects/<int:project_id>/grant", views.GrantAccessView.as_view()),
    path("projects/<int:project_id>/revoke", views.RevokeAccessView.as_view()),
    path("projects/<int:project_id>/rotate", views.RotateKeyView.as_view()),
]
