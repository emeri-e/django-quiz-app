import json
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy, reverse
from django.db import transaction

from .models import Quiz, Category, Sitting, Progress, MCQuestion, TFQuestion, EssayQuestion, Answer
from .forms import (
    QuestionForm, EssayForm, MarkingForm, BulkUploadForm, QuizForm,
    MCQuestionForm, TFQuestionForm, EssayQuestionForm, MCAnswerFormSet,
    CategoryForm
)


# ── Quiz List & Detail ───────────────────────────────────────────────

def quiz_list_view(request):
    quizzes = Quiz.objects.filter(draft=False).select_related('category')
    
    featured_quiz = Quiz.objects.filter(featured=True, draft=False).first()
    
    # If a featured quiz exists, students only see that one
    if not request.user.is_staff:
        if featured_quiz:
            quizzes = quizzes.filter(pk=featured_quiz.pk)
            
    return render(request, 'quiz/quiz_list.html', {
        'quizzes': quizzes,
        'featured_quiz': featured_quiz,
        'is_student': not request.user.is_staff
    })


def quiz_detail_view(request, slug):
    quiz = get_object_or_404(Quiz, url=slug, draft=False)
    
    # If another quiz is featured, students are restricted
    if not request.user.is_staff:
        featured_quiz = Quiz.objects.filter(featured=True, draft=False).first()
        if featured_quiz and featured_quiz != quiz:
            messages.info(request, "Only the featured test is available at this time.")
            return redirect('quiz:quiz_detail', slug=featured_quiz.url)

    previous_sittings = []
    can_take = True
    incomplete_sitting = None

    if request.user.is_authenticated:
        previous_sittings = Sitting.objects.filter(
            user=request.user, quiz=quiz, complete=True
        ).order_by('-end')

        incomplete_sitting = Sitting.objects.user_sitting(request.user, quiz)

        if quiz.single_attempt and previous_sittings.exists():
            can_take = False

    return render(request, 'quiz/quiz_detail.html', {
        'quiz': quiz,
        'previous_sittings': previous_sittings,
        'can_take': can_take,
        'incomplete_sitting': incomplete_sitting,
        'question_count': quiz.get_question_count(),
    })


# ── Quiz Take ────────────────────────────────────────────────────────

def quiz_take_view(request, slug):
    quiz = get_object_or_404(Quiz, url=slug, draft=False)
    
    # Restriction for featured quiz
    if not request.user.is_staff:
        featured_quiz = Quiz.objects.filter(featured=True, draft=False).first()
        if featured_quiz and featured_quiz != quiz:
            messages.info(request, "Only the featured test is available at this time.")
            return redirect('quiz:quiz_detail', slug=featured_quiz.url)

    # Check single attempt for logged-in users
    if request.user.is_authenticated and quiz.single_attempt:
        if Sitting.objects.filter(user=request.user, quiz=quiz, complete=True).exists():
            messages.warning(request, 'You have already completed this quiz.')
            return redirect('quiz:quiz_detail', slug=slug)

    # Get or create sitting
    sitting = None
    if request.user.is_authenticated:
        sitting = Sitting.objects.user_sitting(request.user, quiz)

    # For anonymous users, try session
    if not request.user.is_authenticated:
        sitting_id = request.session.get(f'quiz_{quiz.pk}_sitting')
        if sitting_id:
            try:
                sitting = Sitting.objects.get(pk=sitting_id, complete=False)
            except Sitting.DoesNotExist:
                sitting = None

    if sitting is None:
        sitting = Sitting.objects.new_sitting(request.user, quiz)
        if not request.user.is_authenticated:
            request.session[f'quiz_{quiz.pk}_sitting'] = sitting.pk

    # Calculate time limit
    time_limit_seconds = 0
    if quiz.time_limit:
        deadline = sitting.start + timezone.timedelta(minutes=quiz.time_limit)
        time_left = (deadline - timezone.now()).total_seconds()
        
        if time_left <= 0:
            # Time has completely elapsed while they were away.
            # Mark complete and redirect to results.
            sitting.mark_quiz_complete()
            if request.user.is_authenticated:
                progress, _ = Progress.objects.get_or_create(user=request.user)
                progress.update_score(
                    quiz.category,
                    sitting.current_score,
                    sitting.get_total_questions(),
                )
            else:
                request.session.pop(f'quiz_{quiz.pk}_sitting', None)
            messages.info(request, "Time has elapsed for this attempt. It has been automatically submitted.")
            return redirect('quiz:quiz_results', slug=slug, sitting_pk=sitting.pk)
            
        time_limit_seconds = int(time_left)

    # Handle POST (Single submission of all questions)
    if request.method == 'POST':
        for q in sitting.get_all_questions():
            if q.question_type == 'essay':
                form = EssayForm(request.POST, prefix=str(q.pk))
            else:
                form = QuestionForm(q, request.POST, prefix=str(q.pk))
            
            if form.is_valid():
                answer = form.cleaned_data.get('answer')
                if answer:
                    sitting.add_user_answer(q, answer)
                    if q.question_type != 'essay':
                        is_correct = q.check_if_correct(answer)
                        if is_correct:
                            sitting.add_to_score(1)
                        else:
                            sitting.add_incorrect_question(q)

        sitting.mark_quiz_complete()
        
        # Update progress for logged-in users
        if request.user.is_authenticated:
            progress, _ = Progress.objects.get_or_create(user=request.user)
            progress.update_score(
                quiz.category,
                sitting.current_score,
                sitting.get_total_questions(),
            )
        
        # Clean session for anonymous
        if not request.user.is_authenticated:
            request.session.pop(f'quiz_{quiz.pk}_sitting', None)

        return redirect('quiz:quiz_results', slug=slug, sitting_pk=sitting.pk)

    # For GET request, load all questions and their forms
    questions_data = []
    for idx, q in enumerate(sitting.get_all_questions()):
        if q.question_type == 'essay':
            form = EssayForm(prefix=str(q.pk))
        else:
            form = QuestionForm(q, prefix=str(q.pk))
            
        questions_data.append({
            'index': idx,  # 0-based for JS arrays
            'number': idx + 1, # 1-based for UI
            'question': q,
            'form': form,
        })

    return render(request, 'quiz/quiz_take.html', {
        'quiz': quiz,
        'sitting': sitting,
        'questions_data': questions_data,
        'time_limit_seconds': time_limit_seconds,
    })


