"""
AI-powered lesson data extractor using Claude API.

This module provides intelligent extraction of lesson data from card text
using Claude's natural language understanding capabilities via Vertex AI.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from anthropic import AnthropicVertex

from ..models.lesson import LessonData


logger = logging.getLogger(__name__)


class AIExtractor:
    """
    AI-powered extractor for lesson data using Claude API via Vertex AI.

    This extractor uses Claude's natural language understanding to extract
    structured lesson data from unstructured card text, handling edge cases
    that are difficult to manage with regular expressions.

    Examples:
        >>> extractor = AIExtractor()
        >>> card_text = "11/01(土)20:00~21:00【第2回】Github林晃司マンツー編集"
        >>> lesson = extractor.extract_lesson(card_text, 2025)
        >>> lesson['student_name']
        '林晃司'
    """

    def __init__(self):
        """
        Initialize AIExtractor with Vertex AI client.

        Raises:
            ValueError: If required environment variables are not set
        """
        # Get configuration from environment
        self.project_id = os.getenv("ANTHROPIC_VERTEX_PROJECT_ID")
        self.region = os.getenv("CLOUD_ML_REGION", "global")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5@20250929")

        if not self.project_id:
            raise ValueError(
                "ANTHROPIC_VERTEX_PROJECT_ID environment variable is required"
            )

        # Initialize Vertex AI client
        try:
            self.client = AnthropicVertex(
                project_id=self.project_id,
                region=self.region
            )
            logger.info(
                f"AIExtractor initialized with project={self.project_id}, "
                f"region={self.region}, model={self.model}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {e}")
            raise

    def _create_extraction_prompt(self, card_texts: List[str], target_year: int) -> str:
        """
        Create prompt for extracting lesson data from card texts.

        Args:
            card_texts: List of lesson card texts
            target_year: Year for date context (e.g., 2025)

        Returns:
            Formatted prompt string
        """
        prompt = f"""あなたはレッスン管理システムのデータ抽出エキスパートです。

以下のレッスンカードテキストから情報を抽出し、JSON配列で返してください。

【重要な注意事項】
1. **生徒名の識別**: 人名のみを抽出してください
   - OK: 「林晃司」「土居一光」「柴田善司」
   - NG: 「最終レッスン」「最終レッ」「キャンセル」「キャンセ」「マンツー」
   - これらは生徒名ではなく、レッスンのステータスや種別です

2. **生徒名が存在しない場合**: student_nameに null を設定

3. **日付形式**: {target_year}年の日付として、YYYY-MM-DD形式で出力

4. **カテゴリ判定**:
   - 「マンツー」「専属レッスン」 → "専属レッスン"
   - 「初回レッスン」「初回」 → "初回レッスン"
   - 「エキスパート」 → "エキスパートコース"
   - その他 → "専属レッスン" (default)

5. **時間計算**: 開始時刻と終了時刻から時間(分)を計算

【レッスンカードテキスト】
"""

        for i, card_text in enumerate(card_texts, 1):
            prompt += f"\n{i}. {card_text}\n"

        prompt += f"""

【出力形式】
以下のJSON配列形式で出力してください：

```json
[
  {{
    "date": "YYYY-MM-DD",
    "student_name": "生徒名 または null",
    "category": "専属レッスン",
    "duration": 60,
    "index": 0
  }}
]
```

