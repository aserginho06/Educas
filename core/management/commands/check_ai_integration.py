from django.core.management.base import BaseCommand

from common.ai_content import generate_json, get_ai_runtime_status, is_ai_enabled


class Command(BaseCommand):
    help = "Valida se a integracao de IA do Educas esta configurada e retornando JSON valido."

    def handle(self, *args, **options):
        payload, meta = generate_json(
            prompt=(
                "Gere JSON com as chaves first_names, last_names, teacher_messages e student_comments. "
                "Use um exemplo curto para validacao tecnica."
            ),
            fallback={
                "first_names": ["Ana"],
                "last_names": ["Silva"],
                "teacher_messages": ["Mensagem institucional de teste."],
                "student_comments": ["Comentario curto de teste."],
            },
        )

        if meta["used_api"]:
            self.stdout.write(self.style.SUCCESS("Integracao de IA ativa e respondendo corretamente."))
        elif is_ai_enabled():
            self.stdout.write(
                self.style.WARNING(
                    f"Chave configurada, mas houve falha externa. Fallback local ativado. Motivo: {meta['error']}"
                )
            )
        else:
            self.stdout.write(self.style.WARNING("Chave ausente. Fallback local ativo."))

        runtime_status = get_ai_runtime_status()
        self.stdout.write(self.style.NOTICE(f"Provedor: {meta['provider']}"))
        self.stdout.write(self.style.NOTICE(f"API ativa: {meta['used_api']}"))
        self.stdout.write(self.style.NOTICE(f"Modelo: {runtime_status['model']}"))
        self.stdout.write(self.style.NOTICE(f"Chamadas registradas: {runtime_status['calls']}"))
        self.stdout.write(self.style.NOTICE(f"Fallbacks registrados: {runtime_status['fallback']}"))
        self.stdout.write(self.style.NOTICE(f"Chaves recebidas: {', '.join(sorted(payload.keys()))}"))
