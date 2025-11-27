// main_tsx.js - clean implementation for TSX-like index page
// Responsibilities:
// - fetch categories and NKO list
// - render sidebar cards with React-like hover styles
// - initialize Yandex map with placemarks
// - open modal as a cloned, focus-trapped element

let map;
// Adjusted center: moved further west (decrease longitude) per user request
const INITIAL_MAP_CENTER = [55.0, 60.0];
const INITIAL_MAP_ZOOM = 3;

let placemarks = [];
let placemarkCollection = null;
let activeCategories = [];
let selectedCity = "all";
let rawNkoList = [];
let categoriesMap = {}; // keyed by category id as string

function initMapAndUI(pointsData) {
  if (typeof ymaps === "undefined") {
    // Yandex Maps API not loaded
    return;
  }

  ymaps.ready(() => {
    map = new ymaps.Map("map", {
      center: INITIAL_MAP_CENTER,
      zoom: INITIAL_MAP_ZOOM,
    });

    [
      "geolocationControl",
      "trafficControl",
      "typeSelector",
      "fullscreenControl",
      "rulerControl",
      "searchControl",
    ].forEach((c) => {
      try { map.controls.remove(c); } catch (e) {}
    });

    const iconLayouts = {};
    Object.keys(categoriesMap).forEach((catId) => {
      const cat = categoriesMap[catId];
      iconLayouts[catId] = ymaps.templateLayoutFactory.createClass(
        `<div style="background-color:${cat.color};width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;">${cat.icon || ''}</div>`
      );
    });

    // create a dedicated collection to manage placemarks for easier add/remove
    try { placemarkCollection = new ymaps.GeoObjectCollection(); map.geoObjects.add(placemarkCollection); } catch(e) { placemarkCollection = null; }

    pointsData.forEach((point) => {
      const placemark = new ymaps.Placemark(point.coords, point.properties, {
        iconLayout: iconLayouts[point.properties.category] || null,
        iconShape: { type: "Circle", coordinates: [20, 20], radius: 20 },
        hasBalloon: false,
        hasHint: false,
      });

      // Add click handler to placemark - open modal on click
      placemark.events.add('click', function() {
        if (typeof window.showNkoModal === 'function') {
          window.showNkoModal(point.id);
        }
      });

      // Add placemark to map
      if (placemarkCollection && typeof placemarkCollection.add === 'function') {
        try { placemarkCollection.add(placemark); } catch(e) { try { map.geoObjects.add(placemark); } catch(e) {} }
      } else {
        try { map.geoObjects.add(placemark); } catch(e) {}
      }

      // keep category ids and city for filtering
        const entry = { placemark, id: point.id, coords: point.coords, categories: point.categoryIds, city: point.city };
        placemarks.push(entry);
      // ensure initial visibility respects current filters (in case filters were toggled before map ready)
      try {
        const catList = (activeCategories || []).map(String).filter(Boolean);
        const pCats = (entry.categories || []).map(String).filter(Boolean);
        const pCity = entry.city !== undefined && entry.city !== null ? String(entry.city) : '';
        const matchesCat = catList.length === 0 || catList.some(c => pCats.includes(c));
        const matchesCity = (selectedCity === 'all' || !selectedCity) || pCity === '' || pCity === String(selectedCity);
        const shouldShow = matchesCat && matchesCity;
        if (entry.placemark && entry.placemark.options && typeof entry.placemark.options.set === 'function') {
          entry.placemark.options.set('visible', !!shouldShow);
        } else if (!shouldShow) {
          // fallback remove
          try { map.geoObjects.remove(entry.placemark); } catch(e) {}
        }
      } catch(e) { /* ignore visibility set errors */ }
    });
    // Expose for debug inspection
    try { window.__placemarks = placemarks; window.__placemarkCollection = placemarkCollection; } catch(e) {}
    // After creating all placemarks, re-apply visibility in case async filters changed
    updateMapPlacemarksVisibility(activeCategories, selectedCity);
  });
}

