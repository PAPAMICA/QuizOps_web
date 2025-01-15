import os
import yaml
import random
from flask import current_app

class QuizManager:
    def __init__(self, quiz_repo_path):
        self.quiz_repo_path = quiz_repo_path
        self.quizzes = {}
        self.questions_by_category = {}
        self.load_quizzes()

    def load_quizzes(self):
        """Charge tous les quiz depuis le répertoire"""
        print(f"Loading quizzes from: {self.quiz_repo_path}")
        # Parcourir les catégories (dossiers de premier niveau)
        for category in os.listdir(self.quiz_repo_path):
            category_path = os.path.join(self.quiz_repo_path, category)
            
            # Ignorer les fichiers et les dossiers cachés
            if category.startswith('.') or not os.path.isdir(category_path):
                continue
                
            print(f"Loading category: {category}")
            
            # Initialiser la structure pour cette catégorie
            if category not in self.questions_by_category:
                self.questions_by_category[category] = {
                    'beginner': [],
                    'intermediate': [],
                    'advanced': [],
                    'expert': []
                }
            
            # Charger tous les fichiers yaml de la catégorie
            for file in os.listdir(category_path):
                if file.endswith('.yaml') and not file == 'config.yml':
                    quiz_path = os.path.join(category_path, file)
                    print(f"Loading quiz file: {quiz_path}")
                    
                    try:
                        with open(quiz_path, 'r', encoding='utf-8') as f:
                            quiz_data = yaml.safe_load(f)
                            if not quiz_data:
                                print(f"Empty quiz data in {quiz_path}")
                                continue

                            # Générer un ID de quiz s'il n'existe pas
                            if 'id' not in quiz_data:
                                quiz_id = f"{category}_{os.path.splitext(file)[0]}"
                                quiz_data['id'] = quiz_id
                            else:
                                quiz_id = quiz_data['id']

                            # Ajouter la catégorie aux données du quiz
                            quiz_data['category'] = category

                            print(f"Loaded quiz: {quiz_id} from category {category}")
                            self.quizzes[quiz_id] = quiz_data
                            
                            # Ajouter les questions au bon niveau dans la catégorie
                            level = quiz_data.get('level', 'beginner')
                            if level in self.questions_by_category[category]:
                                for question in quiz_data.get('questions', []):
                                    # Ajouter des métadonnées à la question
                                    question['quiz_id'] = quiz_id
                                    question['category'] = category
                                    question['level'] = level
                                    self.questions_by_category[category][level].append(question)

                    except Exception as e:
                        print(f"Error loading quiz {quiz_path}: {str(e)}")
                        continue

    def get_quiz(self, quiz_id):
        """Récupère un quiz par son ID"""
        return self.quizzes.get(quiz_id)

    def get_questions_by_category_and_level(self, category, level):
        """Récupère toutes les questions d'une catégorie et d'un niveau donnés"""
        if category in self.questions_by_category and level in self.questions_by_category[category]:
            return self.questions_by_category[category][level]
        return []

    def get_all_categories(self):
        """Récupère toutes les catégories disponibles"""
        return list(self.questions_by_category.keys())

    def get_categories(self):
        """Récupère les catégories avec leurs configurations depuis les fichiers config.yml"""
        categories = []
        # Parcourir tous les dossiers dans le répertoire quiz
        for category in os.listdir(self.quiz_repo_path):
            # Ignorer les fichiers et les dossiers cachés
            if category.startswith('.') or not os.path.isdir(os.path.join(self.quiz_repo_path, category)):
                continue
                
            config_path = os.path.join(self.quiz_repo_path, category, 'config.yml')
            try:
                if os.path.isfile(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                        if not config:
                            config = {}
                else:
                    config = {}
                
                # S'assurer que tous les champs requis existent avec des valeurs par défaut
                category_config = {
                    'name': config.get('name', category.replace('_', ' ').title()),
                    'description': config.get('description', ''),
                    'logo': config.get('logo', ''),
                    'color': config.get('color', 'gray')
                }
                categories.append((category, category_config))
                
            except Exception as e:
                print(f"Error loading category config {config_path}: {str(e)}")
                # En cas d'erreur, utiliser des valeurs par défaut
                categories.append((category, {
                    'name': category.replace('_', ' ').title(),
                    'description': '',
                    'logo': '',
                    'color': 'gray'
                }))
        
        # Trier les catégories par nom
        return sorted(categories, key=lambda x: x[1]['name'].lower())

    def get_quiz_list(self):
        """Récupère la liste de tous les quiz disponibles"""
        quiz_list = []
        for quiz_id, quiz_data in self.quizzes.items():
            if not quiz_id.startswith('custom_'):  # Exclure les quiz personnalisés
                quiz_list.append({
                    'id': quiz_id,
                    'title': quiz_data.get('title', ''),
                    'description': quiz_data.get('description', ''),
                    'category': quiz_data.get('category', ''),
                    'level': quiz_data.get('level', 'beginner'),
                    'is_custom': False
                })
        return quiz_list

    def get_quizzes_by_category(self, category):
        """Récupère tous les quiz d'une catégorie donnée"""
        print(f"Getting quizzes for category: {category}")
        print(f"Available quizzes: {list(self.quizzes.keys())}")
        quizzes = []
        for quiz_id, quiz_data in self.quizzes.items():
            if quiz_data.get('category') == category and not quiz_id.startswith('custom_'):
                print(f"Found quiz {quiz_id} in category {category}")
                quizzes.append({
                    'id': quiz_id,
                    'title': quiz_data.get('title', ''),
                    'description': quiz_data.get('description', ''),
                    'category': category,
                    'level': quiz_data.get('level', 'beginner'),
                    'is_custom': False,
                    'questions': quiz_data.get('questions', [])
                })
        
        # Trier les quiz d'abord par niveau puis par titre
        level_order = {'beginner': 0, 'intermediate': 1, 'advanced': 2, 'expert': 3}
        quizzes.sort(key=lambda x: (level_order.get(x['level'], 999), x['title'].lower()))
        
        print(f"Returning {len(quizzes)} quizzes for category {category}")
        return quizzes

    def create_custom_quiz(self, technologies, level, num_questions=10):
        """Crée un quiz personnalisé à partir des technologies et du niveau sélectionnés"""
        all_questions = []
        
        # Récupérer toutes les questions disponibles
        for tech in technologies:
            questions = self.get_questions_by_category_and_level(tech, level)
            all_questions.extend(questions)
        
        # S'assurer qu'il y a assez de questions
        if len(all_questions) < 1:
            return None
            
        # Limiter à 10 questions maximum
        num_questions = min(10, len(all_questions))
        
        # Sélectionner aléatoirement le nombre de questions demandé
        selected_questions = random.sample(all_questions, num_questions)
        
        # Créer l'ID unique pour le quiz personnalisé
        quiz_id = f'custom_{random.randint(10000, 99999)}'
        
        # Créer le quiz personnalisé
        custom_quiz = {
            'id': quiz_id,
            'title': f'Custom Quiz - {", ".join(technologies)} ({level})',
            'description': f'Custom quiz with questions from {", ".join(technologies)} at {level} level',
            'category': 'custom',
            'level': level,
            'questions': selected_questions,
            'is_custom': True
        }
        
        # Stocker le quiz dans self.quizzes
        self.quizzes[quiz_id] = custom_quiz
        return custom_quiz 