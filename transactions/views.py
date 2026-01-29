from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.db.models import Sum
from django.contrib import messages
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.db.models.functions import ExtractWeekDay

# DRF импорты (е REST API)
from rest_framework import viewsets, permissions, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

# Локальные импорты
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer
from .forms import TransactionForm, CategoryForm

# Дополнительные
from collections import OrderedDict
from datetime import datetime, timedelta
import json
from decimal import Decimal

def decimal_to_float(value):
    """Преобразование Decimal в float для JSON сериализации"""
    if isinstance(value, Decimal):
        return float(value)
    return value

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



    
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['type', 'category']  # фильтр по типу и категории
    ordering_fields = ['date', 'amount']     # сортировка по дате и сумме
    ordering = ['-date']                     # сортировка по умолчанию

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Добавьте этот метод!    
# Template Views (новые)


@method_decorator(login_required, name='dispatch')
class TransactionListView(ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Фильтры
        transaction_type = self.request.GET.get('type')
        category_id = self.request.GET.get('category')
        ordering = self.request.GET.get('ordering', '-date')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if transaction_type:
            queryset = queryset.filter(type=transaction_type)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        queryset = queryset.order_by(ordering)
        return queryset.select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user)
        
        # Подсчет итогов
        queryset = self.get_queryset()
        total_income = queryset.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = queryset.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
        balance = total_income - total_expense
        
        context['total_income'] = total_income
        context['total_expense'] = total_expense
        context['balance'] = balance
        
        return context


