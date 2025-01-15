from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User, QuizResult
from app import db, mail
from urllib.parse import urlparse
from werkzeug.security import check_password_hash
from app.forms import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm
from flask_mail import Message
import os
import yaml
from werkzeug.utils import secure_filename
import time

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

def send_password_reset_email(user):
    token = user.generate_reset_token()
    msg = Message('QuizOps - Password Reset Request',
                 sender=current_app.config['MAIL_DEFAULT_SENDER'],
                 recipients=[user.email])
    
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    msg.body = f'''Hi {user.username},

To reset your password, visit the following link:

{reset_url}

If you did not make this request, please ignore this email.

Best regards,
The QuizOps Team'''

    msg.html = f'''
<p>Hi {user.username},</p>

<p>To reset your password, click the button below:</p>

<p style="text-align: center;">
    <a href="{reset_url}" 
       style="display: inline-block; padding: 10px 20px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 4px;">
        Reset Password
    </a>
</p>

<p>If you did not make this request, please ignore this email.</p>

<p>Best regards,<br>
The QuizOps Team</p>'''

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
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

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Page des paramètres utilisateur"""
    if request.method == 'POST':
        action = request.form.get('action')
        print(f"\n==== SETTINGS UPDATE ====")
        print(f"Action: {action}")
        print(f"Current user: {current_user.username}")
        print(f"Form data: {request.form}")

        try:
            # Get a fresh user object from the database using UUID
            user = User.query.get(current_user.id)
            if not user:
                flash('User not found.', 'error')
                return redirect(url_for('auth.settings'))
            
            if action == 'update_email':
                email = request.form.get('email')
                print(f"New email: {email}")
                if email != user.email:
                    if User.query.filter_by(email=email).first():
                        flash('Email already registered.', 'error')
                        return redirect(url_for('auth.settings'))
                    user.email = email
                    db.session.commit()
                    # Refresh the user session
                    login_user(user)
                    flash('Email updated successfully.', 'success')

            elif action == 'update_password':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')

                if not user.check_password(current_password):
                    flash('Current password is incorrect.', 'error')
                else:
                    user.set_password(new_password)
                    db.session.commit()
                    # Refresh the user session
                    login_user(user)
                    flash('Password updated successfully.', 'success')

            elif action == 'update_username':
                new_username = request.form.get('new_username', '').strip()
                print(f"New username: {new_username}")
                
                # Validate username
                if not new_username:
                    flash('Username cannot be empty.', 'error')
                    return redirect(url_for('auth.settings'))
                    
                if len(new_username) < 3 or len(new_username) > 64:
                    flash('Username must be between 3 and 64 characters.', 'error')
                    return redirect(url_for('auth.settings'))
                    
                # Check if username is already taken
                if new_username != user.username:
                    existing_user = User.query.filter_by(username=new_username).first()
                    if existing_user:
                        flash('Username is already taken.', 'error')
                        return redirect(url_for('auth.settings'))
                    
                    # Update username
                    user.username = new_username
                    db.session.commit()
                    # Refresh the user session
                    login_user(user)
                    flash('Username updated successfully.', 'success')
                    print(f"Username updated to: {user.username}")

        except Exception as e:
            print(f"\n==== ERROR ====")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("===============\n")
            db.session.rollback()
            flash('An error occurred while updating settings.', 'error')

        return redirect(url_for('auth.settings'))

    return render_template('auth/settings.html')

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

    # Prepare chart data
    chart_data = {
        'dates': [],
        'scores': [],
        'categories': [],
        'activity': {}
    }

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
            
        # Chart data
        chart_data['dates'].append(result.completed_at.strftime('%Y-%m-%d'))
        chart_data['scores'].append(result.percentage)
        chart_data['categories'].append(result.category)
        
        # Activity data (count quizzes per month)
        month_key = result.completed_at.strftime('%B %Y')
        chart_data['activity'][month_key] = chart_data['activity'].get(month_key, 0) + 1
        
        # Category statistics
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

    # Calculate average scores for categories
    for category, stats in category_stats.items():
        stats['avg_score'] = round(stats['total_score'] / stats['count'], 1)

    return render_template('auth/profile.html',
                         user=user,
                         history=quiz_results,
                         total_quizzes=total_quizzes,
                         perfect_scores=perfect_scores,
                         avg_score=round(avg_score, 1),
                         chart_data=chart_data,
                         category_stats=category_stats,
                         categories=categories)

@bp.route('/profile/privacy/update', methods=['POST'])
@login_required
def update_profile_privacy():
    try:
        print(f"Updating privacy settings for user {current_user.username}")
        private_profile = 'private_profile' in request.form
        print(f"Setting private_profile to: {private_profile}")
        
        # Get a fresh user object from the database using UUID
        user = User.query.get(current_user.id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.settings'))
            
        user.private_profile = private_profile
        db.session.commit()
        # Refresh the user session
        login_user(user)
        
        print("Privacy settings updated successfully")
        flash('Privacy settings updated successfully.', 'success')
    except Exception as e:
        print(f"Error updating privacy settings: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating privacy settings.', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/profile/social-media/update', methods=['POST'])
@login_required
def update_social_media():
    try:
        # Get values from form
        twitter = request.form.get('twitter_username', '').strip()
        bluesky = request.form.get('bluesky_handle', '').strip()
        linkedin = request.form.get('linkedin_url', '').strip()
        website = request.form.get('website_url', '').strip()
        github = request.form.get('github_username', '').strip()
        gitlab = request.form.get('gitlab_username', '').strip()
        dockerhub = request.form.get('dockerhub_username', '').strip()
        stackoverflow = request.form.get('stackoverflow_url', '').strip()
        medium = request.form.get('medium_username', '').strip()
        dev_to = request.form.get('dev_to_username', '').strip()
        
        # Basic validation
        if linkedin and not linkedin.startswith(('http://', 'https://')):
            linkedin = f'https://{linkedin}'
        if website and not website.startswith(('http://', 'https://')):
            website = f'https://{website}'
        if stackoverflow and not stackoverflow.startswith(('http://', 'https://')):
            stackoverflow = f'https://{stackoverflow}'
            
        # Remove @ from Twitter username if present
        if twitter.startswith('@'):
            twitter = twitter[1:]
            
        # Get a fresh user object from the database using UUID
        user = User.query.get(current_user.id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.settings'))
            
        # Update user object
        user.twitter_username = twitter or None
        user.bluesky_handle = bluesky or None
        user.linkedin_url = linkedin or None
        user.website_url = website or None
        user.github_username = github or None
        user.gitlab_username = gitlab or None
        user.dockerhub_username = dockerhub or None
        user.stackoverflow_url = stackoverflow or None
        user.medium_username = medium or None
        user.dev_to_username = dev_to or None
        
        db.session.commit()
        # Refresh the user session
        login_user(user)
        flash('Social media links updated successfully.', 'success')
    except Exception as e:
        print(f"Error updating social media: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating social media links.', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and send_password_reset_email(user):
            flash('Check your email for the instructions to reset your password', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('An error occurred while sending the password reset email. Please try again later.', 'error')
    
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Find user with this token
    user = User.query.filter_by(reset_password_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('auth.reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

@bp.route('/profile/username/update', methods=['POST'])
@login_required
def update_username():
    try:
        new_username = request.form.get('new_username', '').strip()
        
        # Validate username
        if not new_username:
            flash('Username cannot be empty.', 'error')
            return redirect(url_for('auth.settings'))
            
        if len(new_username) < 3 or len(new_username) > 64:
            flash('Username must be between 3 and 64 characters.', 'error')
            return redirect(url_for('auth.settings'))
            
        # Check if username is already taken
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Username is already taken.', 'error')
            return redirect(url_for('auth.settings'))
            
        # Update username
        current_user.username = new_username
        db.session.commit()
        flash('Username updated successfully.', 'success')
        
    except Exception as e:
        print(f"Error updating username: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating username.', 'error')
    
    return redirect(url_for('auth.settings'))

@bp.route('/profile/picture/update', methods=['POST'])
@login_required
def update_profile_picture():
    try:
        if 'profile_picture' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('auth.settings'))
            
        file = request.files['profile_picture']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('auth.settings'))
            
        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload a PNG, JPG, or JPEG file.', 'error')
            return redirect(url_for('auth.settings'))
            
        # Get a fresh user object from the database using UUID
        user = User.query.get(current_user.id)
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('auth.settings'))
            
        # Delete old profile picture if it exists
        if user.profile_picture and user.profile_picture != 'default.png':
            try:
                old_picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_picture)
                if os.path.exists(old_picture_path):
                    os.remove(old_picture_path)
            except Exception as e:
                print(f"Error deleting old profile picture: {str(e)}")
                
        # Save new profile picture
        filename = secure_filename(file.filename)
        # Add timestamp to filename to prevent caching issues
        filename = f"{int(time.time())}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        user.profile_picture = filename
        db.session.commit()
        # Refresh the user session
        login_user(user)
        
        flash('Profile picture updated successfully.', 'success')
    except Exception as e:
        print(f"Error updating profile picture: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating profile picture.', 'error')
        
    return redirect(url_for('auth.settings'))