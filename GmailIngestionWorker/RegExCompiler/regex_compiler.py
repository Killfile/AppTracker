import yaml
import re
from typing import Dict, List

class RegexCompilerError(Exception):
    pass

class RegexCompiler:
    def __init__(self, yml_path: str):
        with open(yml_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self._validate_config()
        self.sub_components = self.config['sub_components']
        self.components = self._build_components()
        self.pattern_cache = {}

    def _validate_config(self):
        for key in ['sub_components', 'components', 'patterns']:
            if key not in self.config:
                raise RegexCompilerError(f"Missing required key: {key}")

    def _replace_anchors(self, s: str, lookup: Dict[str, str]) -> str:
        def replacer(match):
            anchor = match.group(1)
            if anchor in lookup:
                return lookup[anchor]
            raise RegexCompilerError(f"Undefined anchor: {anchor}")
        return re.sub(r'{{\s*(\w+)\s*}}', replacer, s)

    def _build_components(self) -> Dict[str, str]:
        comps = {}
        for name, val in self.config['components'].items():
            comps[name] = self._replace_anchors(val, self.sub_components)
        return comps
    
    def _parse_list_of_patterns(self, patterns: List[str]) -> Dict[str, str]:
        parsed_patterns = {}
        for i, pat in enumerate(patterns):
            key = f'key_{i}'
            parsed_patterns[key] = self._replace_anchors(pat, self.components)
        return parsed_patterns
    
    def _parse_dict_of_patterns(self, patterns: Dict[str, str]) -> Dict[str, str]:
        parsed_patterns = {}
        for key, pat in patterns.items():
            key = pat.get("key", key)
            value = pat.get("value", "")
            parsed_patterns[key] = self._replace_anchors(value, self.components)
        return parsed_patterns

    def _build_patterns(self) -> Dict[str, List[str]]:
        patterns = {}
        lookup = {**self.sub_components, **self.components}

        for pat_group, pat_list in self.config["patterns"].items():
            compiled_list = {}
            if isinstance(pat_list, dict):
                # If the pattern is a dictionary, parse it directly
                compiled_list = self._parse_dict_of_patterns(pat_list)
            elif isinstance(pat_list, list):
                # Otherwise, treat it as a list of patterns
                compiled_list = self._parse_list_of_patterns(pat_list)
            else:
                raise RegexCompilerError(f"Invalid pattern format for group '{pat_group}': {pat_list}")

           

            patterns[pat_group] = compiled_list
        return patterns

    def get_patterns(self) -> Dict[str, List[str]]:
        if not self.pattern_cache:
            self.pattern_cache = self._build_patterns()
        return self.pattern_cache

# Example usage:
# compiler = RegexCompiler('sample.yml')
# patterns = compiler.get_patterns()
# print(patterns)
