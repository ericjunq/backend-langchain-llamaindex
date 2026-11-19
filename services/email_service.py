"""Envio de emails de aviso (LGPD: transparência quando algo muda na conta).

Backends (EMAIL_BACKEND no .env):
  - console: não envia; registra no log só o assunto e o destinatário MASCARADO (nada pessoal em log).
  - smtp:    envia de verdade, em segundo plano (não atrasa a resposta da API), com STARTTLS.
  - memoria: guarda em `caixa_de_saida` (usado pelos testes).
"""
import logging
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage

from security.settings import settings

log = logging.getLogger('email')
caixa_de_saida: list[dict] = []
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='email')

RODAPE = ('\n\nSe não foi você, troque sua senha imediatamente e fale com o responsável pela sua empresa.'
          '\n\nEste é um aviso automático de segurança; não responda este email.')


def mascarar_email(email: str) -> str:
    usuario, _, dominio = (email or '').partition('@')
    return f'{usuario[:1]}***@{dominio}'


def _enviar_smtp(destinatario: str, assunto: str, corpo: str) -> None:
    msg = EmailMessage()
    msg['From'] = settings.email_remetente
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg.set_content(corpo)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_porta, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_usuario:
                smtp.login(settings.smtp_usuario, settings.smtp_senha)
            smtp.send_message(msg)
    except Exception:
        log.exception('Falha ao enviar email "%s" para %s', assunto, mascarar_email(destinatario))


def enviar(destinatario: str, assunto: str, corpo: str) -> None:
    # .invalid é reservado (RFC 2606): usado nas contas anonimizadas, nunca recebe email.
    if not destinatario or destinatario.lower().endswith('.invalid'):
        return
    if settings.email_backend == 'memoria':
        caixa_de_saida.append({'para': destinatario, 'assunto': assunto, 'corpo': corpo})
    elif settings.email_backend == 'smtp':
        _executor.submit(_enviar_smtp, destinatario, assunto, corpo)
    else:
        log.info('Email "%s" para %s (backend console: não enviado)', assunto, mascarar_email(destinatario))


# --- Avisos ---

def avisar_senha_alterada(nome: str, email: str) -> None:
    enviar(email, 'Sua senha foi alterada',
           f'Olá, {nome}.\n\nA senha da sua conta foi alterada e as outras sessões foram encerradas.' + RODAPE)


def avisar_email_alterado(nome: str, email_antigo: str, email_novo: str) -> None:
    corpo = (f'Olá, {nome}.\n\nO email de acesso da sua conta foi alterado de {mascarar_email(email_antigo)} '
             f'para {mascarar_email(email_novo)}.' + RODAPE)
    # Avisa os dois endereços: se a troca foi indevida, o dono do email antigo fica sabendo.
    enviar(email_antigo, 'O email da sua conta foi alterado', corpo)
    enviar(email_novo, 'O email da sua conta foi alterado', corpo)


def avisar_conta_anonimizada(nome: str, email: str) -> None:
    """Último email para o endereço antigo: depois disso ele não fica mais guardado."""
    enviar(email, 'Sua conta foi anonimizada',
           f'Olá, {nome}.\n\nConforme solicitado, seus dados pessoais foram anonimizados e sua conta foi '
           'desativada. O histórico de vendas da empresa continua existindo, sem identificar você.'
           '\n\nEste é um aviso automático; não responda este email.')


def avisar_sessao_comprometida(nome: str, email: str) -> None:
    enviar(email, 'Alerta de segurança: sessões encerradas',
           f'Olá, {nome}.\n\nDetectamos o reuso de um token de acesso antigo, o que pode indicar que ele foi '
           'copiado. Por segurança, encerramos todas as suas sessões: entre novamente.' + RODAPE)
