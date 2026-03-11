from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from django.conf import settings
import environ
import traceback

class Command(BaseCommand):
    help = 'Roda o bot do Telegram'

    def handle(self, *args, **options):
        env = environ.Env()
        token = env('TELEGRAM_BOT_TOKEN', default='SEU_TOKEN_AQUI')
        
        if token == 'SEU_TOKEN_AQUI':
            self.stdout.write(self.style.ERROR('Erro: TELEGRAM_BOT_TOKEN não configurado no .env'))
            return

        app = ApplicationBuilder().token(token).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("vincular", self.vincular))
        app.add_handler(CommandHandler("me", self.me))
        app.add_handler(CommandHandler("base", self.selecionar_base))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.chat))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_pdf))

        self.stdout.write(self.style.SUCCESS('Bot iniciado...'))
        app.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Olá! Bem-vindo ao RAG Enterprise.\n\n"
            "Para começar, você precisa vincular sua conta.\n"
            "Use: /vincular <seu_token_do_site>"
        )

    async def vincular(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from core_api.models import Member
        from asgiref.sync import sync_to_async
        import uuid

        if not context.args:
            await update.message.reply_text("Uso: /vincular <token>")
            return

        token_str = context.args[0]
        try:
            # Validar formato UUID
            token_uuid = uuid.UUID(token_str)
            member = await sync_to_async(Member.objects.get)(linking_token=token_uuid)
            
            # Verificar se já é o ID dele ou de outro
            current_id = update.effective_user.id
            member.telegram_id = current_id
            await sync_to_async(member.save)()
            
            await update.message.reply_text(f"✅ Vinculado! Bem-vindo, {member.user.username} da {member.organization.name}.")
        except ValueError:
            await update.message.reply_text("❌ Erro: Token com formato inválido.")
        except Member.DoesNotExist:
            await update.message.reply_text("❌ Erro: Token não encontrado.")
        except Exception as e:
            # Caso o telegram_id já pertença a outra conta (unique constraint)
            print(f"Erro no vínculo: {str(e)}")
            await update.message.reply_text(f"⚠️ Erro ao vincular: Este ID do Telegram já está em uso por outro usuário.")

    async def me(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Seu ID do Telegram é: {update.effective_user.id}")

    async def selecionar_base(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from core_api.models import Member, KnowledgeBase
        from asgiref.sync import sync_to_async

        telegram_id = update.effective_user.id
        try:
            member = await sync_to_async(lambda: Member.objects.select_related('organization').get(telegram_id=telegram_id))()
        except Member.DoesNotExist:
            await update.message.reply_text("❌ Você precisa vincular sua conta primeiro. Use /vincular <token>")
            return

        if not context.args:
            # Listar bases disponíveis
            bases = await sync_to_async(list)(
                KnowledgeBase.objects.filter(organization=member.organization)
            )
            if not bases:
                await update.message.reply_text("Sua organização ainda não possui nenhuma Base de Conhecimento.")
                return
            
            msg = "📚 **Bases de Conhecimento Disponíveis:**\n"
            for b in bases:
                msg += f"ID: `{b.id}` - {b.name} ({b.get_access_level_display()})\n"
            msg += "\nUse `/base <ID>` para selecionar a sua base ativa para conversar ou subir PDFs."
            from telegram.constants import ParseMode
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            return

        # Selecionar a base
        kb_id = context.args[0]
        try:
            kb = await sync_to_async(KnowledgeBase.objects.get)(id=kb_id, organization=member.organization)
            context.user_data['active_kb_id'] = kb.id
            context.user_data['active_kb_name'] = kb.name
            await update.message.reply_text(f"✅ Base de Conhecimento alterada para: **{kb.name}**", parse_mode='Markdown')
        except KnowledgeBase.DoesNotExist:
            await update.message.reply_text("❌ Base não encontrada ou você não tem acesso.")
        except ValueError:
            await update.message.reply_text("❌ ID inválido.")

    async def chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from core_api.models import Member, ChatSession
        from core_api.services import ChatService
        from asgiref.sync import sync_to_async

        telegram_id = update.effective_user.id
        try:
            member = await sync_to_async(lambda: Member.objects.select_related('user', 'organization').get(telegram_id=telegram_id))()
        except Member.DoesNotExist:
            await update.message.reply_text("❌ Você precisa vincular sua conta primeiro. Use /vincular <token>")
            return
        except Exception as e:
            traceback.print_exc()
            await update.message.reply_text(f"⚠️ Erro ao encontrar sua conta: {str(e)}")
            return

        active_kb_id = context.user_data.get('active_kb_id')
        if not active_kb_id:
            await update.message.reply_text("⚠️ Nenhuma Base de Conhecimento selecionada.\nUse o comando /base para escolher uma antes de conversar.")
            return

        try:
            from core_api.models import KnowledgeBase
            kb = await sync_to_async(KnowledgeBase.objects.get)(id=active_kb_id)
        except Exception:
            await update.message.reply_text("❌ Base de conhecimento inválida.")
            return

        # Feedback imediato
        processing_msg = await update.message.reply_text("Processando sua pergunta... ⏳")

        try:
            session, _ = await sync_to_async(ChatSession.objects.get_or_create)(
                user=member.user,
                knowledge_base=kb,
                title=f"Telegram Chat ({kb.name})"
            )

            service = ChatService()
            bot_msg = await sync_to_async(service.generate_response)(session.id, update.message.text)
            
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
            
            from telegram.constants import ParseMode
            await update.message.reply_text(bot_msg.content, parse_mode=ParseMode.HTML)
        except Exception as e:
            traceback.print_exc()
            await update.message.reply_text(f"💀 Erro ao processar sua pergunta: {str(e)}")

    async def handle_pdf(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from core_api.models import Member, Document
        from asgiref.sync import sync_to_async
        from django.core.files.base import ContentFile
        import traceback

        print(f"Recebido documento de: {update.effective_user.username}")

        telegram_id = update.effective_user.id
        try:
            member = await sync_to_async(lambda: Member.objects.select_related('user', 'organization').get(telegram_id=telegram_id))()
            if member.role == 'USER':
                await update.message.reply_text("❌ Apenas contribuidores ou administradores podem subir arquivos.")
                return
        except Exception:
            await update.message.reply_text("❌ Você precisa vincular sua conta primeiro. Use /vincular <token>")
            return

        active_kb_id = context.user_data.get('active_kb_id')
        if not active_kb_id:
            await update.message.reply_text("⚠️ Você precisa selecionar uma Base de Conhecimento antes de subir PDFs.\nUse o comando /base")
            return

        try:
            from core_api.models import KnowledgeBase
            kb = await sync_to_async(KnowledgeBase.objects.get)(id=active_kb_id)
        except Exception:
            await update.message.reply_text("❌ Base de conhecimento inválida.")
            return

        doc = update.message.document
        if not doc.file_name.lower().endswith('.pdf'):
            await update.message.reply_text("⚠️ Por favor, envie apenas arquivos no formato PDF.")
            return

        status_msg = await update.message.reply_text(f"📥 Recebendo '{doc.file_name}' para a base {kb.name}... ⏳")

        try:
            doc_file = await doc.get_file()
            # download_as_bytearray pode ser pesado para arquivos grandes, mas para 1MB é ok
            byte_array = await doc_file.download_as_bytearray()
            
            # Salva no Django
            new_doc = await sync_to_async(Document.objects.create)(
                uploader=member.user,
                knowledge_base=kb,
                filename=doc.file_name,
                file=ContentFile(byte_array, name=doc.file_name)
            )
            
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
            await update.message.reply_text(f"✅ PDF '{doc.file_name}' recebido com sucesso!\nO processamento em background foi iniciado.")
            print(f"Documento {new_doc.id} salvo e enviado para fila.")
        except Exception as e:
            traceback.print_exc()
            await update.message.reply_text(f"💀 Erro ao processar o arquivo: {str(e)}")
