from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    # Quiz
    path('', views.quiz_list_view, name='quiz_list'),
    path('quiz/<slug:slug>/', views.quiz_detail_view, name='quiz_detail'),
    path('quiz/<slug:slug>/take/', views.quiz_take_view, name='quiz_take'),
    path('quiz/<slug:slug>/results/<int:sitting_pk>/', views.quiz_results_view, name='quiz_results'),

    # Categories
    path('category/', views.category_list_view, name='category_list'),
    path('category/<slug:slug>/', views.category_detail_view, name='category_detail'),

    # Progress
    path('progress/', views.progress_view, name='progress'),

    # Marking
    path('marking/', views.marking_list_view, name='marking_list'),
    path('marking/<int:pk>/', views.marking_detail_view, name='marking_detail'),

    # Sittings
    path('sittings/', views.sitting_list_view, name='sitting_list'),
    path('sittings/<int:pk>/', views.sitting_detail_view, name='sitting_detail'),

    # Admin Frontend Management
    path('manage/quiz/add/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('manage/quiz/<slug:slug>/', views.QuizAdminDetailView.as_view(), name='quiz_admin_detail'),
    path('manage/quiz/<slug:slug>/edit/', views.QuizUpdateView.as_view(), name='quiz_update'),
    path('manage/quiz/<slug:slug>/toggle-featured/', views.quiz_featured_toggle, name='quiz_featured_toggle'),
    path('manage/quiz/<slug:slug>/bulk-upload/', views.bulk_upload_view, name='bulk_upload'),
    path('manage/quiz/<slug:slug>/question/add/mc/', views.MCQuestionCreateView.as_view(), name='mcquestion_create'),
    path('manage/quiz/<slug:slug>/question/add/tf/', views.TFQuestionCreateView.as_view(), name='tfquestion_create'),
    path('manage/quiz/<slug:slug>/question/add/essay/', views.EssayQuestionCreateView.as_view(), name='essayquestion_create'),
    path('manage/question/mc/<int:pk>/edit/', views.MCQuestionUpdateView.as_view(), name='mcquestion_update'),
    path('manage/question/tf/<int:pk>/edit/', views.TFQuestionUpdateView.as_view(), name='tfquestion_update'),
    path('manage/question/essay/<int:pk>/edit/', views.EssayQuestionUpdateView.as_view(), name='essayquestion_update'),
    path('manage/category/add/', views.CategoryCreateView.as_view(), name='category_create'),
]
