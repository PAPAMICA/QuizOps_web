from flask import Blueprint, render_template
from flask_login import current_user
from app.models.user import QuizResult
from flask_babel import gettext as _

bp = Blueprint('main', __name__)

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
    
    return render_template('main/index.html', stats=stats) 