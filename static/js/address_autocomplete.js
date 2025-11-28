/**
 * Автодополнение адреса через Yandex Maps JavaScript API
 *
 * Этот скрипт загружает Yandex Maps JS API на страницу (если он ещё
 * не загружен) и инициализирует подсказки для полей адреса.
 */

// Проверяем наличие API ключа
// Silence noisy logging from this script in production
try { if (typeof window !== 'undefined' && window.console) { window.console.log = function(){}; window.console.debug = function(){}; window.console.info = function(){}; window.console.warn = function(){}; window.console.error = function(){}; } } catch(e) {}
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

        // If a Yandex Maps <script> tag is already present on the page, wait for it
        const existing = Array.from(document.getElementsByTagName('script')).find(s => s.src && s.src.indexOf('api-maps.yandex.ru/2.1') !== -1);
        if (existing) {
            const onLoaded = () => {
                if (typeof ymaps !== 'undefined' && ymaps.ready) {
                    ymaps.ready(() => {
                        ymapsLoaded = true;
                        resolve();
                    });
                } else {
                    // If script already loaded but ymaps not ready, poll briefly
                    const t = setInterval(() => {
                        if (typeof ymaps !== 'undefined' && ymaps.ready) {
                            clearInterval(t);
                            ymaps.ready(() => {
                                ymapsLoaded = true;
                                resolve();
                            });
                        }
                    }, 150);
                    // safety timeout
                    setTimeout(() => { clearInterval(t); reject(new Error('ymaps did not become ready')); }, 8000);
                }
            };

            if (existing.readyState === 'complete' || existing.readyState === 'loaded') {
                // script already finished loading - attempt to attach
                onLoaded();
            } else {
                existing.addEventListener('load', onLoaded);
                existing.addEventListener('error', () => reject(new Error('Failed to load existing Yandex Maps script')));
            }
            return;
        }

        // No existing script found - inject one if we have an API key
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
}

