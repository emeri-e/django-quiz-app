import json
import random

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator


# ── Category & SubCategory ──────────────────────────────────────────

class Category(models.Model):
    name = models.CharField(max_length=250, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    name = models.CharField(max_length=250)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Sub-Category'
        verbose_name_plural = 'Sub-Categories'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} — {self.name}"


# ── Quiz ─────────────────────────────────────────────────────────────

class Quiz(models.Model):
    title = models.CharField(max_length=60, verbose_name='Title')
    description = models.TextField(
        blank=True,
        help_text='A description of the quiz.',
    )
    url = models.SlugField(
        max_length=60,
        unique=True,
        help_text='A user-friendly URL slug.',
        verbose_name='URL',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quizzes',
    )
    image = models.ImageField(
        upload_to='quiz_images/',
        blank=True,
        null=True,
        help_text='An optional image for the quiz.',
    )
    random_order = models.BooleanField(
        default=False,
        verbose_name='Random Order',
        help_text='Display the questions in a random order each time?',
    )
    max_questions = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Max Questions',
        help_text='Number of questions to show (random subset). '
                  'Leave blank to show all.',
    )
    time_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Time Limit (minutes)',
        help_text='Time limit for the quiz in minutes. Leave blank for no limit.',
    )
    answers_at_end = models.BooleanField(
        default=False,
        verbose_name='Answers at End',
        help_text='Show correct answers only after quiz completion?',
    )
    hide_results = models.BooleanField(
        default=False,
        verbose_name='Hide Results',
        help_text='If yes, the user will not see their score or marked answers upon completion. '
                  'Useful for standard exams where results are released later.',
    )
    exam_paper = models.BooleanField(
        default=False,
        verbose_name='Exam Paper',
        help_text='If yes, the result of each attempt is stored. '
                  'Necessary for marking.',
    )
    single_attempt = models.BooleanField(
        default=False,
        verbose_name='Single Attempt',
        help_text='If yes, only one attempt per user is allowed.',
    )
    pass_mark = models.SmallIntegerField(
        default=0,
        verbose_name='Pass Mark (%)',
        help_text='Percentage required to pass. 0 means no pass mark.',
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    success_text = models.TextField(
        blank=True,
        verbose_name='Success Text',
        help_text='Displayed if the user passes.',
    )
    fail_text = models.TextField(
        blank=True,
        verbose_name='Fail Text',
        help_text='Displayed if the user fails.',
    )
    draft = models.BooleanField(
        default=False,
        verbose_name='Draft',
        help_text='If yes, the quiz is not publicly visible.',
    )
    featured = models.BooleanField(
        default=False,
        verbose_name='Featured',
        help_text='If yes, this quiz will be the ONLY one visible to students.',
    )

    class Meta:
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'
        ordering = ['title']
        permissions = (
            ('view_sittings', 'Can see completed exams.'),
        )

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.url:
            self.url = slugify(self.title)
        
        if self.featured:
            # Setting this quiz as featured should un-feature all others
            Quiz.objects.exclude(pk=self.pk).update(featured=False)
            
        super().save(*args, **kwargs)

    def get_questions(self):
        """
        Return all question objects linked to this quiz.
        (MC, TF, and Essay via their M2M to quiz)
        """
        from itertools import chain
        mc = self.mc_questions.all()
        tf = self.tf_questions.all()
        essay = self.essay_questions.all()
        return list(chain(mc, tf, essay))

    def get_question_count(self):
        return len(self.get_questions())

    def get_max_score(self):
        """Max possible score — essay questions are excluded from auto-score."""
        mc_count = self.mc_questions.count()
        tf_count = self.tf_questions.count()
        return mc_count + tf_count


# ── Question (Abstract Base) ────────────────────────────────────────

ANSWER_ORDER_OPTIONS = (
    ('content', 'Content'),
    ('random', 'Random'),
    ('none', 'None'),
)


class Question(models.Model):
    """Abstract base class for all question types."""

    figure = models.ImageField(
        upload_to='question_images/',
        blank=True,
        null=True,
        verbose_name='Figure',
        help_text='An optional image displayed alongside the question.',
    )
    content = models.TextField(
        verbose_name='Question',
        help_text='Enter the question text.',
    )
    explanation = models.TextField(
        blank=True,
        verbose_name='Explanation',
        help_text='Explanation shown after the question is answered.',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.content[:80]


# ── Multiple Choice ──────────────────────────────────────────────────

class MCQuestion(Question):
    quiz = models.ManyToManyField(Quiz, related_name='mc_questions', blank=True)
    answer_order = models.CharField(
        max_length=30,
        choices=ANSWER_ORDER_OPTIONS,
        default='random',
        help_text='The order in which answers are displayed.',
    )

    class Meta:
        verbose_name = 'Multiple Choice Question'
        verbose_name_plural = 'Multiple Choice Questions'

    def check_if_correct(self, guess):
        answer = Answer.objects.get(id=guess)
        return answer.correct

    def get_answers(self):
        return self.answers.all()

    def get_answers_list(self):
        answers = self.answers.all()
        if self.answer_order == 'random':
            answers = list(answers)
            random.shuffle(answers)
        return answers

    def get_correct_answer(self):
        answer = self.answers.filter(correct=True).first()
        return answer.content if answer else ""

    @property
    def question_type(self):
        return 'mc'


class Answer(models.Model):
    question = models.ForeignKey(
        MCQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    content = models.CharField(max_length=1000, verbose_name='Answer')
    correct = models.BooleanField(
        default=False,
        verbose_name='Correct',
        help_text='Is this the correct answer?',
    )

    class Meta:
        verbose_name = 'Answer'
        verbose_name_plural = 'Answers'

    def __str__(self):
        return self.content


# ── True / False ─────────────────────────────────────────────────────

class TFQuestion(Question):
    quiz = models.ManyToManyField(Quiz, related_name='tf_questions', blank=True)
    correct = models.BooleanField(
        default=False,
        verbose_name='Correct Answer',
        help_text='Tick if the correct answer is True.',
    )

    class Meta:
        verbose_name = 'True/False Question'
        verbose_name_plural = 'True/False Questions'

    def check_if_correct(self, guess):
        return str(self.correct) == str(guess)

    def get_correct_answer(self):
        return 'True' if self.correct else 'False'

    @property
    def question_type(self):
        return 'tf'


# ── Essay ────────────────────────────────────────────────────────────

class EssayQuestion(Question):
    quiz = models.ManyToManyField(Quiz, related_name='essay_questions', blank=True)

    class Meta:
        verbose_name = 'Essay Question'
        verbose_name_plural = 'Essay Questions'

    def check_if_correct(self, guess):
        # Essays are manually graded
        return None

    def get_correct_answer(self):
        return 'To be marked manually.'

    @property
    def question_type(self):
        return 'essay'


# ── Progress ─────────────────────────────────────────────────────────

class Progress(models.Model):
    """Tracks a user's success rate per category.

    score is stored as a CSV string: "category_name,score,possible, ..."
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='User',
    )
    score = models.TextField(
        default='',
        blank=True,
        verbose_name='Score',
    )

    class Meta:
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progress'

    def __str__(self):
        return f"Progress for {self.user.username}"

    def _parse_score(self):
        """Parse the CSV score string into a dict."""
        data = {}
        if not self.score:
            return data
        items = self.score.split(',')
        # Format: cat_name, score, possible, cat_name, score, possible, ...
        while len(items) >= 3:
            cat = items.pop(0)
            try:
                score = int(items.pop(0))
                possible = int(items.pop(0))
            except (ValueError, IndexError):
                break
            data[cat] = {'score': score, 'possible': possible}
        return data

    def _save_score(self, data):
        """Save dict back to CSV string."""
        parts = []
        for cat_name, vals in data.items():
            parts.extend([cat_name, str(vals['score']), str(vals['possible'])])
        self.score = ','.join(parts)
        self.save()

    def update_score(self, category, score_to_add, possible_to_add):
        """Add score for a category."""
        if not category:
            return
        cat_name = str(category)
        data = self._parse_score()
        if cat_name in data:
            data[cat_name]['score'] += score_to_add
            data[cat_name]['possible'] += possible_to_add
        else:
            data[cat_name] = {'score': score_to_add, 'possible': possible_to_add}
        self._save_score(data)

    def get_all_scores(self):
        """Return list of dicts: {category, score, possible, percent}."""
        data = self._parse_score()
        result = []
        for cat_name, vals in data.items():
            percent = 0
            if vals['possible'] > 0:
                percent = int(round(vals['score'] / vals['possible'] * 100))
            result.append({
                'category': cat_name,
                'score': vals['score'],
                'possible': vals['possible'],
                'percent': percent,
            })
        return result


# ── Sitting ──────────────────────────────────────────────────────────

class SittingManager(models.Manager):
    def new_sitting(self, user, quiz):
        """Create a new sitting for a quiz."""
        questions = quiz.get_questions()

        if quiz.random_order:
            random.shuffle(questions)

        if quiz.max_questions and quiz.max_questions < len(questions):
            questions = questions[:quiz.max_questions]

        # Store question PKs and types as JSON
        # Format: [{"pk": 1, "type": "mc"}, {"pk": 2, "type": "tf"}, ...]
        question_set = [
            {'pk': q.pk, 'type': q.question_type}
            for q in questions
        ]

        sitting = self.create(
            user=user if user.is_authenticated else None,
            quiz=quiz,
            question_order=json.dumps([q['pk'] for q in question_set]),
            question_list=json.dumps(question_set),
            incorrect_questions='',
            current_score=0,
            complete=False,
            user_answers='{}',
        )
        return sitting

    def user_sitting(self, user, quiz):
        """Get incomplete sitting for logged-in user, or None."""
        if not user.is_authenticated:
            return None
        try:
            return self.get(user=user, quiz=quiz, complete=False)
        except self.model.DoesNotExist:
            return None
        except self.model.MultipleObjectsReturned:
            # Return the most recent one
            return self.filter(
                user=user, quiz=quiz, complete=False
            ).order_by('-start').first()


class Sitting(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sittings',
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='sittings',
    )
    question_order = models.TextField(
        verbose_name='Question Order',
        help_text='JSON list of question PKs in display order.',
    )
    question_list = models.TextField(
        verbose_name='Question List',
        help_text='JSON list of dicts with pk and type.',
    )
    incorrect_questions = models.TextField(
        blank=True,
        verbose_name='Incorrect Questions',
        help_text='Comma-separated PKs of incorrect answers.',
    )
    graded_essays = models.TextField(
        blank=True,
        verbose_name='Graded Essays',
        help_text='Comma-separated PKs of already marked essay questions.',
    )
    current_score = models.IntegerField(default=0)
    complete = models.BooleanField(default=False)
    user_answers = models.TextField(
        default='{}',
        verbose_name='User Answers',
        help_text='JSON dict mapping question pk to user answer.',
    )
    start = models.DateTimeField(auto_now_add=True)
    end = models.DateTimeField(null=True, blank=True)

    objects = SittingManager()

    class Meta:
        verbose_name = 'Sitting'
        verbose_name_plural = 'Sittings'
        ordering = ['-start']
        permissions = ()

    def __str__(self):
        return f"Sitting by {self.user or 'Anonymous'} on {self.quiz.title}"

    def get_question_list(self):
        """Return list of dicts: [{'pk': int, 'type': str}, ...]"""
        try:
            return json.loads(self.question_list)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_remaining_questions(self):
        """Return list of unanswered question dicts."""
        answered = set(self.get_user_answers().keys())
        return [
            q for q in self.get_question_list()
            if str(q['pk']) not in answered
        ]

    def get_current_question(self):
        """Return the next unanswered question object, or None."""
        remaining = self.get_remaining_questions()
        if not remaining:
            return None
        q_info = remaining[0]
        return self._load_question(q_info)

    def _load_question(self, q_info):
        """Load a question model instance from pk and type."""
        q_type = q_info['type']
        pk = q_info['pk']
        if q_type == 'mc':
            return MCQuestion.objects.get(pk=pk)
        elif q_type == 'tf':
            return TFQuestion.objects.get(pk=pk)
        elif q_type == 'essay':
            return EssayQuestion.objects.get(pk=pk)
        return None

    def get_all_questions(self):
        """Return all question objects in order."""
        return [
            self._load_question(q_info)
            for q_info in self.get_question_list()
        ]

    def get_user_answers(self):
        """Return dict of user answers {str(pk): answer}."""
        try:
            return json.loads(self.user_answers)
        except (json.JSONDecodeError, TypeError):
            return {}

    def add_user_answer(self, question, answer):
        """Record the user's answer for a question."""
        answers = self.get_user_answers()
        answers[str(question.pk)] = answer
        self.user_answers = json.dumps(answers)
        self.save()

    def add_incorrect_question(self, question):
        """Add question PK to incorrect list."""
        if str(question.pk) not in [str(pk) for pk in self.get_incorrect_questions()]:
            if self.incorrect_questions:
                self.incorrect_questions += f',{question.pk}'
            else:
                self.incorrect_questions = str(question.pk)
            self.save()

    def remove_incorrect_question(self, question):
        """Remove question PK from incorrect list."""
        incorrect = [str(pk) for pk in self.get_incorrect_questions()]
        if str(question.pk) in incorrect:
            incorrect.remove(str(question.pk))
            self.incorrect_questions = ','.join(incorrect)
            self.save()

    def get_incorrect_questions(self):
        """Return list of PKs of incorrectly answered questions."""
        if not self.incorrect_questions:
            return []
        return [int(pk) for pk in self.incorrect_questions.split(',') if pk]

    def mark_essay_graded(self, question):
        """Add essay PK to graded list."""
        if self.graded_essays:
            if str(question.pk) not in self.get_graded_essays():
                self.graded_essays += f',{question.pk}'
        else:
            self.graded_essays = str(question.pk)
        self.save()

    def get_graded_essays(self):
        """Return list of PKs of graded essays as strings."""
        if not self.graded_essays:
            return []
        return [pk for pk in self.graded_essays.split(',') if pk]

    def add_to_score(self, points):
        self.current_score += points
        self.save()

    def remove_from_score(self, points):
        self.current_score -= points
        if self.current_score < 0:
            self.current_score = 0
        self.save()

    @property
    def get_grading_status(self):
        """Returns the grading status of the sitting (e.g. Graded, Ungraded, Partially Graded)."""
        essay_count = sum(1 for q in self.get_question_list() if q.get('type') == 'essay')
        if essay_count == 0:
            return 'Auto-Graded'
        graded_count = len(self.get_graded_essays())
        if graded_count == 0:
            return 'Ungraded'
        elif graded_count == essay_count:
            return 'Graded'
        else:
            return 'Partially Graded'

    def get_percent_correct(self):
        total = len(self.get_question_list())
        if total == 0:
            return 0
        return int(round(self.current_score / total * 100))

    def check_if_passed(self):
        if self.quiz.pass_mark == 0:
            return True
        return self.get_percent_correct() >= self.quiz.pass_mark

    def mark_quiz_complete(self):
        from django.utils import timezone
        self.complete = True
        self.end = timezone.now()
        self.save()

    def get_questions_with_answers(self):
        """Return list of dicts with question, user_answer, is_correct, correct_answer."""
        user_answers = self.get_user_answers()
        result = []
        for q_info in self.get_question_list():
            question = self._load_question(q_info)
            if not question:
                continue
            q_pk = str(q_info['pk'])
            user_answer = user_answers.get(q_pk, '')
            is_correct = None
            correct_answer = question.get_correct_answer()

            if question.question_type == 'essay':
                is_correct = None  # manually graded
            elif user_answer:
                is_correct = question.check_if_correct(user_answer)

            result.append({
                'question': question,
                'user_answer': user_answer,
                'is_correct': is_correct,
                'correct_answer': correct_answer,
            })
        return result

    def get_question_number(self):
        """Return 1-based index of the current question."""
        total = len(self.get_question_list())
        remaining = len(self.get_remaining_questions())
        return total - remaining + 1

    def get_total_questions(self):
        return len(self.get_question_list())
