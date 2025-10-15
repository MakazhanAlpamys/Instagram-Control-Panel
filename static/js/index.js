// index.js - Страница инициализации

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
            checkForSuccessfulInit(data.log);
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
    
    // Очищаем placeholder если есть
    if (logContainer.querySelector('.text-muted')) {
        logContainer.innerHTML = '';
    }

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

// Проверка на успешную инициализацию
function checkForSuccessfulInit(logMessage) {
    if (logMessage.includes('Приложение готово к работе')) {
        setTimeout(() => {
            showSuccessAlert('Система успешно инициализирована! Переход на панель управления...');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);
        }, 1000);
    } else if (logMessage.includes('Приложение НЕ может работать')) {
        setTimeout(() => {
            showErrorAlert('Критическая ошибка инициализации. Проверьте логи выше и исправьте ошибки в account.json');
            enableInitButton();
        }, 1000);
    }
}

// Инициализация системы
async function initializeSystem() {
    const button = document.getElementById('initButton');
    const buttonText = document.getElementById('initButtonText');
    const buttonSpinner = document.getElementById('initButtonSpinner');
    
    // Отключаем кнопку
    button.disabled = true;
    buttonText.textContent = 'Инициализация...';
    buttonSpinner.classList.remove('d-none');
    
    try {
        const response = await fetch('/api/init', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showInfoAlert(data.message);
        } else {
            showErrorAlert(data.message);
            enableInitButton();
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorAlert('Ошибка подключения к серверу');
        enableInitButton();
    }
}

// Включение кнопки инициализации
function enableInitButton() {
    const button = document.getElementById('initButton');
    const buttonText = document.getElementById('initButtonText');
    const buttonSpinner = document.getElementById('initButtonSpinner');
    
    button.disabled = false;
    buttonText.textContent = 'Инициализировать систему';
    buttonSpinner.classList.add('d-none');
}

// Показ алертов
function showSuccessAlert(message) {
    showAlert(message, 'success');
}

function showErrorAlert(message) {
    showAlert(message, 'danger');
}

function showInfoAlert(message) {
    showAlert(message, 'info');
}

function showAlert(message, type) {
    const alertDiv = document.getElementById('statusAlert');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.classList.remove('d-none');
    
    // Скрыть через 10 секунд для info/success
    if (type === 'info' || type === 'success') {
        setTimeout(() => {
            alertDiv.classList.add('d-none');
        }, 10000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    connectToLogs();
    
    // Проверяем статус системы
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.initialized) {
                // Если уже инициализировано, перенаправляем на dashboard
                window.location.href = '/dashboard';
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
