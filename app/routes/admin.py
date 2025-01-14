from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models.user import User, QuizResult
from app import db
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def index():
    # Statistiques globales
    total_users = User.query.count()
    total_quizzes = QuizResult.query.count()
    verified_users = User.query.filter_by(email_verified=True).count()
    
    # Statistiques des 7 derniers jours
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users_week = User.query.filter(User.created_at >= week_ago).count()
    quizzes_week = QuizResult.query.filter(QuizResult.completed_at >= week_ago).count()
    
    # Moyenne globale des scores
    avg_score = db.session.query(
        func.round(func.avg(QuizResult.score * 100.0 / QuizResult.max_score), 2)
    ).scalar() or 0
    
    # Top 5 des utilisateurs par nombre de quiz complétés
    top_users = db.session.query(
        User,
        func.count(QuizResult.id).label('quiz_count'),
        func.round(func.avg(QuizResult.score * 100.0 / QuizResult.max_score), 2).label('avg_score')
    ).join(QuizResult).group_by(User).order_by(func.count(QuizResult.id).desc()).limit(5).all()

    return render_template('admin/index.html',
                         total_users=total_users,
                         total_quizzes=total_quizzes,
                         verified_users=verified_users,
                         new_users_week=new_users_week,
                         quizzes_week=quizzes_week,
                         avg_score=avg_score,
                         top_users=top_users)

@bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('You cannot modify your own admin status.', 'error')
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
        flash(f'Admin status for {user.username} has been {"granted" if user.is_admin else "revoked"}.', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('You cannot delete your own account.', 'error')
    else:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'User {username} has been deleted.', 'success')
    return redirect(url_for('admin.users')) 