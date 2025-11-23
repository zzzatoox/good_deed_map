/**
 * Автодополнение адреса через Yandex Maps JavaScript API
 *
 * Этот скрипт загружает Yandex Maps JS API на страницу (если он ещё
 * не загружен) и инициализирует подсказки для полей адреса.
 */

// Проверяем наличие API ключа
const YANDEX_API_KEY = window.YANDEX_MAPS_API_KEY;
let ymapsLoaded = false;
let ymapsLoadPromise = null;

// Загружаем Yandex Maps API
function loadYandexMapsAPI() {
    if (ymapsLoadPromise) {
        return ymapsLoadPromise;
    }
    
    ymapsLoadPromise = new Promise((resolve, reject) => {
        if (typeof ymaps !== 'undefined' && ymaps.ready) {
            ymapsLoaded = true;
            resolve();
            return;
        }
        
        if (!YANDEX_API_KEY) {
            console.error('Yandex Maps API key not found');
            reject(new Error('API key not configured'));
            return;
        }
        
        const script = document.createElement('script');
        script.src = `https://api-maps.yandex.ru/2.1/?apikey=${YANDEX_API_KEY}&lang=ru_RU`;
        script.onload = () => {
            ymaps.ready(() => {
                ymapsLoaded = true;
                resolve();
            });
        };
        script.onerror = () => reject(new Error('Failed to load Yandex Maps API'));
        document.head.appendChild(script);
    });
    
    return ymapsLoadPromise;
}

// Запускаем после полной загрузки DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAutocomplete);
} else {
    initAutocomplete();
}

function initAutocomplete() {
    console.log('Address autocomplete initializing...');
    
    // Загружаем API
    loadYandexMapsAPI()
        .then(() => {
            // Ищем поля адреса
            const addressFields = document.querySelectorAll(
                'textarea[name="address"],' +
                'textarea[id*="address"],' +
                'textarea[id="id_address"],' +
                '#id_address'
            );
            
            console.log('Found address fields:', addressFields.length);
            
            addressFields.forEach(function(addressField) {
                console.log('Initializing autocomplete for:', addressField);
                initAddressAutocomplete(addressField);
            });
        })
        .catch(error => {
            console.error('Failed to initialize address autocomplete:', error);
        });
}

