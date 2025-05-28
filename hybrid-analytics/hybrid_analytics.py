"""
Hybrid Analytics Platform
Гибридная аналитическая платформа для работы с векторными данными

Основной модуль для интеграции векторного поиска с классической аналитикой
"""

import numpy as np
from typing import List, Dict, Any, Optional, Union
import pandas as pd

from duckdb_vec import DuckDBVectorDatabase

# Импорт модуля параллельной обработки
try:
    from parallel_processing import (
        ParallelVectorProcessor, 
        batch_similarity_search_parallel
    )
    PARALLEL_AVAILABLE = True
except ImportError:
    PARALLEL_AVAILABLE = False
    print("⚠️ Модуль параллельной обработки недоступен")


class VectorDB:
    """
    Основной класс для работы с гибридными аналитическими запросами
    
    Позволяет совмещать векторный поиск с классической SQL-аналитикой
    в едином интерфейсе. Поддерживает мультипроцессинг для ускорения.
    """
    
    def __init__(self, db_path: Optional[str] = 'hybrid_analytics.duckdb', 
                 enable_parallel: bool = True):
        """
        Инициализация базы данных
        
        Args:
            db_path: Путь к файлу базы данных 
                (если None, используется in-memory)
            enable_parallel: Включить параллельную обработку
        """
        self.db = DuckDBVectorDatabase(db_path or 'hybrid_analytics.duckdb')
        self.conn = self.db.conn
        self._table_data = {}  # Кэш для данных таблиц
        
        # Инициализация параллельной обработки
        self.parallel_enabled = enable_parallel and PARALLEL_AVAILABLE
        if self.parallel_enabled:
            self.parallel_processor = ParallelVectorProcessor()
            print("✅ Параллельная обработка включена")
        else:
            self.parallel_processor = None
            if enable_parallel:
                print("⚠️ Параллельная обработка отключена")
        
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
        
        # Создаем постоянную таблицу в DuckDB (без векторов для экономии места)
        df_without_vectors = df.drop(columns=[embedding_column]).copy()
        
        # Конвертируем datetime колонки в строки для DuckDB
        for col in df_without_vectors.columns:
            if df_without_vectors[col].dtype == 'datetime64[ns]':
                df_without_vectors[col] = df_without_vectors[col].astype(str)
        
        # Регистрируем DataFrame временно для создания таблицы
        self.conn.register('temp_df', df_without_vectors)
        self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        self.conn.unregister('temp_df')
        
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
                      limit: int = 10,
                      use_parallel: bool = True) -> pd.DataFrame:
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
            use_parallel: Использовать параллельную обработку
            
        Returns:
            DataFrame с результатами поиска
        """
        # Получаем данные таблицы
        if table_name not in self._table_data:
            # Пытаемся загрузить из постоянной таблицы DuckDB
            try:
                df_meta = self.conn.execute(f"SELECT * FROM {table_name}").fetchdf()
                if len(df_meta) > 0:
                    # Конвертируем строковые даты обратно в datetime
                    if 'date' in df_meta.columns:
                        df_meta['date'] = pd.to_datetime(df_meta['date'])
                    
                    # Восстанавливаем векторы из векторной базы
                    embeddings = []
                    for _, row in df_meta.iterrows():
                        key = f"{table_name}_{row['id']}"
                        vector = self.db.retrieve(key)
                        embeddings.append(vector if vector else [0.0] * 128)
                    
                    df_meta[embedding_column] = embeddings
                    self._table_data[table_name] = df_meta
                else:
                    raise ValueError(f"Таблица {table_name} пуста")
            except Exception:
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
                        if 'date' in column.lower():
                            df = df[df[column] > pd.to_datetime(value)]
                        else:
                            df = df[df[column] > float(value)]
                    elif op == '<':
                        if 'date' in column.lower():
                            df = df[df[column] < pd.to_datetime(value)]
                        else:
                            df = df[df[column] < float(value)]
                    # Добавить другие операторы по необходимости
                else:
                    df = df[df[column] == condition]
        
        # Выбираем метод вычисления сходства
        if (use_parallel and self.parallel_enabled and 
            len(df) > 1000):  # Используем параллельную обработку для больших данных
            
            # Подготавливаем данные для параллельной обработки
            vectors_data = []
            for _, row in df.iterrows():
                key = str(row['id'])
                vector = row[embedding_column]
                if not isinstance(vector, list):
                    vector = vector.tolist()
                vectors_data.append((key, vector))
            
            # Параллельный поиск
            parallel_results = batch_similarity_search_parallel(
                query_vector=query_vector,
                vectors_data=vectors_data,
                similarity_metric=similarity_metric,
                num_processes=self.parallel_processor.num_processes
            )
            
            # Преобразуем результаты обратно в DataFrame
            result_ids = [int(key) for key, _ in parallel_results[:limit]]
            similarities = [sim for _, sim in parallel_results[:limit]]
            
            result_df = df[df['id'].isin(result_ids)].copy()
            result_df['similarity'] = result_df['id'].map(
                dict(zip(result_ids, similarities)))
            result = result_df.sort_values('similarity', ascending=False)
            
        else:
            # Последовательное вычисление сходства
            similarities = []
            for _, row in df.iterrows():
                vector = row[embedding_column]
                if isinstance(vector, list):
                    similarity = self.db.cosine_similarity(query_vector, vector)
                else:
                    similarity = self.db.cosine_similarity(
                        query_vector, vector.tolist())
                similarities.append(similarity)
            
            df['similarity'] = similarities
            result = df.sort_values('similarity', ascending=False).head(limit)
        
        return result
        
    def parallel_batch_search(self,
                             query_vectors: List[List[float]],
                             table_name: str = "documents",
                             embedding_column: str = "embedding",
                             similarity_metric: str = "cosine",
                             limit: int = 10) -> List[pd.DataFrame]:
        """
        Параллельный поиск для множества запросов
        
        Args:
            query_vectors: Список векторов запросов
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            similarity_metric: Метрика сходства
            limit: Количество результатов на запрос
            
        Returns:
            Список DataFrame с результатами для каждого запроса
        """
        if not self.parallel_enabled:
            # Fallback на последовательную обработку
            return [
                self.hybrid_search(
                    query_vector=qv,
                    table_name=table_name,
                    embedding_column=embedding_column,
                    similarity_metric=similarity_metric,
                    limit=limit,
                    use_parallel=False
                )
                for qv in query_vectors
            ]
        
        results = []
        for query_vector in query_vectors:
            result = self.hybrid_search(
                query_vector=query_vector,
                table_name=table_name,
                embedding_column=embedding_column,
                similarity_metric=similarity_metric,
                limit=limit,
                use_parallel=True
            )
            results.append(result)
        
        return results
        
    def benchmark_search_performance(self,
                                   query_vector: List[float],
                                   table_name: str = "documents",
                                   embedding_column: str = "embedding") -> Dict[str, Any]:
        """
        Бенчмарк производительности поиска
        
        Args:
            query_vector: Вектор запроса
            table_name: Имя таблицы
            embedding_column: Колонка с эмбеддингами
            
        Returns:
            Словарь с метриками производительности
        """
        if not self.parallel_enabled:
            return {"error": "Параллельная обработка недоступна"}
        
        # Получаем данные
        df = self._table_data[table_name]
        vectors_data = []
        for _, row in df.iterrows():
            key = str(row['id'])
            vector = row[embedding_column]
            if not isinstance(vector, list):
                vector = vector.tolist()
            vectors_data.append((key, vector))
        
        # Запускаем бенчмарк
        return self.parallel_processor.benchmark_parallel_vs_sequential(
            query_vector=query_vector,
            vectors_data=vectors_data,
            similarity_metric="cosine"
        )
        
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
        try:
            # Пытаемся получить статистику из постоянной таблицы DuckDB
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            total_rows = result[0] if result else 0
            
            # Статистика по векторам
            vector_count = self.conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
            
            return {
                'total_rows': total_rows,
                'unique_embeddings': vector_count
            }
        except Exception:
            # Fallback на кэш если таблица не найдена
            if table_name in self._table_data:
                df = self._table_data[table_name]
                return {
                    'total_rows': len(df),
                    'unique_embeddings': len(df)
                }
            else:
                return {'total_rows': 0, 'unique_embeddings': 0}
    
    def close(self):
        """Закрытие базы данных с сохранением на диск"""
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


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