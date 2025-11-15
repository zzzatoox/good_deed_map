// Entry point for the index page. This file initializes the map and UI.
// It was moved from inline <script> in templates/index.html

let map;
let placemarks = [];
let searchControl;
let activeCategories = [];
let selectedCity = "all";

function initMapAndUI(pointsData) {
  if (typeof ymaps === "undefined") {
    console.error("Yandex Maps API not loaded");
    return;
  }

  ymaps.ready(() => {
    map = new ymaps.Map("map", {
      center: [58.631194, 59.859275],
      zoom: 12,
    });

    map.controls.remove("geolocationControl");
    map.controls.remove("trafficControl");
    map.controls.remove("typeSelector");
    map.controls.remove("fullscreenControl");
    map.controls.remove("rulerControl");
    map.controls.remove("searchControl");

    searchControl = new ymaps.control.SearchControl({
      options: {
        float: "right",
        floatIndex: 100,
        noPlacemark: true,
        provider: "yandex#search",
      },
    });
    map.controls.add(searchControl);

    searchControl.events.add("resultselect", function (e) {
      const selectedResult = searchControl.getResultsArray()[e.get("index")];
      map.setCenter(selectedResult.geometry.getCoordinates(), 14, {
        duration: 500,
      });
    });

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
      map.geoObjects.add(placemark);
      placemarks.push({
        placemark,
        title: point.title,
        address: point.address,
        categories: point.properties.category,
        coords: point.coords,
        city: point.city,
      });
    });

    // attach UI handlers that rely on map & placemarks
    attachUIHandlers(pointsData);
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
      map.setCenter(coords, 16, { duration: 500 });
      document
        .querySelectorAll(".point-item")
        .forEach((el) =>
          el.classList.remove("bg-blue-500/20", "dark:bg-blue-900")
        );
      this.classList.add("bg-blue-500/20", "dark:bg-blue-900");
      placemarks.forEach((placemarkItem) => {
        if (
          placemarkItem.coords[0] === coords[0] &&
          placemarkItem.coords[1] === coords[1]
        ) {
          placemarkItem.placemark.balloon.open();
        }
      });
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
      const cityNames = {
        moscow: "Москва",
        "saint-petersburg": "Санкт-Петербург",
        novosibirsk: "Новосибирск",
        ekaterinburg: "Екатеринбург",
        "nizhny-novgorod": "Нижний Новгород",
        kazan: "Казань",
        chelyabinsk: "Челябинск",
        omsk: "Омск",
        samara: "Самара",
        rostov: "Ростов-на-Дону",
        ufa: "Уфа",
        krasnoyarsk: "Красноярск",
        voronezh: "Воронеж",
        perm: "Пермь",
        volgograd: "Волгоград",
      };
      cityFilterChip.innerHTML = `<span>${cityNames[selectedCity]}</span><button class="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100" data-filter-type="city"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>`;
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

// Expose init function for template to call after ymaps script loaded
export { initMapAndUI };
