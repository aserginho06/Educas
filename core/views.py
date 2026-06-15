import logging
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch, Q
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.forms import SignUpForm
from accounts.decorators import role_required
from accounts.forms import ProfileUpdateForm
from accounts.models import User
from academics.forms import (
    AttendanceRegistryForm,
    ClassroomCreateForm,
    ClassroomJoinByCodeForm,
    AssessmentForm,
    GradeBatchForm,
    LessonForm,
)
from academics.models import AcademicEvent, AcademicYear, Assessment, Attendance, AttendanceRecord, Classroom, ClassroomSubject, Enrollment, Grade, GradeEntry, GradeLevel, Lesson, Subject, WeeklySchedule
from academics.services import (
    enroll_student_with_access_code,
    scoped_classrooms,
    student_attendance_subject_summary,
    student_attendance_summary,
    student_grade_chart_data,
    student_grade_report,
    teacher_has_subject_access,
)
from assignments.forms import AssignmentForm, SubmissionForm
from assignments.models import Assignment, Notification, Submission
from common.ai_content import generate_json
from engagement.forms import CommentForm, PostForm
from engagement.models import Comment, Post, PostReaction
from engagement.services import REACTION_EMOJI_MAP, set_post_reaction, summarize_post_reactions

logger = logging.getLogger(__name__)


def _local_review_post_copy(title, content):
    headline = (title or "").strip()
    body = (content or "").strip()
    if not body:
        return {"title": headline, "content": ""}
    improved = body.replace("  ", " ").strip()
    if headline and headline.lower() not in improved.lower():
        improved = f"{headline}\n\n{improved}"
    if not improved.endswith((".", "!", "?")):
        improved = f"{improved}."
    improved += "\n\nOrientações: confira o prazo, os anexos e a turma correta antes de publicar."
    return {"title": headline, "content": improved}


def _subject_color(subject_name):
    palette = [
        "#2563eb",
        "#0f766e",
        "#ca8a04",
        "#7c3aed",
        "#db2777",
        "#0891b2",
        "#dc2626",
    ]
    if not subject_name:
        return "#64748b"
    checksum = sum(ord(char) for char in subject_name.strip())
    return palette[checksum % len(palette)]


def static_page(template_name):
    def view(request):
        return render(request, f"core/{template_name}")

    return view


def protected_static_page(template_name):
    @login_required
    def view(request):
        return render(request, f"core/{template_name}")

    return view


