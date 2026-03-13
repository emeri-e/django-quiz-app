from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from apps.quiz.models import (
    Category, SubCategory, Quiz, MCQuestion, TFQuestion, EssayQuestion, Answer
)

class Command(BaseCommand):
    help = 'Populates the database with rich test data for the quiz app.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting to populate test data...")
        
        try:
            with transaction.atomic():
                self.populate_data()
            self.stdout.write(self.style.SUCCESS("Successfully populated test data!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to populate test data: {e}"))

    def populate_data(self):
        # ── Users ──────────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            self.stdout.write("Created superuser 'admin' with password 'admin'")
            
        if not User.objects.filter(username='teststudent').exists():
            User.objects.create_user('teststudent', 'student@example.com', 'student')
            self.stdout.write("Created user 'teststudent' with password 'student'")

        # ── Categories & SubCategories ─────────────────────────
        cat_science = Category.objects.create(
            name='Science',
            description='Test your knowledge of the natural world.'
        )
        SubCategory.objects.create(name='Physics', category=cat_science)
        SubCategory.objects.create(name='Biology', category=cat_science)

        cat_history = Category.objects.create(
            name='History',
            description='Learn from the past to understand the future.'
        )
        SubCategory.objects.create(name='World War II', category=cat_history)
        SubCategory.objects.create(name='Ancient Civilizations', category=cat_history)
        
        cat_general = Category.objects.create(
            name='General Knowledge',
            description='A mix of everything.'
        )

        self.stdout.write("Created categories and subcategories")

        # ── Quizzes ─────────────────────────────────────────────
        quiz_physics = Quiz.objects.create(
            title='Physics Fundamentals',
            description='A basic quiz about everyday physics.',
            category=cat_science,
            random_order=True,
            answers_at_end=True,
            pass_mark=60,
            success_text='Great job! You know your physics.',
            fail_text='You might want to review some physics basics.',
        )

        quiz_history = Quiz.objects.create(
            title='World History Mini-Exam',
            description='Test your knowledge of world history events.',
            category=cat_history,
            random_order=False,
            single_attempt=True,
            exam_paper=True,
            time_limit=2,  # 2 minute CBT exam
            pass_mark=75,
        )
        
        quiz_mixed = Quiz.objects.create(
            title='Mixed Trivia',
            description='A quick general knowledge trivia.',
            category=cat_general,
            max_questions=3, # Random subset of 3 out of however many
            answers_at_end=False,
            pass_mark=50,
        )

        self.stdout.write("Created quizzes")

        # ── MC Questions - Physics ──────────────────────────────
        mc1 = MCQuestion.objects.create(
            content='What is the primary force that keeps planets in orbit?',
            explanation='Gravity is the fundamental force of attraction between masses.',
            category=cat_science,
            answer_order='random'
        )
        mc1.quiz.add(quiz_physics)
        Answer.objects.create(question=mc1, content='Gravity', correct=True)
        Answer.objects.create(question=mc1, content='Magnetism', correct=False)
        Answer.objects.create(question=mc1, content='Strong Nuclear Force', correct=False)
        Answer.objects.create(question=mc1, content='Friction', correct=False)

        mc2 = MCQuestion.objects.create(
            content='What is the speed of light in a vacuum?',
            explanation='Light travels at approximately 299,792,458 meters per second in a vacuum.',
            category=cat_science,
            answer_order='content'
        )
        mc2.quiz.add(quiz_physics)
        Answer.objects.create(question=mc2, content='~300,000 km/s', correct=True)
        Answer.objects.create(question=mc2, content='~150,000 km/s', correct=False)
        Answer.objects.create(question=mc2, content='~1,000,000 km/s', correct=False)

        # ── MC Questions - Mixed ────────────────────────────────
        mc_mix1 = MCQuestion.objects.create(content='What is the capital of Japan?', category=cat_general)
        mc_mix1.quiz.add(quiz_mixed)
        Answer.objects.create(question=mc_mix1, content='Tokyo', correct=True)
        Answer.objects.create(question=mc_mix1, content='Kyoto', correct=False)
        Answer.objects.create(question=mc_mix1, content='Osaka', correct=False)

        mc_mix2 = MCQuestion.objects.create(content='Who painted the Mona Lisa?', category=cat_general)
        mc_mix2.quiz.add(quiz_mixed)
        Answer.objects.create(question=mc_mix2, content='Leonardo da Vinci', correct=True)
        Answer.objects.create(question=mc_mix2, content='Pablo Picasso', correct=False)
        Answer.objects.create(question=mc_mix2, content='Vincent van Gogh', correct=False)
        
        mc_mix3 = MCQuestion.objects.create(content='Which planet is known as the Red Planet?', category=cat_general)
        mc_mix3.quiz.add(quiz_mixed)
        Answer.objects.create(question=mc_mix3, content='Mars', correct=True)
        Answer.objects.create(question=mc_mix3, content='Venus', correct=False)
        Answer.objects.create(question=mc_mix3, content='Jupiter', correct=False)

        mc_mix4 = MCQuestion.objects.create(content='What is the largest ocean on Earth?', category=cat_general)
        mc_mix4.quiz.add(quiz_mixed)
        Answer.objects.create(question=mc_mix4, content='Pacific Ocean', correct=True)
        Answer.objects.create(question=mc_mix4, content='Atlantic Ocean', correct=False)
        Answer.objects.create(question=mc_mix4, content='Indian Ocean', correct=False)

        self.stdout.write("Created Multiple Choice questions")

        # ── TF Questions ────────────────────────────────────────
        tf1 = TFQuestion.objects.create(
            content='Water boils at 100 degrees Celsius at sea level.',
            explanation='This is the standard boiling point of water.',
            category=cat_science,
            correct=True
        )
        tf1.quiz.add(quiz_physics)

        tf2 = TFQuestion.objects.create(
            content='The Great Wall of China is visible from the Moon with the naked eye.',
            explanation='This is a common myth. It is generally not visible without magnification.',
            category=cat_history,
            correct=False
        )
        tf2.quiz.add(quiz_history)

        tf3 = TFQuestion.objects.create(
            content='Julius Caesar was the first Roman Emperor.',
            explanation='Augustus was the first Roman Emperor. Caesar was a dictator.',
            category=cat_history,
            correct=False
        )
        tf3.quiz.add(quiz_history)

        self.stdout.write("Created True/False questions")

        # ── Essay Questions ─────────────────────────────────────
        eq1 = EssayQuestion.objects.create(
            content='Explain the main causes of World War I.',
            explanation='Key concepts to cover: Militarism, Alliances, Imperialism, Nationalism (MAIN), and the assassination of Archduke Franz Ferdinand.',
            category=cat_history,
        )
        eq1.quiz.add(quiz_history)
        
        eq2 = EssayQuestion.objects.create(
            content='Describe the impact of the Industrial Revolution on urban society.',
            category=cat_history,
        )
        eq2.quiz.add(quiz_history)

        self.stdout.write("Created Essay questions")
