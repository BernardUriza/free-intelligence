#!/usr/bin/env python3.14
"""
Compress existing OG banner to <300KB for WhatsApp compatibility
"""

from PIL import Image
from pathlib import Path

def compress_image(input_path: Path, max_size_kb: int = 300):
    """
    Compress image to be under max_size_kb while maintaining quality.

    Args:
        input_path: Path to input image
        max_size_kb: Maximum file size in KB (default 300 for WhatsApp)
    """
    print(f"📥 Loading image: {input_path}")

    # Load image
    img = Image.open(input_path)
    original_size = input_path.stat().st_size / 1024
    print(f"   Original size: {original_size:.1f} KB")
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}")
    print(f"   Mode: {img.mode}")

    # Convert RGBA to RGB if needed
    if img.mode == 'RGBA':
        print("   Converting RGBA → RGB...")
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3])
        img = rgb_img

    # Create backup
    backup_path = input_path.with_suffix('.backup.png')
    input_path.rename(backup_path)
    print(f"   Backup created: {backup_path.name}")

    # Try PNG optimization first
    print("\n🔧 Trying PNG optimization...")
    img.save(input_path, format='PNG', optimize=True, compress_level=9)
    png_size = input_path.stat().st_size / 1024
    print(f"   PNG optimized: {png_size:.1f} KB")

    if png_size < max_size_kb:
        print(f"   ✅ PNG under {max_size_kb}KB! Using PNG format.")
        backup_path.unlink()
        return input_path, png_size

    # PNG too large, try JPEG with quality reduction
    print(f"\n🔧 PNG too large, trying JPEG compression...")

    for quality in [95, 85, 75, 65, 55, 45]:
        img.save(input_path, format='JPEG', quality=quality, optimize=True)
        jpeg_size = input_path.stat().st_size / 1024
        print(f"   Quality {quality}: {jpeg_size:.1f} KB", end="")

        if jpeg_size < max_size_kb:
            print(f" ✅")
            backup_path.unlink()
            return input_path, jpeg_size
        else:
            print(f" ❌")

    # If still too large, reduce dimensions
    print(f"\n🔧 Still too large, reducing dimensions...")
    img = Image.open(backup_path)
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3])
        img = rgb_img

    scale = 0.8
    new_width = int(img.size[0] * scale)
    new_height = int(img.size[1] * scale)
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    img_resized.save(input_path, format='JPEG', quality=85, optimize=True)
    final_size = input_path.stat().st_size / 1024
    print(f"   Resized to {new_width}x{new_height}: {final_size:.1f} KB")

    backup_path.unlink()
    return input_path, final_size


def main():
    script_dir = Path(__file__).parent
    public_dir = script_dir.parent / "public"
    banner_path = public_dir / "og-banner.png"

    if not banner_path.exists():
        print(f"❌ Banner not found: {banner_path}")
        return 1

    print("🎨 Compressing OG banner for WhatsApp compatibility")
    print("=" * 60)

    try:
        output_path, final_size = compress_image(banner_path, max_size_kb=300)

        print("\n" + "=" * 60)
        print("✅ Compression complete!")
        print(f"\n📊 Results:")
        print(f"   - Output: {output_path}")
        print(f"   - Final size: {final_size:.1f} KB")
        print(f"   - WhatsApp compatible: {'YES ✅' if final_size < 300 else 'NO ❌'}")

        print(f"\n🚀 Next steps:")
        print(f"   1. Rebuild: cd apps/aurity && pnpm build")
        print(f"   2. Deploy: python3 docs/archive/obsolete-scripts/deploy-scp.py")
        print(f"   3. Test in WhatsApp!")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
