from django.contrib import admin

from .models import (
    Category, SubCategory, Quiz,
    MCQuestion, Answer, TFQuestion, EssayQuestion,
    Progress, Sitting,
)


# ── Category ─────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


# ── Quiz ─────────────────────────────────────────────────────────────

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'featured', 'draft', 'single_attempt', 'hide_results', 'pass_mark')
    list_filter = ('category', 'featured', 'draft', 'single_attempt', 'hide_results', 'exam_paper')
    search_fields = ('title', 'description')
    prepopulated_fields = {'url': ('title',)}


# ── Multiple Choice ──────────────────────────────────────────────────

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4
    min_num = 2


@admin.register(MCQuestion)
class MCQuestionAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'category', 'answer_order')
    list_filter = ('category', 'quiz')
    search_fields = ('content',)
    filter_horizontal = ('quiz',)
    inlines = [AnswerInline]

    def content_short(self, obj):
        return obj.content[:80]
    content_short.short_description = 'Question'


# ── True / False ─────────────────────────────────────────────────────

@admin.register(TFQuestion)
class TFQuestionAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'category', 'correct')
    list_filter = ('category', 'quiz', 'correct')
    search_fields = ('content',)
    filter_horizontal = ('quiz',)

    def content_short(self, obj):
        return obj.content[:80]
    content_short.short_description = 'Question'


# ── Essay ────────────────────────────────────────────────────────────

@admin.register(EssayQuestion)
class EssayQuestionAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'category')
    list_filter = ('category', 'quiz')
    search_fields = ('content',)
    filter_horizontal = ('quiz',)

    def content_short(self, obj):
        return obj.content[:80]
    content_short.short_description = 'Question'


# ── Progress & Sitting ───────────────────────────────────────────────

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)


@admin.register(Sitting)
class SittingAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'current_score', 'complete', 'start', 'end')
    list_filter = ('quiz', 'complete')
    search_fields = ('user__username', 'quiz__title')
