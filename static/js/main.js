// Entry point for the index page. This file initializes the map and UI.
// It was moved from inline <script> in templates/index.html

let map;
const INITIAL_MAP_CENTER = [61.524, 105.3188];
const INITIAL_MAP_ZOOM = 3;
let placemarks = [];
let searchControl;
let activeCategories = [];
let selectedCity = "all";
let rawNkoList = [];

function initMapAndUI(pointsData) {
  if (typeof ymaps === "undefined") {
    console.error("Yandex Maps API not loaded");
    return;
  }

  ymaps.ready(() => {
    map = new ymaps.Map("map", {
      center: INITIAL_MAP_CENTER,
      zoom: INITIAL_MAP_ZOOM,
    });

    map.controls.remove("geolocationControl");
    map.controls.remove("trafficControl");
    map.controls.remove("typeSelector");
    map.controls.remove("fullscreenControl");
    map.controls.remove("rulerControl");
    map.controls.remove("searchControl");
    const iconLayouts = {
      ecology: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #56C02B;">🍃</div>'
      ),
      territory: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #FCC30B;">🏕️</div>'
      ),
      animals: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #259789;">🐶</div>'
      ),
      sport: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #E20072;">🏋️</div>'
      ),
      social: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #1D293D;">🛡️</div>'
      ),
      other: ymaps.templateLayoutFactory.createClass(
        '<div class="rounded-full w-10 h-10 flex items-center justify-center text-white text-xl font-bold shadow-md" style="background-color: #6CACE4;">🎸</div>'
      ),
    };

    // Add placemarks
    pointsData.forEach((point) => {
      const placemark = new ymaps.Placemark(point.coords, point.properties, {
        iconLayout: iconLayouts[point.properties.category] || iconLayouts.other,
        iconShape: { type: "Circle", coordinates: [0, 0], radius: 20 },
      });
      // open modal when placemark clicked
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
        categories: point.properties.category,
        coords: point.coords,
        city: point.city,
        id: point.id,
      });
    });

    // attach UI handlers that rely on map & placemarks
    attachUIHandlers(pointsData);
  });
}

// Fetch NKO list from API and initialize the map with real data
async function fetchAndInit() {
  try {
    const resp = await fetch("/nko/api/nko-list/");
    if (!resp.ok) throw new Error("Failed to fetch NKO list");
    const list = await resp.json();
    rawNkoList = list;
    const pointsData = list
      .filter((nko) => nko.latitude && nko.longitude)
      .map((nko) => ({
        id: nko.id,
        coords: [parseFloat(nko.latitude), parseFloat(nko.longitude)],
        properties: {
          hintContent: nko.name,
          balloonContent: `${nko.address || ""}<br>${(
            nko.categories || []
          ).join(", ")}`,
          category:
            nko.primary_category ||
            (nko.category_slugs && nko.category_slugs[0]) ||
            "other",
        },
        title: nko.name,
        address: nko.address,
        city:
          nko.city_id !== undefined && nko.city_id !== null
            ? String(nko.city_id)
            : nko.city_slug ||
              (nko.city || "").toString().toLowerCase().replace(/\s+/g, "-"),
      }));

    renderPointsList(pointsData, list);

    initMapAndUI(pointsData);
  } catch (err) {
    console.error("Error initializing map from API:", err);
  }
}

function renderPointsList(pointsData, rawList) {
  const container = document.getElementById("points-list");
  if (!container) return;
  container.innerHTML = "";

  const categoryNames = {
    ecology: "Экология",
    territory: "Территория",
    animals: "Животные",
    sport: "Спорт",
    social: "Соц. защита",
    other: "Другое",
  };

  const badgeColors = {
    ecology: "bg-[#56C02B]",
    territory: "bg-[#FCC30B]",
    animals: "bg-[#259789]",
    sport: "bg-[#E20072]",
    social: "bg-[#1D293D]",
    other: "bg-[#6CACE4]",
  };

  pointsData.forEach((p) => {
    const raw = rawList.find((r) => r.id === p.id) || {};
    const keys =
      raw.category_keys ||
      (p.properties.category ? [p.properties.category] : ["other"]);
    const addr = p.address || "";

    const badgesHtml = keys
      .map(
        (k) =>
          `<span class="${
            badgeColors[k] || badgeColors.other
          } text-white text-xs font-medium px-2 py-1 rounded-md">${
            categoryNames[k] || k
          }</span>`
      )
      .join(" ");

    const item = document.createElement("div");
    item.className =
      "py-5 cursor-pointer hover:bg-white/20 transition-colors point-item rounded-l-lg";
    item.setAttribute("data-id", p.id);
    item.setAttribute("data-coords", JSON.stringify(p.coords));
    item.setAttribute("data-title", p.title || "");
    item.setAttribute("data-address", addr);
    item.setAttribute("data-categories", keys.join(","));
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

  document
    .getElementById("city-select")
    .addEventListener("change", function () {
      selectedCity = this.value;
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
    });

  document
    .getElementById("clear-filters")
    .addEventListener("click", function () {
      activeCategories = [];
      selectedCity = "all";
      document.getElementById("city-select").value = "all";
      updateCategoryVisualState();
      filterPointsByCategoriesAndCity(activeCategories, selectedCity);
      this.classList.add("hidden");
    });

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
    const searchText = document
      .getElementById("search-input")
      .value.trim()
      .toLowerCase();
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
      const categories = item.getAttribute("data-categories").split(",");
      const itemCity = item.getAttribute("data-city");
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
          if (
            placemarkItem.coords[0] === itemCoords[0] &&
            placemarkItem.coords[1] === itemCoords[1]
          )
            placemarkItem.placemark.options.set("visible", true);
        });
      } else {
        item.style.display = "none";
        placemarks.forEach((placemarkItem) => {
          if (
            placemarkItem.coords[0] === itemCoords[0] &&
            placemarkItem.coords[1] === itemCoords[1]
          )
            placemarkItem.placemark.options.set("visible", false);
        });
      }
    });
    document.getElementById(
      "points-count"
    ).textContent = `Найдено ${foundCount} ${getPointsWord(foundCount)}`;
    if (foundCount === 1) map.setCenter(foundCoords[0], 14, { duration: 200 });
    else if (foundCount > 1) {
      const bounds = ymaps.util.bounds.fromPoints(foundCoords);
      if (bounds)
        map.setBounds(bounds, { checkZoomRange: true, duration: 200 });
    }
  }

  document
    .getElementById("search-input")
    .addEventListener("input", performSearch);
  document
    .getElementById("search-input")
    .addEventListener("keypress", function (e) {
      if (e.key === "Enter") performSearch();
    });
  document
    .getElementById("search-button")
    .addEventListener("click", performSearch);

  // initial count
  document.getElementById("points-count").textContent = `Найдено ${
    pointsData.length
  } ${getPointsWord(pointsData.length)}`;
}

