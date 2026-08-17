import discord
from discord.ext import commands
import sqlite3
import os
import threading
from flask import Flask

# --- KEEP ALIVE (FLASK PARA O RENDER) ---
app = Flask(__name__)
@app.route('/')
def home(): return "Bot Online 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask).start()

# --- BANCO DE DADOS (AUTOMÁTICO) ---
DB_NAME = "banco.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT DEFAULT 'Conta Nitrada',
            descricao TEXT DEFAULT 'Sem nenhuma descrição',
            preco_de TEXT DEFAULT '0.00',
            preco_para TEXT DEFAULT '2.25',
            estoque TEXT DEFAULT '0',
            cargo_id TEXT DEFAULT '@Cliente',
            expira TEXT DEFAULT '∞ dias',
            thumb_url TEXT DEFAULT '',
            banner_url TEXT DEFAULT '',
            texto_botao TEXT DEFAULT 'Comprar',
            emoji_botao TEXT DEFAULT '🛒',
            cor_botao TEXT DEFAULT 'verde',
            cupom_codigo TEXT DEFAULT 'Nenhum',
            cupom_desconto TEXT DEFAULT '0'
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO produtos (titulo) VALUES ('Conta Nitrada')")
    conn.commit()
    conn.close()

init_db()

def get_produto():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row

def update_field(field, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE produtos SET {field} = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()

# --- BOT CONFIG ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- GERADOR DE EMBED ---
def gerar_embed():
    p = get_produto()
    embed = discord.Embed(
        title=p[1],
        description=f"```{p[2]}```\n\n"
                    f"⛔ | **Preço de:**\n{p[3]}\n\n"
                    f"💵 | **Preço para:**\n{p[4]}\n\n"
                    f"🛒 | **Estoque:**\n{p[5]}\n\n"
                    f"🛂 | **Você receberá o cargo:**\n{p[6]}\n\n"
                    f"📅 | **Expira em:**\n{p[7]}\n\n"
                    f"🎟️ | **Cupom Ativo:** {p[13]} ({p[14]}% OFF)",
        color=0xFF5500
    )
    if p[8]: embed.set_thumbnail(url=p[8])
    if p[9]: embed.set_image(url=p[9])
    embed.set_footer(text="Powered by: Sua Loja")
    return embed

# --- MODAIS ---
class ModalTexto(discord.ui.Modal):
    def __init__(self, titulo_modal, campo_label, campo_bd, paragrafo=False):
        super().__init__(title=titulo_modal)
        self.campo_bd = campo_bd
        style = discord.TextStyle.paragraph if paragrafo else discord.TextStyle.short
        self.input = discord.ui.TextInput(label=campo_label, style=style, required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        update_field(self.campo_bd, self.input.value)
        await interaction.response.edit_message(embed=gerar_embed(), view=PainelEditorView())

class ModalCupom(discord.ui.Modal, title="Configurar Cupom"):
    codigo = discord.ui.TextInput(label="Código do Cupom", placeholder="Ex: NATAL10")
    desconto = discord.ui.TextInput(label="Desconto (%)", placeholder="Ex: 10")

    async def on_submit(self, interaction: discord.Interaction):
        update_field("cupom_codigo", self.codigo.value)
        update_field("cupom_desconto", self.desconto.value)
        await interaction.response.edit_message(embed=gerar_embed(), view=PainelEditorView())

class ModalBotaoCompra(discord.ui.Modal, title="Personalizar Botão"):
    texto = discord.ui.TextInput(label="Texto do Botão", placeholder="Ex: Comprar Agora")
    emoji = discord.ui.TextInput(label="Emoji do Botão", placeholder="Ex: 🛒")
    cor = discord.ui.TextInput(label="Cor (verde, azul, cinza, vermelho)", placeholder="Ex: verde")

    async def on_submit(self, interaction: discord.Interaction):
        update_field("texto_botao", self.texto.value)
        update_field("emoji_botao", self.emoji.value)
        update_field("cor_botao", self.cor.value.lower())
        await interaction.response.edit_message(embed=gerar_embed(), view=PainelEditorView())

# --- VIEW EDITOR (TODOS OS BOTÕES DE CONFIGURAÇÃO) ---
class PainelEditorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Nome", style=discord.ButtonStyle.secondary, emoji="📝", row=0)
    async def alt_nome(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Nome", "Novo Nome", "titulo"))

    @discord.ui.button(label="Descrição", style=discord.ButtonStyle.secondary, emoji="📄", row=0)
    async def alt_desc(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Descrição", "Nova Descrição", "descricao", paragrafo=True))

    @discord.ui.button(label="Logo", style=discord.ButtonStyle.primary, emoji="🖼️", row=0)
    async def alt_thumb(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Logo", "URL da Imagem", "thumb_url"))

    @discord.ui.button(label="Banner", style=discord.ButtonStyle.primary, emoji="🎨", row=0)
    async def alt_banner(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Banner", "URL da Imagem", "banner_url"))

    @discord.ui.button(label="Preço DE", style=discord.ButtonStyle.secondary, emoji="⛔", row=1)
    async def alt_pde(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Preço Antigo", "Ex: 10.00", "preco_de"))

    @discord.ui.button(label="Preço PARA", style=discord.ButtonStyle.secondary, emoji="💵", row=1)
    async def alt_ppara(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Preço Atual", "Ex: 2.25", "preco_para"))

    @discord.ui.button(label="Estoque", style=discord.ButtonStyle.secondary, emoji="🛒", row=1)
    async def alt_est(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Estoque", "Quantidade ou 'Infinito'", "estoque"))

    @discord.ui.button(label="Cupom", style=discord.ButtonStyle.success, emoji="🎟️", row=2)
    async def alt_cupom(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalCupom())

    @discord.ui.button(label="Botão Compra", style=discord.ButtonStyle.success, emoji="⚙️", row=2)
    async def alt_btn(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalBotaoCompra())

    @discord.ui.button(label="Voltar ao Menu", style=discord.ButtonStyle.danger, emoji="⬅️", row=2)
    async def voltar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content="**Painel Geral de Controle:**", embed=None, view=PainelGeralView())

# --- VIEW CLIENTE (LOJA FINAL) ---
class PainelClienteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        p = get_produto()
        
        cores = {
            "verde": discord.ButtonStyle.success,
            "azul": discord.ButtonStyle.primary,
            "cinza": discord.ButtonStyle.secondary,
            "vermelho": discord.ButtonStyle.danger
        }
        estilo = cores.get(p[12], discord.ButtonStyle.success)

        btn_compra = discord.ui.Button(label=p[10], emoji=p[11], style=estilo)
        btn_compra.callback = self.comprar_callback
        self.add_item(btn_compra)

    async def comprar_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🛒 Processando sua compra...", ephemeral=True)

# --- VIEW PRINCIPAL DO COMANDO /PAINEL ---
class PainelGeralView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Editar Produto", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=gerar_embed(), view=PainelEditorView())

    @discord.ui.button(label="Postar Anúncio na Loja", style=discord.ButtonStyle.success, emoji="🚀")
    async def postar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.channel.send(embed=gerar_embed(), view=PainelClienteView())
        await interaction.response.send_message("✅ Anúncio enviado com sucesso neste canal!", ephemeral=True)

# --- UNICO COMANDO ---
@bot.tree.command(name="painel", description="Abre o painel central da loja")
async def painel(interaction: discord.Interaction):
    await interaction.response.send_message("**Painel Geral de Controle:**", view=PainelGeralView(), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot {bot.user} pronto!")

bot.run(os.environ.get("TOKEN"))
