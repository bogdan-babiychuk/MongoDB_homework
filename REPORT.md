# Отчёт по итоговому заданию: MongoDB для учёта оценок студентов университета

**Студент:** Бабийчук Богдан

**Дисциплина:** Программная инженерия 2

**Преподаватель:** Дмитрий Калугин-Балашов

---

## 1. Постановка задачи

Спроектировать в MongoDB базу данных, в которой деканат, преподаватели и
студенты университета смогут учитывать и анализировать оценки. Реализация
выполнена на Python с использованием драйвера `pymongo`; зависимости
управляются Poetry. Полный исходный код находится в каталоге `src/`,
запуск — `poetry run python -m src.main`.

## 2. Сценарии использования

Перед проектированием я смоделировал основных потребителей данных:

| Роль | Ключевые сценарии |
| --- | --- |
| **Студент** | посмотреть свои оценки, средний балл, оценки по конкретному курсу |
| **Преподаватель** | выставить оценку, посмотреть свою группу/поток, статистику по курсу |
| **Деканат** | рейтинги студентов и групп, должники, отчёты по семестру, поиск студента |
| **Учебный отдел** | назначение преподавателей на курсы, формирование ведомостей |

Из этих сценариев и выводятся коллекции, схемы и индексы.

## 3. Структура базы данных

База `university` содержит **6 коллекций**:

```
groups        ←─── students ──┐
                              │
professors ──┐                │
             │                │
courses ──── enrollments ──── grades
```

Решение про **referencing vs embedding** для каждой связи приняли так:

* Студенты/преподаватели/курсы/группы — **самостоятельные коллекции** со
  ссылками `ObjectId`. Эти сущности живут долго, обновляются независимо
  (студент меняет группу, преподаватель — кафедру и т.д.) — embedding
  привёл бы к дублированию и риску рассинхрона.
* `contacts` студента/преподавателя — **embedded subdocument**: всегда
  читается вместе с владельцем, не нужен отдельно, объём ограничен.
* Оценки вынесены в отдельную коллекцию `grades`, а не вкладываются в
  студента. Аргументы:
  * write-heavy сценарий (за 4 года десятки оценок на студента → документ
    студента раздувался бы и нарушал MongoDB-практику "rarely growing
    documents");
  * запросы строятся по разным "осям" (по студенту, курсу, преподавателю,
    периоду) — отдельная коллекция позволяет завести нужные индексы и не
    тащить полный документ студента;
  * атомарность операции выставления одной оценки достигается атомарностью
    одного документа.
* `enrollments` отделена от `grades` намеренно: запись на курс существует
  до сессии, оценка появляется позже. Это позволяет хранить факт записи
  даже без оценки и считать "ещё не сдавшие" корректно.

### 3.1. Коллекции и JSON Schema

Все валидаторы заданы в `src/schema.py` и применяются через
`db.create_collection(..., validator=...)` / `collMod`. Уровень
валидации — `moderate`, чтобы не падать при существующих данных.

#### `students`
```json
{
  "_id": ObjectId,
  "full_name": "Иванов Иван Иванович",
  "email": "ivanov@univ.ru",
  "group_id": ObjectId,
  "enrollment_year": 2023,
  "status": "active | academic_leave | expelled | graduated",
  "birth_date": ISODate,
  "contacts": { "phone": "...", "address": "..." }
}
```

#### `professors`
```json
{
  "_id": ObjectId,
  "full_name": "Петров П.П.",
  "email": "petrov@univ.ru",
  "department": "ФИТ",
  "position": "assistant | senior_lecturer | associate_professor | professor | head_of_department",
  "hire_date": ISODate,
  "degree": "к.т.н."
}
```

#### `courses`
```json
{
  "_id": ObjectId,
  "code": "CS301",
  "title": "Базы данных",
  "department": "ФИТ",
  "credits": 5,
  "description": "...",
  "semester_offered": [3, 5]
}
```

#### `groups`
```json
{
  "_id": ObjectId,
  "name": "ФИ-23-1",
  "faculty": "ФИТ",
  "year": 1,
  "specialization": "Программная инженерия"
}
```

#### `enrollments`
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "course_id": ObjectId,
  "professor_id": ObjectId,
  "semester": 1,
  "year": 2025
}
```

#### `grades`
```json
{
  "_id": ObjectId,
  "student_id": ObjectId,
  "course_id": ObjectId,
  "professor_id": ObjectId,
  "enrollment_id": ObjectId,
  "value": 5,
  "date": ISODate,
  "type": "exam | credit | midterm | coursework",
  "semester": 1,
  "year": 2025,
  "comment": ""
}
```

## 4. Схема (диаграмма)

```
┌─────────────┐         ┌──────────────┐
│  groups     │◄────────│  students    │
│  _id        │ N:1     │  _id         │
│  name       │         │  group_id ───┘
│  faculty    │         │  status
└─────────────┘         └──────┬───────┘
                               │ 1:N
                               ▼
