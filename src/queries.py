"""
12 типовых запросов к базе данных.

Каждая функция возвращает результат и сопровождается описанием use case
("кому нужно") и индексом, который её ускоряет.
"""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo.database import Database


# ---------------------------------------------------------------------------
# Q1. Все оценки конкретного студента (личный кабинет студента).
#     Индекс: grades.by_student_date
# ---------------------------------------------------------------------------
def q1_student_grades(db: Database, student_id: ObjectId) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"student_id": student_id}},
        {"$lookup": {
            "from": "courses",
            "localField": "course_id",
            "foreignField": "_id",
            "as": "course",
        }},
        {"$unwind": "$course"},
        {"$project": {
            "_id": 0,
            "course": "$course.title",
            "code": "$course.code",
            "value": 1,
            "year": 1,
            "semester": 1,
            "type": 1,
            "date": 1,
        }},
        {"$sort": {"date": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q2. Средний балл (GPA) конкретного студента (личный кабинет, рейтинги).
#     Индекс: grades.by_student_date (по student_id ведущий)
# ---------------------------------------------------------------------------
def q2_student_gpa(db: Database, student_id: ObjectId) -> dict[str, Any] | None:
    pipeline = [
        {"$match": {"student_id": student_id}},
        {"$group": {
            "_id": "$student_id",
            "gpa": {"$avg": "$value"},
            "total_grades": {"$sum": 1},
        }},
    ]
    result = list(db.grades.aggregate(pipeline))
    return result[0] if result else None


# ---------------------------------------------------------------------------
# Q3. Топ-10 студентов по среднему баллу (отчёт деканата).
#     Индекс: grades.by_student_date
# ---------------------------------------------------------------------------
def q3_top_students(db: Database, limit: int = 10) -> list[dict[str, Any]]:
    pipeline = [
        {"$group": {"_id": "$student_id", "gpa": {"$avg": "$value"}, "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 5}}},  # отсеять случайных
        {"$sort": {"gpa": -1}},
        {"$limit": limit},
        {"$lookup": {
            "from": "students",
            "localField": "_id",
            "foreignField": "_id",
            "as": "student",
        }},
        {"$unwind": "$student"},
        {"$project": {
            "_id": 0,
            "student": "$student.full_name",
            "gpa": {"$round": ["$gpa", 2]},
            "grades_count": "$n",
        }},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q4. Студенты с академическими задолженностями за конкретный семестр
#     (двойки). Используется деканатом перед сессией.
#     Индекс: grades.by_value_period
# ---------------------------------------------------------------------------
def q4_students_with_debts(db: Database, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"value": 2, "year": year, "semester": semester}},
        {"$group": {"_id": "$student_id", "failed_courses": {"$sum": 1}}},
        {"$lookup": {
            "from": "students",
            "localField": "_id",
            "foreignField": "_id",
            "as": "student",
        }},
        {"$unwind": "$student"},
        {"$lookup": {
            "from": "groups",
            "localField": "student.group_id",
            "foreignField": "_id",
            "as": "group",
        }},
        {"$unwind": "$group"},
        {"$project": {
            "_id": 0,
            "student": "$student.full_name",
            "group": "$group.name",
            "failed_courses": 1,
        }},
        {"$sort": {"failed_courses": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q5. Средний балл по курсу (статистика для преподавателя/деканата).
#     Индекс: grades.by_course_period
# ---------------------------------------------------------------------------
def q5_average_per_course(db: Database, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"year": year, "semester": semester}},
        {"$group": {
            "_id": "$course_id",
            "avg_grade": {"$avg": "$value"},
            "students_n": {"$addToSet": "$student_id"},
        }},
        {"$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course",
        }},
        {"$unwind": "$course"},
        {"$project": {
            "_id": 0,
            "code": "$course.code",
            "title": "$course.title",
            "avg_grade": {"$round": ["$avg_grade", 2]},
            "students": {"$size": "$students_n"},
        }},
        {"$sort": {"avg_grade": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q6. Ведомость группы за семестр: список студентов с их средними.
#     Индексы: students.by_group + grades.by_student_date
# ---------------------------------------------------------------------------
def q6_group_report(db: Database, group_name: str, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"name": group_name}},
        {"$lookup": {
            "from": "students",
            "localField": "_id",
            "foreignField": "group_id",
            "as": "students",
        }},
        {"$unwind": "$students"},
        {"$lookup": {
            "from": "grades",
            "let": {"sid": "$students._id"},
            "pipeline": [
                {"$match": {
                    "$expr": {"$eq": ["$student_id", "$$sid"]},
                    "year": year,
                    "semester": semester,
                }},
            ],
            "as": "grades",
        }},
        {"$project": {
            "_id": 0,
            "student": "$students.full_name",
            "status": "$students.status",
            "avg_grade": {"$round": [{"$avg": "$grades.value"}, 2]},
            "grades_n": {"$size": "$grades"},
        }},
        {"$sort": {"avg_grade": -1}},
    ]
    return list(db.groups.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q7. Все оценки, выставленные конкретным преподавателем в конкретный семестр.
#     Индекс: grades.by_professor_period
# ---------------------------------------------------------------------------
def q7_professor_grades(
    db: Database, professor_id: ObjectId, year: int, semester: int
) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"professor_id": professor_id, "year": year, "semester": semester}},
        {"$group": {
            "_id": "$value",
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q8. Распределение оценок по курсу (pass/fail-ratio).
#     Индекс: grades.by_course_period
# ---------------------------------------------------------------------------
def q8_pass_fail_per_course(db: Database, course_code: str) -> dict[str, Any] | None:
    pipeline = [
        {"$match": {"code": course_code}},
        {"$lookup": {
            "from": "grades",
            "localField": "_id",
            "foreignField": "course_id",
            "as": "g",
        }},
        {"$unwind": "$g"},
        {"$group": {
            "_id": "$code",
            "title": {"$first": "$title"},
            "total": {"$sum": 1},
            "passed": {"$sum": {"$cond": [{"$gte": ["$g.value", 3]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$g.value", 2]}, 1, 0]}},
            "excellent": {"$sum": {"$cond": [{"$eq": ["$g.value", 5]}, 1, 0]}},
        }},
        {"$project": {
            "_id": 0,
            "code": "$_id",
            "title": 1,
            "total": 1,
            "passed": 1,
            "failed": 1,
            "excellent": 1,
            "pass_rate": {"$round": [{"$divide": ["$passed", "$total"]}, 3]},
        }},
    ]
    result = list(db.courses.aggregate(pipeline))
    return result[0] if result else None


# ---------------------------------------------------------------------------
# Q9. Поиск студента по фамилии (личный кабинет деканата/секретариата).
#     Индекс: students.text_full_name
# ---------------------------------------------------------------------------
def q9_search_student(db: Database, query: str) -> list[dict[str, Any]]:
    return list(db.students.find(
        {"$text": {"$search": query}},
        {"score": {"$meta": "textScore"}, "full_name": 1, "email": 1, "status": 1, "group_id": 1},
    ).sort([("score", {"$meta": "textScore"})]).limit(20))


# ---------------------------------------------------------------------------
# Q10. Рейтинг групп по среднему баллу (отчёт деканата).
#      Использует $lookup + $group по двум коллекциям.
# ---------------------------------------------------------------------------
def q10_groups_ranking(db: Database, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"year": year, "semester": semester}},
        {"$lookup": {
            "from": "students",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student",
        }},
        {"$unwind": "$student"},
        {"$group": {
            "_id": "$student.group_id",
            "avg_grade": {"$avg": "$value"},
            "students_n": {"$addToSet": "$student._id"},
        }},
        {"$lookup": {
            "from": "groups",
            "localField": "_id",
            "foreignField": "_id",
            "as": "group",
        }},
        {"$unwind": "$group"},
        {"$project": {
            "_id": 0,
            "group": "$group.name",
            "faculty": "$group.faculty",
            "avg_grade": {"$round": ["$avg_grade", 2]},
            "students": {"$size": "$students_n"},
        }},
        {"$sort": {"avg_grade": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q11. Список курсов с количеством записанных студентов (для деканата).
#      Индекс: enrollments.by_course_period
# ---------------------------------------------------------------------------
def q11_course_enrollments(db: Database, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"year": year, "semester": semester}},
        {"$group": {"_id": "$course_id", "students": {"$sum": 1}}},
        {"$lookup": {
            "from": "courses",
            "localField": "_id",
            "foreignField": "_id",
            "as": "course",
        }},
        {"$unwind": "$course"},
        {"$project": {
            "_id": 0,
            "code": "$course.code",
            "title": "$course.title",
            "students": 1,
        }},
        {"$sort": {"students": -1}},
    ]
    return list(db.enrollments.aggregate(pipeline))


# ---------------------------------------------------------------------------
# Q12. Отличники — студенты, у которых все оценки за период >= 4 и хотя бы
#      одна 5 (для назначения повышенной стипендии).
#      Индекс: grades.by_student_course / by_student_date
# ---------------------------------------------------------------------------
def q12_honor_students(db: Database, year: int, semester: int) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"year": year, "semester": semester}},
        {"$group": {
            "_id": "$student_id",
            "min_grade": {"$min": "$value"},
            "max_grade": {"$max": "$value"},
            "avg_grade": {"$avg": "$value"},
            "n": {"$sum": 1},
        }},
        {"$match": {"min_grade": {"$gte": 4}, "max_grade": 5, "n": {"$gte": 3}}},
        {"$lookup": {
            "from": "students",
            "localField": "_id",
            "foreignField": "_id",
            "as": "student",
        }},
        {"$unwind": "$student"},
        {"$project": {
            "_id": 0,
            "student": "$student.full_name",
            "avg_grade": {"$round": ["$avg_grade", 2]},
            "grades_n": "$n",
        }},
        {"$sort": {"avg_grade": -1}},
    ]
    return list(db.grades.aggregate(pipeline))


QUERIES = [
    ("Q1", "Все оценки студента", q1_student_grades),
    ("Q2", "Средний балл (GPA) студента", q2_student_gpa),
    ("Q3", "Топ-10 студентов по GPA", q3_top_students),
    ("Q4", "Студенты с задолженностями за семестр", q4_students_with_debts),
    ("Q5", "Средний балл по каждому курсу за семестр", q5_average_per_course),
    ("Q6", "Ведомость группы за семестр", q6_group_report),
    ("Q7", "Распределение оценок преподавателя за семестр", q7_professor_grades),
    ("Q8", "Pass/fail статистика по курсу", q8_pass_fail_per_course),
    ("Q9", "Поиск студента по ФИО (text index)", q9_search_student),
    ("Q10", "Рейтинг групп по среднему баллу", q10_groups_ranking),
    ("Q11", "Количество студентов на каждом курсе", q11_course_enrollments),
    ("Q12", "Отличники за семестр (для стипендии)", q12_honor_students),
]
