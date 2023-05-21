from django.views.generic.list import ListView

from .models import Answer


class AnswerListView(ListView):
    model = Answer
    template_name = 'answer_list.html'

    def get_queryset(self):
        return Answer.objects.unbound().with_topic_entities()
