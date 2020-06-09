import inspect


def log(data: str) -> None:
    function_name = inspect.stack()[1][3]
    print(f"{function_name}: {data}")
