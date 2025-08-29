import os
import math
import logging
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Modal, TextInput
from dotenv import load_dotenv

# --- Optional: your keep-alive server for hosting ---
import webserver

# ---------- Load env ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")           # your bot token
GUILD_ID = int(os.getenv("GUILD_ID", "0"))   # optional: speeds up slash command updates during dev

# ---------- Logging ----------
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# ---------- Intents ----------
intents = discord.Intents.default()
# Needed for your existing prefix commands that check author roles, etc.
intents.message_content = True    # Make sure this is enabled in the Dev Portal if prefix cmds don't respond
intents.members = True

# ---------- Bot ----------
bot = commands.Bot(command_prefix='!', intents=intents)

# ---------- Your existing settings ----------
secret_role = "Gay"

# =========================
#   MATH MENU (Slash)
#   Derivative / Integral / Euler (ZYX)
# =========================

# SymPy bits (safe parsing)
from sympy import symbols, Matrix, sin, cos, tan, asin, acos, atan, exp, log, sqrt, pi, E, integrate
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)

x, y = symbols("x y")

ALLOWED = {
    # variables/constants
    "x": x, "y": y, "pi": pi, "E": E,
    # funcs
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan,
    "exp": exp, "log": log, "sqrt": sqrt,
    "abs": abs
}
TRANSFORMS = (standard_transformations + (implicit_multiplication_application, convert_xor))

def parse_safe(expr_str: str):
    return parse_expr(expr_str, local_dict=ALLOWED, transformations=TRANSFORMS, evaluate=True)

