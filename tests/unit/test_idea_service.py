import pytest
import json
from unittest.mock import MagicMock, patch

from src.services.idea_service import IdeaGenerationService


@pytest.fixture
def service():
    return IdeaGenerationService()


class TestNormalizeIdea:
    """Test the _normalize_idea method."""

    def test_complete_idea(self, service: IdeaGenerationService):
        idea = {
            "title": "Test Idea",
            "description": "A test description",
            "rationale": "Because reasons",
            "target_cpc": "H01L21/00",
            "inspired_by": ["US-123", "US-456"],
            "novelty_score": 0.85,
        }
        result = service._normalize_idea(idea)
        assert result["title"] == "Test Idea"
        assert result["description"] == "A test description"
        assert result["novelty_score"] == 0.85
        assert result["inspired_by"] == ["US-123", "US-456"]

    def test_missing_fields_defaults(self, service: IdeaGenerationService):
        idea = {"title": "Partial Idea"}
        result = service._normalize_idea(idea)
        assert result["title"] == "Partial Idea"
        assert result["description"] == ""
        assert result["rationale"] == ""
        assert result["target_cpc"] == ""
        assert result["inspired_by"] == []
        assert result["novelty_score"] == 0.5

    def test_empty_idea(self, service: IdeaGenerationService):
        result = service._normalize_idea({})
        assert result["title"] == "Untitled Idea"
        assert result["novelty_score"] == 0.5

    def test_novelty_score_clamping(self, service: IdeaGenerationService):
        # Above 1.0
        result = service._normalize_idea({"novelty_score": 1.5})
        assert result["novelty_score"] == 1.0

        # Below 0.0
        result = service._normalize_idea({"novelty_score": -0.3})
        assert result["novelty_score"] == 0.0

    def test_novelty_score_string(self, service: IdeaGenerationService):
        result = service._normalize_idea({"novelty_score": "0.75"})
        assert result["novelty_score"] == 0.75


class TestParseLlmResponse:
    """Test the _parse_llm_response method."""

    def test_valid_json_array(self, service: IdeaGenerationService):
        content = json.dumps([
            {"title": "Idea 1", "description": "Desc 1", "novelty_score": 0.8},
            {"title": "Idea 2", "description": "Desc 2", "novelty_score": 0.6},
        ])
        result = service._parse_llm_response(content, 5)
        assert len(result) == 2
        assert result[0]["title"] == "Idea 1"
        assert result[1]["title"] == "Idea 2"

    def test_json_in_code_block(self, service: IdeaGenerationService):
        content = "Here are the ideas:\n```json\n" + json.dumps([
            {"title": "Blocked Idea", "novelty_score": 0.7}
        ]) + "\n```"
        result = service._parse_llm_response(content, 5)
        assert len(result) == 1
        assert result[0]["title"] == "Blocked Idea"

    def test_json_in_generic_code_block(self, service: IdeaGenerationService):
        content = "```\n" + json.dumps([
            {"title": "Generic Block", "novelty_score": 0.9}
        ]) + "\n```"
        result = service._parse_llm_response(content, 5)
        assert len(result) == 1
        assert result[0]["title"] == "Generic Block"

    def test_count_limit(self, service: IdeaGenerationService):
        ideas = [{"title": f"Idea {i}", "novelty_score": 0.5} for i in range(10)]
        content = json.dumps(ideas)
        result = service._parse_llm_response(content, 3)
        assert len(result) == 3

    def test_invalid_json_fallback(self, service: IdeaGenerationService):
        content = "This is not valid JSON at all"
        result = service._parse_llm_response(content, 3)
        # Should return fallback ideas
        assert len(result) == 3
        assert all("title" in idea for idea in result)

    def test_non_array_json_fallback(self, service: IdeaGenerationService):
        content = json.dumps({"not": "an array"})
        result = service._parse_llm_response(content, 2)
        # Should fall back since it's not a list
        assert len(result) == 2


class TestFallbackIdeas:
    """Test the fallback idea generation."""

    def test_correct_count(self, service: IdeaGenerationService):
        result = service._generate_fallback_ideas(3)
        assert len(result) == 3

    def test_max_count(self, service: IdeaGenerationService):
        result = service._generate_fallback_ideas(8)
        assert len(result) == 8

    def test_all_have_required_fields(self, service: IdeaGenerationService):
        result = service._generate_fallback_ideas(5)
        for idea in result:
            assert "title" in idea
            assert "description" in idea
            assert "rationale" in idea
            assert "target_cpc" in idea
            assert "inspired_by" in idea
            assert "novelty_score" in idea
            assert 0.0 <= idea["novelty_score"] <= 1.0

    def test_ideas_are_unique(self, service: IdeaGenerationService):
        result = service._generate_fallback_ideas(5)
        titles = [idea["title"] for idea in result]
        assert len(set(titles)) == len(titles)


