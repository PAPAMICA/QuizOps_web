# QuizIT

Une application web Flask pour tester vos connaissances en IT avec des quiz interactifs.

## Fonctionnalités

- Système d'authentification (inscription/connexion)
- Format YAML pour les quiz (facile à ajouter/modifier)
- Suivi des résultats
- Interface moderne avec Tailwind CSS

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-username/quizit.git
cd quizit
```

2. Créez un environnement virtuel et activez-le :
```bash
python -m venv venv
source venv/bin/activate  # Sur Unix/macOS
# ou
.\venv\Scripts\activate  # Sur Windows
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Initialisez la base de données :
```bash
flask init-db
```

## Lancement de l'application

```bash
python run.py
```

L'application sera accessible à l'adresse `http://localhost:5000`

## Structure des quiz

Les quiz sont stockés dans le dossier `app/quiz_data` au format YAML. Voici un exemple de structure :

```yaml
id: network_basics
title: Les bases du réseau
description: Un quiz pour tester vos connaissances sur les bases du réseau informatique

questions:
  - id: q1
    question: Que signifie IP ?
    options:
      - Internet Protocol
      - Internet Program
      - Internal Protocol
      - Internet Provider
    explanation: IP signifie Internet Protocol. C'est le protocole fondamental qui permet l'adressage et le routage des paquets sur Internet.
    source: "RFC 791 - https://datatracker.ietf.org/doc/html/rfc791"
    correct_answer: 0  # Index de la bonne réponse (0-3)
```

## Contribution

1. Fork le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committez vos changements (`git commit -am 'Ajout d'une nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Créez une Pull Request

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.