"""
Создание вторичных индексов.

Каждый индекс мотивирован конкретным запросом из src/queries.py
(см. блок "ИНДЕКСЫ" в REPORT.md).
"""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.database import Database

INDEX_PLAN: dict[str, list[dict]] = {
    "students": [
        {"keys": [("email", ASCENDING)], "unique": True, "name": "uniq_email"},
        {"keys": [("group_id", ASCENDING)], "name": "by_group"},
        {"keys": [("status", ASCENDING)], "name": "by_status"},
        {"keys": [("enrollment_year", ASCENDING)], "name": "by_year"},
        {"keys": [("full_name", TEXT)], "name": "text_full_name"},
    ],
    "professors": [
        {"keys": [("email", ASCENDING)], "unique": True, "name": "uniq_email"},
        {"keys": [("department", ASCENDING)], "name": "by_department"},
    ],
    "courses": [
        {"keys": [("code", ASCENDING)], "unique": True, "name": "uniq_code"},
        {"keys": [("department", ASCENDING)], "name": "by_department"},
        {"keys": [("title", TEXT)], "name": "text_title"},
    ],
    "groups": [
        {"keys": [("name", ASCENDING)], "unique": True, "name": "uniq_name"},
        {"keys": [("faculty", ASCENDING), ("year", ASCENDING)], "name": "by_faculty_year"},
    ],
    "enrollments": [
        {
            "keys": [
                ("student_id", ASCENDING),
                ("course_id", ASCENDING),
                ("year", ASCENDING),
                ("semester", ASCENDING),
            ],
            "unique": True,
            "name": "uniq_student_course_period",
        },
        {"keys": [("course_id", ASCENDING), ("year", ASCENDING), ("semester", ASCENDING)],
         "name": "by_course_period"},
        {"keys": [("professor_id", ASCENDING), ("year", ASCENDING), ("semester", ASCENDING)],
         "name": "by_professor_period"},
    ],
    "grades": [
        # Для "получить все оценки студента" и расчёта среднего.
        {"keys": [("student_id", ASCENDING), ("date", DESCENDING)], "name": "by_student_date"},
        # Для "статистика по курсу за период".
        {"keys": [("course_id", ASCENDING), ("year", ASCENDING), ("semester", ASCENDING)],
         "name": "by_course_period"},
        # Для отчётов преподавателя.
        {"keys": [("professor_id", ASCENDING), ("year", ASCENDING), ("semester", ASCENDING)],
         "name": "by_professor_period"},
        # Для запросов "студенты с долгами" — поиск оценок == 2.
        {"keys": [("value", ASCENDING), ("year", ASCENDING), ("semester", ASCENDING)],
         "name": "by_value_period"},
        # Поиск двойников: один студент + один курс (history of attempts).
        {"keys": [("student_id", ASCENDING), ("course_id", ASCENDING)],
         "name": "by_student_course"},
    ],
}


def apply_indexes(db: Database) -> None:
    for collection, plans in INDEX_PLAN.items():
        coll = db[collection]
        for plan in plans:
            options = {k: v for k, v in plan.items() if k not in {"keys"}}
            name = coll.create_index(plan["keys"], **options)
            print(f"[index] {collection}.{name}")
