from django.db import models

class EstruturaProduto(models.Model):
    codigo_vo = models.CharField(max_length=50, default=0.0, verbose_name="Código Vo", db_index=True)
    descricao_vo = models.CharField(max_length=255, default='', verbose_name="Descrição Vo")

    codigo_pai = models.CharField(max_length=50, default=0.0, verbose_name="Código Pai", db_index=True)
    descricao_pai = models.CharField(max_length=255, default='', verbose_name="Descrição Pai")

    codigo_filho = models.CharField(max_length=50, default=0.0, verbose_name="Código filho", db_index=True)
    descricao_filho = models.CharField(max_length=255, default='', verbose_name="Descrição filho")

    quantidade_necessaria_filho = models.DecimalField(max_digits=12, decimal_places=4, default=0.0, verbose_name="Qtd Necessária")
    quantidade_em_op = models.DecimalField(max_digits=12, decimal_places=4, default=0.0, verbose_name="Quantidade em OP")
    falta_produzir = models.DecimalField(max_digits=12, decimal_places=4, default=0.0, verbose_name="Falta Produzir")

    data_importacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Importação", db_index=True)

    class Meta:
        verbose_name = "Estrutura e Produção"
        verbose_name_plural = "Estruturas e Produção"

    def __str__(self):
        return f"{self.codigo_vo} | {self.codigo_pai} -> {self.codigo_filho}"