async function fetchAndInit() {
  try {
    const categoriesResp = await fetch("/nko/api/categories/");
    if (!categoriesResp.ok) throw new Error("Failed to fetch categories");
    const categories = await categoriesResp.json();

    categoriesMap = {};
    categories.forEach((cat) => {
      const id = String(cat.id);
      categoriesMap[id] = {
        id: cat.id,
        name: cat.name,
        icon: cat.icon || "",
        color: cat.color || "#6CACE4",
      };
    });

    const resp = await fetch("/nko/api/nko-list/");
    if (!resp.ok) throw new Error("Failed to fetch NKO list");
    const list = await resp.json();
    rawNkoList = list;

    const pointsData = list
      .filter((nko) => nko.latitude && nko.longitude)
      .map((nko) => {
        const categoryIds = (nko.categories || []).map((c) => String(c.id)).filter(Boolean);
        const primaryCategoryId = categoryIds[0] || Object.keys(categoriesMap)[0] || null;

        return {
          id: nko.id,
          coords: [parseFloat(nko.latitude), parseFloat(nko.longitude)],
          properties: {
            hintContent: nko.name,
            balloonContent: `${nko.address || ""}<br>${(nko.categories || []).map((c) => c.name).join(", ")}`,
            category: primaryCategoryId,
          },
          title: nko.name,
          address: nko.address,
          categoryIds: categoryIds,
          city: nko.city_id !== undefined && nko.city_id !== null ? String(nko.city_id) : String(nko.city_slug || ""),
          raw: nko,
        };
      });

    renderPointsList(pointsData, list);
    attachUIHandlers();
    initMapAndUI(pointsData);
  } catch (err) {
    // Error initializing map from API
  }
}

function renderPointsList(pointsData, rawList) {
  const container = document.getElementById("points-list");
  if (!container) return;
  container.innerHTML = "";

  pointsData.forEach((p) => {
    const raw = rawList.find((r) => r.id === p.id) || {};
    const addr = p.address || "";
    // Resolve primary category metadata: raw.categories may contain objects or ids
    let primaryCat = {};
    const primaryCatId = (p.categoryIds && p.categoryIds[0]) || (p.properties && p.properties.category) || null;
    if (primaryCatId && categoriesMap[String(primaryCatId)]) {
      primaryCat = categoriesMap[String(primaryCatId)];
    } else if (raw.categories && raw.categories[0]) {
      const rc = raw.categories[0];
      if (typeof rc === 'object') primaryCat = rc;
      else {
        // rc may be an id (number or string) — resolve via categoriesMap
        const meta = categoriesMap[String(rc)];
        if (meta) primaryCat = meta;
      }
    }
    const catColor = primaryCat && primaryCat.color ? primaryCat.color : "#6CACE4";
    const catIcon = primaryCat && primaryCat.icon ? primaryCat.icon : "";

    const item = document.createElement("div");
    item.className =
      "p-4 bg-white/80 border border-slate-200/90 rounded-xl shadow-md hover:shadow-xl hover:ring-2 hover:ring-brand-green/80 cursor-pointer transition-all duration-200 ease-in-out group point-item";
    item.setAttribute("data-id", String(p.id));
    item.setAttribute("data-coords", JSON.stringify(p.coords));
    item.setAttribute("data-title", p.title || "");
    item.setAttribute("data-address", addr);
    item.setAttribute("data-categories", (p.categoryIds || []).join(","));
    item.setAttribute("data-city", p.city || "");

    item.innerHTML = `
      <div class="flex items-center gap-4">
          <div class="flex-shrink-0 w-12 h-12 rounded-lg transition-transform group-hover:scale-110 shadow-sm" style="background-color: ${catColor}; display:flex; align-items:center; justify-content:center;">
          ${catIcon ? `<span class="text-white">${catIcon}</span>` : '<span class="text-white">🏢</span>'}
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-slate-800 text-lg group-hover:text-brand-green-dark transition-colors truncate">${p.title || ""}</h3>
          <p class="text-sm text-slate-500 mt-1 truncate">${addr}</p>
        </div>
      </div>
    `;

    container.appendChild(item);
  });

  updatePointsCount(pointsData.length);
  updateCategoryVisualState();
}

