"""
Flask Web Application для управления множественными Instagram аккаунтами
"""

from flask import Flask, render_template, request, jsonify, Response
from instagram_manager import InstagramManager
import json
import queue
import time
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Глобальные переменные
instagram_manager = None
log_queue = queue.Queue()
is_initialized = False

def log_callback(message):
    """Callback функция для отправки логов в очередь"""
    log_queue.put(message)

def initialize_manager():
    """Инициализация Instagram Manager"""
    global instagram_manager, is_initialized
    
    instagram_manager = InstagramManager(log_callback=log_callback)
    
    # Загрузка аккаунтов
    if not instagram_manager.load_accounts():
        log_callback("[SYSTEM] [INIT] [ERROR] Не удалось загрузить аккаунты из account.json")
        return False
    
    # КРИТИЧЕСКАЯ ОПЕРАЦИЯ: Вход во все аккаунты
    log_callback("[SYSTEM] [INIT] [INFO] Начало авторизации аккаунтов...")
    success, results = instagram_manager.login_all()
    
    if not success:
        log_callback("[SYSTEM] [INIT] [ERROR] ====================================")
        log_callback("[SYSTEM] [INIT] [ERROR] КРИТИЧЕСКАЯ ОШИБКА АВТОРИЗАЦИИ")
        log_callback("[SYSTEM] [INIT] [ERROR] Не все аккаунты смогли войти")
        log_callback("[SYSTEM] [INIT] [ERROR] ====================================")
        for result in results:
            if result['status'] == 'error':
                log_callback(f"[SYSTEM] [INIT] [ERROR] Аккаунт: {result['username']} - {result['message']}")
        log_callback("[SYSTEM] [INIT] [ERROR] Приложение НЕ может работать. Исправьте ошибки и перезапустите.")
        is_initialized = False
        return False
    
    log_callback("[SYSTEM] [INIT] [SUCCESS] ====================================")
    log_callback("[SYSTEM] [INIT] [SUCCESS] Все аккаунты успешно авторизованы")
    log_callback("[SYSTEM] [INIT] [SUCCESS] Приложение готово к работе")
    log_callback("[SYSTEM] [INIT] [SUCCESS] ====================================")
    is_initialized = True
    return True

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Страница дашборда (после успешной авторизации)"""
    if not is_initialized:
        return render_template('index.html')
    return render_template('dashboard.html')

@app.route('/api/init', methods=['POST'])
def api_init():
    """API: Инициализация и авторизация аккаунтов"""
    global is_initialized
    
    if is_initialized:
        return jsonify({
            'success': True,
            'message': 'Система уже инициализирована'
        })
    
    # Запуск инициализации в отдельном потоке
    def init_thread():
        initialize_manager()
    
    thread = Thread(target=init_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Инициализация запущена. Следите за логами.'
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """API: Получение статуса аккаунтов"""
    if not instagram_manager:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована',
            'accounts': []
        })
    
    accounts = instagram_manager.get_accounts_status()
    return jsonify({
        'success': True,
        'initialized': is_initialized,
        'accounts': accounts
    })

@app.route('/api/follow', methods=['POST'])
def api_follow():
    """API: Подписка на пользователя"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({
            'success': False,
            'message': 'Username не указан'
        })
    
    # Выполнение в отдельном потоке
    def follow_thread():
        instagram_manager.follow_user(username)
    
    thread = Thread(target=follow_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Подписка на @{username} запущена. Следите за логами.'
    })

@app.route('/api/unfollow', methods=['POST'])
def api_unfollow():
    """API: Отписка от пользователя"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({
            'success': False,
            'message': 'Username не указан'
        })
    
    def unfollow_thread():
        instagram_manager.unfollow_user(username)
    
    thread = Thread(target=unfollow_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Отписка от @{username} запущена. Следите за логами.'
    })

@app.route('/api/like', methods=['POST'])
def api_like():
    """API: Лайк поста"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'URL поста не указан'
        })
    
    def like_thread():
        instagram_manager.like_media(url)
    
    thread = Thread(target=like_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Лайк поста запущен. Следите за логами.'
    })

@app.route('/api/unlike', methods=['POST'])
def api_unlike():
    """API: Удаление лайка"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'URL поста не указан'
        })
    
    def unlike_thread():
        instagram_manager.unlike_media(url)
    
    thread = Thread(target=unlike_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Удаление лайка запущено. Следите за логами.'
    })

@app.route('/api/comment', methods=['POST'])
def api_comment():
    """API: Комментарий к посту"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    url = data.get('url', '').strip()
    comment = data.get('comment', '').strip()
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'URL поста не указан'
        })
    
    if not comment:
        return jsonify({
            'success': False,
            'message': 'Текст комментария не указан'
        })
    
    def comment_thread():
        instagram_manager.comment_media(url, comment)
    
    thread = Thread(target=comment_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Комментирование запущено. Следите за логами.'
    })

@app.route('/api/save', methods=['POST'])
def api_save():
    """API: Сохранение поста в избранное"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'URL поста не указан'
        })
    
    def save_thread():
        instagram_manager.save_media(url)
    
    thread = Thread(target=save_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Сохранение поста запущено. Следите за логами.'
    })

@app.route('/api/unsave', methods=['POST'])
def api_unsave():
    """API: Удаление поста из избранного"""
    if not is_initialized:
        return jsonify({
            'success': False,
            'message': 'Система не инициализирована'
        })
    
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({
            'success': False,
            'message': 'URL поста не указан'
        })
    
    def unsave_thread():
        instagram_manager.unsave_media(url)
    
    thread = Thread(target=unsave_thread)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Удаление из избранного запущено. Следите за логами.'
    })

@app.route('/api/logs')
def api_logs():
    """API: Server-Sent Events для логов в реальном времени"""
    def generate():
        while True:
            try:
                # Ожидание новых логов с таймаутом
                message = log_queue.get(timeout=1)
                yield f"data: {json.dumps({'log': message})}\n\n"
            except queue.Empty:
                # Отправка keep-alive сообщения
                yield f"data: {json.dumps({'keepalive': True})}\n\n"
            except Exception as e:
                print(f"Error in log stream: {e}")
                break
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("=" * 60)
    print("Instagram Control Panel")
    print("=" * 60)
    print("Запуск веб-сервера...")
    print("Откройте браузер и перейдите по адресу: http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