# ── Quiz Results ─────────────────────────────────────────────────────

def quiz_results_view(request, slug, sitting_pk):
    quiz = get_object_or_404(Quiz, url=slug)
    sitting = get_object_or_404(Sitting, pk=sitting_pk, complete=True)

    # Security: only let the sitting owner (or staff/anon) view results
    if sitting.user and request.user != sitting.user and not request.user.is_staff:
        messages.error(request, 'You do not have permission to view these results.')
        return redirect('quiz:quiz_list')

    questions_with_answers = sitting.get_questions_with_answers()
    passed = sitting.check_if_passed()

    if quiz.hide_results:
        return render(request, 'quiz/quiz_results.html', {
            'quiz': quiz,
            'sitting': sitting,
            'results_hidden': True,
        })

    return render(request, 'quiz/quiz_results.html', {
        'quiz': quiz,
        'sitting': sitting,
        'questions_with_answers': questions_with_answers,
        'passed': passed,
        'percent': sitting.get_percent_correct(),
        'results_hidden': False,
    })


# ── Categories ───────────────────────────────────────────────────────

def category_list_view(request):
    categories = Category.objects.all()
    return render(request, 'quiz/category_list.html', {'categories': categories})


def category_detail_view(request, slug):
    # Use name as slug for simplicity
    category = get_object_or_404(Category, name__iexact=slug.replace('-', ' '))
    quizzes = Quiz.objects.filter(category=category, draft=False)

    # Restriction for featured quiz
    if not request.user.is_staff:
        featured_quiz = Quiz.objects.filter(featured=True, draft=False).first()
        if featured_quiz:
            quizzes = quizzes.filter(pk=featured_quiz.pk)

    user_scores = {}
    if request.user.is_authenticated:
        for quiz in quizzes:
            sittings = Sitting.objects.filter(
                user=request.user, quiz=quiz, complete=True
            ).order_by('-end')
            if sittings.exists():
                latest = sittings.first()
                user_scores[quiz.pk] = {
                    'score': latest.current_score,
                    'total': latest.get_total_questions(),
                    'percent': latest.get_percent_correct(),
                    'passed': latest.check_if_passed(),
                }

    return render(request, 'quiz/category_detail.html', {
        'category': category,
        'quizzes': quizzes,
        'user_scores': user_scores,
    })


# ── Progress ─────────────────────────────────────────────────────────

@login_required
def progress_view(request):
    progress, _ = Progress.objects.get_or_create(user=request.user)
    scores = progress.get_all_scores()
    return render(request, 'quiz/progress.html', {'scores': scores})


