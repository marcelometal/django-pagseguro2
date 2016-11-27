# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from pagseguro.settings import PAGSEGURO_LOG_IN_MODEL
from pagseguro.signals import (
    checkout_realizado, notificacao_recebida, save_checkout,
    update_transaction, pre_approvals_realizado, save_pre_approvals
)


TRANSACTION_TYPE = (
    ('1', 'Pagamento'),
    ('11', 'Recorrência'),
)

TRANSACTION_STATUS_CHOICES = (
    ('aguardando', 'Aguardando'),
    ('em_analise', 'Em análise'),
    ('pago', 'Pago'),
    ('disponivel', 'Disponível'),
    ('em_disputa', 'Em disputa'),
    ('devolvido', 'Devolvido'),
    ('cancelado', 'Cancelado')
)

PRE_APPROVALS_PERIOD = (
    ('WEEKLY', 'Semanal'),
    ('MONTHLY', 'Mensal'),
    ('BIMONTHLY', '2 vezes ao mês'),
    ('TRIMONTHLY', '3 vezes por mês'),
    ('SEMIANNUALLY', 'A cada 6 meses'),
    ('YEARLY', 'Anualmente'),
)

PRE_APPROVALS_CHARGE = (
    ('auto', 'Automática'),
    ('manual', 'Manual'),
)


@python_2_unicode_compatible
class Checkout(models.Model):

    code = models.CharField(
        'código',
        max_length=100,
        blank=True,
        help_text='Código gerado para redirecionamento.'
    )

    date = models.DateTimeField(
        'Data',
        help_text='Data em que o checkout foi realizado.'
    )

    success = models.BooleanField(
        'Sucesso',
        db_index=True,
        help_text='O checkout foi feito com sucesso?',
        default=False
    )

    message = models.TextField(
        'Mensagem de erro',
        blank=True,
        help_text='Mensagem apresentada no caso de erro no checkout.'
    )

    def __str__(self):
        return '{0}'.format(self.pk)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Checkout'
        verbose_name_plural = 'Checkouts'


@python_2_unicode_compatible
class Transaction(models.Model):

    transaction_type = models.CharField(
        'tipo',
        default='1',
        max_length=2,
        db_index=True,
        choices=TRANSACTION_TYPE,
        help_text='Representa o tipo da transação recebida.'
    )

    code = models.CharField(
        'código',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='O código da transação.'
    )

    reference = models.CharField(
        'referência',
        max_length=200,
        db_index=True,
        blank=True,
        help_text='A referência passada na transação.'
    )

    status = models.CharField(
        'Status',
        max_length=20,
        db_index=True,
        choices=TRANSACTION_STATUS_CHOICES,
        help_text='Status atual da transação.'
    )

    date = models.DateTimeField(
        'Data',
        help_text='Data em que a transação foi criada.'
    )

    last_event_date = models.DateTimeField(
        'Última alteração',
        help_text='Data da última alteração na transação.'
    )

    content = models.TextField(
        'Transação',
        help_text='Transação no formato json.'
    )

    def __str__(self):
        return self.code

    class Meta:
        ordering = ['-date']
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'


@python_2_unicode_compatible
class TransactionHistory(models.Model):

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        verbose_name='Transação'
    )

    status = models.CharField(
        'Status',
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES,
        help_text='Status da transação.'
    )

    date = models.DateTimeField(
        'Data'
    )

    def __str__(self):
        return '{0} - {1} - {2}'.format(
            self.transaction, self.status, self.date
        )

    class Meta:
        ordering = ['date']
        verbose_name = 'Histórico da transação'
        verbose_name_plural = 'Históricos de transações'


@python_2_unicode_compatible
class PreApprovals(models.Model):

    charge = models.CharField(
        'Cobrança',
        max_length=20,
        db_index=True,
        choices=PRE_APPROVALS_CHARGE,
        help_text='Indica se a assinatura será gerenciada pelo PagSeguro (automática) ou pelo Vendedor (manual)',
    )

    name = models.CharField(
        'Nome',
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Nome/Identificador da assinatura',
    )

    details = models.TextField(
        'Detalhes',
        max_length=255,
        blank=True,
        help_text='Detalhes/Descrição da assinatura',
    )

    amount_per_payment = models.DecimalField(
        'Valor da cobrança',
        max_digits=9,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor exato de cada cobrança',
    )

    max_amount_per_payment = models.DecimalField(
        'Valor máximo de cada cobrança',
        max_digits=9,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de cada cobrança',
    )

    period = models.CharField(
        'Periodicidade',
        max_length=20,
        db_index=True,
        choices=PRE_APPROVALS_PERIOD,
        help_text='Periodicidade da cobrança',
    )

    final_date = models.DateTimeField(
        'Data Final',
        db_index=True,
        help_text='Fim da vigência da assinatura',
    )

    max_total_amount = models.DecimalField(
        'Valor máximo de cada cobrança',
        max_digits=9,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Valor máximo de cada cobrança',
    )

    reference = models.CharField(
        'Referência',
        max_length=200,
        db_index=True,
        blank=True,
        null=True,
        help_text='A referência passada na transação.'
    )

    redirect_code = models.CharField(
        'código',
        max_length=100,
        blank=True,
        null=True,
        help_text='Código gerado para redirecionamento.'
    )

    def __str__(self):
        return '{0}'.format(self.name)

    def redirect_url(self):
        if self.redirect_code:
            return '{0}?code={1}'.format(
                self.pre_approvals_redirect_url, self.redirect_code
            )
        return ''

    class Meta:
        verbose_name = 'Plano de Assinatura'
        verbose_name_plural = 'Planos de Assinaturas'


@python_2_unicode_compatible
class PreApprovalsRequest(models.Model):

    code = models.CharField(
        'código',
        max_length=100,
        blank=True,
        help_text='Código gerado para redirecionamento.'
    )

    date = models.DateTimeField(
        'Data',
        help_text='Data em que a assinatura foi realizada.'
    )

    success = models.BooleanField(
        'Sucesso',
        db_index=True,
        help_text='A assinatura foi feito com sucesso?',
        default=False
    )

    message = models.TextField(
        'Mensagem de erro',
        blank=True,
        help_text='Mensagem apresentada no caso de erro na assinatura.'
    )

    def __str__(self):
        return '{0}'.format(self.pk)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Assinatura Request'
        verbose_name_plural = 'Assinaturas Request'


# Signals
if PAGSEGURO_LOG_IN_MODEL:
    checkout_realizado.connect(save_checkout)
    notificacao_recebida.connect(update_transaction)
    pre_approvals_realizado.connect(save_pre_approvals)
