// dashboard.js - Панель управления

let eventSource = null;

// Подключение к SSE для логов
function connectToLogs() {
    if (eventSource) {
        eventSource.close();
    }

    eventSource = new EventSource('/api/logs');
    
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.log) {
            addLogEntry(data.log);
        }
    };

    eventSource.onerror = function(error) {
        console.error('SSE Error:', error);
        // Переподключение через 5 секунд
        setTimeout(connectToLogs, 5000);
    };
}

// Добавление записи в лог
function addLogEntry(logMessage) {
    const logContainer = document.getElementById('logContainer');
    
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    // Определяем тип лога по содержимому
    if (logMessage.includes('[SUCCESS]')) {
        logEntry.classList.add('success');
    } else if (logMessage.includes('[ERROR]')) {
        logEntry.classList.add('error');
    } else if (logMessage.includes('[WARNING]')) {
        logEntry.classList.add('warning');
    } else if (logMessage.includes('[INFO]')) {
        logEntry.classList.add('info');
    }
    
    logEntry.textContent = logMessage;
    logContainer.appendChild(logEntry);
    
    // Автопрокрутка вниз
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Очистка логов
function clearLogs() {
    const logContainer = document.getElementById('logContainer');
    logContainer.innerHTML = '<div class="text-muted text-center">Логи очищены</div>';
}

// Загрузка статуса аккаунтов
async function loadAccountsStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.success && data.accounts) {
            displayAccounts(data.accounts);
        }
    } catch (error) {
        console.error('Error loading accounts:', error);
    }
}

// Отображение аккаунтов
function displayAccounts(accounts) {
    const accountsList = document.getElementById('accountsList');
    
    if (accounts.length === 0) {
        accountsList.innerHTML = '<div class="text-muted text-center">Нет аккаунтов</div>';
        return;
    }
    
    accountsList.innerHTML = '';
    
    accounts.forEach(account => {
        const accountItem = document.createElement('div');
        accountItem.className = `account-item ${account.logged_in ? 'logged-in' : 'logged-out'}`;
        
        accountItem.innerHTML = `
            <div class="account-username">@${account.username}</div>
            <div class="account-status">${account.logged_in ? '✅' : '❌'}</div>
        `;
        
        accountsList.appendChild(accountItem);
    });
}

// API запросы с обработкой ошибок
async function apiRequest(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message, 'success');
        } else {
            showToast(result.message, 'error');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        showToast('Ошибка подключения к серверу', 'error');
        return { success: false, message: 'Ошибка подключения' };
    }
}

// Подписка на пользователя
async function followUser() {
    const username = document.getElementById('followUsername').value.trim();
    
    if (!username) {
        showToast('Введите username', 'warning');
        return;
    }
    
    await apiRequest('/api/follow', { username });
}

// Отписка от пользователя
async function unfollowUser() {
    const username = document.getElementById('followUsername').value.trim();
    
    if (!username) {
        showToast('Введите username', 'warning');
        return;
    }
    
    await apiRequest('/api/unfollow', { username });
}

// Лайк поста
async function likePost() {
    const url = document.getElementById('likeUrl').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    await apiRequest('/api/like', { url });
}

// Удаление лайка
async function unlikePost() {
    const url = document.getElementById('likeUrl').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    await apiRequest('/api/unlike', { url });
}

// Обычный комментарий (одинаковый текст)
async function commentPost() {
    const url = document.getElementById('commentUrl').value.trim();
    const comment = document.getElementById('commentText').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    if (!comment) {
        showToast('Введите текст комментария', 'warning');
        return;
    }
    
    await apiRequest('/api/comment', { url, comment });
}

// AI-комментарий (уникальный текст для каждого аккаунта)
async function commentPostAI() {
    const url = document.getElementById('commentUrl').value.trim();
    const comment = document.getElementById('commentText').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    if (!comment) {
        showToast('Введите базовый текст комментария', 'warning');
        return;
    }
    
    await apiRequest('/api/comment-ai', { url, comment });
}

// Сохранение поста
async function savePost() {
    const url = document.getElementById('saveUrl').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    await apiRequest('/api/save', { url });
}

// Удаление поста из избранного
async function unsavePost() {
    const url = document.getElementById('saveUrl').value.trim();
    
    if (!url) {
        showToast('Введите URL поста', 'warning');
        return;
    }
    
    await apiRequest('/api/unsave', { url });
}

// Показ toast уведомлений
function showToast(message, type = 'info') {
    // Создаем toast элемент
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'warning'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
    bsToast.show();
    
    // Удаление элемента после скрытия
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Создание контейнера для toast
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Подключение к логам
    connectToLogs();
    
    // Загрузка статуса аккаунтов
    loadAccountsStatus();
    
    // Обновление статуса каждые 30 секунд
    setInterval(loadAccountsStatus, 30000);
    
    // Проверка инициализации
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (!data.initialized) {
                // Если не инициализировано, перенаправляем на главную
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error('Error checking status:', error);
        });
});

// Закрытие SSE при уходе со страницы
window.addEventListener('beforeunload', function() {
    if (eventSource) {
        eventSource.close();
    }
});

// Обработка Enter в полях ввода
document.addEventListener('DOMContentLoaded', function() {
    // Follow/Unfollow
    const followInput = document.getElementById('followUsername');
    if (followInput) {
        followInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                followUser();
            }
        });
    }
    
    // Like/Unlike
    const likeInput = document.getElementById('likeUrl');
    if (likeInput) {
        likeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                likePost();
            }
        });
    }
    
    // Save/Unsave
    const saveInput = document.getElementById('saveUrl');
    if (saveInput) {
        saveInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                savePost();
            }
        });
    }
});
