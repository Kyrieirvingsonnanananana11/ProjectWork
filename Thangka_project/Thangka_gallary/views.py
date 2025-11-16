from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse, HttpResponseBadRequest

from .models import Artwork, Category, Tag, Artist, ArtworkImage, Review, ChatMessage, ArtworkLike, Bookmark, Follow, Notification
from .forms import RegisterForm, ArtworkForm, ContactForm, ArtistForm
from django.contrib.auth.models import User

# Home page with featured artworks
def index(request):
    featured = Artwork.objects.filter(is_published=True).order_by('-is_featured', '-created_at')[:6]
    categories = Category.objects.all()
    return render(request, 'Thangka_gallary/index.html', {'featured': featured, 'categories': categories})

# Gallery with search, category, tag filters, and pagination
def gallery(request):
    # initial render - serve first page of artworks
    qs = Artwork.objects.filter(is_published=True).order_by('-created_at')
    paginator = Paginator(qs, 12)
    page1 = paginator.get_page(1)

    # convert to list and annotate simple attributes for template (avoid calling QuerySet methods in template)
    artworks = list(page1)
    for art in artworks:
        art.likes_count = art.likes.count() if hasattr(art, 'likes') else 0
        art.is_bookmarked = False
        if request.user.is_authenticated:
            art.is_bookmarked = Bookmark.objects.filter(user=request.user, artwork=art).exists()
        art.display_artist = art.artist.name if getattr(art, 'artist', None) and getattr(art.artist, 'name', None) else getattr(art.artist.user, 'username', '')

    return render(request, 'Thangka_gallary/gallery.html', {
        'artworks': artworks,
        'has_next': page1.has_next(),
    })

def gallery_json(request):
    # JSON endpoint for infinite scroll
    page = int(request.GET.get('page', 1))
    per_page = 12
    qs = Artwork.objects.filter(is_published=True).order_by('-created_at')
    paginator = Paginator(qs, per_page)
    pg = paginator.get_page(page)
    items = []
    for a in pg:
        img = a.images.order_by('order').first() if hasattr(a, 'images') else None
        items.append({
            'id': a.id,
            'title': a.title,
            'artist': (a.artist.name if getattr(a, 'artist', None) and getattr(a.artist, 'name', None) else getattr(a.artist.user, 'username', '')),
            'thumb': img.image.url if img else '',
            'likes_count': a.likes.count() if hasattr(a, 'likes') else 0,
        })
    return JsonResponse({'items': items, 'has_next': pg.has_next()})

# Artwork detail with related artworks and reviews
def artwork_detail(request, pk):
    art = get_object_or_404(Artwork, pk=pk, is_published=True)
    Artwork.objects.filter(pk=art.pk).update(view_count=art.view_count + 1)

    related = Artwork.objects.filter(is_published=True).exclude(pk=art.pk)
    if art.category:
        related = related.filter(category=art.category)[:6]
    else:
        tag_ids = art.tags.values_list('id', flat=True)
        related = related.filter(tags__in=tag_ids).distinct()[:6]

    return render(request, 'Thangka_gallary/detail.html', {
        'art': art,
        'related': related,
        'reviews': art.reviews.all()
    })

# Static pages
def about_thangka(request):
    team = [
        {'name': 'Tenzin Dorji', 'role': 'Founder & Curator', 'bio': 'Thangka conservator and curator.', 'photo': ''},
        {'name': 'Pema Choden', 'role': 'Artist Relations', 'bio': 'Onboards and supports artists.', 'photo': ''},
        {'name': 'Kinzang Wangmo', 'role': 'Product & Design', 'bio': 'Design lead for the gallery.', 'photo': ''},
    ]
    return render(request, 'Thangka_gallary/about_thangka.html', {'team': team})

def about_team(request):
    return render(request, 'Thangka_gallary/about_team.html')

# Contact page
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Message sent. We'll reply soon.")
            return redirect('/')
    else:
        form = ContactForm()
    return render(request, 'Thangka_gallary/contact.html', {'form': form})

# User registration
def user_register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        artist_form = ArtistForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # Create or update Artist profile
            artist = Artist.objects.create(user=user, name=user.username)
            if artist_form.is_valid():
                artist.bio = artist_form.cleaned_data.get('bio') or artist.bio
                if artist_form.cleaned_data.get('avatar'):
                    artist.avatar = artist_form.cleaned_data.get('avatar')
                artist.save()
            messages.success(request, "Account created. Please log in.")
            return redirect('/login/')
    else:
        form = RegisterForm()
        artist_form = ArtistForm()
    return render(request, 'Thangka_gallary/register.html', {'form': form, 'artist_form': artist_form})