function attachUIHandlers() {
  // Reset category listeners
  document.querySelectorAll(".category-filter").forEach((btn) => btn.replaceWith(btn.cloneNode(true)));
  document.querySelectorAll(".category-filter").forEach((btn) => {
    btn.addEventListener("click", function () {
      this.classList.toggle("active");
      activeCategories = Array.from(document.querySelectorAll(".category-filter.active")).map((el) => el.getAttribute("data-category"));
      updateCategoryVisualState();
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });
  });

  const citySelect = document.getElementById("city-select");
  if (citySelect) citySelect.addEventListener("change", function () {
    selectedCity = this.value;
    filterPointsByCategoriesAndCity(activeCategories, selectedCity);
  });

  // City filter autocomplete handler
  const cityFilterInput = document.getElementById("city-filter-input");
  const cityFilterId = document.getElementById("city-filter-id");
  const cityFilterSuggestions = document.getElementById("city-filter-suggestions");
  
  if (cityFilterInput && cityFilterId && cityFilterSuggestions) {
    // Get cities from APP_DATA
    const cities = window.APP_DATA?.cities || [];
    
    // Show suggestions on focus or input
    function showCitySuggestions() {
      const query = cityFilterInput.value.toLowerCase().trim();
      
      // Always include "Все города" option at the top
      const allCitiesOption = { id: 'all', name: 'Все города' };
      const filtered = query 
        ? cities.filter(c => c.name.toLowerCase().includes(query))
        : cities;
      
      const allOptions = [allCitiesOption, ...filtered];
      
      if (allOptions.length === 0) {
        cityFilterSuggestions.classList.add('hidden');
        return;
      }
      
      cityFilterSuggestions.innerHTML = allOptions.map(city => 
        `<div class="city-suggestion px-4 py-2 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer ${city.id === 'all' ? 'font-medium border-b border-slate-200 dark:border-slate-700' : ''}" data-city-id="${city.id}" data-city-name="${city.name}">${city.name}</div>`
      ).join('');
      
      cityFilterSuggestions.classList.remove('hidden');
    }
    
    // Use event delegation for city suggestions clicks
    cityFilterSuggestions.addEventListener('click', function(e) {
      const suggestion = e.target.closest('.city-suggestion');
      if (!suggestion) return;
      
      const cityId = suggestion.getAttribute('data-city-id');
      const cityName = suggestion.getAttribute('data-city-name');
      
      cityFilterInput.value = cityName;
      cityFilterId.value = cityId;
      cityFilterSuggestions.classList.add('hidden');
      
      // Update selectedCity and filter
      selectedCity = cityId;
      updateCategoryVisualState();
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });
    
    cityFilterInput.addEventListener('focus', showCitySuggestions);
    cityFilterInput.addEventListener('input', showCitySuggestions);
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
      if (!cityFilterInput.contains(e.target) && !cityFilterSuggestions.contains(e.target)) {
        cityFilterSuggestions.classList.add('hidden');
      }
    });
  }

  const clearFiltersBtn = document.getElementById("clear-filters");
  if (clearFiltersBtn) clearFiltersBtn.addEventListener("click", function () {
    activeCategories = [];
    selectedCity = 'all';
    const citySel = document.getElementById('city-select'); if (citySel) citySel.value = 'all';
    const cityFilterInput = document.getElementById('city-filter-input'); if (cityFilterInput) cityFilterInput.value = '';
    const cityFilterId = document.getElementById('city-filter-id'); if (cityFilterId) cityFilterId.value = 'all';
    document.querySelectorAll('.category-filter').forEach(el => el.classList.remove('active'));
    updateCategoryVisualState();
    filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    this.classList.add('hidden');
  });

  // Mobile sidebar open/close handlers
  const mobileSidebar = document.getElementById('mobile-sidebar');
  const mobileSidebarOverlay = document.getElementById('mobile-sidebar-overlay');
  const openSidebarBtn = document.getElementById('open-sidebar-mobile');
  const closeSidebarBtn = document.getElementById('sidebar-close-mobile');

  // Ensure mobile sidebar and overlay are direct children of body so their
  // z-index/staking context isn't affected by ancestor transforms or stacking contexts.
  try {
    // append overlay first, then sidebar so sidebar sits above overlay in DOM order
    if (mobileSidebarOverlay && mobileSidebarOverlay.parentElement !== document.body) document.body.appendChild(mobileSidebarOverlay);
    if (mobileSidebar && mobileSidebar.parentElement !== document.body) document.body.appendChild(mobileSidebar);
  } catch (e) { /* ignore DOM move errors */ }
  try {
    if (mobileSidebar) {
      // prevent clicks inside the sidebar from bubbling up to any overlay that might be intercepting
      mobileSidebar.addEventListener('click', function (ev) { try { ev.stopPropagation(); } catch(e){} });
    }
    if (mobileSidebarOverlay) {
      mobileSidebarOverlay.style.pointerEvents = 'auto';
    }
  } catch(e){}

  function showSidebarMobile() {
    try {
      if (mobileSidebar) mobileSidebar.classList.add('open');
      if (mobileSidebarOverlay) { mobileSidebarOverlay.classList.remove('hidden'); }

      // hide other overlays/carousels that might dim or intercept events
      const toHide = [];
      const carousel = document.getElementById('background-carousel'); if (carousel) toHide.push(carousel);
      const nkoOverlay = document.getElementById('nko-modal-overlay'); if (nkoOverlay) toHide.push(nkoOverlay);
      document.querySelectorAll('.cloned-overlay').forEach(el => toHide.push(el));
      toHide.forEach(el => {
        try { el.dataset._prevDisplay = el.style.display || ''; el.style.display = 'none'; } catch(e){}
      });
    } catch (e) { }
  }

  function hideSidebarMobile() {
    try {
      if (mobileSidebar) mobileSidebar.classList.remove('open');
      if (mobileSidebarOverlay) mobileSidebarOverlay.classList.add('hidden');
      // restore previously hidden overlays
      try {
        const maybe = [];
        const carousel = document.getElementById('background-carousel'); if (carousel) maybe.push(carousel);
        const nkoOverlay = document.getElementById('nko-modal-overlay'); if (nkoOverlay) maybe.push(nkoOverlay);
        document.querySelectorAll('.cloned-overlay').forEach(el => maybe.push(el));
        maybe.forEach(el => { try { if (el.dataset && typeof el.dataset._prevDisplay !== 'undefined') { el.style.display = el.dataset._prevDisplay || ''; delete el.dataset._prevDisplay; } } catch(e){} });
      } catch(e){}
    } catch (e) { }
  }

  if (openSidebarBtn) openSidebarBtn.addEventListener('click', function(e){ e.preventDefault(); showSidebarMobile(); });
  if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', function(e){ e.preventDefault(); hideSidebarMobile(); });
  if (mobileSidebarOverlay) mobileSidebarOverlay.addEventListener('click', function(e){ if (e.target === mobileSidebarOverlay) hideSidebarMobile(); });
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') { hideSidebarMobile(); } });

  // Point clicks: use event delegation on the points list container so clicks
  // still work if items are re-rendered or the sidebar DOM is moved.
  const pointsListContainer = document.getElementById('points-list');
  if (pointsListContainer) {
    // remove previously attached handler if present
    try { if (pointsListContainer._pointClickHandler) pointsListContainer.removeEventListener('click', pointsListContainer._pointClickHandler); } catch(e){}
    pointsListContainer._pointClickHandler = function (e) {
      try {
        const clicked = e.target && e.target.closest ? e.target.closest('.point-item') : null;
        if (!clicked) return;
        const id = clicked.getAttribute('data-id');
        if (!id) return;
        e.preventDefault();
        showNkoModal(Number(id));
      } catch (err) {
        // Error handling point click
      }
    };
    pointsListContainer.addEventListener('click', pointsListContainer._pointClickHandler);
  }

  const searchInput = document.getElementById('search-input');
  const searchButton = document.getElementById('search-button');
  function performSearch() {
    const el = document.getElementById('search-input');
    if (!el) return;
    const q = el.value.trim().toLowerCase();
    if (!q) { filterPointsByCategoriesAndCity(activeCategories, selectedCity); return; }

    let found = 0; let coords = [];
    document.querySelectorAll('.point-item').forEach(item => {
      const title = (item.getAttribute('data-title')||'').toLowerCase();
      const address = (item.getAttribute('data-address')||'').toLowerCase();
      const cats = (item.getAttribute('data-categories')||'').split(',').filter(Boolean);
      const city = item.getAttribute('data-city') || '';
      const matches = (title.includes(q) || address.includes(q)) && (activeCategories.length === 0 || activeCategories.some(c => cats.includes(c))) && (selectedCity === 'all' || city === selectedCity);
      if (matches) { item.style.display = 'block'; found++; coords.push(JSON.parse(item.getAttribute('data-coords') || '[]') || []); }
      else item.style.display = 'none';
    });
    updatePointsCount(found);
    if (found === 1 && coords[0] && map) map.setCenter(coords[0], 14, { duration: 200 });
  }
  if (searchInput) { searchInput.addEventListener('input', performSearch); searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(); }); }
  if (searchButton) searchButton.addEventListener('click', performSearch);

  updatePointsCount(document.querySelectorAll('.point-item').length || 0);
}

