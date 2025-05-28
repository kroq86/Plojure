"""
Hybrid Analytics Platform
Гибридная аналитическая платформа для работы с векторными данными

Основной модуль для интеграции векторного поиска с классической аналитикой
"""

import numpy as np
from typing import List, Dict, Any, Optional, Union
import pandas as pd

from duckdb_vec import DuckDBVectorDatabase


class VectorDB:
    """
    Основной класс для работы с гибридными аналитическими запросами
    
    Позволяет совмещать векторный поиск с классической SQL-аналитикой
    в едином интерфейсе
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Инициализация базы данных
        
        Args:
            db_path: Путь к файлу базы данных 
                (если None, используется in-memory)
        """
        self.db = DuckDBVectorDatabase(db_path or ':memory:')
        self.conn = self.db.conn
        self._table_data = {}  # Кэш для данных таблиц
        
    def load_embeddings(self,
                        data_source: Union[str, pd.DataFrame],
                        table_name: str = "documents",
                        embedding_column: str = "embedding",
                        **kwargs) -> None:
        """
        Загрузка данных с эмбеддингами
        
        Args:
            data_source: Путь к файлу или DataFrame с данными
            table_name: Имя таблицы для создания
            embedding_column: Название колонки с векторами
        """
        if isinstance(data_source, str):
            # Загрузка из файла
            if data_source.endswith('.parquet'):
                df = pd.read_parquet(data_source)
            elif data_source.endswith('.csv'):
                df = pd.read_csv(data_source)
            else:
                raise ValueError(
                    f"Неподдерживаемый формат файла: {data_source}")
        else:
            df = data_source
            
        # Сохраняем данные для SQL запросов
        self._table_data[table_name] = df
        self.conn.register(table_name, df)
        
        # Загружаем векторы в векторную базу
        for _, row in df.iterrows():
            key = f"{table_name}_{row['id']}"
            vector = row[embedding_column]
            if isinstance(vector, list):
                self.db.insert(key, vector)
            else:
                # Если вектор в другом формате, конвертируем
                self.db.insert(key, vector.tolist())
        
    def hybrid_search(self,
                      query_vector: List[float],
                      table_name: str = "documents",
                      embedding_column: str = "embedding",
                      filters: Optional[Dict[str, Any]] = None,
                      similarity_metric: str = "cosine",
                      limit: int = 10) -> pd.DataFrame:
        """
        Гибридный поиск: векторное сходство + фильтрация по метаданным
        
        Args:
            query_vector: Вектор запроса
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            filters: Фильтры по метаданным 
                {'column': 'value', 'date': '>2023-01-01'}
            similarity_metric: Метрика сходства 
                ('cosine', 'euclidean', 'dot_product')
            limit: Количество результатов
            
        Returns:
            DataFrame с результатами поиска
        """
        # Получаем данные таблицы
        if table_name not in self._table_data:
            raise ValueError(f"Таблица {table_name} не найдена")
        
        df = self._table_data[table_name].copy()
        
        # Применяем фильтры
        if filters:
            for column, condition in filters.items():
                if isinstance(condition, str) and condition.startswith(
                        ('>', '<', '>=', '<=', '!=')):
                    # Парсим условие
                    op = condition.rstrip('0123456789.-')
                    value = condition[len(op):]
                    if op == '>':
                        df = df[df[column] > pd.to_datetime(value) if 'date' in column.lower() else df[column] > float(value)]
                    elif op == '<':
                        df = df[df[column] < pd.to_datetime(value) if 'date' in column.lower() else df[column] < float(value)]
                    # Добавить другие операторы по необходимости
                else:
                    df = df[df[column] == condition]
        
        # Вычисляем сходство для отфильтрованных записей
        similarities = []
        for _, row in df.iterrows():
            vector = row[embedding_column]
            if isinstance(vector, list):
                similarity = self.db.cosine_similarity(query_vector, vector)
            else:
                similarity = self.db.cosine_similarity(query_vector, vector.tolist())
            similarities.append(similarity)
        
        df['similarity'] = similarities
        
        # Сортируем и ограничиваем результаты
        result = df.sort_values('similarity', ascending=False).head(limit)
        
        return result
        
    def analyze_clusters(self,
                         table_name: str = "documents",
                         embedding_column: str = "embedding",
                         similarity_threshold: float = 0.8,
                         group_by: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Анализ кластеров похожих документов
        
        Args:
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            similarity_threshold: Порог сходства для кластеризации
            group_by: Колонки для группировки
            
        Returns:
            DataFrame с анализом кластеров
        """
        if table_name not in self._table_data:
            raise ValueError(f"Таблица {table_name} не найдена")
        
        df = self._table_data[table_name]
        
        # Простая реализация кластерного анализа
        clusters = []
        for group_name, group_df in df.groupby(group_by or ['id']):
            vectors = [row[embedding_column] for _, row in group_df.iterrows()]
            
            # Вычисляем средние сходства внутри группы
            similarities = []
            for i, v1 in enumerate(vectors):
                for j, v2 in enumerate(vectors[i+1:], i+1):
                    if isinstance(v1, list) and isinstance(v2, list):
                        sim = self.db.cosine_similarity(v1, v2)
                        similarities.append(sim)
            
            if similarities:
                avg_similarity = np.mean(similarities)
                if avg_similarity > similarity_threshold:
                    clusters.append({
                        'cluster_group': str(group_name),
                        'documents_count': len(group_df),
                        'avg_similarity': avg_similarity,
                        'max_similarity': max(similarities),
                        'min_similarity': min(similarities)
                    })
        
        return pd.DataFrame(clusters)
        
    def similarity_trends(self,
                          reference_vector: List[float],
                          table_name: str = "documents",
                          embedding_column: str = "embedding",
                          time_column: str = "date",
                          period: str = "month") -> pd.DataFrame:
        """
        Анализ временной динамики похожести
        
        Args:
            reference_vector: Референсный вектор для сравнения
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            time_column: Колонка с датой/временем
            period: Период агрегации ('day', 'week', 'month', 'year')
            
        Returns:
            DataFrame с временной динамикой
        """
        if table_name not in self._table_data:
            raise ValueError(f"Таблица {table_name} не найдена")
        
        df = self._table_data[table_name].copy()
        
        # Вычисляем сходство для всех записей
        similarities = []
        for _, row in df.iterrows():
            vector = row[embedding_column]
            if isinstance(vector, list):
                similarity = self.db.cosine_similarity(reference_vector, vector)
            else:
                similarity = self.db.cosine_similarity(reference_vector, vector.tolist())
            similarities.append(similarity)
        
        df['similarity'] = similarities
        
        # Группируем по времени
        df[time_column] = pd.to_datetime(df[time_column])
        
        if period == "month":
            df['period'] = df[time_column].dt.to_period('M')
        elif period == "week":
            df['period'] = df[time_column].dt.to_period('W')
        elif period == "day":
            df['period'] = df[time_column].dt.to_period('D')
        elif period == "year":
            df['period'] = df[time_column].dt.to_period('Y')
        
        # Агрегируем по периодам
        result = df.groupby('period').agg({
            'similarity': ['count', 'mean', 'max', 'min']
        }).round(3)
        
        result.columns = ['documents_count', 'avg_similarity', 'max_similarity', 'min_similarity']
        result = result.reset_index()
        
        return result
        
    def execute_sql(self, query: str, 
                    parameters: Optional[List] = None) -> pd.DataFrame:
        """
        Выполнение произвольного SQL запроса
        
        Args:
            query: SQL запрос
            parameters: Параметры для запроса
            
        Returns:
            DataFrame с результатами
        """
        if parameters:
            result = self.conn.execute(query, parameters).fetchdf()
        else:
            result = self.conn.execute(query).fetchdf()
        return result
        
    def create_vector_index(self,
                            table_name: str,
                            embedding_column: str,
                            index_type: str = "hnsw") -> None:
        """
        Создание индекса для ускорения векторного поиска
        
        Args:
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            index_type: Тип индекса
        """
        print(f"Создание индекса {index_type} для {table_name}."
              f"{embedding_column}")
        
    def get_statistics(self, table_name: str) -> Dict[str, Any]:
        """
        Получение статистики по таблице
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            Словарь со статистикой
        """
        if table_name in self._table_data:
            df = self._table_data[table_name]
            return {
                'total_rows': len(df),
                'unique_embeddings': len(df)  # Упрощенная версия
            }
        else:
            return {'total_rows': 0, 'unique_embeddings': 0}


# Удобные функции для быстрого старта
def quick_search(data_file: str,
                 query_vector: List[float],
                 filters: Optional[Dict[str, Any]] = None,
                 limit: int = 10) -> pd.DataFrame:
    """
    Быстрый поиск без создания объекта VectorDB
    
    Args:
        data_file: Путь к файлу с данными
        query_vector: Вектор запроса
        filters: Фильтры
        limit: Количество результатов
        
    Returns:
        DataFrame с результатами
    """
    db = VectorDB()
    db.load_embeddings(data_file)
    return db.hybrid_search(query_vector, filters=filters, limit=limit)


def create_sample_data(num_documents: int = 1000,
                       embedding_dim: int = 128,
                       categories: List[str] = None) -> pd.DataFrame:
    """
    Создание тестовых данных для демонстрации
    
    Args:
        num_documents: Количество документов
        embedding_dim: Размерность эмбеддингов
        categories: Список категорий
        
    Returns:
        DataFrame с тестовыми данными
    """
    if categories is None:
        categories = ['технологии', 'наука', 'спорт', 'политика', 'культура']
    
    np.random.seed(42)
    
    data = {
        'id': range(num_documents),
        'title': [f'Документ {i}' for i in range(num_documents)],
        'text': [f'Текст документа {i}' for i in range(num_documents)],
        'embedding': [np.random.rand(embedding_dim).tolist() 
                      for _ in range(num_documents)],
        'category': np.random.choice(categories, num_documents),
        'date': pd.date_range('2023-01-01', periods=num_documents, 
                              freq='D')[:num_documents]
    }
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Пример использования
    print("🚀 Hybrid Analytics Platform - Демонстрация")
    
    # Создание тестовых данных
    print("\n1. Создание тестовых данных...")
    sample_data = create_sample_data(100, 128)
    print(f"Создано {len(sample_data)} документов")
    
    # Инициализация базы данных
    print("\n2. Инициализация базы данных...")
    db = VectorDB()
    db.load_embeddings(sample_data)
    
    # Гибридный поиск
    print("\n3. Гибридный поиск...")
    query_vector = np.random.rand(128).tolist()
    results = db.hybrid_search(
        query_vector=query_vector,
        filters={'category': 'технологии'},
        limit=5
    )
    print(f"Найдено {len(results)} похожих документов в категории "
          "'технологии'")
    print(results[['id', 'title', 'category', 'similarity']].head())
    
    # Анализ кластеров
    print("\n4. Анализ кластеров...")
    clusters = db.analyze_clusters(group_by=['category'])
    print("Анализ кластеров по категориям:")
    print(clusters)
    
    print("\n✅ Демонстрация завершена!") 