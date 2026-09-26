import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.inference import get_classifier

SAMPLES_DIR = Path(settings.BASE_DIR) / 'asset' / 'samples'
FILENAME_RE = re.compile(r'^grade(\d)_\d+\.png$')


class Command(BaseCommand):
    help = 'Runs the KOA classifier against asset/samples/ and reports predicted vs true grade.'

    def handle(self, *args, **options):
        classifier = get_classifier()
        samples = sorted(SAMPLES_DIR.glob('grade*_*.png'))

        if not samples:
            self.stderr.write(f'No sample images found in {SAMPLES_DIR}')
            return

        first_x = classifier.preprocess(str(samples[0]))
        self.stdout.write(
            f'Preprocessed array stats for {samples[0].name}: '
            f'min={first_x.min():.2f} max={first_x.max():.2f} mean={first_x.mean():.2f}'
        )
        if first_x.max() <= 1.5:
            self.stdout.write(self.style.ERROR(
                'max ~= 1.0 -- looks like the image was normalized (/255 bug). Expected max ~= 255.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('max ~= 255 -- raw pixel range looks correct.'))
        self.stdout.write('')

        header = f'{"file":<14}{"true":>6}{"pred":>6}{"expected":>10}{"confidence":>12}{"match":>7}'
        self.stdout.write(header)
        self.stdout.write('-' * len(header))

        matches = 0
        for sample_path in samples:
            m = FILENAME_RE.match(sample_path.name)
            if not m:
                continue
            true_grade = int(m.group(1))
            result = classifier.predict(str(sample_path))
            is_match = result['grade'] == true_grade
            matches += is_match

            self.stdout.write(
                f'{sample_path.name:<14}{true_grade:>6}{result["grade"]:>6}'
                f'{result["expected_grade"]:>10.2f}{result["confidence"]:>12.2%}'
                f'{"OK" if is_match else "X":>7}'
            )

        self.stdout.write('')
        self.stdout.write(f'{matches}/{len(samples)} matched')