@login_required
def home(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("core:administrador")
    if request.user.role == User.Role.TEACHER:
        return redirect("core:professor")
    return redirect("core:aluno")


class EducasLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.role == User.Role.ADMIN:
            return reverse_lazy("core:administrador")
        if self.request.user.role == User.Role.TEACHER:
            return reverse_lazy("core:professor")
        return reverse_lazy("core:aluno")


@login_required
def logout_view(request):
    logout(request)
    request.session.flush()
    response = redirect('core:login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Cadastro realizado com sucesso.")
        return redirect("core:home")

    return render(request, "core/cadastro.html", {"form": form})


def _get_scoped_post_or_404(user, post_id):
    try:
        return (
            Post.objects.select_related("classroom", "author", "subject")
            .prefetch_related("comments__author", "reactions")
            .get(pk=post_id, classroom__in=scoped_classrooms(user))
        )
    except Post.DoesNotExist as exc:
        raise Http404("Publicacao nao encontrada.") from exc


def _is_ajax_request(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _user_initials(user):
    initials = f"{user.first_name[:1]}{user.last_name[:1] if user.last_name else ''}".upper()
    return initials or "ED"


def _serialize_comment(comment):
    return {
        "id": comment.id,
        "author": comment.author.full_name or comment.author.email,
        "avatar": comment.author.avatar_url,
        "initials": _user_initials(comment.author),
        "content": comment.content,
        "created_at": comment.created_at.strftime("%d/%m/%Y %H:%M"),
        "can_delete": False,
    }


def _serialize_reaction_summary(post, user):
    summary = summarize_post_reactions(post, current_user=user)
    return {
        "total": summary["total"],
        "current_user_reaction": summary["current_user_reaction"],
        "items": summary["items"],
        "available": [{"type": key, "emoji": emoji} for key, emoji in REACTION_EMOJI_MAP.items()],
    }


def _serialize_post(post, user):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author": post.author.full_name or post.author.email,
        "author_initials": _user_initials(post.author),
        "classroom": post.classroom.name,
        "subject": post.subject.name if post.subject_id else "",
        "created_at": post.created_at.strftime("%d/%m/%Y %H:%M"),
        "is_pinned": post.is_pinned,
        "attachment_url": post.attachment.url if post.attachment else "",
        "attachment_name": post.attachment.name.split("/", 1)[-1] if post.attachment else "",
        "attachment_is_image": post.attachment_is_image,
        "attachment_extension": post.attachment_extension.replace(".", "").upper(),
        "comment_count": post.comments.count(),
        "reaction_payload": _serialize_reaction_summary(post, user),
        "can_delete": user.role == User.Role.ADMIN or post.author_id == user.id,
        "delete_url": reverse("core:feed"),
        "react_url": reverse("core:feed_react"),
        "comment_url": reverse("core:feed_comment"),
        "delete_comment_url": reverse("core:feed_delete_comment"),
    }


@login_required
@role_required("teacher")
def professor_dashboard(request):
    classrooms = (
        scoped_classrooms(request.user)
        .select_related("academic_year", "grade_level")
        .prefetch_related("classroom_subjects__subject", "weekly_schedules__subject", "weekly_schedules__teacher")
    )
    today_weekday = timezone.localdate().strftime("%A").lower()
    weekday_map = {
        "monday": "monday",
        "tuesday": "tuesday",
        "wednesday": "wednesday",
        "thursday": "thursday",
        "friday": "friday",
        "saturday": "saturday",
        "segunda-feira": "monday",
        "terça-feira": "tuesday",
        "quarta-feira": "wednesday",
        "quinta-feira": "thursday",
        "sexta-feira": "friday",
        "sábado": "saturday",
    }
    weekday_key = weekday_map.get(today_weekday, "monday")
    today_schedule = WeeklySchedule.objects.select_related("classroom", "subject").filter(
        teacher=request.user,
        weekday=weekday_key,
        entry_type=WeeklySchedule.EntryType.CLASS,
    ).order_by("starts_at")
    pending_assignments = Assignment.objects.select_related("classroom", "subject").filter(
        author=request.user,
        status=Assignment.Status.ACTIVE,
    ).order_by("due_at")[:6]
    recent_posts = Post.objects.select_related("classroom", "subject").filter(author=request.user).order_by("-created_at")[:6]
    recent_events = AcademicEvent.objects.select_related("classroom", "subject").filter(
        created_by=request.user
    ).order_by("starts_at")[:6]
    subject_links = ClassroomSubject.objects.select_related("classroom", "subject").filter(teacher=request.user).order_by(
        "classroom__name", "subject__name"
    )
    return render(
        request,
        "core/professor.html",
        {
            "classrooms": classrooms,
            "today_schedule": today_schedule,
            "pending_assignments": pending_assignments,
            "recent_posts": recent_posts,
            "recent_events": recent_events,
            "subject_links": subject_links,
            "today_label": timezone.localdate().strftime("%d/%m/%Y"),
        },
    )


def _get_scoped_assignment_or_404(user, assignment_id):
    queryset = Assignment.objects.select_related("classroom", "subject").prefetch_related("submissions__student")
    if user.role == User.Role.TEACHER:
        return get_object_or_404(queryset, pk=assignment_id, author=user)
    return get_object_or_404(queryset, pk=assignment_id, classroom__in=scoped_classrooms(user))


def _create_notification(user, assignment, notification_type, message, link=""):
    Notification.objects.create(
        user=user,
        assignment=assignment,
        notification_type=notification_type,
        message=message,
        link=link,
    )


@login_required
@role_required("teacher")
def assignment_list(request):
    # REVISÃO TOTAL: Uso exclusivo de total_submissions para evitar AttributeError
    assignments = (
        Assignment.objects.select_related("classroom", "subject")
        .filter(author=request.user)
        .annotate(total_submissions=Count("submissions", distinct=True))
        .order_by("-created_at")
    )
    open_assignment_count = sum(1 for assignment in assignments if not assignment.is_closed)
    return render(
        request,
        "core/assignment_list.html",
        {"assignments": assignments, "open_assignment_count": open_assignment_count},
    )


@login_required
@role_required("teacher")
def assignment_create(request):
    form = AssignmentForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.author = request.user
        assignment.status = Assignment.Status.ACTIVE
        assignment.save()

        students = Enrollment.objects.filter(classroom=assignment.classroom, status=Enrollment.Status.APPROVED).select_related("student")
        for enrollment in students:
            _create_notification(
                enrollment.student,
                assignment,
                Notification.NotificationType.NEW_ACTIVITY,
                f"Nova atividade '{assignment.title}' para {assignment.classroom.name}.",
                reverse("core:student_assignment_detail", args=[assignment.pk]),
            )

        messages.success(request, "Atividade criada com sucesso.")
        return redirect("core:assignment_list")
    return render(request, "core/assignment_form.html", {"form": form, "is_editing": False})


@login_required
@role_required("teacher")
def assignment_edit(request, assignment_id):
    assignment = _get_scoped_assignment_or_404(request.user, assignment_id)
    form = AssignmentForm(request.POST or None, request.FILES or None, instance=assignment, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Atividade atualizada com sucesso.")
        return redirect("core:assignment_list")
    return render(request, "core/assignment_form.html", {"form": form, "is_editing": True, "assignment": assignment})


@login_required
def assignment_detail(request, assignment_id):
    assignment = _get_scoped_assignment_or_404(request.user, assignment_id)
    if request.user.role == User.Role.TEACHER:
        submissions = assignment.submissions.select_related("student").order_by("-submitted_at")
        total_students = Enrollment.objects.filter(
            classroom=assignment.classroom,
            status=Enrollment.Status.APPROVED,
        ).count()
        total_submissions = assignment.submissions.count()
        pending_submissions = max(total_students - total_submissions, 0)
        return render(
            request,
            "core/assignment_detail.html",
            {
                "assignment": assignment,
                "submissions": submissions,
                "total_students": total_students,
                "total_submissions": total_submissions,
                "pending_submissions": pending_submissions,
            },
        )

    submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
    form = SubmissionForm(request.POST or None, request.FILES or None, instance=submission, user=request.user)
    total_students = Enrollment.objects.filter(
        classroom=assignment.classroom,
        status=Enrollment.Status.APPROVED,
    ).count()
    total_submissions = assignment.submissions.count()
    pending_submissions = max(total_students - total_submissions, 0)
    if request.method == "POST" and form.is_valid():
        if assignment.is_closed and not submission:
            messages.error(request, "A entrega nao pode ser enviada porque a atividade foi encerrada.")
        else:
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.status = Submission.Status.SUBMITTED
            submission.submitted_at = timezone.now()
            submission.save()
            _create_notification(
                assignment.author,
                assignment,
                Notification.NotificationType.CORRECTION,
                f"{request.user.full_name} entregou a atividade '{assignment.title}'.",
                reverse("core:assignment_detail", args=[assignment.pk]),
            )
            messages.success(request, "Entrega registrada com sucesso.")
            return redirect("core:student_assignment_detail", assignment_id=assignment.pk)
    return render(
        request,
        "core/activity_detail.html",
        {
            "assignment": assignment,
            "submission": submission,
            "form": form,
            "total_students": total_students,
            "total_submissions": total_submissions,
            "pending_submissions": pending_submissions,
        },
    )


@login_required
@role_required("student")
def student_assignment_list(request):
    assignments = Assignment.objects.select_related("classroom", "subject").filter(
        classroom__in=scoped_classrooms(request.user)
    ).order_by("due_at")
    student_submissions = Submission.objects.filter(student=request.user, assignment__in=assignments)
    submission_map = {submission.assignment_id: submission for submission in student_submissions}
    assignment_rows = [
        {
            "assignment": assignment,
            "submission": submission_map.get(assignment.id),
        }
        for assignment in assignments
    ]
    return render(request, "core/student_assignment_list.html", {"assignment_rows": assignment_rows})


@login_required
def notifications(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:20]
    return render(request, "core/notifications.html", {"notifications": notifications})


@login_required
@role_required("teacher")
def aulas(request):
    lessons = Lesson.objects.select_related("classroom", "subject").filter(professor=request.user)
    lessons = lessons.order_by("-date", "-created_at")

    classroom_filter = request.GET.get("classroom")
    date_filter = request.GET.get("date")
    if classroom_filter:
        lessons = lessons.filter(classroom_id=classroom_filter)
    if date_filter:
        lessons = lessons.filter(date=date_filter)

    form = LessonForm(user=request.user, prefix="lesson")
    if request.method == "POST":
        form = LessonForm(request.POST, user=request.user, prefix="lesson")
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.professor = request.user
            lesson.save()
            messages.success(request, "Aula registrada com sucesso.")
            return redirect("core:aulas")
        messages.error(request, "Nao foi possivel cadastrar a aula. Revise os campos.")

    available_classrooms = Classroom.objects.filter(classroom_subjects__teacher=request.user).distinct()
    return render(
        request,
        "core/aulas.html",
        {
            "lessons": lessons,
            "form": form,
            "available_classrooms": available_classrooms,
            "classroom_filter": int(classroom_filter) if classroom_filter else None,
            "date_filter": date_filter,
        },
    )


@login_required
@role_required("teacher")
def editar_aula(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id, professor=request.user)
    form = LessonForm(instance=lesson, user=request.user, prefix="lesson")

    if request.method == "POST":
        form = LessonForm(request.POST, instance=lesson, user=request.user, prefix="lesson")
        if form.is_valid():
            form.save()
            messages.success(request, "Aula atualizada com sucesso.")
            return redirect("core:aulas")
        messages.error(request, "Nao foi possivel atualizar a aula. Revise os campos.")

    return render(
        request,
        "core/aulas.html",
        {
            "lessons": Lesson.objects.select_related("classroom", "subject").filter(professor=request.user).order_by("-date", "-created_at"),
            "form": form,
            "editing": lesson,
            "available_classrooms": Classroom.objects.filter(classroom_subjects__teacher=request.user).distinct(),
            "classroom_filter": None,
            "date_filter": None,
        },
    )


@login_required
@role_required("teacher")
def lesson_attendance(request, lesson_id):
    lesson = get_object_or_404(Lesson.objects.select_related("classroom", "subject", "professor"), pk=lesson_id)
    if request.user.role == User.Role.TEACHER and lesson.professor_id != request.user.id:
        raise Http404("Aula nao encontrada.")

    enrollments = Enrollment.objects.filter(classroom=lesson.classroom, status=Enrollment.Status.APPROVED).select_related("student")
    attendance_records = {record.student_id: record for record in AttendanceRecord.objects.filter(lesson=lesson).select_related("student")}
    lesson_student_ids = [enrollment.student_id for enrollment in enrollments]
    option_range = range(lesson.quantidade_aulas + 1)
    if request.method == "POST":
        saved_count = 0
        for enrollment in enrollments:
            student = enrollment.student
            raw_value = request.POST.get(f"absences_{student.id}")
            try:
                absences = int(raw_value)
            except (TypeError, ValueError):
                absences = 0
            absences = max(0, min(absences, lesson.quantidade_aulas))
            record, created = AttendanceRecord.objects.update_or_create(
                lesson=lesson,
                student=student,
                defaults={"absences": absences},
            )
            if created or record.absences != absences:
                saved_count += 1
        messages.success(request, f"Frequencia salva para {enrollments.count()} alunos.")
        return redirect("core:lesson_attendance", lesson_id=lesson.pk)

    attendance_summary = {
        "total_students": enrollments.count(),
        "total_possible": lesson.quantidade_aulas * enrollments.count(),
        "total_absences": sum(record.absences for record in attendance_records.values()),
    }
    attendance_summary["presence_percentage"] = (
        100 if attendance_summary["total_possible"] == 0 else round(
            ((attendance_summary["total_possible"] - attendance_summary["total_absences"]) / attendance_summary["total_possible"]) * 100,
            1,
        )
    )
    student_data = []
    for enrollment in enrollments:
        student = enrollment.student
        record = attendance_records.get(student.id)
        absences = record.absences if record else 0
        percentage = 100 if lesson.quantidade_aulas == 0 else round(((lesson.quantidade_aulas - absences) / lesson.quantidade_aulas) * 100, 1)
        student_data.append(
            {
                "student": student,
                "registration_code": getattr(getattr(student, "student_profile", None), "registration_code", student.email),
                "status": enrollment.get_status_display(),
                "record": record,
                "absences": absences,
                "percentage": percentage,
            }
        )

    return render(
        request,
        "core/lesson_attendance.html",
        {
            "lesson": lesson,
            "student_data": student_data,
            "attendance_summary": attendance_summary,
            "option_range": option_range,
        },
    )


@login_required
def attendance(request):
    if request.user.role not in {User.Role.TEACHER, User.Role.ADMIN}:
        raise PermissionDenied("Somente professores e administradores podem acessar este painel.")

    allowed_classrooms = scoped_classrooms(request.user)
    attendance_records = AttendanceRecord.objects.select_related("lesson__classroom", "lesson__subject", "student")
    if request.user.role == User.Role.TEACHER:
        attendance_records = attendance_records.filter(lesson__professor=request.user)

    classroom_filter = request.GET.get("classroom")
    subject_filter = request.GET.get("subject")
    student_filter = request.GET.get("student")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if classroom_filter:
        attendance_records = attendance_records.filter(lesson__classroom_id=classroom_filter)
    if subject_filter:
        attendance_records = attendance_records.filter(lesson__subject_id=subject_filter)
    if student_filter:
        attendance_records = attendance_records.filter(student_id=student_filter)
    if start_date:
        try:
            attendance_records = attendance_records.filter(lesson__date__gte=date.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            attendance_records = attendance_records.filter(lesson__date__lte=date.fromisoformat(end_date))
        except ValueError:
            pass

    attendance_list = list(attendance_records)
    student_summary = {}
    for record in attendance_list:
        student_id = record.student_id
        item = student_summary.setdefault(
            student_id,
            {
                "student": record.student,
                "absences": 0,
                "possible": 0,
                "lessons": 0,
            },
        )
        item["absences"] += record.absences
        item["possible"] += record.lesson.quantidade_aulas
        item["lessons"] += 1

    for item in student_summary.values():
        item["percentage"] = 100 if item["possible"] == 0 else round(((item["possible"] - item["absences"]) / item["possible"]) * 100, 1)
        if item["percentage"] >= 90:
            item["severity"] = "positive"
        elif item["percentage"] >= 75:
            item["severity"] = "warning"
        else:
            item["severity"] = "danger"

    overall_possible = sum(item["possible"] for item in student_summary.values())
    overall_absences = sum(item["absences"] for item in student_summary.values())
    overall_percentage = 100 if overall_possible == 0 else round(((overall_possible - overall_absences) / overall_possible) * 100, 1)

    classrooms = allowed_classrooms.order_by("name")
    subjects = Subject.objects.filter(lessons__classroom__in=allowed_classrooms).distinct().order_by("name")
    students = User.objects.filter(
        enrollments__classroom__in=allowed_classrooms,
        role=User.Role.STUDENT,
        enrollments__status=Enrollment.Status.APPROVED,
    ).distinct().order_by("first_name", "last_name")
    total_records = len(attendance_list)

    return render(
        request,
        "core/attendance.html",
        {
            "classrooms": classrooms,
            "subjects": subjects,
            "students": students,
            "student_summary": sorted(student_summary.values(), key=lambda item: item["student"].full_name),
            "overall_absences": overall_absences,
            "overall_percentage": overall_percentage,
            "record_count": total_records,
            "filters": {
                "classroom": classroom_filter,
                "subject": subject_filter,
                "student": student_filter,
                "start_date": start_date,
                "end_date": end_date,
            },
        },
    )


@login_required
@role_required("student")
def aluno_dashboard(request):
    classrooms = scoped_classrooms(request.user).select_related("academic_year", "grade_level").prefetch_related(
        "weekly_schedules__subject",
        "weekly_schedules__teacher",
    )
    report = student_grade_report(request.user)
    attendance = student_attendance_summary(request.user)
    attendance_subjects = student_attendance_subject_summary(request.user)
    assignments = Assignment.objects.select_related("classroom", "subject").filter(
        classroom__in=classrooms
    ).order_by("due_at")[:8]
    events = AcademicEvent.objects.select_related("classroom", "subject").filter(
        Q(classroom__in=classrooms) | Q(classroom__isnull=True)
    ).order_by("starts_at")[:8]
    today_weekday = timezone.localdate().strftime("%A").lower()
    weekday_map = {
        "monday": "monday",
        "tuesday": "tuesday",
        "wednesday": "wednesday",
        "thursday": "thursday",
        "friday": "friday",
        "saturday": "saturday",
        "segunda-feira": "monday",
        "terca-feira": "tuesday",
        "terça-feira": "tuesday",
        "quarta-feira": "wednesday",
        "quinta-feira": "thursday",
        "sexta-feira": "friday",
        "sabado": "saturday",
        "sábado": "saturday",
    }
    weekday_key = weekday_map.get(today_weekday, "monday")
    today_schedule = WeeklySchedule.objects.select_related("classroom", "subject", "teacher").filter(
        classroom__in=classrooms,
        weekday=weekday_key,
    ).order_by("starts_at")
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:5]
    return render(
        request,
        "core/aluno.html",
        {
            "classrooms": classrooms,
            "report": report,
            "attendance": attendance,
            "attendance_subjects": attendance_subjects,
            "overall_average": request.user.academic_average,
            "assignments": assignments,
            "events": events,
            "today_schedule": today_schedule,
            "notifications": notifications,
            "today_label": timezone.localdate().strftime("%d/%m/%Y"),
        },
    )


@login_required
def feed(request):
    classrooms = scoped_classrooms(request.user).prefetch_related("subjects")
    post_form = PostForm(user=request.user, prefix="post")
    comment_form = CommentForm(prefix="comment")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_post":
            if request.user.role not in {User.Role.ADMIN, User.Role.TEACHER}:
                if _is_ajax_request(request):
                    return JsonResponse({"errors": {"__all__": [{"message": "Permissão negada."}]}}, status=403)
                raise PermissionDenied()

            post_form = PostForm(request.POST, request.FILES, user=request.user, prefix="post")
            if post_form.is_valid():
                post = post_form.save(commit=False)
                post.author = request.user
                post.is_published = True
                post.save()
                post = (
                    Post.objects.select_related("classroom", "author", "subject")
                    .prefetch_related("comments", "reactions__user")
                    .annotate(total_comments=Count("comments", distinct=True), total_reactions=Count("reactions", distinct=True))
                    .get(pk=post.pk)
                )
                if _is_ajax_request(request):
                    return JsonResponse({"post": _serialize_post(post, request.user)}, status=201)
                messages.success(request, "Publicacao criada com sucesso.")
                return redirect("core:feed")

            if _is_ajax_request(request):
                return JsonResponse({"errors": post_form.errors.get_json_data()}, status=400)
            messages.error(request, "Nao foi possivel publicar. Revise os campos.")

        if action == "create_comment":
            post = _get_scoped_post_or_404(request.user, request.POST.get("post_id"))
            comment_form = CommentForm(request.POST, prefix="comment")
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                messages.success(request, "Comentario enviado.")
                return redirect("core:feed")

        if action == "toggle_like":
            post = _get_scoped_post_or_404(request.user, request.POST.get("post_id"))
            current = set_post_reaction(
                post=post,
                user=request.user,
                reaction_type=PostReaction.ReactionType.LIKE,
            )
            messages.success(request, "Reacao registrada." if current else "Reacao removida.")
            return redirect("core:feed")

        if action == "delete_post":
            post = _get_scoped_post_or_404(request.user, request.POST.get("post_id"))
            if request.user.role != User.Role.ADMIN and post.author_id != request.user.id:
                raise PermissionDenied("Voce nao pode excluir esta publicacao.")
            post.delete()
            messages.success(request, "Publicacao removida.")
            return redirect("core:feed")

        if action == "delete_comment":
            comment = Comment.objects.select_related("post__classroom").filter(
                pk=request.POST.get("comment_id"),
                post__classroom__in=scoped_classrooms(request.user),
            ).first()
            if not comment:
                raise Http404("Comentario nao encontrado.")
            if request.user.role != User.Role.ADMIN and comment.author_id != request.user.id:
                raise PermissionDenied("Voce nao pode excluir este comentario.")
            comment.delete()
            messages.success(request, "Comentario removido.")
            return redirect("core:feed")

    posts = (
        Post.objects.select_related("classroom", "author", "subject")
        .prefetch_related(
            Prefetch("comments", queryset=Comment.objects.select_related("author", "author__profile")),
            "reactions__user",
        )
        .filter(classroom__in=classrooms, is_published=True)
        .annotate(total_comments=Count("comments", distinct=True), total_reactions=Count("reactions", distinct=True))
        .order_by("-is_pinned", "-created_at")
    )
    logger.debug("Feed queryset montado | user=%s role=%s posts=%s", request.user.pk, request.user.role, posts.count())
    for post in posts:
        post.reaction_payload = _serialize_reaction_summary(post, request.user)

    visible_events = AcademicEvent.objects.select_related("classroom", "subject").filter(
        Q(classroom__in=classrooms) | Q(classroom__isnull=True)
    )[:24]
    upcoming_events = visible_events[:5]
    upcoming_assignments = Assignment.objects.select_related("classroom", "subject").filter(classroom__in=classrooms)[:5]
    calendar_events = [
        {
            "date": event.starts_at.strftime("%Y-%m-%d"),
            "title": event.title,
            "shortTitle": event.title[:18],
            "classroom": event.classroom.name if event.classroom_id else "Geral",
            "subject": event.subject.name if event.subject_id else "",
            "type": event.get_event_type_display(),
            "event_type": event.event_type,
        }
        for event in visible_events
    ]

    return render(
        request,
        "core/feed.html",
        {
            "classrooms": classrooms,
            "post_form": post_form,
            "comment_form": comment_form,
            "posts": posts,
            "upcoming_events": upcoming_events,
            "upcoming_assignments": upcoming_assignments,
            "reaction_options": REACTION_EMOJI_MAP.items(),
            "calendar_events_json": json.dumps(calendar_events, ensure_ascii=False),
        },
    )


@login_required
@require_POST
def feed_review_ai(request):
    if request.user.role not in {User.Role.ADMIN, User.Role.TEACHER}:
        raise PermissionDenied("Aluno nao pode revisar publicacoes com IA.")

    title = request.POST.get("title", "").strip()
    content = request.POST.get("content", "").strip()

    if not content:
        return JsonResponse({"error": "Escreva algo antes de pedir revisao."}, status=400)

    fallback = _local_review_post_copy(title, content)
    prompt = (
        "Reescreva a publicacao abaixo em tom institucional, claro e objetivo. "
        "Mantenha o contexto da turma. Responda em JSON com as chaves title e content.\n\n"
        f"TITULO: {title or 'Sem titulo'}\n"
        f"CONTEUDO: {content}"
    )
    reviewed, metadata = generate_json(prompt, fallback)
    return JsonResponse(
        {
            "reviewed": {
                "title": reviewed.get("title", title),
                "content": reviewed.get("content", content),
            },
            "meta": metadata,
        }
    )


@login_required
@require_POST
def feed_react(request):
    post = _get_scoped_post_or_404(request.user, request.POST.get("post_id"))
    reaction_type = request.POST.get("reaction_type")
    valid_types = {choice for choice, _label in PostReaction.ReactionType.choices}
    if reaction_type not in valid_types:
        return JsonResponse({"error": "Reacao invalida."}, status=400)
    current = set_post_reaction(post=post, user=request.user, reaction_type=reaction_type)
    post.refresh_from_db()
    post = Post.objects.prefetch_related("reactions__user").get(pk=post.pk)
    payload = _serialize_reaction_summary(post, request.user)
    payload["current_user_reaction"] = current
    return JsonResponse(payload)


@login_required
@require_POST
def feed_comment(request):
    post = _get_scoped_post_or_404(request.user, request.POST.get("post_id"))
    form = CommentForm(request.POST, prefix="comment")
    if not form.is_valid():
        return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
    comment = form.save(commit=False)
    comment.post = post
    comment.author = request.user
    comment.save()
    if post.author_id != request.user.id:
        _create_notification(
            post.author,
            None,
            Notification.NotificationType.COMMENT,
            f"{request.user.full_name or request.user.email} comentou em '{post.title}'.",
            f"{reverse('core:feed')}#post-{post.pk}",
        )
    serialized = _serialize_comment(comment)
    serialized["can_delete"] = True
    return JsonResponse(
        {
            "comment": serialized,
            "comment_count": Comment.objects.filter(post=post).count(),
        },
        status=201,
    )


@login_required
@require_POST
def feed_delete_comment(request):
    comment = (
        Comment.objects.select_related("post__classroom", "author")
        .filter(
            pk=request.POST.get("comment_id"),
            post__classroom__in=scoped_classrooms(request.user),
        )
        .first()
    )
    if not comment:
        raise Http404("Comentario nao encontrado.")
    if request.user.role != User.Role.ADMIN and comment.author_id != request.user.id:
        raise PermissionDenied("Voce nao pode excluir este comentario.")
    post = comment.post
    comment.delete()
    return JsonResponse({"comment_count": post.comments.count()})


@login_required
def attendance(request):
    if request.user.role not in {User.Role.TEACHER, User.Role.ADMIN}:
        raise PermissionDenied("Somente professores e administradores podem acessar este painel.")

    attendance_form = AttendanceRegistryForm(request.POST or None, user=request.user, prefix="attendance")
    student_records = []
    is_prepared = False
    attendance_context = {}

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "prepare_attendance" and attendance_form.is_valid():
            classroom = attendance_form.cleaned_data["classroom"]
            subject = attendance_form.cleaned_data["subject"]
            attendance_date = attendance_form.cleaned_data["date"]
            if request.user.role == User.Role.TEACHER and not teacher_has_subject_access(
                teacher=request.user,
                classroom=classroom,
                subject=subject,
            ):
                raise PermissionDenied("Professor so pode registrar frequencia nas disciplinas vinculadas.")

            enrollments = Enrollment.objects.filter(classroom=classroom, status=Enrollment.Status.APPROVED).select_related("student")
            existing_attendance = {
                item.student_id: item
                for item in Attendance.objects.filter(
                    classroom=classroom,
                    subject=subject,
                    date=attendance_date,
                ).select_related("student")
            }
            is_prepared = True
            attendance_context = {
                "classroom_pk": classroom.pk,
                "classroom_name": classroom.name,
                "subject_pk": subject.pk,
                "subject_name": subject.name,
                "date": attendance_date,
                "lesson_count": attendance_form.cleaned_data["lesson_count"],
                "student_total": enrollments.count(),
            }
            student_records = [
                {
                    "student": enrollment.student,
                    "attendance": existing_attendance.get(enrollment.student_id),
                }
                for enrollment in enrollments
            ]

        if action == "save_attendance":
            classroom = Classroom.objects.filter(pk=request.POST.get("attendance-classroom")).first()
            subject = Subject.objects.filter(pk=request.POST.get("attendance-subject")).first()
            raw_date = request.POST.get("attendance-date")
            try:
                attendance_date = date.fromisoformat(raw_date)
            except (TypeError, ValueError):
                attendance_date = None

            if not classroom or not subject:
                attendance_form.add_error(None, "Turma e disciplina sao obrigatorias.")
            elif not attendance_date:
                attendance_form.add_error(None, "Data da aula invalida.")
            elif request.user.role == User.Role.TEACHER and not teacher_has_subject_access(
                teacher=request.user,
                classroom=classroom,
                subject=subject,
            ):
                raise PermissionDenied("Professor so pode registrar frequencia nas disciplinas vinculadas.")
            else:
                enrollments = Enrollment.objects.filter(classroom=classroom, status=Enrollment.Status.APPROVED).select_related("student")
                saved_count = 0
                for enrollment in enrollments:
                    student = enrollment.student
                    status = request.POST.get(f"status_{student.id}", Attendance.Status.PRESENT)
                    if status not in {
                        Attendance.Status.PRESENT,
                        Attendance.Status.ABSENT,
                        Attendance.Status.EXCUSED,
                    }:
                        status = Attendance.Status.PRESENT
                    notes = request.POST.get(f"notes_{student.id}", "").strip()
                    notes = f"Aulas ministradas: {request.POST.get('attendance-lesson_count', '1')}" + (f" - {notes}" if notes else "")
                    Attendance.objects.update_or_create(
                        student=student,
                        subject=subject,
                        date=attendance_date,
                        defaults={
                            "classroom": classroom,
                            "marked_by": request.user,
                            "status": status,
                            "term": Grade.Term.BIMESTER_1,
                            "notes": notes,
                        },
                    )
                    saved_count += 1
                messages.success(request, f"Frequencia registrada para {saved_count} alunos.")
                return redirect("core:attendance")

    return render(
        request,
        "core/attendance.html",
        {
            "attendance_form": attendance_form,
            "student_records": student_records,
            "is_prepared": is_prepared,
            "attendance_context": attendance_context,
        },
    )


@login_required
def grades_batch(request):
    if request.user.role not in {User.Role.TEACHER, User.Role.ADMIN}:
        raise PermissionDenied("Somente professores e administradores podem acessar este painel.")

    assessment_id = request.GET.get("assessment_id")
    edit_assessment_id = request.GET.get("edit_assessment_id")
    selected_assessment = None
    is_editing = False
    student_list = []
    grade_context = {}

    if edit_assessment_id:
        selected_assessment = get_object_or_404(Assessment, pk=edit_assessment_id)
        if request.user.role == User.Role.TEACHER and selected_assessment.professor_id != request.user.id:
            raise PermissionDenied("Professor so pode editar suas proprias avaliacoes.")
        is_editing = True

    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"create_assessment", "edit_assessment"}:
            assessment_form = AssessmentForm(
                request.POST,
                user=request.user,
                instance=selected_assessment if is_editing else None,
                prefix="assessment",
            )
            if assessment_form.is_valid():
                assessment = assessment_form.save(commit=False)
                assessment.professor = request.user
                assessment.save()
                messages.success(request, "Avaliacao salva com sucesso.")
                return redirect(f"{reverse('core:grades_batch')}?assessment_id={assessment.pk}")
        elif action == "save_grades":
            assessment = get_object_or_404(Assessment, pk=request.POST.get("assessment_id"))
            if request.user.role == User.Role.TEACHER and assessment.professor_id != request.user.id:
                raise PermissionDenied("Professor so pode lancar notas nas suas proprias avaliacoes.")
            enrollments = Enrollment.objects.filter(classroom=assessment.classroom, status=Enrollment.Status.APPROVED).select_related("student")
            saved_count = 0
            for enrollment in enrollments:
                student = enrollment.student
                score_value = request.POST.get(f"score_{student.id}")
                if score_value is None or score_value.strip() == "":
                    continue
                try:
                    score = Decimal(score_value)
                except (InvalidOperation, TypeError):
                    continue
                GradeEntry.objects.update_or_create(
                    assessment=assessment,
                    student=student,
                    defaults={"score": score},
                )
                _create_notification(
                    student,
                    None,
                    Notification.NotificationType.GRADE,
                    f"Nova nota lancada em {assessment.subject.name}: {score}.",
                    reverse("core:notas"),
                )
                saved_count += 1
            messages.success(request, f"Notas salvas para {saved_count} alunos.")
            return redirect(f"{reverse('core:grades_batch')}?assessment_id={assessment.pk}")
    else:
        assessment_form = AssessmentForm(user=request.user, prefix="assessment", instance=selected_assessment if is_editing else None)

    if assessment_id:
        selected_assessment = get_object_or_404(Assessment, pk=assessment_id)
        if request.user.role == User.Role.TEACHER and selected_assessment.professor_id != request.user.id:
            raise PermissionDenied("Professor so pode visualizar suas proprias avaliacoes.")

    assessments = Assessment.objects.filter(professor=request.user).select_related("classroom", "subject").order_by("-date")
    if request.user.role == User.Role.ADMIN:
        assessments = Assessment.objects.select_related("classroom", "subject", "professor").order_by("-date")

    if selected_assessment:
        student_list = list(
            Enrollment.objects.filter(classroom=selected_assessment.classroom, status=Enrollment.Status.APPROVED).select_related("student")
        )
        existing_entries = GradeEntry.objects.filter(assessment=selected_assessment).select_related("student")
        grade_entry_map = {entry.student_id: entry for entry in existing_entries}
        for enrollment in student_list:
            entry = grade_entry_map.get(enrollment.student_id)
            enrollment.entry_score = entry.score if entry else ""
        grade_context = {
            "assessment": selected_assessment,
        }

    return render(
        request,
        "core/grades_batch.html",
        {
            "assessments": assessments,
            "assessment_form": assessment_form,
            "selected_assessment": selected_assessment,
            "student_list": student_list,
            "grade_context": grade_context,
            "is_editing": is_editing,
        },
    )


@login_required
def perfil(request):
    # BUG FIX: Perfil agora focado em dados do usuário, Configurações em preferências
    profile = getattr(request.user, 'profile', None)
    form = ProfileUpdateForm(request.POST or None, request.FILES or None, instance=profile, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil atualizado com sucesso.")
        return redirect("core:perfil")
    return render(request, "core/profile.html", {"form": form})

@login_required
def configuracoes(request):
    # PRIORIDADE 5: Página própria de configurações
    return render(request, "core/settings.html", {
        "user": request.user,
        "app_version": "1.2.0-stable",
        "build_date": "14/06/2026"
    })

    attendance = student_attendance_summary(request.user) if request.user.role == User.Role.STUDENT else None
    average = request.user.academic_average
    return render(
        request,
        "core/profile.html",
        {
            "form": form,
            "attendance": attendance,
            "average": average,
        },
    )


@login_required
@role_required("student")
def notas(request):
    report = student_grade_report(request.user) if request.user.role == User.Role.STUDENT else []
    attendance = student_attendance_summary(request.user) if request.user.role == User.Role.STUDENT else None
    attendance_subjects = student_attendance_subject_summary(request.user) if request.user.role == User.Role.STUDENT else {}
    overall_average = request.user.academic_average if request.user.role == User.Role.STUDENT else None
    grade_chart_data = student_grade_chart_data(request.user) if request.user.role == User.Role.STUDENT else []
    return render(
        request,
        "core/notas.html",
        {
            "report": report,
            "attendance": attendance,
            "attendance_subjects": attendance_subjects,
            "overall_average": overall_average,
            "grade_chart_data": json.dumps(grade_chart_data, ensure_ascii=False),
            "attendance_subjects_json": json.dumps(attendance_subjects, ensure_ascii=False),
        },
    )


@login_required
def turmas(request):
    classrooms = scoped_classrooms(request.user).select_related("academic_year", "grade_level", "homeroom_teacher").prefetch_related(
        "subjects",
        "classroom_subjects__teacher",
    ).annotate(
        student_count=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.APPROVED), distinct=True),
        subject_count=Count("subjects", distinct=True),
        teacher_count=Count("classroom_subjects__teacher", distinct=True),
    )
    create_form = ClassroomCreateForm(prefix="create")
    join_form = ClassroomJoinByCodeForm(prefix="join")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_classroom":
            if request.user.role != User.Role.ADMIN:
                messages.error(request, "Voce nao pode criar turmas.")
                return redirect("core:turmas")
            create_form = ClassroomCreateForm(request.POST, prefix="create")
            if create_form.is_valid():
                classroom = create_form.save(commit=False)
                classroom.created_by = request.user
                classroom.save()
                messages.success(request, f"Turma criada. Codigo de acesso: {classroom.access_code}")
                return redirect("core:turmas")

        if action == "join_classroom":
            if request.user.role != User.Role.STUDENT:
                messages.error(request, "Somente alunos entram por codigo.")
                return redirect("core:turmas")
            join_form = ClassroomJoinByCodeForm(request.POST, prefix="join")
            if join_form.is_valid():
                try:
                    enrollment = enroll_student_with_access_code(
                        student=request.user,
                        access_code=join_form.cleaned_data["access_code"],
                    )
                    messages.success(request, f"Matricula confirmada em {enrollment.classroom.name}.")
                    return redirect("core:turmas")
                except Classroom.DoesNotExist:
                    join_form.add_error("access_code", "Codigo de acesso invalido.")

    for classroom in classrooms:
        classroom.homeroom_name = classroom.homeroom_teacher.full_name if classroom.homeroom_teacher else "Nao definido"
        classroom.view_schedule_url = reverse("core:classroom_schedule", args=[classroom.pk])

    return render(
        request,
        "core/turmas.html",
        {
            "classrooms": classrooms,
            "create_form": create_form,
            "join_form": join_form,
        },
    )


@login_required
def classroom_schedule(request, classroom_id):
    classroom = get_object_or_404(
        scoped_classrooms(request.user).select_related("academic_year", "grade_level", "homeroom_teacher").prefetch_related(
            "weekly_schedules__subject",
            "weekly_schedules__teacher",
        ),
        pk=classroom_id,
    )

    schedules = classroom.weekly_schedules.filter(
        weekday__in=[
            WeeklySchedule.Weekday.MONDAY,
            WeeklySchedule.Weekday.TUESDAY,
            WeeklySchedule.Weekday.WEDNESDAY,
            WeeklySchedule.Weekday.THURSDAY,
            WeeklySchedule.Weekday.FRIDAY,
        ],
    ).order_by("weekday", "starts_at")

    weekday_labels = [
        (WeeklySchedule.Weekday.MONDAY, "Segunda"),
        (WeeklySchedule.Weekday.TUESDAY, "Terca"),
        (WeeklySchedule.Weekday.WEDNESDAY, "Quarta"),
        (WeeklySchedule.Weekday.THURSDAY, "Quinta"),
        (WeeklySchedule.Weekday.FRIDAY, "Sexta"),
    ]

    time_slots = sorted({(schedule.starts_at, schedule.ends_at) for schedule in schedules})
    schedule_map = {
        (schedule.weekday, schedule.starts_at, schedule.ends_at): schedule for schedule in schedules
    }

    subject_color_map = {}
    default_colors = [
        "#2563eb",
        "#16a34a",
        "#ca8a04",
        "#7c3aed",
        "#0f766e",
        "#db2777",
        "#0891b2",
    ]
    for schedule in schedules:
        if schedule.entry_type == WeeklySchedule.EntryType.CLASS and schedule.subject:
            key = schedule.subject.name.strip()
            if key not in subject_color_map:
                subject_color_map[key] = next(
                    (color for color in default_colors if color not in subject_color_map.values()),
                    default_colors[0],
                )

    rows = []
    for starts_at, ends_at in time_slots:
        cells = []
        for weekday, _label in weekday_labels:
            schedule = schedule_map.get((weekday, starts_at, ends_at))
            color = None
            if schedule and schedule.entry_type == WeeklySchedule.EntryType.CLASS and schedule.subject:
                color = subject_color_map.get(schedule.subject.name.strip(), default_colors[0])
            cells.append({
                "schedule": schedule,
                "color": color,
            })
        rows.append(
            {
                "time": f"{starts_at:%H:%M} - {ends_at:%H:%M}",
                "cells": cells,
            }
        )

    return render(
        request,
        "core/classroom_schedule.html",
        {
            "classroom": classroom,
            "weekday_labels": weekday_labels,
            "rows": rows,
            "subject_color_map": subject_color_map,
        },
    )


@login_required
def calendario(request):
    classrooms = scoped_classrooms(request.user)
    events = AcademicEvent.objects.select_related("classroom", "subject").filter(
        Q(classroom__in=classrooms) | Q(classroom__isnull=True)
    )
    today = timezone.localdate()
    for event in events:
        event_date = timezone.localtime(event.starts_at).date()
        delta_days = (event_date - today).days
        if delta_days < 0:
            event.urgency_label = "Encerrada"
            event.urgency_class = "legend-closed"
        elif delta_days <= 7:
            event.urgency_label = "Próxima"
            event.urgency_class = "legend-soon"
        else:
            event.urgency_label = "Futura"
            event.urgency_class = "legend-future"
        event.subject_color = _subject_color(event.subject.name if event.subject_id else "")
    return render(request, "core/calendario.html", {"events": events})


@login_required
@role_required("admin")
def administrador(request):
    context = {
        "total_usuarios": User.objects.count(),
        "total_turmas": Classroom.objects.count(),
        "total_disciplinas": Subject.objects.count(),
        "total_eventos": AcademicEvent.objects.count(),
        "total_anos_letivos": AcademicYear.objects.count(),
        "total_series": GradeLevel.objects.count(),
        "usuarios": User.objects.select_related("profile").all()[:6],
        "turmas": Classroom.objects.select_related("homeroom_teacher").prefetch_related("subjects")[:4],
        "eventos": AcademicEvent.objects.select_related("classroom", "subject")[:6],
        "notas": Grade.objects.select_related("student", "subject")[:6],
        "posts": Post.objects.select_related("author", "classroom")[:5],
        "atividades": Assignment.objects.select_related("classroom", "subject")[:5],
        "teacher_logins": User.objects.filter(role=User.Role.TEACHER).select_related("teacher_profile").order_by("first_name")[:10],
        "student_logins": User.objects.filter(role=User.Role.STUDENT).select_related("student_profile").order_by("first_name")[:10],
        "teacher_temp_password": "Professor@2026",
        "student_temp_password": "Aluno@2026",
    }
    return render(request, "core/administrador.html", context)