function filterPointsByCategoriesAndCity(categories, city) {
  const items = document.querySelectorAll('.point-item');
  let visible = 0; const coords = [];
  items.forEach(item => {
    const itemCats = (item.getAttribute('data-categories')||'').split(',').filter(Boolean);
    const itemCity = item.getAttribute('data-city') || '';
    const matchesCat = categories.length === 0 || categories.some(c => itemCats.includes(c));
    const matchesCity = city === 'all' || itemCity === city;
    if (matchesCat && matchesCity) { item.style.display = 'block'; visible++; coords.push(JSON.parse(item.getAttribute('data-coords') || '[]') || []); }
    else item.style.display = 'none';
  });
  updatePointsCount(visible);
  const clearBtn = document.getElementById('clear-filters'); if (clearBtn) { if (categories.length > 0 || city !== 'all') clearBtn.classList.remove('hidden'); else clearBtn.classList.add('hidden'); }
  updateActiveFiltersDisplay();
  // Ensure placemarks are updated even when city === 'all'
  try { updateMapPlacemarksVisibility(categories, city); } catch(e) { }
  if (city === 'all') { if (map) map.setCenter(INITIAL_MAP_CENTER, INITIAL_MAP_ZOOM, { duration: 200 }); return; }
  if (visible > 0 && typeof ymaps !== 'undefined') {
    try { const bounds = ymaps.util.bounds.fromPoints(coords); if (bounds) map.setBounds(bounds, { checkZoomRange:true, duration:200 }); } catch(e) {}
  }

  // Also update placemarks visibility on the map
  updateMapPlacemarksVisibility(categories, city);
}