function initAddressAutocomplete(addressField) {
    // Проверяем, что поле еще не инициализировано
    if (addressField.dataset.autocompleteInitialized) {
        console.log('Autocomplete already initialized for this field');
        return;
    }
    addressField.dataset.autocompleteInitialized = 'true';
    
    // Создаём контейнер для подсказок и добавляем в document.body
    const suggestContainer = document.createElement('div');
    suggestContainer.className = 'address-suggest-container';
    // Append to body so it won't be clipped by parent overflow and can position freely
    document.body.appendChild(suggestContainer);

    let suggestTimeout;
    let currentSuggests = [];
    let geocodeTimer = null;
    let lastGeocodedQuery = null;

    // Position and size the suggestion container to match the input
    function repositionSuggestContainer() {
        try {
            const rect = addressField.getBoundingClientRect();
            // For fixed-positioned container we should use viewport coordinates (no scroll offsets)
            let left = rect.left;
            let top = rect.bottom + 6; // small gap below the input
            let width = rect.width || addressField.offsetWidth || 220;

            // If the input is hidden or not yet laid out, rect.width can be 0.
            // Retry a few times with small delay to wait for layout (useful inside modals).
            if ((width || 0) < 8) {
                suggestContainer._repositionRetries = (suggestContainer._repositionRetries || 0) + 1;
                if (suggestContainer._repositionRetries <= 6) {
                    setTimeout(repositionSuggestContainer, 80);
                    return;
                }
                // fallback to computed styles
                const cs = window.getComputedStyle(addressField);
                const pw = parseFloat(cs.width) || addressField.offsetWidth || 220;
                width = pw;
            }

            // Ensure width isn't too small
            width = Math.max(width, 220);

            suggestContainer.style.left = Math.round(left) + 'px';
            suggestContainer.style.top = Math.round(top) + 'px';
            suggestContainer.style.width = Math.round(width) + 'px';
            // reset retry counter on success
            suggestContainer._repositionRetries = 0;
        } catch (e) {
            // fallback: ensure visible with some defaults
            suggestContainer.style.left = '0px';
            suggestContainer.style.top = '0px';
            suggestContainer.style.width = '220px';
        }
    }

    // Reposition on resize/scroll and when input moves
    const repositionHandler = () => repositionSuggestContainer();
    window.addEventListener('resize', repositionHandler);
    window.addEventListener('scroll', repositionHandler, true);
    // Also reposition on focus (in case element became visible)
    addressField.addEventListener('focus', repositionHandler);
    // Initial position
    repositionSuggestContainer();

    // Watch for input becoming hidden/removed (e.g. modal closed) and hide suggestions
    let _visibilityWatcher = null;
    function startVisibilityWatcher() {
        if (_visibilityWatcher) return;
        _visibilityWatcher = setInterval(() => {
            try {
                // If not displayed or input not in DOM or not visible, hide the suggestions
                const inputConnected = document.body.contains(addressField);
                const rects = addressField.getClientRects();
                const visible = inputConnected && rects && rects.length > 0 && addressField.offsetParent !== null;
                if (!visible && suggestContainer.style.display === 'block') {
                    suggestContainer.style.display = 'none';
                }
            } catch (e) {
                // if input removed unexpectedly, hide container
                if (suggestContainer.style.display === 'block') suggestContainer.style.display = 'none';
            }
        }, 200);
    }
    startVisibilityWatcher();
    
    // Обработчик ввода
    addressField.addEventListener('input', function() {
        const query = this.value.trim();

        // clear suggestion timer
        clearTimeout(suggestTimeout);
        // clear geocode timer
        if (geocodeTimer) { clearTimeout(geocodeTimer); geocodeTimer = null; }

        if (query.length < 3) {
            suggestContainer.style.display = 'none';
            return;
        }

        // Задержка перед запросом подсказок
        suggestTimeout = setTimeout(() => {
            fetchSuggestions(query);
        }, 500);

        // Запланировать геокодирование после паузы ввода (если пользователь не выбрал подсказку)
        geocodeTimer = setTimeout(() => {
            // don't geocode if it's the same string we've already geocoded
            if (!query || query.length < 3) return;
            if (lastGeocodedQuery && lastGeocodedQuery === query) return;
            lastGeocodedQuery = query;
            // best-effort geocode to update mini-map
            geocodeAndFillCoords(query).catch(() => {});
        }, 1000);
    });

    // On blur, try to geocode immediately (user left field without selecting suggestion)
    addressField.addEventListener('blur', function() {
        const query = this.value.trim();
        if (!query || query.length < 3) return;
        if (geocodeTimer) { clearTimeout(geocodeTimer); geocodeTimer = null; }
        if (lastGeocodedQuery && lastGeocodedQuery === query) return;
        lastGeocodedQuery = query;
        geocodeAndFillCoords(query).catch(() => {});
    });
    
    // Используем Yandex Suggest API для автодополнения адресов
    function fetchSuggestions(query) {
        console.log('Fetching suggestions for:', query);
        
        // Используем YANDEX_MAPS_GEO_API_KEY для Suggest API
        const apiKey = window.YANDEX_MAPS_GEO_API_KEY || '';
        if (!apiKey) {
            console.error('YANDEX_MAPS_GEO_API_KEY not found');
            suggestContainer.style.display = 'none';
            return;
        }

        // Yandex Suggest API URL
        const url = `https://suggest-maps.yandex.ru/v1/suggest?apikey=${encodeURIComponent(apiKey)}&text=${encodeURIComponent(query)}&results=7`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Suggest API failed: ' + response.status);
                }
                return response.json();
            })
            .then(data => {
                const results = [];
                
                if (data.results && Array.isArray(data.results)) {
                    data.results.forEach(item => {
                        // Формируем адрес из title и subtitle
                        const name = item.title && item.title.text ? item.title.text : '';
                        const description = item.subtitle && item.subtitle.text ? item.subtitle.text : '';
                        
                        // Полный адрес - объединяем название и описание
                        let address = name;
                        if (description && description !== name) {
                            address = name + ', ' + description;
                        }
                        
                        results.push({
                            address: address,
                            name: name,
                            description: description
                        });
                    });
                }
                
                console.log('Suggestions:', results);
                displaySuggestions(results);
            })
            .catch(error => {
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
        
        // ensure container is positioned correctly before rendering
        repositionSuggestContainer();
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
        // focus the first item for accessibility? keep for now
        console.log('Suggestions displayed');
    }
    
    // Закрытие при клике вне
    document.addEventListener('click', function(e) {
        if (!addressField.contains(e.target) && !suggestContainer.contains(e.target)) {
            suggestContainer.style.display = 'none';
        }
    });

    // Additionally, if the input is inside a modal, ensure clicks inside the modal
    // (but outside the input or suggestion container) also hide the suggestions.
    try {
        const modalAncestor = addressField.closest('#add-nko-modal, .modal, [role="dialog"]');
        if (modalAncestor) {
            modalAncestor.addEventListener('click', function(e) {
                if (!addressField.contains(e.target) && !suggestContainer.contains(e.target)) {
                    suggestContainer.style.display = 'none';
                }
            });
        }
    } catch (e) {}

    // Also listen for clicks on the modal content itself (empty space inside modal)
    try {
        const modalContent = addressField.closest('#add-nko-content, .modal-content, .modal-body');
        if (modalContent) {
            modalContent.addEventListener('click', function(e) {
                // If the click is not on the input or suggestion container, hide suggestions
                if (!addressField.contains(e.target) && !suggestContainer.contains(e.target)) {
                    suggestContainer.style.display = 'none';
                }
            });
        }
    } catch (e) {}
    
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
// Используем только HTTP Geocoder API, так как ymaps.geocode требует другой тип ключа
function geocodeAndFillCoords(address) {
    return new Promise((resolve, reject) => {
        // Используем HTTP Geocoder API напрямую
        httpGeocode(address).then(resolve).catch(reject);
    });
}

function httpGeocode(address) {
    return new Promise((resolve, reject) => {
        // Используем YANDEX_MAPS_API_KEY (первый ключ) для Geocoder API
        const apiKey = window.YANDEX_MAPS_API_KEY || '';
        if (!apiKey) {
            reject(new Error('No API key for HTTP geocode'));
            return;
        }
        const url = `https://geocode-maps.yandex.ru/1.x/?format=json&results=1&geocode=${encodeURIComponent(address)}&apikey=${encodeURIComponent(apiKey)}`;
        fetch(url).then(r => {
            if (!r.ok) throw new Error('HTTP geocode failed: ' + r.status);
            return r.json();
        }).then(data => {
            try{
                const fm = data && data.response && data.response.GeoObjectCollection && data.response.GeoObjectCollection.featureMember && data.response.GeoObjectCollection.featureMember[0];
                if (!fm) { throw new Error('No featureMember'); }
                const geo = fm.GeoObject;
                // Yandex HTTP geocoder returns Point.pos as "lon lat"
                const pos = (geo && geo.Point && geo.Point.pos) || null;
                if (!pos) throw new Error('No point pos');
                const parts = pos.split(' ');
                if (parts.length < 2) throw new Error('Invalid pos');
                const lon = parseFloat(parts[0]);
                const lat = parseFloat(parts[1]);
                setLatLonValues(lat, lon);
                try{ document.dispatchEvent(new CustomEvent('addressCoordsUpdated', { detail: { lat: lat, lon: lon } })); }catch(e){}
                resolve({ lat, lon });
            }catch(err){ reject(err); }
        }).catch(err => reject(err));
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
