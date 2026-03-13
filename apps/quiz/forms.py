from django import forms

from .models import MCQuestion, TFQuestion, EssayQuestion, Answer


class QuestionForm(forms.Form):
    """Dynamic form for MC and TF questions."""

    def __init__(self, question, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question

        if question.question_type == 'mc':
            answers = question.get_answers_list()
            choices = [(str(a.pk), a.content) for a in answers]
            self.fields['answer'] = forms.ChoiceField(
                choices=choices,
                widget=forms.RadioSelect,
                label='',
            )
        elif question.question_type == 'tf':
            self.fields['answer'] = forms.ChoiceField(
                choices=[('True', 'True'), ('False', 'False')],
                widget=forms.RadioSelect,
                label='',
            )


class EssayForm(forms.Form):
    """Form for essay questions."""
    answer = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Write your answer here...',
        }),
        label='',
    )


class MarkingForm(forms.Form):
    """Form for grading essay answers."""
    MARK_CHOICES = (
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
    )
    mark = forms.ChoiceField(
        choices=MARK_CHOICES,
        widget=forms.RadioSelect,
        label='Mark as:',
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional feedback...',
        }),
        required=False,
        label='Feedback',
    )


class BulkUploadForm(forms.Form):
    """Form to upload a CSV of multiple choice questions."""
    file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with columns: Quiz_Slug, Category_Name, Question_Content, Correct_Answer, Wrong_Answer_1, Wrong_Answer_2, Wrong_Answer_3, Explanation'
    )

# ── Admin Frontend Management Forms ─────────────────────────────────

from .models import Quiz, Category

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'url', 'category', 'random_order', 
            'max_questions', 'answers_at_end', 'exam_paper', 'single_attempt', 
            'pass_mark', 'success_text', 'fail_text', 'draft', 'hide_results',
            'featured'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'success_text': forms.Textarea(attrs={'rows': 2}),
            'fail_text': forms.Textarea(attrs={'rows': 2}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = 'form-control'


class BaseQuestionForm(forms.ModelForm):
    class Meta:
        fields = ['content', 'explanation', 'figure', 'category', 'sub_category']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
            'explanation': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect, forms.FileInput)):
                field.widget.attrs['class'] = 'form-control'


class MCQuestionForm(BaseQuestionForm):
    class Meta(BaseQuestionForm.Meta):
        model = MCQuestion
        fields = BaseQuestionForm.Meta.fields + ['answer_order']


class TFQuestionForm(BaseQuestionForm):
    class Meta(BaseQuestionForm.Meta):
        model = TFQuestion
        fields = BaseQuestionForm.Meta.fields + ['correct']


class EssayQuestionForm(BaseQuestionForm):
    class Meta(BaseQuestionForm.Meta):
        model = EssayQuestion


from django.forms import inlineformset_factory

MCAnswerFormSet = inlineformset_factory(
    MCQuestion, 
    Answer, 
    fields=['content', 'correct'],
    extra=4,
    can_delete=True,
    widgets={
        'content': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Answer text...'}),
        'correct': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
