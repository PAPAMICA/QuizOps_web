from flask import Blueprint, render_template
from flask_login import current_user
from app.models.user import QuizResult
import os
import yaml

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