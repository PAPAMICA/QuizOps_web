from flask import Blueprint, render_template, current_app, g, request
from flask_login import current_user, login_required
from sqlalchemy import func, desc, text, case
from app.models import User, QuizResult
from app import db
import os
import yaml
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

def load_categories():
    quiz_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'QuizOps_quiz')
    categories = []
    total_quizzes = 0

    for category in os.listdir(quiz_dir):
        category_path = os.path.join(quiz_dir, category)
        if not os.path.isdir(category_path):
            continue

        config_path = os.path.join(category_path, 'config.yml')
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Count quiz files in the category directory
            quiz_files = [f for f in os.listdir(category_path)
                        if f.endswith(('.yml', '.yaml')) and f != 'config.yml']
            total_quizzes += len(quiz_files)

            categories.append((category, config))

    return categories, total_quizzes

@bp.route('/')
def index():
    stats = {}
    if current_user.is_authenticated:
        total_quizzes = QuizResult.query.filter_by(user_id=current_user.id).count()
        if total_quizzes > 0:
            avg_score = QuizResult.query.filter_by(user_id=current_user.id).with_entities(
                QuizResult.score, QuizResult.max_score
            ).all()
            total_score = sum(score for score, _ in avg_score)
            total_possible = sum(max_score for _, max_score in avg_score)
            avg_percentage = (total_score / total_possible * 100) if total_possible > 0 else 0

            stats = {
                'total_quizzes': total_quizzes,
                'avg_percentage': round(avg_percentage, 1)
            }

    categories, total_quizzes = load_categories()
    return render_template('main/index.html', stats=stats, categories=categories, total_quizzes=total_quizzes)

@bp.route('/profile/<username>')
def profile(username):
    """Affiche le profil d'un utilisateur"""
    user = User.query.filter_by(username=username).first_or_404()

    # Récupérer l'historique complet des quiz
    history = QuizResult.query.filter_by(user_id=user.id).order_by(QuizResult.completed_at.desc()).all()

    # Récupérer les configurations des catégories
    categories = {}
    for category, config in load_categories()[0]:
        categories[category] = config

    # Statistiques globales
    total_quizzes = len(history)
    total_score = sum(result.percentage for result in history) if history else 0
    avg_score = round(total_score / total_quizzes, 1) if total_quizzes > 0 else 0.0
    perfect_scores = sum(1 for result in history if result.percentage >= 100)

    # Statistiques par catégorie
    category_stats = {}
    for result in history:
        # Skip custom quizzes (those with multiple categories)
        if ',' in result.category:
            continue
            
        if result.category not in category_stats:
            category_stats[result.category] = {
                'count': 0,
                'total_score': 0,
                'best_score': 0
            }
        stats = category_stats[result.category]
        stats['count'] += 1
        stats['total_score'] += result.percentage
        stats['best_score'] = max(stats['best_score'], result.percentage)

    for cat_stats in category_stats.values():
        cat_stats['avg_score'] = round(cat_stats['total_score'] / cat_stats['count'], 1)

    # Préparer les données pour le graphique des scores
    chart_data = {
        'dates': [],
        'scores': [],
        'categories': [],
        'activity': {}
    }

    # Créer un dictionnaire pour compter les quiz par jour
    if history:
        # Définir la plage de dates (30 derniers jours)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=29)
        current_date = start_date

        # Initialiser tous les jours à 0
        while current_date <= end_date:
            chart_data['activity'][current_date.strftime('%Y-%m-%d')] = 0
            current_date += timedelta(days=1)

        # Compter les quiz pour chaque jour
        for result in history:
            quiz_date = result.completed_at.date()
            if start_date <= quiz_date <= end_date:
                date_str = quiz_date.strftime('%Y-%m-%d')
                chart_data['activity'][date_str] = chart_data['activity'].get(date_str, 0) + 1

    # Données pour le graphique des scores (20 derniers quiz)
    for result in sorted(history[-20:], key=lambda x: x.completed_at):
        chart_data['dates'].append(result.completed_at.strftime('%d/%m/%Y'))
        chart_data['scores'].append(float(result.percentage))
        chart_data['categories'].append(result.category)

    return render_template('auth/profile.html',
                         user=user,
                         history=history[-10:],  # Derniers 10 quiz
                         categories=categories,
                         category_stats=category_stats,
                         chart_data=chart_data,
                         total_quizzes=total_quizzes,
                         avg_score=avg_score,
                         perfect_scores=perfect_scores)

@bp.route('/leaderboard')
@login_required
def leaderboard():
    # Get time filter
    time_filter = request.args.get('time', 'all')
    category = request.args.get('category', 'all')
    
    # Base query
    base_query = db.session.query(
        User,
        func.count(QuizResult.id).label('total_quizzes'),
        func.avg(QuizResult.score * 100.0 / QuizResult.max_score).label('avg_score'),
        func.sum(case((QuizResult.score == QuizResult.max_score, 1), else_=0)).label('perfect_scores')
    ).join(QuizResult)

    # Apply time filter
    if time_filter != 'all':
        if time_filter == '7days':
            date_limit = datetime.utcnow() - timedelta(days=7)
        elif time_filter == '30days':
            date_limit = datetime.utcnow() - timedelta(days=30)
        base_query = base_query.filter(QuizResult.completed_at >= date_limit)

    # Apply category filter
    if category != 'all':
        base_query = base_query.filter(QuizResult.category == category)

    # Group and filter private profiles
    base_query = base_query.group_by(User).filter(User.private_profile == False)

    # Get top users by perfect scores
    perfect_scores = base_query.order_by(text('perfect_scores DESC')).limit(10).all()

    # Get most active users
    most_active = base_query.order_by(text('total_quizzes DESC')).limit(10).all()

    # Get users with best average scores (minimum 5 quizzes)
    best_average = base_query.having(func.count(QuizResult.id) >= 5).order_by(text('avg_score DESC')).limit(10).all()

    # Get categories from quiz results
    categories = db.session.query(QuizResult.category).distinct().all()
    categories = [cat[0] for cat in categories]

    return render_template('leaderboard.html',
                         perfect_scores=perfect_scores,
                         most_active=most_active,
                         best_average=best_average,
                         categories=sorted(categories),
                         selected_time=time_filter,
                         selected_category=category)