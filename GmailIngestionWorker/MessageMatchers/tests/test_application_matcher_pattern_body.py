import pytest
from unittest.mock import MagicMock
from MessageMatchers.application_matcher__pattern_body import ApplicationMatcher_PatternBody
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message
import builtins
import yaml
from unittest.mock import patch

class TestApplicationMatcher_PatternBody:
    @pytest.fixture
    def matcher(self):
        patterns = [
            r"(?i)position[:\s-]+([A-Za-z0-9 ,:.'\-/]+)",
            r"(?i)applied for the ([A-Za-z0-9 ,:.'\-/]+) position"
        ]
        # Mock open and yaml.safe_load so ApplicationMatcher_PatternBody() init never fails and loads our patterns

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = ""  # content doesn't matter, as safe_load is mocked


        with patch("builtins.open", return_value=mock_file), \
            patch("yaml.safe_load", return_value={"application_patterns": patterns}):
            matcher = ApplicationMatcher_PatternBody()
        matcher.patterns = patterns
        return matcher

    def make_message(self, body):
        msg = MagicMock(spec=Message)
        msg.message_body = body
        return msg

    def test_match_position_pattern(self, matcher):
        msg = self.make_message("We are excited to offer you the position: Senior Developer")
        match, found = matcher.process(msg)
        assert found
        assert match.match_string == "Senior Developer"
        assert "position" in match.match_detail

    def test_match_applied_for_pattern(self, matcher):
        msg = self.make_message("You have applied for the Administrative Assistant position.")
        match: MessageMatch
        found: bool
        match, found = matcher.process(msg)
        assert found
        assert match.match_string == "Administrative Assistant"
        assert "applied for the" in match.match_detail

    def test_no_match(self, matcher):
        msg = self.make_message("Thank you for your interest.")
        match, found = matcher.process(msg)
        assert not found
        assert match.match_string == ""
        assert match.match_detail == "No Match"
