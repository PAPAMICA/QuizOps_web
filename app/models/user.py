from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6))
    verification_code_expires = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_code(self):
        """Génère un nouveau code de vérification de 6 chiffres"""
        self.verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.verification_code_expires = datetime.utcnow() + timedelta(hours=24)
        print(f"\n==== GENERATING VERIFICATION CODE ====")
        print(f"User: {self.username}")
        print(f"Code: {self.verification_code}")
        print(f"Expires: {self.verification_code_expires}")
        print("=====================================\n")
        return self.verification_code

    def verify_email(self, code):
        """Vérifie le code de vérification d'email"""
        print(f"\n==== VERIFYING EMAIL CODE ====")
        print(f"User: {self.username}")
        print(f"Stored code: {self.verification_code}")
        print(f"Received code: {code}")
        print(f"Code expires: {self.verification_code_expires}")
        print(f"Current time: {datetime.utcnow()}")
        
        if not self.verification_code:
            print("No verification code stored")
            return False
            
        if not code:
            print("No code provided")
            return False
            
        if self.verification_code != code:
            print("Codes don't match")
            return False
            
        if datetime.utcnow() > self.verification_code_expires:
            print("Code has expired")
            return False
            
        print("Code is valid! Verifying email...")
        self.email_verified = True
        self.verification_code = None
        self.verification_code_expires = None
        print("Email verified successfully!")
        print("============================\n")
        return True

    def get_best_score_by_quiz(self, quiz_id):
        """Récupère le meilleur score pour un quiz donné"""
        best_result = QuizResult.query.filter_by(
            user_id=self.id,
            quiz_id=quiz_id
        ).order_by(QuizResult.percentage.desc()).first()
        return best_result.percentage if best_result else None

    def get_total_quizzes_completed(self):
        """Récupère le nombre total de quiz complétés"""
        return QuizResult.query.filter_by(user_id=self.id).count()

    def get_average_score(self):
        """Calcule le score moyen sur tous les quiz"""
        results = QuizResult.query.filter_by(user_id=self.id).all()
        if not results:
            return 0
        return sum(result.percentage for result in results) / len(results)

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(64), nullable=False)
    quiz_title = db.Column(db.String(128))
    category = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.JSON)
    time_spent = db.Column(db.Integer)  # temps en secondes

    @property
    def percentage(self):
        """Calcule le pourcentage de réussite"""
        try:
            return round((self.score / self.max_score) * 100, 1)
        except (ZeroDivisionError, TypeError):
            return 0.0 