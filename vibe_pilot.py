import discord
from discord.ext import commands
from discord import ui
import os
import subprocess
import asyncio
import io
import json
import re
import shutil
from dotenv import load_dotenv
from openai import OpenAI

# Utility functions for the Vibe Pilot Brain

def read_file(relative_path: str) -> str:
    """Read the content of a file relative to BASE_DIR.
    Returns the file content as a string, or an empty string if the file does not exist.
    """
    file_path = os.path.abspath(os.path.join(BASE_DIR, relative_path))
    # Sécurité : vérifier que le fichier est bien dans BASE_DIR
    if not file_path.startswith(os.path.abspath(BASE_DIR)):
        return "Erreur de sécurité : Accès interdit en dehors du projet."
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Erreur : Fichier introuvable."
    except UnicodeDecodeError:
        return "Erreur : Ce fichier est binaire et ne peut pas être lu sous forme de texte."

def write_file(relative_path: str, content: str) -> str:
    """Write content to a file relative to BASE_DIR and backup the old version."""
    file_path = os.path.abspath(os.path.join(BASE_DIR, relative_path))
    # Sécurité : vérifier que le fichier est bien dans BASE_DIR
    if not file_path.startswith(os.path.abspath(BASE_DIR)):
        return "Erreur de sécurité : Accès interdit en dehors du projet."
        
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Création d'un backup automatique
    if os.path.exists(file_path):
        backup_dir = os.path.join(BASE_DIR, ".vibe_backups")
        os.makedirs(backup_dir, exist_ok=True)
        # On remplace les / par des _ pour avoir un fichier à plat
        safe_name = relative_path.replace("/", "_") + ".bak"
        backup_path = os.path.join(backup_dir, safe_name)
        shutil.copy2(file_path, backup_path)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Fichier {relative_path} écrit avec succès (backup créé dans .vibe_backups)."

def get_project_tree(relative_path: str = "") -> str:
    """Retourne l'arborescence du dossier sous forme de texte (profondeur max 2)."""
    abs_path = os.path.abspath(os.path.join(BASE_DIR, relative_path))
    if not abs_path.startswith(os.path.abspath(BASE_DIR)):
        return "Erreur de sécurité : Accès interdit en dehors du projet."
        
    if not os.path.exists(abs_path):
        return f"Erreur: Dossier '{relative_path}' introuvable."
    
    tree_str = []
    start_level = abs_path.rstrip(os.path.sep).count(os.path.sep)
    
    for root, dirs, files in os.walk(abs_path):
        # Exclure les dossiers lourds ou non pertinents
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'env']]
        
        level = root.count(os.path.sep) - start_level
        if level > 2:
            continue
            
        indent = '  ' * level
        folder_name = os.path.basename(root) if root != abs_path else (relative_path or "Racine")
        tree_str.append(f"{indent}📂 {folder_name}/")
        
        sub_indent = '  ' * (level + 1)
        for f in sorted(files):
            if not f.startswith('.'):
                tree_str.append(f"{sub_indent}📄 {f}")
                
    return "\n".join(tree_str)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit le contenu d'un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin relatif du fichier"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Affiche l'arborescence d'un dossier pour l'explorer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin relatif du dossier (laisser vide '' pour la racine)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Écrit du contenu dans un fichier. Remplace le fichier s'il existe.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin relatif du fichier"},
                    "content": {"type": "string", "description": "Contenu complet à écrire"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exec_shell",
            "description": "Exécute une commande shell et retourne la sortie.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Commande bash à exécuter"}
                },
                "required": ["command"]
            }
        }
    }
]

def get_initial_timeout(command: str) -> int:
    """Détermine un timeout initial basé sur la commande."""
    cmd = command.lower()
    if any(k in cmd for k in ["install", "npm", "pip", "build", "setup"]):
        return 120
    if any(k in cmd for k in ["test", "pytest", "jest", "cypress"]):
        return 60
    return 20

