// Основные функции JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Автосабмит форм с селектами
    document.querySelectorAll('select[onchange*="submit"]').forEach(select => {
        select.onchange = function() {
            this.form.submit();
        };
    });
    
    // Подтверждение удаления
    document.querySelectorAll('form[action*="delete"]').forEach(form => {
        form.onsubmit = function(e) {
            if (!confirm('Вы уверены, что хотите удалить?')) {
                e.preventDefault();
                return false;
            }
            return true;
        };
    });
    
    // Форматирование сумм
    document.querySelectorAll('.income, .expense').forEach(el => {
        const amount = parseFloat(el.textContent);
        if (!isNaN(amount)) {
            el.textContent = formatCurrency(amount);
        }
    });
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 2
    }).format(amount);
}

function showCategoryForm() {
    document.getElementById('categoryForm').style.display = 'block';
    document.getElementById('categoryForm').scrollIntoView({ behavior: 'smooth' });
}

function hideCategoryForm() {
    document.getElementById('categoryForm').style.display = 'none';
}
