from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from .models import Ticket, Message, FAQCategory, FAQArticle, QuickReply
from .forms import TicketCreateForm, TicketReplyForm
from .services.ticket_service import TicketService
from .services.faq_service import FAQService
from django.utils import timezone

staff_member_required = user_passes_test(lambda u: u.is_staff)


@login_required
def support_center(request):
    """Support center homepage."""
    categories = FAQCategory.objects.filter(is_active=True)
    popular_articles = FAQArticle.objects.filter(
        is_active=True,
        is_pinned=True
    ).order_by('-views_count')[:6]

    context = {
        'categories': categories,
        'popular_articles': popular_articles,
    }
    return render(request, 'support/center.html', context)


@login_required
def create_ticket(request):
    """Create new ticket."""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket, error = TicketService.create_ticket(
                user=request.user,
                category=form.cleaned_data['category'],
                subject=form.cleaned_data['subject'],
                description=form.cleaned_data['description'],
                attachments=request.FILES.getlist('attachments'),
                request=request,
            )
            if ticket:
                messages.success(request, f'Тикет #{ticket.ticket_number} создан успешно!')
                return redirect('support:ticket_detail', ticket_id=ticket.id)
            else:
                messages.error(request, error or 'Ошибка при создании тикета')
    else:
        form = TicketCreateForm()

    # Предложить FAQ
    suggested_faqs = []
    if request.GET.get('category') and request.GET.get('subject'):
        suggested_faqs = TicketService.suggest_faq_articles(
            request.GET['category'],
            request.GET['subject'],
            request.GET.get('description', ''),
        )

    return render(request, 'support/create_ticket.html', {
        'form': form,
        'suggested_faqs': suggested_faqs,
    })


@login_required
def my_tickets(request):
    """Мои тикеты"""
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')

    tickets = Ticket.objects.filter(user=request.user)

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if category_filter:
        tickets = tickets.filter(category=category_filter)

    tickets = tickets.order_by('-created_at')

    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    return render(request, 'support/my_tickets.html', {
        'tickets': tickets_page,
        'status_filter': status_filter,
        'category_filter': category_filter,
    })


