import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, TypeGuard
from google import genai
from google.genai import types
from app.config import get_settings

logger = logging.getLogger("luxe_tech.gemini")
settings = get_settings()

_PROPHECY_STAGES = ("current", "emerging", "accelerating", "mainstream", "next")


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _valid_trend_analysis(value: Any) -> TypeGuard[Dict[str, Any]]:
    if not isinstance(value, dict):
        return False
    dna = value.get("visual_dna")
    return (
        all(isinstance(value.get(key), str) and value[key].strip() for key in (
            "summary", "consumer_interpretation", "future_direction"
        ))
        and isinstance(dna, dict)
        and all(_string_list(dna.get(key)) for key in (
            "colors", "materials", "textures", "silhouettes", "patterns"
        ))
        and _string_list(value.get("product_opportunities"))
        and _string_list(value.get("retail_implications"))
    )


def _valid_image_analysis(value: Any) -> TypeGuard[Dict[str, Any]]:
    if not isinstance(value, dict):
        return False
    analysis = value.get("image_analysis")
    return (
        isinstance(analysis, dict)
        and _string_list(analysis.get("dominant_colors"))
        and _string_list(analysis.get("materials"))
        and all(isinstance(analysis.get(key), str) and analysis[key].strip() for key in (
            "silhouette", "pattern", "texture"
        ))
        and isinstance(value.get("trend_interpretation"), str)
        and bool(value["trend_interpretation"].strip())
        and _string_list(value.get("possible_categories"))
    )


def _valid_product_opportunities(value: Any) -> TypeGuard[List[Dict[str, Any]]]:
    if not isinstance(value, list) or len(value) != 3:
        return False
    required_strings = (
        "name", "category", "description", "material", "silhouette", "color",
        "target_consumer", "design_rationale",
    )
    for item in value:
        if not isinstance(item, dict):
            return False
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in required_strings):
            return False
    return True


def _valid_prophecy(value: Any) -> TypeGuard[List[Dict[str, Any]]]:
    if not isinstance(value, list) or len(value) != len(_PROPHECY_STAGES):
        return False
    for stage, item in zip(_PROPHECY_STAGES, value):
        if not isinstance(item, dict) or item.get("stage") != stage:
            return False
        if not all(isinstance(item.get(key), str) and item[key].strip() for key in (
            "forecast", "opportunity", "risk"
        )):
            return False
        if not _string_list(item.get("evidence")):
            return False
    return True