**注意**:
- 各カードに対応する要素を配列に含めてください
- index は元のカードテキストのインデックス (0始まり)
- 生徒名が判別できない、またはステータス語の場合は student_name を null に設定
- JSON以外の説明文は不要です。JSON配列のみを出力してください。
"""

        return prompt

    def extract_lessons_batch(
        self,
        card_texts: List[str],
        target_year: int,
        batch_size: int = 10
    ) -> List[Optional[LessonData]]:
        """
        Extract lesson data from multiple card texts in batches.

        Args:
            card_texts: List of lesson card texts
            target_year: Year for date context (e.g., 2025)
            batch_size: Number of cards to process in one API call

        Returns:
            List of extracted LessonData (or None if extraction failed)
        """
        results: List[Optional[LessonData]] = []

        # Process in batches
        for i in range(0, len(card_texts), batch_size):
            batch = card_texts[i:i + batch_size]
            batch_card_texts = card_texts[i:i + batch_size]

            try:
                batch_dict_results = self._extract_batch(batch, target_year)

                # Convert Dict results to LessonData
                for idx, data in enumerate(batch_dict_results):
                    card_idx = i + idx
                    card_text = batch_card_texts[idx] if idx < len(batch_card_texts) else ""

                    if data is None:
                        results.append(None)
                        continue

                    # Validate student_name
                    student_name = data.get("student_name")
                    if not student_name or student_name == "null":
                        logger.debug(f"No valid student name found in card {card_idx}: {card_text[:50]}")
                        results.append(None)
                        continue

                    # Convert to LessonData format
                    try:
                        lesson_data: LessonData = {
                            "id": f"lesson_{data['date'].replace('-', '')}_{card_idx}",
                            "date": data["date"],
                            "student_id": f"student_{hash(student_name) % 100000:05d}",
                            "student_name": student_name,
                            "status": "completed",
                            "duration": data.get("duration", 60),
                            "category": data.get("category", "専属レッスン")
                        }

                        results.append(lesson_data)

                    except (KeyError, ValueError) as e:
                        logger.error(f"Failed to convert AI response to LessonData at card {card_idx}: {e}")
                        logger.debug(f"Response data: {data}")
                        results.append(None)

            except Exception as e:
                logger.error(f"Batch extraction failed for cards {i}-{i+len(batch)}: {e}")
                # Return None for failed extractions
                results.extend([None] * len(batch))

        return results

    def _extract_batch(
        self,
        card_texts: List[str],
        target_year: int
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Extract lesson data from a batch of card texts.

        Args:
            card_texts: List of lesson card texts
            target_year: Year for date context

        Returns:
            List of extracted lesson data dictionaries
        """
        prompt = self._create_extraction_prompt(card_texts, target_year)

        try:
            # Call Claude API via Vertex AI
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Parse JSON (handle markdown code blocks)
            json_text = response_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]  # Remove ```json
            if json_text.startswith("```"):
                json_text = json_text[3:]  # Remove ```
            if json_text.endswith("```"):
                json_text = json_text[:-3]  # Remove trailing ```

            json_text = json_text.strip()

            # Parse JSON array
            extracted_data = json.loads(json_text)

            if not isinstance(extracted_data, list):
                logger.error(f"Expected JSON array, got: {type(extracted_data)}")
                return [None] * len(card_texts)

            # Sort by index to match original order
            extracted_data.sort(key=lambda x: x.get("index", 0))

            # Validate and return
            results = []
            for i, data in enumerate(extracted_data):
                if i < len(card_texts):
                    results.append(data)
                else:
                    logger.warning(f"Extra data in response at index {i}")

            # Fill missing results with None
            while len(results) < len(card_texts):
                results.append(None)

            return results

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return [None] * len(card_texts)
        except Exception as e:
            logger.error(f"AI extraction failed: {e}", exc_info=True)
            return [None] * len(card_texts)

    def extract_lesson(
        self,
        card_text: str,
        target_year: int
    ) -> Optional[LessonData]:
        """
        Extract lesson data from a single card text.

        Args:
            card_text: Lesson card text
            target_year: Year for date context (e.g., 2025)

        Returns:
            LessonData or None if extraction failed or student name is invalid

        Examples:
            >>> extractor = AIExtractor()
            >>> card_text = "11/01(土)20:00~21:00林晃司マンツー編集"
            >>> lesson = extractor.extract_lesson(card_text, 2025)
            >>> lesson['student_name']
            '林晃司'
        """
        results = self.extract_lessons_batch([card_text], target_year, batch_size=1)

        if not results or results[0] is None:
            return None

        data = results[0]

        # Validate student_name
        student_name = data.get("student_name")
        if not student_name or student_name == "null":
            logger.debug(f"No valid student name found in card: {card_text[:50]}")
            return None

        # Convert to LessonData format
        try:
            lesson_data: LessonData = {
                "id": f"lesson_ai_{hash(card_text) % 1000000:06d}",
                "date": data["date"],
                "student_id": f"student_{hash(student_name) % 100000:05d}",
                "student_name": student_name,
                "status": "completed",
                "duration": data.get("duration", 60),
                "category": data.get("category", "専属レッスン")
            }

            return lesson_data

        except (KeyError, ValueError) as e:
            logger.error(f"Failed to convert AI response to LessonData: {e}")
            logger.debug(f"Response data: {data}")
            return None
