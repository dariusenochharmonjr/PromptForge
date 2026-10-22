from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import JsonResponse 
from django.utils import timezone
from datetime import timedelta

from .models import Workflow, Upvote, Profile, Follow, LoveReaction, Comment, Notification, Bookmark
from .forms import WorkflowForm, UserUpdateForm, ProfileUpdateForm, CommentForm


# --- FEED & SEARCH ---
def feed_view(request):
    workflows = Workflow.objects.all()
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

    return render(request, 'workflows/feed.html', {
        'workflows': workflows, 'search_query': search_query, 'model_filter': model_filter,
        'loved_ids': loved_ids, 'upvoted_ids': upvoted_ids, 'bookmarked_ids': bookmarked_ids, 'following_usernames': following_usernames
    })


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


# --- CREATE WORKFLOW ---
@login_required
def create_workflow_view(request):
    if request.method == 'POST':
        form = WorkflowForm(request.POST, request.FILES)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.author = request.user
            workflow.save()
            return redirect('detail', pk=workflow.pk)
    else:
        form = WorkflowForm()
    return render(request, 'workflows/create_workflow.html', {'form': form})


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


# --- EDIT & DELETE WORKFLOW ---
@login_required
def update_workflow_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if workflow.author != request.user: return redirect('feed')
    if request.method == 'POST':
        form = WorkflowForm(request.POST, request.FILES, instance=workflow)
        if form.is_valid():
            form.save()
            return redirect('detail', pk=workflow.pk)
    else:
        form = WorkflowForm(instance=workflow)
    return render(request, 'workflows/update_workflow.html', {'form': form})

@login_required
def delete_workflow_view(request, pk):
    workflow = get_object_or_404(Workflow, pk=pk)
    if workflow.author != request.user: return redirect('feed')
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