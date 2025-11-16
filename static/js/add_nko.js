// Extracted JS from templates/nko/add_nko.html
// Runs on module import (attach listeners on DOMContentLoaded)

function autocomplete(inp, arr) {
  let currentFocus;
  inp.addEventListener("input", function () {
    let val = this.value;
    closeAllLists();
    if (!val) {
      return false;
    }
    currentFocus = -1;
    const container = document.createElement("DIV");
    container.setAttribute("id", this.id + "autocomplete-list");
    container.setAttribute("class", "autocomplete-items");
    this.parentNode.appendChild(container);
    let count = 0;
    for (let i = 0; i < arr.length; i++) {
      if (arr[i].substr(0, val.length).toUpperCase() === val.toUpperCase()) {
        count++;
        if (count > 10) break;
        const item = document.createElement("DIV");
        item.innerHTML =
          "<strong>" + arr[i].substr(0, val.length) + "</strong>";
        item.innerHTML += arr[i].substr(val.length);
        item.innerHTML += "<input type='hidden' value='" + arr[i] + "'>";
        item.addEventListener("click", function () {
          inp.value = this.getElementsByTagName("input")[0].value;
          closeAllLists();
        });
        container.appendChild(item);
      }
    }
  });

  inp.addEventListener("keydown", function (e) {
    let x = document.getElementById(this.id + "autocomplete-list");
    if (x) x = x.getElementsByTagName("div");
    if (e.keyCode == 40) {
      currentFocus++;
      addActive(x);
    } else if (e.keyCode == 38) {
      currentFocus--;
      addActive(x);
    } else if (e.keyCode == 13) {
      e.preventDefault();
      if (currentFocus > -1) {
        if (x) x[currentFocus].click();
      }
    }
  });

  function addActive(x) {
    if (!x) return false;
    removeActive(x);
    if (currentFocus >= x.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = x.length - 1;
    x[currentFocus].classList.add("autocomplete-active");
  }

  function removeActive(x) {
    for (let i = 0; i < x.length; i++)
      x[i].classList.remove("autocomplete-active");
  }

  function closeAllLists(elmnt) {
    const x = document.getElementsByClassName("autocomplete-items");
    for (let i = 0; i < x.length; i++) {
      if (elmnt != x[i] && elmnt != inp) x[i].parentNode.removeChild(x[i]);
    }
  }

  document.addEventListener("click", function (e) {
    closeAllLists(e.target);
  });
}

function validateLogoFile(fileInput) {
  const validationMessage = document.getElementById("logo-validation");
  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    const fileName = file.name;
    const fileExtension = fileName.split(".").pop().toLowerCase();
    if (["png", "jpg", "jpeg"].includes(fileExtension)) {
      validationMessage.textContent = "Файл принят: " + fileName;
      validationMessage.className =
        "file-validation-message file-validation-success";
      validationMessage.style.display = "block";
      return true;
    } else {
      validationMessage.textContent =
        "Ошибка: допустимы только файлы с расширениями PNG, JPG, JPEG";
      validationMessage.className =
        "file-validation-message file-validation-error";
      validationMessage.style.display = "block";
      fileInput.value = "";
      return false;
    }
  } else {
    validationMessage.style.display = "none";
    return true;
  }
}

function initializeTheme(htmlElement, moonIcon, sunIcon) {
  if (
    localStorage.theme === "dark" ||
    (!("theme" in localStorage) &&
      window.matchMedia("(prefers-color-scheme: dark)").matches)
  ) {
    enableDarkTheme(htmlElement, moonIcon, sunIcon);
  } else {
    enableLightTheme(htmlElement, moonIcon, sunIcon);
  }
}

function enableDarkTheme(htmlElement, moonIcon, sunIcon) {
  htmlElement.classList.add("dark");
  localStorage.setItem("theme", "dark");
  if (moonIcon) moonIcon.classList.add("hidden");
  if (sunIcon) sunIcon.classList.remove("hidden");
}

function enableLightTheme(htmlElement, moonIcon, sunIcon) {
  htmlElement.classList.remove("dark");
  localStorage.setItem("theme", "light");
  if (moonIcon) moonIcon.classList.remove("hidden");
  if (sunIcon) sunIcon.classList.add("hidden");
}

function toggleTheme(htmlElement, moonIcon, sunIcon) {
  if (htmlElement.classList.contains("dark"))
    enableLightTheme(htmlElement, moonIcon, sunIcon);
  else enableDarkTheme(htmlElement, moonIcon, sunIcon);
}

// Auto-run initialization on DOMContentLoaded
document.addEventListener("DOMContentLoaded", function () {
  // Russian cities for autocomplete taken from template
  const russianCities = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Нижний Новгород",
    "Казань",
    "Челябинск",
    "Омск",
    "Самара",
  ];

  const cityInput = document.getElementById("city");
  if (cityInput) autocomplete(cityInput, russianCities);

  const logoInput = document.getElementById("logo");
  if (logoInput)
    logoInput.addEventListener("change", function () {
      validateLogoFile(this);
    });

  const form = document.getElementById("ngo-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      const logoInput = document.getElementById("logo");
      if (logoInput && !validateLogoFile(logoInput)) {
        e.preventDefault();
        alert(
          "Пожалуйста, выберите файл с правильным расширением (PNG, JPG, JPEG)"
        );
      }
    });
  }

  // Theme toggle
  const themeToggle = document.getElementById("theme-toggle");
  const moonIcon = document.getElementById("moon-icon");
  const sunIcon = document.getElementById("sun-icon");
  const htmlElement = document.documentElement;

  initializeTheme(htmlElement, moonIcon, sunIcon);
  if (themeToggle)
    themeToggle.addEventListener("click", function () {
      toggleTheme(htmlElement, moonIcon, sunIcon);
    });
});

// Optionally export helpers (not required by template)
export { autocomplete, validateLogoFile, initializeTheme };
