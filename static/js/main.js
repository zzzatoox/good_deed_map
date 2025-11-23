/**
 * main.js - Главный скрипт для страницы с картой НКО
 *
 * Отвечает за:
 * - Инициализацию Яндекс.Карт
 * - Загрузку данных об НКО через API
 * - Отображение меток на карте
 * - Фильтрацию по категориям и городам
 * - Поиск НКО
 * - Взаимодействие с модальным окном
 *
 * Основные функции:
 * - fetchAndInit() - загружает данные и инициализирует карту
 * - initMapAndUI() - создает карту и добавляет метки
 * - attachUIHandlers() - подключает обработчики событий UI
 * - filterPoints() - фильтрует НКО по выбранным критериям
 * - showNkoModal() - отображает модальное окно с информацией об НКО
 */

// ========================================
// Глобальные переменные
// ========================================

let map; // Экземпляр Яндекс.Карты
const INITIAL_MAP_CENTER = [61.524, 105.3188]; // Центр России
const INITIAL_MAP_ZOOM = 3; // Начальный зум

let placemarks = []; // Массив всех меток на карте
let searchControl; // Контрол поиска
let activeCategories = []; // Активные фильтры категорий
let selectedCity = "all"; // Выбранный город
let rawNkoList = []; // Исходный список НКО с сервера
let categoriesMap = {}; // Словарь категорий: {slug: {id, name, icon, color}}

// ========================================
// Инициализация карты
// ========================================

/**
 * Инициализирует Яндекс.Карту и UI элементы
 * @param {Array} pointsData - Массив данных о точках НКО
 */
function initMapAndUI(pointsData) {
  if (typeof ymaps === "undefined") {
    console.error("Yandex Maps API not loaded");
    return;
  }

  ymaps.ready(() => {
    // Создаем экземпляр карты
    map = new ymaps.Map("map", {
      center: INITIAL_MAP_CENTER,
      zoom: INITIAL_MAP_ZOOM,
    });

    // Удаляем ненужные контролы
    map.controls.remove("geolocationControl");
    map.controls.remove("trafficControl");
    map.controls.remove("typeSelector");
    map.controls.remove("fullscreenControl");
    map.controls.remove("rulerControl");
    map.controls.remove("searchControl");

    // Создаем динамические иконки для категорий
    const iconLayouts = {};
    Object.keys(categoriesMap).forEach((slug) => {
      const cat = categoriesMap[slug];
      iconLayouts[slug] = ymaps.templateLayoutFactory.createClass(
        `<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: ${cat.color};">${cat.icon || '❓'}</div>`
      );
    });

    // Добавляем метки на карту
    pointsData.forEach((point) => {
      const placemark = new ymaps.Placemark(point.coords, point.properties, {
        iconLayout: iconLayouts[point.properties.category] || iconLayouts[Object.keys(iconLayouts)[0]],
        iconShape: { type: "Circle", coordinates: [20, 20], radius: 20 },
      });

      // Обработчик клика по метке - открываем модальное окно
      placemark.events.add("click", function () {
        try {
          showNkoModal(point.id);
        } catch (e) {
          console.error("Error opening modal from placemark", e);
        }
      });

      map.geoObjects.add(placemark);
      placemarks.push({
        placemark,
        title: point.title,
        address: point.address,
        categories: point.categorySlugs,
        coords: point.coords,
        city: point.city,
        id: point.id,
      });
    });

    // Подключаем обработчики UI элементов
    attachUIHandlers(pointsData);
  });
}

// ========================================
// Загрузка данных
// ========================================

/**
 * Загружает список НКО из API и инициализирует карту
 */
