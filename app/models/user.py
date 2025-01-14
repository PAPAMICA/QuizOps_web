from app.extensions import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    category = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.JSON)
    time_spent = db.Column(db.Integer)  # temps en secondes

    @property
    def percentage(self):
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0 