class ContinueView(ui.View):
    """Vue Discord pour demander si on continue l'exécution."""
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @ui.button(label="Continuer (30s)", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "continue"
        self.stop()
        await interaction.response.send_message("On continue...", ephemeral=True)

    @ui.button(label="Arrêter", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "stop"
        self.stop()
        await interaction.response.send_message("Arrêt de la commande.", ephemeral=True)

class AgentContinueView(ui.View):
    """Vue Discord pour demander si l'agent peut continuer ses actions."""
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.value = None

    @ui.button(label="Autoriser +15 actions", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "continue"
        self.stop()
        await interaction.response.send_message("L'agent repart pour un tour !", ephemeral=True)

    @ui.button(label="Arrêter l'agent", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = "stop"
        self.stop()
        await interaction.response.send_message("L'agent a été stoppé.", ephemeral=True)

async def exec_shell_interactive(ctx, command: str) -> str:
    """Exécute une commande shell de manière asynchrone avec timeout adaptatif et interaction."""
    timeout = get_initial_timeout(command)
    
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=BASE_DIR
    )
    
    output_log = []
    
    async def read_stream(stream):
        while True:
            line = await stream.readline()
            if line:
                output_log.append(line.decode())
                if len(output_log) > 1000: # On garde les 1000 dernières lignes en mémoire
                    output_log.pop(0)
            else:
                break

    # On lance la lecture des flux en arrière-plan
    stdout_task = asyncio.create_task(read_stream(process.stdout))
    stderr_task = asyncio.create_task(read_stream(process.stderr))
    
    while True:
        try:
            # On attend que le processus se termine ou que le timeout soit atteint
            await asyncio.wait_for(process.wait(), timeout=timeout)
            break
        except asyncio.TimeoutExpired:
            # Timeout atteint : on demande à l'utilisateur
            last_output = "".join(output_log[-15:]) # 15 dernières lignes pour le contexte rapide
            full_history = "".join(output_log)
            view = ContinueView()
            
            prompt = f"⏳ **Timeout ({timeout}s)** atteint pour :\n`{command}`\n\n**Aperçu (15 dernières lignes) :**\n```\n{last_output or 'Pas encore de sortie...'}\n```\nEst-ce qu'on continue ?"
            
            # Si on a beaucoup de log, on envoie le tout dans un fichier pour que l'utilisateur puisse fouiller
            file = None
            if len(output_log) > 15:
                file = discord.File(io.BytesIO(full_history.encode()), filename="full_output.txt")
            
            msg = await ctx.send(content=prompt, file=file, view=view)
            
            await view.wait()
            if view.value == "continue":
                timeout = 30 # On repart pour 30s
                await msg.edit(view=None) # On enlève les boutons
                continue
            else:
                process.terminate()
                output_log.append("\n[ARRÊTÉ PAR L'UTILISATEUR]")
                await msg.edit(view=None)
                break

    await stdout_task
    await stderr_task
    
    return "".join(output_log).strip()

def format_console_output(title: str, output: str, lang: str = "") -> str:
    """Formatte le texte pour Discord avec des blocs de code et gère la limite de caractères."""
    max_len = 1900 - len(title) - len(lang)
    if len(output) > max_len:
        output = output[:max_len] + "\n... [TRONQUÉ]"
    if not output.strip():
        output = "Aucun retour de la console."
    return f"{title}\n```{lang}\n{output}\n```"


load_dotenv()

# Configuration
BASE_DIR = os.path.expanduser("~/projects")
client_ds = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

AGENT_SYSTEM_PROMPT = """Tu es un Agent de Vibe Coding autonome et expert.
Tu as accès à des outils pour lire des fichiers, écrire des fichiers, et exécuter des commandes shell (avec bash).
Utilise ces outils pour accomplir la mission confiée par l'utilisateur.
- Explore l'environnement si nécessaire (ex: ls, find).
- Lis les fichiers pertinents avant de les modifier.
- Si tu modifies du code, tu DOIS le tester avec exec_shell.
- Ne demande pas la permission pour utiliser un outil.

⚠️ IMPORTANT POUR L'ÉCRITURE DE FICHIERS :
L'outil `write_file` (JSON) peut bugger sur des fichiers très longs. Privilégie CETTE SYNTAXE directement dans ton message texte pour écrire ou modifier un fichier complet :

FILE: chemin/relatif/vers/fichier.py
```python
# ton code complet ici
```

Tu peux inclure plusieurs blocs FILE: dans un seul message pour modifier plusieurs fichiers d'un coup.
Quand tu as terminé la mission ou que tu as besoin d'une décision humaine, réponds directement sans utiliser d'outil pour faire ton rapport."""

conversation_history = {}

@bot.event
async def on_ready():
    print(f"✅ Cerveau connecté : {bot.user}")

@bot.command()
async def reset(ctx):
    """Efface la mémoire de l'agent pour ce channel."""
    if ctx.channel.id in conversation_history:
        del conversation_history[ctx.channel.id]
        await ctx.send("🧹 **Mémoire effacée**. L'agent repart à zéro pour ce channel.")
    else:
        await ctx.send("🧹 **La mémoire est déjà vide** pour ce channel.")

@bot.command()
async def vibe(ctx, *, instructions: str):
    await ctx.send("🤖 **Agent activé**. Analyse de l'environnement et lancement...")
    
    channel_id = ctx.channel.id
    if channel_id not in conversation_history:
        # Initialisation avec l'arborescence
        initial_tree = get_project_tree("")
        context_msg = f"Voici l'arborescence actuelle du projet (fichiers pertinents) :\n```text\n{initial_tree}\n```"
        conversation_history[channel_id] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": context_msg}
        ]
        
    messages = conversation_history[channel_id]
    messages.append({"role": "user", "content": instructions})
    
    max_steps = 15
    step = 0
    
    try:
        while True:
            if step >= max_steps:
                view = AgentContinueView()
                msg = await ctx.send(f"⚠️ **Limite de {max_steps} actions atteinte**. L'agent a encore besoin de réfléchir. L'autorises-tu à continuer ?", view=view)
                await view.wait()
                if view.value == "continue":
                    max_steps += 15
                    await msg.edit(view=None)
                else:
                    await ctx.send("🛑 **Agent stoppé par l'utilisateur**.")
                    await msg.edit(view=None)
                    break

            step += 1
            
            response = client_ds.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            messages.append(message)
            
            # Interception des blocs texte FILE: pour la modification multi-fichiers
            if message.content:
                file_pattern = re.compile(r"(?:^|\n)(?:📝\s*)?FILE:\s*([^\n]+)\n```[a-zA-Z0-9_]*\n(.*?)```", re.DOTALL)
                matches = file_pattern.findall(message.content)
                for path, code in matches:
                    path = path.strip()
                    write_file(path, code.strip())
                    await ctx.send(f"📝 **Fichier mis à jour (via bloc texte)** : `{path}`")
            
            if not message.tool_calls:
                # Fin de la boucle, l'agent répond à l'utilisateur
                if message.content:
                    content = message.content[:1900] + "..." if len(message.content) > 1900 else message.content
                    await ctx.send(f"✅ **Bilan de l'Agent** :\n{content}")
                else:
                    await ctx.send("✅ **Mission terminée** (pas de message final).")
                break
                
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    # On informe l'IA de son erreur de formatage pour qu'elle corrige
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": "Erreur interne: JSON invalide fourni dans les arguments. Réessaie ou utilise les blocs texte FILE:."
                    })
                    continue
                
                # Masquer le contenu complet s'il est trop long pour l'affichage Discord
                display_args = str(args)
                if len(display_args) > 100:
                    display_args = display_args[:100] + "...}"
                    
                await ctx.send(f"🛠️ **Action [{step}/{max_steps}]** : `{func_name}` avec `{display_args}`")
                
                result = ""
                if func_name == "read_file":
                    result = read_file(args.get("path"))
                elif func_name == "write_file":
                    result = write_file(args.get("path"), args.get("content"))
                elif func_name == "list_directory":
                    result = get_project_tree(args.get("path", ""))
                elif func_name == "exec_shell":
                    result = await exec_shell_interactive(ctx, args.get("command"))
                
                # Ajouter le résultat à l'historique de conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result or "Commande exécutée avec succès (aucune sortie)."
                })
                
    except Exception as e:
        await ctx.send(format_console_output("❌ **Erreur fatale de l'agent** :", str(e), "python"))

bot.run(os.getenv("DISCORD_TOKEN"))