function updateMapPlacemarksVisibility(categories, city) {
  // Use the canonical id-based visibility toggle approach from main.js
  if (!map || !Array.isArray(placemarks)) {
    return;
  }

  // Iterate through sidebar items and set matching placemark visibility by id
  const items = document.querySelectorAll('.point-item');
  
  items.forEach((item) => {
    try {
      const itemId = item.getAttribute('data-id');
      if (!itemId) return;
      // Determine whether the item is visible in the sidebar
      const isVisibleInList = item.style.display !== 'none';
      // For each placemark entry with matching id, set visibility
      placemarks.forEach((placemarkEntry) => {
        try {
          if (String(placemarkEntry.id) === String(itemId)) {
            const hasOptions = placemarkEntry.placemark && placemarkEntry.placemark.options && typeof placemarkEntry.placemark.options.set === 'function';
            if (hasOptions) {
              try {
                placemarkEntry.placemark.options.set('visible', !!isVisibleInList);
              } catch (e) { }
            }
          }
        } catch (e) {
          /* ignore per-placemark errors */
        }
      });
    } catch (e) {
      /* ignore per-item errors */
    }
  });
}

function updateActiveFiltersDisplay() {
  const container = document.getElementById('active-filters'); if (!container) return; const filtersList = container.querySelector('.flex'); if (!filtersList) return; filtersList.innerHTML = '';
  if (activeCategories.length > 0 || selectedCity !== 'all') {
    container.classList.remove('hidden');
    if (selectedCity !== 'all') {
      const chip = document.createElement('div'); chip.className = 'flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-xs font-medium';
      chip.innerHTML = `<span>${selectedCity}</span><button class="text-blue-600" data-filter-type="city">✕</button>`;
      chip.title = String(selectedCity);
      chip.setAttribute('aria-label', String(selectedCity));
      filtersList.appendChild(chip);
    }
    activeCategories.forEach(catId => {
      const filterChip = document.createElement('div');
      filterChip.className = 'flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-xs font-medium';
      const categoryData = categoriesMap[catId] || {};
      const categoryName = categoryData.name || catId;
      filterChip.innerHTML = `<span>${categoryName}</span><button class="text-blue-600" data-category="${catId}">✕</button>`;
      filterChip.title = String(categoryName);
      filterChip.setAttribute('aria-label', String(categoryName));
      filtersList.appendChild(filterChip);
    });
  } else container.classList.add('hidden');
  filtersList.querySelectorAll('button').forEach(btn => btn.addEventListener('click', function(){ const cat = this.getAttribute('data-category'); if (cat) { removeCategoryFilter(cat); filterPointsByCategoriesAndCity(activeCategories, selectedCity); } else { selectedCity='all'; filterPointsByCategoriesAndCity(activeCategories, selectedCity); } }));
}

function removeCategoryFilter(categoryId) {
  activeCategories = activeCategories.filter(c => c !== categoryId);
  document.querySelectorAll('.category-filter').forEach(el => { if (el.getAttribute('data-category') === categoryId) el.classList.remove('active'); });
  updateCategoryVisualState();
}