# User login/logout
def user_login(request):
    next_url = request.GET.get('next') or request.POST.get('next') or None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Logged in successfully.")
            # prefer explicit next param, otherwise send to artist dashboard
            return redirect(next_url or 'artist_dashboard')
        messages.error(request, "Invalid credentials.")
    return render(request, 'Thangka_gallary/login.html', {'next': next_url})

def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    # send to login page after logout
    return redirect('login')

# Upload artwork (supports multiple images)
@login_required
def upload_artwork(request):
    if request.method == 'POST':
        form = ArtworkForm(request.POST)
        files = request.FILES.getlist('images')  # multiple images from template
        if form.is_valid():
            artwork = form.save(commit=False)
            # assign artist profile
            artwork.artist, created = Artist.objects.get_or_create(user=request.user, defaults={'name': request.user.username})
            artwork.save()
            form.save_m2m()  # save tags
            # save multiple images
            for order, f in enumerate(files):
                ArtworkImage.objects.create(artwork=artwork, image=f, order=order)
            messages.success(request, "Artwork uploaded successfully.")
            return redirect('/gallery/')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ArtworkForm()
    return render(request, 'Thangka_gallary/upload_artwork.html', {'form': form})

# User profile page
@login_required
def profile(request):
    user_artworks = Artwork.objects.filter(artist__user=request.user).order_by('-created_at')
    return render(request, 'Thangka_gallary/profile.html', {'user_artworks': user_artworks})

# Password reset page (demo)
def password_reset(request):
    if request.method == 'POST':
        messages.info(request, "If an account exists with that email, a reset link will be sent (demo).")
        return redirect('/login/')
    return render(request, 'Thangka_gallary/password_reset.html')

@login_required
def artist_dashboard(request):
    """
    Artist dashboard: inline upload + pinterest-like gallery + links to logout/chat.
    Handles GET (render) and POST (upload).
    """
    if request.method == 'POST':
        form = ArtworkForm(request.POST)
        files = request.FILES.getlist('images')
        if form.is_valid():
            artwork = form.save(commit=False)
            artwork.artist, _ = Artist.objects.get_or_create(user=request.user, defaults={'name': request.user.username})
            artwork.save()
            form.save_m2m()
            for order, f in enumerate(files):
                ArtworkImage.objects.create(artwork=artwork, image=f, order=order)
            messages.success(request, "Artwork uploaded.")
            return redirect('artist_dashboard')
        else:
            messages.error(request, "Please correct the upload errors.")
    else:
        form = ArtworkForm()

    # fetch artworks
    user_qs = Artwork.objects.filter(artist__user=request.user, is_published=True).order_by('-created_at')[:12]
    feed_qs = Artwork.objects.filter(is_published=True).order_by('-created_at')[:12]

    # annotate runtime attributes used by template (avoids template queryset calls)
    user_artworks = list(user_qs)
    feed_artworks = list(feed_qs)
    for art in user_artworks + feed_artworks:
        # likes/bookmarks/follow flags for current user
        art.likes_count = art.likes.count() if hasattr(art, 'likes') else 0
        art.is_liked = art.likes.filter(user=request.user).exists() if hasattr(art, 'likes') else False
        art.is_bookmarked = Bookmark.objects.filter(user=request.user, artwork=art).exists()
        # artist display name fallback
        art.display_artist = art.artist.name if getattr(art, 'artist', None) and getattr(art.artist, 'name', None) else getattr(art.artist.user, 'username', '')

    return render(request, 'Thangka_gallary/artist_dashboard.html', {
        'form': form,
        'user_artworks': user_artworks,
        'feed_artworks': feed_artworks,
    })

@require_GET
def artist_artworks_json(request):
    """
    Returns paginated artworks as JSON for infinite scroll.
    Query params: page (int)
    """
    page = int(request.GET.get('page', 1))
    per_page = 12
    qs = Artwork.objects.filter(is_published=True).order_by('-created_at')
    start = (page - 1) * per_page
    end = start + per_page
    items = []
    for a in qs[start:end]:
        thumb = ''
        # attempt to get first image url
        img = a.images.order_by('order').first() if hasattr(a, 'images') else None
        if img:
            thumb = img.image.url
        items.append({
            'id': a.id,
            'title': a.title,
            'artist': a.artist.name if a.artist else a.artist.user.username,
            'thumb': thumb,
            'url': a.get_absolute_url() if hasattr(a, 'get_absolute_url') else f"/gallery/{a.id}/"
        })
    return JsonResponse({'items': items})

