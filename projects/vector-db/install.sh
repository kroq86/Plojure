#!/bin/bash

set -e

echo "🚀 Hybrid Analytics Platform - Установка"
echo "========================================"

# Определение ОС
OS="$(uname -s)"
ARCH="$(uname -m)"

echo "Система: $OS $ARCH"

# Установка FASM
install_fasm() {
    echo "📦 Установка FASM..."
    
    if command -v fasm &> /dev/null; then
        echo "✅ FASM уже установлен"
        return
    fi
    
    case "$OS" in
        "Darwin")
            if command -v brew &> /dev/null; then
                brew install fasm
            else
                echo "❌ Homebrew не найден. Установите Homebrew или FASM вручную"
                exit 1
            fi
            ;;
        "Linux")
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y fasm
            elif command -v yum &> /dev/null; then
                sudo yum install -y fasm
            elif command -v pacman &> /dev/null; then
                sudo pacman -S fasm
            else
                echo "❌ Неподдерживаемый пакетный менеджер"
                exit 1
            fi
            ;;
        *)
            echo "❌ Неподдерживаемая ОС: $OS"
            exit 1
            ;;
    esac
    
    echo "✅ FASM установлен"
}

# Установка Python зависимостей
install_python_deps() {
    echo "🐍 Установка Python зависимостей..."
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 не найден. Установите Python3"
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        echo "❌ pip3 не найден. Установите pip3"
        exit 1
    fi
    
    pip3 install -r requirements.txt
    echo "✅ Python зависимости установлены"
}

# Компиляция ассемблерного кода
compile_asm() {
    echo "⚡ Компиляция ассемблерного кода..."
    
    if [ ! -f "dot_product.asm" ]; then
        echo "❌ Файл dot_product.asm не найден"
        exit 1
    fi
    
    case "$OS" in
        "Darwin")
            if [ "$ARCH" = "arm64" ]; then
                # Apple Silicon
                fasm dot_product.asm dot_product.o
                gcc -shared -o dot_product.so dot_product.o
            else
                # Intel Mac
                fasm dot_product.asm dot_product.o
                gcc -shared -o dot_product.so dot_product.o
            fi
            ;;
        "Linux")
            fasm dot_product.asm dot_product.o
            gcc -shared -fPIC -o dot_product.so dot_product.o
            ;;
    esac
    
    echo "✅ Ассемблерный код скомпилирован"
}

# Создание виртуального окружения
setup_venv() {
    echo "🔧 Настройка виртуального окружения..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Виртуальное окружение создано"
    else
        echo "✅ Виртуальное окружение уже существует"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Виртуальное окружение настроено"
}

# Тестирование установки
test_installation() {
    echo "🧪 Тестирование установки..."
    
    # Активируем виртуальное окружение
    source venv/bin/activate
    
    python3 -c "
import sys
sys.path.append('.')
try:
    from hybrid_analytics import VectorDB, create_sample_data
    import numpy as np
    
    # Быстрый тест
    data = create_sample_data(10, 64)
    db = VectorDB()
    db.load_embeddings(data)
    
    query = np.random.rand(64).tolist()
    results = db.hybrid_search(query, limit=3)
    
    print('✅ Тест прошел успешно!')
    print(f'Найдено {len(results)} результатов')
    
except Exception as e:
    print(f'❌ Ошибка теста: {e}')
    sys.exit(1)
"
}

# Основная функция
main() {
    echo "Начинаем установку..."
    
    # Проверка что мы в правильной директории
    if [ ! -f "requirements.txt" ]; then
        echo "❌ Файл requirements.txt не найден. Запустите скрипт из корня проекта"
        exit 1
    fi
    
    install_fasm
    compile_asm
    setup_venv
    test_installation
    
    echo ""
    echo "🎉 Установка завершена успешно!"
    echo ""
    echo "Для активации виртуального окружения:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Для запуска демо:"
    echo "  source venv/bin/activate && python examples/quick_start.py"
    echo ""
    echo "Для запуска основного модуля:"
    echo "  source venv/bin/activate && python hybrid_analytics.py"
}

# Запуск
main "$@" 