┌─────────────┐         ┌──────────────────┐         ┌──────────────┐
│  courses    │◄────────│  enrollments     │────────►│ professors   │
│  _id, code  │ N:1     │  student_id      │ N:1     │  _id         │
│  title      │         │  course_id       │         │  department  │
└─────┬───────┘         │  professor_id    │         └──────┬───────┘
      │                 │  year, semester  │                │
      │ 1:N             └─────────┬────────┘                │ 1:N
      │                           │ 1:1                     │
      │                           ▼                         │
      │                 ┌──────────────────┐                │
      └────────────────►│  grades          │◄───────────────┘
                        │  student_id      │
                        │  course_id       │
                        │  professor_id    │
                        │  enrollment_id   │
                        │  value, date     │
                        │  year, semester  │
                        └──────────────────┘
```

## 5. Вторичные индексы

Каждый индекс мотивирован конкретным запросом (см. раздел 6).
Полный набор задан в `src/indexes.py`.

| Коллекция | Индекс | Тип | Зачем |
| --- | --- | --- | --- |
| `students` | `email` | unique | гарантия уникальности логина |
| `students` | `group_id` | btree | ведомости группы (Q6) |
| `students` | `status` | btree | выборка только активных |
| `students` | `enrollment_year` | btree | отчёты по году поступления |
| `students` | `full_name` | **text** | поиск по ФИО (Q9) |
| `professors` | `email` | unique | уникальность |
| `professors` | `department` | btree | список преподавателей кафедры |
| `courses` | `code` | unique | уникальный шифр курса |
| `courses` | `department` | btree | курсы кафедры |
| `courses` | `title` | **text** | поиск курса |
| `groups` | `name` | unique | уникальное имя группы |
| `groups` | `(faculty, year)` | compound | списки групп факультета |
| `enrollments` | `(student_id, course_id, year, semester)` | **unique compound** | один и тот же курс нельзя записать дважды в один семестр |
| `enrollments` | `(course_id, year, semester)` | compound | количество студентов на курсе (Q11) |
| `enrollments` | `(professor_id, year, semester)` | compound | нагрузка преподавателя |
| `grades` | `(student_id, date DESC)` | compound | оценки студента в порядке свежести (Q1, Q2) |
| `grades` | `(course_id, year, semester)` | compound | статистика по курсу (Q5, Q8) |
| `grades` | `(professor_id, year, semester)` | compound | статистика преподавателя (Q7) |
| `grades` | `(value, year, semester)` | compound | поиск должников (Q4) |
| `grades` | `(student_id, course_id)` | compound | история попыток по курсу |

Compound-индексы построены по правилу ESR (Equality → Sort → Range):
ведущим ставим поле, по которому фильтруется равенство (student_id /
course_id / professor_id), затем — поля периода и сортировки.

## 6. Типовые запросы

В `src/queries.py` реализовано **12** запросов; ниже — краткое описание
каждого. Все они доказательно покрывают сценарии из раздела 2.

| # | Запрос | Кто использует | Индекс |
| --- | --- | --- | --- |
| Q1 | Все оценки конкретного студента | Студент | `grades.by_student_date` |
| Q2 | Средний балл (GPA) студента | Студент / деканат | `grades.by_student_date` |
| Q3 | Топ-10 студентов по GPA | Деканат | `grades.by_student_date` |
| Q4 | Должники за семестр | Деканат | `grades.by_value_period` |
| Q5 | Средний балл по каждому курсу за семестр | Преподаватель / деканат | `grades.by_course_period` |
| Q6 | Ведомость группы за семестр | Деканат / куратор | `students.by_group` + `grades.by_student_date` |
| Q7 | Распределение оценок преподавателя | Преподаватель / зав. кафедрой | `grades.by_professor_period` |
| Q8 | Pass/fail по курсу | Преподаватель / деканат | `grades.by_course_period` |
| Q9 | Поиск студента по ФИО | Секретариат | `students.text_full_name` |
| Q10 | Рейтинг групп по среднему баллу | Деканат | `grades.by_student_date` + `students.by_group` |
| Q11 | Количество студентов на каждом курсе | Учебный отдел | `enrollments.by_course_period` |
| Q12 | Отличники за семестр (для стипендии) | Деканат | `grades.by_student_date` |

### Примеры pipeline-ов

**Q1 — оценки студента:**
```python
db.grades.aggregate([
    {"$match": {"student_id": student_id}},
    {"$lookup": {"from": "courses", "localField": "course_id",
                 "foreignField": "_id", "as": "course"}},
    {"$unwind": "$course"},
    {"$project": {"course": "$course.title", "value": 1,
                  "year": 1, "semester": 1, "date": 1}},
    {"$sort": {"date": -1}},
])
```

**Q4 — должники за семестр:**
```python
db.grades.aggregate([
    {"$match": {"value": 2, "year": year, "semester": semester}},
    {"$group": {"_id": "$student_id", "failed_courses": {"$sum": 1}}},
    {"$lookup": {"from": "students", "localField": "_id",
                 "foreignField": "_id", "as": "student"}},
    {"$unwind": "$student"},
    {"$sort": {"failed_courses": -1}},
])
```

**Q9 — текстовый поиск студента:**
```python
db.students.find(
    {"$text": {"$search": "Иванов"}},
    {"score": {"$meta": "textScore"}, "full_name": 1, "email": 1},
).sort([("score", {"$meta": "textScore"})]).limit(20)
```

**Q12 — отличники (для стипендии):**
```python
db.grades.aggregate([
    {"$match": {"year": year, "semester": semester}},
    {"$group": {"_id": "$student_id",
                "min_grade": {"$min": "$value"},
                "max_grade": {"$max": "$value"},
                "avg_grade": {"$avg": "$value"},
                "n": {"$sum": 1}}},
    {"$match": {"min_grade": {"$gte": 4}, "max_grade": 5, "n": {"$gte": 3}}},
])
```

Остальные запросы — в файле `src/queries.py`.

## 7. Запуск проекта

```bash
poetry install
cp .env.example .env       # при необходимости поправить MONGO_URI

