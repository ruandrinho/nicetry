from django.views.generic.list import ListView

from .models import Answer


class AnswerListView(ListView):
    model = Answer
    paginate_by = 20
    template_name = 'answer_list.html'

    def get_queryset(self):
        return Answer.objects.order_by('-sent_at').unbound().with_topic_entities()
