#!/usr/bin/env python3
"""
Тест персистентности базы данных
"""

import os
import numpy as np
from hybrid_analytics import VectorDB, create_sample_data

def test_database_persistence():
    """Тест сохранения базы данных на диск"""
    
    db_file = "test_persistence.duckdb"
    
    # Удаляем файл если существует
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"🗑️ Удален старый файл {db_file}")
    
    print("🧪 Тест персистентности базы данных")
    print("=" * 40)
    
    # 1. Создание и заполнение базы данных
    print("\n1. Создание базы данных...")
    db = VectorDB(db_path=db_file)
    
    # Создаем тестовые данные
    test_data = create_sample_data(100, 128)
    db.load_embeddings(test_data, table_name="test_docs")
    
    print(f"✅ Добавлено {len(test_data)} документов")
    
    # 2. Закрываем базу данных
    print("\n2. Закрытие базы данных...")
    db.close()
    
    # 3. Проверяем, что файл создан
    if os.path.exists(db_file):
        file_size = os.path.getsize(db_file)
        print(f"✅ Файл базы данных создан: {db_file}")
        print(f"📊 Размер файла: {file_size:,} байт")
    else:
        print(f"❌ Файл базы данных НЕ создан!")
        return False
    
    # 4. Открываем базу данных заново
    print("\n3. Повторное открытие базы данных...")
    db2 = VectorDB(db_path=db_file)
    
    # 5. Проверяем, что данные сохранились
    stats = db2.get_statistics("test_docs")
    print(f"📈 Статистика после переоткрытия:")
    print(f"   Всего строк: {stats.get('total_rows', 0)}")
    
    # 6. Тестируем поиск
    query_vector = np.random.rand(128).tolist()
    try:
        results = db2.hybrid_search(
            query_vector=query_vector,
            table_name="test_docs",
            limit=5
        )
        print(f"✅ Поиск работает: найдено {len(results)} результатов")
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return False
    
    # 7. Закрываем вторую сессию
    db2.close()
    
    print(f"\n🎉 Тест персистентности ПРОЙДЕН!")
    print(f"💾 База данных сохранена в файле: {db_file}")
    
    return True

if __name__ == "__main__":
    success = test_database_persistence()
    if success:
        print("\n✅ Все тесты пройдены успешно!")
    else:
        print("\n❌ Тесты провалены!")
        exit(1) 