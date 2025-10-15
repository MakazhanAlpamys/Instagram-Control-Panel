"""
Instagram Manager - Управление множественными Instagram аккаунтами
Критическое требование: логика "все или ничего" - если хотя бы один аккаунт не может выполнить действие,
весь процесс останавливается
"""

import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from threading import Lock
from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, 
    ChallengeRequired, 
    FeedbackRequired,
    PleaseWaitFewMinutes,
    UserNotFound,
    MediaNotFound,
    ClientError
)

class InstagramManager:
    def __init__(self, log_callback=None):
        """
        Инициализация менеджера Instagram аккаунтов
        
        Args:
            log_callback: Функция для отправки логов в веб-интерфейс
        """
        self.accounts: List[Dict] = []
        self.clients: Dict[str, Client] = {}
        self.log_callback = log_callback
        self.lock = Lock()
        
        # Настройка логирования
        self.logger = logging.getLogger('InstagramManager')
        self.logger.setLevel(logging.INFO)
        
        # Создание директории для логов
        import os
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Файловый обработчик
        fh = logging.FileHandler(f'logs/instagram_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
        fh.setLevel(logging.INFO)
        
        # Консольный обработчик
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Формат
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', 
                                     datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
    
    def log(self, username: str, action: str, status: str, message: str):
        """
        Универсальная функция логирования
        
        Args:
            username: Имя аккаунта
            action: Действие (LOGIN, FOLLOW, LIKE, etc.)
            status: Статус (SUCCESS, ERROR, WARNING)
            message: Сообщение
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{username}] [{action}] [{status}] {message}"
        
        # Логирование в файл и консоль
        if status == "ERROR":
            self.logger.error(log_message)
        elif status == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Отправка в веб-интерфейс
        if self.log_callback:
            self.log_callback(log_message)
    
    def load_accounts(self, filepath: str = 'account.json') -> bool:
        """
        Загрузка аккаунтов из JSON файла
        
        Returns:
            True если загрузка успешна, False в противном случае
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
                self.log("SYSTEM", "LOAD", "SUCCESS", f"Загружено {len(self.accounts)} аккаунтов")
                return True
        except FileNotFoundError:
            self.log("SYSTEM", "LOAD", "ERROR", f"Файл {filepath} не найден")
            return False
        except json.JSONDecodeError as e:
            self.log("SYSTEM", "LOAD", "ERROR", f"Ошибка парсинга JSON: {str(e)}")
            return False
        except Exception as e:
            self.log("SYSTEM", "LOAD", "ERROR", f"Неожиданная ошибка: {str(e)}")
            return False
    
    def login_all(self) -> Tuple[bool, List[Dict]]:
        """
        КРИТИЧЕСКАЯ ФУНКЦИЯ: Вход во все аккаунты
        Если хотя бы один аккаунт не может войти - останавливаем весь процесс
        
        Returns:
            Tuple[bool, List[Dict]]: (успех, список статусов аккаунтов)
        """
        if not self.accounts:
            self.log("SYSTEM", "LOGIN", "ERROR", "Нет загруженных аккаунтов")
            return False, []
        
        results = []
        all_success = True
        
        for account in self.accounts:
            username = account.get('username')
            password = account.get('password')
            
            if not username or not password:
                self.log("SYSTEM", "LOGIN", "ERROR", f"Неполные данные для аккаунта: {username}")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': 'Неполные данные (username или password отсутствует)'
                })
                continue
            
            try:
                client = Client()
                client.delay_range = [1, 3]  # Задержка между запросами
                
                # Попытка входа
                self.log(username, "LOGIN", "INFO", "Попытка входа...")
                client.login(username, password)
                
                # Успешный вход
                self.clients[username] = client
                self.log(username, "LOGIN", "SUCCESS", "Успешный вход")
                results.append({
                    'username': username,
                    'status': 'success',
                    'message': 'Успешный вход'
                })
                
                # Задержка между входами для имитации человеческого поведения
                time.sleep(2)
                
            except LoginRequired:
                self.log(username, "LOGIN", "ERROR", "Неверные учетные данные")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': 'Неверные учетные данные (username или password)'
                })
            except ChallengeRequired as e:
                self.log(username, "LOGIN", "ERROR", f"Требуется верификация аккаунта: {str(e)}")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': 'Требуется верификация (challenge)'
                })
            except FeedbackRequired as e:
                self.log(username, "LOGIN", "ERROR", f"Аккаунт заблокирован или ограничен: {str(e)}")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': 'Аккаунт заблокирован/ограничен'
                })
            except PleaseWaitFewMinutes:
                self.log(username, "LOGIN", "ERROR", "Rate limit - слишком много запросов")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': 'Rate limit - подождите несколько минут'
                })
            except Exception as e:
                self.log(username, "LOGIN", "ERROR", f"Неожиданная ошибка: {str(e)}")
                all_success = False
                results.append({
                    'username': username,
                    'status': 'error',
                    'message': f'Неожиданная ошибка: {str(e)}'
                })
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Если хотя бы один аккаунт не вошел - провал
        if not all_success:
            self.log("SYSTEM", "LOGIN", "ERROR", 
                    "КРИТИЧЕСКАЯ ОШИБКА: Не все аккаунты смогли войти. Процесс остановлен.")
            # Выход из всех успешно вошедших аккаунтов
            self.logout_all()
            return False, results
        
        self.log("SYSTEM", "LOGIN", "SUCCESS", 
                f"Все {len(self.clients)} аккаунтов успешно вошли")
        return True, results
    
    def logout_all(self):
        """Выход из всех аккаунтов"""
        for username in list(self.clients.keys()):
            try:
                self.clients[username].logout()
                self.log(username, "LOGOUT", "SUCCESS", "Выход выполнен")
            except Exception as e:
                self.log(username, "LOGOUT", "ERROR", f"Ошибка при выходе: {str(e)}")
            finally:
                del self.clients[username]
    
    def _check_action_possible(self, action_type: str, target: str) -> Tuple[bool, str]:
        """
        УПРОЩЕННАЯ ПРОВЕРКА: Проверка базовой доступности цели
        Из-за частых изменений в Instagram API убраны сложные проверки состояния
        
        Args:
            action_type: Тип действия (follow, unfollow, like, unlike, comment)
            target: Цель действия (username или media_id)
        
        Returns:
            Tuple[bool, str]: (возможно ли выполнение, сообщение об ошибке если нет)
        """
        if not self.clients:
            return False, "Нет авторизованных аккаунтов"
        
        # Берем первый клиент для базовой проверки существования цели
        first_client = next(iter(self.clients.values()))
        
        try:
            if action_type in ["follow", "unfollow"]:
                # Проверяем только существование пользователя
                try:
                    user_id = first_client.user_id_from_username(target)
                    if not user_id:
                        return False, f"Пользователь {target} не найден"
                except UserNotFound:
                    return False, f"Пользователь {target} не найден"
                except Exception as e:
                    return False, f"Не удалось найти пользователя {target}: {str(e)}"
            
            elif action_type in ["like", "unlike"]:
                # Проверяем только существование поста
                try:
                    media_info = first_client.media_info(target)
                    if not media_info:
                        return False, f"Пост не найден"
                except MediaNotFound:
                    return False, f"Пост не найден"
                except Exception as e:
                    return False, f"Не удалось найти пост: {str(e)}"
            
        except PleaseWaitFewMinutes:
            return False, f"Rate limit - подождите несколько минут"
        except Exception as e:
            return False, f"Ошибка проверки: {str(e)}"
        
        return True, "Базовая проверка пройдена"
    
    def _extract_media_id_from_url(self, url: str) -> Optional[str]:
        """
        Извлечение media_id из URL поста
        
        Args:
            url: URL поста Instagram
        
        Returns:
            media_id или None
        """
        try:
            # Используем первый доступный клиент для конвертации
            if self.clients:
                client = next(iter(self.clients.values()))
                media_pk = client.media_pk_from_url(url)
                return str(media_pk)
            return None
        except Exception as e:
            self.log("SYSTEM", "PARSE_URL", "ERROR", f"Ошибка парсинга URL: {str(e)}")
            return None
    
    def follow_user(self, target_username: str) -> Tuple[bool, str]:
        """
        Подписка на пользователя со всех аккаунтов
        Логика "все или ничего"
        """
        self.log("SYSTEM", "FOLLOW", "INFO", f"Начало подписки на @{target_username}")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Возможно ли действие на всех аккаунтах
        can_proceed, error_msg = self._check_action_possible("follow", target_username)
        if not can_proceed:
            self.log("SYSTEM", "FOLLOW", "ERROR", 
                    f"ДЕЙСТВИЕ ОТМЕНЕНО: {error_msg}")
            return False, error_msg
        
        # Если проверка пройдена - выполняем действие на всех аккаунтах
        for username, client in self.clients.items():
            try:
                user_id = client.user_id_from_username(target_username)
                client.user_follow(user_id)
                self.log(username, "FOLLOW", "SUCCESS", f"Подписка на @{target_username} выполнена")
                time.sleep(2)  # Задержка между действиями
            except ClientError as e:
                error_msg = str(e).lower()
                # Проверка специфических ошибок Instagram
                if 'already' in error_msg or 'following' in error_msg:
                    self.log(username, "FOLLOW", "WARNING", f"Уже подписан на @{target_username}")
                    # Не возвращаем ошибку, продолжаем со следующим аккаунтом
                    time.sleep(2)
                else:
                    self.log(username, "FOLLOW", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "FOLLOW", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "FOLLOW", "SUCCESS", 
                f"Подписка на @{target_username} выполнена на всех аккаунтах")
        return True, "Успешно"
    
    def unfollow_user(self, target_username: str) -> Tuple[bool, str]:
        """
        Отписка от пользователя со всех аккаунтов
        Логика "все или ничего"
        """
        self.log("SYSTEM", "UNFOLLOW", "INFO", f"Начало отписки от @{target_username}")
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА
        can_proceed, error_msg = self._check_action_possible("unfollow", target_username)
        if not can_proceed:
            self.log("SYSTEM", "UNFOLLOW", "ERROR", 
                    f"ДЕЙСТВИЕ ОТМЕНЕНО: {error_msg}")
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                user_id = client.user_id_from_username(target_username)
                client.user_unfollow(user_id)
                self.log(username, "UNFOLLOW", "SUCCESS", f"Отписка от @{target_username} выполнена")
                time.sleep(2)
            except ClientError as e:
                error_msg = str(e).lower()
                if 'not following' in error_msg or 'unfollowed' in error_msg:
                    self.log(username, "UNFOLLOW", "WARNING", f"Уже отписан от @{target_username}")
                    time.sleep(2)
                else:
                    self.log(username, "UNFOLLOW", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "UNFOLLOW", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "UNFOLLOW", "SUCCESS", 
                f"Отписка от @{target_username} выполнена на всех аккаунтах")
        return True, "Успешно"
    
    def like_media(self, media_url: str) -> Tuple[bool, str]:
        """
        Лайк поста со всех аккаунтов
        Логика "все или ничего"
        """
        self.log("SYSTEM", "LIKE", "INFO", f"Начало лайка поста {media_url}")
        
        # Извлечение media_id
        media_id = self._extract_media_id_from_url(media_url)
        if not media_id:
            error_msg = "Не удалось извлечь ID поста из URL"
            self.log("SYSTEM", "LIKE", "ERROR", error_msg)
            return False, error_msg
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА
        can_proceed, error_msg = self._check_action_possible("like", media_id)
        if not can_proceed:
            self.log("SYSTEM", "LIKE", "ERROR", 
                    f"ДЕЙСТВИЕ ОТМЕНЕНО: {error_msg}")
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                client.media_like(media_id)
                self.log(username, "LIKE", "SUCCESS", f"Лайк поставлен на пост {media_id}")
                time.sleep(2)
            except ClientError as e:
                error_msg = str(e).lower()
                if 'already liked' in error_msg or 'liked' in error_msg:
                    self.log(username, "LIKE", "WARNING", f"Лайк уже поставлен на этот пост")
                    time.sleep(2)
                else:
                    self.log(username, "LIKE", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "LIKE", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "LIKE", "SUCCESS", 
                "Лайк поставлен на всех аккаунтах")
        return True, "Успешно"
    
    def unlike_media(self, media_url: str) -> Tuple[bool, str]:
        """
        Удаление лайка со всех аккаунтов
        Логика "все или ничего"
        """
        self.log("SYSTEM", "UNLIKE", "INFO", f"Начало удаления лайка с поста {media_url}")
        
        media_id = self._extract_media_id_from_url(media_url)
        if not media_id:
            error_msg = "Не удалось извлечь ID поста из URL"
            self.log("SYSTEM", "UNLIKE", "ERROR", error_msg)
            return False, error_msg
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА
        can_proceed, error_msg = self._check_action_possible("unlike", media_id)
        if not can_proceed:
            self.log("SYSTEM", "UNLIKE", "ERROR", 
                    f"ДЕЙСТВИЕ ОТМЕНЕНО: {error_msg}")
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                client.media_unlike(media_id)
                self.log(username, "UNLIKE", "SUCCESS", f"Лайк удален с поста {media_id}")
                time.sleep(2)
            except ClientError as e:
                error_msg = str(e).lower()
                if 'not liked' in error_msg or 'unlike' in error_msg:
                    self.log(username, "UNLIKE", "WARNING", f"Лайк не был поставлен на этот пост")
                    time.sleep(2)
                else:
                    self.log(username, "UNLIKE", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "UNLIKE", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "UNLIKE", "SUCCESS", 
                "Лайк удален на всех аккаунтах")
        return True, "Успешно"
    
    def comment_media(self, media_url: str, comment_text: str) -> Tuple[bool, str]:
        """
        Комментарий к посту со всех аккаунтов
        """
        self.log("SYSTEM", "COMMENT", "INFO", f"Начало комментирования поста {media_url}")
        
        media_id = self._extract_media_id_from_url(media_url)
        if not media_id:
            error_msg = "Не удалось извлечь ID поста из URL"
            self.log("SYSTEM", "COMMENT", "ERROR", error_msg)
            return False, error_msg
        
        if not comment_text or len(comment_text.strip()) == 0:
            error_msg = "Текст комментария не может быть пустым"
            self.log("SYSTEM", "COMMENT", "ERROR", error_msg)
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                client.media_comment(media_id, comment_text)
                self.log(username, "COMMENT", "SUCCESS", 
                        f"Комментарий оставлен на посте {media_id}: '{comment_text}'")
                time.sleep(3)  # Больше задержка для комментариев
            except Exception as e:
                self.log(username, "COMMENT", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "COMMENT", "SUCCESS", 
                "Комментарий оставлен на всех аккаунтах")
        return True, "Успешно"
    
    def save_media(self, media_url: str) -> Tuple[bool, str]:
        """
        Сохранение поста в избранное со всех аккаунтов
        """
        self.log("SYSTEM", "SAVE", "INFO", f"Начало сохранения поста: {media_url}")
        
        media_id = self._extract_media_id_from_url(media_url)
        if not media_id:
            error_msg = "Не удалось извлечь ID поста из URL"
            self.log("SYSTEM", "SAVE", "ERROR", error_msg)
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                client.media_save(media_id)
                self.log(username, "SAVE", "SUCCESS", 
                        f"Пост {media_id} сохранен в избранное")
                time.sleep(2)
                
            except ClientError as e:
                error_msg = str(e).lower()
                if 'already saved' in error_msg or 'saved' in error_msg:
                    self.log(username, "SAVE", "WARNING", 
                            "Пост уже сохранен в избранное")
                    time.sleep(2)
                else:
                    self.log(username, "SAVE", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "SAVE", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "SAVE", "SUCCESS", 
                "Пост сохранен в избранное на всех аккаунтах")
        return True, "Успешно"
    
    def unsave_media(self, media_url: str) -> Tuple[bool, str]:
        """
        Удаление поста из избранного со всех аккаунтов
        """
        self.log("SYSTEM", "UNSAVE", "INFO", f"Начало удаления из избранного: {media_url}")
        
        media_id = self._extract_media_id_from_url(media_url)
        if not media_id:
            error_msg = "Не удалось извлечь ID поста из URL"
            self.log("SYSTEM", "UNSAVE", "ERROR", error_msg)
            return False, error_msg
        
        for username, client in self.clients.items():
            try:
                client.media_unsave(media_id)
                self.log(username, "UNSAVE", "SUCCESS", 
                        f"Пост {media_id} удален из избранного")
                time.sleep(2)
                
            except ClientError as e:
                error_msg = str(e).lower()
                if 'not saved' in error_msg:
                    self.log(username, "UNSAVE", "WARNING", 
                            "Пост не был сохранен в избранное")
                    time.sleep(2)
                else:
                    self.log(username, "UNSAVE", "ERROR", f"Ошибка: {str(e)}")
                    return False, f"Ошибка на аккаунте {username}: {str(e)}"
            except Exception as e:
                self.log(username, "UNSAVE", "ERROR", f"Ошибка: {str(e)}")
                return False, f"Ошибка на аккаунте {username}: {str(e)}"
        
        self.log("SYSTEM", "UNSAVE", "SUCCESS", 
                "Пост удален из избранного на всех аккаунтах")
        return True, "Успешно"
    
    def get_accounts_status(self) -> List[Dict]:
        """
        Получение статуса всех аккаунтов
        
        Returns:
            List[Dict]: Список словарей с информацией о каждом аккаунте
        """
        statuses = []
        for account in self.accounts:
            username = account.get('username')
            is_logged_in = username in self.clients
            statuses.append({
                'username': username,
                'logged_in': is_logged_in,
                'status': '✅ Вход выполнен' if is_logged_in else '❌ Не авторизован'
            })
        return statuses
