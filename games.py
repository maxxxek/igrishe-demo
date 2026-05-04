"""
🎮 ГЕНЕРАТОР ИГР ДЛЯ ИГРИЩЕ
Использует банки из game_data.py для динамической сборки игр.
"""

import random
from game_data import *

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def generate_quiz_question(q_data):
    """Генерирует вопрос для квиза с 4 вариантами ответов"""
    correct = q_data["correct"]
    category = q_data["category"]
    
    # Берём неправильные ответы из соответствующей категории
    wrong_pool = QUIZ_WRONG_ANSWERS.get(category, []).copy()
    
    # Убираем правильный ответ, если он есть в пуле
    if correct in wrong_pool:
        wrong_pool.remove(correct)
    
    # Выбираем 3 случайных неправильных ответа
    wrong_answers = random.sample(wrong_pool, min(3, len(wrong_pool)))
    
    # Собираем все ответы и перемешиваем
    all_answers = wrong_answers + [correct]
    random.shuffle(all_answers)
    
    # Находим индекс правильного ответа
    correct_index = all_answers.index(correct)
    
    return {
        "text": q_data["text"],
        "answers": all_answers,
        "correct": correct_index,
        "time": q_data.get("time", 15)
    }


def generate_truth_dare_question():
    """Генерирует случайный вопрос Правда или Действие"""
    is_truth = random.choice([True, False])
    
    if is_truth:
        question_text = f"🔥 ПРАВДА: {random.choice(TRUTH_QUESTIONS)}"
    else:
        question_text = f"💥 ДЕЙСТВИЕ: {random.choice(DARE_QUESTIONS)}"
    
    # Собираем ответы из разных категорий
    answers = []
    answers.append(random.choice(TRUTH_DARE_ANSWERS["positive"]))
    answers.append(random.choice(TRUTH_DARE_ANSWERS["negative"]))
    answers.append(random.choice(TRUTH_DARE_ANSWERS["alternative"]))
    answers.append(random.choice(TRUTH_DARE_ANSWERS["skip"]))
    
    random.shuffle(answers)
    
    return {
        "text": question_text,
        "answers": answers,
        "correct": 0,  # любой ответ засчитывается
        "time": random.choice([20, 25, 30])
    }


def generate_draw_question():
    """Генерирует вопрос для Рисовача"""
    word = random.choice(DRAW_WORDS)
    
    answers = []
    answers.append(random.choice(DRAW_ANSWERS["positive"]))
    answers.append(random.choice(DRAW_ANSWERS["negative"]))
    answers.append(random.choice(DRAW_ANSWERS["alternative"]))
    answers.append(random.choice(DRAW_ANSWERS["skip"]))
    
    random.shuffle(answers)
    
    return {
        "text": f"🎨 Нарисуй: {word.upper()}",
        "answers": answers,
        "correct": 0,
        "time": 45
    }


# ==================== ФУНКЦИИ ДЛЯ СЕРВЕРА ====================

def get_game(game_id, num_questions=5):
    """
    Создаёт игру с указанным количеством вопросов.
    Вопросы генерируются заново при каждом вызове!
    """
    if game_id == "quiz":
        # Выбираем случайные вопросы из банка
        selected = random.sample(QUIZ_QUESTIONS, min(num_questions, len(QUIZ_QUESTIONS)))
        questions = [generate_quiz_question(q) for q in selected]
        
        return {
            "id": "quiz",
            "name": "🎯 Квиз-Шоу",
            "description": "Отвечай на вопросы быстрее всех!",
            "color": "#7103ff",
            "icon": "🧠",
            "points_per_question": 100,
            "questions": questions
        }
    
    elif game_id == "truth_dare":
        questions = [generate_truth_dare_question() for _ in range(num_questions)]
        
        return {
            "id": "truth_dare",
            "name": "🔥 Правда или Действие",
            "description": "Честность или смелость — выбор за тобой!",
            "color": "#ff010c",
            "icon": "🎭",
            "points_per_question": 50,
            "questions": questions
        }
    
    elif game_id == "draw":
        questions = [generate_draw_question() for _ in range(num_questions)]
        
        return {
            "id": "draw",
            "name": "🎨 Рисовач",
            "description": "Объясни слово рисунком!",
            "color": "#e460f0",
            "icon": "✏️",
            "points_per_question": 200,
            "questions": questions
        }
    
    return None


def get_games_list():
    """Список доступных игр (без генерации вопросов)"""
    return {
        "quiz": {
            "id": "quiz",
            "name": "🎯 Квиз-Шоу",
            "description": "Отвечай на вопросы быстрее всех!",
            "color": "#7103ff",
            "icon": "🧠",
            "questions_count": len(QUIZ_QUESTIONS)
        },
        "truth_dare": {
            "id": "truth_dare",
            "name": "🔥 Правда или Действие",
            "description": "Честность или смелость — выбор за тобой!",
            "color": "#ff010c",
            "icon": "🎭",
            "questions_count": len(TRUTH_QUESTIONS) + len(DARE_QUESTIONS)
        },
        "draw": {
            "id": "draw",
            "name": "🎨 Рисовач",
            "description": "Объясни слово рисунком!",
            "color": "#e460f0",
            "icon": "✏️",
            "questions_count": len(DRAW_WORDS)
        }
    }


def check_answer(game, question_index, player_answer):
    """Проверяет правильность ответа"""
    if 0 <= question_index < len(game['questions']):
        return player_answer == game['questions'][question_index]['correct']
    return False


def get_question(game, question_index):
    """Возвращает вопрос без правильного ответа (для отправки клиенту)"""
    if not game or question_index < 0 or question_index >= len(game['questions']):
        return None
    
    q = game['questions'][question_index]
    return {
        'text': q['text'],
        'answers': q['answers'],
        'time': q['time']
    }