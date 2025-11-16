from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify
from django.urls import reverse

# Category model
class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# Tag model
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

# Artist model
class Artist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='artist', null=True, blank=True)
    name = models.CharField(max_length=140)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='artists/avatars/', blank=True, null=True)
    website = models.URLField(blank=True)
    twitter = models.CharField(max_length=200, blank=True)
    instagram = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name or (self.user.username if self.user else "Unknown")

# Artwork model
class Artwork(models.Model):
    MATERIAL_CHOICES = [
        ('cotton', 'Cotton'),
        ('silk', 'Silk'),
        ('paper', 'Paper'),
        ('mixed', 'Mixed Media'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    artist = models.ForeignKey(Artist, on_delete=models.SET_NULL, null=True, blank=True, related_name='artworks')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='artworks')
    tags = models.ManyToManyField(Tag, blank=True, related_name='artworks')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    materials = models.CharField(max_length=40, choices=MATERIAL_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    year_created = models.PositiveSmallIntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f"/artwork/{self.id}/"

    def save(self, *args, **kwargs):
        # Ensure slug is unique, use year from created_at
        if not self.slug:
            base = slugify(self.title)[:240]
            year = self.created_at.year if self.created_at else ''
            self.slug = f"{base}-{year}"
        super().save(*args, **kwargs)

# ArtworkImage model (supports multiple images per artwork)
class ArtworkImage(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='artworks/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.artwork.title} image #{self.id}"

# Review model
class Review(models.Model):
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)  # 1..5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review {self.rating} for {self.artwork.title}"

# ContactMessage model
class ContactMessage(models.Model):
    name = models.CharField(max_length=140)
    email = models.EmailField()
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} <{self.email}>"

# ArtworkLike model
class ArtworkLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artwork')

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    artwork = models.ForeignKey('Artwork', on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'artwork')

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    followee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followee')

# lightweight chat model (if not present)
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_msgs', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_msgs', on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} -> {self.recipient or 'all'}: {self.message[:30]}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like', 'Artwork Liked'),
        ('comment', 'New Comment'),
        ('follow', 'New Follower'),
        ('bookmark', 'Artwork Bookmarked'),
        ('message', 'New Message'),
        ('feature', 'Artwork Featured'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    artwork = models.ForeignKey(Artwork, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}"