async function fetchAndInit() {
  try {
    // Загружаем категории
    const categoriesResp = await fetch("/nko/api/categories/");
    if (!categoriesResp.ok) throw new Error("Failed to fetch categories");
    const categories = await categoriesResp.json();
    
    // Создаем словарь категорий по slug
    categories.forEach(cat => {
      // Используем slug из Django или создаем свой
      const slug = cat.slug || slugify(cat.name);
      categoriesMap[slug] = {
        id: cat.id,
        name: cat.name,
        slug: slug,
        icon: cat.icon || '❓',
        color: cat.color || '#6CACE4'
      };
    });

    // Загружаем НКО
    const resp = await fetch("/nko/api/nko-list/");
    if (!resp.ok) throw new Error("Failed to fetch NKO list");
    const list = await resp.json();
    rawNkoList = list;

    // Преобразуем данные в формат для карты
    const pointsData = list
      .filter((nko) => nko.latitude && nko.longitude)
      .map((nko) => {
        const categorySlugs = (nko.categories || []).map(cat => cat.slug).filter(s => s);
        const primaryCategorySlug = categorySlugs[0] || Object.keys(categoriesMap)[0] || 'other';
        
        if (categorySlugs.length === 0) {
          console.warn(`NKO ${nko.id} (${nko.name}) has no categories`);
        }
        
        return {
          id: nko.id,
          coords: [parseFloat(nko.latitude), parseFloat(nko.longitude)],
          properties: {
            hintContent: nko.name,
            balloonContent: `${nko.address || ""}<br>${(nko.categories || []).map(c => c.name).join(", ")}`,
            category: primaryCategorySlug,
          },
          title: nko.name,
          address: nko.address,
          categorySlugs: categorySlugs,
          city: nko.city_id !== undefined && nko.city_id !== null
            ? String(nko.city_id)
            : nko.city_slug || (nko.city || "").toString().toLowerCase().replace(/\s+/g, "-"),
        };
      });

    renderPointsList(pointsData, list);
    initMapAndUI(pointsData);
  } catch (err) {
    console.error("Error initializing map from API:", err);
  }
}

// Вспомогательная функция для создания slug
function slugify(text) {
  const map = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
    'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'ju', 'я': 'ja'
  };
  
  return text.toString().toLowerCase()
    .split('').map(char => map[char] || char).join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function renderPointsList(pointsData, rawList) {
  const container = document.getElementById("points-list");
  if (!container) return;
  container.innerHTML = "";

  pointsData.forEach((p) => {
    const raw = rawList.find((r) => r.id === p.id) || {};
    const categories = raw.categories || [];
    const addr = p.address || "";

    const badgesHtml = categories
      .map(cat => 
        `<span class="text-white text-xs font-medium px-2 py-1 rounded-md" style="background-color: ${cat.color};">${cat.name}</span>`
      )
      .join(" ");

    const item = document.createElement("div");
    item.className =
      "py-5 cursor-pointer hover:bg-white/20 transition-colors point-item rounded-l-lg";
    item.setAttribute("data-id", p.id);
    item.setAttribute("data-coords", JSON.stringify(p.coords));
    item.setAttribute("data-title", p.title || "");
    item.setAttribute("data-address", addr);
    item.setAttribute("data-categories", p.categorySlugs.join(","));
    item.setAttribute("data-city", p.city || "");

    item.innerHTML = `
      <div class="flex justify-between items-start mb-1 pl-4">
        <div class="flex flex-wrap gap-1">
          ${badgesHtml}
        </div>
      </div>
      <h4 class="text-base font-semibold mb-2 text-white dark:text-gray-100 pl-4">${
        p.title || ""
      }</h4>
      <p class="text-sm text-white/80 dark:text-gray-300 mb-3 pl-4">${addr}</p>
      <div class="flex justify-between items-center text-xs text-white/80 dark:text-gray-300 pl-4">
        <span class="text-[#90EE90] font-medium">Открыто</span>
      </div>
    `;

    container.appendChild(item);
  });

  // Обновляем счётчик сразу после рендеринга
  updatePointsCount(pointsData.length);
}

