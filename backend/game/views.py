import logging

from django.views.generic.list import ListView

from .models import Answer, Round

logger = logging.getLogger(__name__)


class RoundListView(ListView):
    queryset = Round.objects.filter(checked=False).select_related('topic')
    paginate_by = 20
    template_name = 'round_list.html'


class AnswerListView(ListView):
    model = Answer
    paginate_by = 20
    template_name = 'answer_list.html'

    def get_queryset(self):
        logger.warning('test warning')
        return Answer.objects.order_by('-sent_at').unbound().with_topic_entities()
