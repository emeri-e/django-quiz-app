# CloudtechConnects CBT App 📝

A modern, robust, and user-friendly Computer Based Test (CBT) application built with Django. This platform provides a comprehensive solution for conducting assessments, tracking student progress, and managing exam content with ease.

---

## ✨ Key Features

### 🎓 For Students

- **Featured Test Portal**: A focused, distraction-free landing page designed for primary assessments.
- **Timed Exams**: Automatic submission when the time limit is reached.
- **Single Attempt Enforcement**: Prevents multiple attempts on sensitive exams.
- **Instant/Delayed Results**: Choice to show scores immediately or hide them for later release.
- **Personal Dashboard**: View exam history, scores, and performance trends.

### 🛠️ For Administrators (Frontend Management)

- **Frontend Quiz Builder**: Create and edit quizzes directly from the site UI.
- **Contextual Bulk Upload**: Upload hundreds of questions via CSV specifically for any quiz.
- **Multi-Type Question Support**:
  - **Multiple Choice (MC)**: Support for custom answer options.
  - **True / False (TF)**: Simplified binary questions.
  - **Essay**: Text-based answers that require manual grading.
- **Manual Marking System**: Dedicated interface for staff to grade and provide feedback on essay answers.
- **Quick-Toggle Featured Test**: Easily designate a "primary" test that students see upon login.

---

## 🎨 Branding & UX

- **Branding**: Fully branded as **CloudtechConnects CBT app**.
- **Modern UI**: Clean, responsive design optimized for desktop and mobile browsers.
- **Visual Feedback**: Real-time timers, completion badges, and score progress bars.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Django 6.0.3+

### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd django-quiz-app
   ```

2. **Set up a Virtual Environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database**:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create an Admin User**:

   ```bash
   python manage.py createsuperuser
   ```

6. **(Optional) Seed Test Data**:

   ```bash
   python manage.py populate_test_data
   ```

7. **Run the server**:
   ```bash
   python manage.py runserver
   ```

---

## 📁 Project Structure

- `apps/accounts`: User authentication, profiles, and registration.
- `apps/quiz`: Core logic for quizzes, questions, sittings, and marking.
- `config/`: Project settings and URL routing.
- `static/`: Global CSS, JavaScript, and branding assets (Logo/Favicon).
- `templates/`: HTML structures including focused admin management templates.

---

## 🤝 Contributing

We welcome contributions! If you'd like to improve the CloudtechConnects CBT app:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

Developed with ❤️ by the **CloudtechConnects Team**.