function attachUIHandlers(pointsData) {
  // category filters
  document.querySelectorAll(".category-filter").forEach((category) => {
    category.addEventListener("click", function () {
      const categoryType = this.getAttribute("data-category");
      const isActive = activeCategories.includes(categoryType);
      if (isActive)
        activeCategories = activeCategories.filter(
          (cat) => cat !== categoryType
        );
      else activeCategories.push(categoryType);
      updateCategoryVisualState();
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });
  });

  const citySelect = document.getElementById("city-select");
  if (citySelect) {
    citySelect.addEventListener("change", function () {
      selectedCity = this.value;
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });
  }

  const clearFiltersBtn = document.getElementById("clear-filters");
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", function () {
      activeCategories = [];
      selectedCity = "all";
      const citySelectEl = document.getElementById("city-select");
      if (citySelectEl) citySelectEl.value = "all";
      updateCategoryVisualState();
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
      this.classList.add("hidden");
    });
  }

  document.querySelectorAll(".point-item").forEach((item) => {
    item.addEventListener("click", function () {
      const coords = JSON.parse(this.getAttribute("data-coords"));
      try {
        if (map) map.setCenter(coords, 14, { duration: 500 });
      } catch (e) {}
      document
        .querySelectorAll(".point-item")
        .forEach((el) =>
          el.classList.remove("bg-blue-500/20", "dark:bg-blue-900")
        );
      this.classList.add("bg-blue-500/20", "dark:bg-blue-900");
      const id = this.getAttribute("data-id");
      if (id) showNkoModal(Number(id));
    });
  });

  // search handlers
  function performSearch() {
    const searchInputEl = document.getElementById("search-input");
    if (!searchInputEl) return;
    
    const searchText = searchInputEl.value.trim().toLowerCase();
    if (!searchText) {
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
      return;
    }
    let foundCount = 0;
    let foundCoords = [];
    document.querySelectorAll(".point-item").forEach((item) => {
      const title = item.getAttribute("data-title").toLowerCase();
      const address = item.getAttribute("data-address").toLowerCase();
      const itemCoords = JSON.parse(item.getAttribute("data-coords"));
      const categories = item.getAttribute("data-categories").split(",").filter(c => c);
      const itemCity = item.getAttribute("data-city");
      const itemId = item.getAttribute("data-id");
      const matchesSearch =
        title.includes(searchText) || address.includes(searchText);
      const matchesCategory =
        activeCategories.length === 0 ||
        activeCategories.some((cat) => categories.includes(cat));
      const matchesCity = selectedCity === "all" || itemCity === selectedCity;
      if (matchesSearch && matchesCategory && matchesCity) {
        item.style.display = "block";
        foundCount++;
        foundCoords.push(itemCoords);
        placemarks.forEach((placemarkItem) => {
          if (placemarkItem.id == itemId) {
            placemarkItem.placemark.options.set("visible", true);
          }
        });
      } else {
        item.style.display = "none";
        placemarks.forEach((placemarkItem) => {
          if (placemarkItem.id == itemId) {
            placemarkItem.placemark.options.set("visible", false);
          }
        });
      }
    });
    updatePointsCount(foundCount);
    if (foundCount === 1) map.setCenter(foundCoords[0], 14, { duration: 200 });
    else if (foundCount > 1) {
      const bounds = ymaps.util.bounds.fromPoints(foundCoords);
      if (bounds)
        map.setBounds(bounds, { checkZoomRange: true, duration: 200 });
    }
  }

  const searchInput = document.getElementById("search-input");
  const searchButton = document.getElementById("search-button");
  
  if (searchInput) {
    searchInput.addEventListener("input", performSearch);
    searchInput.addEventListener("keypress", function (e) {
      if (e.key === "Enter") performSearch();
    });
  }
  
  if (searchButton) {
    searchButton.addEventListener("click", performSearch);
  }

  // Обновляем начальный счётчик
  updatePointsCount(pointsData.length);
}

