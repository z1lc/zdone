import datetime

from app.models.tasks import Task, RecurrenceType


def test_calculate_skew_FROM_DUE_DATE():
    task = Task(
        title="Take out garbage",
        ideal_interval=7,
        last_completion=datetime.datetime(2020, 10, 1),
        recurrence_type=RecurrenceType.FROM_DUE_DATE,
    )

    # goes from 0 to 100, real quick
    assert 0 == task.calculate_skew(datetime.datetime(2020, 10, 1))
    assert 0 == task.calculate_skew(datetime.datetime(2020, 10, 3))
    assert 0 == task.calculate_skew(datetime.datetime(2020, 10, 7))
    assert 100 == task.calculate_skew(datetime.datetime(2020, 10, 8))
    assert 100 == task.calculate_skew(datetime.datetime(2020, 11, 1))


def test_calculate_skew_NONE_due():
    task = Task(
        title="Take out garbage",
        ideal_interval=-1,
        last_completion=datetime.datetime(2020, 10, 1),
        recurrence_type=RecurrenceType.NONE,
    )

    # goes from 0 to 100, real quick
    assert 0 == task.calculate_skew(datetime.datetime(2020, 9, 29))
    assert 0 == task.calculate_skew(datetime.datetime(2020, 9, 30))
    assert 100 == task.calculate_skew(datetime.datetime(2020, 10, 1))
    assert 100 == task.calculate_skew(datetime.datetime(2020, 10, 8))
    assert 100 == task.calculate_skew(datetime.datetime(2020, 11, 1))


def test_calculate_skew_NONE_completed():
    task = Task(
        title="Take out garbage",
        ideal_interval=0,
        last_completion=datetime.datetime(2020, 10, 1),
        recurrence_type=RecurrenceType.NONE,
    )

    # ideal_interval is 0, so this task is already done & skew should always be 0
    assert 0 == task.calculate_skew(datetime.datetime(2020, 9, 29))
    assert 0 == task.calculate_skew(datetime.datetime(2020, 11, 1))


def test_calculate_skew_FROM_COMPLETION_DATE():
    task = Task(
        title="Water plants",
        ideal_interval=4,
        last_completion=datetime.datetime(2020, 10, 1),
        recurrence_type=RecurrenceType.FROM_COMPLETION_DATE,
    )

    # slowly increases according to interval (& continues increasing once overdue)
    assert 0 == task.calculate_skew(datetime.datetime(2020, 10, 1))
    assert 1 / 4 == task.calculate_skew(datetime.datetime(2020, 10, 2))
    assert 3 / 4 == task.calculate_skew(datetime.datetime(2020, 10, 4))
    assert 1 == task.calculate_skew(datetime.datetime(2020, 10, 5))
    assert 31 / 4 == task.calculate_skew(datetime.datetime(2020, 11, 1))
