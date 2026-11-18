from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.middleware.csrf import get_token as _ensure_csrf_token

from .models import (Workflow, Upvote, Profile, Follow, LoveReaction, Comment,
                     Notification, Bookmark, Reply, CommentLike)
from .forms import WorkflowForm, UserUpdateForm, ProfileUpdateForm, CommentForm


# FEED AND SEARCH
def feed_view(request):
    if not request.user.is_authenticated:
        recent = list(Workflow.objects.select_related('author').order_by('-created_at')[:40])
        featured = list(Workflow.objects.annotate(love_count=Count('love_reactions'))
                        .order_by('-love_count', '-created_at')[:6])
        authors, seen_a = [], set()
        for w in recent:
            if w.author_id not in seen_a:
                seen_a.add(w.author_id)
                authors.append(w.author)
            if len(authors) >= 5:
                break
        return render(request, 'workflows/landing.html', {
            'featured': featured,
            'authors': authors,
            'hero': featured[0] if featured else None,
            'stats': {
                'members': User.objects.count(),
                'prompts': Workflow.objects.count(),
                'models': Workflow.objects.values('ai_model').distinct().count(),
            },
        })

    workflows = Workflow.objects.all().order_by('-created_at')
    search_query = request.GET.get('q', '')
    model_filter = request.GET.get('model', '')

    if search_query:
        workflows = workflows.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    if model_filter:
        workflows = workflows.filter(ai_model=model_filter)

    paginator = Paginator(workflows, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    loved_ids, upvoted_ids, bookmarked_ids, following_usernames = [], [], [], []
    if request.user.is_authenticated:
        loved_ids = list(LoveReaction.objects.filter(user=request.user, workflow__in=page_obj.object_list).values_list('workflow_id', flat=True))
        upvoted_ids = list(Upvote.objects.filter(user=request.user, workflow__in=page_obj.object_list).values_list('workflow_id', flat=True))
        bookmarked_ids = list(Bookmark.objects.filter(user=request.user, workflow__in=page_obj.object_list).values_list('workflow_id', flat=True))
        following_usernames = list(Follow.objects.filter(follower=request.user).values_list('following__username', flat=True))

    context = {
        'workflows': page_obj, 'page_obj': page_obj,
        'search_query': search_query, 'model_filter': model_filter,
        'loved_ids': loved_ids, 'upvoted_ids': upvoted_ids,
        'bookmarked_ids': bookmarked_ids, 'following_usernames': following_usernames,
    }

    # Infinite scroll: return ONLY the new cards as JSON (no full page)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('workflows/_workflow_cards.html', context, request=request)
        next_url = ''
        if page_obj.has_next():
            params = request.GET.copy()
            params['page'] = page_obj.next_page_number()
            next_url = f'{request.path}?{params.urlencode()}'
        return JsonResponse({'html': html, 'has_next': page_obj.has_next(), 'next_url': next_url})

    return render(request, 'workflows/feed.html', context)

# --- TRENDING FEED ---
def trending_view(request):
    seven_days_ago = timezone.now() - timedelta(days=7)
    workflows = Workflow.objects.filter(created_at__gte=seven_days_ago).annotate(
        upvote_count=Count('upvotes'),
        love_count=Count('love_reactions')
    ).order_by('-upvote_count', '-love_count')

    search_query = request.GET.get('q', '')
    model_filter = request.GET.get('model', '')

    if search_query:
        workflows = workflows.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
    if model_filter:
        workflows = workflows.filter(ai_model=model_filter)

    loved_ids = []
    upvoted_ids = []
    bookmarked_ids = []
    following_usernames = []
    
    if request.user.is_authenticated:
        loved_ids = list(LoveReaction.objects.filter(user=request.user, workflow__in=workflows).values_list('workflow_id', flat=True))
        upvoted_ids = list(Upvote.objects.filter(user=request.user, workflow__in=workflows).values_list('workflow_id', flat=True))
        bookmarked_ids = list(Bookmark.objects.filter(user=request.user, workflow__in=workflows).values_list('workflow_id', flat=True))
        following_usernames = list(Follow.objects.filter(follower=request.user).values_list('following__username', flat=True))

    return render(request, 'workflows/trending.html', {
        'workflows': workflows, 'search_query': search_query, 'model_filter': model_filter,
        'loved_ids': loved_ids, 'upvoted_ids': upvoted_ids, 'bookmarked_ids': bookmarked_ids, 'following_usernames': following_usernames
    })


# --- WORKFLOW DETAILS ---
def detail_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    is_loved = False
    is_upvoted = False
    is_bookmarked = False
    following_usernames = []
    
    if request.user.is_authenticated:
        is_loved = LoveReaction.objects.filter(user=request.user, workflow=workflow).exists()
        is_upvoted = Upvote.objects.filter(user=request.user, workflow=workflow).exists()
        is_bookmarked = Bookmark.objects.filter(user=request.user, workflow=workflow).exists()
        following_usernames = list(Follow.objects.filter(follower=request.user).values_list('following__username', flat=True))

    return render(request, 'workflows/detail.html', {
        'workflow': workflow, 'is_loved': is_loved, 'is_upvoted': is_upvoted, 'is_bookmarked': is_bookmarked, 'following_usernames': following_usernames
    })


@login_required
def create_workflow_view(request):
    remix_pk = request.GET.get('remix') or request.POST.get('remixed_from')
    remix_source = None
    if remix_pk:
        try:
            remix_source = Workflow.objects.filter(pk=int(remix_pk)).first()
        except (TypeError, ValueError):
            remix_source = None

    if request.method == 'POST':
        form = WorkflowForm(request.POST, request.FILES)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.author = request.user
            workflow.remixed_from = remix_source
            try:
                workflow.save()
            except Exception:
                msg = ('Cloudinary could not accept that media file. Please try a different file '
                       '(JPG/PNG/WEBP under 10MB, or MP4/WEBM under 60MB).')
                if request.FILES.get('output_image'):
                    form.add_error('output_image', msg)
                elif request.FILES.get('output_video'):
                    form.add_error('output_video', msg)
                else:
                    form.add_error(None, msg)
                return render(request, 'workflows/create_workflow.html', {'form': form, 'remix_source': remix_source})
            if remix_source and remix_source.author != request.user:
                Notification.objects.create(recipient=remix_source.author, actor=request.user,
                                            verb='remixed your prompt', target=workflow)
            return redirect('detail', pk=workflow.pk)
    else:
        initial = {}
        if remix_source:
            initial = {
                'title': f'Remix: {remix_source.title}',
                'description': remix_source.description,
                'prompt_text': remix_source.prompt_text,
                'ai_model': remix_source.ai_model,
            }
        form = WorkflowForm(initial=initial)
    return render(request, 'workflows/create_workflow.html', {'form': form, 'remix_source': remix_source})


# --- INSTANT UPVOTE ---
@login_required
def upvote_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    existing_upvote = Upvote.objects.filter(user=request.user, workflow=workflow).first()
    
    if existing_upvote:
        existing_upvote.delete()
        is_upvoted = False
    else:
        Upvote.objects.create(user=request.user, workflow=workflow)
        is_upvoted = True
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_upvoted': is_upvoted, 'upvote_count': workflow.total_upvotes})
    
    return redirect('detail', pk=workflow.pk)


# --- PROFILE & FOLLOWING ---
def user_profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    user_workflows = Workflow.objects.filter(author=profile_user) 
    
    is_following = False
    loved_ids = []
    upvoted_ids = []
    bookmarked_ids = []
    following_usernames = []
    
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()
        loved_ids = list(LoveReaction.objects.filter(user=request.user, workflow__in=user_workflows).values_list('workflow_id', flat=True))
        upvoted_ids = list(Upvote.objects.filter(user=request.user, workflow__in=user_workflows).values_list('workflow_id', flat=True))
        bookmarked_ids = list(Bookmark.objects.filter(user=request.user, workflow__in=user_workflows).values_list('workflow_id', flat=True))
        following_usernames = list(Follow.objects.filter(follower=request.user).values_list('following__username', flat=True))

    total_loves = LoveReaction.objects.filter(workflow__author=profile_user).count()

    return render(request, 'workflows/profile.html', {
        'profile_user': profile_user, 'workflows': user_workflows, 'is_following': is_following,
        'loved_ids': loved_ids, 'upvoted_ids': upvoted_ids, 'bookmarked_ids': bookmarked_ids, 'following_usernames': following_usernames,
        'total_loves': total_loves
    })


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            return redirect('profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'workflows/edit_profile.html', {'u_form': u_form, 'p_form': p_form})

@login_required
def update_profile_picture_view(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        request.user.profile.profile_picture = request.FILES['profile_picture']
        request.user.profile.save()
    return redirect('profile', username=request.user.username)

@login_required
def toggle_follow_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    
    if request.user == profile_user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        return redirect('profile', username=request.user.username)

    existing_follow = Follow.objects.filter(follower=request.user, following=profile_user).first()
    
    if existing_follow:
        existing_follow.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, following=profile_user)
        is_following = True
        Notification.objects.create(recipient=profile_user, actor=request.user, verb='followed you')
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_following': is_following})
    
    return redirect('profile', username=profile_user.username)


# --- EDIT & DELETE WORKFLOW (Cloudinary failures become friendly field errors) ---
@login_required
def update_workflow_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if workflow.author != request.user:
        return redirect('feed')
    if request.method == 'POST':
        form = WorkflowForm(request.POST, request.FILES, instance=workflow)
        if form.is_valid():
            try:
                form.save()
            except Exception:
                msg = ('Cloudinary could not accept that media file. Please try a different file '
                       '(JPG/PNG/WEBP under 10MB, or MP4/WEBM under 60MB).')
                if request.FILES.get('output_image'):
                    form.add_error('output_image', msg)
                elif request.FILES.get('output_video'):
                    form.add_error('output_video', msg)
                else:
                    form.add_error(None, msg)
                return render(request, 'workflows/update_workflow.html', {
                    'form': form, 'workflow': workflow, 'workflow_pk': workflow.pk})
            return redirect('detail', pk=workflow.pk)
    else:
        form = WorkflowForm(instance=workflow)
    return render(request, 'workflows/update_workflow.html', {
        'form': form,
        'workflow': workflow,
        'workflow_pk': workflow.pk})

@login_required
def delete_workflow_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if workflow.author != request.user:
        return redirect('feed')
    if request.method == 'POST':
        workflow.delete()
        return redirect('feed')
    return render(request, 'workflows/delete_workflow.html', {'workflow': workflow})


# --- COMMENTS & LOVE REACTIONS ---
@login_required
def add_comment_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.workflow = workflow
            comment.author = request.user
            comment.save()
            if workflow.author != request.user:
                Notification.objects.create(recipient=workflow.author, actor=request.user, verb='commented on your prompt', target=workflow)
    return redirect('detail', pk=pk)

@login_required
def toggle_love_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    existing_love = LoveReaction.objects.filter(user=request.user, workflow=workflow).first()
    
    if existing_love:
        existing_love.delete()
    else:
        LoveReaction.objects.create(user=request.user, workflow=workflow)
        if workflow.author != request.user:
            Notification.objects.create(recipient=workflow.author, actor=request.user, verb='loved your prompt', target=workflow)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        love_count = workflow.love_reactions.count()
        is_loved = LoveReaction.objects.filter(user=request.user, workflow=workflow).exists()
        return JsonResponse({'love_count': love_count, 'is_loved': is_loved})
    
    return redirect('detail', pk=workflow.pk)


# --- BOOKMARKS ---
@login_required
def toggle_bookmark_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    existing = Bookmark.objects.filter(user=request.user, workflow=workflow).first()
    
    if existing:
        existing.delete()
        is_bookmarked = False
    else:
        Bookmark.objects.create(user=request.user, workflow=workflow)
        is_bookmarked = True
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_bookmarked': is_bookmarked})
    return redirect('detail', pk=workflow.pk)

@login_required
def saved_view(request):
    bookmarks = Bookmark.objects.filter(user=request.user).select_related('workflow', 'workflow__author', 'workflow__author__profile')
    return render(request, 'workflows/saved.html', {'bookmarks': bookmarks})


# --- NETWORK & NOTIFICATIONS ---
def network_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    followers = User.objects.filter(following__following=profile_user)
    following = User.objects.filter(followers__follower=profile_user)
    return render(request, 'workflows/network.html', {'profile_user': profile_user, 'followers': followers, 'following': following})

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'workflows/notifications.html', {'notifications': notifications})


# --- Comments v2: replies + likes ---
def _comment_text_field():
    names = {f.name for f in Comment._meta.fields}
    for cand in ("text", "content", "body", "message", "comment"):
        if cand in names:
            return cand
    return "text"


@login_required
def post_comment_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if text:
            kwargs = {'workflow': workflow, 'author': request.user, _comment_text_field(): text}
            comment = Comment.objects.create(**kwargs)
            if workflow.author != request.user:
                Notification.objects.create(recipient=workflow.author, actor=request.user, verb='commented on your prompt', target=workflow)
    return redirect('detail', pk=workflow.pk)


@login_required
def post_reply_view(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        text = (request.POST.get('text') or '').strip()
        if text:
            reply = Reply.objects.create(comment=comment, author=request.user, text=text)
            if comment.author != request.user:
                Notification.objects.create(recipient=comment.author, actor=request.user, verb='replied to your comment', target=comment.workflow)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('workflows/_reply.html', {'reply': reply}, request=request)
                return JsonResponse({'html': html, 'count': comment.replies.count()})
    return redirect('detail', pk=comment.workflow.pk)


@login_required
def like_comment_view(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    existing = CommentLike.objects.filter(user=request.user, comment=comment).first()
    if existing:
        existing.delete()
        is_liked = False
    else:
        CommentLike.objects.create(user=request.user, comment=comment)
        is_liked = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_liked': is_liked, 'like_count': comment.likes.count()})
    return redirect('detail', pk=comment.workflow.pk)


# --- SELF-HEALING CSRF FAILURE PAGE ---
def csrf_failure_view(request, reason=""):
    _ensure_csrf_token(request)  # set a fresh cookie on this very response
    referer = request.META.get('HTTP_REFERER', '')
    host = request.get_host()
    target = '/'
    if referer:
        try:
            from urllib.parse import urlparse
            if urlparse(referer).netloc == host:
                target = referer
        except Exception:
            target = '/'
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Security refresh - SeePrompts</title>
        <style>
            body {{ font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; background: #f6f4fb;
                   color: #241f36; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
            .card {{ background: #fff; border-radius: 16px; padding: 40px 32px; max-width: 420px; text-align: center;
                    box-shadow: 0 12px 40px rgba(111, 66, 193, .18); }}
            .bolt {{ font-size: 42px; }}
            h1 {{ font-size: 1.25rem; margin: 12px 0 8px; }}
            p {{ color: #6c6680; font-size: .95rem; line-height: 1.5; margin: 0 0 20px; }}
            a {{ display: inline-block; background: #6f42c1; color: #fff; text-decoration: none; padding: 10px 22px;
                border-radius: 999px; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="bolt"><svg viewBox="0 0 24 24" width="42" height="42"><path d="M12 5C7 5 3 9.5 2 12c1 2.5 5 7 10 7s9-4.5 10-7c-1-2.5-5-7-10-7zm0 12c-3.9 0-7.2-3.2-8.3-5C4.8 10.2 8.1 7 12 7s7.2 3.2 8.3 5c-1.1 1.8-4.4 5-8.3 5z" fill="#6f42c1"/><circle cx="12" cy="12" r="3" fill="#6f42c1"/><circle cx="11" cy="11" r="1" fill="#fff"/></svg></div>
            <h1>Quick security refresh</h1>
            <p>Your browser needed a fresh security cookie. We've set one for you — taking you right back so you can try again.</p>
            <a href="{target}">Continue now</a>
        </div>
        <script>setTimeout(function () {{ location.href = "{target}"; }}, 1800);</script>
    </body>
    </html>
    """
    return HttpResponse(html, status=403)
def pwa_manifest(request):
    return JsonResponse({
        'id': '/', 'name': f"{_settings.BRAND_NAME} - AI Prompt Community", 'short_name': _settings.BRAND_NAME,
        'description': _settings.BRAND_TAGLINE, 'start_url': '/?source=pwa', 'scope': '/',
        'display': 'standalone', 'display_override': ['standalone', 'minimal-ui'],
        'orientation': 'portrait-primary', 'background_color': '#14101f', 'theme_color': '#6f42c1',
        'lang': 'en', 'categories': ['productivity', 'social', 'utilities'],
        'icons': [
            {'src': '/static/push/icon-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': '/static/push/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': '/static/push/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
        'shortcuts': [
            {'name': 'New prompt', 'short_name': 'Create', 'url': '/create/?source=shortcut', 'icons': [{'src': '/static/push/icon-192.png', 'sizes': '192x192'}]},
            {'name': 'Trending', 'url': '/trending/?source=shortcut', 'icons': [{'src': '/static/push/icon-192.png', 'sizes': '192x192'}]},
            {'name': 'Notifications', 'url': '/notifications/?source=shortcut', 'icons': [{'src': '/static/push/icon-192.png', 'sizes': '192x192'}]},
        ],
        'share_target': {'action': '/create/', 'method': 'GET', 'params': {'title': 'title', 'text': 'text', 'url': 'url'}},
        'prefer_related_applications': False,
    }, content_type='application/manifest+json')


def offline_view(request):
    return render(request, 'workflows/offline.html')


def favicon_svg(request):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
           '<rect width="24" height="24" rx="5.28" fill="#6f42c1"/>'
           '<path d="M12 5C7 5 3 9.5 2 12c1 2.5 5 7 10 7s9-4.5 10-7c-1-2.5-5-7-10-7zm0 12c-3.9 0-7.2-3.2-8.3-5C4.8 10.2 8.1 7 12 7s7.2 3.2 8.3 5c-1.1 1.8-4.4 5-8.3 5z" fill="#ffffff"/>'
           '<circle cx="12" cy="12" r="3" fill="#ffffff"/>'
           '<circle cx="10.8" cy="10.8" r="0.9" fill="#6f42c1"/></svg>')
    return HttpResponse(svg, content_type='image/svg+xml')


def brand_view(request):
    return render(request, 'workflows/brand.html')


def brand_names_view(request):
    return redirect('brand')


def service_worker(request):
    resp = render(request, 'workflows/sw.js', content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache'
    return resp

@login_required
def notifications_poll(request):
    qs = Notification.objects.filter(recipient=request.user, is_read=False).select_related('actor', 'target')[:5]
    items = [{
        'id': n.id,
        'actor': n.actor.username,
        'verb': n.verb,
        'url': ('/workflow/%s/' % n.target_id) if n.target_id else ('/profile/%s/' % n.actor.username),
    } for n in qs]
    return JsonResponse({'notifications': items,
                         'unread': Notification.objects.filter(recipient=request.user, is_read=False).count()})