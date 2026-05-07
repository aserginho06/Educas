from django.db import models


class UsuarioSistema(models.Model):
    class Perfil(models.TextChoices):
        ALUNO = "aluno", "Aluno"
        PROFESSOR = "professor", "Professor"
        GESTOR = "gestor", "Gestor"
        RESPONSAVEL = "responsavel", "Responsavel"

    nome = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    matricula = models.CharField(max_length=30, blank=True)
    perfil = models.CharField(max_length=20, choices=Perfil.choices, default=Perfil.ALUNO)
    turma = models.CharField(max_length=80, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "usuario do sistema"
        verbose_name_plural = "usuarios do sistema"

    def __str__(self):
        return f"{self.nome} ({self.get_perfil_display()})"


class Turma(models.Model):
    nome = models.CharField(max_length=80)
    ano_letivo = models.PositiveIntegerField(default=2026)
    periodo = models.CharField(max_length=40, default="Manha")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.ano_letivo}"


class Disciplina(models.Model):
    nome = models.CharField(max_length=100)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name="disciplinas")
    professor = models.CharField(max_length=120)
    horario = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.turma.nome}"


class EventoAcademico(models.Model):
    class Tipo(models.TextChoices):
        AVALIACAO = "avaliacao", "Avaliacao"
        ENTREGA = "entrega", "Entrega"
        AULA = "aula", "Aula"
        REUNIAO = "reuniao", "Reuniao"

    titulo = models.CharField(max_length=140)
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.AULA)
    disciplina = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["data", "titulo"]
        verbose_name = "evento academico"
        verbose_name_plural = "eventos academicos"

    def __str__(self):
        return f"{self.titulo} - {self.data:%d/%m/%Y}"


class Nota(models.Model):
    aluno = models.ForeignKey(UsuarioSistema, on_delete=models.CASCADE, related_name="notas")
    disciplina = models.CharField(max_length=100)
    avaliacao = models.CharField(max_length=80)
    valor = models.DecimalField(max_digits=4, decimal_places=1)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["aluno__nome", "disciplina"]

    def __str__(self):
        return f"{self.aluno.nome} - {self.disciplina}: {self.valor}"


class PostFeed(models.Model):
    autor = models.CharField(max_length=120)
    conteudo = models.TextField()
    categoria = models.CharField(max_length=60, default="Geral")
    publicado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "post do feed"
        verbose_name_plural = "posts do feed"

    def __str__(self):
        return f"{self.autor} - {self.categoria}"
