from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models.user import User, QuizResult
from app import db
from functools import wraps
from sqlalchemy import func
from datetime import datetime, timedelta
from sqlalchemy.sql import case

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
        func.coalesce(
            func.round(
                func.avg(
                    case(
                        [(QuizResult.max_score > 0, QuizResult.score * 100.0 / QuizResult.max_score)],
                        else_=0
                    )
                ),
                2
            ),
            0
        )
    ).scalar()
    
    # Top 5 des utilisateurs par nombre de quiz complétés
    top_users = db.session.query(
        User,
        func.count(QuizResult.id).label('quiz_count'),
        func.coalesce(
            func.round(
                func.avg(
                    case(
                        [(QuizResult.max_score > 0, QuizResult.score * 100.0 / QuizResult.max_score)],
                        else_=0
                    )
                ),
                2
            ),
            0
        ).label('avg_score')
    ).join(QuizResult).group_by(User).order_by(func.count(QuizResult.id).desc()).limit(5).all()

    # 10 derniers utilisateurs inscrits
    latest_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin/index.html',
                         total_users=total_users,
                         total_quizzes=total_quizzes,
                         verified_users=verified_users,
                         new_users_week=new_users_week,
                         quizzes_week=quizzes_week,
                         avg_score=avg_score,
                         top_users=top_users,
                         latest_users=latest_users)

@bp.route('/users')
@login_required
@admin_required
def users():
    # Get search query
    search = request.args.get('search', '').strip()
    
    # Base query
    query = User.query
    
    # Apply search filter if present
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    # Order by creation date (most recent first)
    query = query.order_by(User.created_at.desc())
    
    # Execute query
    users = query.all()
    
    return render_template('admin/users.html', users=users, search=search)

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

@bp.route('/quiz-results', methods=['GET'])
@login_required
@admin_required
def quiz_results():
    # Récupérer le terme de recherche
    search = request.args.get('search', '').strip()
    
    # Construire la requête de base
    query = db.session.query(
        QuizResult,
        User.username
    ).join(User)
    
    # Appliquer le filtre de recherche si présent
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    
    # Trier par date de complétion (plus récent d'abord)
    results = query.order_by(QuizResult.completed_at.desc()).all()
    
    return render_template('admin/quiz_results.html', results=results, search=search)

@bp.route('/quiz-results/delete/<int:result_id>', methods=['POST'])
@login_required
@admin_required
def delete_quiz_result(result_id):
    try:
        # Supprimer directement en base de données
        db.session.execute(
            "DELETE FROM quiz_result WHERE id = :result_id",
            {"result_id": result_id}
        )
        db.session.commit()
        flash('Quiz result deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting quiz result: {str(e)}', 'error')
    
    return redirect(url_for('admin.quiz_results', search=request.args.get('search', ''))) 