function filterPointsByCategoriesAndCity(categories, city) {
  const pointItems = document.querySelectorAll(".point-item");
  let visibleCount = 0;
  let visibleCoords = [];
  pointItems.forEach((item) => {
    const itemCategories = item.getAttribute("data-categories").split(",");
    const itemCity = item.getAttribute("data-city");
    const matchesCategory =
      categories.length === 0 ||
      categories.some((cat) => itemCategories.includes(cat));
    const matchesCity = city === "all" || itemCity === city;
    const shouldShow = matchesCategory && matchesCity;
    const coords = JSON.parse(item.getAttribute("data-coords"));
    if (shouldShow) {
      item.style.display = "block";
      visibleCount++;
      visibleCoords.push(coords);
      placemarks.forEach((placemarkItem) => {
        if (
          placemarkItem.coords[0] === coords[0] &&
          placemarkItem.coords[1] === coords[1]
        )
          placemarkItem.placemark.options.set("visible", true);
      });
    } else {
      item.style.display = "none";
      placemarks.forEach((placemarkItem) => {
        if (
          placemarkItem.coords[0] === coords[0] &&
          placemarkItem.coords[1] === coords[1]
        )
          placemarkItem.placemark.options.set("visible", false);
      });
    }
  });
  document.getElementById(
    "points-count"
  ).textContent = `Найдено ${visibleCount} ${getPointsWord(visibleCount)}`;
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
  const filtersList = activeFiltersContainer.querySelector(".flex");
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
    activeCategories.forEach((category) => {
      const filterChip = document.createElement("div");
      filterChip.className =
        "flex items-center gap-1 bg-blue-100 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-3 py-1 rounded-full text-xs font-medium";
      const categoryNames = {
        ecology: "Экология",
        territory: "Территория",
        animals: "Животные",
        sport: "Спорт",
        social: "Соц. защита",
        other: "Другое",
      };
      filterChip.innerHTML = `<span>${categoryNames[category]}</span><button class="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100" data-category="${category}"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>`;
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
    category.classList.remove(
      "ring-2",
      "ring-offset-2",
      "ring-[#56C02B]",
      "ring-[#FCC30B]",
      "ring-[#259789]",
      "ring-[#E20072]",
      "ring-[#1D293D]",
      "ring-[#6CACE4]"
    );
    if (isActive) {
      category.classList.add("ring-2", "ring-offset-2");
      const ringColors = {
        ecology: "ring-[#56C02B]",
        territory: "ring-[#FCC30B]",
        animals: "ring-[#259789]",
        sport: "ring-[#E20072]",
        social: "ring-[#1D293D]",
        other: "ring-[#6CACE4]",
      };
      category.classList.add(ringColors[categoryType]);
    }
  });
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
    const keys = nko.category_keys || [];
    const categoryNames = {
      ecology: "Экология",
      territory: "Территория",
      animals: "Животные",
      sport: "Спорт",
      social: "Соц. защита",
      other: "Другое",
    };
    const badgeColors = {
      ecology: "bg-[#56C02B]",
      territory: "bg-[#FCC30B]",
      animals: "bg-[#259789]",
      sport: "bg-[#E20072]",
      social: "bg-[#1D293D]",
      other: "bg-[#6CACE4]",
    };
    (keys.length ? keys : ["other"]).forEach((k) => {
      const span = document.createElement("span");
      span.className = `${
        badgeColors[k] || badgeColors.other
      } text-white text-xs font-medium px-2 py-1 rounded-md`;
      span.textContent = categoryNames[k] || k;
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
