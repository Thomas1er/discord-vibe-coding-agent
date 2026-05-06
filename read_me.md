# 🚀 Documentation de Vibe Pilot

**Vibe Pilot** est un agent de codage autonome intégré à Discord. Il permet de dialoguer avec une Intelligence Artificielle (DeepSeek) pour qu'elle explore votre projet, lise vos fichiers, écrive du code et lance des commandes dans votre terminal, de manière totalement autonome mais sécurisée.

---

## 👤 Ce que VOUS pouvez faire (Utilisateur)

L'interaction avec l'agent se fait principalement via Discord.

### 1. Les Commandes de base
*   **`!vibe <instructions>`** : Lance l'agent avec une mission. 
    *   *Exemple :* `!vibe Crée un script python qui affiche l'heure, lance-le pour tester, et dis-moi si ça marche.`
    *   *Exemple 2 :* `!vibe Le dernier changement a tout cassé, reviens à la version précédente.`
*   **`!reset`** : Efface la mémoire de l'agent pour le salon Discord actuel. Très utile pour commencer un nouveau projet ou si l'agent s'emmêle les pinceaux avec le vieux contexte.

### 2. Interactions en cours d'exécution
*   **Autoriser la continuation** : Par sécurité, l'agent s'arrête après 15 "actions" (réflexions/appels de fonctions). S'il a encore besoin de réfléchir, un message Discord avec des boutons apparaîtra. Vous pouvez cliquer sur **"Autoriser +15 actions"** 🟢 pour le laisser terminer, ou **"Arrêter l'agent"** 🔴.
*   **Gestion des Timeouts longs** : Si une commande de l'agent met trop de temps (ex: boucle infinie ou téléchargement long), elle est mise en pause. Vous recevrez un aperçu des logs et pourrez décider via des boutons de lui accorder **30 secondes supplémentaires** ou de la **Tuer**.
*   **Lecture des logs complets** : Si une erreur console est très longue, le bot joindra automatiquement un fichier `full_output.txt` au message Discord pour ne pas inonder le salon.

### 3. Restauration d'urgence (Rollbacks physiques)
*   Si l'IA a fait une erreur irréparable ou que vous souhaitez retrouver le fichier d'origine, allez dans le dossier caché **`.vibe_backups/`** à la racine de votre projet (`~/projects`).
*   Chaque fichier modifié par l'agent y possède une sauvegarde datant de *juste avant* l'édition (ex: `chemin_vers_fichier.py.bak`).

---

## 🤖 Ce que l'AGENT peut faire (Capacités Autonomes)

Dès que vous lancez `!vibe`, l'agent entre dans une "boucle d'autonomie" et utilise des outils (Tool Calling) sans vous demander la permission.

### 1. 👁️ Explorer l'environnement (Vision)
*   **Analyse automatique** : Dès le premier message, l'agent reçoit l'arborescence actuelle (fichiers pertinents) de votre projet.
*   **Exploration approfondie** : Si nécessaire, il peut utiliser l'outil `list_directory` pour lister le contenu de sous-dossiers spécifiques.
*   **Lecture de code** : Il utilise `read_file` pour analyser le contenu complet de n'importe quel fichier avant de le modifier.

### 2. ✍️ Écrire et Modifier du Code
*   **Écriture multi-fichiers** : L'agent peut générer de longs blocs de code pour un ou plusieurs fichiers simultanément via une syntaxe texte sécurisée (blocs `FILE:`). 
*   **Remplacement sûr** : Avant d'écraser un fichier sur votre disque dur, l'agent (via le script Python) génère silencieusement un backup `.bak`.

### 3. 🖥️ Exécuter des Commandes (Shell)
*   L'agent a le pouvoir de lancer des commandes bash via l'outil `exec_shell`. 
*   **Tests automatisés** : Il est instruit de tester systématiquement son code après modification. S'il génère un script, il essaiera de l'exécuter. S'il manque des dépendances, il fera un `pip install` ou `npm install`.
*   **Timeouts Adaptatifs** : L'agent sait détecter la nature d'une commande. Il allouera 120 secondes pour des installations lourdes, 60s pour des tests, et 20s pour des commandes classiques.

### 4. 🧠 Mémoire Contextuelle (Le Fil d'Ariane)
*   L'agent se souvient de toute la conversation dans un salon donné. 
*   Il connaît vos consignes initiales, les résultats des tests qu'il a lancés, et les modifications qu'il a apportées, ce qui lui permet d'itérer ("Ah, j'ai vu l'erreur, je corrige !") au lieu de repartir de zéro à chaque message.
