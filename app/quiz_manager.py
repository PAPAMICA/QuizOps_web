import os
import yaml
from typing import Dict, List, Optional

class QuizManager:
    def __init__(self, quiz_repo_path: str):
        self.quiz_repo_path = quiz_repo_path
        self.quizzes = {}
        self.categories = {}
        self.load_all_quizzes()

    def load_category_config(self, category_path: str) -> Dict:
        """Load category configuration from config.yml"""
        config_path = os.path.join(category_path, 'config.yml')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {'name': os.path.basename(category_path)}

    def load_all_quizzes(self):
        """Load all quizzes from QuizOps_quiz repository"""
        for root, dirs, files in os.walk(self.quiz_repo_path):
            if 'config.yml' in files:
                category = os.path.basename(root)
                self.categories[category] = self.load_category_config(root)

            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    if 'config.yml' not in file:
                        category = os.path.basename(os.path.dirname(os.path.join(root, file)))
                        quiz_path = os.path.join(root, file)
                        self.load_quiz(quiz_path, category)

    def load_quiz(self, quiz_path: str, category: str):
        """Load an individual quiz from a YAML file"""
        try:
            with open(quiz_path, 'r', encoding='utf-8') as f:
                quiz_data = yaml.safe_load(f)
                quiz_id = quiz_data.get('id')
                if quiz_id:
                    quiz_data['file_path'] = quiz_path
                    quiz_data['category'] = category
                    self.quizzes[quiz_id] = quiz_data
        except Exception as e:
            print(f"Error loading quiz {quiz_path}: {str(e)}")

    def get_quiz(self, quiz_id: str) -> Optional[Dict]:
        """Get a quiz by its ID"""
        return self.quizzes.get(quiz_id)

    def get_all_quizzes(self) -> List[Dict]:
        """Get all available quizzes"""
        return list(self.quizzes.values())

    def get_quizzes_by_category(self, category: str) -> List[Dict]:
        """Get all quizzes for a specific category"""
        return [quiz for quiz in self.quizzes.values() if quiz.get('category') == category]

    def get_categories(self) -> List[Dict]:
        """Get all available categories with their configuration"""
        return [(cat, self.categories.get(cat, {'name': cat})) for cat in set(quiz.get('category') for quiz in self.quizzes.values())] 