function updateCategoryVisualState() {
  document.querySelectorAll('.category-filter').forEach(category => {
    const isActive = category.classList.contains('active');
    const categoryColor = category.getAttribute('data-color') || '#6CACE4';
    const dot = category.querySelector('.category-color-dot');
    const icon = category.querySelector('.category-icon');
    const isDark = document.documentElement.classList.contains('dark');
    // compute dark panel/text values from CSS variables if available
    const rootStyles = getComputedStyle(document.documentElement);
    const darkPanel = rootStyles.getPropertyValue('--panel')?.trim() || 'rgba(6,10,15,0.62)';
    const darkText = rootStyles.getPropertyValue('--text')?.trim() || '#e6eef8';

    if (isActive) {
      // Active: fill the whole button with category color and use white text
      category.style.backgroundColor = categoryColor;
      // force white text with !important to override any global dark-mode rules
      try { category.style.setProperty('color', '#fff', 'important'); } catch(e) { category.style.color = '#fff'; }
      category.style.boxShadow = '0 8px 24px rgba(2,6,23,0.08)';

      if (dot) {
        // show a white inner dot for contrast (matches previous light-theme behaviour)
        dot.style.backgroundColor = '#ffffff';
        dot.style.border = '1px solid rgba(255,255,255,0.12)';
      }
      // also force inner label text to white (in case it has text-* classes with !important)
      try {
        category.querySelectorAll('span, a, p, h3, svg').forEach(el => { try { el.style.setProperty('color', '#fff', 'important'); el.style.setProperty('fill', '#fff', 'important'); } catch(e){} });
      } catch(e) {}

      if (icon) {
        // For category-icon variant: ensure inner icon/text is visible on colored background
        try {
          icon.style.backgroundColor = categoryColor;
          // set inner elements to white and force with !important to override global dark-mode rules
          icon.querySelectorAll('*').forEach(ch => { try { ch.style.setProperty('color', '#fff', 'important'); ch.style.setProperty('fill', '#fff', 'important'); } catch(e){} });
          icon.style.setProperty('color', '#fff', 'important');
        } catch(e) {}
      }
    } else {
      // Inactive state: choose different defaults for dark vs light themes
      if (isDark) {
        category.style.backgroundColor = darkPanel;
        category.style.color = darkText;
      } else {
        category.style.backgroundColor = 'rgba(255,255,255,0.7)';
        category.style.color = '#111827'; // Tailwind slate-900 hex
      }
      category.style.boxShadow = '';
      if (dot) {
        // small colored dot stays visible in both themes
        dot.style.backgroundColor = categoryColor;
        // border should contrast depending on theme
        dot.style.border = isDark ? '1px solid rgba(255,255,255,0.06)' : '1px solid rgba(0,0,0,0.06)';
      }
      if (icon) {
        try {
          // icon tile keeps its category color, icon content remains white for contrast
          icon.style.backgroundColor = categoryColor;
          icon.querySelectorAll('*').forEach(ch => { try { ch.style.setProperty('color', '#fff', 'important'); ch.style.setProperty('fill', '#fff', 'important'); } catch(e){} });
          icon.style.setProperty('color', '#fff', 'important');
        } catch(e) {}
      }
      // remove forced color/fill on inner elements so theme styles can take effect
      try {
        category.style.removeProperty('color');
        category.querySelectorAll('span, a, p, h3, svg').forEach(el => { try { el.style.removeProperty('color'); el.style.removeProperty('fill'); } catch(e){} });
      } catch(e) {}
    }
  });
}

// Expose updater so other non-module scripts (theme toggler) can refresh visuals
try { window.updateCategoryVisualState = updateCategoryVisualState; } catch(e) {}

function updatePointsCount(count) { const el = document.getElementById('points-count'); if (!el) return; el.textContent = `Найдено ${count} ${getPointsWord(count)}`; }
function getPointsWord(count) { if (count % 10 === 1 && count % 100 !== 11) return 'точка НКО'; else if ([2,3,4].includes(count%10) && ![12,13,14].includes(count%100)) return 'точки НKO'.replace('KO','КО'); else return 'точек НКО'; }

