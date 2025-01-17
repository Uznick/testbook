from .exceptions import (
    TestbookExecuteResultNotFoundError,
    TestbookAttributeError,
    TestbookSerializeError,
    TestbookRuntimeError
)
from .utils import random_varname
from .translators import PythonTranslator


class TestbookObjectReference:
    def __init__(self, tb, name):
        self.tb = tb
        self._name: str = name

    @property
    def _type(self):
        return self.tb.value(f"type({self._name}).__name__")

    def __repr__(self):
        return repr(self.tb.value(f"repr({self._name})"))

    def __getattr__(self, name):
        if self.tb.value(f"hasattr({self._name}, '{name}')"):
            return TestbookObjectReference(self.tb, f"{self._name}.{name}")

        raise TestbookAttributeError(f"'{self._type}' object has no attribute {name}")

    def __eq__(self, rhs):
        return self.tb.value(
            "{lhs} == {rhs}".format(lhs=self._name, rhs=PythonTranslator.translate(rhs))
        )

    def __len__(self):
        return self.tb.value(f"len({self._name})")

    def __iter__(self):
        iterobjectname = f"___iter_object_{random_varname()}"
        self.tb.inject(f"""
            {iterobjectname} = iter({self._name})
        """)
        return TestbookObjectReference(self.tb, iterobjectname)

    def __next__(self):
        try:
            return self.tb.value(f"next({self._name})")
        except TestbookRuntimeError as e:
            if e.eclass is StopIteration:
                raise StopIteration
            else:
                raise

    def __getitem__(self, key):
        try:
            return self.tb.value(f"{self._name}.__getitem__({PythonTranslator.translate(key)})")
        except TestbookRuntimeError as e:
            if e.eclass is TypeError:
                raise TypeError(e.evalue)
            elif e.eclass is IndexError:
                raise IndexError(e.evalue)
            else:
                raise

    def __setitem__(self, key, value):
        try:
            return self.tb.inject("{name}[{key}] = {value}".format(
                name=self._name,
                key=PythonTranslator.translate(key),
                value=PythonTranslator.translate(value)
            ), pop=True)
        except TestbookRuntimeError as e:
            if e.eclass is TypeError:
                raise TypeError(e.evalue)
            elif e.eclass is IndexError:
                raise IndexError(e.evalue)
            else:
                raise

    def __contains__(self, item):
        return self.tb.value(f"{self._name}.__contains__({PythonTranslator.translate(item)})")

    def __call__(self, *args, **kwargs):
        code = self.tb._construct_call_code(self._name, args, kwargs)
        try:
            return self.tb.value(code)
        except TestbookExecuteResultNotFoundError:
            # No return value from function call
            pass
        except TestbookSerializeError as e:
            return TestbookObjectReference(self.tb, e.save_varname)

    def resolve(self):
        return self.tb.value(self._name)
