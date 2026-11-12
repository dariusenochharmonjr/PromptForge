from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import NOT_PROVIDED
from django.utils import timezone
from workflows.models import Workflow, Comment, LoveReaction, Upvote, Bookmark, Follow, Profile
try:
    from workflows.models import CommentLike
except ImportError:
    CommentLike = None

PASSWORD = "demo1234!"
PEOPLE = [("nova", "Nova Reyes"), ("atlas", "Atlas Kim"), ("pixel", "Pixel Adeyemi")]
MODELS = ["Claude", "Midjourney", "GPT-4", "DALL-E", "Stable Diffusion", "Gemini"]
TOPICS = [
    ("Cinematic Product Hero", "matte black smart speaker on marble, rim lighting, 85mm f/1.8"),
    ("Legacy Python Refactor", "characterization tests first, then small safe commits"),
    ("Cold Email That Replies", "90 words, one specific reference, one low-friction ask"),
    ("Isometric City Block", "coffee shop, bookstore, rooftop garden, pastel vector"),
    ("SQL Query Optimizer", "indexes, rewrite, expected plan change"),
    ("Brand Voice Guide", "4 principles, do and don't examples, 3 channel samples"),
    ("Watercolor Travel Poster", "Lagos coastline at golden hour, fishing boats, paper grain"),
    ("Django View Tests", "auth, permissions, pagination, AJAX branches, factories"),
    ("Launch Tweet Thread", "7 tweets: hook, demo, proof, CTA"),
    ("Neon Night Market", "rain reflections, steam, cyan and magenta signage, courier"),
    ("Helpful API Errors", "what happened, why, exact next step, under 140 chars"),
    ("Bakery Logo Concepts", "wordmark, emblem, combination mark, hex codes and fonts"),
    ("Coffee Crema Macro", "golden bubbles, shallow depth of field, warm side light"),
    ("ETL Retry Logic", "backoff, dead-letter queue, idempotency keys, metrics"),
    ("Onboarding Checklist", "6 steps to first live dashboard, empty-state copy"),
    ("Desert Observatory", "milky way rising, warm dome light, dust in air, 35mm"),
    ("Readable Changelog", "New, Improved, Fixed; one sentence each"),
    ("Seed Pitch Deck", "10 slides, one headline each, climate-risk API"),
    ("Portrait Lighting Map", "key, fill, rim positions, ratios, modifiers, settings"),
    ("Regex Without Tears", "token by token, 12 test cases, safer rewrite"),
    ("Support Macro Library", "refund, failed payment, plan change, duplicate charge"),
    ("Floating Island Garden", "waterfalls into clouds, greenhouse, tiny visitors"),
    ("Postgres Index Advisor", "reasoning, write overhead, redundant index flags"),
    ("Weekly Review Template", "wins, blockers, metrics, next-week focus"),
]
LINES = [
    "Saved me an hour of trial and error.",
    "Clean results even on a smaller model.",
    "The constraints are what make this work.",
    "Bookmarking for our next sprint.",
    "Clear, testable, no fluff.",
    "Swapped the palette and it still held together.",
]


def fill_required(model, kwargs):
    for f in model._meta.fields:
        if f.primary_key or f.name in kwargs or f.null or f.blank:
            continue
        if getattr(f, "default", NOT_PROVIDED) is not NOT_PROVIDED:
            continue
        if getattr(f, "auto_now", False) or getattr(f, "auto_now_add", False):
            continue
        kind = f.get_internal_type()
        if kind in ("CharField", "TextField", "SlugField"):
            kwargs[f.name] = (str(kwargs.get("title", "demo")) + " " + f.name)[:180]
        elif kind in ("IntegerField", "BigIntegerField", "PositiveIntegerField", "SmallIntegerField"):
            kwargs[f.name] = 0
        elif kind == "BooleanField":
            kwargs[f.name] = False
        elif kind in ("DateTimeField", "DateField"):
            kwargs[f.name] = timezone.now()
        elif kind == "FloatField":
            kwargs[f.name] = 0.0


class Command(BaseCommand):
    help = "Seed demo data for local infinite-scroll testing."

    def handle(self, *args, **options):
        users = []
        for un, full in PEOPLE:
            first, _, last = full.partition(" ")
            u, created = User.objects.get_or_create(
                username=un,
                defaults={"first_name": first, "last_name": last, "email": f"{un}@promptforge.dev"},
            )
            if created:
                u.set_password(PASSWORD)
                u.save()
            try:
                Profile.objects.get_or_create(user=u, defaults={"bio": f"{full} builds prompts that ship."})
            except Exception:
                pass
            users.append(u)

        wfs = []
        for i, (title, idea) in enumerate(TOPICS):
            model = MODELS[i % len(MODELS)]
            author = users[i % len(users)]
            kwargs = {
                "title": title,
                "description": f"A repeatable {model} workflow: {idea}.",
                "prompt_text": f"You are a senior practitioner. {idea}. Return production-ready output with constraints and examples.",
                "ai_model": model,
                "author": author,
            }
            fill_required(Workflow, kwargs)
            wf, _ = Workflow.objects.get_or_create(title=title, defaults=kwargs)
            Workflow.objects.filter(pk=wf.pk).update(created_at=timezone.now() - timedelta(hours=i * 9 + 3))
            wfs.append(wf)

        tf = next((n for n in ("text", "content", "body", "message", "comment")
                   if any(f.name == n for f in Comment._meta.fields)), None)
        comments = []
        if tf:
            for i, wf in enumerate(wfs[:14]):
                for j in range(2):
                    au = users[(i + j + 1) % len(users)]
                    kw = {"workflow": wf, "author": au, tf: LINES[(i + j) % len(LINES)]}
                    fill_required(Comment, kw)
                    c, _ = Comment.objects.get_or_create(workflow=wf, author=au, **{tf: kw[tf]}, defaults=kw)
                    comments.append(c)

        for i, wf in enumerate(wfs):
            for ui, u in enumerate(users):
                if u == wf.author:
                    continue
                if (i + ui) % 2 == 0:
                    LoveReaction.objects.get_or_create(user=u, workflow=wf)
                if (i + ui) % 3 == 0:
                    Upvote.objects.get_or_create(user=u, workflow=wf)
                if (i + ui) % 4 == 0:
                    Bookmark.objects.get_or_create(user=u, workflow=wf)

        Follow.objects.get_or_create(follower=users[0], following=users[1])
        Follow.objects.get_or_create(follower=users[1], following=users[2])
        Follow.objects.get_or_create(follower=users[2], following=users[0])

        if CommentLike:
            for i, c in enumerate(comments):
                for ui, u in enumerate(users):
                    if u != c.author and (i + ui) % 3 == 0:
                        CommentLike.objects.get_or_create(user=u, comment=c)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(wfs)} workflows and {len(comments)} comments. Login: nova / {PASSWORD}"
        ))