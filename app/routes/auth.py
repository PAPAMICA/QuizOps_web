from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, QuizResult
from app import db
from urllib.parse import urlparse
from flask_babel import _
from werkzeug.security import check_password_hash
from app.forms import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        if User.query.filter_by(username=username).first():
            flash(_('Username already taken.'), 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash(_('Email already registered.'), 'error')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash(_('Congratulations, you are now registered!'), 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title=_('Register'), form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'), 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', title=_('Sign In'), form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/profile/<username>')
@login_required
def profile(username):
    """Affiche le profil d'un utilisateur"""
    user = User.query.filter_by(username=username).first_or_404()
    
    # Récupérer l'historique complet des quiz
    history = QuizResult.query.filter_by(user_id=user.id).order_by(QuizResult.completed_at.desc()).all()
    
    # Récupérer les configurations des catégories
    categories = {}
    for category, config in current_app.quiz_manager.get_categories():
        categories[category] = config
    
    # Préparer les données pour le graphique
    chart_data = {'dates': [], 'scores': []}
    for result in sorted(history, key=lambda x: x.completed_at):
        chart_data['dates'].append(result.completed_at.strftime('%d/%m/%Y'))
        chart_data['scores'].append(result.percentage)
    
    # Calculer les statistiques par catégorie
    results_by_category = {}
    for result in history:
        if result.category not in results_by_category:
            results_by_category[result.category] = {
                'attempts': 0,
                'total_score': 0,
                'best_score': 0
            }
        
        cat_stats = results_by_category[result.category]
        cat_stats['attempts'] += 1
        cat_stats['total_score'] += result.percentage
        cat_stats['best_score'] = max(cat_stats['best_score'], result.percentage)
        cat_stats['avg_score'] = cat_stats['total_score'] / cat_stats['attempts']
    
    return render_template('auth/profile.html',
                         user=user,
                         history=history,
                         categories=categories,
                         results_by_category=results_by_category,
                         chart_data=chart_data,
                         is_owner=user == current_user)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres utilisateur"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_language':
            language = request.form.get('language')
            current_user.preferred_language = language
            db.session.commit()
            flash(_('Language preference updated.'), 'success')
        
        elif action == 'update_email':
            email = request.form.get('email')
            if User.query.filter_by(email=email).first() and email != current_user.email:
                flash(_('Email already registered.'), 'error')
            else:
                current_user.email = email
                db.session.commit()
                flash(_('Email updated successfully.'), 'success')
        
        elif action == 'update_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if not current_user.check_password(current_password):
                flash(_('Current password is incorrect.'), 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash(_('Password updated successfully.'), 'success')
        
        return redirect(url_for('auth.settings'))
    
    return render_template('auth/settings.html',
                         supported_languages=['fr', 'en']) 