# ── Marking ──────────────────────────────────────────────────────────

@login_required
@permission_required('quiz.view_sittings', raise_exception=True)
def marking_list_view(request):
    sittings = Sitting.objects.filter(complete=True).select_related('user', 'quiz')

    # Filters
    quiz_filter = request.GET.get('quiz')
    user_filter = request.GET.get('user')
    status_filter = request.GET.get('status')

    if quiz_filter:
        sittings = sittings.filter(quiz__pk=quiz_filter)
    if user_filter:
        sittings = sittings.filter(user__username__icontains=user_filter)

    # Filter by grading status in memory since it's a property
    if status_filter:
        sittings = [s for s in sittings if s.get_grading_status == status_filter]

    quizzes = Quiz.objects.all()

    return render(request, 'quiz/marking_list.html', {
        'sittings': sittings,
        'quizzes': quizzes,
        'quiz_filter': quiz_filter,
        'user_filter': user_filter,
        'status_filter': status_filter,
    })


@login_required
@permission_required('quiz.view_sittings', raise_exception=True)
def marking_detail_view(request, pk):
    sitting = get_object_or_404(Sitting, pk=pk, complete=True)
    questions_with_answers = sitting.get_questions_with_answers()

    # Handle essay marking POST
    if request.method == 'POST':
        graded_list = sitting.get_graded_essays()
        incorrect_list = [str(x) for x in sitting.get_incorrect_questions()]
        graded_count = 0
        regraded_count = 0
        
        for key, mark in request.POST.items():
            if key.startswith('mark_') and mark in ['correct', 'incorrect']:
                try:
                    question_pk = int(key.replace('mark_', ''))
                    question_pk_str = str(question_pk)
                    question = EssayQuestion.objects.get(pk=question_pk)
                    
                    if question_pk_str not in graded_list:
                        # First time grading this essay
                        if mark == 'correct':
                            sitting.add_to_score(1)
                        else:
                            sitting.add_incorrect_question(question)
                        
                        sitting.mark_essay_graded(question)
                        graded_count += 1
                    else:
                        # Regrading an already graded essay
                        was_incorrect = question_pk_str in incorrect_list
                        
                        if was_incorrect and mark == 'correct':
                            # Changed from incorrect -> correct
                            sitting.remove_incorrect_question(question)
                            sitting.add_to_score(1)
                            regraded_count += 1
                        elif not was_incorrect and mark == 'incorrect':
                            # Changed from correct -> incorrect
                            sitting.add_incorrect_question(question)
                            sitting.remove_from_score(1)
                            regraded_count += 1
                            
                except (ValueError, EssayQuestion.DoesNotExist):
                    pass
                    
        if graded_count > 0 or regraded_count > 0:
            msg = []
            if graded_count > 0:
                msg.append(f'Successfully graded {graded_count} new essays.')
            if regraded_count > 0:
                msg.append(f'Successfully updated grades for {regraded_count} existing essays.')
            messages.success(request, ' '.join(msg))
        else:
            messages.info(request, 'No changes were made to the essay grades.')
            
        return redirect('quiz:marking_detail', pk=pk)

    return render(request, 'quiz/marking_detail.html', {
        'sitting': sitting,
        'questions_with_answers': questions_with_answers,
    })


# ── Sitting List (view_sittings permission) ──────────────────────────

@login_required
@permission_required('quiz.view_sittings', raise_exception=True)
def sitting_list_view(request):
    sittings = Sitting.objects.filter(complete=True).select_related('user', 'quiz')
    return render(request, 'quiz/sitting_list.html', {'sittings': sittings})


@login_required
@permission_required('quiz.view_sittings', raise_exception=True)
def sitting_detail_view(request, pk):
    sitting = get_object_or_404(Sitting, pk=pk, complete=True)
    questions_with_answers = sitting.get_questions_with_answers()
    return render(request, 'quiz/sitting_detail.html', {
        'sitting': sitting,
        'questions_with_answers': questions_with_answers,
    })


# ── Admin Bulk Upload ────────────────────────────────────────────────

