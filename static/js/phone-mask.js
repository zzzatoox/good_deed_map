/**
 * Маска для ввода российского номера телефона
 * Использует IMask.js для форматирования ввода
 * Формат: +7 (XXX) XXX-XX-XX
 */

document.addEventListener('DOMContentLoaded', function() {
    // Находим все поля с классом phone-input
    function applyMaskToInput(input) {
        if (!input) return null;
        if (input.dataset.phoneMaskInitialized) return input._phoneMaskInstance || null;
        const initialValue = input.value;
        try {
            const phoneMask = IMask(input, {
                mask: '+7 (000) 000-00-00',
                lazy: true,  // Показывать маску только при вводе
                placeholderChar: '_'
            });
            if (initialValue && initialValue.trim() !== '') {
                phoneMask.value = initialValue;
                    // Force mask to render/format current value immediately (useful when element is visible)
                    try { phoneMask.updateValue(); input.value = phoneMask.value; } catch (e) {}
            }
            input.addEventListener('blur', function() {
                const unmaskedValue = phoneMask.unmaskedValue;
                if (unmaskedValue.length === 0) {
                    input.value = '';
                    phoneMask.value = '';
                }
            });
            input.addEventListener('focus', function() {
                if (!input.value || input.value.trim() === '') {
                    phoneMask.updateValue();
                }
            });
            input.setAttribute('title', 'Российский номер телефона в формате +7 (XXX) XXX-XX-XX');
            input.dataset.phoneMaskInitialized = 'true';
            input._phoneMaskInstance = phoneMask;
            return phoneMask;
        } catch (e) {
            return null;
        }
    }

    // Initialize all existing phone inputs on DOMContentLoaded
    const phoneInputs = document.querySelectorAll('.phone-input, input[name="phone"]');
    phoneInputs.forEach(function(input) { applyMaskToInput(input); });

    // Expose helper to initialize masks for dynamically added inputs
    try { window.initPhoneMask = function(elOrSelector) {
        if (!elOrSelector) {
            document.querySelectorAll('.phone-input, input[name="phone"]').forEach(i=>applyMaskToInput(i));
            return;
        }
        if (typeof elOrSelector === 'string') {
            document.querySelectorAll(elOrSelector).forEach(i=>applyMaskToInput(i));
            return;
        }
        if (elOrSelector instanceof Element) { applyMaskToInput(elOrSelector); return; }
        if (elOrSelector instanceof NodeList || Array.isArray(elOrSelector)) { Array.from(elOrSelector).forEach(i=>applyMaskToInput(i)); return; }
    }; } catch(e) {}
});
