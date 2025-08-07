import pytest
from unittest.mock import MagicMock
from MessageMatchers.application_matcher__pattern_body import ApplicationMatcher_PatternBody
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message
from unittest.mock import patch

class TestApplicationMatcher_PatternBody:
    @pytest.fixture
    def matcher(self):
        patterns = [
            r"(?i)applied for the ([A-Za-z0-9 ,:.'\-/]+) position",
            r"(?i)offer you the position: ([A-Za-z0-9 ,:.'\-/]+)",
            r"overwhelming response to the ([\w,()\s\u00A0]*)(?:position|role|job|opening|opportunity|vacancy|title)+"
        ]
        # Mock open and yaml.safe_load so ApplicationMatcher_PatternBody() init never fails and loads our patterns

        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = ""  # content doesn't matter, as safe_load is mocked


        fake_config = {
            "sub_components": {},
            "components": {},
            "patterns": {},
            "application_patterns": patterns
        }
        with patch("builtins.open", return_value=mock_file), \
            patch("yaml.safe_load", return_value=fake_config):
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

    def test_real_world_example(self, matcher):
        # This is a real-world example that should match the new pattern
        msg = self.make_message("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">\n<html xmlns=\"http://www.w3.org/1999/xhtml\">\n    \n  <head>\n	  <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">\n	  <title>Thank you for your interest in Redflag AI</title>\n	      <style>\n      .AtsEmail p, .AtsEmail ol, .AtsEmail ul {\n        margin: 0;\n      }\n    </style>\n      </head>\n  \n  <body>\n    <table class=\"AtsEmail\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">\n    	<tr>\n        	<td align=\"left\">\n            	##- Yes! You can reply directly to this email and Maddie will get it. Just make sure it’s above this line so we can read it right. -##<br><br><p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">Hi Christopher,</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\"><br></p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">Thank you for your interest in Redflag AI!</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\"><br></p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">We received an overwhelming response to the Vice President of Engineering position, which makes us feel both humble and proud that so many talented individuals (like you!) want to join our team. This volume of response makes for an extremely competitive selection process. Although your background is impressive, we regret to inform you that we have decided to pursue other candidates for the position at this time.</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\"><br></p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">We greatly value our job candidates and invite you to review future job openings on our careers page. We hope you see another position that sparks your interest in the future and wish you the best in your career pursuits!</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\"><br></p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">Best wishes,</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">Redflag AI</p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\"><br></p>\n<p style=\"margin: 0; margin-bottom: 0px; margin-top: 0px;\">**This is an automated message - please do not reply directly. All replies will be filtered into an unmonitored inbox.**</p>\n            </td>\n    	</tr>\n    </table>\n  <img width=\"1px\" height=\"1px\" alt=\"\" src=\"https://email.app.bamboohr.com/o/eJyMkM-O6iAcRp-m7GqgLVgWLNTeeNuMmnHG-Gdj4FcITAQai058-4mJy1nM7kvOtzkHove34EAmF8PZ9QJzwwmpIK-4YTkh2uRK1iTvdckkZxQbohBEP8jweP7B9eeyqhiuEdzGFL3Qjw6f9tSqsO1Oi5a1Xyu8bo7fm0U7tn59V4e5VeHyC6NW7Xdu47pG_u8GKLd3WNoLuPlOLnk6HlbOvGdlk5UN6gVUU6QFmRakpphRiqwoTKlUUTDO6gIT1ZccFNU1rqXi3NApcn_Syyosh2GipFcx2usEokdXAfbqxkmy0csxqzBctAz6CXs9oiRmnx_nf6tZ-4aSDjKkZ5vXeuW5i-InAAD__z9tcj4\"></body>\n  \n</html>\n")
        match, found = matcher.process(msg)
        assert found
        assert match.match_string == "Vice President of Engineering"
        assert "overwhelming response to the" in match.match_detail
