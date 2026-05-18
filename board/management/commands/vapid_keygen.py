import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class Command(BaseCommand):
    help = (
        "Generate a fresh VAPID keypair for web-push. Print the values once and "
        "set them as environment variables: VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY."
    )

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())

        private_number = private_key.private_numbers().private_value
        private_raw = private_number.to_bytes(32, "big")
        private_b64 = _b64url(private_raw)

        public_numbers = private_key.public_key().public_numbers()
        public_bytes = (
            b"\x04"
            + public_numbers.x.to_bytes(32, "big")
            + public_numbers.y.to_bytes(32, "big")
        )
        public_b64 = _b64url(public_bytes)

        self.stdout.write(self.style.SUCCESS("# Add these to your backend environment (Render):\n"))
        self.stdout.write("VAPID_PUBLIC_KEY=" + public_b64 + "\n")
        self.stdout.write("VAPID_PRIVATE_KEY=" + private_b64 + "\n")
        self.stdout.write("VAPID_SUBJECT=mailto:you@example.com\n")
        self.stdout.write(
            "\n# Add this to your frontend environment (Cloudflare):\n"
        )
        self.stdout.write("NEXT_PUBLIC_VAPID_PUBLIC_KEY=" + public_b64 + "\n")