function initAddressAutocomplete(addressField) {
    // Проверяем, что поле еще не инициализировано
    if (addressField.dataset.autocompleteInitialized) {
        console.log('Autocomplete already initialized for this field');
        return;
    }
    addressField.dataset.autocompleteInitialized = 'true';
    
    // Создаём контейнер для подсказок
    const suggestContainer = document.createElement('div');
    suggestContainer.className = 'address-suggest-container';
    
    // Вставляем контейнер после поля
    const parent = addressField.parentNode;
    parent.style.position = 'relative';
    parent.appendChild(suggestContainer);
    
    let suggestTimeout;
    let currentSuggests = [];
    
    // Обновляем ширину при изменении размера окна
    function updateWidth() {
        suggestContainer.style.width = addressField.offsetWidth + 'px';
    }
    updateWidth();
    window.addEventListener('resize', updateWidth);
    
    // Обработчик ввода
    addressField.addEventListener('input', function() {
        const query = this.value.trim();
        
        console.log('Input event, query:', query);
        
        clearTimeout(suggestTimeout);
        
        if (query.length < 3) {
            suggestContainer.style.display = 'none';
            return;
        }
        
        // Задержка перед запросом
        suggestTimeout = setTimeout(() => {
            fetchSuggestions(query);
        }, 500);
    });
    
    // Используем ymaps.geocode для поиска адресов
    function fetchSuggestions(query) {
        console.log('Fetching suggestions for:', query);
        
        ymaps.geocode(query, {
            results: 7,
            boundedBy: [[55.142220, 36.803260], [56.021340, 37.967800]], // Примерно Москва и область
            strictBounds: false
        }).then(function(res) {
            const geoObjects = res.geoObjects;
            const results = [];
            
            geoObjects.each(function(obj) {
                const address = obj.getAddressLine();
                const name = obj.properties.get('name');
                const description = obj.properties.get('description');
                
                results.push({
                    address: address,
                    name: name || address,
                    description: description || ''
                });
            });
            
            console.log('Suggestions:', results);
            displaySuggestions(results);
        }).catch(function(error) {
            console.error('Error fetching suggestions:', error);
            suggestContainer.style.display = 'none';
        });
    }
    
    // Отображение подсказок
    function displaySuggestions(suggestions) {
        if (suggestions.length === 0) {
            suggestContainer.style.display = 'none';
            return;
        }
        
        suggestContainer.innerHTML = '';
        
        suggestions.forEach((suggest, index) => {
            const item = document.createElement('div');
            item.className = 'suggest-item';
            
            item.innerHTML = `
                <div style="font-weight: 500; color: #333;">${escapeHtml(suggest.name)}</div>
                ${suggest.description ? `<div style="font-size: 0.85em; color: #666;">${escapeHtml(suggest.description)}</div>` : ''}
            `;
            
            // Hover эффект
            item.addEventListener('mouseenter', function() {
                this.style.backgroundColor = document.documentElement.classList.contains('dark') ? '#4b5563' : '#f5f5f5';
            });
            
            item.addEventListener('mouseleave', function() {
                this.style.backgroundColor = document.documentElement.classList.contains('dark') ? '#374151' : 'white';
            });
            
            // Клик по подсказке
            item.addEventListener('click', function() {
                addressField.value = suggest.address;
                suggestContainer.style.display = 'none';

                // Запрашиваем координаты и заполняем скрытые поля
                geocodeAndFillCoords(suggest.address).catch(err => {
                    console.warn('Geocode failed on suggest click:', err);
                });

                // Триггерим событие change для других обработчиков
                addressField.dispatchEvent(new Event('change', { bubbles: true }));
                addressField.dispatchEvent(new Event('input', { bubbles: true }));
            });
            
            suggestContainer.appendChild(item);
        });
        
        suggestContainer.style.display = 'block';
        console.log('Suggestions displayed');
    }
    
    // Закрытие при клике вне
    document.addEventListener('click', function(e) {
        if (!addressField.contains(e.target) && !suggestContainer.contains(e.target)) {
            suggestContainer.style.display = 'none';
        }
    });
    
    // Закрытие при нажатии Escape
    addressField.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            suggestContainer.style.display = 'none';
        }
    });

    // При отправке формы: если широта/долгота пусты, попробуем геокодировать адрес
    const form = addressField.closest('form') || document.getElementById('ngo-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            const latEl = findLatEl();
            const lonEl = findLonEl();
            const latEmpty = !latEl || latEl.value === '' || latEl.value === 'None' || latEl.value === 'null';
            const lonEmpty = !lonEl || lonEl.value === '' || lonEl.value === 'None' || lonEl.value === 'null';

            if ((latEmpty || lonEmpty) && addressField.value && addressField.value.trim().length > 0) {
                // Prevent submit until we try to geocode
                e.preventDefault();
                geocodeAndFillCoords(addressField.value)
                    .catch(err => console.warn('Geocode failed on submit:', err))
                    .finally(() => {
                        // Submit the form after attempt (whether success or fail)
                        form.submit();
                    });
            }
        });
    }
    
    console.log('Address autocomplete initialized successfully');
}

// Функция экранирования HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Helper: try to geocode address and fill latitude/longitude inputs
function geocodeAndFillCoords(address) {
    return new Promise((resolve, reject) => {
        if (!ymapsLoaded || typeof ymaps === 'undefined') {
            reject(new Error('ymaps not loaded'));
            return;
        }

        ymaps.geocode(address, { results: 1 }).then(function(res) {
            const first = res.geoObjects.get(0);
            if (!first) {
                reject(new Error('No geocode results'));
                return;
            }
            const coords = first.geometry.getCoordinates(); // [lat, lon]
            if (!coords || coords.length < 2) {
                reject(new Error('Invalid coordinates'));
                return;
            }
            const lat = coords[0];
            const lon = coords[1];
            setLatLonValues(lat, lon);
            resolve({ lat, lon });
        }).catch(err => {
            reject(err);
        });
    });
}

function setLatLonValues(lat, lon) {
    const latEl = findLatEl();
    const lonEl = findLonEl();
    if (latEl) latEl.value = lat;
    if (lonEl) lonEl.value = lon;
}

function findLatEl() {
    return document.getElementById('id_lat') || document.getElementById('id_latitude') || document.querySelector('input[name="latitude"]');
}

function findLonEl() {
    return document.getElementById('id_lon') || document.getElementById('id_longitude') || document.querySelector('input[name="longitude"]');
}
