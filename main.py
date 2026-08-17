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

threading.Thread(target=run_flask, daemon=True).start()

# --- BANCO DE DADOS AUTOMÁTICO ---
DB_NAME = "banco.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT DEFAULT 'TITULO DO PRODUTO',
            descricao TEXT DEFAULT 'Escreva aqui a descrição do produto...',
            valor TEXT DEFAULT '0,00',
            estoque TEXT DEFAULT '∞',
            thumb_url TEXT DEFAULT '',
            banner_url TEXT DEFAULT '',
            texto_botao TEXT DEFAULT 'Comprar',
            emoji_botao TEXT DEFAULT '🛒',
            cor_botao TEXT DEFAULT 'cinza',
            cupom_codigo TEXT DEFAULT 'Nenhum',
            cupom_desconto TEXT DEFAULT '0'
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO produtos (titulo) VALUES ('TITULO DO PRODUTO')")
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

# --- GERADOR DE EMBED CLEAN (FORMATO AMOLED EXATO) ---
def gerar_embed_clean():
    p = get_produto()
    
    desc_formatada = (
        f"**TITULO :** {p[1]}\n\n"
        f"**DESCRIÇÃO :**\n{p[2]}\n\n"
        f"**VALOR :** R$ {p[3]}\n\n"
        f"**ESTOQUE :** {p[4]}"
    )
    
    embed = discord.Embed(
        description=desc_formatada,
        color=0x2b2d31
    )
    
    if p[5]: embed.set_thumbnail(url=p[5])
    if p[6]: embed.set_image(url=p[6])
        
    embed.set_footer(text="AMOLED STORE | Loja Oficial", icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None)
    return embed

# --- GERADOR DE EMBED DE PAINEL INTERNO ---
def gerar_embed_painel():
    p = get_produto()
    embed = discord.Embed(
        title="⚙️ Painel de Edição Amoled",
        description=(
            f"**TITULO :** {p[1]}\n"
            f"**DESCRIÇÃO :** {p[2]}\n"
            f"**VALOR :** R$ {p[3]}\n"
            f"**ESTOQUE :** {p[4]}\n\n"
            f"🎨 **Logo:** {'Sim' if p[5] else 'Não'} | **Banner:** {'Sim' if p[6] else 'Não'}\n"
            f"🔘 **Botão:** {p[8]} {p[7]} ({p[9]})\n"
            f"🎟️ **Cupom:** {p[10]} ({p[11]}%)"
        ),
        color=0x5865F2
    )
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
        await interaction.response.edit_message(embed=gerar_embed_painel(), view=PainelEditorView())

class ModalCupom(discord.ui.Modal, title="Configurar Cupom"):
    codigo = discord.ui.TextInput(label="Código do Cupom", placeholder="Ex: AMOLED10")
    desconto = discord.ui.TextInput(label="Desconto (%)", placeholder="Ex: 10")

    async def on_submit(self, interaction: discord.Interaction):
        update_field("cupom_codigo", self.codigo.value)
        update_field("cupom_desconto", self.desconto.value)
        await interaction.response.edit_message(embed=gerar_embed_painel(), view=PainelEditorView())

class ModalBotaoCompra(discord.ui.Modal, title="Personalizar Botão"):
    texto = discord.ui.TextInput(label="Texto do Botão", placeholder="Ex: Comprar")
    emoji = discord.ui.TextInput(label="Emoji do Botão", placeholder="Ex: 🛒")
    cor = discord.ui.TextInput(label="Cor (cinza, verde, azul, vermelho)", placeholder="Ex: cinza")

    async def on_submit(self, interaction: discord.Interaction):
        update_field("texto_botao", self.texto.value)
        update_field("emoji_botao", self.emoji.value)
        update_field("cor_botao", self.cor.value.lower())
        await interaction.response.edit_message(embed=gerar_embed_painel(), view=PainelEditorView())

# --- VIEW EDITOR (TODOS OS BOTÕES DE CONFIGURAÇÃO) ---
class PainelEditorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Título", style=discord.ButtonStyle.secondary, emoji="📝", row=0)
    async def alt_nome(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Título", "Novo Título", "titulo"))

    @discord.ui.button(label="Descrição", style=discord.ButtonStyle.secondary, emoji="📄", row=0)
    async def alt_desc(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Descrição", "Descrição do Produto", "descricao", paragrafo=True))

    @discord.ui.button(label="Valor", style=discord.ButtonStyle.secondary, emoji="💵", row=0)
    async def alt_valor(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Valor", "Ex: 2,99", "valor"))

    @discord.ui.button(label="Estoque", style=discord.ButtonStyle.secondary, emoji="🛒", row=0)
    async def alt_est(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Estoque", "Quantidade ou '∞'", "estoque"))

    @discord.ui.button(label="Logo", style=discord.ButtonStyle.primary, emoji="🖼️", row=1)
    async def alt_thumb(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Logo", "URL da Imagem", "thumb_url"))

    @discord.ui.button(label="Banner", style=discord.ButtonStyle.primary, emoji="🎨", row=1)
    async def alt_banner(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Banner", "URL da Imagem", "banner_url"))

    @discord.ui.button(label="Cupom", style=discord.ButtonStyle.success, emoji="🎟️", row=1)
    async def alt_cupom(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalCupom())

    @discord.ui.button(label="Botão Compra", style=discord.ButtonStyle.success, emoji="⚙️", row=1)
    async def alt_btn(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalBotaoCompra())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.danger, emoji="⬅️", row=2)
    async def voltar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content="**Painel Geral Amoled:**", embed=None, view=PainelGeralView())

# --- VIEW CLIENTE (LOJA FINAL) ---
class PainelClienteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        p = get_produto()
        
        cores = {
            "cinza": discord.ButtonStyle.secondary,
            "verde": discord.ButtonStyle.success,
            "azul": discord.ButtonStyle.primary,
            "vermelho": discord.ButtonStyle.danger
        }
        estilo = cores.get(p[9], discord.ButtonStyle.secondary)

        btn_compra = discord.ui.Button(label=p[7], emoji=p[8], style=estilo)
        btn_compra.callback = self.comprar_callback
        self.add_item(btn_compra)

    async def comprar_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🛒 Abrindo seu carrinho de compras...", ephemeral=True)

# --- VIEW PRINCIPAL ---
class PainelGeralView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Editar Produto", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=gerar_embed_painel(), view=PainelEditorView())

    @discord.ui.button(label="Postar Anúncio Amoled", style=discord.ButtonStyle.success, emoji="🚀")
    async def postar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.channel.send(embed=gerar_embed_clean(), view=PainelClienteView())
        await interaction.response.send_message("✅ Anúncio Amoled postado com sucesso!", ephemeral=True)

# --- COMANDO ÚNICO ---
@bot.tree.command(name="painel", description="Abre o painel Amoled de controle")
async def painel(interaction: discord.Interaction):
    await interaction.response.send_message("**Painel Geral Amoled:**", view=PainelGeralView(), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot {bot.user} online e atualizado!")

bot.run(os.environ.get("TOKEN"))
