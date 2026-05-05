#!/usr/bin/env python3
"""
🎮 ИГРИЩЕ — Сервер v2.0
"""

import http.server
import json
import random
import string
import time
import os

GAMES = {}

def load_games():
    games_dir = os.path.join(os.path.dirname(__file__), 'games')
    if not os.path.exists(games_dir):
        os.makedirs(games_dir)
        return
    for filename in sorted(os.listdir(games_dir)):
        if filename.endswith('.json'):
            filepath = os.path.join(games_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    game = json.load(f)
                    game_id = game.get('id')
                    if game_id:
                        GAMES[game_id] = game
                        print(f'   ✅ {game.get("name", filename)}')
            except Exception as e:
                print(f'   ❌ {filename}: {e}')

load_games()

rooms = {}

def gen():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def ucode():
    c = gen()
    while c in rooms:
        c = gen()
    return c

class GameServer(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == '/' or self.path == '/tv':
            self.path = '/templates/tv.html'
        elif self.path == '/player':
            self.path = '/templates/player.html'
        
        elif self.path == '/api/games':
            gl = {}
            for gid, g in GAMES.items():
                q_count = len(g.get('questions', []))
                if q_count == 0:
                    q_count = g.get('rounds', 5)
                gl[gid] = {
                    "id": g["id"],
                    "name": g["name"],
                    "description": g["description"],
                    "color": g["color"],
                    "icon": g.get("icon", "🎮"),
                    "icon_image": g.get("icon_image", ""),
                    "questions_count": q_count
                }
            self._json(gl)
            return
        
        elif self.path.startswith('/api/create'):
            gid = 'quiz'
            if '?game=' in self.path:
                gid = self.path.split('?game=')[1]
            if gid not in GAMES:
                self._json({'error': 'Игра не найдена'}, 400)
                return
            
            game = GAMES[gid]
            code = ucode()
            
            room = {
                'game_id': gid,
                'game_name': game['name'],
                'game_color': game['color'],
                'game_icon': game.get('icon', '🎮'),
                'game_icon_image': game.get('icon_image', ''),
                'players': {},
                'state': 'lobby',
                'current_question': -1,
                'answers': {},
                'scores': {},
                'question_start_time': 0,
                'created_at': time.time(),
                'player_order': [],
                'current_player_index': 0,
                'votes': {},
                'round': 0,
                'total_rounds': game.get('rounds', 5)
            }
            
            if gid == 'quiz':
                qs = random.sample(game['questions'], len(game['questions']))
                room['questions'] = qs
                room['points'] = game.get('points_per_question', 100)
            elif gid == 'truth_dare':
                room['truth_pool'] = game.get('truth_pool', [])
                room['dare_pool'] = game.get('dare_pool', [])
                room['points'] = game.get('points_per_question', 50)
            elif gid == 'draw':
                room['questions'] = game.get('questions', [])
                room['points'] = game.get('points_per_question', 200)
                room['player_themes'] = {}
            
            rooms[code] = room
            print(f'✅ Комната {code} — {game["name"]}')
            self._json({'code': code, 'game': {'name': game['name'], 'color': game['color'], 'icon': game.get('icon', '🎮'), 'icon_image': game.get('icon_image', '')}})
            return
        
        elif self.path.startswith('/api/state/'):
            code = self.path.split('/')[-1]
            if code not in rooms:
                self._json({'error': 'Комната не найдена'}, 404)
                return
            
            room = rooms[code]
            gid = room['game_id']
            
            response = {
                'state': room['state'],
                'game_name': room['game_name'],
                'game_color': room['game_color'],
                'game_icon': room.get('game_icon', '🎮'),
                'game_icon_image': room.get('game_icon_image', ''),
                'game_type': gid,
                'players': room['players'],
                'scores': room['scores'],
                'round': room.get('round', 0),
                'total_rounds': room.get('total_rounds', 5)
            }
            
            if gid == 'quiz':
                q_idx = room['current_question']
                current_q = None
                q_time_left = 0
                if q_idx >= 0 and q_idx < len(room.get('questions', [])):
                    q = room['questions'][q_idx]
                    current_q = {'text': q['text'], 'answers': q['answers'], 'time': q.get('time', 30)}
                    if room.get('question_start_time'):
                        elapsed = time.time() - room['question_start_time']
                        q_time_left = max(0, int(q.get('time', 30) - elapsed))
                    else:
                        q_time_left = q.get('time', 30)
                response['current_question'] = current_q
                response['question_index'] = q_idx
                response['total_questions'] = len(room.get('questions', []))
                response['question_time_left'] = q_time_left
                response['answered_players'] = list(room['answers'].keys())
                response['answers_count'] = len(room['answers'])
            
            elif gid == 'truth_dare':
                player_order = room.get('player_order', [])
                cp_index = room.get('current_player_index', 0)
                if player_order and cp_index < len(player_order):
                    response['current_player_id'] = player_order[cp_index]
                    response['current_player_name'] = room['players'].get(player_order[cp_index], {}).get('name', '')
                response['votes'] = room.get('votes', {})
                response['vote_result'] = room.get('vote_result', '')
                response['current_task'] = room.get('current_task', '')
                response['task_type'] = room.get('task_type', '')
                response['show_task'] = room.get('show_task', False)
                response['votes_count'] = len(room.get('votes', {}))
                response['total_voters'] = max(0, len(room['players']) - 1)
            
            self._json(response)
            return
        
        return super().do_GET()
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length)) if length > 0 else {}
        
        if self.path == '/api/join':
            code = data.get('code', '').upper()
            name = data.get('name', 'Игрок').strip() or 'Игрок'
            if code not in rooms:
                self._json({'error': 'Комната не найдена'}, 404)
                return
            room = rooms[code]
            if room['state'] != 'lobby':
                self._json({'error': 'Игра уже началась'}, 400)
                return
            if len(room['players']) >= 8:
                self._json({'error': 'Комната заполнена'}, 400)
                return
            pid = str(random.randint(10000, 99999))
            room['players'][pid] = {'name': name}
            room['scores'][pid] = 0
            print(f'👤 {name} → {code}')
            self._json({'player_id': pid, 'name': name, 'game_type': room['game_id']})
            return
        
        elif self.path == '/api/start':
            code = data.get('code', '').upper()
            if code in rooms:
                room = rooms[code]
                if len(room['players']) == 0:
                    self._json({'error': 'Нужен хотя бы 1 игрок'}, 400)
                    return
                gid = room['game_id']
                if gid == 'quiz':
                    room['state'] = 'playing'
                    room['current_question'] = 0
                    room['question_start_time'] = time.time()
                elif gid == 'truth_dare':
                    player_ids = list(room['players'].keys())
                    random.shuffle(player_ids)
                    room['player_order'] = player_ids
                    room['current_player_index'] = 0
                    room['round'] = 0
                    room['state'] = 'voting'
                    room['votes'] = {}
                    room['vote_result'] = ''
                    room['show_task'] = False
                    room['current_task'] = ''
                    room['task_type'] = ''
                print(f'🚀 Игра в {code} началась!')
            self._json({'ok': True, 'game_type': rooms[code]['game_id']})
            return
        
        elif self.path == '/api/vote':
            code = data.get('code', '').upper()
            pid = data.get('player_id', '')
            vote = data.get('vote', '')
            if code in rooms and pid in rooms[code]['players']:
                room = rooms[code]
                cp_id = room['player_order'][room['current_player_index']]
                if pid == cp_id:
                    self._json({'error': 'Ты выбранный игрок'}, 400)
                    return
                room['votes'][pid] = vote
                total_voters = len(room['players']) - 1
                if len(room['votes']) >= total_voters:
                    truth_count = sum(1 for v in room['votes'].values() if v == 'truth')
                    dare_count = sum(1 for v in room['votes'].values() if v == 'dare')
                    if truth_count >= dare_count:
                        room['vote_result'] = 'truth'
                        room['current_task'] = random.choice(room['truth_pool'])
                        room['task_type'] = 'truth'
                    else:
                        room['vote_result'] = 'dare'
                        room['current_task'] = random.choice(room['dare_pool'])
                        room['task_type'] = 'dare'
                    room['show_task'] = True
                    room['state'] = 'task'
                self._json({'ok': True})
                return
            self._json({'error': 'Ошибка'}, 400)
            return
        
        elif self.path == '/api/task_done':
            code = data.get('code', '').upper()
            pid = data.get('player_id', '')
            if code in rooms and pid in rooms[code]['players']:
                room = rooms[code]
                cp_id = room['player_order'][room['current_player_index']]
                if pid != cp_id:
                    self._json({'error': 'Не твой ход'}, 400)
                    return
                room['scores'][pid] += room.get('points', 50)
                room['current_player_index'] += 1
                room['round'] += 1
                if room['round'] >= room['total_rounds'] or room['current_player_index'] >= len(room['player_order']):
                    room['state'] = 'finished'
                else:
                    room['state'] = 'voting'
                    room['votes'] = {}
                    room['vote_result'] = ''
                    room['show_task'] = False
                self._json({'ok': True})
                return
            self._json({'error': 'Ошибка'}, 400)
            return
        
        elif self.path == '/api/answer':
            code = data.get('code', '').upper()
            pid = data.get('player_id', '')
            answer = data.get('answer', 0)
            if code in rooms and pid in rooms[code]['players']:
                room = rooms[code]
                if room['game_id'] == 'quiz':
                    q_idx = room['current_question']
                    if 0 <= q_idx < len(room.get('questions', [])):
                        is_correct = answer == room['questions'][q_idx]['correct']
                        if is_correct:
                            room['scores'][pid] += room.get('points', 100)
                        room['answers'][pid] = answer
                        self._json({'correct': is_correct, 'score': room['scores'][pid]})
                        return
            self._json({'error': 'Ошибка'}, 400)
            return
        
        elif self.path == '/api/next':
            code = data.get('code', '').upper()
            if code in rooms:
                room = rooms[code]
                if room['game_id'] == 'quiz':
                    room['current_question'] += 1
                    room['answers'] = {}
                    room['question_start_time'] = time.time()
                    if room['current_question'] >= len(room.get('questions', [])):
                        room['state'] = 'finished'
            self._json({'ok': True})
            return
        
        elif self.path == '/api/reset':
            code = data.get('code', '').upper()
            if code in rooms:
                room = rooms[code]
                game = GAMES[room['game_id']]
                if room['game_id'] == 'quiz':
                    room['questions'] = random.sample(game['questions'], len(game['questions']))
                room['state'] = 'lobby'
                room['current_question'] = -1
                room['answers'] = {}
                room['votes'] = {}
                room['scores'] = {pid: 0 for pid in room['players']}
                room['question_start_time'] = 0
                room['round'] = 0
                room['current_player_index'] = 0
                room['show_task'] = False
            self._json({'ok': True})
            return
        
        self._json({'error': 'Неизвестный запрос'}, 404)
    
    def _json(self, data, status=200):
        text = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(text.encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def main():
    port = 8000
    print('=' * 50)
    print('🎮  И Г Р И Щ Е  v2.0')
    print('=' * 50)
    print(f'📺  ТВ:  http://localhost:{port}/tv')
    print(f'📱  Тел: http://localhost:{port}/player')
    print('=' * 50)
    print(f'📦 Игр: {len(GAMES)}')
    for gid, g in GAMES.items():
        print(f'   {g.get("icon","")} {g["name"]}')
    print('=' * 50)
    print('🚀 Запуск...')
    httpd = http.server.HTTPServer(('0.0.0.0', port), GameServer)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Пока!')
        httpd.shutdown()

if __name__ == '__main__':
    main()