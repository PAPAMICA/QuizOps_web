from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, QuizResult
from app import db, mail
from urllib.parse import urlparse
from werkzeug.security import check_password_hash
from app.forms import LoginForm, RegistrationForm
from flask_mail import Message

bp = Blueprint('auth', __name__)

def send_verification_email(user):
    try:
        verification_code = user.generate_verification_code()
        print("\n==== EMAIL CONFIGURATION ====")
        print(f"Generated code: {verification_code}")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print("\nMail Server Settings:")
        print(f"Server: {current_app.config.get('MAIL_SERVER')}")
        print(f"Port: {current_app.config.get('MAIL_PORT')}")
        print(f"Username: {current_app.config.get('MAIL_USERNAME')}")
        print(f"Use TLS: {current_app.config.get('MAIL_USE_TLS')}")
        print(f"Default Sender: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
        print("==========================\n")
        
        msg = Message('QuizOps - Verify Your Email',
                     sender=current_app.config['MAIL_DEFAULT_SENDER'],
                     recipients=[user.email])
        
        msg.body = f'''Hi {user.username},

Thank you for registering with QuizOps! To verify your email address, please use the following code:

{verification_code}

If you did not register for QuizOps, please ignore this email.

Best regards,
The QuizOps Team'''

        msg.html = f'''
<p>Hi {user.username},</p>

<p>Thank you for registering with QuizOps! To verify your email address, please use the following code:</p>

<h2 style="font-size: 24px; color: #4F46E5; text-align: center; padding: 10px; background-color: #F3F4F6; border-radius: 4px;">{verification_code}</h2>

<p>If you did not register for QuizOps, please ignore this email.</p>

<p>Best regards,<br>
The QuizOps Team</p>'''

        print("Attempting to send email...")
        mail.send(msg)
        print("Email sent successfully!")
        return True
    except Exception as e:
        print("\n==== EMAIL ERROR ====")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("====================\n")
        return False

@bp.route('/register', methods=['GET', 'POST'])
def register():
    print("\n==== REGISTER ROUTE ====")
    print(f"Method: {request.method}")
    
    if current_user.is_authenticated:
        print("User already authenticated, redirecting to index")
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    print(f"Form data: {request.form}")
    
    if request.method == 'POST':
        print("\nForm validation:")
        print(f"CSRF Token valid: {form.csrf_token.validate(form)}")
        for field in form:
            print(f"{field.name}: {field.validate(form)}")
        
        if form.validate_on_submit():
            print("Form validated successfully")
            username = form.username.data
            email = form.email.data
            password = form.password.data

            print(f"\n==== NEW REGISTRATION ====")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print("=========================\n")

            if User.query.filter_by(username=username).first():
                print(f"Username {username} already taken")
                flash('Username already taken.', 'error')
                return redirect(url_for('auth.register'))

            if User.query.filter_by(email=email).first():
                print(f"Email {email} already registered")
                flash('Email already registered.', 'error')
                return redirect(url_for('auth.register'))

            user = User(username=username, email=email)
            user.set_password(password)
            
            try:
                print("Adding user to database...")
                db.session.add(user)
                db.session.commit()
                print("User added successfully!")

                print("Sending verification email...")
                if send_verification_email(user):
                    print("Email sent, committing verification code...")
                    db.session.commit()  # Commit again to save the verification code
                    print("Verification code saved, redirecting to verification page...")
                    flash('Please check your email for the verification code.', 'success')
                    return redirect(url_for('auth.verify_email'))
                else:
                    print("Failed to send email!")
                    db.session.delete(user)
                    db.session.commit()
                    flash('Failed to send verification email. Please try again later.', 'error')
                    return redirect(url_for('auth.register'))
            except Exception as e:
                print(f"\n==== DATABASE ERROR ====")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print("======================\n")
                db.session.rollback()
                flash('An error occurred. Please try again later.', 'error')
                return redirect(url_for('auth.register'))
        else:
            print("\nForm validation failed:")
            for field, errors in form.errors.items():
                print(f"{field}: {errors}")

    return render_template('auth/register.html', title='Register', form=form)

@bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    print("\n==== VERIFY EMAIL ROUTE ====")
    if request.method == 'POST':
        code = request.form.get('code')
        print(f"Received code: {code}")
        
        # Rechercher tous les utilisateurs non vérifiés
        unverified_users = User.query.filter_by(email_verified=False).all()
        print(f"\nUnverified users found: {len(unverified_users)}")
        for u in unverified_users:
            print(f"- {u.username} (code: {u.verification_code})")
        
        # Rechercher l'utilisateur avec ce code
        user = User.query.filter_by(verification_code=code, email_verified=False).first()
        
        if user:
            print(f"\nFound user: {user.username}")
            print(f"Email: {user.email}")
            print(f"Verification code: {user.verification_code}")
            print(f"Code expires: {user.verification_code_expires}")
            
            if user.verify_email(code):
                print("Email verified successfully!")
                try:
                    db.session.commit()
                    print("Database updated successfully!")
                    flash('Email verified successfully! You can now log in.', 'success')
                    return redirect(url_for('auth.login'))
                except Exception as e:
                    print(f"Error updating database: {str(e)}")
                    db.session.rollback()
                    flash('An error occurred while verifying your email. Please try again.', 'error')
            else:
                print("Code verification failed")
                flash('Invalid or expired verification code', 'error')
        else:
            print(f"No user found with code: {code}")
            flash('Invalid verification code', 'error')
            
    return render_template('auth/verify_email.html', title='Verify Email')

@bp.route('/resend-verification')
def resend_verification():
    if current_user.is_authenticated and current_user.email_verified:
        return redirect(url_for('main.index'))
        
    user = User.query.filter_by(email_verified=False).order_by(User.id.desc()).first()
    if user:
        print(f"\n[RESEND] Resending verification email to user {user.username}")
        if send_verification_email(user):
            flash('A new verification code has been sent to your email', 'success')
        else:
            flash('Failed to send verification email. Please try again later.', 'error')
    else:
        print("[RESEND] No pending verification found")
        flash('No pending verification found', 'error')
        
    return redirect(url_for('auth.verify_email'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
            
        if not user.email_verified:
            flash('Please verify your email before logging in', 'error')
            return redirect(url_for('auth.verify_email'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')

        return redirect(next_page)

    return render_template('auth/login.html', title='Sign In', form=form)

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

    # Calculer les statistiques
    total_score = 0
    perfect_count = 0
    for result in history:
        total_score += result.percentage
        if result.percentage >= 100:
            perfect_count += 1

    avg_score = round(total_score / len(history), 1) if history else 0.0

    # Préparer les données pour le graphique
    chart_data = {'dates': [], 'scores': []}
    for result in sorted(history, key=lambda x: x.completed_at):
        chart_data['dates'].append(result.completed_at.strftime('%d/%m/%Y'))
        chart_data['scores'].append(float(result.percentage))

    return render_template('auth/profile.html',
                         user=user,
                         history=history,
                         categories=categories,
                         chart_data=chart_data,
                         is_owner=user == current_user,
                         avg_score=avg_score,
                         perfect_count=perfect_count)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres utilisateur"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_email':
            email = request.form.get('email')
            if User.query.filter_by(email=email).first() and email != current_user.email:
                flash('Email already registered.', 'error')
            else:
                current_user.email = email
                db.session.commit()
                flash('Email updated successfully.', 'success')

        elif action == 'update_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')

            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')

        return redirect(url_for('auth.settings'))

    return render_template('auth/settings.html')