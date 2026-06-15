from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import include, path

from accounts.views import UserViewSet
from academics.views import (
    AcademicEventViewSet,
    AcademicYearViewSet,
    AttendanceViewSet,
    ClassroomSubjectViewSet,
    ClassroomViewSet,
    EnrollmentViewSet,
    GradeViewSet,
    GradeLevelViewSet,
    SubjectViewSet,
    WeeklyScheduleViewSet,
)
from assignments.views import AssignmentViewSet, SubmissionViewSet
from engagement.views import CommentViewSet, PostReactionViewSet, PostViewSet


router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("subjects", SubjectViewSet, basename="subjects")
router.register("academic-years", AcademicYearViewSet, basename="academic-years")
router.register("grade-levels", GradeLevelViewSet, basename="grade-levels")
router.register("classrooms", ClassroomViewSet, basename="classrooms")
router.register("classroom-subjects", ClassroomSubjectViewSet, basename="classroom-subjects")
router.register("enrollments", EnrollmentViewSet, basename="enrollments")
router.register("grades", GradeViewSet, basename="grades")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("events", AcademicEventViewSet, basename="events")
router.register("weekly-schedules", WeeklyScheduleViewSet, basename="weekly-schedules")
router.register("posts", PostViewSet, basename="posts")
router.register("comments", CommentViewSet, basename="comments")
router.register("reactions", PostReactionViewSet, basename="reactions")
router.register("assignments", AssignmentViewSet, basename="assignments")
router.register("submissions", SubmissionViewSet, basename="submissions")


urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
