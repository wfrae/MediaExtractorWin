"""Generate icon.ico from icon.svg using Pillow + cairosvg or rsvg-convert."""
import subprocess, sys, os
from pathlib import Path

def main():
    svg = Path(__file__).parent / "icon.svg"
    ico = Path(__file__).parent / "icon.ico"
    png = Path(__file__).parent / "icon_tmp.png"

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=256, output_height=256)
    except ImportError:
        result = subprocess.run(["rsvg-convert", "-w", "256", "-h", "256", str(svg), "-o", str(png)],
                                capture_output=True)
        if result.returncode != 0:
            print("Need cairosvg or rsvg-convert to generate icon.")
            print("pip install cairosvg")
            sys.exit(1)

    from PIL import Image
    img = Image.open(str(png))
    img.save(str(ico), format="ICO", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    png.unlink(missing_ok=True)
    print(f"Created {ico}")

if __name__ == "__main__":
    main()
