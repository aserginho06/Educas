import json
import time

from django.core.management.base import BaseCommand

from common.ai_content import generate_json, get_ai_configuration


class Command(BaseCommand):
    help = "Valida a integracao OpenRouter com uma chamada de teste e exibe métricas detalhadas."

    def handle(self, *args, **options):
        config_data = get_ai_configuration()
        self.stdout.write(self.style.NOTICE("Teste de integracao OpenRouter"))
        self.stdout.write("API ativa: %s" % str(config_data["enabled"]))
        self.stdout.write("Modelo: %s" % config_data["model"])

        prompt = (
            "Gere um aviso escolar curto e profissional em portugues brasileiro. "
            "Retorne um objeto JSON com a chave aviso."  # explicit prompt
        )
        fallback = {
            "aviso": "Lembrem-se de entregar o trabalho de matematica ate sexta-feira."
        }

        start_time = time.perf_counter()
        payload, meta = generate_json(prompt=prompt, fallback=fallback)
        elapsed = time.perf_counter() - start_time

        self.stdout.write("Tempo: %.2f segundos" % elapsed)
        self.stdout.write("Provedor: %s" % meta.get("provider"))
        self.stdout.write("API usada: %s" % str(meta.get("used_api", False)))
        self.stdout.write("Erro: %s" % str(meta.get("error")))
        self.stdout.write("")

        self.stdout.write(self.style.SUCCESS("Resposta recebida:"))
        try:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception:
            self.stdout.write(str(payload))
