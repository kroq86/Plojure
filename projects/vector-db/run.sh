#!/bin/bash

# Активируем виртуальное окружение
source venv/bin/activate

echo "🎯 HYBRID ANALYTICS PLATFORM"
echo "Демонстрация для аналитиков и Data Scientists"
echo "============================================================"

# Проверяем аргументы командной строки
if [ "$1" = "parallel" ]; then
    echo "🚀 Запуск демонстрации мультипроцессинга..."
    python examples/parallel_demo.py
elif [ "$1" = "benchmark" ]; then
    echo "⚡ Запуск бенчмарка параллельной обработки..."
    python parallel_processing.py
elif [ "$1" = "persistence" ]; then
    echo "💾 Запуск теста персистентности базы данных..."
    python test_persistence.py
else
    echo "📊 Запуск основной демонстрации..."
    python examples/quick_start.py
fi

echo ""
echo "💡 Доступные опции:"
echo "  ./run.sh          - Основная демонстрация"
echo "  ./run.sh parallel - Демо мультипроцессинга"
echo "  ./run.sh benchmark - Бенчмарк параллельной обработки"
echo "  ./run.sh persistence - Тест сохранения базы данных" 