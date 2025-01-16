from flask import Blueprint, render_template, current_app, jsonify, request, redirect, url_for, session, g, flash
from flask_login import login_required, current_user
from app.models import QuizResult, Quiz
from app import db
import random
from functools import wraps
from sqlalchemy.exc import OperationalError
import time
import uuid
from datetime import datetime
from app.utils.db_utils import session_manager

bp = Blueprint('quiz', __name__)

def set_locale(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'locale'):
            g.locale = request.accept_languages.best_match(['fr', 'en']) or 'fr'
        return f(*args, **kwargs)
    return decorated_function

def retry_on_db_lock(max_retries=3, delay=0.1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                        continue
                    raise
            return f(*args, **kwargs)
        return wrapper
    return decorator

@bp.route('/quizzes')
@set_locale
def list_quizzes():
    """List all available quizzes"""
    categories = current_app.quiz_manager.get_categories()
    quizzes_by_category = {}

    # Create a dictionary of quizzes by category
    for category, config in categories:
        quizzes_by_category[category] = current_app.quiz_manager.get_quizzes_by_category(category)

    # Get best scores for each quiz only if user is logged in
    best_scores = {}
    if current_user.is_authenticated:
        for category in quizzes_by_category:
            for quiz in quizzes_by_category[category]:
                # Query the best score using QuizResult
                best_score = QuizResult.query.filter_by(
                    user_id=current_user.id,
                    quiz_id=quiz['id']
                ).order_by(QuizResult.score.desc()).first()
                if best_score:
                    best_scores[quiz['id']] = best_score.percentage

    return render_template('quiz/list.html',
                         categories=categories,
                         quizzes_by_category=quizzes_by_category,
                         best_scores=best_scores)

@bp.route('/quiz/<quiz_id>')
@login_required
@set_locale
def show_quiz(quiz_id):
    """Affiche un quiz spécifique"""
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        return render_template('404.html'), 404

    return render_template('quiz/show.html', quiz=quiz)

@bp.route('/quiz/<quiz_id>/start', methods=['GET', 'POST'])
@login_required
@set_locale
def start_quiz(quiz_id):
    """Démarre un quiz"""
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    # Initialize the session
    session['current_quiz'] = quiz_id
    session['current_question'] = 0
    session['answers'] = {}

    # Shuffle questions
    questions = quiz['questions'].copy()
    random.shuffle(questions)

    # Save questions order using their IDs
    session['questions_order'] = [q['id'] for q in questions]

    # Shuffle options for each question
    session['shuffled_options'] = {}
    for i, question in enumerate(questions, 1):
        original_indices = list(range(len(question['options'])))
        shuffled_indices = original_indices.copy()
        random.shuffle(shuffled_indices)

        original_to_shuffled = {str(old_idx): str(new_idx) for new_idx, old_idx in enumerate(shuffled_indices)}
        shuffled_to_original = {str(new_idx): str(old_idx) for new_idx, old_idx in enumerate(shuffled_indices)}

        session['shuffled_options'][str(i)] = {
            'shuffled_to_original': shuffled_to_original,
            'original_to_shuffled': original_to_shuffled
        }

    return redirect(url_for('quiz.show_question', quiz_id=quiz_id, question_number=1))

@bp.route('/quiz/<quiz_id>/question/<int:question_number>')
@login_required
@set_locale
def show_question(quiz_id, question_number):
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    # Get categories configurations
    categories = dict(current_app.quiz_manager.get_categories())

    # Get the current question
    questions_order = session.get('questions_order', [])
    if not questions_order or question_number > len(questions_order):
        flash('Invalid question number.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    # Find the question with the corresponding ID
    question_id = questions_order[question_number - 1]
    question = None
    for q in quiz['questions']:
        if str(q.get('id')) == str(question_id):
            question = q
            break

    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    total_questions = len(questions_order)

    # Get shuffled options
    shuffled_options = []
    if str(question_number - 1) in session.get('shuffled_options', {}):
        original_to_shuffled = session['shuffled_options'][str(question_number - 1)]['original_to_shuffled']
        for i in range(len(question['options'])):
            shuffled_options.append(question['options'][int(original_to_shuffled[str(i)])])
    else:
        shuffled_options = question['options']

    question['options'] = shuffled_options

    return render_template('quiz/question.html',
                         quiz=quiz,
                         question=question,
                         question_number=question_number,
                         total_questions=total_questions,
                         categories=categories,
                         is_demo=False)

@bp.route('/quiz/<quiz_id>/question/<int:question_number>/answer', methods=['POST'])
@login_required
@set_locale
def answer_question(quiz_id, question_number):
    """Traite la réponse à une question"""
    if session.get('current_quiz') != quiz_id:
        return redirect(url_for('quiz.show_quiz', quiz_id=quiz_id))

    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    questions_order = session.get('questions_order', [])
    if not questions_order or question_number > len(questions_order):
        flash('Invalid question number.', 'error')
        return redirect(url_for('quiz.list_quizzes'))

    # Récupérer la réponse
    answer = request.form.get('answer')
    if answer is not None:
        answer = int(answer)
        # Convertir la réponse mélangée en réponse originale
        mappings = session['shuffled_options'][str(question_number)]
        original_answer = int(mappings['shuffled_to_original'][str(answer)])

        # S'assurer que answers est initialisé dans la session
        if 'answers' not in session:
            session['answers'] = {}

        # Créer une copie modifiable du dictionnaire answers et stocker la réponse mélangée
        answers = dict(session['answers'])
        answers[str(question_number)] = answer  # Stocker la réponse mélangée
        session['answers'] = answers

    # Rediriger vers la question suivante si ce n'est pas la dernière
    if question_number < len(questions_order):
        return redirect(url_for('quiz.show_question',
                              quiz_id=quiz_id,
                              question_number=question_number + 1))
    else:
        return redirect(url_for('quiz.show_results', quiz_id=quiz_id))

@bp.route('/quiz/<quiz_id>/results')
@login_required
@set_locale
@retry_on_db_lock()
def show_results(quiz_id):
    """Affiche les résultats du quiz"""
    from flask import session as flask_session

    if flask_session.get('current_quiz') != quiz_id:
        return redirect(url_for('quiz.show_quiz', quiz_id=quiz_id))

    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        return render_template('404.html'), 404

    answers = flask_session.get('answers', {})
    if not answers:
        return redirect(url_for('quiz.show_quiz', quiz_id=quiz_id))

    # Récupérer les questions dans l'ordre où elles ont été présentées
    questions = flask_session.get('questions', [])

    # Calculer le score
    correct_answers = 0
    total_questions = len(questions)

    # Préparer les questions avec leurs réponses pour l'affichage
    questions_with_answers = []
    answers_data = {}  # Pour stocker les réponses dans la base de données

    for i, question in enumerate(questions, 1):
        q = question.copy()
        mappings = session['shuffled_options'][str(i)]

        # Réorganiser les options dans l'ordre d'affichage original
        options = [''] * len(question['options'])

        for new_idx_str, old_idx_str in mappings['shuffled_to_original'].items():
            new_idx = int(new_idx_str)
            old_idx = int(old_idx_str)
            options[new_idx] = question['options'][old_idx]
        q['options'] = options

        # Récupérer la réponse de l'utilisateur (déjà dans l'ordre mélangé)
        user_answer = answers.get(str(i))

        # Vérifier si la réponse est correcte en utilisant les indices originaux
        is_correct = False
        if user_answer is not None:
            original_user_answer = int(mappings['shuffled_to_original'][str(user_answer)])
            is_correct = original_user_answer == question['correct_answer']
            if is_correct:
                correct_answers += 1

            # Stocker la réponse pour la base de données
            answers_data[question['id']] = {
                'user_answer': original_user_answer,
                'correct_answer': question['correct_answer'],
                'is_correct': is_correct
            }

        # Convertir la réponse correcte pour l'affichage
        q['correct_answer'] = int(mappings['original_to_shuffled'][str(question['correct_answer'])])

        # Ajouter la source si elle existe
        if 'source' in question:
            q['source'] = question['source']

        questions_with_answers.append({
            'question': q,
            'user_answer': user_answer,  # Déjà dans l'ordre mélangé
            'is_correct': is_correct
        })

    # Calculate score percentage, handling the case when total_questions is 0
    score_percentage = round((correct_answers / total_questions) * 100) if total_questions > 0 else 0

    try:
        with session_manager() as db_session:
            quiz_result = QuizResult(
                user_id=current_user.id,
                quiz_id=quiz_id,
                category=quiz.get('category', ''),
                level=quiz.get('level', ''),
                score=correct_answers,
                max_score=total_questions,
                answers=answers_data,
                time_spent=0,
                quiz_title=quiz.get('title', quiz_id) if not quiz_id.startswith('custom_') else f"Custom Quiz - {quiz.get('category', '')} ({quiz.get('level', '')})"
            )
            db_session.add(quiz_result)
    except Exception as e:
        current_app.logger.error(f"Error saving quiz result: {e}")
        raise

    # Nettoyer la session Flask
    flask_session.pop('current_quiz', None)
    flask_session.pop('current_question', None)
    flask_session.pop('shuffled_options', None)
    flask_session.pop('answers', None)
    flask_session.pop('questions', None)
    flask_session.pop('questions_order', None)

    return render_template('quiz/results.html',
                         quiz=quiz,
                         questions=questions_with_answers,
                         correct_answers=correct_answers,
                         total_questions=total_questions,
                         score_percentage=score_percentage)

@bp.route('/api/quiz/<quiz_id>')
@login_required
@set_locale
def get_quiz_data(quiz_id):
    """API endpoint pour récupérer les données d'un quiz"""
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404

    return jsonify(quiz)

@bp.route('/quiz/<quiz_id>/history')
@login_required
@set_locale
def show_history(quiz_id):
    """Affiche l'historique des tentatives d'un quiz"""
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        return render_template('404.html'), 404

    # Récupérer l'historique des tentatives
    history = QuizResult.query.filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id
    ).order_by(QuizResult.completed_at.desc()).all()

    # Récupérer le meilleur score
    best_score = 0
    if history:
        best_score = max(attempt.percentage for attempt in history)

    return render_template('quiz/history.html',
                         quiz=quiz,
                         history=history,
                         best_score=best_score)

@bp.route('/custom', methods=['GET'])
def custom_quiz():
    categories = dict(current_app.quiz_manager.get_categories())
    return render_template('quiz/custom.html', categories=categories)

@bp.route('/custom/create', methods=['POST'])
@login_required
def create_custom_quiz():
    technologies = request.form.getlist('technologies[]')
    level = request.form.get('level')

    if not technologies:
        flash('Please select at least one technology.', 'error')
        return redirect(url_for('quiz.custom_quiz'))

    if not level:
        flash('Please select a difficulty level.', 'error')
        return redirect(url_for('quiz.custom_quiz'))

    # Créer le quiz personnalisé
    quiz_manager = current_app.quiz_manager
    custom_quiz = quiz_manager.create_custom_quiz(technologies, level)

    if not custom_quiz:
        flash('Not enough questions available for the selected criteria. Please try different options.', 'error')
        return redirect(url_for('quiz.custom_quiz'))

    # Mettre à jour la catégorie pour inclure toutes les technologies
    custom_quiz['category'] = ','.join(technologies)

    # Stocker uniquement l'ID du quiz dans la session
    session['current_quiz'] = custom_quiz['id']
    session['start_time'] = datetime.utcnow().timestamp()

    # Démarrer directement le quiz sans redirection vers start_quiz
    session['current_question'] = 0
    session['answers'] = {}

    # Mélanger l'ordre des questions
    questions = custom_quiz['questions'].copy()
    random.shuffle(questions)

    # Sauvegarder l'ordre des questions
    session['questions_order'] = [q['id'] for q in questions]
    session['questions'] = questions

    # Mélanger l'ordre des options pour chaque question
    session['shuffled_options'] = {}
    for i, question in enumerate(questions, 1):
        original_indices = list(range(len(question['options'])))
        shuffled_indices = original_indices.copy()
        random.shuffle(shuffled_indices)

        original_to_shuffled = {str(old_idx): str(new_idx) for new_idx, old_idx in enumerate(shuffled_indices)}
        shuffled_to_original = {str(new_idx): str(old_idx) for new_idx, old_idx in enumerate(shuffled_indices)}

        session['shuffled_options'][str(i)] = {
            'shuffled_to_original': shuffled_to_original,
            'original_to_shuffled': original_to_shuffled
        }

    return redirect(url_for('quiz.show_question', quiz_id=custom_quiz['id'], question_number=1))

@bp.route('/demo')
@set_locale
def demo_quiz():
    """Start a demo quiz without login"""
    # List of available demo quizzes
    demo_categories = ['ansible', 'docker', 'git', 'aws']
    demo_quizzes = []
    
    # Get all intermediate quizzes from the selected categories
    for category in demo_categories:
        quizzes = current_app.quiz_manager.get_quizzes_by_category(category)
        for quiz in quizzes:
            if quiz['level'].lower() == 'intermediate':
                demo_quizzes.append(quiz)
    
    if not demo_quizzes:
        flash('No demo quizzes available at the moment.', 'error')
        return redirect(url_for('main.index'))
    
    # Select a random quiz
    quiz = random.choice(demo_quizzes)
    quiz_id = quiz['id']
    
    # Initialize the session
    session['current_quiz'] = quiz_id
    session['current_question'] = 0
    session['answers'] = {}
    session['is_demo'] = True
    
    # Shuffle questions
    questions = quiz['questions'].copy()
    random.shuffle(questions)
    
    # Save questions order
    session['questions_order'] = [q['id'] for q in questions]
    
    # Shuffle options for each question
    session['shuffled_options'] = {}
    for i, question in enumerate(questions, 1):
        original_indices = list(range(len(question['options'])))
        shuffled_indices = original_indices.copy()
        random.shuffle(shuffled_indices)
        
        original_to_shuffled = {str(old_idx): str(new_idx) for new_idx, old_idx in enumerate(shuffled_indices)}
        shuffled_to_original = {str(new_idx): str(old_idx) for new_idx, old_idx in enumerate(shuffled_indices)}
        
        session['shuffled_options'][str(i)] = {
            'shuffled_to_original': shuffled_to_original,
            'original_to_shuffled': original_to_shuffled
        }
    
    # Save shuffled questions
    session['questions'] = questions
    
    return redirect(url_for('quiz.show_demo_question', quiz_id=quiz_id, question_number=1))

@bp.route('/demo/<quiz_id>/question/<int:question_number>')
@set_locale
def show_demo_question(quiz_id, question_number):
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        flash('Quiz not found.', 'error')
        return redirect(url_for('main.index'))

    # Get categories configurations
    categories = dict(current_app.quiz_manager.get_categories())

    # Get the current question
    questions_order = session.get('questions_order', [])
    if not questions_order or question_number > len(questions_order):
        flash('Invalid question number.', 'error')
        return redirect(url_for('main.index'))

    # Find the question with the corresponding ID
    question_id = questions_order[question_number - 1]
    question = None
    for q in quiz['questions']:
        if str(q.get('id')) == str(question_id):
            question = q
            break

    if not question:
        flash('Question not found.', 'error')
        return redirect(url_for('main.index'))

    total_questions = len(questions_order)

    # Get shuffled options
    shuffled_options = []
    if str(question_number - 1) in session.get('shuffled_options', {}):
        original_to_shuffled = session['shuffled_options'][str(question_number - 1)]['original_to_shuffled']
        for i in range(len(question['options'])):
            shuffled_options.append(question['options'][int(original_to_shuffled[str(i)])])
    else:
        shuffled_options = question['options']

    question['options'] = shuffled_options

    return render_template('quiz/question.html',
                         quiz=quiz,
                         question=question,
                         question_number=question_number,
                         total_questions=total_questions,
                         categories=categories,
                         is_demo=True)

@bp.route('/demo/<quiz_id>/question/<int:question_number>/answer', methods=['POST'])
@set_locale
def answer_demo_question(quiz_id, question_number):
    """Handle answer for demo quiz"""
    if session.get('current_quiz') != quiz_id or not session.get('is_demo'):
        return redirect(url_for('quiz.demo_quiz'))
    
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz or question_number < 1 or question_number > len(quiz['questions']):
        return render_template('404.html'), 404
    
    # Get answer
    answer = request.form.get('answer')
    if answer is not None:
        answer = int(answer)
        mappings = session['shuffled_options'][str(question_number)]
        original_answer = int(mappings['shuffled_to_original'][str(answer)])
        
        if 'answers' not in session:
            session['answers'] = {}
        
        answers = dict(session['answers'])
        answers[str(question_number)] = answer
        session['answers'] = answers
    
    if question_number < len(quiz['questions']):
        return redirect(url_for('quiz.show_demo_question',
                              quiz_id=quiz_id,
                              question_number=question_number + 1))
    else:
        return redirect(url_for('quiz.show_demo_results', quiz_id=quiz_id))

@bp.route('/demo/<quiz_id>/results')
@set_locale
def show_demo_results(quiz_id):
    """Show results for demo quiz"""
    if session.get('current_quiz') != quiz_id or not session.get('is_demo'):
        return redirect(url_for('quiz.demo_quiz'))
    
    quiz = current_app.quiz_manager.get_quiz(quiz_id)
    if not quiz:
        return render_template('404.html'), 404
    
    answers = session.get('answers', {})
    if not answers:
        return redirect(url_for('quiz.demo_quiz'))
    
    questions = session.get('questions', [])
    
    correct_answers = 0
    total_questions = len(questions)
    questions_with_answers = []
    
    for i, question in enumerate(questions, 1):
        q = question.copy()
        mappings = session['shuffled_options'][str(i)]
        
        options = [''] * len(question['options'])
        for new_idx_str, old_idx_str in mappings['shuffled_to_original'].items():
            new_idx = int(new_idx_str)
            old_idx = int(old_idx_str)
            options[new_idx] = question['options'][old_idx]
        
        q['options'] = options
        user_answer = answers.get(str(i))
        
        is_correct = False
        if user_answer is not None:
            original_user_answer = int(mappings['shuffled_to_original'][str(user_answer)])
            is_correct = original_user_answer == question['correct_answer']
            if is_correct:
                correct_answers += 1
        
        questions_with_answers.append({
            'question': q,
            'user_answer': user_answer,
            'is_correct': is_correct
        })
    
    score_percentage = round((correct_answers / total_questions) * 100)
    
    # Clear demo session
    session.pop('is_demo', None)
    session.pop('current_quiz', None)
    session.pop('questions', None)
    session.pop('answers', None)
    session.pop('shuffled_options', None)
    
    return render_template('quiz/results.html',
                         quiz=quiz,
                         questions=questions_with_answers,
                         score_percentage=score_percentage,
                         correct_answers=correct_answers,
                         total_questions=total_questions,
                         is_demo=True)