@login_required
def chat_page(request):
    """
    Messenger-style chat with user list and 1-on-1 threads.
    """
    selected_user_id = request.GET.get('user') or request.POST.get('recipient')
    selected_user = None
    conversation = []

    if selected_user_id:
        try:
            selected_user = User.objects.get(pk=selected_user_id)
        except User.DoesNotExist:
            pass

    if request.method == 'POST' and selected_user:
        message_text = request.POST.get('message', '').strip()
        if message_text:
            ChatMessage.objects.create(
                sender=request.user,
                recipient=selected_user,
                message=message_text
            )
            # Redirect using reverse() to build the URL properly
            return redirect(reverse('chat_page') + f'?user={selected_user.id}')

    # fetch 1-on-1 conversation with selected user
    if selected_user:
        conversation = ChatMessage.objects.filter(
            Q(sender=request.user, recipient=selected_user) |
            Q(sender=selected_user, recipient=request.user)
        ).order_by('created_at')

    # get list of artists (users who have an artist profile)
    from Thangka_gallary.models import Artwork
    artist_users = Artist.objects.filter(
        user__isnull=False
    ).values_list('user_id', flat=True)
    
    # get artworks per user
    artwork_counts = {}
    for user_id in artist_users:
        count = Artwork.objects.filter(artist__user_id=user_id).count()
        if count > 0:
            artwork_counts[user_id] = count

    # fetch users sorted by artwork count
    artists = User.objects.filter(
        pk__in=artwork_counts.keys()
    ).exclude(pk=request.user.pk)
    
    # sort in Python by artwork count descending
    artists_list = sorted(
        artists,
        key=lambda u: artwork_counts.get(u.pk, 0),
        reverse=True
    )[:20]

    return render(request, 'Thangka_gallary/chat.html', {
        'selected_user': selected_user,
        'conversation': conversation,
        'artists': artists_list,
    })

@login_required
@require_POST
def toggle_like(request):
    art_id = request.POST.get('artwork_id')
    if not art_id:
        return HttpResponseBadRequest("Missing artwork_id")
    try:
        art = Artwork.objects.get(pk=art_id)
    except Artwork.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Artwork not found'}, status=404)
    liked, created = ArtworkLike.objects.get_or_create(user=request.user, artwork=art)
    if not created:
        liked.delete()
        action = 'unliked'
    else:
        action = 'liked'
    return JsonResponse({'status': 'ok', 'action': action, 'likes_count': art.likes.count()})

@login_required
@require_POST
def toggle_bookmark(request):
    art_id = request.POST.get('artwork_id')
    if not art_id:
        return HttpResponseBadRequest("Missing artwork_id")
    try:
        art = Artwork.objects.get(pk=art_id)
    except Artwork.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Artwork not found'}, status=404)
    bm, created = Bookmark.objects.get_or_create(user=request.user, artwork=art)
    if not created:
        bm.delete()
        action = 'removed'
    else:
        action = 'saved'
    return JsonResponse({'status': 'ok', 'action': action})

@login_required
@require_POST
def toggle_follow(request):
    user_id = request.POST.get('user_id')
    if not user_id:
        return HttpResponseBadRequest("Missing user_id")
    if str(request.user.id) == str(user_id):
        return JsonResponse({'status': 'error', 'message': "Can't follow yourself"}, status=400)
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    f, created = Follow.objects.get_or_create(follower=request.user, followee=target)
    if not created:
        f.delete()
        action = 'unfollowed'
    else:
        action = 'followed'
    return JsonResponse({'status': 'ok', 'action': action, 'followers_count': target.followers.count()})

@login_required
def notifications_page(request):
    """
    Display user notifications - what's new in the community.
    """
    notifications = Notification.objects.filter(user=request.user)
    
    # Mark as read if viewing
    unread = notifications.filter(is_read=False)
    unread.update(is_read=True)
    
    # Group by type
    notifications_by_type = {}
    for notif in notifications[:50]:  # last 50
        notif_type = notif.get_notification_type_display()
        if notif_type not in notifications_by_type:
            notifications_by_type[notif_type] = []
        notifications_by_type[notif_type].append(notif)
    
    return render(request, 'Thangka_gallary/notifications.html', {
        'notifications': notifications[:50],
        'notifications_by_type': notifications_by_type,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    })

@login_required
def mark_notification_read(request, notif_id):
    """Mark a single notification as read."""
    notif = get_object_or_404(Notification, pk=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'status': 'ok'})

@login_required
def clear_notifications(request):
    """Clear all notifications for user."""
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'ok'})