# ----- Modals -----
class DerivativeModal(Modal, title="Derivative"):
    expr = TextInput(label="f(x, y)", placeholder="e.g. x^2*sin(y) + 3*x", required=True)
    var  = TextInput(label="Differentiate w.r.t.", placeholder="x or y", required=True, max_length=1)
    order = TextInput(label="Order (default 1)", placeholder="1", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            f = parse_safe(str(self.expr))
            var_name = str(self.var).strip()
            if var_name not in ("x", "y"):
                raise ValueError("Variable must be x or y.")
            n = int(str(self.order).strip() or "1")
            var_sym = x if var_name == "x" else y
            df = f.diff(var_sym, n)
            await interaction.response.send_message(
                f"**∂^{n} f / ∂{var_name}^{n}**\n```text\n{df}\n```",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

class IntegralModal(Modal, title="Integral"):
    expr = TextInput(label="f(x, y)", placeholder="e.g. x^2 + y", required=True)
    var  = TextInput(label="Integrate w.r.t.", placeholder="x or y", required=True, max_length=1)
    lower = TextInput(label="Lower limit (optional)", placeholder="e.g. 0", required=False)
    upper = TextInput(label="Upper limit (optional)", placeholder="e.g. 1", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            f = parse_safe(str(self.expr))
            var_name = str(self.var).strip()
            if var_name not in ("x", "y"):
                raise ValueError("Variable must be x or y.")
            var_sym = x if var_name == "x" else y

            lo = str(self.lower).strip()
            hi = str(self.upper).strip()

            if lo and hi:
                a = parse_safe(lo)
                b = parse_safe(hi)
                val = integrate(f, (var_sym, a, b))
                msg = f"**∫_{lo}^{hi} f d{var_name}**\n```text\n{val}\n```"
            else:
                F = integrate(f, var_sym)
                msg = f"**∫ f d{var_name} (indefinite)**\n```text\n{F}\n```"

            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

class EulerModal(Modal, title="Euler Z-Y-X (yaw-pitch-roll)"):
    phi   = TextInput(label="φ (roll, degrees)", placeholder="e.g. 10", required=True)
    theta = TextInput(label="θ (pitch, degrees)", placeholder="e.g. -5", required=True)
    psi   = TextInput(label="ψ (yaw, degrees)", placeholder="e.g. 30", required=True)

    def rot_x(self, a):
        return Matrix([[1, 0, 0],
                       [0, cos(a), -sin(a)],
                       [0, sin(a),  cos(a)]])

    def rot_y(self, b):
        return Matrix([[ cos(b), 0, sin(b)],
                       [ 0,      1, 0     ],
                       [-sin(b), 0, cos(b)]])

    def rot_z(self, c):
        return Matrix([[cos(c), -sin(c), 0],
                       [sin(c),  cos(c), 0],
                       [0,       0,      1]])

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from sympy import N
            φ = math.radians(float(str(self.phi).strip()))
            θ = math.radians(float(str(self.theta).strip()))
            ψ = math.radians(float(str(self.psi).strip()))
            R = self.rot_z(ψ) * self.rot_y(θ) * self.rot_x(φ)  # ZYX
            Rn = N(R, 6)
            rows = ["[" + ", ".join(f"{float(val): .6f}" for val in Rn.row(i)) + "]" for i in range(3)]
            txt = "\n".join(rows)
            await interaction.response.send_message(
                "**Rotation matrix (ZYX / yaw-pitch-roll, degrees input)**\n"
                f"φ={self.phi}°, θ={self.theta}°, ψ={self.psi}°\n"
                f"```text\n{txt}\n```",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)

# ----- Dropdown View -----
class MathSelect(Select):
    def __init__(self, options, user_id: int):
        super().__init__(placeholder="Choose a calculator…", options=options, min_values=1, max_values=1)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This menu isn't for you 😅", ephemeral=True)
            return
        choice = self.values[0]
        if choice == "derivative":
            await interaction.response.send_modal(DerivativeModal())
        elif choice == "integral":
            await interaction.response.send_modal(IntegralModal())
        elif choice == "euler":
            await interaction.response.send_modal(EulerModal())
        else:
            await interaction.response.send_message("Unknown option.", ephemeral=True)

class MathMenu(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        options = [
            discord.SelectOption(label="Derivative", value="derivative", description="Compute ∂/∂x or ∂/∂y"),
            discord.SelectOption(label="Integral", value="integral", description="Definite or indefinite"),
            discord.SelectOption(label="Euler Matrix (ZYX)", value="euler", description="3×3 rotation matrix"),
        ]
        self.add_item(MathSelect(options, user_id))

# ----- Slash command -----
@bot.tree.command(name="math", description="Open the math menu (derivative, integral, Euler matrix).")
async def math_menu(interaction: discord.Interaction):
    view = MathMenu(user_id=interaction.user.id)
    await interaction.response.send_message(
        "Pick a calculator from the dropdown below:",
        view=view,
        ephemeral=True
    )

# =========================
#   Your existing prefix commands
# =========================
@bot.event
async def on_ready():
    # Sync slash commands (guild-scoped if GUILD_ID set for instant updates)
    try:
        if GUILD_ID:
            await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
            print(f"[slash] Synced to guild {GUILD_ID}")
        else:
            await bot.tree.sync()
            print("[slash] Synced globally (can take a bit to appear).")
    except Exception as e:
        print(f"[slash] Sync failed: {e}")
    print(f'We have logged in as {bot.user.name}')

@bot.command()
async def logout(ctx):
    await ctx.send("Logging out!")
    await bot.close()

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.mention}!')

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secret_role)
    if role:
        if role in ctx.author.roles:
            await ctx.send(f'You already have the role {secret_role}, {ctx.author.mention}!')
            return
        try:
            await ctx.author.add_roles(role, reason="Self-assign command")
            await ctx.send(f'Role {secret_role} has been assigned to {ctx.author.mention}')
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage roles. Please move my role higher.")
    else:
        await ctx.send('Role does not exist.')

@bot.command()
async def remove(ctx):
    role = discord.utils.get(ctx.guild.roles, name=secret_role)
    if role and role in ctx.author.roles:
        try:
            await ctx.author.remove_roles(role, reason="Self-remove command")
            await ctx.send(f'Role {secret_role} has been removed from {ctx.author.mention}')
        except discord.Forbidden:
            await ctx.send("I don't have permission to manage roles. Please move my role higher.")
    else:
        await ctx.send("You don't have that role.")

# ---------- Keep-alive + run ----------
webserver.keep_alive()
bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
