from django.core.management.base import BaseCommand
from game.models import Player

from tqdm import tqdm


class Command(BaseCommand):

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        for player in tqdm(Player.objects.all()):
            player.update_statistics()
