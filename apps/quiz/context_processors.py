from .models import Quiz

def quiz_context(request):
    featured_quiz = Quiz.objects.filter(featured=True, draft=False).first()
    return {
        'featured_quiz': featured_quiz,
        'is_student': not request.user.is_staff if request.user.is_authenticated else True
    }
