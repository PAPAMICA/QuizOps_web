from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models.user import User, QuizResult
from app import db
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta
from flask_session import session_manager

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

    # 10 derniers utilisateurs inscrits
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin/index.html',
                         total_users=total_users,
                         total_quizzes=total_quizzes,
                         verified_users=verified_users,
                         new_users_week=new_users_week,
                         quizzes_week=quizzes_week,
                         avg_score=avg_score,
                         top_users=top_users,
                         recent_users=recent_users)

@bp.route('/users')
@login_required
@admin_required
def users():
    # Trier les utilisateurs par date d'inscription (plus récent en premier)
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@bp.route('/user/<user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    # Get current user info
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('You cannot modify your own admin status.', 'error')
    else:
        try:
            # Toggle admin status using direct SQL
            db.session.execute(
                "UPDATE \"user\" SET is_admin = NOT is_admin WHERE id = :user_id RETURNING is_admin",
                {"user_id": user_id}
            )
            db.session.commit()
            # Get the updated status
            new_status = db.session.execute(
                "SELECT is_admin FROM \"user\" WHERE id = :user_id",
                {"user_id": user_id}
            ).scalar()
            flash(f'Admin status for {user.username} has been {"granted" if new_status else "revoked"}.', 'success')
        except Exception as e:
            print(f"Error toggling admin status: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating admin status.', 'error')
    return redirect(url_for('admin.users'))

@bp.route('/user/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    # Get user info for the message
    user = User.query.get_or_404(user_id)
    if user == current_user:
        flash('You cannot delete your own account.', 'error')
    else:
        try:
            username = user.username
            # Delete quiz results first
            db.session.execute(
                "DELETE FROM quiz_result WHERE user_id = :user_id",
                {"user_id": user_id}
            )
            # Then delete the user
            db.session.execute(
                "DELETE FROM \"user\" WHERE id = :user_id",
                {"user_id": user_id}
            )
            db.session.commit()
            flash(f'User {username} has been deleted.', 'success')
        except Exception as e:
            print(f"Error deleting user: {str(e)}")
            db.session.rollback()
            flash('An error occurred while deleting the user.', 'error')
    return redirect(url_for('admin.users'))

@bp.route('/quizzes')
@login_required
@admin_required
def quizzes():
    # Récupérer le terme de recherche
    search_term = request.args.get('search', '')
    
    # Base query pour les résultats de quiz
    query = db.session.query(QuizResult, User).join(User)
    
    # Appliquer le filtre de recherche si présent
    if search_term:
        query = query.filter(User.username.ilike(f'%{search_term}%'))
    
    # Récupérer les résultats triés par date
    results = query.order_by(QuizResult.completed_at.desc()).all()
    
    return render_template('admin/quizzes.html', 
                         results=results,
                         search_term=search_term)

@bp.route('/quiz/<quiz_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_quiz(quiz_id):
    try:
        with session_manager() as db_session:
            quiz_result = db_session.query(QuizResult).get(quiz_id)
            if not quiz_result:
                flash('Quiz result not found.', 'error')
                return redirect(url_for('admin.quizzes'))
            
            db_session.delete(quiz_result)
            flash('Quiz result deleted successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting quiz result: {e}")
        flash('An error occurred while deleting the quiz result.', 'error')
    
    # Rediriger vers la page précédente avec les paramètres de recherche
    return redirect(request.referrer or url_for('admin.quizzes')) 