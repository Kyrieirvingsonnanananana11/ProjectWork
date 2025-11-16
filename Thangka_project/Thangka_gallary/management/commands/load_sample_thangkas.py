from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from Thangka_gallary.models import Artwork, ArtworkImage, Artist, Category
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create sample Artwork entries from files placed in MEDIA_ROOT/sample_thangkas/"

    def handle(self, *args, **options):
        media_dir = os.path.join(getattr(settings, 'MEDIA_ROOT', ''), 'sample_thangkas')
        if not os.path.isdir(media_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {media_dir}"))
            self.stdout.write("Create the folder and add image files, then run: python manage.py load_sample_thangkas")
            return

        files = [f for f in sorted(os.listdir(media_dir)) if f.lower().endswith(('.jpg','.jpeg','.png','webp'))]
        if not files:
            self.stdout.write(self.style.ERROR("No image files found in sample_thangkas/"))
            return

        # pick an existing user to be the artist owner, or create a fallback user
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='sample_artist', password='password')
            self.stdout.write(self.style.WARNING("No users found — created user 'sample_artist' with password 'password'"))

        artist, _ = Artist.objects.get_or_create(user=user, defaults={'name': getattr(user, 'username', 'artist')})

        # optional: get a category if you have one
        category = Category.objects.first() if 'Category' in globals() else None

        created = 0
        for i, fname in enumerate(files, start=1):
            fp = os.path.join(media_dir, fname)
            title = os.path.splitext(fname)[0].replace('_',' ').title()[:60]
            description = f"Sample Thangka {i} imported from sample_thangkas"
            art = Artwork.objects.create(
                title=title,
                description=description,
                artist=artist,
                category=category,
                is_published=True
            )
            # attach image
            with open(fp, 'rb') as f:
                django_file = File(f, name=fname)
                ArtworkImage.objects.create(artwork=art, image=django_file, order=0)
            created += 1
            self.stdout.write(f"Created artwork: {title}")

        self.stdout.write(self.style.SUCCESS(f"Imported {created} artworks."))