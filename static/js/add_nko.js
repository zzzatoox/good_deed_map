/**
 * add_nko.js - Form enhancements for NKO add/edit pages
 *
 * Features:
 * - City autocomplete with Russian cities
 * - Logo file validation (PNG/JPG/JPEG only)
 * - Form submission validation
 *
 * Note: Theme toggle functionality is handled in base.html
 */

/**
 * Creates autocomplete functionality for an input field
 * @param {HTMLInputElement} inp - The input element to attach autocomplete to
 * @param {string[]} arr - Array of possible autocomplete values
 */
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
        if (count > 10) break; // Limit to 10 suggestions
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
      // Down arrow
      currentFocus++;
      addActive(x);
    } else if (e.keyCode == 38) {
      // Up arrow
      currentFocus--;
      addActive(x);
    } else if (e.keyCode == 13) {
      // Enter
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
    for (let i = 0; i < x.length; i++) {
      x[i].classList.remove("autocomplete-active");
    }
  }

  function closeAllLists(elmnt) {
    const x = document.getElementsByClassName("autocomplete-items");
    for (let i = 0; i < x.length; i++) {
      if (elmnt != x[i] && elmnt != inp) {
        x[i].parentNode.removeChild(x[i]);
      }
    }
  }

  document.addEventListener("click", function (e) {
    closeAllLists(e.target);
  });
}

/**
 * Validates logo file extension (PNG, JPG, JPEG only)
 * Displays inline validation messages
 * @param {HTMLInputElement} fileInput - File input element
 * @returns {boolean} True if valid or empty, false otherwise
 */
function validateLogoFile(fileInput) {
  const validationMessage = document.getElementById("logo-validation");

  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    const fileName = file.name;
    const fileExtension = fileName.split(".").pop().toLowerCase();

    if (["png", "jpg", "jpeg"].includes(fileExtension)) {
      // Valid file
      validationMessage.textContent = "Файл принят: " + fileName;
      validationMessage.className =
        "file-validation-message file-validation-success";
      validationMessage.style.display = "block";
      return true;
    } else {
      // Invalid file extension
      validationMessage.textContent =
        "Ошибка: допустимы только файлы с расширениями PNG, JPG, JPEG";
      validationMessage.className =
        "file-validation-message file-validation-error";
      validationMessage.style.display = "block";
      fileInput.value = ""; // Clear invalid file
      return false;
    }
  } else {
    // No file selected
    validationMessage.style.display = "none";
    return true;
  }
}

/**
 * Initialize form functionality on DOMContentLoaded
 * - City autocomplete for Russian cities
 * - Logo file validation on change
 * - Form submit validation
 */
document.addEventListener("DOMContentLoaded", function () {
  // Russian cities for autocomplete (most populated)
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
    "Ростов-на-Дону",
    "Уфа",
    "Красноярск",
    "Воронеж",
    "Пермь",
    "Волгоград",
  ];

  // Attach autocomplete to city input
  const cityInput = document.getElementById("city");
  if (cityInput) {
    autocomplete(cityInput, russianCities);
  }

  // Attach file validation to logo input
  const logoInput = document.getElementById("logo");
  if (logoInput) {
    logoInput.addEventListener("change", function () {
      validateLogoFile(this);
    });
  }

  // Attach form submit validation
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
});

// Export helpers for potential reuse
export { autocomplete, validateLogoFile };
