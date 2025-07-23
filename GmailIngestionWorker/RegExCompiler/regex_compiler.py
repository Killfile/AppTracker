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

    def _build_patterns(self) -> Dict[str, List[str]]:
        patterns = {}
        lookup = {**self.sub_components, **self.components}

        for pat_group, pat_list in self.config["patterns"].items():
            compiled_list = []
            for pat in pat_list:
                compiled_list.append(self._replace_anchors(pat, lookup))
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
