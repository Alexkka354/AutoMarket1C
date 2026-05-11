"""
Модуль ранжирования изображений с использованием CLIP (ViT-B/32).

Оценивает семантическое соответствие изображения наименованию товара
на основе косинусного сходства векторных представлений текста и изображения
в едином пространстве CLIP (d = 512).

Формулы из диплома (раздел 2.Y):
  (18) score_CLIP(I, q) = cos(E_text(q), E_img(I))
  (19) R(I) = β₁ × score_CLIP + β₂ × Q(I) + β₃ × T_c(t)
  (20) Порог: R_threshold = 0.45
"""

import io
import logging

import aiohttp
import torch
import open_clip
from PIL import Image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Весовые коэффициенты итогового рангового балла — формула (19)
# ---------------------------------------------------------------------------
BETA_CLIP = 0.60      # β₁ — вес CLIP-оценки
BETA_QUALITY = 0.25   # β₂ — вес технического качества
BETA_TREND = 0.15     # β₃ — вес индекса тренда категории

# ---------------------------------------------------------------------------
# Пороговые значения — формула (20)
# ---------------------------------------------------------------------------
R_THRESHOLD = 0.45            # минимальный балл для принятия изображения
R_VERIFICATION_ZONE = 0.60    # ниже этого — требуется верификация пользователем

# ---------------------------------------------------------------------------
# Весовые коэффициенты оценки качества Q(I)
# ---------------------------------------------------------------------------
GAMMA_RES = 0.50      # γ₁ — вес разрешения
GAMMA_RATIO = 0.30    # γ₂ — вес соотношения сторон
GAMMA_FORMAT = 0.20   # γ₃ — вес формата файла

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class CLIPRanker:
    """
    Ранжирует изображения-кандидаты по релевантности к текстовому
    запросу (наименованию товара) с помощью модели CLIP ViT-B/32.
    """

    def __init__(self):
        """Загружает модель CLIP ViT-B/32 (один раз при создании экземпляра)."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        self.model = self.model.to(self.device).eval()
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")
        logger.info("CLIP ViT-B/32 загружена на %s", self.device)

    # ------------------------------------------------------------------
    # Векторные представления
    # ------------------------------------------------------------------

    def _encode_text(self, text: str) -> torch.Tensor:
        """E_text(q) ∈ ℝ^512 — нормализованный вектор текста."""
        tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad():
            features = self.model.encode_text(tokens)
            features /= features.norm(dim=-1, keepdim=True)
        return features

    def _encode_image(self, image: Image.Image) -> torch.Tensor:
        """E_img(I) ∈ ℝ^512 — нормализованный вектор изображения."""
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(tensor)
            features /= features.norm(dim=-1, keepdim=True)
        return features

    # ------------------------------------------------------------------
    # Формула (18): score_CLIP
    # ------------------------------------------------------------------

    def compute_clip_score(self, image: Image.Image, text: str) -> float:
        """
        Косинусное сходство между текстовым запросом и изображением.
        score_CLIP(I, q) = (E_text(q) · E_img(I)) / (‖E_text(q)‖ × ‖E_img(I)‖)
        """
        text_features = self._encode_text(text)
        image_features = self._encode_image(image)
        similarity = (text_features @ image_features.T).item()
        return float(similarity)

    # ------------------------------------------------------------------
    # Оценка технического качества Q(I)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_quality_score(image: Image.Image, image_url: str) -> float:
        """
        Q(I) = γ₁ × Q_res + γ₂ × Q_ratio + γ₃ × Q_format

        Q_res    = 1.0  если разрешение ≥ 800×600
        Q_ratio  = 1.0  если соотношение сторон ≈ 4:3 или 16:9
        Q_format = 1.0  для JPEG / PNG
        """
        width, height = image.size

        # Q_res
        if width >= 800 and height >= 600:
            q_res = 1.0
        else:
            q_res = min((width * height) / (800 * 600), 1.0)

        # Q_ratio
        ratio = width / height if height > 0 else 0
        target_ratios = [4 / 3, 16 / 9, 1.0]
        ratio_diff = min(abs(ratio - t) for t in target_ratios)
        q_ratio = max(0.0, 1.0 - ratio_diff * 2)

        # Q_format
        url_lower = image_url.lower()
        if any(ext in url_lower for ext in (".jpg", ".jpeg", ".png")):
            q_format = 1.0
        elif ".webp" in url_lower:
            q_format = 0.8
        else:
            q_format = 0.5

        quality = GAMMA_RES * q_res + GAMMA_RATIO * q_ratio + GAMMA_FORMAT * q_format
        return float(quality)

    # ------------------------------------------------------------------
    # Формула (19): итоговый ранговый балл R(I)
    # ------------------------------------------------------------------

    def compute_rank_score(
        self,
        image: Image.Image,
        text: str,
        image_url: str,
        trend_index: float = 0.5,
    ) -> dict:
        """
        R(I) = β₁ × score_CLIP(I, q) + β₂ × Q(I) + β₃ × T_c(t)

        Возвращает словарь с отдельными компонентами и итоговым баллом.
        """
        clip_score = self.compute_clip_score(image, text)
        quality_score = self.compute_quality_score(image, image_url)
        rank = (
            BETA_CLIP * clip_score
            + BETA_QUALITY * quality_score
            + BETA_TREND * trend_index
        )
        return {
            "clip_score": round(clip_score, 4),
            "quality_score": round(quality_score, 4),
            "rank_score": round(rank, 4),
        }

    # ------------------------------------------------------------------
    # Загрузка изображения по URL
    # ------------------------------------------------------------------

    @staticmethod
    async def download_image(url: str) -> Image.Image | None:
        """Загружает изображение по URL, возвращает PIL.Image (RGB) или None."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    url, headers={"User-Agent": USER_AGENT}
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.read()
                    image = Image.open(io.BytesIO(data)).convert("RGB")
                    return image
        except Exception as exc:
            logger.warning("Ошибка загрузки изображения %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Ранжирование набора кандидатов
    # ------------------------------------------------------------------

    async def rank_images(
        self,
        query: str,
        image_urls: list[str],
        trend_index: float = 0.5,
    ) -> list[dict]:
        """
        Загружает изображения, вычисляет ранговый балл R(I) для каждого
        и возвращает отсортированный по убыванию R список.

        Каждый элемент:
        {
            "url": str,
            "clip_score": float,
            "quality_score": float,
            "rank_score": float,
            "status": "accepted" | "needs_verification" | "rejected"
        }
        """
        results: list[dict] = []

        for url in image_urls:
            image = await self.download_image(url)
            if image is None:
                continue

            scores = self.compute_rank_score(image, query, url, trend_index)

            rank = scores["rank_score"]
            if rank >= R_VERIFICATION_ZONE:
                status = "accepted"
            elif rank >= R_THRESHOLD:
                status = "needs_verification"
            else:
                status = "rejected"

            results.append({
                "url": url,
                "clip_score": scores["clip_score"],
                "quality_score": scores["quality_score"],
                "rank_score": rank,
                "status": status,
            })

        results.sort(key=lambda x: x["rank_score"], reverse=True)
        return results


# ---------------------------------------------------------------------------
# Singleton: модель загружается один раз при первом обращении (~400 МБ)
# ---------------------------------------------------------------------------
_instance: CLIPRanker | None = None


def get_clip_ranker() -> CLIPRanker:
    """Возвращает (или создаёт) глобальный экземпляр CLIPRanker."""
    global _instance
    if _instance is None:
        logger.info("Инициализация CLIP ViT-B/32 ...")
        _instance = CLIPRanker()
    return _instance