@method_decorator(login_required, name='dispatch')
class TransactionCreateView(CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Транзакция успешно создана')
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


@method_decorator(login_required, name='dispatch')
class TransactionUpdateView(UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


@method_decorator(login_required, name='dispatch')
@method_decorator(require_POST, name='dispatch')  
class TransactionDeleteView(DeleteView):
    model = Transaction
    success_url = reverse_lazy('transaction_list') 

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Транзакция удалена')
        return super().delete(request, *args, **kwargs)
    

@method_decorator(login_required, name='dispatch')
class CategoryListView(ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


@method_decorator(login_required, name='dispatch')
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        # Привязываем категорию к текущему пользователю
        form.instance.user = self.request.user
        messages.success(self.request, 'Категория успешно создана!')
        return super().form_valid(form)
    
    def get_form_kwargs(self):
        # Передаем пользователя в форму
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


@method_decorator(login_required, name='dispatch')
@method_decorator(require_POST, name='dispatch')  # ← ВАЖНО!
class CategoryDeleteView(DeleteView):
    model = Category
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
def delete(self, request, *args, **kwargs):
    self.object = self.get_object()
    self.object.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Для AJAX-запросов
        return JsonResponse({'success': True, 'message': 'Категория удалена'})
    
    # Для обычных POST-запросов
    messages.success(request, 'Категория удалена')
    return redirect(self.success_url)



@method_decorator(login_required, name='dispatch')
class StatisticsTemplateView(TemplateView):
    template_name = 'transactions/statistics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Получаем даты из GET-параметров или используем значения по умолчанию
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        
        # Устанавливаем дефолтные значения (последние 30 дней)
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')
        
        # Сохраняем даты для отображения в форме
        context['from_date'] = from_date
        context['to_date'] = to_date
        
        # Получаем данные статистики
        statistics_data = self._get_statistics_data(user, from_date, to_date)
        context.update(statistics_data)
        
        return context
    
    def _get_statistics_data(self, user, from_date, to_date):
        """Получение данных статистики для пользователя за период"""
        
        # Фильтруем транзакции пользователя по дате
        transactions = Transaction.objects.filter(
            user=user,
            date__range=[from_date, to_date]
        )
        
        # Основные показатели (преобразуем Decimal в float)
        total_income_result = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )
        total_income = decimal_to_float(total_income_result['total']) or 0
        
        total_expense_result = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )
        total_expense = decimal_to_float(total_expense_result['total']) or 0
        
        balance = total_income - total_expense
        
        # Статистика по категориям расходов
        expense_by_category = list(transactions.filter(
            type='expense'
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        # Преобразуем Decimal в float для категорий расходов
        for item in expense_by_category:
            item['total'] = decimal_to_float(item['total']) or 0
        
        # Статистика по категориям доходов
        income_by_category = list(transactions.filter(
            type='income'
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        # Преобразуем Decimal в float для категорий доходов
        for item in income_by_category:
            item['total'] = decimal_to_float(item['total']) or 0
        
        # Динамика по месяцам
        monthly_data = list(transactions.annotate(
            month=TruncMonth('date')
        ).values(
            'month', 
            'type'
        ).annotate(
            total=Sum('amount')
        ).order_by('month'))
        
        # Форматируем данные для графика (преобразуем Decimal в float)
        monthly_trend = OrderedDict()
        for entry in monthly_data:
            month_str = entry['month'].strftime('%Y-%m')
            if month_str not in monthly_trend:
                monthly_trend[month_str] = {'income': 0, 'expense': 0}
            monthly_trend[month_str][entry['type']] = decimal_to_float(entry['total']) or 0
        
        # Самые крупные транзакции (уже будут Decimal в amount)
        largest_transactions = transactions.select_related(
            'category'
        ).order_by('-amount')[:10]
        
        # Количество транзакций по дням недели (совместимо с SQLite)
        weekday_data = list(transactions.annotate(
            weekday=ExtractWeekDay('date')
        ).values('weekday').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('weekday'))
        
        # Преобразуем Decimal в float для дней недели
        for item in weekday_data:
            item['total'] = decimal_to_float(item['total']) or 0
        
        # Преобразуем номера дней недели в названия
        weekday_names = {
            1: 'Воскресенье',
            2: 'Понедельник', 
            3: 'Вторник',
            4: 'Среда',
            5: 'Четверг',
            6: 'Пятница',
            7: 'Суббота'
        }
        
        formatted_weekday_data = []
        for item in weekday_data:
            formatted_weekday_data.append({
                'weekday': weekday_names.get(item['weekday'], f"День {item['weekday']}"),
                'total': item['total'],
                'count': item['count']
            })
        
        # Подготавливаем данные для JavaScript (графиков)
        context = {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': balance,
            'expense_by_category': expense_by_category,
            'income_by_category': income_by_category,
            'monthly_trend': monthly_trend,
            'largest_transactions': largest_transactions,
            'weekday_data': formatted_weekday_data,
            'transaction_count': transactions.count(),
        }
        
        # Средняя транзакция расходов (с проверкой деления на ноль)
        expense_count = transactions.filter(type='expense').count()
        if expense_count > 0:
            context['avg_transaction'] = total_expense / expense_count
        else:
            context['avg_transaction'] = 0
        
        # JSON данные для JavaScript (теперь все значения float)
        try:
            context['monthly_trend_json'] = json.dumps(monthly_trend)
            context['expense_by_category_json'] = json.dumps(expense_by_category)
            context['income_by_category_json'] = json.dumps(income_by_category)
            context['weekday_data_json'] = json.dumps(formatted_weekday_data)
        except TypeError as e:
            # Если все равно ошибка, показываем пустые данные
            print(f"JSON serialization error: {e}")
            context['monthly_trend_json'] = '{}'
            context['expense_by_category_json'] = '[]'
            context['income_by_category_json'] = '[]'
            context['weekday_data_json'] = '[]'
            
        return context


class StatisticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        # Устанавливаем дефолтные значения
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not to_date:
            to_date = datetime.now().strftime('%Y-%m-%d')

        transactions = Transaction.objects.filter(
            user=request.user,
            date__range=[from_date, to_date]
        )

        # Преобразуем Decimal в float
        total_income_result = transactions.filter(type='income').aggregate(
            total=Sum('amount')
        )
        total_income = decimal_to_float(total_income_result['total']) or 0
        
        total_expense_result = transactions.filter(type='expense').aggregate(
            total=Sum('amount')
        )
        total_expense = decimal_to_float(total_expense_result['total']) or 0
        
        balance = total_income - total_expense

        # Сумма по категориям (преобразуем Decimal в float)
        category_summary = list(transactions.values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total'))
        
        for item in category_summary:
            item['total'] = decimal_to_float(item['total']) or 0

        # Тренд по месяцам
        monthly_trend_data = list(transactions.annotate(
            month=TruncMonth('date')
        ).values(
            'month', 
            'type'
        ).annotate(
            total=Sum('amount')
        ).order_by('month'))

        # Форматируем месячные данные (преобразуем Decimal в float)
        trend = OrderedDict()
        for entry in monthly_trend_data:
            month_str = entry['month'].strftime('%Y-%m')
            if month_str not in trend:
                trend[month_str] = {'income': 0, 'expense': 0}
            trend[month_str][entry['type']] = decimal_to_float(entry['total']) or 0

        data = {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "category_summary": category_summary,
            "monthly_trend": trend,
            "transaction_count": transactions.count(),
            "date_range": {
                "from": from_date,
                "to": to_date
            }
        }

        return Response(data)
    
