/**
 * Маска для ввода российского номера телефона
 * Использует IMask.js для форматирования ввода
 * Формат: +7 (XXX) XXX-XX-XX
 */

document.addEventListener('DOMContentLoaded', function() {
    // Находим все поля с классом phone-input
    const phoneInputs = document.querySelectorAll('.phone-input, input[name="phone"]');
    
    phoneInputs.forEach(function(input) {
        // Сохраняем исходное значение если оно есть
        const initialValue = input.value;
        
        // Применяем маску IMask
        const phoneMask = IMask(input, {
            mask: '+7 (000) 000-00-00',
            lazy: false,  // Показывать маску сразу
            placeholderChar: '_'
        });
        
        // Если было исходное значение, устанавливаем его
        if (initialValue && initialValue.trim() !== '') {
            phoneMask.value = initialValue;
        }
        
        // При потере фокуса, если введено меньше цифр, очищаем поле
        input.addEventListener('blur', function() {
            const unmaskedValue = phoneMask.unmaskedValue;
            
            if (unmaskedValue.length > 0 && unmaskedValue.length < 11) {
                // Если введено что-то, но недостаточно цифр - оставляем как есть
                // Валидация покажет ошибку
            } else if (unmaskedValue.length === 0) {
                // Если ничего не введено, очищаем поле полностью
                input.value = '';
                phoneMask.value = '';
            }
        });
        
        // При получении фокуса, если поле пустое, показываем маску
        input.addEventListener('focus', function() {
            if (!input.value || input.value.trim() === '') {
                phoneMask.updateValue();
            }
        });
        
        // Добавляем подсказку при наведении
        input.setAttribute('title', 'Российский номер телефона в формате +7 (XXX) XXX-XX-XX');
    });
});
