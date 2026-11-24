"""The 15 animation styles. Each one is a prompt recipe sent to the AI model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    id: str
    name: str
    desc: str
    prompt: str
    negative: str
    c1: str
    c2: str
    motif: str
    eye: float = 1.0


NEG = "lowres, bad anatomy, deformed face, extra fingers, blurry, watermark, text, jpeg artifacts"

STYLES: list[Style] = [
    Style("anime", "Japanese Anime", "Clean cel-shaded lines, big expressive eyes, vivid colour.",
          "best quality, perfect anime illustration, cel shading, clean lineart, vibrant colors",
          NEG, "#EC4899", "#5425D6", "stars", 1.25),
    Style("cartoon3d", "3D Cartoon", "Soft, glossy 3D animated-movie look.",
          "3d render, pixar style, cute stylized character, soft studio lighting, smooth shading",
          NEG, "#22D3EE", "#3B82F6", "clay", 1.15),
    Style("cartoon2d", "2D Cartoon", "Bold outlines and flat colours like a TV cartoon.",
          "2d cartoon, thick outlines, flat colors, saturday morning cartoon, simple shading",
          NEG, "#F59E0B", "#EF4444", "retro", 1.1),
    Style("manga", "Manga", "Black-and-white ink with screentone and speed lines.",
          "manga page, black and white ink, screentone, high contrast, detailed linework",
          NEG + ", color", "#E5E7EB", "#6B7280", "manga", 1.2),
    Style("comic", "Comic Book", "Halftone dots, heavy ink and punchy colours.",
          "american comic book art, halftone dots, bold ink outlines, dynamic colors, pop art",
          NEG, "#FACC15", "#DC2626", "halftone", 1.0),
    Style("cyberpunk", "Cyberpunk", "Neon city glow, magenta and cyan highlights.",
          "cyberpunk, neon lights, futuristic city, magenta and cyan glow, high contrast, rainy night",
          NEG, "#EC4899", "#0EA5E9", "grid", 1.0),
    Style("fantasy", "Fantasy Anime", "Magical light, dreamy skies and storybook colour.",
          "fantasy anime illustration, magical glow, ethereal light, detailed painted background",
          NEG, "#8B5CF6", "#22D3EE", "moon", 1.2),
    Style("watercolor", "Watercolor", "Soft washes of paint with paper texture.",
          "watercolor painting, soft washes, paper texture, delicate brush strokes, pastel colors",
          NEG, "#38BDF8", "#F9A8D4", "wash", 1.0),
    Style("clay", "Clay Animation", "Hand-sculpted stop-motion clay figures.",
          "claymation, plasticine, stop motion, handmade clay texture, fingerprints, soft light",
          NEG, "#FB923C", "#B45309", "clay", 1.1),
    Style("pixel", "Pixel Art", "Chunky retro game pixels.",
          "pixel art, 16-bit, retro video game sprite, limited palette, crisp pixels",
          NEG, "#34D399", "#0F766E", "pixels", 1.0),
    Style("retro", "Retro Cartoon", "Vintage 1930s rubber-hose animation.",
          "vintage 1930s cartoon, rubber hose animation, grainy film, sepia tones, old animation",
          NEG, "#FDE68A", "#B45309", "retro", 1.1),
    Style("chibi", "Chibi", "Tiny, cute characters with giant heads.",
          "chibi, super deformed, cute big head, kawaii, pastel colors, sparkles",
          NEG, "#F472B6", "#A78BFA", "stars", 1.6),
    Style("cinematic", "Cinematic Anime", "Film-grade lighting and wide shots.",
          "cinematic anime movie still, dramatic lighting, lens flare, detailed background, studio quality",
          NEG, "#1E3A8A", "#F97316", "sun", 1.2),
    Style("pencil", "Pencil Sketch", "Graphite hatching on paper.",
          "pencil sketch, graphite drawing, cross hatching, detailed shading, white paper",
          NEG + ", color", "#F3F4F6", "#9CA3AF", "sketch", 1.0),
    Style("lowpoly", "Low Poly 3D", "Faceted geometric polygons.",
          "low poly 3d, faceted geometry, flat shaded triangles, isometric, minimal colors",
          NEG, "#6366F1", "#14B8A6", "lowpoly", 1.0),
]

BY_ID = {s.id: s for s in STYLES}
POPULAR = ["anime", "cartoon3d", "comic", "cyberpunk", "chibi", "watercolor"]


def get(style_id: str) -> Style:
    return BY_ID.get(style_id, STYLES[0])
