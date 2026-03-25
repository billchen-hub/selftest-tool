from selftest.generator.test_builder import parse_ai_response, validate_test_code


def test_parse_python_code_block():
    response = '''Here is the test:
```python
import pytest

def test_example():
    assert 1 + 1 == 2
```
'''
    code = parse_ai_response(response)
    assert "def test_example" in code
    assert "assert 1 + 1 == 2" in code


def test_parse_no_code_block():
    response = """import pytest

def test_example():
    assert 1 == 1
"""
    code = parse_ai_response(response)
    assert "def test_example" in code


def test_parse_multiple_code_blocks():
    response = '''First block:
```python
import pytest
```

Second block:
```python
def test_foo():
    assert True == True
```
'''
    code = parse_ai_response(response)
    assert "import pytest" in code
    assert "def test_foo" in code


def test_validate_good_test_code():
    code = '''
import pytest

def test_foo():
    result = 42
    assert result == 42

def test_bar():
    with pytest.raises(ValueError, match="bad"):
        raise ValueError("bad")
'''
    issues = validate_test_code(code)
    assert len(issues) == 0


def test_validate_weak_assertion_is_not_none():
    code = '''
def test_foo():
    result = some_func()
    assert result is not None
'''
    issues = validate_test_code(code)
    assert any("weak assertion" in i.lower() for i in issues)


def test_validate_weak_assertion_true():
    code = '''
def test_foo():
    assert True
'''
    issues = validate_test_code(code)
    assert any("weak assertion" in i.lower() or "Weak" in i for i in issues)


def test_validate_no_assertions():
    code = '''
def test_foo():
    x = 1 + 1
'''
    issues = validate_test_code(code)
    assert any("no assertion" in i.lower() for i in issues)


def test_validate_no_test_functions():
    code = '''
def helper():
    return 42
'''
    issues = validate_test_code(code)
    assert any("no test functions" in i.lower() for i in issues)


def test_validate_syntax_error():
    code = "def test_foo(\n    assert True"
    issues = validate_test_code(code)
    assert any("syntax error" in i.lower() for i in issues)