function filterPointsByCategoriesAndCity(categories, city) {
  const pointItems = document.querySelectorAll(".point-item");
  let visibleCount = 0;
  let visibleCoords = [];
  pointItems.forEach((item) => {
    const itemCategories = item.getAttribute("data-categories").split(",").filter(c => c);
    const itemCity = item.getAttribute("data-city");
    const matchesCategory =
      categories.length === 0 ||
      categories.some((cat) => itemCategories.includes(cat));
    const matchesCity = city === "all" || itemCity === city;
    const shouldShow = matchesCategory && matchesCity;
    const coords = JSON.parse(item.getAttribute("data-coords"));
    const itemId = item.getAttribute("data-id");
    
    if (shouldShow) {
      item.style.display = "block";
      visibleCount++;
      visibleCoords.push(coords);
      // Находим соответствующий плейсмарк по ID, а не по координатам
      placemarks.forEach((placemarkItem) => {
        if (placemarkItem.id == itemId) {
          placemarkItem.placemark.options.set("visible", true);
        }
      });
    } else {
      item.style.display = "none";
      placemarks.forEach((placemarkItem) => {
        if (placemarkItem.id == itemId) {
          placemarkItem.placemark.options.set("visible", false);
        }
      });
    }
  });
  updatePointsCount(visibleCount);
  const clearFiltersBtn = document.getElementById("clear-filters");
  if (categories.length > 0 || city !== "all")
    clearFiltersBtn.classList.remove("hidden");
  else clearFiltersBtn.classList.add("hidden");
  updateActiveFiltersDisplay();
  // If user selected "Все города", reset to the initial Russian Federation view
  if (city === "all") {
    if (typeof map !== "undefined" && map) {
      map.setCenter(INITIAL_MAP_CENTER, INITIAL_MAP_ZOOM, { duration: 200 });
    }
    return;
  }

  if (visibleCount > 0) {
    const bounds = ymaps.util.bounds.fromPoints(visibleCoords);
    if (bounds) map.setBounds(bounds, { checkZoomRange: true, duration: 200 });
  }
}

function updateActiveFiltersDisplay() {
  const activeFiltersContainer = document.getElementById("active-filters");
  if (!activeFiltersContainer) return; // Элемент может отсутствовать на странице
  
  const filtersList = activeFiltersContainer.querySelector(".flex");
  if (!filtersList) return;
  
  filtersList.innerHTML = "";
  if (activeCategories.length > 0 || selectedCity !== "all") {
    activeFiltersContainer.classList.remove("hidden");
    if (selectedCity !== "all") {
      const cityFilterChip = document.createElement("div");
      cityFilterChip.className =
        "flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-xs font-medium";

      const citySelect = document.getElementById("city-select");
      let cityDisplay = selectedCity;
      if (citySelect) {
        const opt = citySelect.querySelector(`option[value="${selectedCity}"]`);
        if (opt) cityDisplay = opt.textContent.trim();
      }
      cityFilterChip.innerHTML = `<span>${cityDisplay}</span><button class="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100" data-filter-type="city"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>`;
      filtersList.appendChild(cityFilterChip);
    }
    activeCategories.forEach((categorySlug) => {
      const filterChip = document.createElement("div");
      filterChip.className =
        "flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-xs font-medium";
      const categoryData = categoriesMap[categorySlug] || {};
      const categoryName = categoryData.name || categorySlug;
      filterChip.innerHTML = `<span>${categoryName}</span><button class="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100" data-category="${categorySlug}"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>`;
      filtersList.appendChild(filterChip);
    });
  } else activeFiltersContainer.classList.add("hidden");
  filtersList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", function () {
      const categoryToRemove = this.getAttribute("data-category");
      const filterType = this.getAttribute("data-filter-type");
      if (filterType === "city") {
        document.getElementById("city-select").value = "all";
        selectedCity = "all";
      } else if (categoryToRemove) removeCategoryFilter(categoryToRemove);
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });
  });
}

function removeCategoryFilter(category) {
  activeCategories = activeCategories.filter((cat) => cat !== category);
  updateCategoryVisualState();
}