@login_required
def bulk_upload_view(request, slug):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('quiz:quiz_list')

    quiz = get_object_or_404(Quiz, url=slug)

    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']

            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'This is not a CSV file.')
                return redirect('quiz:bulk_upload', slug=slug)

            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)

                # Required: Question_Content. Optional: Question_Type, Correct_Answer, Wrong_Answer_1/2/3, Explanation
                required_headers = ['Question_Content']
                if reader.fieldnames is None:
                    messages.error(request, 'The CSV file appears to be empty.')
                    return redirect('quiz:bulk_upload', slug=slug)

                missing = [h for h in required_headers if h not in reader.fieldnames]
                if missing:
                    messages.error(request, f'Missing required column: {", ".join(missing)}')
                    return redirect('quiz:bulk_upload', slug=slug)

                # Default category is the quiz's own category
                default_category = quiz.category

                count = 0
                errors = []
                for row_num, row in enumerate(reader, start=2):
                    content = row.get('Question_Content', '').strip()
                    if not content:
                        continue  # Skip blank rows

                    q_type = row.get('Question_Type', 'MC').strip().upper()
                    correct_ans = row.get('Correct_Answer', '').strip()
                    wrong1 = row.get('Wrong_Answer_1', '').strip()
                    wrong2 = row.get('Wrong_Answer_2', '').strip()
                    wrong3 = row.get('Wrong_Answer_3', '').strip()
                    explanation = row.get('Explanation', '').strip()

                    if q_type == 'MC':
                        if not correct_ans:
                            errors.append(f'Row {row_num}: MC question missing Correct_Answer.')
                            continue
                        mcq = MCQuestion.objects.create(
                            content=content,
                            category=default_category,
                            explanation=explanation,
                            answer_order='random',
                        )
                        mcq.quiz.add(quiz)
                        Answer.objects.create(question=mcq, content=correct_ans, correct=True)
                        if wrong1: Answer.objects.create(question=mcq, content=wrong1, correct=False)
                        if wrong2: Answer.objects.create(question=mcq, content=wrong2, correct=False)
                        if wrong3: Answer.objects.create(question=mcq, content=wrong3, correct=False)

                    elif q_type == 'TF':
                        if correct_ans.lower() not in ('true', 'false'):
                            errors.append(f'Row {row_num}: TF question Correct_Answer must be "True" or "False".')
                            continue
                        tfq = TFQuestion.objects.create(
                            content=content,
                            category=default_category,
                            explanation=explanation,
                            correct=(correct_ans.lower() == 'true'),
                        )
                        tfq.quiz.add(quiz)

                    elif q_type == 'ESSAY':
                        eq = EssayQuestion.objects.create(
                            content=content,
                            category=default_category,
                            explanation=explanation,
                        )
                        eq.quiz.add(quiz)

                    else:
                        errors.append(f'Row {row_num}: Unknown Question_Type "{q_type}". Use MC, TF, or ESSAY.')
                        continue

                    count += 1

                if errors:
                    for err in errors[:5]:
                        messages.warning(request, err)
                    if len(errors) > 5:
                        messages.warning(request, f'...and {len(errors) - 5} more issues.')

                messages.success(request, f'Successfully uploaded {count} question{"s" if count != 1 else ""} to "{quiz.title}"!')
                return redirect('quiz:quiz_admin_detail', slug=slug)

            except Exception as e:
                messages.error(request, f'Error processing file: {e}')
                return redirect('quiz:bulk_upload', slug=slug)
    else:
        form = BulkUploadForm()

    return render(request, 'quiz/admin/bulk_upload.html', {
        'form': form,
        'quiz': quiz,
        'title': f'Bulk Upload Questions — {quiz.title}',
    })

# ── Frontend Admin Management ────────────────────────────────────────

class QuizCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'quiz/admin/quiz_form.html'
    permission_required = 'quiz.add_quiz'

    def get_success_url(self):
        messages.success(self.request, "Quiz created successfully.")
        return reverse_lazy('quiz:quiz_admin_detail', kwargs={'slug': self.object.url})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Quiz'
        return context


class QuizUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'quiz/admin/quiz_form.html'
    permission_required = 'quiz.change_quiz'
    slug_field = 'url'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        messages.success(self.request, "Quiz updated successfully.")
        return reverse_lazy('quiz:quiz_admin_detail', kwargs={'slug': self.object.url})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Quiz: {self.object.title}'
        return context


@login_required
@permission_required('quiz.change_quiz', raise_exception=True)
def quiz_featured_toggle(request, slug):
    quiz = get_object_or_404(Quiz, url=slug)
    quiz.featured = not quiz.featured
    quiz.save()
    
    status = "featured" if quiz.featured else "un-featured"
    messages.success(request, f'"{quiz.title}" has been {status}.')
    return redirect('quiz:quiz_admin_detail', slug=quiz.url)


class QuizAdminDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Quiz
    template_name = 'quiz/admin/quiz_admin_detail.html'
    permission_required = 'quiz.change_quiz'
    slug_field = 'url'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.object
        
        # Submissions
        sittings = Sitting.objects.filter(quiz=quiz, complete=True).select_related('user').order_by('-end')
        
        # Questions Breakdown
        mc_q = quiz.mc_questions.all()
        tf_q = quiz.tf_questions.all()
        essay_q = quiz.essay_questions.all()
        
        context['sittings'] = sittings
        context['mc_questions'] = mc_q
        context['tf_questions'] = tf_q
        context['essay_questions'] = essay_q
        context['featured_quiz'] = Quiz.objects.filter(featured=True).first()
        return context

# ── Question Management ──────────────────────────────────────────────

class MCQuestionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = MCQuestion
    form_class = MCQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.add_mcquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, url=self.kwargs['slug'])
        context['title'] = 'Add Multiple Choice Question'
        if self.request.POST:
            context['answers'] = MCAnswerFormSet(self.request.POST, self.request.FILES)
        else:
            context['answers'] = MCAnswerFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        answers = context['answers']
        
        with transaction.atomic():
            self.object = form.save()
            quiz = context['quiz']
            self.object.quiz.add(quiz)
            
            if answers.is_valid():
                answers.instance = self.object
                answers.save()
                
        messages.success(self.request, "Multiple choice question added successfully.")
        return redirect('quiz:quiz_admin_detail', slug=quiz.url)


class TFQuestionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = TFQuestion
    form_class = TFQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.add_tfquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, url=self.kwargs['slug'])
        context['title'] = 'Add True/False Question'
        return context

    def form_valid(self, form):
        self.object = form.save()
        quiz = self.get_context_data()['quiz']
        self.object.quiz.add(quiz)
        messages.success(self.request, "True/False question added successfully.")
        return redirect('quiz:quiz_admin_detail', slug=quiz.url)


class EssayQuestionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = EssayQuestion
    form_class = EssayQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.add_essayquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = get_object_or_404(Quiz, url=self.kwargs['slug'])
        context['title'] = 'Add Essay Question'
        return context

    def form_valid(self, form):
        self.object = form.save()
        quiz = self.get_context_data()['quiz']
        self.object.quiz.add(quiz)
        messages.success(self.request, "Essay question added successfully.")
        return redirect('quiz:quiz_admin_detail', slug=quiz.url)

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'quiz/admin/category_form.html'
    permission_required = 'quiz.add_category'
    success_url = reverse_lazy('quiz:category_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Category'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully.")
        return super().form_valid(form)


# ── Question Update Views ────────────────────────────────────────────

class MCQuestionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = MCQuestion
    form_class = MCQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.change_mcquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.object.quiz.first()
        context['quiz'] = quiz
        context['title'] = 'Edit Multiple Choice Question'
        if self.request.POST:
            context['answers'] = MCAnswerFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['answers'] = MCAnswerFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        answers = context['answers']
        quiz = context['quiz']

        with transaction.atomic():
            self.object = form.save()
            if answers.is_valid():
                answers.instance = self.object
                answers.save()

        messages.success(self.request, "Multiple choice question updated successfully.")
        if quiz:
            return redirect('quiz:quiz_admin_detail', slug=quiz.url)
        return redirect('quiz:quiz_list')


class TFQuestionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = TFQuestion
    form_class = TFQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.change_tfquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.object.quiz.first()
        context['quiz'] = quiz
        context['title'] = 'Edit True/False Question'
        return context

    def form_valid(self, form):
        self.object = form.save()
        quiz = self.object.quiz.first()
        messages.success(self.request, "True/False question updated successfully.")
        if quiz:
            return redirect('quiz:quiz_admin_detail', slug=quiz.url)
        return redirect('quiz:quiz_list')


class EssayQuestionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = EssayQuestion
    form_class = EssayQuestionForm
    template_name = 'quiz/admin/question_form.html'
    permission_required = 'quiz.change_essayquestion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.object.quiz.first()
        context['quiz'] = quiz
        context['title'] = 'Edit Essay Question'
        return context

    def form_valid(self, form):
        self.object = form.save()
        quiz = self.object.quiz.first()
        messages.success(self.request, "Essay question updated successfully.")
        if quiz:
            return redirect('quiz:quiz_admin_detail', slug=quiz.url)
        return redirect('quiz:quiz_list')