class TestBuildPrompt:
    """Test prompt construction."""

    def test_expiring_strategy(self, service: IdeaGenerationService):
        seeds = {"expiring_patents": [], "growth_areas": []}
        prompt = service._build_prompt(seeds, "expiring", 5, None)
        assert "Expiring Patent Opportunities" in prompt
        assert "Generate exactly 5" in prompt

    def test_combination_strategy(self, service: IdeaGenerationService):
        seeds = {"expiring_patents": [], "growth_areas": []}
        prompt = service._build_prompt(seeds, "combination", 3, None)
        assert "Cross-Domain Combinations" in prompt
        assert "Generate exactly 3" in prompt

    def test_improvement_strategy(self, service: IdeaGenerationService):
        seeds = {"expiring_patents": [], "growth_areas": []}
        prompt = service._build_prompt(seeds, "improvement", 5, None)
        assert "High-Impact Improvements" in prompt

    def test_with_context_text(self, service: IdeaGenerationService):
        seeds = {"expiring_patents": [], "growth_areas": []}
        prompt = service._build_prompt(seeds, "expiring", 5, "Focus on battery tech")
        assert "Focus on battery tech" in prompt
        assert "Additional Context" in prompt

    def test_with_seed_patents(self, service: IdeaGenerationService):
        seeds = {
            "expiring_patents": [
                {"patent_number": "US-123", "title": "Test Patent", "abstract": "About batteries", "cpc_codes": ["H01M"]}
            ],
            "growth_areas": [{"cpc_code": "G06N", "patent_count": 100}],
        }
        prompt = service._build_prompt(seeds, "expiring", 5, None)
        assert "US-123" in prompt
        assert "Test Patent" in prompt
        assert "G06N" in prompt

    def test_json_output_instruction(self, service: IdeaGenerationService):
        seeds = {"expiring_patents": [], "growth_areas": []}
        prompt = service._build_prompt(seeds, "expiring", 5, None)
        assert "valid JSON array" in prompt
        assert "title" in prompt
        assert "novelty_score" in prompt


class TestIdeaSchemas:
    """Test idea request/response schemas."""

    def test_idea_request_defaults(self):
        from src.api.schemas.ideas import IdeaRequest

        req = IdeaRequest()
        assert req.focus == "expiring"
        assert req.count == 5
        assert req.cpc_prefix is None
        assert req.context_text is None

    def test_idea_request_custom(self):
        from src.api.schemas.ideas import IdeaRequest

        req = IdeaRequest(cpc_prefix="H01L", focus="combination", count=8)
        assert req.cpc_prefix == "H01L"
        assert req.focus == "combination"
        assert req.count == 8

    def test_idea_request_validation(self):
        from src.api.schemas.ideas import IdeaRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            IdeaRequest(count=0)  # ge=1

        with pytest.raises(ValidationError):
            IdeaRequest(count=11)  # le=10

        with pytest.raises(ValidationError):
            IdeaRequest(focus="invalid")  # pattern match

    def test_generated_idea_schema(self):
        from src.api.schemas.ideas import GeneratedIdea

        idea = GeneratedIdea(
            title="Test",
            description="Desc",
            rationale="Why",
            target_cpc="H01L",
            inspired_by=["US-1"],
            novelty_score=0.8,
        )
        assert idea.title == "Test"
        assert idea.novelty_score == 0.8

    def test_generated_idea_score_bounds(self):
        from src.api.schemas.ideas import GeneratedIdea
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GeneratedIdea(
                title="T", description="D", rationale="R",
                target_cpc="X", novelty_score=1.5,
            )

    def test_idea_response(self):
        from src.api.schemas.ideas import IdeaResponse, GeneratedIdea

        resp = IdeaResponse(
            ideas=[
                GeneratedIdea(
                    title="T", description="D", rationale="R",
                    target_cpc="H01L", novelty_score=0.7,
                )
            ],
            focus="expiring",
            cpc_prefix="H01L",
            seed_patents_used=5,
            trends_used=3,
        )
        assert len(resp.ideas) == 1
        assert resp.seed_patents_used == 5

    def test_seed_response(self):
        from src.api.schemas.ideas import SeedResponse, SeedPatent, GrowthArea

        resp = SeedResponse(
            expiring_patents=[
                SeedPatent(
                    patent_number="US-1", title="T", abstract="A",
                    cpc_codes=["H01L"], cited_by_count=10,
                )
            ],
            growth_areas=[GrowthArea(cpc_code="G06N", patent_count=50)],
        )
        assert len(resp.expiring_patents) == 1
        assert resp.growth_areas[0].patent_count == 50