def _valid_retail_interpretation(value: Any) -> TypeGuard[Dict[str, Any]]:
    required = ("interpretation", "assortment_recommendation", "price_tier")
    return isinstance(value, dict) and all(
        isinstance(value.get(key), str) and value[key].strip()
        for key in required
    )


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"
        self._client = genai.Client(api_key=self.api_key) if self.is_available else None
        self._cache: Dict[str, Any] = {}

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _cache_key(self, prefix: str, payload: Any) -> str:
        dumped = json.dumps(payload, sort_keys=True)
        return f"{prefix}:{hashlib.sha256(dumped.encode()).hexdigest()}"

    async def _call_gemini(self, prompt: str, image_bytes: Optional[bytes] = None, mime_type: str = "image/jpeg") -> Optional[Any]:
        if not self.is_available or self._client is None:
            return None

        contents: List[Any] = [prompt]
        if image_bytes:
            contents.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    top_p=0.8,
                ),
            )
            response_text = response.text
            if not response_text:
                logger.warning("Gemini returned an empty response.")
                return None
            result = json.loads(response_text)
            if isinstance(result, (dict, list)):
                return result
            logger.warning("Gemini returned JSON with an unexpected top-level type.")
        except json.JSONDecodeError:
            logger.warning("Gemini returned invalid JSON; using local fallback.")
        except Exception as exc:
            logger.warning(
                "Gemini API call failed (%s); using local fallback.",
                type(exc).__name__,
            )

        return None

    async def analyze_trend(self, trend_name: str, category: str, season: str, signals: Dict[str, float]) -> Dict[str, Any]:
        cache_k = self._cache_key("trend_analysis", {"name": trend_name, "cat": category, "season": season, "signals": signals})
        if cache_k in self._cache:
            return self._cache[cache_k]

        prompt = f"""You are the senior fashion intelligence analyst for LUXE.TECH.
Analyze this emerging trend and return structured JSON matching this exact schema:
{{
  "summary": "Precise luxury market summary explaining why this trend matters.",
  "visual_dna": {{
    "colors": ["List of 3 to 5 precise color names/codes"],
    "materials": ["List of 3 to 5 high-spec textile names"],
    "textures": ["List of tactile descriptions"],
    "silhouettes": ["List of silhouette cut directions"],
    "patterns": ["List of pattern motifs or structural repeat codes"]
  }},
  "consumer_interpretation": "Demographic and psychographic consumer mindset driving this.",
  "product_opportunities": ["Top 3 commercial product silhouettes to develop"],
  "retail_implications": ["Key retail assortment and pricing strategies"],
  "future_direction": "Projected trajectory into the subsequent season"
}}

Input:
Trend Name: {trend_name}
Category: {category}
Season: {season}
Signal Strengths: {json.dumps(signals)}
"""

        result = await self._call_gemini(prompt)

        is_ai_generated = _valid_trend_analysis(result)
        if not is_ai_generated:
            if result is not None:
                logger.warning("Gemini trend response did not match the expected schema; using local fallback.")
            result = {
                "summary": f"{trend_name} represents a progressive synthesis within {category} for {season}, propelled by strong runway and social signal alignment.",
                "visual_dna": {
                    "colors": [f"{trend_name} Chroma", "Mineral Graphite", "Vapour Grey", "Luminescent Tint"],
                    "materials": ["Technical organza", "Double-faced virgin wool", "Bonded nylon membrane", "Liquid viscose"],
                    "textures": ["Micro-ribbed translucency", "Matte crepe tactility", "High-gauge smoothness"],
                    "silhouettes": ["Fluid architectural volume", "Dropped shoulder cocoon", "Ergonomic tailoring"],
                    "patterns": ["Subtle generative gradient", "Engineered micro-grid", "Monochrome planar solids"]
                },
                "consumer_interpretation": "Driven by post-digital professionals prioritizing tactile tactility, elevated performance, and modern comfort.",
                "product_opportunities": [
                    f"{trend_name} Relaxed Unstructured Blazer",
                    "Modular Technical Trench Coat",
                    "Layered Translucent Popover Shirt"
                ],
                "retail_implications": [
                    "High initial full-price sell-through potential in tier-1 flagships",
                    "Test controlled capsule batches before expanding SKU breadth"
                ],
                "future_direction": f"Expected evolution into mainstream premium contemporary assortments over the next 12-18 months."
            }

        result["data_status"] = "ai_generated" if is_ai_generated else "demo"
        self._cache[cache_k] = result
        return result

    async def analyze_image(self, image_bytes: bytes, mime_type: str, vision_features: Dict[str, Any]) -> Dict[str, Any]:
        cache_k = self._cache_key("image_analysis", {
            "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
            "mime_type": mime_type,
            "features": vision_features,
        })
        if cache_k in self._cache:
            return self._cache[cache_k]

        prompt = f"""You are the LUXE.TECH vision intelligence model. Analyze this fashion garment or editorial image.
Local computer vision engine has already extracted these low-level features:
{json.dumps(vision_features)}

Return structured JSON strictly matching:
{{
  "image_analysis": {{
    "dominant_colors": ["Color names corresponding to extracted palettes"],
    "materials": ["Identified or probable fabrics/textiles"],
    "silhouette": "Dominant garment silhouette description",
    "pattern": "Observed surface pattern or solid description",
    "texture": "Tactile surface texture"
  }},
  "trend_interpretation": "Fashion editorial interpretation connecting this visual to broader cultural shifts.",
  "possible_categories": ["Outerwear", "Tailoring", "Streetwear", "etc."]
}}
"""
        result = await self._call_gemini(prompt, image_bytes=image_bytes, mime_type=mime_type)

        is_ai_generated = _valid_image_analysis(result)
        if not is_ai_generated:
            if result is not None:
                logger.warning("Gemini image response did not match the expected schema; using local fallback.")
            result = {
                "image_analysis": {},
                "trend_interpretation": (
                    "Local image metrics were extracted. Fashion interpretation is unavailable "
                    "because no valid vision-provider result was returned."
                ),
                "possible_categories": [],
            }

        result["data_status"] = "ai_generated" if is_ai_generated else "demo"
        self._cache[cache_k] = result
        return result

    async def generate_trend_dna(self, trend_name: str, signals: Dict[str, float]) -> Dict[str, Any]:
        analysis = await self.analyze_trend(trend_name, "Concept", "SS 2027", signals)
        return {
            "trend_name": trend_name,
            "visual_dna": analysis.get("visual_dna", {}),
            "summary": analysis.get("summary", ""),
            "ai_interpretation": analysis.get("consumer_interpretation", ""),
            "data_status": analysis.get("data_status", "demo"),
        }

    async def generate_product_opportunities(self, trend_name: str, visual_dna: Dict[str, Any], target_consumer: str) -> List[Dict[str, Any]]:
        cache_k = self._cache_key("product_opps", {"name": trend_name, "dna": visual_dna, "consumer": target_consumer})
        if cache_k in self._cache:
            return self._cache[cache_k]

        prompt = f"""Generate 3 clearly hypothetical luxury apparel/accessory design concepts for the trend '{trend_name}'.
Target Consumer: {target_consumer}
Visual DNA: {json.dumps(visual_dna)}

Return JSON array of objects:
[
  {{
    "name": "Product Name",
    "category": "Apparel Category",
    "description": "Design concept description, not a product listing",
    "material": "Primary specification material",
    "silhouette": "Exact silhouette cut",
    "color": "Colorway",
    "target_consumer": "{target_consumer}",
    "design_rationale": "Explain only the design choices"
  }}
]
Do not claim sales, demand, search interest, market whitespace, performance, or commercial opportunity.
Do not include scores, metrics, or evidence claims.
"""
        result = await self._call_gemini(prompt)

        is_ai_generated = _valid_product_opportunities(result)
        if not is_ai_generated:
            if result is not None:
                logger.warning("Gemini product response did not match the expected schema; returning no concepts.")
            self._cache[cache_k] = []
            return []

        concepts = [
            {
                key: item[key]
                for key in (
                    "name", "category", "description", "material", "silhouette",
                    "color", "target_consumer", "design_rationale",
                )
            }
            for item in result
        ]
        self._cache[cache_k] = concepts
        return concepts

    async def generate_retail_interpretation(self, trend_name: str, signals: Dict[str, float], region: str) -> Dict[str, Any]:
        cache_k = self._cache_key("retail_interpretation", {
            "name": trend_name, "signals": signals, "region": region
        })
        if cache_k in self._cache:
            return self._cache[cache_k]

        prompt = f"""Interpret the supplied retail signal summary for the fashion trend '{trend_name}' in '{region}'.
Use only the provided signal values. Do not invent retailer counts, sales, markdowns, price points, growth rates, or external evidence.
If the supplied values do not support a conclusion, state that clearly.
Return JSON with non-empty string fields 'interpretation', 'assortment_recommendation', and 'price_tier'.
Signal summary: {json.dumps(signals, sort_keys=True)}
"""
        result = await self._call_gemini(prompt)
        if _valid_retail_interpretation(result):
            result["data_status"] = "ai_generated"
        else:
            result = {
                "interpretation": "No AI interpretation is available. This local fallback does not infer retail performance.",
                "assortment_recommendation": "Review verified regional demand and growth observations before making assortment decisions.",
                "price_tier": "insufficient_data",
                "data_status": "demo",
            }
        result["trend_name"] = trend_name
        result["region"] = region
        self._cache[cache_k] = result
        return result

    async def generate_prophecy(self, trend_name: str, signals: Dict[str, float], forecast_value: Optional[float]) -> List[Dict[str, Any]]:
        cache_k = self._cache_key("prophecy", {"name": trend_name, "signals": signals, "forecast": forecast_value})
        if cache_k in self._cache:
            return self._cache[cache_k]

        prompt = f"""Generate a 5-stage evolutionary prophecy trajectory for the fashion trend '{trend_name}'.
Observed signal strengths: {json.dumps(signals)}
Statistical forecast index: {forecast_value}

Return JSON array of 5 stage objects for:
'current', 'emerging', 'accelerating', 'mainstream', 'next'.
Each object format:
{{
  "stage": "stage_name",
  "forecast": "Hypothetical scenario, not a prediction of validated accuracy",
  "evidence": ["Only supplied observation/source-level values; use [] if none directly supports the statement"],
  "opportunity": "Actionable commercial opportunity",
  "risk": "Potential risk, explicitly framed as a hypothesis"
}}
Do not invent sales, consumer demand, search interest, social reach, or external evidence.
"""
        result = await self._call_gemini(prompt)

        is_ai_generated = _valid_prophecy(result)
        if not is_ai_generated:
            if result is not None:
                logger.warning("Gemini prophecy response did not match the expected schema; returning no scenario.")
            self._cache[cache_k] = []
            return []

        stages = [
            {
                key: item[key]
                for key in ("stage", "forecast", "evidence", "opportunity", "risk")
            }
            | {"data_status": "ai_generated"}
            for item in result
        ]
        self._cache[cache_k] = stages
        return stages

    async def summarize_current_fashion(self) -> Dict[str, Any]:
        return {
            "title": "What's happening in fashion right now?",
            "headline": "Current fashion summary unavailable without verified source material.",
            "summary": "This demonstration summary does not represent a live global fashion index or verified market observations.",
            "metrics": {
                "runway": None,
                "social": None,
                "search": None,
                "retail": None,
                "culture": None
            },
            "data_status": "demo",
        }


gemini_service = GeminiService()
