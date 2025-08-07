import pytest
from unittest.mock import mock_open, patch
import yaml
from GmailIngestionWorker.RegExCompiler.regex_compiler import RegexCompiler, RegexCompilerError

# Sample YAML config for testing
SAMPLE_YAML = '''
sub_components:
  word: '\\w+'
  space: '\\s+'
components:
  phrase: '{{word}}{{space}}{{word}}'
patterns:
  test_group:
    phrase: 
      key: 'phrase'
      value: '^{{phrase}}$'

'''


SIMPLE_YAML = '''
sub_components:
  word: '\\w+'
  space: '\\s+'
components:
  phrase: '{{word}}{{space}}{{word}}'
patterns:
  test_group:
    - '^{{phrase}}$'

'''

@pytest.fixture
def mock_yaml_file():
    m = mock_open(read_data=SAMPLE_YAML)
    with patch('builtins.open', m):
        yield


@pytest.fixture
def mock_simple_yaml():
    m = mock_open(read_data=SIMPLE_YAML)
    with patch('builtins.open', m):
        yield

@pytest.fixture
def valid_config_path():
    return 'dummy_path.yml'


def test_successful_compilation(valid_config_path, mock_yaml_file):
    compiler = RegexCompiler(valid_config_path)
    patterns = compiler.get_patterns()
    assert 'test_group' in patterns
    assert patterns['test_group']['phrase'] == r'^\w+\s+\w+$'


def test_missing_key_raises(valid_config_path, mock_yaml_file):
    bad_yaml = '''
sub_components:
  word: '\\w+'
patterns:
  test_group:
    - '^{{word}}$'
'''
    m = mock_open(read_data=bad_yaml)
    with patch('builtins.open', m):
        with pytest.raises(RegexCompilerError) as exc:
            RegexCompiler(valid_config_path)
        assert 'Missing required key' in str(exc.value)


def test_undefined_anchor_raises(valid_config_path, mock_yaml_file):
    bad_yaml = '''
sub_components:
  word: '\\w+'
components:
  phrase: '{{not_defined}}'
patterns:
  test_group:
    - '^{{phrase}}$'
'''
    m = mock_open(read_data=bad_yaml)
    with patch('builtins.open', m):
        with pytest.raises(RegexCompilerError) as exc:
            RegexCompiler(valid_config_path)
        assert 'Undefined anchor' in str(exc.value)


def test_get_patterns_caching(valid_config_path, mock_simple_yaml):
    compiler = RegexCompiler(valid_config_path)
    patterns1 = compiler.get_patterns()
    patterns2 = compiler.get_patterns()
    # Should be the same object (cached)
    assert patterns1 is patterns2
    # Changing the returned dict should affect subsequent calls
    patterns1["test_group"]["key_1"] = "extra_pattern"
    patterns3 = compiler.get_patterns()
    assert True == True
    assert "extra_pattern" in patterns3["test_group"].values()