// Cloned modal with focus trap
function showNkoModal(id) {
  const originalModal = document.getElementById('nko-modal');
  const originalOverlay = document.getElementById('nko-modal-overlay');
  if (!originalModal || !originalOverlay) return;
  const nko = rawNkoList.find(i => i.id === id);
  if (!nko) return;

  const modalClone = originalModal.cloneNode(true);
  const overlayClone = originalOverlay.cloneNode(true);

  // populate clone
  const logoEl = modalClone.querySelector('#nko-modal-logo');
  const titleEl = modalClone.querySelector('#nko-modal-title');
  const badgesEl = modalClone.querySelector('#nko-modal-badges');
  const descEl = modalClone.querySelector('#nko-modal-description');
  const addrEl = modalClone.querySelector('#nko-modal-address');
  const phoneEl = modalClone.querySelector('#nko-modal-phone');
  const websiteEl = modalClone.querySelector('#nko-modal-website');
  const moreEl = modalClone.querySelector('#nko-modal-more');

  if (logoEl) { const headerLogo = document.querySelector('.logo-light'); const defaultLogo = (headerLogo && headerLogo.src) || '/static/images/LOGO_ROSATOM.svg'; logoEl.src = nko.logo_url || defaultLogo; logoEl.classList.remove('hidden'); }
  if (titleEl) titleEl.textContent = nko.name || '';
  if (descEl) descEl.textContent = nko.description || '';
  if (addrEl) addrEl.textContent = nko.address || '';
  if (phoneEl) { phoneEl.textContent = nko.phone || ''; phoneEl.href = nko.phone ? `tel:${nko.phone}` : '#'; }
  if (websiteEl) { websiteEl.textContent = nko.website || ''; websiteEl.href = nko.website || '#'; }

  // Resolve categories to metadata (categoriesMap may contain id->meta)
  const resolvedCats = (nko.categories || []).map(c => {
    // category entry may be an object or an id
    if (!c) return null;
    if (typeof c === 'object') {
      if (c.id && categoriesMap[String(c.id)]) return categoriesMap[String(c.id)];
      return { id: c.id || c.key || null, name: c.name || '', color: c.color || '', icon: c.icon || '' };
    }
    // primitive id
    const meta = categoriesMap[String(c)];
    return meta || { id: c, name: String(c), color: '', icon: '' };
  }).filter(Boolean);

  // Populate category badges using resolved metadata
  if (badgesEl) {
    badgesEl.innerHTML = '';
    resolvedCats.forEach(cat => {
      const span = document.createElement('span');
      span.className = 'text-white text-xs font-medium px-2 py-1 rounded-md whitespace-nowrap overflow-hidden text-ellipsis max-w-[120px] inline-block transition-colors';
      span.style.backgroundColor = cat.color || '#6CACE4';
      span.textContent = cat.name || '';
      span.title = cat.name || '';
      badgesEl.appendChild(span);
    });
  }

  // Populate primary category display (colored tile + name) — show colored background (ignore DB icon)
  try {
    const categoryIconEl = modalClone.querySelector('#nko-modal-category-icon');
    const categoryIconInner = modalClone.querySelector('#nko-modal-category-icon-inner');
    const categoryNameEl = modalClone.querySelector('#nko-modal-category-name');
    const primaryCat = resolvedCats.length ? resolvedCats[0] : null;
    if (primaryCat) {
      if (categoryNameEl) {
        categoryNameEl.textContent = primaryCat.name || '';
        categoryNameEl.style.display = 'block';
      }
      if (categoryIconEl) {
        categoryIconEl.style.display = 'flex';
        if (primaryCat.color) categoryIconEl.style.backgroundColor = primaryCat.color;
        // Do not inject raw SVG/icon from DB — show an empty colored tile or initial
        if (categoryIconInner) {
          // If category provides an SVG string, inject it; otherwise show initial/emoji
          const iconVal = primaryCat.icon || primaryCat.emoji || (primaryCat.name && primaryCat.name.charAt(0)) || '🏢';
          try {
            const looksLikeSvg = typeof iconVal === 'string' && iconVal.trim().startsWith('<');
            if (looksLikeSvg) categoryIconInner.innerHTML = iconVal;
            else categoryIconInner.textContent = iconVal;
            categoryIconInner.style.color = '#fff';
          } catch (e) {
            try { categoryIconInner.textContent = String(iconVal); } catch(e) { categoryIconInner.innerText = String(iconVal); }
          }
        }
      }
    } else {
      if (categoryNameEl) categoryNameEl.style.display = 'none';
      if (categoryIconEl) categoryIconEl.style.display = 'none';
    }
  } catch(e) { /* non-fatal */ }

  if (moreEl) moreEl.href = nko.id ? `/nko/${nko.id}/` : '#';

  modalClone.removeAttribute('id'); overlayClone.removeAttribute('id');
  modalClone.classList.add('animate-fade-in-up-sm','transition-all','duration-200','cloned-modal');
  overlayClone.classList.add('cloned-overlay');

  // Ensure modal clone appears above mobile sidebar and other overlays by
  // applying a very high inline z-index. This prevents the modal from
  // rendering behind the slide-up drawer on small screens.
  try {
    overlayClone.style.zIndex = '110000';
    overlayClone.style.pointerEvents = 'auto';
    modalClone.style.zIndex = '110001';
    modalClone.style.pointerEvents = 'auto';
  } catch (e) { /* ignore style set errors */ }

  document.body.appendChild(overlayClone);
  document.body.appendChild(modalClone);
  overlayClone.classList.remove('hidden'); modalClone.classList.remove('hidden');

  // Debug logs to help diagnose stacking issues in browser console
  try { /* debug logs removed */ } catch(e){}

  // focus trap
  const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const outside = Array.from(document.body.children).filter(n => n !== overlayClone && n !== modalClone);
  outside.forEach(n => { try { if (n instanceof HTMLElement) { n.setAttribute('aria-hidden','true'); try { n.inert = true; } catch(e){} } } catch(e){} });

  const focusableSelector = 'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])';
  const focusable = Array.from(modalClone.querySelectorAll(focusableSelector)).filter(el => el.offsetParent !== null);
  const first = focusable[0] instanceof HTMLElement ? focusable[0] : null;
  if (first) first.focus(); else { modalClone.setAttribute('tabindex','-1'); modalClone.focus(); }

  function onKey(e) {
    if (e.key === 'Escape') { closeAll(); }
    if (e.key === 'Tab') {
      if (focusable.length === 0) { e.preventDefault(); return; }
      const idx = focusable.indexOf(document.activeElement);
      if (e.shiftKey) { if (idx === 0 || document.activeElement === modalClone) { e.preventDefault(); focusable[focusable.length-1].focus(); } }
      else { if (idx === focusable.length-1) { e.preventDefault(); focusable[0].focus(); } }
    }
  }

  function closeAll() {
    try { overlayClone.remove(); } catch(e) {}
    try { modalClone.remove(); } catch(e) {}
    outside.forEach(n => { try { if (n instanceof HTMLElement) { n.removeAttribute('aria-hidden'); if (typeof n.inert !== 'undefined') n.inert = false; } } catch(e){} });
    document.removeEventListener('keydown', onKey, true);
    try { document.removeEventListener('click', outsideClickHandler, true); } catch(e){}
    try { if (previouslyFocused) previouslyFocused.focus(); } catch(e){}
  }

  const closeBtn = modalClone.querySelector('#nko-modal-close') || modalClone.querySelector('[data-close]');
  if (closeBtn) closeBtn.addEventListener('click', closeAll);
  overlayClone.addEventListener('click', e => { if (e.target === overlayClone) closeAll(); });
  document.addEventListener('keydown', onKey, true);

  // Close modal when clicking anywhere outside the modal content (robust
  // fallback in case overlay isn't catching the event due to stacking
  // contexts). We prefer to detect clicks that are outside the inner dialog
  // element (the white card) rather than the outer `modalClone` which itself
  // fills the viewport.
  const modalContentEl = (function(){
    try {
      // preferentially find the white content card by common classes
      return modalClone.querySelector('.bg-white, .rounded-t-2xl, .sm\\:rounded-2xl') || modalClone.firstElementChild || null;
    } catch(e) { return modalClone.firstElementChild || null; }
  })();

  function outsideClickHandler(e) {
    try {
      if (modalContentEl) {
        if (!modalContentEl.contains(e.target)) closeAll();
      } else {
        if (!modalClone.contains(e.target)) closeAll();
      }
    } catch (err) { /* ignore */ }
  }
  document.addEventListener('click', outsideClickHandler, true);

  modalClone.querySelectorAll('button,a').forEach(el => el.classList.add('transition-colors','duration-150'));
}

// Export to window immediately after function definition
window.showNkoModal = showNkoModal;

function hideNkoModal() {
  const overlay = document.getElementById('nko-modal-overlay');
  const modal = document.getElementById('nko-modal');
  if (!modal || !overlay) return;
  overlay.classList.add('hidden'); modal.classList.add('hidden');
}

document.addEventListener('click', function(e){ if (!e.target) return; if (e.target.id === 'nko-modal-close') hideNkoModal(); if (e.target.id === 'nko-modal-overlay') hideNkoModal(); });

export { initMapAndUI, fetchAndInit };