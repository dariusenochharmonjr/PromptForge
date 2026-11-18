import os
from PIL import Image, ImageDraw
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Draw the SeePrompts push icons in the existing brand purple"
    def handle(self, *args, **options):
        d = os.path.join(settings.BASE_DIR, "workflows", "static", "push")
        os.makedirs(d, exist_ok=True)
        for s in (192, 512):
            im = Image.new("RGBA", (s, s), (111, 66, 193, 255))
            dr = ImageDraw.Draw(im)
            lens = [(0.08,0.50),(0.28,0.28),(0.50,0.22),(0.72,0.28),(0.92,0.50),(0.72,0.72),(0.50,0.78),(0.28,0.72)]
            dr.polygon([(x*s, y*s) for x, y in lens], fill=(255,255,255,255))
            dr.ellipse([0.34*s, 0.34*s, 0.66*s, 0.66*s], fill=(111,66,193,255))
            dr.ellipse([0.42*s, 0.42*s, 0.50*s, 0.50*s], fill=(255,255,255,255))
            im.save(os.path.join(d, "icon-%d.png" % s))
        self.stdout.write(self.style.SUCCESS("SeePrompts icons written in brand purple"))