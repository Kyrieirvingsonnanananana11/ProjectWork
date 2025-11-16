from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tag, Artist, Artwork, ArtworkImage, Review, ContactMessage, Notification

class ArtworkImageInline(admin.TabularInline):
    model = ArtworkImage
    extra = 1
    readonly_fields = ('preview',)
    fields = ('image', 'caption', 'order', 'preview')

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;object-fit:cover;border-radius:4px;"/>', obj.image.url)
        return "(no image)"
    preview.short_description = "Preview"

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'rating', 'comment', 'created_at')

@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist_link', 'category', 'is_published', 'is_featured', 'created_at', 'price', 'views_count')
    list_filter = ('is_published', 'is_featured', 'category', 'materials')
    search_fields = ('title', 'description')
    inlines = [ArtworkImageInline, ReviewInline]
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('artist',)

    def artist_link(self, obj):
        return obj.artist.name if obj.artist else "—"
    artist_link.short_description = 'Artist'

    def views_count(self, obj):
        return obj.view_count
    views_count.short_description = 'Views'

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'website')
    search_fields = ('name', 'user__username')
    raw_id_fields = ('user',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('artwork', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('artwork__title', 'user__username', 'comment')

@admin.register(ContactMessage)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)