@login_required
def ticket_detail(request, ticket_id):
    """Детальная страница тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    if request.method == 'POST':
        form = TicketReplyForm(request.POST, request.FILES)
        if form.is_valid():
            message = TicketService.add_reply(
                ticket=ticket,
                sender=request.user,
                text=form.cleaned_data['text'],
                attachments=request.FILES.getlist('attachments'),
                is_internal=False,
            )
            messages.success(request, 'Ответ отправлен!')
            return redirect('support:ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketReplyForm()

    messages_list = Message.objects.filter(ticket=ticket, is_internal=False).order_by('created_at')

    return render(request, 'support/ticket_detail.html', {
        'ticket': ticket,
        'messages': messages_list,
        'form': form,
    })


@login_required
@require_POST
def rate_ticket(request, ticket_id):
    """Оценка тикета"""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        return HttpResponseBadRequest('Invalid rating')

    success, error = TicketService.rate_ticket(ticket, request.user, int(rating), comment)
    if success:
        messages.success(request, 'Спасибо за оценку!')
    else:
        messages.error(request, error or 'Ошибка при оценке тикета')

    return redirect('support:ticket_detail', ticket_id=ticket.id)


@login_required
def faq_list(request):
    """Список FAQ статей"""
    category_slug = request.GET.get('category')
    query = request.GET.get('q')

    articles = FAQArticle.objects.filter(is_active=True)

    if category_slug:
        articles = articles.filter(category__slug=category_slug)
    if query:
        articles = articles.filter(
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(keywords__icontains=query)
        )

    articles = articles.order_by('-is_pinned', 'sort_order', '-views_count')

    return render(request, 'support/faq_list.html', {
        'articles': articles,
        'query': query,
        'category_slug': category_slug,
    })


@login_required
def faq_detail(request, category_slug, article_slug):
    """Детальная страница FAQ статьи"""
    article = get_object_or_404(
        FAQArticle,
        category__slug=category_slug,
        slug=article_slug,
        is_active=True
    )

    # Увеличить счётчик просмотров
    article.views_count += 1
    article.save(update_fields=['views_count'])

    return render(request, 'support/faq_detail.html', {
        'article': article,
    })


@login_required
@require_POST
def faq_helpful(request, article_id):
    """Оценка полезности FAQ статьи"""
    article = get_object_or_404(FAQArticle, id=article_id, is_active=True)

    helpful = request.POST.get('helpful')
    if helpful == 'yes':
        article.helpful_yes += 1
    elif helpful == 'no':
        article.helpful_no += 1
    else:
        return HttpResponseBadRequest('Invalid choice')

    article.save(update_fields=['helpful_yes', 'helpful_no'])

    return JsonResponse({'success': True})


# HTMX API views

@login_required
def suggest_faq(request):
    """Предложение FAQ статей (HTMX)"""
    category = request.GET.get('category')
    subject = request.GET.get('subject', '')
    description = request.GET.get('description', '')

    if not category or not subject:
        return JsonResponse({'html': ''})

    suggested_faqs = TicketService.suggest_faq_articles(category, subject, description)

    html = render(request, 'support/partials/faq_suggestions.html', {
        'suggested_faqs': suggested_faqs,
    }).content.decode('utf-8')

    return JsonResponse({'html': html})

from .services.sla_service import SLAService


@login_required
@staff_member_required
def analytics(request):
    """Аналитика поддержки для администраторов."""
    sla_stats = SLAService.get_sla_stats()
    category_stats = SLAService.get_category_stats()
    operator_stats = SLAService.get_operator_stats()
    chat_stats = SLAService.get_chat_stats()
    faq_stats = SLAService.get_faq_stats()

    context = {
        'sla_stats': sla_stats,
        'category_stats': category_stats,
        'operator_stats': operator_stats,
        'chat_stats': chat_stats,
        'faq_stats': faq_stats,
    }

    return render(request, 'support/analytics.html', context)


# Operator views
@login_required
@staff_member_required
def operator_dashboard(request):
    """Operator dashboard."""
    # Get operator profile
    operator_profile = request.user.operator_profile

    # Stats
    stats = {
        'active_chats': operator_profile.current_chats_count,
        'active_tickets': operator_profile.current_tickets_count,
        'avg_rating': operator_profile.avg_rating,
        'total_handled': operator_profile.total_tickets_handled,
    }

    # Active chats (simplified)
    active_chats = []  # TODO: implement

    # Active tickets
    active_tickets = Ticket.objects.filter(
        assigned_to=request.user,
        status__in=['open', 'in_progress', 'waiting_user']
    ).order_by('-updated_at')[:10]

    context = {
        'stats': stats,
        'active_chats': active_chats,
        'active_tickets': active_tickets,
    }
    return render(request, 'support/operator/dashboard.html', context)


@login_required
@staff_member_required
def operator_tickets(request):
    """Operator tickets list."""
    tickets = Ticket.objects.filter(assigned_to=request.user).order_by('-updated_at')

    # Filters
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)

    paginator = Paginator(tickets, 20)
    page = request.GET.get('page')
    tickets_page = paginator.get_page(page)

    context = {
        'tickets': tickets_page,
        'status_filter': status,
    }
    return render(request, 'support/operator/tickets.html', context)


@login_required
@staff_member_required
def operator_ticket_detail(request, ticket_id):
    """Operator ticket detail."""
    ticket = get_object_or_404(Ticket, id=ticket_id, assigned_to=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reply':
            # Handle reply
            pass
        elif action == 'change_status':
            # Handle status change
            pass

    messages_list = Message.objects.filter(ticket=ticket, is_internal=False).order_by('created_at')

    context = {
        'ticket': ticket,
        'messages': messages_list,
    }
    return render(request, 'support/operator/ticket_detail.html', context)
