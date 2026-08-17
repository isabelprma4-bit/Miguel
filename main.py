import discord
from discord import app_commands
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- DADOS GLOBAIS DE CONFIGURAÇÃO ---
CONFIG = {
    "canal_feedback": 123456789012345678,
    "cargo_suporte": 123456789012345678,
    "pix_key": "sua-chave-pix-aqui",
    "qr_code": "https://link-da-sua-imagem-do-qr.png"
}

AMOLED_COLOR = discord.Color.from_rgb(0, 0, 0)

PRODUTOS = {
    "produto_1": {
        "nome": "Cargo VIP Bronze",
        "preco": "R$ 10,00",
        "desc": "Acesso a canais VIPs e vantagens Bronze.",
        "cargo_id": 123456789012345678,
        "estoque": 5
    }
}

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos Slash.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print(f'Bot online como {bot.user}')

# --- REAÇÃO AUTOMÁTICA DE FEEDBACK ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.id == CONFIG["canal_feedback"]:
        await message.add_reaction("💖")
    
    await bot.process_commands(message)

# --- FORMULÁRIO MODAL PARA /CONFIGURAR ---
class ConfigModal(discord.ui.Modal, title="⚙️ Configuração Geral da Loja"):
    pix = discord.ui.TextInput(
        label="Nova Chave PIX",
        default=CONFIG["pix_key"],
        required=True
    )
    qr = discord.ui.TextInput(
        label="Link da Imagem do QR Code",
        default=CONFIG["qr_code"],
        required=True
    )
    feedback_id = discord.ui.TextInput(
        label="ID do Canal de Feedback",
        default=str(CONFIG["canal_feedback"]),
        required=True
    )
    suporte_id = discord.ui.TextInput(
        label="ID do Cargo da Staff/Suporte",
        default=str(CONFIG["cargo_suporte"]),
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            CONFIG["pix_key"] = self.pix.value
            CONFIG["qr_code"] = self.qr.value
            CONFIG["canal_feedback"] = int(self.feedback_id.value)
            CONFIG["cargo_suporte"] = int(self.suporte_id.value)

            await interaction.response.send_message(
                "✅ Configurações atualizadas com sucesso!", 
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Erro: Certifique-se de inserir IDs numéricos válidos para o canal e cargo.", 
                ephemeral=True
            )

# --- SISTEMA DE COMPRA E TÓPICOS ---
class PainelPagamentoView(discord.ui.View):
    def __init__(self, cliente: discord.Member, prod_key: str):
        super().__init__(timeout=None)
        self.cliente = cliente
        self.prod_key = prod_key

    @discord.ui.button(label="Aprovar Pagamento (Staff)", style=discord.ButtonStyle.success, emoji="✅")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargo_suporte = interaction.guild.get_role(CONFIG["cargo_suporte"])
        
        if cargo_suporte not in interaction.user.roles:
            await interaction.response.send_message("❌ Apenas a equipe de suporte pode aprovar compras!", ephemeral=True)
            return

        produto = PRODUTOS[self.prod_key]

        if produto["estoque"] <= 0:
            await interaction.response.send_message("❌ Produto sem estoque!", ephemeral=True)
            return

        cargo_cliente = interaction.guild.get_role(produto["cargo_id"])
        if cargo_cliente:
            PRODUTOS[self.prod_key]["estoque"] -= 1
            await self.cliente.add_roles(cargo_cliente)
            
            embed_sucesso = discord.Embed(
                title="🎉 Compra Aprovada!",
                description=f"Pagamento aprovado por {interaction.user.mention}.\nCargo {cargo_cliente.mention} entregue a {self.cliente.mention}!\n\n📦 **Estoque restante:** `{PRODUTOS[self.prod_key]['estoque']}`",
                color=AMOLED_COLOR
            )
            await interaction.response.send_message(embed=embed_sucesso)
            
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("❌ Cargo do produto não encontrado no servidor.", ephemeral=True)

    @discord.ui.button(label="Cancelar Pedido", style=discord.ButtonStyle.danger, emoji="✖")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.cliente.id or any(role.id == CONFIG["cargo_suporte"] for role in interaction.user.roles):
            await interaction.response.send_message("🗑️ Cancelando e fechando o tópico...")
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Permissão negada.", ephemeral=True)

class CarrinhoView(discord.ui.View):
    def __init__(self, produto: dict, prod_key: str, cliente: discord.Member):
        super().__init__(timeout=None)
        self.produto = produto
        self.prod_key = prod_key
        self.cliente = cliente

    @discord.ui.button(label="Ir para o Pagamento", style=discord.ButtonStyle.primary, emoji="💳")
    async def pagamento(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_pix = discord.Embed(
            title=f"💳 Pagamento via PIX - {self.produto['nome']}",
            description=f"**Valor:** `{self.produto['preco']}`\n\n**Chave PIX:**\n`{CONFIG['pix_key']}`\n\nAguarde a aprovação da equipe.",
            color=AMOLED_COLOR
        )
        embed_pix.set_image(url=CONFIG["qr_code"])
        embed_pix.set_footer(text="AMOLED Store")

        await interaction.response.send_message(
            embed=embed_pix, 
            view=PainelPagamentoView(cliente=self.cliente, prod_key=self.prod_key)
        )

class LojaSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for key, info in PRODUTOS.items():
            status = f"Estoque: {info['estoque']}" if info['estoque'] > 0 else "SEM ESTOQUE"
            options.append(
                discord.SelectOption(
                    label=f"{info['nome']} ({status})",
                    description=f"{info['preco']} - {info['desc']}",
                    value=key
                )
            )
        super().__init__(placeholder="Selecione o produto...", options=options)

    async def callback(self, interaction: discord.Interaction):
        prod_key = self.values[0]
        produto = PRODUTOS[prod_key]

        if produto["estoque"] <= 0:
            await interaction.response.send_message("❌ Produto esgotado!", ephemeral=True)
            return

        await interaction.response.send_message("🔄 Abrindo carrinho privado...", ephemeral=True)

        topico = await interaction.channel.create_thread(
            name=f"🛒-pedido-{interaction.user.name}",
            type=discord.ChannelType.private_thread
        )

        await topico.add_user(interaction.user)

        embed_carrinho = discord.Embed(
            title="📋 Revisão do Pedido",
            color=AMOLED_COLOR
        )
        embed_carrinho.add_field(name="Produto", value=produto["nome"], inline=False)
        embed_carrinho.add_field(name="Valor", value=produto["preco"], inline=False)
        embed_carrinho.add_field(name="Estoque", value=str(produto["estoque"]), inline=False)

        await topico.send(
            content=f"{interaction.user.mention}, carrinho aberto! Suporte: <@&{CONFIG['cargo_suporte']}>",
            embed=embed_carrinho,
            view=CarrinhoView(produto, prod_key, interaction.user)
        )

class LojaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LojaSelect())

# --- COMANDOS SLASH ---

@bot.tree.command(name="configurar", description="Abre a janela para alterar as configurações do bot")
@app_commands.checks.has_permissions(administrator=True)
async def configurar(interaction: discord.Interaction):
    """Exibe um formulário na tela para o administrador alterar as configurações da loja"""
    await interaction.response.send_modal(ConfigModal())

@bot.tree.command(name="entrar", description="Conecta o bot ao seu canal de voz")
async def entrar(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"🔊 Conectado a **{channel.name}**!")
    else:
        await interaction.response.send_message("❌ Entre em um canal de voz primeiro.", ephemeral=True)

@bot.tree.command(name="painel", description="Envia o painel de compras no canal")
@app_commands.checks.has_permissions(administrator=True)
async def painel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 Loja de Cargos da Comunidade",
        description="Selecione um produto no menu abaixo para abrir seu carrinho de compras.",
        color=AMOLED_COLOR
    )
    await interaction.channel.send(embed=embed, view=LojaView())
    await interaction.response.send_message("✅ Painel enviado com sucesso!", ephemeral=True)

import os

bot.run(os.getenv("TOKEN"))
_zg.oZaClf2E5hDSmvDcJo0set1rfNzGzlU8wrLT_4")
