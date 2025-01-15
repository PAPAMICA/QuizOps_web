from flask import Blueprint, render_template, current_app, g
from flask_login import current_user, login_required
from sqlalchemy import func, desc
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
    # Most active users (most quizzes taken)
    most_active = db.session.query(
        User,
        func.count(QuizResult.id).label('quiz_count')
    ).join(QuizResult).filter(
        User.private_profile == False
    ).group_by(User).order_by(
        desc('quiz_count')
    ).limit(10).all()

    # Best average score
    best_average = db.session.query(
        User,
        func.avg(
            (func.cast(QuizResult.score, db.Float) / 
             func.cast(QuizResult.max_score, db.Float) * 100)
        ).label('average_score')
    ).join(QuizResult).filter(
        User.private_profile == False
    ).group_by(User).having(
        func.count(QuizResult.id) >= 5  # Minimum 5 quizzes to be ranked
    ).order_by(
        desc('average_score')
    ).limit(10).all()

    # Most perfect scores (100%)
    most_perfect = db.session.query(
        User,
        func.count(QuizResult.id).label('perfect_count')
    ).join(QuizResult).filter(
        User.private_profile == False,
        QuizResult.score == QuizResult.max_score
    ).group_by(User).order_by(
        desc('perfect_count')
    ).limit(10).all()

    # Format the data for the template
    most_active_data = [{'username': user.username, 'quiz_count': count} 
                       for user, count in most_active]
    best_average_data = [{'username': user.username, 'average_score': float(avg)} 
                        for user, avg in best_average]
    most_perfect_data = [{'username': user.username, 'perfect_count': count} 
                        for user, count in most_perfect]

    return render_template('leaderboard.html',
                         most_active=most_active_data,
                         best_average=best_average_data,
                         most_perfect=most_perfect_data)