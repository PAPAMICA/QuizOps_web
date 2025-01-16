from flask import Blueprint, render_template, current_app, g, request, flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, desc, text, case, cast, Float
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
    user = User.query.filter_by(username=username).first_or_404()

    # If profile is private and current user is not the owner, show private message
    if user.private_profile and (not current_user.is_authenticated or current_user.id != user.id):
        flash('This profile is private.', 'error')
        return redirect(url_for('main.index'))

    # Get quiz results for the user (excluding custom quizzes)
    quiz_results = (QuizResult.query
                   .filter_by(user_id=user.id)
                   .filter(~QuizResult.category.like('custom%'))  # Exclude custom quizzes
                   .order_by(QuizResult.completed_at.desc())
                   .all())

    # Calculate statistics
    total_quizzes = len(quiz_results)
    perfect_scores = sum(1 for result in quiz_results if result.percentage == 100)
    avg_score = sum(result.percentage for result in quiz_results) / total_quizzes if total_quizzes > 0 else 0

    # Get time range for activity graph
    time_range = request.args.get('time_range', '30days')
    if time_range == '365days':
        start_date = datetime.utcnow() - timedelta(days=365)
        group_by = 'month'
    else:  # 30days
        start_date = datetime.utcnow() - timedelta(days=30)
        group_by = 'day'

    # Prepare chart data
    chart_data = {
        'dates': [],
        'scores': [],
        'categories': [],
        'activity': {}
    }

    # Initialize activity data
    current_date = start_date
    end_date = datetime.utcnow()

    if group_by == 'day':
        while current_date <= end_date:
            chart_data['activity'][current_date.strftime('%Y-%m-%d')] = 0
            current_date += timedelta(days=1)
    else:  # month
        while current_date <= end_date:
            chart_data['activity'][current_date.strftime('%Y-%m')] = 0
            # Add one month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

    # Get the last 20 quiz results for the score chart
    recent_results = sorted(quiz_results[:20], key=lambda x: x.completed_at)
    for result in recent_results:
        chart_data['dates'].append(result.completed_at.strftime('%d/%m/%Y'))
        chart_data['scores'].append(float(result.percentage))
        chart_data['categories'].append(result.category)

    # Fill activity data
    for result in quiz_results:
        if result.completed_at >= start_date:
            if group_by == 'day':
                date_key = result.completed_at.strftime('%Y-%m-%d')
            else:
                date_key = result.completed_at.strftime('%Y-%m')
            chart_data['activity'][date_key] = chart_data['activity'].get(date_key, 0) + 1

    # Load categories from quiz directory
    quiz_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'QuizOps_quiz')
    categories = {}
    for category in os.listdir(quiz_dir):
        category_path = os.path.join(quiz_dir, category)
        if not os.path.isdir(category_path) or category.startswith('custom'):
            continue

        config_path = os.path.join(category_path, 'config.yml')
        if os.path.isfile(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
                categories[category] = {
                    'name': config.get('name', category.replace('_', ' ').title()),
                    'description': config.get('description', ''),
                    'logo': config.get('logo', ''),
                    'color': config.get('color', 'gray')
                }

    # Calculate category statistics
    category_stats = {}
    for result in quiz_results:
        # Skip custom quizzes for category stats
        if ',' in result.category or result.category.startswith('custom'):
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

    return render_template('auth/profile.html',
                         user=user,
                         history=quiz_results[:10],  # Derniers 10 quiz
                         categories=categories,
                         category_stats=category_stats,
                         chart_data=chart_data,
                         total_quizzes=total_quizzes,
                         avg_score=avg_score,
                         perfect_scores=perfect_scores,
                         time_range=time_range,
                         group_by=group_by)

@bp.route('/leaderboard')
def leaderboard():
    # Get time filter
    time_filter = request.args.get('time', 'all')
    category = request.args.get('category', 'all')
    
    # Base query for user statistics
    base_query = db.session.query(
        User,
        func.count(QuizResult.id).label('total_quizzes'),
        (func.sum(QuizResult.score * 100.0) / func.sum(QuizResult.max_score)).label('avg_score'),
        func.sum(case((QuizResult.score == QuizResult.max_score, 1), else_=0)).label('perfect_scores')
    ).join(QuizResult).filter(~QuizResult.category.like('custom%'))  # Exclude custom quizzes

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

    # Group by user and filter out private profiles
    base_query = base_query.group_by(User).filter(User.private_profile == False)

    # Get top users by perfect scores
    perfect_scores = base_query.order_by(text('perfect_scores DESC')).limit(10).all()

    # Get most active users
    most_active = base_query.order_by(text('total_quizzes DESC')).limit(10).all()

    # Get users with best average scores (minimum 5 quizzes)
    best_average = base_query.having(func.count(QuizResult.id) >= 5).order_by(text('avg_score DESC')).limit(10).all()

    # Get unique categories from quiz results, excluding custom quizzes
    categories = db.session.query(QuizResult.category).filter(
        ~QuizResult.category.like('custom%')
    ).distinct().all()
    categories = sorted([cat[0] for cat in categories])

    return render_template('leaderboard.html',
                         perfect_scores=perfect_scores,
                         most_active=most_active,
                         best_average=best_average,
                         categories=categories,
                         selected_time=time_filter,
                         selected_category=category)