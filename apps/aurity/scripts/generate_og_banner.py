#!/usr/bin/env python3.14
"""
Generate Open Graph Banner for Free Intelligence
Card: FI-UI-DESIGN-003 (Metadata enhancement)

Creates a 1200x630 PNG banner for social media sharing (WhatsApp, Twitter, Facebook, LinkedIn)
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

# Dimensions (Open Graph standard)
WIDTH = 1200
HEIGHT = 630

# Color palette (matching app theme)
PURPLE_DARK = (102, 126, 234)  # #667eea
PURPLE_LIGHT = (118, 75, 162)  # #764ba2
BLUE_ACCENT = (59, 130, 246)   # #3b82f6
WHITE = (255, 255, 255)
WHITE_ALPHA_90 = (255, 255, 255, 230)
WHITE_ALPHA_70 = (255, 255, 255, 180)
WHITE_ALPHA_30 = (255, 255, 255, 77)


def create_gradient_background(width: int, height: int) -> Image.Image:
    """Create a diagonal gradient from purple to blue."""
    base = Image.new('RGB', (width, height), PURPLE_DARK)
    draw = ImageDraw.Draw(base, 'RGBA')

    # Create diagonal gradient effect
    for y in range(height):
        for x in range(width):
            # Calculate gradient factor (0.0 to 1.0)
            factor = (x + y) / (width + height)

            # Interpolate between PURPLE_DARK and PURPLE_LIGHT
            r = int(PURPLE_DARK[0] + (PURPLE_LIGHT[0] - PURPLE_DARK[0]) * factor)
            g = int(PURPLE_DARK[1] + (PURPLE_LIGHT[1] - PURPLE_DARK[1]) * factor)
            b = int(PURPLE_DARK[2] + (PURPLE_LIGHT[2] - PURPLE_DARK[2]) * factor)

            draw.point((x, y), fill=(r, g, b))

    return base


def add_radial_overlays(image: Image.Image) -> Image.Image:
    """Add radial gradient overlays for depth."""
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, 'RGBA')

    # First radial glow (top-left area)
    center1 = (int(WIDTH * 0.3), int(HEIGHT * 0.4))
    max_radius1 = 400
    for i in range(max_radius1, 0, -5):
        alpha = int(30 * (i / max_radius1))  # Fade out as radius increases
        color = (139, 92, 246, alpha)  # Purple with alpha
        draw.ellipse([
            center1[0] - i, center1[1] - i,
            center1[0] + i, center1[1] + i
        ], fill=color)

    # Second radial glow (bottom-right area)
    center2 = (int(WIDTH * 0.7), int(HEIGHT * 0.6))
    max_radius2 = 350
    for i in range(max_radius2, 0, -5):
        alpha = int(25 * (i / max_radius2))
        color = (59, 130, 246, alpha)  # Blue with alpha
        draw.ellipse([
            center2[0] - i, center2[1] - i,
            center2[0] + i, center2[1] + i
        ], fill=color)

    # Composite overlay onto base image
    return Image.alpha_composite(image.convert('RGBA'), overlay)


def add_text_content(image: Image.Image) -> Image.Image:
    """Add text content: logo, title, tagline, features."""
    draw = ImageDraw.Draw(image, 'RGBA')

    # Try to use system fonts, fallback to default
    try:
        # macOS system fonts
        font_title = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Black.ttf', 80)
        font_tagline = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 38)
        font_features = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
        font_logo = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 26)
    except OSError:
        # Fallback to default font
        font_title = ImageFont.load_default()
        font_tagline = ImageFont.load_default()
        font_features = ImageFont.load_default()
        font_logo = ImageFont.load_default()

    # Logo (top-right)
    logo_text = "AURITY"
    logo_pos = (WIDTH - 180, 60)
    draw.text(logo_pos, logo_text, font=font_logo, fill=WHITE_ALPHA_70)

    # Main title
    title_text = "Free Intelligence"
    title_pos = (80, 200)
    draw.text(title_pos, title_text, font=font_title, fill=WHITE)

    # Tagline
    tagline_text = "Asistente Médico con IA · Soberanía de Datos"
    tagline_pos = (80, 310)
    draw.text(tagline_pos, tagline_text, font=font_tagline, fill=WHITE_ALPHA_90)

    # Features badges
    features = [
        ("🩺", "Notas SOAP", 80),
        ("🔒", "Datos Seguros", 340),
        ("🧠", "IA Médica", 640),
    ]

    badge_y = 420
    for emoji, label, x_pos in features:
        # Badge background (rounded rectangle)
        badge_width = 180
        badge_height = 50
        badge_rect = [x_pos, badge_y, x_pos + badge_width, badge_y + badge_height]
        draw.rounded_rectangle(badge_rect, radius=8, fill=WHITE_ALPHA_30)

        # Emoji + Text
        emoji_pos = (x_pos + 15, badge_y + 8)
        draw.text(emoji_pos, emoji, font=font_features, fill=WHITE, embedded_color=True)

        text_pos = (x_pos + 55, badge_y + 13)
        draw.text(text_pos, label, font=font_features, fill=WHITE)

    return image


def main():
    """Generate the Open Graph banner."""
    print("🎨 Generating Open Graph banner...")

    # Create base gradient
    print("  ├─ Creating gradient background...")
    image = create_gradient_background(WIDTH, HEIGHT)

    # Add radial overlays for depth
    print("  ├─ Adding radial overlays...")
    image = add_radial_overlays(image)

    # Add text content
    print("  ├─ Adding text content...")
    image = add_text_content(image)

    # Save to public directory
    output_path = Path(__file__).parent.parent / "public" / "og-banner.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  ├─ Saving to {output_path}...")
    image.convert('RGB').save(output_path, 'PNG', optimize=True, quality=95)

    file_size = output_path.stat().st_size / 1024  # KB
    print(f"  └─ ✅ Banner created successfully!")
    print(f"\n📊 File info:")
    print(f"   - Path: {output_path}")
    print(f"   - Size: {file_size:.1f} KB")
    print(f"   - Dimensions: {WIDTH}x{HEIGHT}")
    print(f"\n🚀 Next steps:")
    print(f"   1. Review the banner: open {output_path}")
    print(f"   2. Deploy: pnpm build && python3 scripts/deploy-scp.py")
    print(f"   3. Test sharing: https://app.aurity.io")
    print(f"   4. Validate metadata: https://www.opengraph.xyz/")


if __name__ == "__main__":
    main()
