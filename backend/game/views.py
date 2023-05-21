from django.utils import timezone
from django.views.generic.list import ListView

from .models import Answer


class AnswerListView(ListView):
    model = Answer
    paginate_by = 20
    template_name = 'answer_list.html'

    def get_queryset(self):
        return Answer.objects.order_by('-sent_at').unbound().with_topic_entities()


class AnswerList24hView(ListView):
    model = Answer
    paginate_by = 20
    template_name = 'answer_list.html'

    def get_queryset(self):
        now = timezone.now()
        one_day_ago = now - timezone.timedelta(days=1)
        return Answer.objects.filter(sent_at__gte=one_day_ago).order_by('-sent_at').unbound().with_topic_entities()
