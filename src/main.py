"""
Точка входа: применяет схемы, индексы, наполняет данные и прогоняет все
12 типовых запросов с выводом результата в консоль.

Запуск:
    poetry run python -m src.main           # полный цикл
    poetry run python -m src.main --no-seed # без перезаполнения данных
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any

from bson import ObjectId

from src import queries
from src.db import get_db
from src.indexes import apply_indexes
from src.schema import apply_schemas
from src.seed import seed


def _json_default(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Не сериализуется: {type(obj)}")


def _dump(value: Any, *, limit: int = 5) -> str:
    if isinstance(value, list):
        head = value[:limit]
        suffix = f"  ... ещё {len(value) - limit}" if len(value) > limit else ""
        return json.dumps(head, ensure_ascii=False, indent=2, default=_json_default) + suffix
    return json.dumps(value, ensure_ascii=False, indent=2, default=_json_default)


def run_all_queries(db) -> None:
    student = db.students.find_one({"status": "active"})
    professor = db.professors.find_one()
    sample_group = db.groups.find_one()
    sample_course = db.courses.find_one()
    assert student and professor and sample_group and sample_course, "Сначала нужно засеять данные"

    print("\n" + "=" * 70)
    print("Q1. Все оценки конкретного студента")
    print("=" * 70)
    print(_dump(queries.q1_student_grades(db, student["_id"])))

    print("\n" + "=" * 70)
    print("Q2. Средний балл (GPA) студента")
    print("=" * 70)
    print(_dump(queries.q2_student_gpa(db, student["_id"])))

    print("\n" + "=" * 70)
    print("Q3. Топ-10 студентов")
    print("=" * 70)
    print(_dump(queries.q3_top_students(db)))

    print("\n" + "=" * 70)
    print("Q4. Студенты с задолженностями за 2025 г., 1 семестр")
    print("=" * 70)
    print(_dump(queries.q4_students_with_debts(db, 2025, 1)))

    print("\n" + "=" * 70)
    print("Q5. Средний балл по каждому курсу за 2025 г., 1 семестр")
    print("=" * 70)
    print(_dump(queries.q5_average_per_course(db, 2025, 1)))

    print("\n" + "=" * 70)
    print(f"Q6. Ведомость группы {sample_group['name']} за 2025 г., 1 семестр")
    print("=" * 70)
    print(_dump(queries.q6_group_report(db, sample_group["name"], 2025, 1)))

    print("\n" + "=" * 70)
    print(f"Q7. Распределение оценок преподавателя {professor['full_name']} за 2025/1")
    print("=" * 70)
    print(_dump(queries.q7_professor_grades(db, professor["_id"], 2025, 1)))

    print("\n" + "=" * 70)
    print(f"Q8. Pass/fail для курса {sample_course['code']}")
    print("=" * 70)
    print(_dump(queries.q8_pass_fail_per_course(db, sample_course["code"])))

    print("\n" + "=" * 70)
    last_name = student["full_name"].split()[0]
    print(f"Q9. Поиск студентов по фамилии «{last_name}»")
    print("=" * 70)
    print(_dump(queries.q9_search_student(db, last_name)))

    print("\n" + "=" * 70)
    print("Q10. Рейтинг групп по среднему баллу (2025 г., 1 семестр)")
    print("=" * 70)
    print(_dump(queries.q10_groups_ranking(db, 2025, 1)))

    print("\n" + "=" * 70)
    print("Q11. Количество студентов на каждом курсе (2025 г., 1 семестр)")
    print("=" * 70)
    print(_dump(queries.q11_course_enrollments(db, 2025, 1)))

    print("\n" + "=" * 70)
    print("Q12. Отличники за 2025 г., 1 семестр")
    print("=" * 70)
    print(_dump(queries.q12_honor_students(db, 2025, 1)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-seed", action="store_true", help="не перезаполнять данные")
    parser.add_argument("--only-queries", action="store_true", help="только запустить запросы")
    args = parser.parse_args()

    db = get_db()
    if not args.only_queries:
        apply_schemas(db)
        apply_indexes(db)
        if not args.no_seed:
            seed(db)
    run_all_queries(db)


if __name__ == "__main__":
    main()