function updateCategoryVisualState() {
  document.querySelectorAll(".category-filter").forEach((category) => {
    const categoryType = category.getAttribute("data-category");
    const isActive = activeCategories.includes(categoryType);
    
    // Находим цвет категории из data-атрибута
    const categoryColor = category.getAttribute("data-color") || '#6CACE4';
    
    // Устанавливаем CSS переменную для цвета категории
    category.style.setProperty('--category-color', categoryColor);
    
    if (isActive) {
      category.classList.add("active");
    } else {
      category.classList.remove("active");
    }
  });
}

/**
 * Обновляет счётчик найденных точек НКО
 * @param {number} count - Количество точек
 */
function updatePointsCount(count) {
  const pointsCountEl = document.getElementById("points-count");
  if (pointsCountEl) {
    pointsCountEl.textContent = `Найдено ${count} ${getPointsWord(count)}`;
  }
}

function getPointsWord(count) {
  if (count % 10 === 1 && count % 100 !== 11) return "точка НКО";
  else if (
    [2, 3, 4].includes(count % 10) &&
    ![12, 13, 14].includes(count % 100)
  )
    return "точки НКО";
  else return "точек НКО";
}

// Modal logic for NKO details
function showNkoModal(id) {
  const overlay = document.getElementById("nko-modal-overlay");
  const modal = document.getElementById("nko-modal");
  if (!modal || !overlay) return;

  const nko = rawNkoList.find((i) => i.id === id);
  if (!nko) return;

  const logoEl = document.getElementById("nko-modal-logo");
  const titleEl = document.getElementById("nko-modal-title");
  const badgesEl = document.getElementById("nko-modal-badges");
  const descEl = document.getElementById("nko-modal-description");
  const addrEl = document.getElementById("nko-modal-address");
  const phoneEl = document.getElementById("nko-modal-phone");
  const websiteEl = document.getElementById("nko-modal-website");
  const moreEl = document.getElementById("nko-modal-more");

  if (logoEl) {
    // Use NKO logo if available, otherwise fallback to the project's header logo
    const headerLogo = document.querySelector(".logo-light");
    const defaultLogo =
      (headerLogo && headerLogo.src) || "/static/images/LOGO_ROSATOM.svg";
    logoEl.src = nko.logo_url || defaultLogo;
    logoEl.classList.remove("hidden");
  }
  if (titleEl) titleEl.textContent = nko.name || "";
  if (descEl) descEl.textContent = nko.description || "";
  if (addrEl) addrEl.textContent = nko.address || "";
  if (phoneEl) {
    phoneEl.textContent = nko.phone || "";
    phoneEl.href = nko.phone ? `tel:${nko.phone}` : "#";
  }
  if (websiteEl) {
    websiteEl.textContent = nko.website || "";
    websiteEl.href = nko.website || "#";
  }

  // badges
  if (badgesEl) {
    badgesEl.innerHTML = "";
    const categories = nko.categories || [];
    categories.forEach((cat) => {
      const span = document.createElement("span");
      span.className = "text-white text-xs font-medium px-2 py-1 rounded-md";
      span.style.backgroundColor = cat.color || '#6CACE4';
      span.textContent = cat.name;
      badgesEl.appendChild(span);
    });
  }

  if (moreEl) {
    moreEl.href = nko.id ? `/nko/${nko.id}/` : "#";
  }

  overlay.classList.remove("hidden");
  modal.classList.remove("hidden");
}

function hideNkoModal() {
  const overlay = document.getElementById("nko-modal-overlay");
  const modal = document.getElementById("nko-modal");
  if (!modal || !overlay) return;
  overlay.classList.add("hidden");
  modal.classList.add("hidden");
}

document.addEventListener("click", function (e) {
  if (!e.target) return;
  if (e.target.id === "nko-modal-close") hideNkoModal();
  if (e.target.id === "nko-modal-overlay") hideNkoModal();
});

// expose for inline balloon links or external usage
window.showNkoModal = showNkoModal;

// Expose init function for template to call after ymaps script loaded
export { initMapAndUI, fetchAndInit };