# Полный цикл: создать коллекции, индексы, наполнить данными, выполнить запросы
poetry run python -m src.main

# Только перезапустить запросы на существующих данных
poetry run python -m src.main --no-seed --only-queries
```

Для локального запуска MongoDB достаточно:
```bash
docker run -d --name mongo-hw -p 27017:27017 mongo:7
```

## 8. Структура проекта

```
MongoDB_homework/
├── pyproject.toml          # Poetry: pymongo, faker, python-dotenv
├── poetry.lock
├── .env.example
├── REPORT.md               # этот отчёт
└── src/
    ├── db.py               # подключение к MongoDB
    ├── schema.py           # JSON Schema валидаторы для 6 коллекций
    ├── indexes.py          # все вторичные индексы
    ├── seed.py             # генерация тестовых данных через Faker
    ├── queries.py          # 12 типовых запросов
    └── main.py             # точка входа: schemas → indexes → seed → queries
```

## 9. Итоги по критериям

| Критерий | Где реализовано |
| --- | --- |
| Структура базы данных (20 б.) | 6 коллекций, обоснование embedding vs referencing (раздел 3), JSON Schema валидаторы в `src/schema.py` |
| Наличие схемы (10 б.) | Раздел 4 (диаграмма) + JSON-описание каждой коллекции в разделе 3.1 |
| Наличие индексов (10 б.) | `src/indexes.py` (20 индексов, включая unique, compound и text); таблица в разделе 5 с обоснованием |
| 10 запросов × 3 б. (30 б.) | `src/queries.py` — 12 запросов с описанием use case и используемого индекса |
| **Итого**: 70 б. | |
