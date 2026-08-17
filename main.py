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
            titulo TEXT DEFAULT 'YT PR3M1UM',
            destaque TEXT DEFAULT '⚡ Entrega Automática!',
            descricao TEXT DEFAULT '• Youtube premium na sua conta\n• Não precisa ativar nada ( so apertar e usar)\n• Oficial do youtube nada pirata\n• Entrega automática\n• garantia apenas com feedback + print',
            valor TEXT DEFAULT '3,99',
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
        cursor.execute("INSERT INTO produtos (titulo) VALUES ('YT PR3M1UM')")
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

# --- EMBED FINAL DA LOJA ---
def gerar_embed_clean():
    p = get_produto()
    
    # Montagem exata da estrutura da foto
    corpo = ""
    if p[2]:  # Destaque (ex: Entrega Automática)
        corpo += f"{p[2]}\n\n"
        
    corpo += f"{p[3]}\n\n"
    corpo += f"**Valor à vista**\n```R$ {p[4]}```\n"
    corpo += f"**Restam**\n``` {p[5]} ```"
    
    embed = discord.Embed(
        title=p[1],
        description=corpo,
        color=0x2b2d31
    )
    
    if p[6]: embed.set_thumbnail(url=p[6])
    if p[7]: embed.set_image(url=p[7])
        
    embed.set_footer(
        text="AMOLED STORE | Loja Oficial", 
        icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None
    )
    return embed

# --- EMBED DO PAINEL DE EDIÇÃO INTERNO ---
def gerar_embed_painel():
    p = get_produto()
    embed = discord.Embed(
        title="⚙️ Painel de Configuração Amoled",
        description=(
            f"**Título:** {p[1]}\n"
            f"**Destaque:** {p[2]}\n\n"
            f"**Descrição:**\n{p[3]}\n\n"
            f"**Valor:** R$ {p[4]} | **Estoque:** {p[5]}\n"
            f"🎨 **Logo:** {'Sim' if p[6] else 'Não'} | **Banner:** {'Sim' if p[7] else 'Não'}\n"
            f"🔘 **Botão:** {p[9]} {p[8]} ({p[10]}) | 🎟️ **Cupom:** {p[11]} ({p[12]}%)"
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

# --- BOTOES DO EDITOR ---
class PainelEditorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Título", style=discord.ButtonStyle.secondary, emoji="📝", row=0)
    async def alt_nome(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Título", "Ex: YT PR3M1UM", "titulo"))

    @discord.ui.button(label="Destaque", style=discord.ButtonStyle.secondary, emoji="⚡", row=0)
    async def alt_destaque(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Texto em Destaque", "Ex: ⚡ Entrega Automática!", "destaque"))

    @discord.ui.button(label="Descrição", style=discord.ButtonStyle.secondary, emoji="📄", row=0)
    async def alt_desc(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Descrição", "Tópicos com •", "descricao", paragrafo=True))

    @discord.ui.button(label="Valor", style=discord.ButtonStyle.secondary, emoji="💵", row=1)
    async def alt_valor(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Valor", "Ex: 3,99", "valor"))

    @discord.ui.button(label="Estoque", style=discord.ButtonStyle.secondary, emoji="🛒", row=1)
    async def alt_est(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("Alterar Estoque", "Quantidade ou ∞", "estoque"))

    @discord.ui.button(label="Logo", style=discord.ButtonStyle.primary, emoji="🖼️", row=1)
    async def alt_thumb(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("URL da Logo", "Cole o link da imagem", "thumb_url"))

    @discord.ui.button(label="Banner", style=discord.ButtonStyle.primary, emoji="🎨", row=1)
    async def alt_banner(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalTexto("URL do Banner", "Cole o link do banner", "banner_url"))

    @discord.ui.button(label="Cupom", style=discord.ButtonStyle.success, emoji="🎟️", row=2)
    async def alt_cupom(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalCupom())

    @discord.ui.button(label="Botão Compra", style=discord.ButtonStyle.success, emoji="⚙️", row=2)
    async def alt_btn(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.send_modal(ModalBotaoCompra())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.danger, emoji="⬅️", row=2)
    async def voltar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content="**Painel Geral Amoled:**", embed=None, view=PainelGeralView())

# --- CLIENTE VIEW ---
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
        estilo = cores.get(p[10], discord.ButtonStyle.secondary)

        btn_compra = discord.ui.Button(label=p[8], emoji=p[9], style=estilo)
        btn_compra.callback = self.comprar_callback
        self.add_item(btn_compra)

    async def comprar_callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("🛒 Abrindo seu carrinho de compras...", ephemeral=True)

# --- PAINEL PRINCIPAL ---
class PainelGeralView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Editar Produto", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def editar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=gerar_embed_painel(), view=PainelEditorView())

    @discord.ui.button(label="Postar Anúncio", style=discord.ButtonStyle.success, emoji="🚀")
    async def postar(self, interaction: discord.Interaction, b: discord.ui.Button):
        await interaction.channel.send(embed=gerar_embed_clean(), view=PainelClienteView())
        await interaction.response.send_message("✅ Anúncio postado no canal!", ephemeral=True)

@bot.tree.command(name="painel", description="Abre o painel Amoled")
async def painel(interaction: discord.Interaction):
    await interaction.response.send_message("**Painel Geral Amoled:**", view=PainelGeralView(), ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot {bot.user} pronto!")

bot.run(os.environ.get("TOKEN"))
